#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.tracing.router_mtp import (  # noqa: E402
    _disable_optional_cuda_kernels_on_rocm,
    _dtype_from_name,
    _load_transformers_config,
    _load_transformers_model,
    _model_input_device,
)
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path  # noqa: E402


DEFAULT_MODEL_CONFIG = Path("configs/model/qwen3_6_35b_a3b_autoround_int4.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a tiny local generation smoke test.")
    parser.add_argument("--model-config", type=Path, default=DEFAULT_MODEL_CONFIG)
    parser.add_argument("--prompt", default="Reply with exactly one English word: hello")
    parser.add_argument("--max-new-tokens", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        msg = "Generation smoke requires transformers."
        raise RuntimeError(msg) from exc

    args = parse_args()
    started_at = time.perf_counter()
    project_root = find_project_root(args.model_config)
    model_config = load_yaml(resolve_path(args.model_config, base_dir=project_root))
    if bool(model_config.get("disable_optional_cuda_kernels_on_rocm", True)):
        _disable_optional_cuda_kernels_on_rocm()

    model_id = model_config["model_id"]
    trust_remote_code = bool(model_config.get("trust_remote_code", True))
    local_files_only = bool(model_config.get("local_files_only", False))
    quantization_options = model_config.get("quantization", {})
    gptq_backend = model_config.get("gptq_backend") or quantization_options.get("backend")
    dtype = _dtype_from_name(str(model_config.get("torch_dtype", "bfloat16")))
    hf_config = _load_transformers_config(
        model_id,
        trust_remote_code=trust_remote_code,
        local_files_only=local_files_only,
        gptq_backend=gptq_backend,
    )

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=trust_remote_code,
        local_files_only=local_files_only,
    )
    model = _load_transformers_model(
        model_id,
        hf_config=hf_config,
        trust_remote_code=trust_remote_code,
        dtype=dtype,
        device_map=model_config.get("device_map", "auto"),
        local_files_only=local_files_only,
        attn_implementation=model_config.get("attn_implementation"),
    )
    model.eval()
    loaded_at = time.perf_counter()

    encoded = tokenizer(args.prompt, return_tensors="pt")
    input_device = _model_input_device(model)
    encoded = {key: value.to(input_device) for key, value in encoded.items()}
    generated_at_start = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(
            **encoded,
            max_new_tokens=int(args.max_new_tokens),
            do_sample=False,
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    if input_device.type == "cuda":
        torch.cuda.synchronize(input_device)
    generated_at_end = time.perf_counter()

    new_tokens = generated[:, encoded["input_ids"].shape[-1] :]
    text = tokenizer.decode(new_tokens[0], skip_special_tokens=True).strip()
    generated_token_count = int(new_tokens.shape[-1])
    generation_seconds = generated_at_end - generated_at_start
    device_name = None
    if input_device.type == "cuda":
        device_name = torch.cuda.get_device_name(input_device)
    result = {
        "ok": bool(text),
        "model_id": model_id,
        "attn_implementation": model_config.get("attn_implementation"),
        "prompt": args.prompt,
        "max_new_tokens": int(args.max_new_tokens),
        "generated_text": text,
        "generated_token_count": generated_token_count,
        "input_device": str(input_device),
        "input_device_name": device_name,
        "load_seconds": loaded_at - started_at,
        "generation_seconds": generation_seconds,
        "tokens_per_second": generated_token_count / max(generation_seconds, 1e-9),
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
