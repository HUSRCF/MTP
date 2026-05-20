#!/usr/bin/env python3
"""Microbenchmark vLLM's GDN causal_conv1d_update Triton decode kernel.

This is a diagnostic/autotune helper. It does not patch vLLM runtime code.
The goal is to test whether simple launch-meta variants beat vLLM's default
causal-conv update settings for the Qwen3.5/Qwen3.6 GDN decode shape.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
from typing import Any

import torch

from vllm.model_executor.layers.mamba.ops.causal_conv1d import (
    _causal_conv1d_update_kernel,
)
from vllm.triton_utils import triton
from vllm.v1.attention.backends.utils import NULL_BLOCK_ID


def _bench_variant(
    *,
    batch: int,
    dim: int,
    seqlen: int,
    width: int,
    block_n: int,
    num_warps: int,
    num_stages: int,
    dtype: torch.dtype,
    state_dtype: torch.dtype,
    repeats: int,
    warmup: int,
) -> dict[str, Any]:
    device = torch.device("cuda")
    state_len = width - 1
    num_cache_lines = batch + 1

    x = torch.randn((batch, dim, seqlen), device=device, dtype=state_dtype)
    weight = torch.randn((dim, width), device=device, dtype=dtype)
    bias = torch.randn((dim,), device=device, dtype=dtype)
    conv_state = torch.randn(
        (num_cache_lines, dim, state_len), device=device, dtype=state_dtype
    )
    conv_state_indices = torch.arange(1, batch + 1, device=device, dtype=torch.int32)
    out = x

    stride_x_seq, stride_x_dim, stride_x_token = x.stride()
    stride_w_dim, stride_w_width = weight.stride()
    stride_state_seq, stride_state_dim, stride_state_token = conv_state.stride()
    stride_o_seq, stride_o_dim, stride_o_token = out.stride()
    stride_state_indices = conv_state_indices.stride(0)
    np2_statelen = triton.next_power_of_2(state_len)
    grid = (batch, triton.cdiv(dim, block_n))

    kwargs = {
        "x_ptr": x,
        "w_ptr": weight,
        "bias_ptr": bias,
        "conv_state_ptr": conv_state,
        "conv_state_indices_ptr": conv_state_indices,
        "num_accepted_tokens_ptr": None,
        "query_start_loc_ptr": None,
        "block_idx_last_scheduled_token": None,
        "initial_state_idx": None,
        "o_ptr": out,
        "batch": batch,
        "dim": dim,
        "seqlen": seqlen,
        "state_len": state_len,
        "num_cache_lines": num_cache_lines,
        "stride_x_seq": stride_x_seq,
        "stride_x_dim": stride_x_dim,
        "stride_x_token": stride_x_token,
        "stride_w_dim": stride_w_dim,
        "stride_w_width": stride_w_width,
        "stride_conv_state_seq": stride_state_seq,
        "stride_conv_state_dim": stride_state_dim,
        "stride_conv_state_tok": stride_state_token,
        "stride_state_indices": stride_state_indices,
        "stride_o_seq": stride_o_seq,
        "stride_o_dim": stride_o_dim,
        "stride_o_token": stride_o_token,
        "null_block_id": NULL_BLOCK_ID,
        "HAS_BIAS": True,
        "KERNEL_WIDTH": width,
        "SILU_ACTIVATION": True,
        "IS_VARLEN": False,
        "IS_APC_ENABLED": False,
        "IS_SPEC_DECODING": False,
        "NP2_STATELEN": np2_statelen,
        "HAS_NULL_BLOCK": True,
        "BLOCK_N": block_n,
        "num_warps": num_warps,
        "num_stages": num_stages,
    }

    for _ in range(warmup):
        _causal_conv1d_update_kernel[grid](**kwargs)
    torch.cuda.synchronize()

    samples: list[float] = []
    for _ in range(repeats):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        _causal_conv1d_update_kernel[grid](**kwargs)
        end.record()
        end.synchronize()
        samples.append(float(start.elapsed_time(end)) * 1000.0)

    return {
        "batch": batch,
        "dim": dim,
        "seqlen": seqlen,
        "width": width,
        "state_len": state_len,
        "block_n": block_n,
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
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--batches", type=int, nargs="+", default=[8])
    parser.add_argument("--block-n", type=int, nargs="+", default=[128, 256, 512])
    parser.add_argument("--num-warps", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--num-stages", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--repeats", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--dim", type=int, default=8192)
    parser.add_argument("--seqlen", type=int, default=1)
    parser.add_argument("--width", type=int, default=4)
    args = parser.parse_args()

    torch.cuda.set_device(args.gpu)
    rows: list[dict[str, Any]] = []
    for batch in args.batches:
        for block_n in args.block_n:
            for num_warps in args.num_warps:
                for num_stages in args.num_stages:
                    row = _bench_variant(
                        batch=batch,
                        dim=args.dim,
                        seqlen=args.seqlen,
                        width=args.width,
                        block_n=block_n,
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
