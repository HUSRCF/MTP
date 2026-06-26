#!/usr/bin/env python3
"""Build and run the native stream producer-state canary.

This canary validates the next boundary after the single-packet producer-state
stub: previous expert state remains in native/GPU-side storage across decode
steps, and issue candidates are generated from that persistent state without
payload movement or current WNA16 kernel-argument handoff.
"""

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
SRC = (
    REPO_ROOT
    / "microbench"
    / "premap_kernel_consumer"
    / "premap_payload_cache_producer_state_stream_stub.hip"
)
ABI_HEADER = (
    REPO_ROOT
    / "microbench"
    / "premap_kernel_consumer"
    / "premap_typed_consumer_abi_v1.h"
)
BUILD_DIR = REPO_ROOT / "microbench" / "premap_kernel_consumer" / "build"
MAX_NATIVE_STREAM_COUNT = 65536


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


def _validate_count(value: int, name: str, *, allow_zero: bool = False) -> int:
    parsed = int(value)
    if parsed < 0 or (parsed == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {qualifier}")
    if parsed > MAX_NATIVE_STREAM_COUNT:
        raise ValueError(
            f"{name} exceeds native stream canary safety bound "
            f"{MAX_NATIVE_STREAM_COUNT}"
        )
    return parsed


def build(*, offload_arch: str, force: bool) -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    binary = BUILD_DIR / (
        f"premap_payload_cache_producer_state_stream_stub_{_build_key(offload_arch)}"
    )
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
    steps = _validate_count(args.steps, "steps")
    layers = _validate_count(args.layers, "layers")
    experts_per_layer = _validate_count(args.experts_per_layer, "experts-per-layer")
    transition_topk_count = _validate_count(
        args.transition_topk_count,
        "transition-topk-count",
        allow_zero=True,
    )
    max_num_experts = _validate_count(args.max_num_experts, "max-num-experts")
    step_shift = _validate_count(args.step_shift, "step-shift", allow_zero=True)
    layer_stride = _validate_count(args.layer_stride, "layer-stride", allow_zero=True)
    cmd = [
        str(binary),
        "--device",
        str(args.device),
        "--steps",
        str(steps),
        "--layers",
        str(layers),
        "--experts-per-layer",
        str(experts_per_layer),
        "--transition-topk-count",
        str(transition_topk_count),
        "--max-num-experts",
        str(max_num_experts),
        "--step-shift",
        str(step_shift),
        "--layer-stride",
        str(layer_stride),
        "--state-hash-base",
        str(int(args.state_hash_base)),
    ]
    if args.disable_vectorized_copy:
        cmd.append("--disable-vectorized-copy")
    if args.graph_replay:
        cmd.append("--graph-replay")
    packet_stream_bin = getattr(args, "packet_stream_bin", None)
    if packet_stream_bin is not None:
        cmd.extend(["--packet-stream-bin", str(packet_stream_bin)])

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
    payload["requested_steps"] = int(steps)
    payload["requested_layers"] = int(layers)
    payload["requested_experts_per_layer"] = int(experts_per_layer)
    payload["requested_transition_topk_count"] = int(transition_topk_count)
    payload["requested_disable_vectorized_copy"] = bool(args.disable_vectorized_copy)
    payload["requested_graph_replay"] = bool(args.graph_replay)
    payload["requested_packet_stream_bin"] = (
        None if args.packet_stream_bin is None else str(args.packet_stream_bin)
    )
    if result.returncode != 0:
        payload["ok"] = False
        payload["passed"] = False
        failures = payload.get("failures")
        if not isinstance(failures, list):
            failures = []
        if "native_returncode_nonzero" not in failures:
            failures.append("native_returncode_nonzero")
        payload["failures"] = failures
    if result.stderr:
        payload["stderr"] = result.stderr
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--layers", type=int, default=40)
    parser.add_argument("--experts-per-layer", type=int, default=8)
    parser.add_argument("--transition-topk-count", type=int, default=8)
    parser.add_argument("--max-num-experts", type=int, default=256)
    parser.add_argument("--step-shift", type=int, default=1)
    parser.add_argument("--layer-stride", type=int, default=17)
    parser.add_argument("--state-hash-base", type=int, default=0x8A45D2C91FE01237)
    parser.add_argument("--disable-vectorized-copy", action="store_true")
    parser.add_argument("--graph-replay", action="store_true")
    parser.add_argument("--packet-stream-bin", type=Path)
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
        / "payload_cache_producer_state_stream_stub.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_stub(args)
    payload.setdefault("passed", bool(payload.get("ok", False)))
    payload.setdefault("failures", [] if payload.get("ok", False) else ["stub_not_ok"])
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
