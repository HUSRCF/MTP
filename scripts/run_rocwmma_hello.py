#!/usr/bin/env python3
"""Build and run the minimal rocWMMA hello-world smoke."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "microbench" / "rocwmma_smoke" / "rocwmma_hello.hip"
BUILD_DIR = REPO_ROOT / "microbench" / "rocwmma_smoke" / "build"
BIN = BUILD_DIR / "rocwmma_hello"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def build(*, force: bool = False, offload_arch: str = "gfx1100") -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if BIN.exists() and not force and BIN.stat().st_mtime >= SRC.stat().st_mtime:
        return
    cmd = [
        "hipcc",
        "-O3",
        "--std=c++17",
        f"--offload-arch={offload_arch}",
        str(SRC),
        "-o",
        str(BIN),
    ]
    result = run(cmd)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, action="append", default=None)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iters", type=int, default=50)
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "rocwmma_smoke" / "rocwmma_hello.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    devices = sorted(set(args.device or [0]))
    build(force=args.force_build, offload_arch=args.offload_arch)
    results: list[dict[str, Any]] = []
    for device in devices:
        result = run(
            [
                str(BIN),
                "--device",
                str(device),
                "--warmup",
                str(args.warmup),
                "--iters",
                str(args.iters),
            ]
        )
        payload = json.loads(result.stdout)
        if result.stderr:
            payload["stderr"] = result.stderr
        results.append(payload)
    report = {
        "ok": all(bool(row.get("ok")) for row in results),
        "config": {
            "devices": devices,
            "warmup": args.warmup,
            "iters": args.iters,
            "offload_arch": args.offload_arch,
            "binary": str(BIN),
            "source": str(SRC),
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
