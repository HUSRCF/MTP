#!/usr/bin/env python3
"""Microbenchmark vLLM's GDN packed recurrent decode Triton kernel.

This is a diagnostic/autotune helper.  It does not patch vLLM runtime code.
The goal is to test whether simple launch-meta variants beat vLLM's default
packed decode settings for the Qwen3.5/Qwen3.6 GDN shape.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
from typing import Any

import torch

from vllm.model_executor.layers.fla.ops.fused_recurrent import (
    fused_recurrent_gated_delta_rule_packed_decode_kernel,
)
from vllm.triton_utils import triton


def _bench_variant(
    *,
    batch: int,
    h: int,
    hv: int,
    k: int,
    v: int,
    bv: int,
    num_warps: int,
    num_stages: int,
    dtype: torch.dtype,
    state_dtype: torch.dtype,
    repeats: int,
    warmup: int,
) -> dict[str, Any]:
    device = torch.device("cuda")
    qkv_dim = 2 * h * k + hv * v
    mixed_qkv = torch.randn((batch, qkv_dim), device=device, dtype=dtype)
    a = torch.randn((batch, hv), device=device, dtype=dtype)
    b = torch.randn((batch, hv), device=device, dtype=dtype)
    a_log = torch.randn((hv,), device=device, dtype=torch.float32)
    dt_bias = torch.randn((hv,), device=device, dtype=torch.float32)
    initial_state = torch.randn((batch + 1, hv, v, k), device=device, dtype=state_dtype)
    out = torch.empty((batch, 1, hv, v), device=device, dtype=dtype)
    indices = torch.arange(1, batch + 1, device=device, dtype=torch.int32)

    bk = triton.next_power_of_2(k)
    nv = triton.cdiv(v, bv)
    grid = (nv, batch * hv)
    kwargs = {
        "mixed_qkv": mixed_qkv,
        "a": a,
        "b": b,
        "A_log": a_log,
        "dt_bias": dt_bias,
        "o": out,
        "h0": initial_state,
        "ht": initial_state,
        "ssm_state_indices": indices,
        "scale": k**-0.5,
        "stride_mixed_qkv_tok": mixed_qkv.stride(0),
        "stride_a_tok": a.stride(0),
        "stride_b_tok": b.stride(0),
        "stride_init_state_token": initial_state.stride(0),
        "stride_final_state_token": initial_state.stride(0),
        "stride_indices_seq": indices.stride(0),
        "H": h,
        "HV": hv,
        "K": k,
        "V": v,
        "BK": bk,
        "BV": bv,
        "SOFTPLUS_THRESHOLD": 20.0,
        "USE_QK_L2NORM_IN_KERNEL": True,
        "num_warps": num_warps,
        "num_stages": num_stages,
    }

    for _ in range(warmup):
        fused_recurrent_gated_delta_rule_packed_decode_kernel[grid](**kwargs)
    torch.cuda.synchronize()

    samples: list[float] = []
    for _ in range(repeats):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        fused_recurrent_gated_delta_rule_packed_decode_kernel[grid](**kwargs)
        end.record()
        end.synchronize()
        samples.append(float(start.elapsed_time(end)) * 1000.0)

    return {
        "batch": batch,
        "h": h,
        "hv": hv,
        "k": k,
        "v": v,
        "bv": bv,
        "bk": bk,
        "num_warps": num_warps,
        "num_stages": num_stages,
        "dtype": str(dtype).replace("torch.", ""),
        "state_dtype": str(state_dtype).replace("torch.", ""),
        "median_us": statistics.median(samples),
        "mean_us": statistics.fmean(samples),
        "min_us": min(samples),
        "max_us": max(samples),
        "p90_us": sorted(samples)[int(0.9 * (len(samples) - 1))],
        "samples_us": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--batches", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--bv", type=int, nargs="+", default=[16, 32, 64])
    parser.add_argument("--num-warps", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--num-stages", type=int, nargs="+", default=[2, 3, 4])
    parser.add_argument("--repeats", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--h", type=int, default=16)
    parser.add_argument("--hv", type=int, default=32)
    parser.add_argument("--k", type=int, default=128)
    parser.add_argument("--v", type=int, default=128)
    args = parser.parse_args()

    torch.cuda.set_device(args.gpu)
    rows: list[dict[str, Any]] = []
    for batch in args.batches:
        for bv in args.bv:
            for num_warps in args.num_warps:
                for num_stages in args.num_stages:
                    row = _bench_variant(
                        batch=batch,
                        h=args.h,
                        hv=args.hv,
                        k=args.k,
                        v=args.v,
                        bv=bv,
                        num_warps=num_warps,
                        num_stages=num_stages,
                        dtype=torch.bfloat16,
                        state_dtype=torch.float32,
                        repeats=args.repeats,
                        warmup=args.warmup,
                    )
                    rows.append(row)
                    print(json.dumps({k: v for k, v in row.items() if k != "samples_us"}))

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
