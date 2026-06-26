from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any

import torch

from mtp_expert_prefetch.data.material import iter_text_material
from mtp_expert_prefetch.mtp import (
    MtpAttentionConfig,
    MtpExtraRunner,
    load_token_embeddings_from_model_dir,
)
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path


@dataclass
class HookState:
    router_topk: dict[str, list[Any]] = field(default_factory=dict)
    router_scores: dict[str, list[Any]] = field(default_factory=dict)
    mtp_shapes: dict[str, list[Any]] = field(default_factory=dict)


def _as_tensor(output: Any) -> torch.Tensor | None:
    if isinstance(output, torch.Tensor):
        return output
    if isinstance(output, dict):
        for key in ("logits", "router_logits", "scores", "hidden_states"):
            value = output.get(key)
            if isinstance(value, torch.Tensor):
                return value
    if isinstance(output, tuple | list):
        for value in output:
            tensor = _as_tensor(value)
            if tensor is not None:
                return tensor
    return None


def _tensor_shape(output: Any) -> Any:
    if isinstance(output, torch.Tensor):
        return list(output.shape)
    if isinstance(output, dict):
        return {key: _tensor_shape(value) for key, value in output.items()}
    if isinstance(output, tuple | list):
        return [_tensor_shape(value) for value in output]
    return type(output).__name__


def _router_hook(
    name: str,
    state: HookState,
    *,
    top_k: int,
    capture_scores: bool,
):
    def hook(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: Any) -> None:
        logits = _as_tensor(output)
        if logits is None or logits.shape[-1] < top_k:
            return
        values, indices = torch.topk(logits.detach().float().cpu(), k=top_k, dim=-1)
        state.router_topk.setdefault(name, []).append(indices.to(torch.int16).tolist())
        if capture_scores:
            state.router_scores.setdefault(name, []).append(values.tolist())

    return hook


def _mtp_shape_hook(name: str, state: HookState):
    def hook(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: Any) -> None:
        state.mtp_shapes.setdefault(name, []).append(_tensor_shape(output))

    return hook


def _is_router_module(name: str, num_experts: int | None) -> bool:
    if ".mlp.gate" in name or name.endswith("mlp.gate"):
        return True
    if num_experts is not None and (name.endswith(".gate") or name.endswith(".router")):
        return True
    return False


def _is_mtp_module(name: str) -> bool:
    lowered = name.lower()
    return ".mtp" in lowered or lowered.endswith("mtp") or "multi_token" in lowered


def register_trace_hooks(
    model: torch.nn.Module,
    state: HookState,
    *,
    num_experts: int | None,
    top_k: int,
    capture_router_scores: bool,
    capture_mtp_shapes: bool,
) -> list[torch.utils.hooks.RemovableHandle]:
    handles: list[torch.utils.hooks.RemovableHandle] = []
    for name, module in model.named_modules():
        if _is_router_module(name, num_experts):
            handles.append(
                module.register_forward_hook(
                    _router_hook(name, state, top_k=top_k, capture_scores=capture_router_scores)
                )
            )
        elif capture_mtp_shapes and _is_mtp_module(name):
            handles.append(module.register_forward_hook(_mtp_shape_hook(name, state)))
    return handles


