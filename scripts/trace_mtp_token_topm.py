#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.mtp import (  # noqa: E402
    MtpExtraRunner,
    load_lm_head_from_model_dir,
    load_token_embeddings_from_model_dir,
)
from mtp_expert_prefetch.repack import resolve_torch_dtype  # noqa: E402
from mtp_expert_prefetch.utils.config import find_project_root, resolve_path  # noqa: E402

DEFAULT_EXTRA_TENSORS = Path(
    "data/modelscope_downloads/Intel/Qwen3.6-35B-A3B-int4-AutoRound/"
    "model_extra_tensors.safetensors"
)
DEFAULT_MODEL_DIR = Path("data/modelscope_downloads/Intel/Qwen3.6-35B-A3B-int4-AutoRound")
DEFAULT_TRACE_SAMPLE = Path("data/traces/aya_dataset_smoke_autoround/sample_000000.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trace native MTP token top-M predictions from AutoRound extra tensors."
    )
    parser.add_argument("--extra-tensors", type=Path, default=DEFAULT_EXTRA_TENSORS)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--trace-sample", type=Path, default=DEFAULT_TRACE_SAMPLE)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--top-k-experts", type=int, default=8)
    parser.add_argument("--top-m-tokens", type=int, default=16)
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument("--bits", type=int, default=4)
    parser.add_argument("--group-size", type=int, default=128)
    parser.add_argument(
        "--dtype",
        choices=("bf16", "bfloat16", "fp16", "float16", "fp32", "float32"),
        default="bf16",
    )
    parser.add_argument("--device", default="cuda")
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


def _topm_token_logits(
    final_states: torch.Tensor,
    lm_head: torch.Tensor,
    *,
    top_m: int,
    chunk_tokens: int = 16,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    flat = final_states.reshape(-1, final_states.shape[-1])
    id_parts = []
    logit_parts = []
    prob_parts = []
    for start in range(0, flat.shape[0], chunk_tokens):
        chunk = flat[start : start + chunk_tokens]
        logits = F.linear(chunk, lm_head).float()
        top_values, top_ids = torch.topk(logits, k=top_m, dim=-1)
        top_probs = F.softmax(top_values, dim=-1)
        id_parts.append(top_ids.detach().cpu())
        logit_parts.append(top_values.detach().cpu())
        prob_parts.append(top_probs.detach().cpu())
    shape = (*final_states.shape[:-1], top_m)
    return (
        torch.cat(id_parts, dim=0).reshape(shape).to(torch.int32),
        torch.cat(logit_parts, dim=0).reshape(shape),
        torch.cat(prob_parts, dim=0).reshape(shape),
    )


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.trace_sample)
    extra_tensors = resolve_path(args.extra_tensors, base_dir=project_root)
    model_dir = resolve_path(args.model_dir, base_dir=project_root)
    trace_sample = resolve_path(args.trace_sample, base_dir=project_root)
    output = (
        resolve_path(args.output, base_dir=project_root)
        if args.output is not None
        else trace_sample.with_name(trace_sample.stem + "_mtp_token_topm.pt")
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    dtype = resolve_torch_dtype(args.dtype)
    hidden_states, input_ids = _load_trace_sample(trace_sample, dtype)
    token_limit = min(int(args.max_tokens), int(hidden_states.shape[1]))
    hidden_states = hidden_states[:, :token_limit].contiguous()
    input_ids = input_ids[:, :token_limit].contiguous()

    token_embeddings = load_token_embeddings_from_model_dir(
        model_dir,
        input_ids,
        dtype=dtype,
        device=args.device,
    )
    probe_runner = MtpExtraRunner.from_file(
        extra_tensors,
        expert_ids=(0,),
        bits=args.bits,
        group_size=args.group_size,
        dtype=dtype,
        device=args.device,
        load_moe=False,
    )
    with torch.inference_mode():
        attention_states = probe_runner.attention_states(hidden_states, token_embeddings)
        mtp_moe_inputs = probe_runner.normalize_moe_inputs(attention_states)
        router_output = probe_runner.router_topk(mtp_moe_inputs, top_k=args.top_k_experts)
    unique_expert_ids = tuple(
        int(expert_id)
        for expert_id in torch.unique(router_output.topk_ids.detach().cpu()).to(torch.long).tolist()
    )

    runner = MtpExtraRunner.from_file(
        extra_tensors,
        expert_ids=unique_expert_ids,
        bits=args.bits,
        group_size=args.group_size,
        dtype=dtype,
        device=args.device,
        load_moe=True,
    )
    lm_head = load_lm_head_from_model_dir(model_dir, dtype=dtype, device=args.device)
    with torch.inference_mode():
        attention_states = runner.attention_states(hidden_states, token_embeddings)
        mtp_moe_inputs = runner.normalize_moe_inputs(attention_states)
        router_output = runner.router_topk(mtp_moe_inputs, top_k=args.top_k_experts)
        moe_outputs = runner.moe_tokens(
            mtp_moe_inputs,
            router_output.topk_ids,
            router_output.topk_weights,
        )
        final_states = runner.finalize_tokens(attention_states, moe_outputs)
        token_topm_ids, token_topm_logits, token_topm_probs = _topm_token_logits(
            final_states,
            lm_head,
            top_m=args.top_m_tokens,
        )

    payload = {
        "input_ids": input_ids.detach().cpu().to(torch.int32),
        "native_mtp_token_topm_ids": token_topm_ids,
        "native_mtp_token_topm_logits": token_topm_logits,
        "native_mtp_token_topm_probs": token_topm_probs,
        "native_mtp_router_topk": router_output.topk_ids.detach().cpu().to(torch.int16),
        "native_mtp_router_weights": router_output.topk_weights.detach().cpu(),
        "loaded_mtp_expert_ids": torch.tensor(unique_expert_ids, dtype=torch.int16),
        "trace_sample": str(trace_sample),
    }
    torch.save(payload, output)
    report = {
        "ok": True,
        "output": str(output),
        "trace_sample": str(trace_sample),
        "device": str(args.device),
        "dtype": str(dtype).replace("torch.", ""),
        "num_tokens": token_limit,
        "top_m_tokens": int(args.top_m_tokens),
        "top_k_experts": int(args.top_k_experts),
        "num_loaded_mtp_experts": len(unique_expert_ids),
        "first_position_token_ids": [
            int(x) for x in token_topm_ids[0, 0].to(torch.long).tolist()
        ],
        "first_position_token_probs": [
            float(x) for x in token_topm_probs[0, 0].to(torch.float32).tolist()
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
