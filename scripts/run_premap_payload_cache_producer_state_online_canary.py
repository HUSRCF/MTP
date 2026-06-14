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
    previous = payload.get("previous_experts", [])
    if not isinstance(previous, list):
        return 0
    try:
        previous_count = len(previous)
        topk = int(payload.get("transition_topk_count", 0) or 0)
    except (TypeError, ValueError):
        return 0
    if previous_count <= 0:
        return 0
    if topk <= 0:
        return previous_count
    return min(previous_count, topk)


def _select_nonempty_issue_packet(paths: list[Path]) -> tuple[int, Path] | None:
    for index, path in enumerate(paths):
        if not path.exists():
            raise ValueError(f"producer-state packet export path missing: {path}")
        if _packet_issue_candidate_count(path) > 0:
            return index, path
    return None


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
        selected = _select_nonempty_issue_packet(paths)
        if selected is not None:
            selected_index, selected_path = selected
            return (
                selected_path,
                performance,
                paths,
                selected_index,
                "first_nonempty_issue",
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
    if performance is not None:
        payload["online_configured_export_enabled"] = bool(
            performance.get(
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled",
                False,
            )
        )
        payload["online_configured_export_count"] = int(
            performance.get(
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count",
                0,
            )
            or 0
        )
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