def iter_jsonl_texts(path: str | Path) -> Iterable[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _load_trace_texts(trace_config: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    data_ref = trace_config["data"]
    data_config = load_yaml(resolve_path(data_ref, base_dir=project_root))

    material_path = data_config.get("material_path")
    if material_path:
        resolved = resolve_path(material_path, base_dir=project_root)
        if resolved.exists():
            return list(iter_jsonl_texts(resolved))
    return list(iter_text_material(data_config))


def _dtype_from_name(name: str) -> torch.dtype:
    normalized = name.lower()
    if normalized in {"bf16", "bfloat16"}:
        return torch.bfloat16
    if normalized in {"fp16", "float16"}:
        return torch.float16
    if normalized in {"fp32", "float32"}:
        return torch.float32
    msg = f"Unsupported torch dtype: {name}"
    raise ValueError(msg)


def _load_transformers_config(
    model_id: str,
    *,
    trust_remote_code: bool,
    local_files_only: bool,
    gptq_backend: str | None,
):
    try:
        from transformers import AutoConfig

        config = AutoConfig.from_pretrained(
            model_id,
            trust_remote_code=trust_remote_code,
            local_files_only=local_files_only,
        )
    except ValueError as exc:
        if "qwen3_5_moe" not in str(exc):
            raise
        msg = (
            "The current transformers installation does not support model_type "
            "`qwen3_5_moe`. Use an isolated project env with a transformers build that exports "
            "`Qwen3_5MoeForConditionalGeneration`. Recommended:\n"
            "  python -m venv --system-site-packages .venv\n"
            "  . .venv/bin/activate\n"
            "  python -m pip install --upgrade "
            "'git+https://github.com/huggingface/transformers.git'\n"
            "Then rerun the trace command from that env."
        )
        raise RuntimeError(msg) from exc

    if gptq_backend and hasattr(config, "quantization_config"):
        quantization_config = config.quantization_config
        if isinstance(quantization_config, dict):
            quantization_config["backend"] = gptq_backend
        else:
            quantization_config.backend = gptq_backend
    return config


def _check_transformers_model_type(
    model_id: str,
    trust_remote_code: bool,
    local_files_only: bool = False,
) -> None:
    _load_transformers_config(
        model_id,
        trust_remote_code=trust_remote_code,
        local_files_only=local_files_only,
        gptq_backend=None,
    )


def _disable_optional_cuda_kernels_on_rocm() -> None:
    """Force torch fallbacks only for optional kernels that are broken in a ROCm env."""
    if getattr(torch.version, "hip", None) is None:
        return

    import transformers.utils.import_utils as import_utils

    def mark_unavailable(name: str) -> None:
        current = getattr(import_utils, name, None)
        if hasattr(current, "cache_clear"):
            current.cache_clear()

        def unavailable() -> bool:
            return False

        setattr(import_utils, name, unavailable)

    try:
        from causal_conv1d import causal_conv1d_fn, causal_conv1d_update

        if causal_conv1d_fn is None or causal_conv1d_update is None:
            mark_unavailable("is_causal_conv1d_available")
    except Exception:
        mark_unavailable("is_causal_conv1d_available")

    try:
        from fla.modules import FusedRMSNormGated
        from fla.ops.gated_delta_rule import (
            chunk_gated_delta_rule,
            fused_recurrent_gated_delta_rule,
        )

        if not all((FusedRMSNormGated, chunk_gated_delta_rule, fused_recurrent_gated_delta_rule)):
            mark_unavailable("is_flash_linear_attention_available")
    except Exception:
        mark_unavailable("is_flash_linear_attention_available")


def _prewarm_rocm_torch_cuda_for_vllm_backend() -> bool:
    debug = str(os.environ.get("MTP_DEBUG_ROCM_PREWARM", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if getattr(torch.version, "hip", None) is None:
        if debug:
            print("[mtp-rocm-router-prewarm] skipped: torch.version.hip is false", file=sys.stderr)
        return False
    try:
        device_count = int(torch.cuda.device_count())
        available = bool(torch.cuda.is_available())
        if debug:
            print(
                "[mtp-rocm-router-prewarm] "
                f"device_count={device_count} is_available={available}",
                file=sys.stderr,
            )
        if device_count <= 0:
            return False
        if not available:
            return False
        _ = torch.cuda.get_device_properties(0)
    except Exception as exc:
        if debug:
            print(
                "[mtp-rocm-router-prewarm] "
                f"failed {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
        return False
    if debug:
        print("[mtp-rocm-router-prewarm] ok", file=sys.stderr)
    return True


def _model_input_device(model: torch.nn.Module) -> torch.device:
    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_transformers_model(
    model_id: str,
    *,
    hf_config: Any,
    trust_remote_code: bool,
    dtype: torch.dtype,
    device_map: str | dict[str, Any] | None,
    local_files_only: bool,
    attn_implementation: str | None = None,
) -> torch.nn.Module:
    attention_kwargs = {}
    if attn_implementation:
        attention_kwargs["attn_implementation"] = attn_implementation
    if (
        getattr(hf_config, "model_type", None) == "qwen3_5_moe"
        and "Qwen3_5MoeForConditionalGeneration" in getattr(hf_config, "architectures", [])
        and hasattr(hf_config, "text_config")
    ):
        from transformers.models.qwen3_5_moe.modeling_qwen3_5_moe import (
            Qwen3_5MoeForConditionalGeneration,
        )

        return Qwen3_5MoeForConditionalGeneration.from_pretrained(
            model_id,
            config=hf_config,
            trust_remote_code=trust_remote_code,
            dtype=dtype,
            device_map=device_map,
            local_files_only=local_files_only,
            **attention_kwargs,
        )

    from transformers import AutoModelForCausalLM

    return AutoModelForCausalLM.from_pretrained(
        model_id,
        config=hf_config,
        trust_remote_code=trust_remote_code,
        dtype=dtype,
        device_map=device_map,
        local_files_only=local_files_only,
        **attention_kwargs,
    )


def _mtp_attention_config_from_hf(hf_config: Any) -> MtpAttentionConfig:
    text_config = getattr(hf_config, "text_config", hf_config)
    rope_parameters = getattr(text_config, "rope_parameters", {}) or {}
    return MtpAttentionConfig(
        num_attention_heads=int(getattr(text_config, "num_attention_heads", 16)),
        num_key_value_heads=int(getattr(text_config, "num_key_value_heads", 2)),
        head_dim=int(getattr(text_config, "head_dim", 256)),
        rope_theta=float(rope_parameters.get("rope_theta", 10_000_000.0)),
        partial_rotary_factor=float(rope_parameters.get("partial_rotary_factor", 0.25)),
        rms_norm_eps=float(getattr(text_config, "rms_norm_eps", 1e-6)),
    )


def _build_native_mtp_runner(
    model_config: dict[str, Any],
    trace_options: dict[str, Any],
    *,
    project_root: Path,
    hf_config: Any,
    dtype: torch.dtype,
) -> MtpExtraRunner | None:
    mtp_config = model_config.get("mtp", {})
    if not mtp_config or not bool(trace_options.get("capture_native_mtp_router", True)):
        return None
    extra_tensors = mtp_config.get("extra_tensors")
    if not extra_tensors:
        return None
    device = trace_options.get("native_mtp_device", "cpu")
    return MtpExtraRunner.from_file(
        resolve_path(extra_tensors, base_dir=project_root),
        bits=int(mtp_config.get("bits", 4)),
        group_size=int(mtp_config.get("group_size", 128)),
        dtype=dtype,
        device=device,
        attention_config=_mtp_attention_config_from_hf(hf_config),
        load_moe=False,
    )


def _capture_native_mtp_router(
    runner: MtpExtraRunner,
    *,
    model_dir: str | Path,
    input_ids: torch.Tensor,
    last_hidden_state: torch.Tensor,
    top_k: int,
    dtype: torch.dtype,
) -> dict[str, torch.Tensor | list[int]]:
    device = runner.target_device
    input_ids_cpu = input_ids.detach().cpu().to(torch.long)
    token_embeddings = load_token_embeddings_from_model_dir(
        model_dir,
        input_ids_cpu,
        dtype=dtype,
        device=device,
    )
    hidden_states = last_hidden_state.detach().to(device=device, dtype=dtype)
    with torch.inference_mode():
        mtp_moe_inputs = runner.moe_inputs(hidden_states, token_embeddings)
        router_output = runner.router_topk(mtp_moe_inputs, top_k=top_k)
    return {
        "native_mtp_router_topk": router_output.topk_ids.detach().cpu().to(torch.int16),
        "native_mtp_router_weights": router_output.topk_weights.detach().cpu(),
        "native_mtp_router_logits_shape": list(router_output.logits.shape),
        "native_mtp_moe_inputs_shape": list(mtp_moe_inputs.shape),
    }


def trace_router_mtp(config_path: str | Path) -> Path:
    config_path = Path(config_path)
    project_root = find_project_root(config_path)
    trace_config = load_yaml(config_path)
    model_config = load_yaml(resolve_path(trace_config["model"], base_dir=project_root))
    backend = str(model_config.get("backend", "")).strip().lower()
    if backend == "vllm":
        _prewarm_rocm_torch_cuda_for_vllm_backend()
        # Import lazily to avoid a router_mtp <-> vllm_router_trace import cycle:
        # vLLM tracing reuses dataset loading helpers from this module.
        from mtp_expert_prefetch.tracing.vllm_router_trace import trace_router_mtp_vllm

        return trace_router_mtp_vllm(config_path)

    try:
        from transformers import AutoProcessor, AutoTokenizer
    except ImportError as exc:
        msg = "Tracing requires transformers."
        raise RuntimeError(msg) from exc

    trace_options = trace_config.get("trace", {})
    if bool(model_config.get("disable_optional_cuda_kernels_on_rocm", True)):
        _disable_optional_cuda_kernels_on_rocm()

    output_dir = resolve_path(trace_config["output_dir"], base_dir=project_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    texts = _load_trace_texts(trace_config, project_root)
    start_sample = int(trace_options.get("start_sample", 0))
    if start_sample:
        texts = texts[start_sample:]
    max_samples = trace_options.get("max_samples")
    if max_samples is not None:
        texts = texts[: int(max_samples)]
    if not texts:
        msg = "Trace config produced no text records."
        raise RuntimeError(msg)

    model_id = model_config["model_id"]
    trust_remote_code = bool(model_config.get("trust_remote_code", True))
    local_files_only = bool(model_config.get("local_files_only", False))
    quantization_options = model_config.get("quantization", {})
    gptq_backend = model_config.get("gptq_backend") or quantization_options.get("backend")
    hf_config = _load_transformers_config(
        model_id,
        trust_remote_code=trust_remote_code,
        local_files_only=local_files_only,
        gptq_backend=gptq_backend,
    )
    dtype = _dtype_from_name(str(model_config.get("torch_dtype", "bfloat16")))
    device_map = model_config.get("device_map", "auto")
    attn_implementation = model_config.get("attn_implementation")

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=trust_remote_code,
        local_files_only=local_files_only,
    )
    try:
        processor = AutoProcessor.from_pretrained(
            model_id,
            trust_remote_code=trust_remote_code,
            local_files_only=local_files_only,
        )
    except Exception:
        processor = None

    model = _load_transformers_model(
        model_id,
        hf_config=hf_config,
        trust_remote_code=trust_remote_code,
        dtype=dtype,
        device_map=device_map,
        local_files_only=local_files_only,
        attn_implementation=attn_implementation,
    )
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)

    arch = model_config.get("architecture", {})
    num_experts = arch.get("num_experts")
    top_k = int(arch.get("num_experts_per_tok", 8))
    max_length = int(trace_options.get("max_length", 512))
    skip_existing = bool(trace_options.get("skip_existing", False))
    capture_scores = bool(trace_options.get("capture_router_scores", False))
    capture_mtp_shapes = bool(trace_options.get("capture_mtp_shapes", True))
    capture_hidden_states = trace_options.get("capture_hidden_states", "last")
    native_mtp_runner = _build_native_mtp_runner(
        model_config,
        trace_options,
        project_root=project_root,
        hf_config=hf_config,
        dtype=dtype,
    )
    if native_mtp_runner is not None and capture_hidden_states != "last":
        msg = "`capture_native_mtp_router` requires `capture_hidden_states: last`."
        raise ValueError(msg)

    manifest_path = output_dir / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as manifest:
        for local_idx, record in enumerate(texts):
            sample_idx = start_sample + local_idx
            sample_file = output_dir / f"sample_{sample_idx:06d}.pt"
            if skip_existing and sample_file.exists():
                existing_payload = torch.load(
                    sample_file,
                    map_location="cpu",
                    weights_only=False,
                )
                manifest.write(
                    json.dumps(
                        {
                            "sample_idx": sample_idx,
                            "record_id": existing_payload.get("record", {}).get("id"),
                            "path": sample_file.name,
                            "num_tokens": int(existing_payload["input_ids"].shape[-1]),
                            "num_router_modules": len(existing_payload.get("router_topk", {})),
                            "num_mtp_modules": len(existing_payload.get("mtp_shapes", {})),
                            "has_native_mtp_router": "native_mtp_router_topk"
                            in existing_payload,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                manifest.flush()
                print(
                    f"{local_idx + 1}/{len(texts)} sample_{sample_idx:06d} skipped_existing",
                    flush=True,
                )
                continue
            state = HookState()
            handles = register_trace_hooks(
                model,
                state,
                num_experts=num_experts,
                top_k=top_k,
                capture_router_scores=capture_scores,
                capture_mtp_shapes=capture_mtp_shapes,
            )

            text = record["text"]
            if processor is not None and hasattr(processor, "tokenizer"):
                encoded = processor.tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=max_length,
                )
            else:
                encoded = tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=max_length,
                )
            input_device = _model_input_device(model)
            encoded = {key: value.to(input_device) for key, value in encoded.items()}

            with torch.inference_mode():
                outputs = model(
                    **encoded,
                    output_hidden_states=capture_hidden_states is not None,
                    use_cache=False,
                )

            sample_payload: dict[str, Any] = {
                "record": record,
                "input_ids": encoded["input_ids"].detach().cpu().to(torch.int32),
                "router_topk": state.router_topk,
                "mtp_shapes": state.mtp_shapes,
            }
            if capture_scores:
                sample_payload["router_scores"] = state.router_scores
            if capture_hidden_states == "last" and getattr(outputs, "hidden_states", None):
                sample_payload["last_hidden_state"] = outputs.hidden_states[-1].detach().cpu()
            if native_mtp_runner is not None:
                if "last_hidden_state" not in sample_payload:
                    msg = "Cannot compute native MTP router without `last_hidden_state`."
                    raise RuntimeError(msg)
                sample_payload.update(
                    _capture_native_mtp_router(
                        native_mtp_runner,
                        model_dir=resolve_path(model_id, base_dir=project_root),
                        input_ids=sample_payload["input_ids"],
                        last_hidden_state=sample_payload["last_hidden_state"],
                        top_k=top_k,
                        dtype=dtype,
                    )
                )

            torch.save(sample_payload, sample_file)
            manifest.write(
                json.dumps(
                    {
                        "sample_idx": sample_idx,
                        "record_id": record.get("id"),
                        "path": sample_file.name,
                        "num_tokens": int(encoded["input_ids"].shape[-1]),
                        "num_router_modules": len(state.router_topk),
                        "num_mtp_modules": len(state.mtp_shapes),
                        "has_native_mtp_router": "native_mtp_router_topk" in sample_payload,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            manifest.flush()
            print(
                f"{local_idx + 1}/{len(texts)} sample_{sample_idx:06d} "
                f"tokens={int(encoded['input_ids'].shape[-1])}",
                flush=True,
            )

            for handle in handles:
                handle.remove()

    return manifest_path
