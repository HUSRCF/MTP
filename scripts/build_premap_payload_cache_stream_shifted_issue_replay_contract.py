#!/usr/bin/env python3
"""Build a token-shifted producer issue replay contract.

This artifact is the next step after the queue-aware earlier-issue gate: it
does not move payload, grant ready credit, or pass kernel arguments. It only
uses real exported producer packets to prove that a token-index lead can be
materialized into a deterministic issue schedule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
U64_MASK = 0xFFFFFFFFFFFFFFFF
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ONLINE_CANARY_JSON = (
    REPO_ROOT
    / "data"
    / "traces"
    / "external_prompt_gate_dolly_4_awq_vllm_gpu1_decode_gen64_producer_state_packet_export_token_provenance_smoke_v3"
    / "producer_packet_token_provenance_online_canary.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_stream_shifted_issue_replay_contract_v1.json"
)

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
OPTIONAL_SAFE_FALSE_FLAGS = (
    "full_fetch_runtime_allowed",
    "full_fetch_allowed",
    "current_wna16_arg_compatible",
    "requires_wna16_arg_reinterpretation",
    "wna16_benchmark_ready",
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


def _valid_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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
    for key in OPTIONAL_SAFE_FALSE_FLAGS:
        if key in payload and payload.get(key) is not False:
            failures.append(f"{prefix}_{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif not _valid_number(payload.get(key)) or float(payload.get(key)) != 0.0:
            failures.append(f"{prefix}_{key}_not_zero")


def _issue_hash_from_packet(packet: dict[str, Any]) -> str | None:
    value = packet.get("issue_candidate_hash")
    return str(value) if isinstance(value, str) and value else None


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


def _issue_candidates_from_packet(
    packet: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
) -> tuple[int, int, int, str | None]:
    raw_experts = packet.get("issue_candidate_experts")
    if not isinstance(raw_experts, list):
        failures.append(f"{prefix}_issue_candidate_experts_invalid")
        experts: list[int] = []
    else:
        experts = []
        for offset, value in enumerate(raw_experts):
            if _is_int(value) and int(value) >= 0:
                experts.append(int(value))
            else:
                failures.append(f"{prefix}_issue_candidate_expert_{offset}_invalid")
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
        if key not in packet:
            failures.append(f"{prefix}_{key}_missing")
        elif packet.get(key) != expected:
            failures.append(f"{prefix}_{key}_mismatch")
    return expected_count, expected_first, expected_last, expected_hash


def _check_context_issue_mirror(
    context: dict[str, Any],
    *,
    issue_count: int,
    issue_first: int,
    issue_last: int,
    issue_hash: str | None,
    failures: list[str],
    prefix: str,
) -> None:
    checks: tuple[tuple[str, int | str | None], ...] = (
        ("issue_candidate_count", issue_count),
        ("issue_candidate_first_expert", issue_first),
        ("issue_candidate_last_expert", issue_last),
        ("issue_candidate_hash", issue_hash),
    )
    for key, expected in checks:
        if key not in context:
            failures.append(f"{prefix}_{key}_missing")
        elif context.get(key) != expected:
            failures.append(f"{prefix}_{key}_mismatch")


def build_shifted_issue_replay_contract(args: argparse.Namespace) -> dict[str, Any]:
    online_path = _resolve(args.online_canary_json)
    output_path = _resolve(args.output_json)
    issue_lead_tokens = int(args.issue_lead_tokens)
    if issue_lead_tokens < 0:
        raise ValueError("issue-lead-tokens must be non-negative")
    failures: list[str] = []
    try:
        online = _load_json(online_path, label="online canary")
    except Exception as exc:
        online = {}
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
    if _is_int(online_packet_export_count):
        if len(raw_paths) != int(online_packet_export_count):
            failures.append("online_packet_export_paths_count_mismatch")
    else:
        failures.append("online_packet_export_count_invalid")
    online_configured_export_count = online.get("online_configured_export_count")
    if _is_int(online_configured_export_count):
        if int(online_configured_export_count) != len(raw_paths):
            failures.append("online_configured_export_count_mismatch")
    else:
        failures.append("online_configured_export_count_invalid")

    rows: list[dict[str, Any]] = []
    demand_keys: set[tuple[int | None, str | None, int, int, int]] = set()
    issue_keys: set[tuple[int | None, str | None, int, int, int]] = set()
    packet_count = 0
    schedulable_packet_count = 0
    empty_issue_exempt_count = 0
    clamped_issue_count = 0
    duplicate_demand_key_count = 0
    duplicate_issue_key_count = 0
    total_issue_candidates = 0
    issue_hashes: list[str] = []
    first_packet_path: str | None = None
    last_packet_path: str | None = None

    for index, raw_path in enumerate(raw_paths):
        if not isinstance(raw_path, str) or not raw_path:
            failures.append(f"packet_{index}_path_invalid")
            continue
        packet_path = _resolve(raw_path, base_dir=online_path.parent)
        if first_packet_path is None:
            first_packet_path = str(packet_path)
        last_packet_path = str(packet_path)
        try:
            packet = _load_json(packet_path, label=f"packet {index}")
        except Exception as exc:
            failures.append(
                f"packet_{index}_load_failed:{exc.__class__.__name__}:{exc}"
            )
            continue
        packet_count += 1
        _check_safe_flags(packet, failures, prefix=f"packet_{index}")
        if packet.get("ready") is not True:
            failures.append(f"packet_{index}_ready_not_true")
        raw_layer_id = packet.get("layer_id")
        if _is_int(raw_layer_id) and int(raw_layer_id) >= 0:
            layer_id = int(raw_layer_id)
        else:
            layer_id = -1
            failures.append(f"packet_{index}_layer_id_invalid")
        issue_count, issue_first, issue_last, issue_hash = _issue_candidates_from_packet(
            packet,
            failures,
            prefix=f"packet_{index}",
        )

        context = packet.get("_export_context")
        if not isinstance(context, dict):
            failures.append(f"packet_{index}_export_context_missing")
            continue
        _check_safe_flags(context, failures, prefix=f"packet_{index}_export_context")
        _check_context_issue_mirror(
            context,
            issue_count=issue_count,
            issue_first=issue_first,
            issue_last=issue_last,
            issue_hash=issue_hash,
            failures=failures,
            prefix=f"packet_{index}_export_context",
        )
        context_layer_id = context.get("layer_id")
        if not (_is_int(context_layer_id) and int(context_layer_id) == layer_id):
            failures.append(f"packet_{index}_export_context_layer_id_mismatch")

        source = context.get("token_index_source")
        empty_config_exempt = (
            bool(args.allow_empty_config_packets)
            and issue_count == 0
            and source == "config"
        )
        if bool(args.allow_empty_config_packets) and issue_count == 0 and source != "config":
            failures.append(f"packet_{index}_empty_issue_source_not_config")
        requires_token_provenance = not empty_config_exempt
        if empty_config_exempt:
            empty_issue_exempt_count += 1

        if not requires_token_provenance:
            continue

        token_index = context.get("token_index")
        if not (_is_int(token_index) and int(token_index) >= 0):
            failures.append(f"packet_{index}_token_index_invalid")
            continue
        if source == "decode_workload_collector":
            pass
        elif source == "config" and bool(args.allow_config_token_source):
            pass
        else:
            failures.append(f"packet_{index}_token_index_source_unexpected")
        sample_idx = context.get("sample_idx")
        record_id = context.get("record_id")
        sequence_id = context.get("sequence_id")
        normalized_sample_idx = int(sample_idx) if _is_int(sample_idx) else None
        normalized_record_id = (
            str(record_id) if isinstance(record_id, str) and record_id else None
        )
        normalized_sequence_id = int(sequence_id) if _is_int(sequence_id) else 0
        if normalized_sample_idx is None and not bool(args.allow_missing_sample_idx):
            failures.append(f"packet_{index}_sample_idx_invalid")
        if normalized_record_id is None and not bool(args.allow_missing_record_id):
            failures.append(f"packet_{index}_record_id_invalid")

        demand_token_index = int(token_index)
        unclamped_issue_token_index = demand_token_index - issue_lead_tokens
        issue_token_index = max(0, unclamped_issue_token_index)
        clamped = unclamped_issue_token_index < 0
        if clamped:
            clamped_issue_count += 1
        demand_key = (
            normalized_sample_idx,
            normalized_record_id,
            normalized_sequence_id,
            layer_id,
            demand_token_index,
        )
        issue_key = (
            normalized_sample_idx,
            normalized_record_id,
            normalized_sequence_id,
            layer_id,
            issue_token_index,
        )
        if demand_key in demand_keys:
            duplicate_demand_key_count += 1
        demand_keys.add(demand_key)
        if issue_key in issue_keys:
            duplicate_issue_key_count += 1
        issue_keys.add(issue_key)

        issue_hash = _issue_hash_from_packet(packet)
        if issue_hash is not None:
            issue_hashes.append(issue_hash)
        total_issue_candidates += max(0, issue_count)
        schedulable_packet_count += 1
        rows.append(
            {
                "packet_index": index,
                "packet_path": str(packet_path),
                "layer_id": layer_id,
                "sample_idx": normalized_sample_idx,
                "record_id": normalized_record_id,
                "sequence_id": normalized_sequence_id,
                "demand_token_index": demand_token_index,
                "issue_token_index": issue_token_index,
                "issue_lead_tokens": issue_lead_tokens,
                "issue_clamped_to_zero": clamped,
                "token_index_source": source,
                "issue_candidate_count": issue_count,
                "issue_candidate_hash": issue_hash,
            }
        )

    if schedulable_packet_count < int(args.min_schedulable_packet_count):
        failures.append("schedulable_packet_count_below_min")
    if duplicate_demand_key_count:
        failures.append("duplicate_demand_keys_present")
    if duplicate_issue_key_count and not bool(args.allow_duplicate_issue_keys):
        failures.append("duplicate_issue_keys_present")
    if clamped_issue_count and not bool(args.allow_clamped_issue_tokens):
        failures.append("clamped_issue_tokens_present")

    payload = {
        "artifact_kind": "premap_payload_cache_stream_shifted_issue_replay_contract",
        "passed": not failures,
        "failures": failures,
        "online_canary_json": str(online_path),
        "online_canary_sha256": _sha256(online_path),
        "issue_lead_tokens": issue_lead_tokens,
        "packet_count": packet_count,
        "online_packet_export_count": (
            int(online_packet_export_count)
            if _is_int(online_packet_export_count)
            else None
        ),
        "schedulable_packet_count": schedulable_packet_count,
        "empty_issue_exempt_count": empty_issue_exempt_count,
        "clamped_issue_count": clamped_issue_count,
        "duplicate_demand_key_count": duplicate_demand_key_count,
        "duplicate_issue_key_count": duplicate_issue_key_count,
        "unique_issue_key_count": len(issue_keys),
        "unique_demand_key_count": len(demand_keys),
        "total_issue_candidates": total_issue_candidates,
        "issue_hash_count": len(issue_hashes),
        "issue_hash_unique_count": len(set(issue_hashes)),
        "first_packet_path": first_packet_path,
        "last_packet_path": last_packet_path,
        "min_schedulable_packet_count": int(args.min_schedulable_packet_count),
        "allow_config_token_source": bool(args.allow_config_token_source),
        "allow_empty_config_packets": bool(args.allow_empty_config_packets),
        "allow_missing_sample_idx": bool(args.allow_missing_sample_idx),
        "allow_missing_record_id": bool(args.allow_missing_record_id),
        "allow_clamped_issue_tokens": bool(args.allow_clamped_issue_tokens),
        "allow_duplicate_issue_keys": bool(args.allow_duplicate_issue_keys),
        "full_fetch_runtime_allowed": False,
        "full_fetch_allowed": False,
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
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "wna16_benchmark_ready": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "rows": rows,
        "boundary": (
            "shifted producer issue replay contract only; no payload movement, "
            "ready credit, kernel arg pass, or endpoint latency"
        ),
        "next_runtime_stage": (
            "producer_side_shifted_issue_runtime_shadow"
            if not failures
            else "fix_token_provenance_or_keep_full_fetch_blocked"
        ),
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
    parser.add_argument("--issue-lead-tokens", type=int, default=1)
    parser.add_argument("--min-schedulable-packet-count", type=int, default=1)
    parser.add_argument("--allow-config-token-source", action="store_true")
    parser.add_argument(
        "--allow-empty-config-packets",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Allow issue_candidate_count=0 packets to keep config/static token "
            "provenance. Enabled by default because the default online canary "
            "contains empty bootstrap packets."
        ),
    )
    parser.add_argument("--allow-missing-sample-idx", action="store_true")
    parser.add_argument("--allow-missing-record-id", action="store_true")
    parser.add_argument("--allow-clamped-issue-tokens", action="store_true")
    parser.add_argument("--allow-duplicate-issue-keys", action="store_true")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_shifted_issue_replay_contract(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
