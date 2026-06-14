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
    previous_count = _validate_count(args.previous_count, "previous-count")
    current_count = _validate_count(args.current_count, "current-count")
    transition_topk_count = _validate_count(
        args.transition_topk_count,
        "transition-topk-count",
    )
    current_offset = _validate_count(args.current_offset, "current-offset")
    cmd = [
        str(binary),
        "--device",
        str(args.device),
        "--previous-count",
        str(previous_count),
        "--current-count",
        str(current_count),
        "--transition-topk-count",
        str(transition_topk_count),
        "--current-offset",
        str(current_offset),
    ]
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
    if result.stderr:
        payload["stderr"] = result.stderr
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--previous-count", type=int, default=8)
    parser.add_argument("--current-count", type=int, default=8)
    parser.add_argument("--transition-topk-count", type=int, default=8)
    parser.add_argument("--current-offset", type=int, default=4)
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
