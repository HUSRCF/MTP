#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from safetensors.torch import load_file

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.repack import (  # noqa: E402
    GptqProjectionTensors,
    SingleExpertMlp,
    SingleExpertWeights,
    dequantize_gptq_projection,
    resolve_torch_dtype,
    synthesize_g_idx,
)


DEFAULT_EXTRA_TENSORS = Path(
    "data/modelscope_downloads/Intel/Qwen3.6-35B-A3B-int4-AutoRound/"
    "model_extra_tensors.safetensors"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dequantize one MTP MoE expert from model_extra_tensors and run an MLP smoke test."
    )
    parser.add_argument("--extra-tensors", type=Path, default=DEFAULT_EXTRA_TENSORS)
    parser.add_argument("--expert", type=int, default=0)
    parser.add_argument("--bits", type=int, default=4)
    parser.add_argument("--group-size", type=int, default=128)
    parser.add_argument("--dtype", choices=("bf16", "bfloat16", "fp16", "float16", "fp32", "float32"), default="bf16")
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--seq-len", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def _dequant_projection(
    tensors: dict[str, torch.Tensor],
    *,
    prefix: str,
    bits: int,
    group_size: int,
    dtype: torch.dtype,
) -> torch.Tensor:
    qweight = tensors[f"{prefix}.qweight"]
    return dequantize_gptq_projection(
        GptqProjectionTensors(
            qweight=qweight,
            qzeros=tensors[f"{prefix}.qzeros"],
            scales=tensors[f"{prefix}.scales"],
            g_idx=synthesize_g_idx(qweight, bits=bits, group_size=group_size),
        ),
        bits=bits,
        dtype=dtype,
    )


def main() -> None:
    args = parse_args()
    target_dtype = resolve_torch_dtype(args.dtype)
    torch.manual_seed(args.seed)

    tensors = load_file(args.extra_tensors, device="cpu")
    base = f"mtp.layers.0.mlp.experts.{args.expert}"
    weights = SingleExpertWeights(
        gate_proj=_dequant_projection(
            tensors,
            prefix=f"{base}.gate_proj",
            bits=args.bits,
            group_size=args.group_size,
            dtype=target_dtype,
        ),
        up_proj=_dequant_projection(
            tensors,
            prefix=f"{base}.up_proj",
            bits=args.bits,
            group_size=args.group_size,
            dtype=target_dtype,
        ),
        down_proj=_dequant_projection(
            tensors,
            prefix=f"{base}.down_proj",
            bits=args.bits,
            group_size=args.group_size,
            dtype=target_dtype,
        ),
    )

    mlp = SingleExpertMlp(weights)
    input_tensor = torch.randn(args.batch, args.seq_len, mlp.hidden_size, dtype=target_dtype)
    output = mlp(input_tensor)
    result = {
        "ok": bool(torch.isfinite(output).all().item()),
        "extra_tensors": str(args.extra_tensors),
        "expert": args.expert,
        "bits": args.bits,
        "group_size": args.group_size,
        "gate_proj_shape": list(weights.gate_proj.shape),
        "up_proj_shape": list(weights.up_proj.shape),
        "down_proj_shape": list(weights.down_proj.shape),
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
