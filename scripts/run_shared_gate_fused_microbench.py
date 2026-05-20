#!/usr/bin/env python3
"""Microbenchmark a fused shared-expert output gate for decode.

The Qwen3.5/Qwen3.6 MoE shared branch computes:

    out = sigmoid(shared_expert_gate(hidden_states)) * shared_expert(hidden_states)

For small decode batches this can be launch/dispatch dominated.  This helper
tests a narrow Triton fusion of the scalar gate projection, sigmoid, and output
multiply. It is diagnostic only and does not patch vLLM runtime code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
from typing import Any

import torch

from vllm.triton_utils import tl, triton


@triton.jit
def _shared_gate_fused_kernel(
    hidden_ptr,
    gate_weight_ptr,
    out_ptr,
    dst_ptr,
    n_tokens: tl.constexpr,
    hidden_size: tl.constexpr,
    stride_hidden_token: tl.constexpr,
    stride_hidden_dim: tl.constexpr,
    stride_out_token: tl.constexpr,
    stride_out_dim: tl.constexpr,
    stride_dst_token: tl.constexpr,
    stride_dst_dim: tl.constexpr,
    BLOCK_H: tl.constexpr,
):
    token = tl.program_id(0)
    offs = tl.arange(0, BLOCK_H)
    mask = offs < hidden_size

    hidden = tl.load(
        hidden_ptr + token * stride_hidden_token + offs * stride_hidden_dim,
        mask=mask,
        other=0.0,
    ).to(tl.float32)
    gate_weight = tl.load(gate_weight_ptr + offs, mask=mask, other=0.0).to(tl.float32)
    gate = tl.sum(hidden * gate_weight, axis=0)
    gate = 1.0 / (1.0 + tl.exp(-gate))

    out = tl.load(
        out_ptr + token * stride_out_token + offs * stride_out_dim,
        mask=mask,
        other=0.0,
    )
    scaled = out.to(tl.float32) * gate
    tl.store(
        dst_ptr + token * stride_dst_token + offs * stride_dst_dim,
        scaled,
        mask=mask,
    )


def _event_time_us(fn, *, repeats: int, warmup: int) -> tuple[float, list[float]]:
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()

    samples: list[float] = []
    for _ in range(repeats):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        fn()
        end.record()
        end.synchronize()
        samples.append(float(start.elapsed_time(end)) * 1000.0)
    return statistics.median(samples), samples


def _bench_variant(
    *,
    batch: int,
    hidden_size: int,
    num_warps: int,
    num_stages: int,
    dtype: torch.dtype,
    repeats: int,
    warmup: int,
) -> dict[str, Any]:
    device = torch.device("cuda")
    hidden = torch.randn((batch, hidden_size), device=device, dtype=dtype)
    gate_weight = torch.randn((hidden_size,), device=device, dtype=dtype)
    out = torch.randn((batch, hidden_size), device=device, dtype=dtype)
    baseline_dst = torch.empty_like(out)
    fused_dst = torch.empty_like(out)

    def baseline() -> None:
        gate = torch.sigmoid(hidden @ gate_weight).unsqueeze(-1)
        torch.mul(out, gate, out=baseline_dst)

    block_h = triton.next_power_of_2(hidden_size)

    def fused() -> None:
        _shared_gate_fused_kernel[(batch,)](
            hidden,
            gate_weight,
            out,
            fused_dst,
            batch,
            hidden_size,
            hidden.stride(0),
            hidden.stride(1),
            out.stride(0),
            out.stride(1),
            fused_dst.stride(0),
            fused_dst.stride(1),
            BLOCK_H=block_h,
            num_warps=num_warps,
            num_stages=num_stages,
        )

    baseline()
    fused()
    torch.cuda.synchronize()
    max_abs_diff = float((baseline_dst.float() - fused_dst.float()).abs().max().item())

    baseline_median, baseline_samples = _event_time_us(
        baseline, repeats=repeats, warmup=warmup
    )
    fused_median, fused_samples = _event_time_us(fused, repeats=repeats, warmup=warmup)

    return {
        "batch": batch,
        "hidden_size": hidden_size,
        "num_warps": num_warps,
        "num_stages": num_stages,
        "dtype": str(dtype).replace("torch.", ""),
        "block_h": block_h,
        "baseline_median_us": baseline_median,
        "baseline_mean_us": statistics.fmean(baseline_samples),
        "baseline_p90_us": sorted(baseline_samples)[
            int(0.9 * (len(baseline_samples) - 1))
        ],
        "fused_median_us": fused_median,
        "fused_mean_us": statistics.fmean(fused_samples),
        "fused_p90_us": sorted(fused_samples)[int(0.9 * (len(fused_samples) - 1))],
        "speedup_median": baseline_median / fused_median if fused_median > 0 else None,
        "max_abs_diff": max_abs_diff,
        "baseline_samples_us": baseline_samples,
        "fused_samples_us": fused_samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--batches", type=int, nargs="+", default=[1, 2, 4, 8, 16])
    parser.add_argument("--hidden-size", type=int, default=2048)
    parser.add_argument("--num-warps", type=int, nargs="+", default=[4, 8])
    parser.add_argument("--num-stages", type=int, nargs="+", default=[3, 4])
    parser.add_argument("--repeats", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=10)
    args = parser.parse_args()

    torch.cuda.set_device(args.gpu)
    rows: list[dict[str, Any]] = []
    for batch in args.batches:
        for num_warps in args.num_warps:
            for num_stages in args.num_stages:
                row = _bench_variant(
                    batch=batch,
                    hidden_size=args.hidden_size,
                    num_warps=num_warps,
                    num_stages=num_stages,
                    dtype=torch.bfloat16,
                    repeats=args.repeats,
                    warmup=args.warmup,
                )
                rows.append(row)
                print(
                    json.dumps(
                        {
                            key: value
                            for key, value in row.items()
                            if not key.endswith("_samples_us")
                        }
                    )
                )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
