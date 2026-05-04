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
    load_single_expert_mlp,
    resolve_torch_dtype,
)


DEFAULT_REPACKED_DIR = Path("data/repacked/qwen3_6_moe_experts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one dense-dequantized Qwen3 MoE expert MLP smoke test."
    )
    parser.add_argument("--repacked-dir", type=Path, default=DEFAULT_REPACKED_DIR)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--expert", type=int, default=0)
    parser.add_argument("--bits", type=int, default=4)
    parser.add_argument(
        "--dtype",
        choices=("bf16", "bfloat16", "fp16", "float16", "fp32", "float32"),
        default="bf16",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--seq-len", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_dtype = resolve_torch_dtype(args.dtype)
    torch.manual_seed(args.seed)

    with RepackedMoeExpertStore(args.repacked_dir) as store:
        mlp = load_single_expert_mlp(
            store,
            layer=args.layer,
            expert=args.expert,
            bits=args.bits,
            dtype=target_dtype,
            device=args.device,
        )

    input_tensor = torch.randn(
        args.batch,
        args.seq_len,
        mlp.hidden_size,
        device=mlp.gate_proj.device,
        dtype=mlp.gate_proj.dtype,
    )
    with torch.inference_mode():
        output = mlp(input_tensor)

    result = {
        "ok": bool(torch.isfinite(output).all().item()),
        "layer": args.layer,
        "expert": args.expert,
        "bits": args.bits,
        "dtype": str(mlp.gate_proj.dtype).replace("torch.", ""),
        "hidden_size": mlp.hidden_size,
        "intermediate_size": mlp.intermediate_size,
        "gate_proj_shape": list(mlp.gate_proj.shape),
        "up_proj_shape": list(mlp.up_proj.shape),
        "down_proj_shape": list(mlp.down_proj.shape),
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
