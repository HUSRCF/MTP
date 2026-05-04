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
from mtp_expert_prefetch.tracing import (  # noqa: E402
    load_trace_payload,
    resolve_trace_sample,
    select_router_topk,
    select_trace_hidden_token,
)


DEFAULT_REPACKED_DIR = Path("data/repacked/qwen3_6_moe_experts")
DEFAULT_TRACE_MANIFEST = Path("data/traces/aya_dataset_smoke/manifest.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge a router trace top-k selection into dense-dequantized TopKExpertMlp."
    )
    parser.add_argument("--trace-sample", type=Path, default=None)
    parser.add_argument("--trace-manifest", type=Path, default=DEFAULT_TRACE_MANIFEST)
    parser.add_argument("--repacked-dir", type=Path, default=DEFAULT_REPACKED_DIR)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--module-name", default=None)
    parser.add_argument("--call-index", type=int, default=0)
    parser.add_argument("--batch-index", type=int, default=0)
    parser.add_argument("--token-index", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument(
        "--scores-to-weights",
        choices=("softmax", "raw", "identity", "uniform", "equal"),
        default="softmax",
    )
    parser.add_argument("--bits", type=int, default=4)
    parser.add_argument(
        "--dtype",
        choices=("bf16", "bfloat16", "fp16", "float16", "fp32", "float32"),
        default="bf16",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--allow-random-input", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_dtype = resolve_torch_dtype(args.dtype)
    torch.manual_seed(args.seed)

    sample_path = resolve_trace_sample(
        sample_path=args.trace_sample,
        manifest_path=args.trace_manifest,
    )
    payload = load_trace_payload(sample_path)
    selection = select_router_topk(
        payload,
        layer=args.layer if args.module_name is None else None,
        module_name=args.module_name,
        call_index=args.call_index,
        batch_index=args.batch_index,
        token_index=args.token_index,
        top_k=args.top_k,
        scores_to_weights=args.scores_to_weights,
    )

    with RepackedMoeExpertStore(args.repacked_dir) as store:
        topk_mlp = load_topk_expert_mlp(
            store,
            layer=args.layer,
            expert_ids=[int(value) for value in selection.expert_ids.tolist()],
            bits=args.bits,
            dtype=target_dtype,
            device=args.device,
        )

    input_source = "last_hidden_state"
    try:
        input_tensor = select_trace_hidden_token(
            payload,
            batch_index=args.batch_index,
            token_index=args.token_index,
        ).to(device=args.device, dtype=target_dtype)
    except KeyError:
        if not args.allow_random_input:
            raise
        input_source = "random"
        input_tensor = torch.randn(
            1,
            1,
            topk_mlp.hidden_size,
            device=args.device,
            dtype=target_dtype,
        )

    ids = selection.expert_ids.to(torch.long)
    weights = selection.expert_weights.to(device=input_tensor.device, dtype=target_dtype)
    with torch.inference_mode():
        output = topk_mlp(input_tensor, ids, weights)

    result = {
        "ok": bool(torch.isfinite(output).all().item()),
        "trace_sample": str(sample_path),
        "router_module": selection.module_name,
        "layer": args.layer,
        "call_index": selection.call_index,
        "batch_index": selection.batch_index,
        "token_index": selection.token_index,
        "expert_ids": [int(value) for value in selection.expert_ids.tolist()],
        "expert_weights": [float(value) for value in selection.expert_weights.tolist()],
        "has_router_scores": selection.raw_scores is not None,
        "scores_to_weights": args.scores_to_weights,
        "weight_sum": float(selection.expert_weights.float().sum().item()),
        "input_source": input_source,
        "input_shape": list(input_tensor.shape),
        "output_shape": list(output.shape),
        "output_dtype": str(output.dtype).replace("torch.", ""),
        "output_abs_mean": float(output.float().abs().mean().item()),
        "output_abs_max": float(output.float().abs().max().item()),
        "note": (
            "`last_hidden_state` is dimensionally valid for this bridge smoke; "
            "it is not guaranteed to be the exact pre-MLP hidden state for the selected layer."
        )
        if input_source == "last_hidden_state"
        else "Random input was used because the trace did not contain last_hidden_state.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
