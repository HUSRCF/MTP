#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.mtp import MtpExtraRunner, load_token_embeddings_from_model_dir  # noqa: E402
from mtp_expert_prefetch.repack import resolve_torch_dtype  # noqa: E402


DEFAULT_EXTRA_TENSORS = Path(
    "data/modelscope_downloads/Intel/Qwen3.6-35B-A3B-int4-AutoRound/"
    "model_extra_tensors.safetensors"
)
DEFAULT_MODEL_DIR = Path("data/modelscope_downloads/Intel/Qwen3.6-35B-A3B-int4-AutoRound")
DEFAULT_TRACE_SAMPLE = Path("data/traces/aya_dataset_smoke_autoround/sample_000000.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bypass-load model_extra_tensors and run a minimal MTP pre-fc/router/MoE smoke."
    )
    parser.add_argument("--extra-tensors", type=Path, default=DEFAULT_EXTRA_TENSORS)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--trace-sample", type=Path, default=DEFAULT_TRACE_SAMPLE)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--token-index", type=int, default=0)
    parser.add_argument("--bits", type=int, default=4)
    parser.add_argument("--group-size", type=int, default=128)
    parser.add_argument(
        "--dtype",
        choices=("bf16", "bfloat16", "fp16", "float16", "fp32", "float32"),
        default="bf16",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seed", type=int, default=20260426)
    parser.add_argument("--random-token-embeddings", action="store_true")
    return parser.parse_args()


def _load_trace_sample(path: Path, dtype: torch.dtype) -> tuple[torch.Tensor, torch.Tensor]:
    sample = torch.load(path, map_location="cpu", weights_only=False)
    hidden = sample["last_hidden_state"]
    if hidden.ndim != 3:
        msg = f"last_hidden_state must be [batch, seq, hidden], got {tuple(hidden.shape)}"
        raise ValueError(msg)
    input_ids = sample["input_ids"]
    if input_ids.shape != hidden.shape[:2]:
        msg = (
            f"input_ids shape {tuple(input_ids.shape)} does not match "
            f"hidden {tuple(hidden.shape[:2])}"
        )
        raise ValueError(msg)
    return hidden.to(dtype=dtype), input_ids.to(dtype=torch.long)


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)
    dtype = resolve_torch_dtype(args.dtype)

    hidden_states, input_ids = _load_trace_sample(args.trace_sample, dtype)
    if args.random_token_embeddings:
        token_embeddings = torch.randn_like(hidden_states)
        embedding_source = "random"
    else:
        token_embeddings = load_token_embeddings_from_model_dir(
            args.model_dir,
            input_ids,
            dtype=dtype,
            device=args.device,
        )
        embedding_source = "model.language_model.embed_tokens.weight"

    probe_runner = MtpExtraRunner.from_file(
        args.extra_tensors,
        expert_ids=(0,),
        bits=args.bits,
        group_size=args.group_size,
        dtype=dtype,
        device=args.device,
    )
    mtp_moe_inputs = probe_runner.moe_inputs(hidden_states, token_embeddings)
    router_output = probe_runner.router_topk(mtp_moe_inputs, top_k=args.top_k)

    token_index = int(args.token_index)
    if token_index < 0 or token_index >= mtp_moe_inputs.shape[1]:
        msg = f"token-index must be in [0, {mtp_moe_inputs.shape[1] - 1}], got {token_index}"
        raise ValueError(msg)
    selected_ids = router_output.topk_ids[0, token_index].to(device="cpu", dtype=torch.long)
    selected_weights = router_output.topk_weights[0, token_index].to(device="cpu", dtype=dtype)

    runner = MtpExtraRunner.from_file(
        args.extra_tensors,
        expert_ids=tuple(int(x) for x in selected_ids.tolist()),
        bits=args.bits,
        group_size=args.group_size,
        dtype=dtype,
        device=args.device,
    )
    attention_states = runner.attention_states(hidden_states, token_embeddings)
    mtp_moe_inputs = runner.normalize_moe_inputs(attention_states)
    router_output = runner.router_topk(mtp_moe_inputs, top_k=args.top_k)
    selected_ids = router_output.topk_ids[0, token_index].to(device=args.device, dtype=torch.long)
    selected_weights = router_output.topk_weights[0, token_index].to(
        device=args.device,
        dtype=dtype,
    )
    moe_output = runner.moe_token(mtp_moe_inputs[0, token_index], selected_ids, selected_weights)
    final_output = runner.finalize_token(attention_states[0, token_index], moe_output)

    result = {
        "ok": bool(torch.isfinite(final_output).all().item()),
        "extra_tensors": str(args.extra_tensors),
        "model_dir": str(args.model_dir),
        "trace_sample": str(args.trace_sample),
        "embedding_source": embedding_source,
        "dtype": str(dtype).replace("torch.", ""),
        "device": str(args.device),
        "input_ids_shape": list(input_ids.shape),
        "hidden_shape": list(hidden_states.shape),
        "token_embeddings_shape": list(token_embeddings.shape),
        "attention_states_shape": list(attention_states.shape),
        "mtp_moe_inputs_shape": list(mtp_moe_inputs.shape),
        "router_logits_shape": list(router_output.logits.shape),
        "topk_ids_shape": list(router_output.topk_ids.shape),
        "topk_weights_shape": list(router_output.topk_weights.shape),
        "token_index": token_index,
        "selected_expert_ids": [int(x) for x in selected_ids.to(device="cpu").tolist()],
        "selected_expert_weights": [
            float(x) for x in selected_weights.to(device="cpu", dtype=torch.float32).tolist()
        ],
        "loaded_expert_ids": list(runner.loaded_expert_ids),
        "moe_output_shape": list(moe_output.shape),
        "moe_output_dtype": str(moe_output.dtype).replace("torch.", ""),
        "moe_output_abs_mean": float(moe_output.float().abs().mean().item()),
        "moe_output_abs_max": float(moe_output.float().abs().max().item()),
        "final_output_shape": list(final_output.shape),
        "final_output_dtype": str(final_output.dtype).replace("torch.", ""),
        "final_output_abs_mean": float(final_output.float().abs().mean().item()),
        "final_output_abs_max": float(final_output.float().abs().max().item()),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
