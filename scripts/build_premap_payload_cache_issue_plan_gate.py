#!/usr/bin/env python3
"""Build a strict issue-plan gate from the native producer-state canary.

The gate intentionally stays above real payload movement.  It verifies that the
online producer transition-state packet and the native stub agree on the issue
prefix that a future payload/cache-manager runtime would consume.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
    / "premap_payload_cache_issue_plan_gate_dolly128_gen64_native_v1.json"
)

ARTIFACT_KIND = "premap_payload_cache_issue_plan_gate"
GATE_NAME = "premap_payload_cache_issue_plan_gate_v1"
ISSUE_PLAN_SCHEMA_NAME = "premap_payload_cache_producer_issue_plan_v1"
ISSUE_PLAN_SCHEMA_FIELDS = (
    "layer_id",
    "issue_candidate_count",
    "issue_candidate_first_expert",
    "issue_candidate_last_expert",
    "issue_candidate_hash",
    "state_hash",
    "payload_bytes",
    "ready_credit",
    "passed_to_kernel",
    "changes_kernel_launch_args",
)
ISSUE_PLAN_SCHEMA_HASH = hashlib.sha256(
    "|".join(ISSUE_PLAN_SCHEMA_FIELDS).encode("utf-8")
).hexdigest()
SAFE_FALSE_FLAGS = (
    "ready_credit",
    "ready_before_demand_credit",
    "payload_deref_allowed",
    "payload_transfer_enabled",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "current_wna16_arg_compatible",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)
SAFE_ZERO_FLAGS = ("payload_bytes",)
ALLOWED_SELECTION_MODES = {
    "first_nonempty_issue",
    "summary_first_nonempty_issue",
    "explicit_packet_json_nonempty_issue",
}
REQUIRED_NATIVE_ISSUE_KEYS = (
    "issue_candidate_count",
    "issue_candidate_hash",
    "issue_candidate_first_expert",
    "issue_candidate_last_expert",
)
PACKET_SAFE_FALSE_FLAGS = (
    "ready_credit",
    "passed_to_kernel",
    "changes_kernel_launch_args",
)
PACKET_SAFE_ZERO_FLAGS = ("payload_bytes",)
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
U64_MASK = 0xFFFFFFFFFFFFFFFF


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


def _canonical_experts(values: Any) -> tuple[int, ...]:
    if not isinstance(values, list):
        raise ValueError("expert list must be a list")
    if any(type(value) is not int for value in values):
        raise ValueError("expert list must contain only ints")
    if any(int(value) < 0 for value in values):
        raise ValueError("expert list must be non-negative")
    return tuple(sorted({int(value) for value in values}))


def _issue_experts_from_packet(packet: dict[str, Any]) -> tuple[int, ...]:
    previous = _canonical_experts(packet.get("previous_experts", []))
    topk = int(packet.get("transition_topk_count", 0) or 0)
    if topk < 0:
        raise ValueError("transition_topk_count must be non-negative")
    limit = len(previous) if topk == 0 else min(len(previous), topk)
    return previous[:limit]


def _issue_hash(issue_experts: tuple[int, ...]) -> str:
    value = FNV_OFFSET
    count = 0
    for expert_id in issue_experts:
        value ^= int(expert_id) & 0xFFFFFFFF
        value = (value * FNV_PRIME) & U64_MASK
        count += 1
    value ^= count & 0xFFFFFFFF
    value = (value * FNV_PRIME) & U64_MASK
    return f"{value:016x}"


def _packet_issue_summary(packet: dict[str, Any]) -> dict[str, Any]:
    issue_experts = _issue_experts_from_packet(packet)
    return {
        "issue_candidate_experts": list(issue_experts),
        "issue_candidate_count": len(issue_experts),
        "issue_candidate_first_expert": int(issue_experts[0]) if issue_experts else -1,
        "issue_candidate_last_expert": int(issue_experts[-1]) if issue_experts else -1,
        "issue_candidate_hash": _issue_hash(issue_experts),
    }


def _check_online_flags(online: dict[str, Any], failures: list[str]) -> None:
    for key in ("ok", "passed", "ready", "native_stub_invoked"):
        if online.get(key) is not True:
            failures.append(f"{key}_not_true")
    if online.get("native_returncode") != 0:
        failures.append("native_returncode_nonzero")
    if online.get("failures") not in ([], None):
        failures.append("online_failures_not_empty")
    if online.get("input_source") != "semantic_packet_json":
        failures.append("input_source_not_semantic_packet_json")
    if (
        online.get("online_export_source")
        != "runtime_shadow_premap_payload_cache_producer_state_packet_export"
    ):
        failures.append("online_export_source_mismatch")
    if online.get("selected_packet_selection_mode") not in ALLOWED_SELECTION_MODES:
        failures.append("selected_packet_selection_mode_not_nonempty")
    for key in SAFE_FALSE_FLAGS:
        if key in online and online.get(key) is not False:
            failures.append(f"{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        if key in online and online.get(key) != 0:
            failures.append(f"{key}_not_zero")


def _check_packet_flags(packet: dict[str, Any], failures: list[str]) -> None:
    if packet.get("ready") is not True:
        failures.append("packet_ready_not_true")
    for key in PACKET_SAFE_FALSE_FLAGS:
        if key in packet and packet.get(key) is not False:
            failures.append(f"packet_{key}_not_false")
    for key in PACKET_SAFE_ZERO_FLAGS:
        if key in packet and packet.get(key) != 0:
            failures.append(f"packet_{key}_not_zero")
    for key in (
        "ready_before_demand_credit",
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if key in packet and packet.get(key) is not False:
            failures.append(f"packet_{key}_not_false")


def _check_selected_packet_provenance(
    *,
    online: dict[str, Any],
    packet_path: Path,
    online_path: Path,
    failures: list[str],
) -> None:
    raw_paths = online.get("online_packet_export_paths")
    if isinstance(raw_paths, list) and raw_paths:
        resolved_paths = {
            str(_resolve(path, base_dir=online_path.parent).resolve())
            for path in raw_paths
            if isinstance(path, str) and path
        }
        try:
            selected_resolved = str(packet_path.resolve())
        except OSError:
            selected_resolved = str(packet_path)
        if selected_resolved not in resolved_paths:
            failures.append("selected_packet_not_in_online_export_paths")
    selected_index = online.get("selected_packet_index")
    if isinstance(selected_index, int) and isinstance(raw_paths, list):
        if selected_index < 0 or selected_index >= len(raw_paths):
            failures.append("selected_packet_index_out_of_range")
        else:
            indexed_path = _resolve(raw_paths[selected_index], base_dir=online_path.parent)
            try:
                indexed_matches = indexed_path.resolve() == packet_path.resolve()
            except OSError:
                indexed_matches = indexed_path == packet_path
            if not indexed_matches:
                failures.append("selected_packet_index_path_mismatch")


def _check_issue_plan(
    *,
    online: dict[str, Any],
    packet_summary: dict[str, Any],
    require_nonempty_issue: bool,
    failures: list[str],
) -> None:
    issue_count = packet_summary["issue_candidate_count"]
    if require_nonempty_issue and issue_count <= 0:
        failures.append("issue_candidate_count_not_positive")
    for key in REQUIRED_NATIVE_ISSUE_KEYS:
        if key not in online:
            failures.append(f"native_{key}_missing")
        elif online.get(key) != packet_summary[key]:
            failures.append(f"native_{key}_packet_mismatch")
    expected_hash = online.get("expected_issue_candidate_hash")
    if expected_hash is not None and expected_hash != packet_summary["issue_candidate_hash"]:
        failures.append("expected_issue_candidate_hash_packet_mismatch")


def build_issue_plan_gate(args: argparse.Namespace) -> dict[str, Any]:
    online_path = _resolve(args.online_canary_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    online: dict[str, Any] = {}
    packet: dict[str, Any] = {}
    packet_path: Path | None = None
    packet_summary = {
        "issue_candidate_experts": [],
        "issue_candidate_count": 0,
        "issue_candidate_first_expert": -1,
        "issue_candidate_last_expert": -1,
        "issue_candidate_hash": "0000000000000000",
    }
    try:
        online = _load_json(online_path, label="online canary")
    except Exception as exc:
        failures.append(f"online_canary_load_failed:{exc.__class__.__name__}:{exc}")
    if online:
        _check_online_flags(online, failures)
        raw_packet_path = online.get("selected_packet_json") or online.get("packet_json")
        if not isinstance(raw_packet_path, str) or not raw_packet_path:
            failures.append("selected_packet_json_missing")
        else:
            packet_path = _resolve(raw_packet_path, base_dir=online_path.parent)
            if not packet_path.exists():
                failures.append("selected_packet_json_not_found")
            else:
                try:
                    packet = _load_json(packet_path, label="producer-state packet")
                    _check_selected_packet_provenance(
                        online=online,
                        packet_path=packet_path,
                        online_path=online_path,
                        failures=failures,
                    )
                    _check_packet_flags(packet, failures)
                    packet_summary = _packet_issue_summary(packet)
                    _check_issue_plan(
                        online=online,
                        packet_summary=packet_summary,
                        require_nonempty_issue=bool(args.require_nonempty_issue),
                        failures=failures,
                    )
                except Exception as exc:
                    failures.append(f"packet_issue_summary_failed:{exc.__class__.__name__}:{exc}")

    passed = not failures
    payload = {
        "artifact_kind": ARTIFACT_KIND,
        "gate_name": GATE_NAME,
        "issue_plan_schema_name": ISSUE_PLAN_SCHEMA_NAME,
        "issue_plan_schema_hash": ISSUE_PLAN_SCHEMA_HASH,
        "issue_plan_schema_fields": list(ISSUE_PLAN_SCHEMA_FIELDS),
        "passed": passed,
        "failures": failures,
        "issue_plan_ready": passed,
        "payload_cache_issue_plan_candidate": passed,
        "native_issue_plan_valid": passed,
        "runtime_contract_ready": passed,
        "online_canary_json": str(online_path),
        "online_canary_sha256": _sha256(online_path),
        "selected_packet_json": None if packet_path is None else str(packet_path),
        "selected_packet_sha256": None if packet_path is None else _sha256(packet_path),
        "selected_packet_selection_mode": online.get("selected_packet_selection_mode"),
        "online_packet_export_count": online.get("online_packet_export_count"),
        "online_configured_export_count": online.get("online_configured_export_count"),
        "layer_id": online.get("layer_id", packet.get("layer_id")),
        "state_hash": online.get("state_hash"),
        "packet_state_hash": online.get("packet_state_hash"),
        "issue_candidate_count": int(packet_summary["issue_candidate_count"]),
        "issue_candidate_first_expert": int(
            packet_summary["issue_candidate_first_expert"]
        ),
        "issue_candidate_last_expert": int(packet_summary["issue_candidate_last_expert"]),
        "issue_candidate_hash": str(packet_summary["issue_candidate_hash"]),
        "issue_candidate_experts": list(packet_summary["issue_candidate_experts"]),
        "native_issue_candidate_count": online.get("issue_candidate_count"),
        "native_issue_candidate_hash": online.get("issue_candidate_hash"),
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "next_runtime_stage": "implement_payload_cache_manager_issue_executor",
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
    parser.add_argument("--require-nonempty-issue", action="store_true", default=True)
    parser.add_argument("--allow-empty-issue", dest="require_nonempty_issue", action="store_false")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_issue_plan_gate(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
