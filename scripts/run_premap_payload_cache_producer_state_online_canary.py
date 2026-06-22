#!/usr/bin/env python3
"""Run the producer transition-state native canary from online packet exports."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_stub_runner():
    path = REPO_ROOT / "scripts" / "run_premap_payload_cache_producer_state_stub.py"
    spec = importlib.util.spec_from_file_location(
        "run_premap_payload_cache_producer_state_stub",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load producer-state stub runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _resolve_path(raw: Any, *, base_dir: Path) -> Path | None:
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = base_dir / path
    return path


def _packet_paths_from_performance(
    performance: dict[str, Any],
    *,
    base_dir: Path,
) -> list[Path]:
    raw_paths = performance.get(
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths",
        [],
    )
    paths: list[Path] = []
    if isinstance(raw_paths, list):
        for raw_path in raw_paths:
            path = _resolve_path(raw_path, base_dir=base_dir)
            if path is not None:
                paths.append(path)
    first_path = _resolve_path(
        performance.get(
            "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_path"
        ),
        base_dir=base_dir,
    )
    if first_path is not None and first_path not in paths:
        paths.insert(0, first_path)
    return paths


def _packet_issue_candidate_count(path: Path) -> int:
    payload = _load_json_object(path, label="producer-state packet")
    try:
        return int(_packet_issue_summary(payload)[0])
    except (TypeError, ValueError):
        return 0


def _issue_candidate_hash(issue_experts: tuple[int, ...]) -> str:
    value = 0xCBF29CE484222325
    count = 0
    for expert_id in issue_experts:
        value ^= int(expert_id) & 0xFFFFFFFF
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        count += 1
    value ^= count & 0xFFFFFFFF
    value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{value:016x}"


def _packet_issue_summary(payload: dict[str, Any]) -> tuple[int, tuple[int, ...], str]:
    previous_raw = payload.get("previous_experts", [])
    if not isinstance(previous_raw, list):
        raise ValueError("producer-state previous_experts must be a list")
    if any(type(value) is not int for value in previous_raw):
        raise ValueError("producer-state previous_experts must contain ints")
    if any(int(value) < 0 for value in previous_raw):
        raise ValueError("producer-state previous_experts must be non-negative")
    previous = tuple(int(value) for value in previous_raw)
    topk = int(payload.get("transition_topk_count", 0) or 0)
    if topk < 0:
        raise ValueError("producer-state transition_topk_count must be non-negative")
    limit = len(previous) if topk == 0 else min(len(previous), topk)
    issue_experts = previous[:limit]
    issue_count = len(issue_experts)
    issue_hash = _issue_candidate_hash(issue_experts)
    self_described_keys = {
        "issue_candidate_count",
        "issue_candidate_hash",
        "issue_candidate_experts",
        "issue_candidate_first_expert",
        "issue_candidate_last_expert",
    }
    present_self_described_keys = {
        key for key in payload if str(key).startswith("issue_candidate_")
    }
    if present_self_described_keys:
        if present_self_described_keys != self_described_keys:
            raise ValueError("producer-state issue_candidate self-description is partial")
        raw_count = payload.get("issue_candidate_count")
        if type(raw_count) is not int or raw_count != issue_count:
            raise ValueError("producer-state issue_candidate_count mismatch")
        raw_hash = payload.get("issue_candidate_hash")
        if not isinstance(raw_hash, str) or raw_hash != issue_hash:
            raise ValueError("producer-state issue_candidate_hash mismatch")
        raw_experts = payload.get("issue_candidate_experts")
        if not isinstance(raw_experts, list):
            raise ValueError("producer-state issue_candidate_experts must be a list")
        if any(type(value) is not int for value in raw_experts):
            raise ValueError("producer-state issue_candidate_experts must be ints")
        if tuple(int(value) for value in raw_experts) != issue_experts:
            raise ValueError("producer-state issue_candidate_experts mismatch")
        expected_first = int(issue_experts[0]) if issue_experts else -1
        expected_last = int(issue_experts[-1]) if issue_experts else -1
        raw_first = payload.get("issue_candidate_first_expert")
        raw_last = payload.get("issue_candidate_last_expert")
        if type(raw_first) is not int or raw_first != expected_first:
            raise ValueError("producer-state issue_candidate_first_expert mismatch")
        if type(raw_last) is not int or raw_last != expected_last:
            raise ValueError("producer-state issue_candidate_last_expert mismatch")
    return issue_count, issue_experts, issue_hash


def _select_nonempty_issue_packet(paths: list[Path]) -> tuple[int, Path] | None:
    for index, path in enumerate(paths):
        if not path.exists():
            raise ValueError(f"producer-state packet export path missing: {path}")
        if _packet_issue_candidate_count(path) > 0:
            return index, path
    return None


def _validate_selected_packet_issue_contract(path: Path) -> tuple[int, tuple[int, ...], str]:
    payload = _load_json_object(path, label="selected producer-state packet")
    try:
        return _packet_issue_summary(payload)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "selected producer-state packet issue self-description is invalid"
        ) from exc


def _select_nonempty_issue_packet_from_summary(
    performance: dict[str, Any],
    *,
    paths: list[Path],
    base_dir: Path,
) -> tuple[int, Path] | None:
    prefix = "runtime_shadow_premap_payload_cache_producer_state_packet_export_"
    if f"{prefix}nonempty_issue_count" not in performance:
        return None
    try:
        nonempty_count = int(performance.get(f"{prefix}nonempty_issue_count") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("producer-state nonempty issue summary count is invalid") from exc
    try:
        scan_error_count = int(performance.get(f"{prefix}scan_error_count") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("producer-state packet export scan error count is invalid") from exc
    if scan_error_count > 0:
        raise ValueError(
            "producer-state packet export scan had errors; nonempty issue "
            "summary is incomplete"
        )
    if nonempty_count <= 0:
        return None
    try:
        selected_index = int(
            performance.get(f"{prefix}first_nonempty_issue_index")
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("producer-state first nonempty issue index is invalid") from exc
    if selected_index < 0:
        raise ValueError("producer-state first nonempty issue index is negative")
    selected_path = _resolve_path(
        performance.get(f"{prefix}first_nonempty_issue_path"),
        base_dir=base_dir,
    )
    if selected_path is None:
        raise ValueError("producer-state first nonempty issue path is missing")
    if selected_index < len(paths) and paths[selected_index] == selected_path:
        return selected_index, selected_path
    if selected_path in paths:
        return paths.index(selected_path), selected_path
    raise ValueError("producer-state first nonempty issue path is not exported")


def select_packet_json(
    *,
    performance_summary: Path | None,
    packet_json: Path | None,
    packet_index: int,
    prefer_nonempty_issue: bool = False,
    require_nonempty_issue: bool = False,
) -> tuple[Path, dict[str, Any] | None, list[Path], int, str]:
    if packet_json is not None:
        selection_mode = "explicit_packet_json"
        if (
            packet_json.exists()
            and (prefer_nonempty_issue or require_nonempty_issue)
        ):
            if _packet_issue_candidate_count(packet_json) > 0:
                selection_mode = "explicit_packet_json_nonempty_issue"
            elif require_nonempty_issue:
                raise ValueError(
                    "explicit producer-state packet does not contain a nonempty "
                    "issue prefix"
                )
        return packet_json, None, [packet_json], 0, selection_mode
    if performance_summary is None:
        raise ValueError("--performance-summary or --packet-json is required")
    performance = _load_json_object(performance_summary, label="performance summary")
    if not bool(
        performance.get(
            "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled",
            False,
        )
    ):
        raise ValueError("producer-state packet export is not enabled in summary")
    configured_count = int(
        performance.get(
            "runtime_shadow_premap_payload_cache_producer_state_packet_export_count",
            0,
        )
        or 0
    )
    if configured_count <= 0:
        raise ValueError("producer-state packet export count is zero in summary")
    paths = _packet_paths_from_performance(
        performance,
        base_dir=performance_summary.parent,
    )
    if not paths:
        raise ValueError(
            "performance summary does not contain producer-state packet export paths"
        )
    if prefer_nonempty_issue or require_nonempty_issue:
        selected = _select_nonempty_issue_packet_from_summary(
            performance,
            paths=paths,
            base_dir=performance_summary.parent,
        )
        selection_mode = "summary_first_nonempty_issue"
        if selected is None and (
            "runtime_shadow_premap_payload_cache_producer_state_packet_export_nonempty_issue_count"
            not in performance
        ):
            selected = _select_nonempty_issue_packet(paths)
            selection_mode = "first_nonempty_issue"
        if selected is not None:
            selected_index, selected_path = selected
            return (
                selected_path,
                performance,
                paths,
                selected_index,
                selection_mode,
            )
        if require_nonempty_issue:
            raise ValueError(
                "performance summary does not contain a nonempty producer-state "
                "issue packet"
            )
    if packet_index < 0 or packet_index >= len(paths):
        raise ValueError(
            f"--packet-index {packet_index} is out of range for {len(paths)} paths"
        )
    return paths[packet_index], performance, paths, packet_index, "packet_index"


def run_online_canary(args: argparse.Namespace) -> dict[str, Any]:
    (
        selected_packet,
        performance,
        paths,
        selected_packet_index,
        selection_mode,
    ) = select_packet_json(
        performance_summary=args.performance_summary,
        packet_json=args.packet_json,
        packet_index=int(args.packet_index),
        prefer_nonempty_issue=bool(getattr(args, "prefer_nonempty_issue", False)),
        require_nonempty_issue=bool(getattr(args, "require_nonempty_issue", False)),
    )
    if not selected_packet.exists():
        return {
            "ok": False,
            "passed": False,
            "failures": ["packet_json_missing"],
            "packet_json": str(selected_packet),
            "online_performance_summary": (
                None
                if args.performance_summary is None
                else str(args.performance_summary)
            ),
        }
    _validate_selected_packet_issue_contract(selected_packet)
    stub_runner = _load_stub_runner()
    payload = stub_runner.run_stub(
        argparse.Namespace(
            device=int(args.device),
            previous_count=0,
            current_count=0,
            transition_topk_count=0,
            current_offset=int(args.current_offset),
            packet_json=selected_packet,
            offload_arch=str(args.offload_arch),
            force_build=bool(args.force_build),
            hip_visible_devices=args.hip_visible_devices,
        )
    )
    payload.setdefault("passed", bool(payload.get("ok", False)))
    payload.setdefault("failures", [] if payload.get("ok", False) else ["stub_not_ok"])
    payload["online_export_source"] = (
        "runtime_shadow_premap_payload_cache_producer_state_packet_export"
    )
    payload["online_performance_summary"] = (
        None if args.performance_summary is None else str(args.performance_summary)
    )
    payload["online_packet_export_count"] = int(len(paths))
    payload["online_packet_export_paths"] = [str(path) for path in paths]
    payload["selected_packet_index"] = int(selected_packet_index)
    payload["selected_packet_json"] = str(selected_packet)
    payload["selected_packet_selection_mode"] = str(selection_mode)
    payload["payload_bytes"] = 0
    payload["issued_payload_count"] = 0
    payload["ready_credit"] = False
    payload["ready_before_demand_credit"] = False
    payload["real_ready_credit_granted"] = False
    payload["payload_transfer_enabled"] = False
    payload["live_payload_runtime_enabled"] = False
    payload["payload_transfer_runtime_enabled"] = False
    payload["payload_deref_allowed"] = False
    payload["payload_deref_runtime_allowed"] = False
    payload["kernel_arg_pass_allowed"] = False
    payload["full_fetch_runtime_allowed"] = False
    payload["live_runtime_instantiated"] = False
    payload["passed_to_kernel"] = False
    payload["changes_kernel_launch_args"] = False
    payload["uses_current_wna16_args"] = False
    payload["passes_current_wna16_args"] = False
    payload["measures_tpot"] = False
    payload["measures_vllm_latency"] = False
    if performance is not None:
        export_prefix = (
            "runtime_shadow_premap_payload_cache_producer_state_packet_export_"
        )
        payload["online_configured_export_enabled"] = bool(
            performance.get(
                f"{export_prefix}enabled",
                False,
            )
        )
        payload["online_configured_export_count"] = int(
            performance.get(
                f"{export_prefix}count",
                0,
            )
            or 0
        )
        for summary_key in (
            "nonempty_issue_count",
            "first_nonempty_issue_index",
            "first_nonempty_issue_path",
            "first_nonempty_issue_count",
            "first_nonempty_issue_hash",
            "scan_error_count",
        ):
            raw_key = f"{export_prefix}{summary_key}"
            if raw_key in performance:
                payload[f"online_packet_export_{summary_key}"] = performance[raw_key]
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--performance-summary", type=Path)
    parser.add_argument("--packet-json", type=Path)
    parser.add_argument("--packet-index", type=int, default=0)
    parser.add_argument(
        "--prefer-nonempty-issue",
        action="store_true",
        help="Select the first exported packet with a nonempty previous-expert issue prefix.",
    )
    parser.add_argument(
        "--require-nonempty-issue",
        action="store_true",
        help="Fail if no exported packet has a nonempty previous-expert issue prefix.",
    )
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--current-offset", type=int, default=0)
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT
        / "outputs"
        / "reports"
        / "premap_kernel_consumer"
        / "payload_cache_producer_state_online_canary.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload = run_online_canary(args)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        payload = {
            "ok": False,
            "passed": False,
            "failures": ["online_canary_error"],
            "online_canary_error": str(exc),
            "online_performance_summary": (
                None
                if args.performance_summary is None
                else str(args.performance_summary)
            ),
            "packet_json": None if args.packet_json is None else str(args.packet_json),
        }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
