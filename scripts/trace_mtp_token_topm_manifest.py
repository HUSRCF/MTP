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
from mtp_expert_prefetch.training.alignment_merge import (  # noqa: E402
    manifest_record_path,
    read_trace_manifest,
)
from mtp_expert_prefetch.utils.config import find_project_root, resolve_path  # noqa: E402

DEFAULT_EXTRA_TENSORS = Path(
    "data/modelscope_downloads/Intel/Qwen3.6-35B-A3B-int4-AutoRound/"
    "model_extra_tensors.safetensors"
)
DEFAULT_MODEL_DIR = Path("data/modelscope_downloads/Intel/Qwen3.6-35B-A3B-int4-AutoRound")
DEFAULT_MERGED_MANIFEST = Path("data/traces/aya_dataset_smoke_merged_mtp_vllm/manifest.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch trace native MTP token top-M predictions.")
    parser.add_argument("--merged-manifest", type=Path, default=DEFAULT_MERGED_MANIFEST)
    parser.add_argument("--extra-tensors", type=Path, default=DEFAULT_EXTRA_TENSORS)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/traces/mtp_token_topm_64sample"),
    )
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--top-k-experts", type=int, default=8)
    parser.add_argument("--top-m-tokens", type=int, default=32)
    parser.add_argument("--max-tokens", type=int, default=None)
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
    input_ids = sample["input_ids"]
    if hidden.ndim != 3 or input_ids.shape != hidden.shape[:2]:
        msg = (
            f"Bad trace sample shapes: hidden={tuple(hidden.shape)}, "
            f"input_ids={tuple(input_ids.shape)}"
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
        logits = F.linear(flat[start : start + chunk_tokens], lm_head).float()
        top_values, top_ids = torch.topk(logits, k=top_m, dim=-1)
        id_parts.append(top_ids.detach().cpu())
        logit_parts.append(top_values.detach().cpu())
        prob_parts.append(F.softmax(top_values, dim=-1).detach().cpu())
    shape = (*final_states.shape[:-1], top_m)
    return (
        torch.cat(id_parts, dim=0).reshape(shape).to(torch.int32),
        torch.cat(logit_parts, dim=0).reshape(shape),
        torch.cat(prob_parts, dim=0).reshape(shape),
    )


def _source_path(record: dict, project_root: Path) -> Path:
    source = record.get("mtp_source_path")
    if source:
        return Path(source)
    merged_path = manifest_record_path(record)
    payload = torch.load(merged_path, map_location="cpu", weights_only=False)
    source = payload.get("mtp_source_path")
    if source:
        return Path(source)
    msg = f"Cannot resolve MTP source path for record {record.get('sample_idx')}"
    raise KeyError(msg)


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.merged_manifest)
    merged_manifest = resolve_path(args.merged_manifest, base_dir=project_root)
    output_dir = resolve_path(args.output_dir, base_dir=project_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_manifest = output_dir / "manifest.jsonl"

    dtype = resolve_torch_dtype(args.dtype)
    records = read_trace_manifest(merged_manifest)
    if args.max_samples is not None:
        records = records[: int(args.max_samples)]

    runner = MtpExtraRunner.from_file(
        resolve_path(args.extra_tensors, base_dir=project_root),
        expert_ids=tuple(range(256)),
        bits=args.bits,
        group_size=args.group_size,
        dtype=dtype,
        device=args.device,
        load_moe=True,
    )
    lm_head = load_lm_head_from_model_dir(
        resolve_path(args.model_dir, base_dir=project_root),
        dtype=dtype,
        device=args.device,
    )

    with output_manifest.open("w", encoding="utf-8") as manifest:
        for index, record in enumerate(records):
            sample_idx = int(record["sample_idx"])
            source_path = _source_path(record, project_root)
            hidden_states, input_ids = _load_trace_sample(source_path, dtype)
            token_limit = int(hidden_states.shape[1])
            if args.max_tokens is not None:
                token_limit = min(token_limit, int(args.max_tokens))
            hidden_states = hidden_states[:, :token_limit].contiguous()
            input_ids = input_ids[:, :token_limit].contiguous()
            token_embeddings = load_token_embeddings_from_model_dir(
                resolve_path(args.model_dir, base_dir=project_root),
                input_ids,
                dtype=dtype,
                device=args.device,
            )
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
                    top_m=int(args.top_m_tokens),
                )

            output_path = output_dir / f"sample_{sample_idx:06d}.pt"
            torch.save(
                {
                    "input_ids": input_ids.detach().cpu().to(torch.int32),
                    "native_mtp_token_topm_ids": token_topm_ids,
                    "native_mtp_token_topm_logits": token_topm_logits,
                    "native_mtp_token_topm_probs": token_topm_probs,
                    "native_mtp_router_topk": router_output.topk_ids.detach().cpu().to(torch.int16),
                    "native_mtp_router_weights": router_output.topk_weights.detach().cpu(),
                    "mtp_source_path": str(source_path),
                },
                output_path,
            )
            manifest.write(
                json.dumps(
                    {
                        "sample_idx": sample_idx,
                        "path": output_path.name,
                        "mtp_source_path": str(source_path),
                        "num_tokens": token_limit,
                        "top_m_tokens": int(args.top_m_tokens),
                        "top_k_experts": int(args.top_k_experts),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            print(f"{index + 1}/{len(records)} sample_{sample_idx:06d}", flush=True)

    print(str(output_manifest))


if __name__ == "__main__":
    main()
