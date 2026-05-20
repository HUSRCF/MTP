#!/usr/bin/env python3
"""Sample rocm-smi GPU utilization into JSONL.

This is intended as a low-intrusion sidecar for AWQ/vLLM decode runs.  It does
not import torch or touch the model process.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "N/A":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _sample_once() -> dict[str, Any]:
    proc = subprocess.run(
        [
            "rocm-smi",
            "--showuse",
            "--showmemuse",
            "--showpower",
            "--json",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(proc.stdout)


def _card_row(raw: dict[str, Any], gpu: int) -> dict[str, Any]:
    card = raw.get(f"card{gpu}", {})
    return {
        "gpu": gpu,
        "gpu_use_pct": _parse_number(card.get("GPU use (%)")),
        "vram_allocated_pct": _parse_number(card.get("GPU Memory Allocated (VRAM%)")),
        "mem_rw_activity_pct": _parse_number(
            card.get("GPU Memory Read/Write Activity (%)")
        ),
        "avg_graphics_power_w": _parse_number(
            card.get("Average Graphics Package Power (W)")
        ),
        "raw": card,
    }


def sample_to_jsonl(
    *,
    gpu: int,
    output: Path,
    interval_s: float,
    duration_s: float | None,
    max_samples: int | None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    count = 0
    with output.open("w", encoding="utf-8") as handle:
        while True:
            now = time.monotonic()
            if duration_s is not None and now - start >= duration_s:
                break
            if max_samples is not None and count >= max_samples:
                break
            try:
                raw = _sample_once()
                row = _card_row(raw, gpu)
                row["ok"] = True
            except Exception as exc:  # pragma: no cover - depends on local ROCm state
                row = {
                    "gpu": gpu,
                    "ok": False,
                    "error": repr(exc),
                }
            row["utc"] = datetime.now(timezone.utc).isoformat()
            row["elapsed_s"] = now - start
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            count += 1
            time.sleep(interval_s)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval-s", type=float, default=1.0)
    parser.add_argument("--duration-s", type=float)
    parser.add_argument("--max-samples", type=int)
    args = parser.parse_args()
    if args.duration_s is None and args.max_samples is None:
        raise SystemExit("provide --duration-s or --max-samples")
    if args.interval_s <= 0:
        raise SystemExit("--interval-s must be positive")
    sample_to_jsonl(
        gpu=args.gpu,
        output=args.output,
        interval_s=args.interval_s,
        duration_s=args.duration_s,
        max_samples=args.max_samples,
    )


if __name__ == "__main__":
    main()

