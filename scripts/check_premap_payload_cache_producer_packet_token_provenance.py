#!/usr/bin/env python3
"""Check decode-token provenance on exported producer-state packets.

This gate sits between the online producer-state export and token-aware replay.
It does not move payload bytes, grant ready credit, or pass kernel arguments.
It only verifies that exported packets carry enough provenance to shift issue
events by decode-token lead in a later replay step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
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
    / "premap_payload_cache_producer_packet_token_provenance_gate_v1.json"
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
        elif payload.get(key) != 0:
            failures.append(f"{prefix}_{key}_not_zero")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    if len(values) == 1:
        return int(values[0])
    index = round((float(pct) / 100.0) * (len(values) - 1))
    index = max(0, min(len(values) - 1, int(index)))
    return int(sorted(values)[index])


def check_packet_token_provenance(args: argparse.Namespace) -> dict[str, Any]:
    online_path = _resolve(args.online_canary_json)
    output_path = _resolve(args.output_json)
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

    packet_count = 0
    packet_error_count = 0
    valid_token_count = 0
    decode_source_count = 0
    config_source_count = 0
    missing_source_count = 0
    nonempty_issue_count = 0
    empty_issue_provenance_exempt_count = 0
    required_token_provenance_packet_count = 0
    required_decode_source_count = 0
    required_valid_token_count = 0
    required_config_source_count = 0
    required_missing_source_count = 0
    missing_context_count = 0
    token_indices: list[int] = []
    required_token_indices: list[int] = []
    sample_indices: set[int] = set()
    record_ids: set[str] = set()
    layer_ids: set[int] = set()
    token_layer_keys: set[tuple[int | None, str | None, int, int]] = set()
    required_token_layer_keys: set[tuple[int | None, str | None, int, int]] = set()
    duplicate_token_layer_count = 0
    required_duplicate_token_layer_count = 0
    first_packet_path: str | None = None
    last_packet_path: str | None = None
    first_token_index: int | None = None
    last_token_index: int | None = None

    for index, raw_path in enumerate(raw_paths):
        if not isinstance(raw_path, str) or not raw_path:
            failures.append(f"packet_{index}_path_invalid")
            packet_error_count += 1
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
            packet_error_count += 1
            continue
        packet_count += 1
        _check_safe_flags(packet, failures, prefix=f"packet_{index}")
        if packet.get("ready") is not True:
            failures.append(f"packet_{index}_ready_not_true")
        layer_id = packet.get("layer_id")
        if _is_int(layer_id):
            layer_ids.add(int(layer_id))
        else:
            failures.append(f"packet_{index}_layer_id_invalid")
            layer_id = -1
        issue_candidate_count = packet.get("issue_candidate_count")
        if _is_int(issue_candidate_count):
            if int(issue_candidate_count) > 0:
                nonempty_issue_count += 1
        else:
            failures.append(f"packet_{index}_issue_candidate_count_invalid")
            issue_candidate_count = -1
        requires_token_provenance = not (
            bool(args.allow_empty_config_packets)
            and _is_int(issue_candidate_count)
            and int(issue_candidate_count) == 0
        )
        if requires_token_provenance:
            required_token_provenance_packet_count += 1
        else:
            empty_issue_provenance_exempt_count += 1
        context = packet.get("_export_context")
        if not isinstance(context, dict):
            missing_context_count += 1
            failures.append(f"packet_{index}_export_context_missing")
            continue
        _check_safe_flags(context, failures, prefix=f"packet_{index}_export_context")
        token_index = context.get("token_index")
        sample_idx = context.get("sample_idx")
        record_id = context.get("record_id")
        normalized_sample_idx = int(sample_idx) if _is_int(sample_idx) else None
        normalized_record_id = (
            str(record_id) if isinstance(record_id, str) and record_id else None
        )
        if _is_int(token_index) and int(token_index) >= 0:
            token_value = int(token_index)
            token_indices.append(token_value)
            valid_token_count += 1
            if requires_token_provenance:
                required_valid_token_count += 1
                required_token_indices.append(token_value)
            key = (
                normalized_sample_idx,
                normalized_record_id,
                token_value,
                int(layer_id),
            )
            if key in token_layer_keys:
                duplicate_token_layer_count += 1
            token_layer_keys.add(key)
            if requires_token_provenance:
                if key in required_token_layer_keys:
                    required_duplicate_token_layer_count += 1
                required_token_layer_keys.add(key)
            if first_token_index is None:
                first_token_index = token_value
            last_token_index = token_value
        elif requires_token_provenance:
            failures.append(f"packet_{index}_token_index_invalid")
        source = context.get("token_index_source")
        if source == "decode_workload_collector":
            decode_source_count += 1
            if requires_token_provenance:
                required_decode_source_count += 1
        elif source == "config":
            config_source_count += 1
            if requires_token_provenance:
                required_config_source_count += 1
        elif source is None:
            missing_source_count += 1
            if requires_token_provenance:
                required_missing_source_count += 1
                failures.append(f"packet_{index}_token_index_source_missing")
        else:
            if requires_token_provenance:
                failures.append(f"packet_{index}_token_index_source_unexpected")
        if normalized_sample_idx is not None:
            if requires_token_provenance:
                sample_indices.add(normalized_sample_idx)
        elif requires_token_provenance and not bool(args.allow_missing_sample_idx):
            failures.append(f"packet_{index}_sample_idx_invalid")
        if normalized_record_id is not None:
            if requires_token_provenance:
                record_ids.add(normalized_record_id)
        elif requires_token_provenance and not bool(args.allow_missing_record_id):
            failures.append(f"packet_{index}_record_id_invalid")

    if packet_count < int(args.min_packet_count):
        failures.append("packet_count_below_min")
    if nonempty_issue_count < int(args.min_nonempty_packet_count):
        failures.append("nonempty_packet_count_below_min")
    if required_valid_token_count < int(args.min_valid_token_count):
        failures.append("valid_token_count_below_min")
    if not bool(args.allow_config_token_source):
        if required_decode_source_count != required_token_provenance_packet_count:
            failures.append("decode_workload_source_count_mismatch")
        if required_config_source_count:
            failures.append("config_token_source_present")
        if required_missing_source_count:
            failures.append("missing_token_source_present")
    if required_duplicate_token_layer_count:
        failures.append("duplicate_token_layer_keys_present")
    if packet_error_count:
        failures.append("packet_error_count_nonzero")
    if missing_context_count:
        failures.append("missing_context_count_nonzero")

    sorted_tokens = sorted(token_indices)
    token_span = (
        None
        if not sorted_tokens
        else int(sorted_tokens[-1]) - int(sorted_tokens[0]) + 1
    )
    payload = {
        "artifact_kind": "premap_payload_cache_producer_packet_token_provenance_gate",
        "passed": not failures,
        "failures": failures,
        "online_canary_json": str(online_path),
        "online_canary_sha256": _sha256(online_path),
        "packet_count": packet_count,
        "online_packet_export_count": (
            int(online_packet_export_count)
            if _is_int(online_packet_export_count)
            else None
        ),
        "packet_error_count": packet_error_count,
        "missing_context_count": missing_context_count,
        "nonempty_packet_count": nonempty_issue_count,
        "empty_issue_provenance_exempt_count": empty_issue_provenance_exempt_count,
        "required_token_provenance_packet_count": required_token_provenance_packet_count,
        "valid_token_count": valid_token_count,
        "required_valid_token_count": required_valid_token_count,
        "decode_workload_source_count": decode_source_count,
        "required_decode_workload_source_count": required_decode_source_count,
        "config_source_count": config_source_count,
        "required_config_source_count": required_config_source_count,
        "missing_source_count": missing_source_count,
        "required_missing_source_count": required_missing_source_count,
        "sample_count": len(sample_indices),
        "record_count": len(record_ids),
        "layer_count": len(layer_ids),
        "layer_ids": sorted(layer_ids),
        "token_index_min": sorted_tokens[0] if sorted_tokens else None,
        "token_index_p50": _percentile(sorted_tokens, 50.0),
        "token_index_p90": _percentile(sorted_tokens, 90.0),
        "token_index_max": sorted_tokens[-1] if sorted_tokens else None,
        "token_index_mean": (
            None if not token_indices else float(statistics.fmean(token_indices))
        ),
        "first_token_index": first_token_index,
        "last_token_index": last_token_index,
        "token_span": token_span,
        "unique_token_count": len(set(token_indices)),
        "required_unique_token_count": len(set(required_token_indices)),
        "unique_token_layer_count": len(token_layer_keys),
        "duplicate_token_layer_count": duplicate_token_layer_count,
        "required_unique_token_layer_count": len(required_token_layer_keys),
        "required_duplicate_token_layer_count": required_duplicate_token_layer_count,
        "first_packet_path": first_packet_path,
        "last_packet_path": last_packet_path,
        "min_packet_count": int(args.min_packet_count),
        "min_nonempty_packet_count": int(args.min_nonempty_packet_count),
        "min_valid_token_count": int(args.min_valid_token_count),
        "require_decode_workload_source": not bool(args.allow_config_token_source),
        "require_sample_idx": not bool(args.allow_missing_sample_idx),
        "require_record_id": not bool(args.allow_missing_record_id),
        "allow_config_token_source": bool(args.allow_config_token_source),
        "allow_empty_config_packets": bool(args.allow_empty_config_packets),
        "allow_missing_sample_idx": bool(args.allow_missing_sample_idx),
        "allow_missing_record_id": bool(args.allow_missing_record_id),
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "full_fetch_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "boundary": (
            "producer packet token-provenance gate only; no payload movement, "
            "ready credit, kernel arg pass, or endpoint latency"
        ),
        "next_runtime_stage": "token_aware_shifted_issue_stream_replay",
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
    parser.add_argument("--min-packet-count", type=int, default=1)
    parser.add_argument("--min-nonempty-packet-count", type=int, default=1)
    parser.add_argument("--min-valid-token-count", type=int, default=1)
    parser.add_argument(
        "--allow-config-token-source",
        action="store_true",
        help="Audit-only mode: allow config/static token provenance instead of requiring decode workload source.",
    )
    parser.add_argument(
        "--allow-empty-config-packets",
        action="store_true",
        help=(
            "Allow issue_candidate_count=0 packets to keep config/static token "
            "provenance; nonempty packets still require decode workload provenance."
        ),
    )
    parser.add_argument(
        "--allow-missing-sample-idx",
        action="store_true",
        help="Audit-only mode: allow packets without sample_idx provenance.",
    )
    parser.add_argument(
        "--allow-missing-record-id",
        action="store_true",
        help="Audit-only mode: allow packets without record_id provenance.",
    )
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = check_packet_token_provenance(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
