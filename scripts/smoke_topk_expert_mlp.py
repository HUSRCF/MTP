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
    load_topk_expert_mlp,
    resolve_torch_dtype,
)


DEFAULT_REPACKED_DIR = Path("data/repacked/qwen3_6_moe_experts")


def parse_int_list(text: str) -> list[int]:
    values = [part.strip() for part in text.split(",") if part.strip()]
    if not values:
        msg = "Expected at least one expert id"
        raise argparse.ArgumentTypeError(msg)
    return [int(value) for value in values]


def parse_float_list(text: str) -> list[float]:
    values = [part.strip() for part in text.split(",") if part.strip()]
    if not values:
        msg = "Expected at least one expert weight"
        raise argparse.ArgumentTypeError(msg)
    return [float(value) for value in values]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a dense-dequantized top-k Qwen3 MoE expert aggregation smoke test."
    )
    parser.add_argument("--repacked-dir", type=Path, default=DEFAULT_REPACKED_DIR)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--experts", type=parse_int_list, default=[0, 1, 2])
    parser.add_argument(
        "--weights",
        type=parse_float_list,
        default=None,
        help="Comma-separated router weights. Default: equal normalized weights.",
    )
    parser.add_argument("--bits", type=int, default=4)
    parser.add_argument(
        "--dtype",
        choices=("bf16", "bfloat16", "fp16", "float16", "fp32", "float32"),
        default="bf16",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--seq-len", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_dtype = resolve_torch_dtype(args.dtype)
    expert_ids = list(args.experts)
    if args.weights is None:
        expert_weights = [1.0 / len(expert_ids)] * len(expert_ids)
    else:
        expert_weights = list(args.weights)
    if len(expert_ids) != len(expert_weights):
        msg = f"--experts and --weights length mismatch: {len(expert_ids)} vs {len(expert_weights)}"
        raise SystemExit(msg)

    torch.manual_seed(args.seed)
    with RepackedMoeExpertStore(args.repacked_dir) as store:
        topk_mlp = load_topk_expert_mlp(
            store,
            layer=args.layer,
            expert_ids=expert_ids,
            bits=args.bits,
            dtype=target_dtype,
            device=args.device,
        )

    input_tensor = torch.randn(
        args.batch,
        args.seq_len,
        topk_mlp.hidden_size,
        device=next(topk_mlp.parameters(), next(topk_mlp.buffers())).device,
        dtype=target_dtype,
    )
    ids = torch.tensor(expert_ids, dtype=torch.long)
    weights = torch.tensor(expert_weights, dtype=target_dtype, device=input_tensor.device)
    with torch.inference_mode():
        output = topk_mlp(input_tensor, ids, weights)

    result = {
        "ok": bool(torch.isfinite(output).all().item()),
        "layer": args.layer,
        "expert_ids": expert_ids,
        "expert_weights": expert_weights,
        "loaded_expert_ids": list(topk_mlp.loaded_expert_ids),
        "weight_sum": float(weights.float().sum().item()),
        "bits": args.bits,
        "dtype": str(target_dtype).replace("torch.", ""),
        "hidden_size": topk_mlp.hidden_size,
        "intermediate_size": topk_mlp.intermediate_size,
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
