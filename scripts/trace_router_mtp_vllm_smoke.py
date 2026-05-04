from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PROJECT_SRC))

from mtp_expert_prefetch.tracing.vllm_router_trace import (
    VllmRouterRecorder,
    patch_vllm_qwen35_moe_router_trace,
    set_active_vllm_router_recorder,
    write_vllm_trace_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline vLLM Qwen3.6 MoE router trace smoke.")
    parser.add_argument(
        "--model",
        default="data/modelscope_downloads/Intel/Qwen3.6-35B-A3B-int4-AutoRound",
    )
    parser.add_argument("--output-dir", default="data/traces/vllm_smoke")
    parser.add_argument("--prompt", default="Who are you? Give one concise C++ fast input example.")
    parser.add_argument("--max-model-len", type=int, default=128)
    parser.add_argument("--max-tokens", type=int, default=1)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.85)
    parser.add_argument(
        "--with-mm",
        action="store_true",
        help="Initialize multimodal towers. Default is text-only to avoid vision tower overhead.",
    )
    parser.add_argument(
        "--disable-return-routed-experts",
        action="store_true",
        help="Disable vLLM built-in routed expert capture.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.with_mm:
        os.environ["MTP_PREFETCH_DISABLE_FLASH_ATTN_PROBE"] = "1"
        os.environ["PYTHONPATH"] = (
            str(PROJECT_SRC)
            if not os.environ.get("PYTHONPATH")
            else f"{PROJECT_SRC}:{os.environ['PYTHONPATH']}"
        )
        original_find_spec = importlib.util.find_spec

        def find_spec_without_flash_attn(name: str, package: str | None = None):
            if name == "flash_attn" or name.startswith("flash_attn."):
                return None
            return original_find_spec(name, package)

        importlib.util.find_spec = find_spec_without_flash_attn

    patch_vllm_qwen35_moe_router_trace()
    recorder = VllmRouterRecorder(top_k=args.top_k)
    set_active_vllm_router_recorder(recorder)

    if args.dry_run:
        print("vLLM router trace patch installed.")
        return

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    tokenizer = AutoTokenizer.from_pretrained(
        args.model,
        trust_remote_code=True,
        local_files_only=True,
    )
    input_ids = tokenizer(args.prompt, return_tensors=None)["input_ids"]

    llm = LLM(
        model=args.model,
        trust_remote_code=True,
        dtype="bfloat16",
        max_model_len=args.max_model_len,
        tensor_parallel_size=args.tensor_parallel_size,
        gpu_memory_utilization=args.gpu_memory_utilization,
        enforce_eager=True,
        enable_return_routed_experts=not args.disable_return_routed_experts,
        language_model_only=not args.with_mm,
        limit_mm_per_prompt={} if args.with_mm else {"image": 0, "video": 0},
    )
    outputs = llm.generate(
        [args.prompt],
        SamplingParams(max_tokens=args.max_tokens, temperature=0.0),
    )
    generated_text = outputs[0].outputs[0].text if outputs and outputs[0].outputs else ""

    output_dir = Path(args.output_dir)
    sample_path = recorder.save(output_dir / "sample_000000.pt", input_ids=input_ids)
    routed_experts = None
    if outputs and outputs[0].outputs:
        routed_experts = getattr(outputs[0].outputs[0], "routed_experts", None)
    if routed_experts is not None:
        import torch

        payload = torch.load(sample_path, map_location="cpu")
        payload["vllm_routed_experts"] = torch.as_tensor(routed_experts, dtype=torch.int16)
        payload["vllm_routed_experts_shape"] = list(payload["vllm_routed_experts"].shape)
        torch.save(payload, sample_path)
    manifest_path = write_vllm_trace_manifest(
        output_dir,
        sample_path=sample_path,
        prompt=args.prompt,
        generated_text=generated_text,
        num_router_calls=len(recorder.calls),
    )
    print(manifest_path)


if __name__ == "__main__":
    main()
