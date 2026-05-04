#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Microbenchmark CPU->GPU transfer cost for expert-sized payloads."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/expert_transfer_bench.json"),
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument("--batch-experts", default="1,2,4,8,16,32")
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=80)
    parser.add_argument("--include-pageable", action="store_true", default=True)
    parser.add_argument("--no-pageable", dest="include_pageable", action="store_false")
    parser.add_argument("--include-pinned", action="store_true", default=True)
    parser.add_argument("--no-pinned", dest="include_pinned", action="store_false")
    parser.add_argument("--include-gpu-to-cpu", action="store_true")
    return parser.parse_args()


def _parse_int_list(value: str) -> list[int]:
    return [int(part.strip()) for part in str(value).split(",") if part.strip()]


def _resolve_device(name: str) -> torch.device:
    if name.startswith("cuda") and not torch.cuda.is_available():
        msg = f"Requested {name}, but torch.cuda.is_available() is false."
        raise RuntimeError(msg)
    return torch.device(name)


def main() -> None:
    args = parse_args()
    device = _resolve_device(args.device)
    batch_experts = _parse_int_list(args.batch_experts)
    if not batch_experts:
        msg = "--batch-experts cannot be empty."
        raise ValueError(msg)

    rows = []
    for pinned in [False, True]:
        if pinned and not args.include_pinned:
            continue
        if not pinned and not args.include_pageable:
            continue
        for experts in batch_experts:
            total_bytes = int(args.expert_bytes) * int(experts)
            rows.append(
                _bench_h2d(
                    total_bytes=total_bytes,
                    expert_bytes=int(args.expert_bytes),
                    experts=int(experts),
                    pinned=pinned,
                    device=device,
                    warmup=int(args.warmup),
                    repeats=int(args.repeats),
                )
            )
            if args.include_gpu_to_cpu:
                rows.append(
                    _bench_d2h(
                        total_bytes=total_bytes,
                        expert_bytes=int(args.expert_bytes),
                        experts=int(experts),
                        pinned=pinned,
                        device=device,
                        warmup=int(args.warmup),
                        repeats=int(args.repeats),
                    )
                )

    payload = {
        "ok": True,
        "device": str(device),
        "torch_version": str(torch.__version__),
        "device_name": torch.cuda.get_device_name(device) if device.type == "cuda" else "cpu",
        "expert_bytes": int(args.expert_bytes),
        "batch_experts": batch_experts,
        "warmup": int(args.warmup),
        "repeats": int(args.repeats),
        "rows": rows,
        "recommendation": _recommend_bandwidth(rows),
        "notes": {
            "h2d": "CPU->GPU transfer, closest to expert offload load into VRAM.",
            "payload": "uint8 contiguous payload; it measures transfer envelope, not dequant/materialization.",
            "use_for_stall_proxy": (
                "Use conservative_h2d_gbps as --bandwidth-gbps in event/ready simulators."
            ),
        },
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def _bench_h2d(
    *,
    total_bytes: int,
    expert_bytes: int,
    experts: int,
    pinned: bool,
    device: torch.device,
    warmup: int,
    repeats: int,
) -> dict[str, float | int | str | bool]:
    src = _make_cpu_buffer(total_bytes, pinned=pinned)
    dst = torch.empty(total_bytes, dtype=torch.uint8, device=device)
    torch.cuda.synchronize(device)
    for _ in range(max(0, warmup)):
        dst.copy_(src, non_blocking=pinned)
    torch.cuda.synchronize(device)
    times_ms = []
    for _ in range(max(1, repeats)):
        start = time.perf_counter()
        dst.copy_(src, non_blocking=pinned)
        torch.cuda.synchronize(device)
        times_ms.append((time.perf_counter() - start) * 1000.0)
    return _summarize_times(
        times_ms,
        direction="h2d",
        pinned=pinned,
        total_bytes=total_bytes,
        expert_bytes=expert_bytes,
        experts=experts,
    )


def _bench_d2h(
    *,
    total_bytes: int,
    expert_bytes: int,
    experts: int,
    pinned: bool,
    device: torch.device,
    warmup: int,
    repeats: int,
) -> dict[str, float | int | str | bool]:
    src = torch.empty(total_bytes, dtype=torch.uint8, device=device)
    dst = _make_cpu_buffer(total_bytes, pinned=pinned)
    torch.cuda.synchronize(device)
    for _ in range(max(0, warmup)):
        dst.copy_(src, non_blocking=pinned)
    torch.cuda.synchronize(device)
    times_ms = []
    for _ in range(max(1, repeats)):
        start = time.perf_counter()
        dst.copy_(src, non_blocking=pinned)
        torch.cuda.synchronize(device)
        times_ms.append((time.perf_counter() - start) * 1000.0)
    return _summarize_times(
        times_ms,
        direction="d2h",
        pinned=pinned,
        total_bytes=total_bytes,
        expert_bytes=expert_bytes,
        experts=experts,
    )


def _make_cpu_buffer(total_bytes: int, *, pinned: bool) -> torch.Tensor:
    try:
        return torch.empty(total_bytes, dtype=torch.uint8, pin_memory=pinned)
    except RuntimeError as exc:
        if pinned:
            print(f"[warn] pinned allocation failed; falling back to pageable: {exc}")
            return torch.empty(total_bytes, dtype=torch.uint8)
        raise


def _summarize_times(
    times_ms: list[float],
    *,
    direction: str,
    pinned: bool,
    total_bytes: int,
    expert_bytes: int,
    experts: int,
) -> dict[str, float | int | str | bool]:
    sorted_times = sorted(times_ms)
    p50 = _quantile(sorted_times, 0.50)
    p90 = _quantile(sorted_times, 0.90)
    p95 = _quantile(sorted_times, 0.95)
    mean = statistics.fmean(sorted_times)
    return {
        "direction": direction,
        "pinned": bool(pinned),
        "experts": int(experts),
        "expert_bytes": int(expert_bytes),
        "total_bytes": int(total_bytes),
        "mean_ms": float(mean),
        "p50_ms": float(p50),
        "p90_ms": float(p90),
        "p95_ms": float(p95),
        "min_ms": float(min(sorted_times)),
        "max_ms": float(max(sorted_times)),
        "mean_gbps": _gbps(total_bytes, mean),
        "p50_gbps": _gbps(total_bytes, p50),
        "p90_gbps": _gbps(total_bytes, p90),
        "p95_gbps": _gbps(total_bytes, p95),
    }


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = (len(sorted_values) - 1) * float(q)
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = pos - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def _gbps(total_bytes: int, ms: float) -> float:
    if ms <= 0.0:
        return 0.0
    return float(total_bytes) / (float(ms) / 1000.0) / 1_000_000_000.0


def _recommend_bandwidth(rows: list[dict[str, float | int | str | bool]]) -> dict[str, float]:
    h2d = [row for row in rows if row["direction"] == "h2d"]
    if not h2d:
        return {}
    pinned_rows = [row for row in h2d if bool(row["pinned"])]
    source = pinned_rows or h2d
    # Use p95 latency bandwidth to avoid optimistic stall-proxy calibration.
    conservative = min(float(row["p95_gbps"]) for row in source)
    median_large = max(
        (float(row["p50_gbps"]) for row in source if int(row["experts"]) >= 8),
        default=max(float(row["p50_gbps"]) for row in source),
    )
    return {
        "conservative_h2d_gbps": conservative,
        "large_batch_p50_h2d_gbps": median_large,
    }


if __name__ == "__main__":
    main()
