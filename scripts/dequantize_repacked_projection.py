#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.repack import (  # noqa: E402
    RepackedMoeExpertStore,
    apply_dequantized_projection,
    dequantize_repacked_projection,
    resolve_torch_dtype,
)


DEFAULT_REPACKED_DIR = Path("data/repacked/qwen3_6_moe_experts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dequantize one repacked GPTQ MoE expert projection and run a tiny matmul smoke test."
    )
    parser.add_argument("--repacked-dir", type=Path, default=DEFAULT_REPACKED_DIR)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--expert", type=int, default=0)
    parser.add_argument(
        "--projection",
        choices=("gate_proj", "up_proj", "down_proj"),
        default="gate_proj",
    )
    parser.add_argument("--bits", type=int, default=4)
    parser.add_argument("--dtype", choices=("bf16", "bfloat16", "fp16", "float16", "fp32", "float32"), default="bf16")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_dtype = resolve_torch_dtype(args.dtype)
    torch.manual_seed(args.seed)

    with RepackedMoeExpertStore(args.repacked_dir) as store:
        weight = dequantize_repacked_projection(
            store,
            layer=args.layer,
            expert=args.expert,
            projection=args.projection,
            bits=args.bits,
            dtype=target_dtype,
            device=args.device,
        )

    input_tensor = torch.randn(
        args.batch,
        weight.shape[1],
        device=weight.device,
        dtype=weight.dtype,
    )
    output = apply_dequantized_projection(input_tensor, weight)
    result = {
        "ok": bool(torch.isfinite(output).all().item()),
        "layer": args.layer,
        "expert": args.expert,
        "projection": args.projection,
        "bits": args.bits,
        "weight_shape": list(weight.shape),
        "weight_dtype": str(weight.dtype).replace("torch.", ""),
        "input_shape": list(input_tensor.shape),
        "output_shape": list(output.shape),
        "output_dtype": str(output.dtype).replace("torch.", ""),
        "output_abs_mean": float(output.float().abs().mean().item()),
        "output_abs_max": float(output.float().abs().max().item()),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
