#!/usr/bin/env python3
"""Run a command while sampling rocm-smi until the command exits."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sample_rocm_smi import _card_row, _sample_once


def run_with_sampling(
    *,
    command: list[str],
    gpu: int,
    output: Path,
    interval_s: float,
) -> int:
    if not command:
        raise ValueError("command must not be empty")
    output.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(command)
    start = time.monotonic()
    sample_count = 0
    try:
        with output.open("w", encoding="utf-8") as handle:
            while True:
                now = time.monotonic()
                if proc.poll() is not None:
                    break
                try:
                    raw = _sample_once()
                    row = _card_row(raw, gpu)
                    row["ok"] = True
                except Exception as exc:  # pragma: no cover - depends on local ROCm state
                    row = {"gpu": gpu, "ok": False, "error": repr(exc)}
                row["utc"] = datetime.now(timezone.utc).isoformat()
                row["elapsed_s"] = now - start
                row["sample_index"] = sample_count
                handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
                sample_count += 1
                time.sleep(interval_s)
        return int(proc.wait())
    except BaseException:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval-s", type=float, default=1.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("provide a command after --")
    if args.interval_s <= 0:
        raise SystemExit("--interval-s must be positive")
    raise SystemExit(
        run_with_sampling(
            command=command,
            gpu=args.gpu,
            output=args.output,
            interval_s=args.interval_s,
        )
    )


if __name__ == "__main__":
    main()
