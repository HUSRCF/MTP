#!/usr/bin/env python3
"""Build and run the readonly payload-cache producer transition-state stub."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for _path in (REPO_ROOT, SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    PremapPayloadCacheProducerTransitionStatePacket,
)

SRC = (
    REPO_ROOT
    / "microbench"
    / "premap_kernel_consumer"
    / "premap_payload_cache_producer_state_stub.hip"
)
ABI_HEADER = (
    REPO_ROOT
    / "microbench"
    / "premap_kernel_consumer"
    / "premap_typed_consumer_abi_v1.h"
)
BUILD_DIR = REPO_ROOT / "microbench" / "premap_kernel_consumer" / "build"


def _build_key(offload_arch: str) -> str:
    latest = "|".join(
        [
            offload_arch,
            SRC.read_text(encoding="utf-8"),
            ABI_HEADER.read_text(encoding="utf-8"),
        ]
    )
    return hashlib.sha256(latest.encode("utf-8")).hexdigest()[:12]


def build_command(*, offload_arch: str, output: Path) -> list[str]:
    return [
        "hipcc",
        "-O3",
        "--std=c++17",
        f"--offload-arch={offload_arch}",
        str(SRC),
        "-o",
        str(output),
    ]


MAX_NATIVE_CANARY_COUNT = 65536


def run_cmd(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 and not allow_failure:
        msg = (
            "command failed with exit code "
            f"{result.returncode}: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        raise RuntimeError(msg)
    return result


def _validate_count(value: int, name: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    if parsed > MAX_NATIVE_CANARY_COUNT:
        raise ValueError(
            f"{name} exceeds native canary safety bound {MAX_NATIVE_CANARY_COUNT}"
        )
    return parsed


def _experts_arg(values: tuple[int, ...]) -> str:
    return ",".join(str(int(value)) for value in values)


def _packet_state_hash_u64(packet: PremapPayloadCacheProducerTransitionStatePacket) -> int:
    return int(str(packet.state_hash)[:16], 16) & 0xFFFFFFFFFFFFFFFF


def _load_packet_json(path: Path) -> PremapPayloadCacheProducerTransitionStatePacket:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"producer transition-state packet JSON must be an object: {path}")
    packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=int(payload.get("layer_id", 0)),
        previous_experts=tuple(int(value) for value in payload.get("previous_experts", [])),
        current_experts=tuple(int(value) for value in payload.get("current_experts", [])),
        state_owner=str(payload.get("state_owner", "producer")),
        issue_source=str(
            payload.get("issue_source", "prelaunch_observed_transition_premap_shadow")
        ),
        transition_summary_mode=str(payload.get("transition_summary_mode", "matrix_topk")),
        transition_topk_count=int(payload.get("transition_topk_count", 0)),
        max_num_experts=(
            None
            if payload.get("max_num_experts") is None
            else int(payload["max_num_experts"])
        ),
        schema_name=str(payload.get("schema_name", "")),
        schema_hash=str(payload.get("schema_hash", "")),
        payload_bytes=int(payload.get("payload_bytes", 0)),
        ready_credit=bool(payload.get("ready_credit", False)),
        passed_to_kernel=bool(payload.get("passed_to_kernel", False)),
        changes_kernel_launch_args=bool(payload.get("changes_kernel_launch_args", False)),
    )
    if not packet.ready:
        raise ValueError(f"producer transition-state packet is not ready: {path}")
    return packet


def _packet_json_error_payload(path: Path, exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "passed": False,
        "failures": ["packet_json_error"],
        "packet_json": str(path),
        "packet_json_error": str(exc),
    }


def build(*, offload_arch: str, force: bool) -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    binary = BUILD_DIR / f"premap_payload_cache_producer_state_stub_{_build_key(offload_arch)}"
    latest_source_mtime = max(SRC.stat().st_mtime, ABI_HEADER.stat().st_mtime)
    if binary.exists() and not force and binary.stat().st_mtime >= latest_source_mtime:
        return binary
    result = run_cmd(build_command(offload_arch=offload_arch, output=binary))
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    return binary


def run_stub(args: argparse.Namespace) -> dict[str, Any]:
    binary = build(offload_arch=args.offload_arch, force=args.force_build)
    packet_json = getattr(args, "packet_json", None)
    try:
        packet = _load_packet_json(packet_json) if packet_json is not None else None
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        payload = _packet_json_error_payload(packet_json, exc)
        payload["native_returncode"] = None
        payload["binary"] = str(binary)
        payload["source"] = str(SRC)
        payload["abi_header"] = str(ABI_HEADER)
        payload["offload_arch"] = str(args.offload_arch)
        return payload
    previous_experts: tuple[int, ...] | None = None
    current_experts: tuple[int, ...] | None = None
    layer_id = _validate_count(getattr(args, "layer_id", 0), "layer-id")
    state_hash_u64 = int(getattr(args, "state_hash", 0x8A45D2C91FE01237))
    if packet is None:
        previous_count = _validate_count(args.previous_count, "previous-count")
        current_count = _validate_count(args.current_count, "current-count")
        transition_topk_count = _validate_count(
            args.transition_topk_count,
            "transition-topk-count",
        )
    else:
        previous_experts = packet.native_previous_experts_i32
        current_experts = packet.native_current_experts_i32
        previous_count = len(previous_experts)
        current_count = len(current_experts)
        transition_topk_count = int(packet.transition_topk_count)
        layer_id = _validate_count(packet.layer_id, "layer-id")
        state_hash_u64 = _packet_state_hash_u64(packet)
    current_offset = _validate_count(args.current_offset, "current-offset")
    cmd = [
        str(binary),
        "--device",
        str(args.device),
        "--layer-id",
        str(layer_id),
        "--state-hash",
        str(state_hash_u64),
        "--previous-count",
        str(previous_count),
        "--current-count",
        str(current_count),
        "--transition-topk-count",
        str(transition_topk_count),
        "--current-offset",
        str(current_offset),
    ]
    if previous_experts is not None:
        cmd.extend(["--previous-experts", _experts_arg(previous_experts)])
    if current_experts is not None:
        cmd.extend(["--current-experts", _experts_arg(current_experts)])
    env = os.environ.copy()
    if args.hip_visible_devices is not None:
        env["HIP_VISIBLE_DEVICES"] = str(args.hip_visible_devices)
    result = run_cmd(cmd, env=env, allow_failure=True)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        payload = {
            "ok": False,
            "passed": False,
            "failures": ["native_json_parse_error"],
            "native_json_parse_error": str(exc),
            "native_stdout": result.stdout,
        }
    if not isinstance(payload, dict):
        payload = {
            "ok": False,
            "passed": False,
            "failures": ["native_json_root_type_error"],
            "native_json_root_type": type(payload).__name__,
            "native_stdout": result.stdout,
        }
    payload["native_returncode"] = int(result.returncode)
    payload["binary"] = str(binary)
    payload["source"] = str(SRC)
    payload["abi_header"] = str(ABI_HEADER)
    payload["offload_arch"] = str(args.offload_arch)
    payload["requested_previous_count"] = int(previous_count)
    payload["requested_current_count"] = int(current_count)
    payload["requested_transition_topk_count"] = int(transition_topk_count)
    payload["requested_current_offset"] = int(current_offset)
    payload["requested_layer_id"] = int(layer_id)
    payload["requested_state_hash"] = f"{int(state_hash_u64):016x}"
    if packet is not None:
        payload["packet_json"] = str(packet_json)
        payload["packet_ready"] = bool(packet.ready)
        payload["packet_state_hash"] = str(packet.state_hash)
        payload["packet_state_hash_u64"] = f"{_packet_state_hash_u64(packet):016x}"
        payload["packet_layer_id"] = int(packet.layer_id)
        payload["input_source"] = "semantic_packet_json"
    else:
        payload["input_source"] = "synthetic"
    if result.stderr:
        payload["stderr"] = result.stderr
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--layer-id", type=int, default=0)
    parser.add_argument("--state-hash", type=int, default=0x8A45D2C91FE01237)
    parser.add_argument("--previous-count", type=int, default=8)
    parser.add_argument("--current-count", type=int, default=8)
    parser.add_argument("--transition-topk-count", type=int, default=8)
    parser.add_argument("--current-offset", type=int, default=4)
    parser.add_argument("--packet-json", type=Path)
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
        / "payload_cache_producer_state_stub.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_stub(args)
    payload.setdefault("passed", bool(payload.get("ok", False)))
    payload.setdefault("failures", [] if payload.get("ok", False) else ["stub_not_ok"])
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
