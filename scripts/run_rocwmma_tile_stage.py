#!/usr/bin/env python3
"""Build and run rocWMMA global-vs-LDS tile staging smoke."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "microbench" / "rocwmma_smoke" / "rocwmma_tile_stage.hip"
BUILD_DIR = REPO_ROOT / "microbench" / "rocwmma_smoke" / "build"
BIN = BUILD_DIR / "rocwmma_tile_stage"
DEFAULT_MODES = ["global_baseline", "lds_hit", "lds_miss_overwrite"]


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
    parser.add_argument("--mode", action="append", default=None, choices=DEFAULT_MODES)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--iters", type=int, default=200)
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "rocwmma_smoke" / "rocwmma_tile_stage.json",
    )
    return parser.parse_args()


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_device: dict[int, dict[str, dict[str, Any]]] = {}
    for row in results:
        by_device.setdefault(int(row["device"]), {})[str(row["mode"])] = row

    comparisons: list[dict[str, Any]] = []
    for device, rows in sorted(by_device.items()):
        baseline = rows.get("global_baseline")
        if not baseline:
            continue
        base_ms = float(baseline["wall_ms_mean"])
        for mode in ("lds_hit", "lds_miss_overwrite"):
            row = rows.get(mode)
            if not row:
                continue
            mode_ms = float(row["wall_ms_mean"])
            comparisons.append(
                {
                    "device": device,
                    "mode": mode,
                    "delta_vs_global_ms": mode_ms - base_ms,
                    "speedup_vs_global": base_ms / mode_ms if mode_ms > 0 else None,
                }
            )
    return {"comparisons": comparisons}


def main() -> None:
    args = parse_args()
    devices = sorted(set(args.device or [0]))
    modes = args.mode or DEFAULT_MODES
    build(force=args.force_build, offload_arch=args.offload_arch)
    results: list[dict[str, Any]] = []
    for device in devices:
        for mode in modes:
            result = run(
                [
                    str(BIN),
                    "--device",
                    str(device),
                    "--mode",
                    mode,
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
            "modes": modes,
            "warmup": args.warmup,
            "iters": args.iters,
            "offload_arch": args.offload_arch,
            "binary": str(BIN),
            "source": str(SRC),
        },
        "results": results,
        "summary": summarize(results),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
