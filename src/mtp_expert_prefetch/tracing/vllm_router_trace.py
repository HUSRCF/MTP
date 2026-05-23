from __future__ import annotations

import gc
import hashlib
import functools
import importlib.util
import importlib
import inspect
import json
import os
import sys
import contextvars
from dataclasses import dataclass, field, replace
from pathlib import Path
import time
from typing import Any, Iterable, Protocol

import torch

from mtp_expert_prefetch.runtime.admission import AdmissionDecisionMasks
from mtp_expert_prefetch.runtime.descriptor_order import (
    DescriptorOrderReport,
    build_layer_prior_plan_report_from_router_topk,
    hash_ints,
    hash_layer_tile_prior,
)
from mtp_expert_prefetch.runtime.descriptor_order_gate import (
    DescriptorOrderEvidenceKey,
    DescriptorOrderExecutionEvidence,
    DescriptorOrderRuntimeGate,
    load_descriptor_order_consumer_evidence,
)
from mtp_expert_prefetch.runtime.cache_manager import (
    ControlledPremapAddressManager,
    PremapRealDescriptorHandle,
)
from mtp_expert_prefetch.runtime.online_shadow import OnlineShadowLogger
from mtp_expert_prefetch.runtime.premap import (
    ExpertPrefetchDescriptor,
    prepare_premap_address_plan,
)
from mtp_expert_prefetch.runtime.shadow_controller import RuntimeShadowController
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowDescriptorPrelaunchAssertEvent,
    ShadowDescriptorSummaryMinEvent,
    ShadowEventId,
    ShadowOutcomeAggregateEvent,
    ShadowOutcomeEvent,
    ShadowPolicyConfig,
    ShadowPremapConsumerMappingEvent,
    ShadowSummaryEvent,
    aggregate_shadow_events,
    read_shadow_jsonl,
)
from mtp_expert_prefetch.runtime.tile_order import (
    LayerTilePrior,
    TileRequest,
    load_layer_tile_prior,
)
from mtp_expert_prefetch.tracing.router_mtp import _load_trace_texts
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path


class RouterShadowOutcomeSink(Protocol):
    def write_outcome(self, event: ShadowOutcomeEvent) -> None: ...


_WNA16_RUNTIME_OVERRIDE_KEYS = (
    "BLOCK_SIZE_M",
    "GROUP_SIZE_M",
    "SPLIT_K",
    "num_warps",
    "num_stages",
)

_ATTENTION_HANDOFF_COMPONENT_PREFIX = "attention_linear_handoff_"
_ATTENTION_HANDOFF_COMPONENTS = (
    "attention_linear_handoff_linear_proj_total",
    "attention_linear_handoff_norm",
    "attention_linear_handoff_core_total",
    "attention_linear_handoff_core_decode_non_spec",
    "attention_linear_handoff_conv_update",
    "attention_linear_handoff_recurrent",
    "attention_linear_handoff_core_post_layout",
    "attention_linear_handoff_out_proj",
)

_PREMAP_DESCRIPTOR_PREP_EXECUTION_MODES = frozenset(
    {"readonly_descriptor_address_object"}
)


def _normalize_premap_descriptor_prep_execution_mode(raw: Any) -> str | None:
    mode = str(raw or "off").strip().lower()
    if mode in {"", "off", "none", "false", "0"}:
        return None
    if mode not in _PREMAP_DESCRIPTOR_PREP_EXECUTION_MODES:
        msg = (
            "Unsupported premap_descriptor_prep_execution_mode="
            f"{raw!r}; supported modes are "
            f"{sorted(_PREMAP_DESCRIPTOR_PREP_EXECUTION_MODES)}."
        )
        raise ValueError(msg)
    return mode

RUNTIME_SHADOW_AGGREGATE_PERFORMANCE_KEYS = (
    "outcome_aggregate_count",
    "descriptor_summary_min_count",
    "premap_summary_count",
    "premap_summary_descriptor_count",
    "premap_summary_payload_bytes",
    "premap_summary_actual_bytes",
    "premap_address_manager_count",
    "premap_address_resident_count_max",
    "premap_address_resident_descriptor_bytes_max",
    "premap_address_prepared_descriptor_actual_bytes_max",
    "premap_address_reused_count",
    "premap_address_evicted_count",
    "premap_address_reuse_rate_mean",
    "premap_address_eviction_pressure_mean",
    "premap_consumer_mapping_count",
    "premap_consumer_address_hit_rate",
    "premap_consumer_descriptor_handle_hit_rate",
    "premap_consumer_parity_ok_rate",
    "premap_consumer_descriptor_handle_parity_ok_rate",
    "premap_consumer_prelaunch_boundary_checked_count",
    "premap_consumer_prelaunch_boundary_aligned_count",
    "premap_consumer_prelaunch_boundary_aligned_rate",
    "premap_consumer_prelaunch_handle_available_count",
    "premap_consumer_prelaunch_handle_available_rate",
    "premap_consumer_prelaunch_block_count",
    "premap_consumer_prelaunch_block_size_max",
    "premap_consumer_prelaunch_unique_expert_count",
    "premap_consumer_lookup_after_prepare_rate",
    "premap_consumer_real_descriptor_handle_hit_count",
    "premap_consumer_real_descriptor_handle_miss_count",
    "premap_consumer_real_descriptor_handle_hit_rate",
    "premap_consumer_real_descriptor_handle_available_rate",
    "premap_consumer_real_descriptor_handle_packed_weight_hit_count",
    "premap_consumer_real_descriptor_handle_packed_weight_miss_count",
    "premap_consumer_real_descriptor_handle_scale_metadata_hit_count",
    "premap_consumer_real_descriptor_handle_scale_metadata_miss_count",
    "premap_consumer_real_descriptor_handle_aux_metadata_hit_count",
    "premap_consumer_real_descriptor_handle_aux_metadata_miss_count",
    "premap_consumer_real_descriptor_handle_resolver_disabled_count",
    "premap_consumer_real_descriptor_handle_consumer_layer_missing_count",
    "premap_consumer_real_descriptor_handle_expert_map_miss_count",
    "premap_consumer_real_descriptor_handle_no_handle_parts_count",
    "premap_consumer_real_descriptor_handle_new_binding_count",
    "premap_consumer_real_descriptor_handle_reused_binding_count",
    "premap_consumer_real_descriptor_handle_binding_mismatch_count",
    "premap_consumer_real_descriptor_handle_for_address_miss_count",
    "premap_consumer_readonly_lookup_count",
    "premap_consumer_readonly_handle_hit_count",
    "premap_consumer_readonly_handle_miss_count",
    "premap_consumer_readonly_handle_hit_rate",
    "premap_consumer_readonly_evicted_before_consume_count",
    "premap_consumer_readonly_evicted_before_consume_rate",
    "premap_consumer_readonly_stale_handle_count",
    "premap_consumer_readonly_stale_handle_rate",
    "premap_consumer_readonly_handle_parity_ok_rate",
    "premap_consumer_descriptor_prep_lookup_count",
    "premap_consumer_descriptor_prep_attempted_count",
    "premap_consumer_descriptor_prep_executed_count",
    "premap_consumer_descriptor_prep_handle_count",
    "premap_consumer_descriptor_prep_missing_handle_count",
    "premap_consumer_descriptor_prep_handle_hit_rate",
    "premap_consumer_descriptor_prep_descriptor_ptr_count",
    "premap_consumer_descriptor_prep_packed_weight_descriptor_count",
    "premap_consumer_descriptor_prep_scale_metadata_handle_count",
    "premap_consumer_descriptor_prep_real_handle_count",
    "premap_consumer_descriptor_prep_real_handle_miss_count",
    "premap_consumer_descriptor_prep_real_handle_hit_rate",
    "premap_consumer_descriptor_prep_real_handle_backed_count",
    "premap_consumer_descriptor_prep_real_handle_backed_rate",
    "premap_consumer_descriptor_prep_consumer_object_count",
    "premap_consumer_descriptor_prep_consumer_object_rate",
    "premap_consumer_descriptor_prep_consumer_object_read_lookup_count",
    "premap_consumer_descriptor_prep_consumer_object_read_hit_count",
    "premap_consumer_descriptor_prep_consumer_object_read_miss_count",
    "premap_consumer_descriptor_prep_consumer_object_stale_count",
    "premap_consumer_descriptor_prep_consumer_object_read_hit_rate",
    "premap_consumer_descriptor_prep_consumer_object_stale_rate",
    "premap_consumer_descriptor_prep_consumer_object_read_ok_rate",
    "premap_consumer_descriptor_prep_consumer_shim_executed_count",
    "premap_consumer_descriptor_prep_consumer_shim_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_ok_rate",
    "premap_consumer_descriptor_prep_consumer_shim_object_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_checked_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_missing_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_mismatch_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_violation_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_rate",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_rate",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel_count",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_bytes",
    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_violation_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_rate",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_checked_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_missing_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_mismatch_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes",
    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_violation_count",
    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_violation_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count",
    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count",
    "premap_consumer_descriptor_prep_execution_ok_rate",
    "premap_consumer_descriptor_prep_execution_ok_attempted_rate",
    "premap_consumer_descriptor_prep_blocked_count",
    "premap_consumer_descriptor_prep_blocked_rate",
    "premap_consumer_descriptor_prep_blocked_attempted_rate",
    "premap_consumer_error_count",
    "premap_consumer_payload_violation_count",
    "premap_consumer_router_change_violation_count",
    "premap_consumer_descriptor_order_change_violation_count",
    "premap_consumer_ready_credit_violation_count",
)


def _add_runtime_shadow_aggregate_to_performance(
    performance: dict[str, Any],
    aggregate: dict[str, Any],
) -> None:
    for key in RUNTIME_SHADOW_AGGREGATE_PERFORMANCE_KEYS:
        if key in aggregate:
            performance[f"runtime_shadow_aggregate_{key}"] = aggregate[key]


_ATTENTION_HANDOFF_COMPONENT_INDEX = {
    name: idx for idx, name in enumerate(_ATTENTION_HANDOFF_COMPONENTS)
}


_SHARED_EXPERT_OUTPUT_GATE_FUSED_KERNEL: Any | None = None


class SharedExpertFusedGateUnsupportedError(RuntimeError):
    """Raised when the narrow fused shared-gate kernel cannot preserve semantics."""


def _signature_cache_key(callable_obj: Any) -> Any:
    return getattr(callable_obj, "__func__", callable_obj)


@functools.lru_cache(maxsize=256)
def _supports_var_kwargs(callable_key: Any) -> bool:
    try:
        signature = inspect.signature(callable_key)
    except (TypeError, ValueError):
        return True
    return any(
        param.kind is inspect.Parameter.VAR_KEYWORD
        for param in signature.parameters.values()
    )


@functools.lru_cache(maxsize=256)
def _supported_kwarg_names(callable_key: Any) -> frozenset[str] | None:
    try:
        signature = inspect.signature(callable_key)
    except (TypeError, ValueError):
        return None
    if any(
        param.kind is inspect.Parameter.VAR_KEYWORD
        for param in signature.parameters.values()
    ):
        return None
    return frozenset(signature.parameters)


def _filter_supported_kwargs(callable_obj: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    if not kwargs:
        return {}
    key = _signature_cache_key(callable_obj)
    try:
        if _supports_var_kwargs(key):
            return kwargs
        supported = _supported_kwarg_names(key)
    except TypeError:
        try:
            signature = inspect.signature(callable_obj)
        except (TypeError, ValueError):
            return kwargs
        parameters = signature.parameters
        if any(
            param.kind is inspect.Parameter.VAR_KEYWORD
            for param in parameters.values()
        ):
            return kwargs
        return {key: value for key, value in kwargs.items() if key in parameters}
    if supported is None:
        return kwargs
    return {key: value for key, value in kwargs.items() if key in supported}


def _call_with_supported_kwargs(callable_obj: Any, /, *args: Any, **kwargs: Any) -> Any:
    return callable_obj(*args, **_filter_supported_kwargs(callable_obj, kwargs))


def _split_optional_input_ids(
    extra_args: tuple[Any, ...],
    extra_kwargs: dict[str, Any],
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    input_ids = extra_kwargs.get("input_ids")
    remaining_args = extra_args
    if extra_args:
        positional_input_ids = extra_args[0]
        remaining_args = extra_args[1:]
        if input_ids is None and positional_input_ids is not None:
            input_ids = positional_input_ids
    if input_ids is None:
        return remaining_args, extra_kwargs
    kwargs = dict(extra_kwargs)
    kwargs["input_ids"] = input_ids
    return remaining_args, kwargs


def _get_shared_expert_output_gate_fused_kernel() -> tuple[Any, Any]:
    global _SHARED_EXPERT_OUTPUT_GATE_FUSED_KERNEL
    from vllm.triton_utils import tl, triton

    if _SHARED_EXPERT_OUTPUT_GATE_FUSED_KERNEL is None:

        @triton.jit
        def _kernel(
            hidden_ptr,
            gate_weight_ptr,
            out_ptr,
            dst_ptr,
            hidden_size: tl.constexpr,
            stride_hidden_token: tl.constexpr,
            stride_hidden_dim: tl.constexpr,
            stride_out_token: tl.constexpr,
            stride_out_dim: tl.constexpr,
            stride_dst_token: tl.constexpr,
            stride_dst_dim: tl.constexpr,
            BLOCK_H: tl.constexpr,
        ):
            token = tl.program_id(0)
            offsets = tl.arange(0, BLOCK_H)
            mask = offsets < hidden_size
            hidden = tl.load(
                hidden_ptr + token * stride_hidden_token + offsets * stride_hidden_dim,
                mask=mask,
                other=0.0,
            ).to(tl.float32)
            weight = tl.load(gate_weight_ptr + offsets, mask=mask, other=0.0).to(
                tl.float32
            )
            gate = tl.sum(hidden * weight, axis=0)
            gate = 1.0 / (1.0 + tl.exp(-gate))
            out_values = tl.load(
                out_ptr + token * stride_out_token + offsets * stride_out_dim,
                mask=mask,
                other=0.0,
            )
            scaled = out_values.to(tl.float32) * gate
            tl.store(
                dst_ptr + token * stride_dst_token + offsets * stride_dst_dim,
                scaled,
                mask=mask,
            )

        _SHARED_EXPERT_OUTPUT_GATE_FUSED_KERNEL = _kernel

    return _SHARED_EXPERT_OUTPUT_GATE_FUSED_KERNEL, triton


def _run_shared_expert_output_gate_fused_triton(
    *,
    hidden_states: torch.Tensor,
    out: torch.Tensor,
    expert_gate: Any,
) -> torch.Tensor:
    weight = getattr(expert_gate, "weight", None)
    bias = getattr(expert_gate, "bias", None)
    if weight is None or bias is not None:
        raise SharedExpertFusedGateUnsupportedError(
            "fused shared gate requires a bias-free weight parameter"
        )
    if hidden_states.dim() != 2 or out.dim() != 2:
        raise SharedExpertFusedGateUnsupportedError(
            "fused shared gate requires rank-2 hidden/out tensors"
        )
    if hidden_states.shape != out.shape:
        raise SharedExpertFusedGateUnsupportedError(
            "fused shared gate requires hidden/out tensors with matching shape"
        )
    if weight.numel() != hidden_states.shape[-1]:
        raise SharedExpertFusedGateUnsupportedError(
            "fused shared gate weight size does not match hidden dimension"
        )
    if hidden_states.device.type != "cuda" or out.device.type != "cuda":
        raise SharedExpertFusedGateUnsupportedError(
            "fused shared gate requires CUDA/HIP tensors"
        )

    kernel, triton = _get_shared_expert_output_gate_fused_kernel()
    gate_weight = weight.reshape(-1)
    dst = torch.empty_like(out)
    hidden_size = int(hidden_states.shape[-1])
    block_h = int(triton.next_power_of_2(hidden_size))
    num_warps = 8 if hidden_size >= 2048 else 4
    kernel[(int(hidden_states.shape[0]),)](
        hidden_states,
        gate_weight,
        out,
        dst,
        hidden_size,
        hidden_states.stride(0),
        hidden_states.stride(1),
        out.stride(0),
        out.stride(1),
        dst.stride(0),
        dst.stride(1),
        BLOCK_H=block_h,
        num_warps=num_warps,
        num_stages=3,
    )
    return dst


def _shared_expert_output_gate_postprocess_mode(
    recorder: VllmRouterRecorder | None,
) -> str:
    if recorder is None:
        return "default"
    return str(
        recorder.shadow_shared_expert_output_gate_postprocess or "default"
    ).strip().lower()


def _shared_expert_output_gate_ablation_mode(
    recorder: VllmRouterRecorder | None,
) -> str:
    if recorder is None:
        return "off"
    return str(recorder.shadow_shared_expert_output_gate_ablation or "off").strip().lower()


def _shared_expert_custom_gate_enabled(
    recorder: VllmRouterRecorder | None,
) -> bool:
    if recorder is None:
        return False
    postprocess = _shared_expert_output_gate_postprocess_mode(recorder)
    ablation = _shared_expert_output_gate_ablation_mode(recorder)
    return postprocess in {"inplace", "fused_triton", "triton_fused"} or ablation in {
        "unity",
        "identity",
        "skip",
        "disabled",
    }


def _shared_expert_fused_gate_unsupported(exc: RuntimeError) -> bool:
    return isinstance(exc, SharedExpertFusedGateUnsupportedError)


def _shared_expert_fused_gate_fallbackable(exc: RuntimeError) -> bool:
    """Whether a diagnostic fused-gate failure may fall back to default math."""

    if _shared_expert_fused_gate_unsupported(exc):
        return True
    message = str(exc).lower()
    if "out of memory" in message or "hiperroroutofmemory" in message:
        return False
    return True


def _run_shared_expert_output_gate_default_postprocess(
    *,
    hidden_states: torch.Tensor,
    out: torch.Tensor,
    expert_gate: Any,
    postprocess: str,
) -> torch.Tensor:
    gate_out = _unwrap_vllm_projection_output(expert_gate(hidden_states))
    if postprocess == "inplace":
        gate_out.sigmoid_()
        out.mul_(gate_out)
        return out
    return torch.sigmoid(gate_out) * out


def _unwrap_vllm_projection_output(value: Any) -> torch.Tensor:
    if isinstance(value, torch.Tensor):
        return value
    if isinstance(value, tuple) and value and isinstance(value[0], torch.Tensor):
        return value[0]
    raise TypeError(
        "expected vLLM projection output to be a tensor or a tuple whose first "
        "element is a tensor"
    )


def _patch_missing_vllm_activation_ops_for_trace() -> bool:
    """Install native activation fallbacks when vLLM C ops are unavailable.

    This is a diagnostic escape hatch for broken local environments. It keeps
    the trace path runnable without editing site-packages, but any timing from
    a run using this fallback is not production-like.
    """

    patched = False
    if not hasattr(torch.ops._C, "silu_and_mul"):
        import torch.nn.functional as F

        def silu_and_mul_fallback(out: torch.Tensor, x: torch.Tensor) -> None:
            d = x.shape[-1] // 2
            out.copy_(F.silu(x[..., :d]) * x[..., d:])

        torch.ops._C.silu_and_mul = silu_and_mul_fallback
        patched = True

    if not hasattr(torch.ops._C, "gelu_and_mul"):
        import torch.nn.functional as F

        def gelu_and_mul_fallback(out: torch.Tensor, x: torch.Tensor) -> None:
            d = x.shape[-1] // 2
            out.copy_(F.gelu(x[..., :d]) * x[..., d:])

        torch.ops._C.gelu_and_mul = gelu_and_mul_fallback
        patched = True

    if not hasattr(torch.ops, "_moe_C"):
        torch.ops._moe_C = type("_MoeOpsFallbackNamespace", (), {})()
        patched = True

    if not hasattr(torch.ops._moe_C, "topk_softmax"):

        def topk_softmax_fallback(
            topk_weights: torch.Tensor,
            topk_ids: torch.Tensor,
            token_expert_indices: torch.Tensor,
            gating_output: torch.Tensor,
            renormalize: bool = False,
            e_score_correction_bias: torch.Tensor | None = None,
        ) -> None:
            scores = torch.softmax(gating_output.float(), dim=-1)
            if e_score_correction_bias is not None:
                scores = scores + e_score_correction_bias.float()
            values, indices = torch.topk(scores, k=topk_weights.shape[-1], dim=-1)
            if renormalize:
                values = values / values.sum(dim=-1, keepdim=True).clamp_min(1.0e-20)
            topk_weights.copy_(values.to(topk_weights.dtype))
            topk_ids.copy_(indices.to(topk_ids.dtype))
            token_expert_indices.copy_(
                torch.arange(
                    int(topk_weights.shape[-1]),
                    device=token_expert_indices.device,
                    dtype=token_expert_indices.dtype,
                )
                .view(1, -1)
                .expand_as(token_expert_indices)
            )

        torch.ops._moe_C.topk_softmax = topk_softmax_fallback
        patched = True

    if not hasattr(torch.ops._moe_C, "topk_sigmoid"):

        def topk_sigmoid_fallback(
            topk_weights: torch.Tensor,
            topk_ids: torch.Tensor,
            token_expert_indices: torch.Tensor,
            gating_output: torch.Tensor,
            renormalize: bool = False,
            e_score_correction_bias: torch.Tensor | None = None,
        ) -> None:
            scores = torch.sigmoid(gating_output.float())
            if e_score_correction_bias is not None:
                scores = scores + e_score_correction_bias.float()
            values, indices = torch.topk(scores, k=topk_weights.shape[-1], dim=-1)
            if renormalize:
                values = values / values.sum(dim=-1, keepdim=True).clamp_min(1.0e-20)
            topk_weights.copy_(values.to(topk_weights.dtype))
            topk_ids.copy_(indices.to(topk_ids.dtype))
            token_expert_indices.copy_(
                torch.arange(
                    int(topk_weights.shape[-1]),
                    device=token_expert_indices.device,
                    dtype=token_expert_indices.dtype,
                )
                .view(1, -1)
                .expand_as(token_expert_indices)
            )

        torch.ops._moe_C.topk_sigmoid = topk_sigmoid_fallback
        patched = True

    try:
        from vllm.model_executor.layers import activation
    except Exception:
        return patched

    original_init = getattr(activation.SiluAndMul, "__init__", None)
    if callable(original_init) and not getattr(
        activation.SiluAndMul,
        "_mtp_missing_op_fallback_patched",
        False,
    ):

        def silu_init_with_fallback(self: Any, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            if not hasattr(self, "op"):
                self._forward_method = self.forward_native

        activation.SiluAndMul.__init__ = silu_init_with_fallback
        activation.SiluAndMul._mtp_missing_op_fallback_patched = True
        patched = True

    return patched


@dataclass
class VllmRouterCall:
    layer_id: int | None
    call_index: int
    num_tokens: int
    topk_ids: torch.Tensor
    topk_weights: torch.Tensor
    oracle_topk_ids: torch.Tensor | None = None
    oracle_topk_weights: torch.Tensor | None = None
    router_input_hidden: torch.Tensor | None = None


@dataclass
class VllmRouterRecorder:
    top_k: int
    capture_router_input_hidden: bool = False
    shadow_outcome_sink: RouterShadowOutcomeSink | None = None
    shadow_emit_transition_summary: bool = False
    shadow_num_experts: int = 256
    shadow_transition_topk_count: int | None = None
    shadow_transition_summary_mode: str = "previous_topk"
    shadow_transition_matrix: torch.Tensor | None = None
    shadow_emit_premap_summary: bool = False
    shadow_emit_transition_premap_summary: bool = False
    shadow_premap_policy: str = "premap_only"
    shadow_premap_source: str = "current_router_topk_premap_shadow"
    shadow_transition_premap_source: str = "previous_token_transition_premap_shadow"
    shadow_premap_descriptor_bytes: int = 4_096
    shadow_emit_premap_address_manager_counters: bool = False
    shadow_premap_address_manager_capacity: int | None = None
    shadow_premap_summary_sample_period: int = 1
    shadow_emit_premap_consumer_mapping: bool = False
    shadow_premap_consumer_mapping_mode: str = "noop_assertion"
    shadow_premap_consumer_mapping_source: str = "fused_moe_prepare_expert_assignment"
    shadow_premap_consumer_resolve_real_handles: bool = False
    shadow_premap_consumer_mapping_sample_period: int = 1
    shadow_premap_consumer_readonly_gate_required: bool = False
    shadow_premap_consumer_readonly_gate_id: str | None = None
    shadow_premap_consumer_readonly_gate_path: str | None = None
    shadow_premap_consumer_readonly_gate_passed: bool | None = None
    shadow_premap_descriptor_prep_execution_mode: str = "off"
    shadow_premap_address_namespace: str = "expert_weight_descriptor"
    shadow_premap_priority: int = 2
    shadow_transition_premap_priority: int = 3
    shadow_premap_event_token_index: int = -1
    shadow_emit_descriptor_order_summary: bool = False
    shadow_descriptor_order_prior: LayerTilePrior | None = None
    shadow_descriptor_order_prior_id: str | None = None
    shadow_descriptor_order_prior_hash: str | None = None
    shadow_descriptor_order_tiles_per_expert: int = 1
    shadow_descriptor_order_token_window_size: int = 0
    shadow_descriptor_order_cache_sizes: tuple[int, ...] = (8, 16, 32)
    shadow_descriptor_order_top_k: int = 8
    shadow_descriptor_order_top_utility_override: int = 0
    shadow_descriptor_order_metrics_mode: str = "full"
    shadow_descriptor_order_event_mode: str = "summary"
    shadow_descriptor_order_execution_mode: str = "two_level_group_plan"
    shadow_descriptor_order_mapping_assertion_mode: str = "off"
    shadow_descriptor_order_mapping_source: str = "base_router_select_experts_topk"
    shadow_descriptor_order_prelaunch_assertion_mode: str = "off"
    shadow_descriptor_order_prelaunch_mapping_source: str = (
        "moe_runner_quant_method_apply_topk"
    )
    shadow_descriptor_order_emit_consumer_handle_events: bool = True
    shadow_descriptor_order_reorder_mvp_enabled: bool = False
    shadow_descriptor_order_reorder_mvp_apply_mode: str = "dry_run"
    shadow_descriptor_order_reorder_mvp_attribution_mode: str = "full"
    shadow_descriptor_order_reorder_mvp_require_profitable: bool = True
    shadow_descriptor_order_reorder_mvp_layer_allowlist: tuple[int, ...] | None = None
    shadow_descriptor_order_groups_per_cta: int = 8
    shadow_descriptor_order_tile_elems: int = 1024
    _shadow_premap_address_manager: ControlledPremapAddressManager | None = field(
        default=None,
        init=False,
        repr=False,
    )
    shadow_descriptor_order_device: int | None = None
    shadow_descriptor_order_runtime_gate: DescriptorOrderRuntimeGate | None = None
    shadow_descriptor_order_evidence: (
        dict[DescriptorOrderEvidenceKey, DescriptorOrderExecutionEvidence] | None
    ) = None
    shadow_descriptor_order_evidence_cache_flush_elems: int = 0
    shadow_descriptor_order_same_multiset_evidence: bool | None = None
    shadow_descriptor_order_checksum_delta_evidence: float | None = None
    shadow_descriptor_order_event_token_index: int = -1
    shadow_wna16_config_override: dict[str, Any] | None = None
    shadow_wna16_config_override_preserve_dynamic_nk: bool = True
    shadow_wna16_config_override_max_tokens: int | None = None
    shadow_wna16_config_override_route_product: int | None = 8
    shadow_wna16_config_override_target_top_k: int | None = None
    shadow_wna16_kernel_timing_mode: str = "host"
    shadow_emit_wna16_kernel_timing: bool = False
    shadow_emit_descriptor_layer_timing: bool = True
    shadow_emit_decoder_layer_timing: bool = False
    shadow_emit_decoder_component_timing: bool = True
    shadow_decoder_component_logging_mode: str = "rows"
    shadow_emit_moe_substage_timing: bool = True
    shadow_moe_substage_logging_mode: str = "rows"
    shadow_moe_substage_sample_period: int = 1
    shadow_emit_engine_timing: bool = False
    shadow_moe_source_timing_mode: str = "full"
    shadow_decoder_source_timing_mode: str = "off"
    shadow_shared_experts_force_aux_stream: bool = False
    shadow_shared_expert_output_gate_ablation: str = "off"
    shadow_shared_expert_output_gate_postprocess: str = "default"
    shadow_record_router_topk: bool = True
    shadow_outcome_logging_mode: str = "full"
    request_id: str = "vllm"
    sequence_id: int = 0
    token_offset: int = 0
    calls: list[VllmRouterCall] = field(default_factory=list)
    _last_descriptor_mapping_by_layer: dict[int, dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )
    _last_descriptor_consumer_handle_by_layer: dict[int, dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )
    _last_premap_address_mapping_by_layer: dict[int, dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )
    # Intentionally recorder/model-lifetime rather than clear()-lifetime:
    # clear() resets per-sample trace buffers, but live vLLM/AWQ tensor handles
    # are runtime address signatures for the loaded model instance.  Keeping
    # this binding across samples lets the no-op consumer contract detect
    # unexpected handle churn or reallocation during the same recorder lifetime.
    _premap_real_handle_binding_by_address_key: dict[str, str] = field(
        default_factory=dict,
        repr=False,
    )
    _premap_consumer_mapping_call_count: int = field(default=0, repr=False)
    _premap_summary_call_count: int = field(default=0, repr=False)
    _descriptor_order_prior_rank_tensor_cache: dict[tuple[Any, ...], torch.Tensor] = (
        field(default_factory=dict, repr=False)
    )
    _descriptor_order_direct_placeholder_cache: dict[tuple[Any, ...], tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = (
        field(default_factory=dict, repr=False)
    )
    _decoder_component_aggregate: dict[tuple[Any, ...], dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )
    _decoder_component_counter_aggregate: dict[tuple[Any, ...], dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )
    _moe_substage_aggregate: dict[tuple[Any, ...], dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )
    _moe_substage_sample_counters: dict[tuple[Any, ...], int] = field(
        default_factory=dict,
        repr=False,
    )

    def clear(self) -> None:
        self.calls.clear()
        self._last_descriptor_mapping_by_layer.clear()
        self._last_descriptor_consumer_handle_by_layer.clear()
        self._last_premap_address_mapping_by_layer.clear()
        self._descriptor_order_prior_rank_tensor_cache.clear()
        self._descriptor_order_direct_placeholder_cache.clear()
        self._decoder_component_aggregate.clear()
        self._decoder_component_counter_aggregate.clear()
        self._moe_substage_aggregate.clear()
        self._moe_substage_sample_counters.clear()

    def apply_wna16_runtime_config_override(
        self,
        config: dict[str, Any],
        *,
        num_tokens: int | None = None,
        top_k: int | None = None,
        use_int8_w8a16: bool = False,
        use_int4_w4a16: bool = False,
        block_shape: list[int] | None = None,
    ) -> dict[str, Any]:
        override = self.shadow_wna16_config_override
        if not override:
            return config
        unsupported = sorted(
            key for key in override if key not in _WNA16_RUNTIME_OVERRIDE_KEYS
        )
        if unsupported:
            raise ValueError(
                "Unsupported WNA16 runtime override keys: "
                + ", ".join(unsupported)
                + ". Only "
                + ", ".join(_WNA16_RUNTIME_OVERRIDE_KEYS)
                + " are allowed."
            )
        max_tokens = self.shadow_wna16_config_override_max_tokens
        if (
            max_tokens is not None
            and max_tokens > 0
            and num_tokens is not None
            and int(num_tokens) > int(max_tokens)
        ):
            return config
        route_product = self.shadow_wna16_config_override_route_product
        target_top_k = self.shadow_wna16_config_override_target_top_k
        if target_top_k is not None and top_k is None:
            return config
        if top_k is not None:
            if target_top_k is not None and int(top_k) != int(target_top_k):
                return config
            if int(top_k) not in {1, 8}:
                return config
            if (
                route_product is not None
                and route_product > 0
                and num_tokens is not None
                and int(num_tokens) * int(top_k) != int(route_product)
            ):
                return config
        if not (bool(use_int8_w8a16) or bool(use_int4_w4a16)):
            return config
        if block_shape is None:
            return config
        patched = dict(config)
        for key in _WNA16_RUNTIME_OVERRIDE_KEYS:
            value = override.get(key)
            if value is not None:
                patched[key] = int(value)
        return patched

    def record(self, *, layer_id: int | None, router_logits: torch.Tensor) -> None:
        if not self.shadow_record_router_topk:
            return
        logits = router_logits.detach().float()
        weights = torch.softmax(logits, dim=-1)
        topk_weights, topk_ids = torch.topk(weights, k=self.top_k, dim=-1)
        self.record_topk(
            layer_id=layer_id,
            topk_ids=topk_ids,
            topk_weights=topk_weights,
            oracle_router_logits=router_logits,
        )

    def record_topk(
        self,
        *,
        layer_id: int | None,
        topk_ids: torch.Tensor,
        topk_weights: torch.Tensor,
        oracle_router_logits: torch.Tensor | None = None,
        router_input_hidden: torch.Tensor | None = None,
    ) -> None:
        oracle_topk_ids = None
        oracle_topk_weights = None
        if oracle_router_logits is not None:
            oracle_weights = torch.softmax(oracle_router_logits.detach().float(), dim=-1)
            oracle_topk_weights, oracle_topk_ids = torch.topk(
                oracle_weights,
                k=self.top_k,
                dim=-1,
            )
        captured_hidden = None
        if self.capture_router_input_hidden and router_input_hidden is not None:
            captured_hidden = router_input_hidden.detach().cpu().to(torch.bfloat16)
        self.calls.append(
            VllmRouterCall(
                layer_id=layer_id,
                call_index=len(self.calls),
                num_tokens=int(topk_ids.shape[0]),
                topk_ids=topk_ids.detach().cpu().to(torch.int16),
                topk_weights=topk_weights.detach().cpu().to(torch.float32),
                oracle_topk_ids=(
                    oracle_topk_ids.detach().cpu().to(torch.int16)
                    if oracle_topk_ids is not None
                    else None
                ),
                oracle_topk_weights=(
                    oracle_topk_weights.detach().cpu().to(torch.float32)
                    if oracle_topk_weights is not None
                    else None
                ),
                router_input_hidden=captured_hidden,
            )
        )
        if self.shadow_outcome_sink is not None and layer_id is not None:
            self._write_shadow_outcomes(
                layer_id=int(layer_id),
                topk_ids=topk_ids,
                topk_weights=topk_weights,
            )

    def _write_shadow_outcomes(
        self,
        *,
        layer_id: int,
        topk_ids: torch.Tensor,
        topk_weights: torch.Tensor,
    ) -> None:
        from mtp_expert_prefetch.runtime.shadow_log import ShadowEventId

        outcome_mode = self._resolved_outcome_logging_mode()
        if self.shadow_emit_transition_summary:
            # Transition summaries require per-token outcomes for same-event
            # ready-mask joins. Keep the debug/full path in that mode.
            outcome_mode = "full"
        if (
            outcome_mode == "off"
            and not self.shadow_emit_descriptor_order_summary
            and not self.shadow_emit_premap_summary
            and not self.shadow_emit_transition_premap_summary
            and not self.shadow_emit_transition_summary
        ):
            return

        ids = topk_ids.detach().cpu().to(torch.long)
        weights = topk_weights.detach().cpu().to(torch.float32)
        if ids.ndim != 2 or weights.shape != ids.shape:
            return
        if outcome_mode == "full":
            self._write_full_shadow_outcomes(
                layer_id=layer_id,
                ids=ids,
                weights=weights,
            )
        elif outcome_mode == "aggregate":
            self._write_aggregate_shadow_outcome(
                layer_id=layer_id,
                ids=ids,
                weights=weights,
            )
        elif outcome_mode == "off":
            pass
        else:
            msg = f"Unsupported shadow_outcome_logging_mode: {outcome_mode}"
            raise ValueError(msg)
        if self.shadow_emit_descriptor_order_summary:
            self._write_current_router_descriptor_order_summary(
                layer_id=layer_id,
                topk_ids=ids,
                topk_weights=weights,
            )
        if self.shadow_emit_premap_summary:
            self._write_current_router_premap_summary(
                layer_id=layer_id,
                topk_ids=ids,
                topk_weights=weights,
            )
        if self.shadow_emit_transition_premap_summary:
            self._write_previous_token_transition_premap_summaries(
                layer_id=layer_id,
                topk_ids=ids,
                topk_weights=weights,
            )

    def _resolved_outcome_logging_mode(self) -> str:
        mode = str(self.shadow_outcome_logging_mode or "full").strip().lower()
        aliases = {
            "none": "off",
            "false": "off",
            "0": "off",
            "true": "full",
            "1": "full",
        }
        return aliases.get(mode, mode)

    def _write_full_shadow_outcomes(
        self,
        *,
        layer_id: int,
        ids: torch.Tensor,
        weights: torch.Tensor,
    ) -> None:
        assert self.shadow_outcome_sink is not None
        for token_idx in range(int(ids.shape[0])):
            if self.shadow_emit_transition_summary and token_idx > 0:
                self._write_previous_token_transition_summary(
                    layer_id=layer_id,
                    token_idx=token_idx,
                    previous_topk_ids=ids[token_idx - 1],
                    previous_topk_weights=weights[token_idx - 1],
                )
            token_ids = [int(value) for value in ids[token_idx].tolist()]
            token_weights = [float(value) for value in weights[token_idx].tolist()]
            total = float(sum(max(0.0, value) for value in token_weights))
            event = ShadowOutcomeEvent(
                event_id=ShadowEventId(
                    request_id=str(self.request_id),
                    sequence_id=int(self.sequence_id),
                    token_index=int(self.token_offset + token_idx),
                    layer=int(layer_id),
                ),
                true_topk_experts=token_ids,
                true_topk_weights=token_weights,
                full_fetch_used_count=0,
                metadata_later_used_count=0,
                premap_later_used_count=0,
                skip_would_have_used_count=0,
                covered_mass=0.0,
                miss_mass=total,
                top1_ready=False,
                weighted_top1_miss=float(token_weights[0]) if token_weights else 0.0,
            )
            self.shadow_outcome_sink.write_outcome(event)

    def _write_aggregate_shadow_outcome(
        self,
        *,
        layer_id: int,
        ids: torch.Tensor,
        weights: torch.Tensor,
    ) -> None:
        sink = self.shadow_outcome_sink
        if sink is None:
            return
        if not hasattr(sink, "write_outcome_aggregate"):
            msg = (
                "shadow_outcome_logging_mode='aggregate' requires a sink with "
                "write_outcome_aggregate(event)."
            )
            raise TypeError(msg)
        token_count = int(ids.shape[0])
        top_k = int(ids.shape[1]) if ids.ndim == 2 else 0
        token_start = int(self.token_offset)
        token_end = int(self.token_offset + token_count)
        top1_weight_sum = (
            float(weights[:, 0].sum().item()) if token_count > 0 and top_k > 0 else 0.0
        )
        event = ShadowOutcomeAggregateEvent(
            event_id=ShadowEventId(
                request_id=str(self.request_id),
                sequence_id=int(self.sequence_id),
                token_index=token_start,
                layer=int(layer_id),
            ),
            token_start=token_start,
            token_end=token_end,
            token_count=token_count,
            top_k=top_k,
            topk_entry_count=int(ids.numel()),
            routed_expert_count=int(torch.unique(ids).numel()),
            topk_weight_mass_sum=float(weights.clamp_min(0.0).sum().item()),
            top1_weight_sum=top1_weight_sum,
            top1_weight_mean=top1_weight_sum / max(1, token_count),
        )
        sink.write_outcome_aggregate(event)

    def _write_current_router_descriptor_order_summary(
        self,
        *,
        layer_id: int,
        topk_ids: torch.Tensor,
        topk_weights: torch.Tensor,
    ) -> None:
        """Emit a shadow-only descriptor-order summary for this router call.

        This path observes the true-router tile stream after routing is known.
        It does not alter execution order and does not participate in the
        action-summary/outcome ready-mask join.
        """

        sink = self.shadow_outcome_sink
        prior = self.shadow_descriptor_order_prior
        if sink is None or prior is None:
            return
        event_mode = self._resolved_descriptor_order_event_mode()
        if event_mode == "minimal":
            if not hasattr(sink, "write_descriptor_order_min_summary"):
                msg = (
                    "descriptor_order_event_mode='minimal' requires a sink with "
                    "write_descriptor_order_min_summary(event)."
                )
                raise TypeError(msg)
        elif event_mode == "summary":
            if not hasattr(sink, "write_descriptor_order_summary"):
                return
        else:
            msg = f"Unsupported descriptor_order_event_mode: {event_mode}"
            raise ValueError(msg)
        if not prior.order_for_layer(int(layer_id)):
            return
        if topk_ids.ndim != 2 or topk_weights.shape != topk_ids.shape:
            return

        total_start_ns = time.perf_counter_ns()
        stream_start_ns = total_start_ns
        ids = topk_ids.detach().cpu()
        weights = topk_weights.detach().cpu()
        stream_build_us = (time.perf_counter_ns() - stream_start_ns) / 1000.0
        prior_hash = self.shadow_descriptor_order_prior_hash or hash_layer_tile_prior(prior)
        prior_id = self.shadow_descriptor_order_prior_id or str(
            prior.metadata.get("experiment_id") or prior.score_name
        )
        descriptor_report, baseline_order_hash = build_layer_prior_plan_report_from_router_topk(
            layer_id=layer_id,
            topk_ids=ids,
            topk_weights=weights,
            prior=prior,
            prior_id=prior_id,
            prior_hash=prior_hash,
            tiles_per_expert=int(self.shadow_descriptor_order_tiles_per_expert),
            token_window_size=int(self.shadow_descriptor_order_token_window_size),
            top_utility_override=int(self.shadow_descriptor_order_top_utility_override),
            cache_sizes=self.shadow_descriptor_order_cache_sizes,
            tile_order_top_k=int(self.shadow_descriptor_order_top_k),
            metrics_mode=str(self.shadow_descriptor_order_metrics_mode),
        )
        if descriptor_report is None:
            return
        decision_us = (time.perf_counter_ns() - total_start_ns) / 1000.0
        counter_update_us = max(
            0.0,
            decision_us - stream_build_us - float(descriptor_report.order_build_us),
        )
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.shadow_descriptor_order_event_token_index),
            layer=int(layer_id),
        )
        if event_mode == "minimal":
            metrics = descriptor_report.metrics
            group_plan = metrics.get("group_plan", {})
            mapping_assertion = _descriptor_order_mapping_assertion_from_router_topk(
                mode=str(self.shadow_descriptor_order_mapping_assertion_mode),
                source=str(self.shadow_descriptor_order_mapping_source),
                topk_ids=ids,
                descriptor_report=descriptor_report,
                tiles_per_expert=int(self.shadow_descriptor_order_tiles_per_expert),
                token_window_size=int(self.shadow_descriptor_order_token_window_size),
            )
            group_count = int(group_plan.get("group_count", 0) or 0)
            if mapping_assertion:
                self._last_descriptor_mapping_by_layer[int(layer_id)] = dict(
                    mapping_assertion
                )
            groups_per_cta = max(1, int(self.shadow_descriptor_order_groups_per_cta))
            gate_decision = None
            gate_evidence = None
            if (
                self.shadow_descriptor_order_evidence is not None
                and self.shadow_descriptor_order_device is not None
            ):
                gate_evidence = self.shadow_descriptor_order_evidence.get(
                    (
                        int(self.shadow_descriptor_order_device),
                        int(self.shadow_descriptor_order_tile_elems),
                        int(groups_per_cta),
                        int(self.shadow_descriptor_order_evidence_cache_flush_elems),
                    )
                )
            same_multiset_evidence = self.shadow_descriptor_order_same_multiset_evidence
            checksum_delta_evidence = self.shadow_descriptor_order_checksum_delta_evidence
            if gate_evidence is not None:
                same_multiset_evidence = bool(gate_evidence.same_multiset)
                checksum_delta_evidence = gate_evidence.checksum_delta
            if self.shadow_descriptor_order_runtime_gate is not None:
                gate_decision = self.shadow_descriptor_order_runtime_gate.decide(
                    tile_elems=int(self.shadow_descriptor_order_tile_elems),
                    groups_per_cta=groups_per_cta,
                    device=self.shadow_descriptor_order_device,
                    execution_mode=str(self.shadow_descriptor_order_execution_mode),
                    group_count=group_count,
                    avg_group_size=(
                        float(group_plan.get("avg_group_size"))
                        if group_plan.get("avg_group_size") is not None
                        else None
                    ),
                    p95_group_size=(
                        float(group_plan.get("p95_group_size"))
                        if group_plan.get("p95_group_size") is not None
                        else None
                    ),
                    max_group_size=(
                        int(group_plan.get("max_group_size"))
                        if group_plan.get("max_group_size") is not None
                        else None
                    ),
                    same_multiset=same_multiset_evidence,
                    checksum_delta=checksum_delta_evidence,
                )
            sink.write_descriptor_order_min_summary(
                ShadowDescriptorSummaryMinEvent(
                    event_id=event_id,
                    descriptor_order_policy=descriptor_report.policy,
                    descriptor_order_prior_id=descriptor_report.prior_id,
                    descriptor_order_prior_hash=descriptor_report.prior_hash,
                    descriptor_order_metrics_mode=str(
                        metrics.get("metrics_mode", self.shadow_descriptor_order_metrics_mode)
                    ),
                    descriptor_tile_request_count=int(descriptor_report.descriptor_count),
                    descriptor_unique_b_tiles=int(metrics.get("unique_tiles_total", 0) or 0),
                    descriptor_window_count=int(metrics.get("window_count", 0) or 0),
                    descriptor_order_top_utility_override=(
                        descriptor_report.top_utility_override
                    ),
                    descriptor_order_execution_mode=str(
                        self.shadow_descriptor_order_execution_mode
                    ),
                    descriptor_group_plan_groups_per_cta=groups_per_cta,
                    descriptor_group_plan_group_count=group_count,
                    descriptor_group_plan_avg_group_size=(
                        float(group_plan.get("avg_group_size"))
                        if group_plan.get("avg_group_size") is not None
                        else None
                    ),
                    descriptor_group_plan_p95_group_size=(
                        float(group_plan.get("p95_group_size"))
                        if group_plan.get("p95_group_size") is not None
                        else None
                    ),
                    descriptor_group_plan_max_group_size=(
                        int(group_plan.get("max_group_size"))
                        if group_plan.get("max_group_size") is not None
                        else None
                    ),
                    descriptor_group_plan_cta_count=(
                        (group_count + groups_per_cta - 1) // groups_per_cta
                    ),
                    descriptor_order_gate_allow=(
                        bool(gate_decision.allow) if gate_decision is not None else None
                    ),
                    descriptor_order_gate_reason=(
                        gate_decision.reason if gate_decision is not None else None
                    ),
                    descriptor_order_gate_tile_elems=(
                        int(gate_decision.tile_elems) if gate_decision is not None else None
                    ),
                    descriptor_order_gate_device=(
                        gate_decision.device if gate_decision is not None else None
                    ),
                    descriptor_order_gate_evidence_found=(
                        gate_evidence is not None
                        if self.shadow_descriptor_order_evidence is not None
                        else None
                    ),
                    descriptor_order_gate_checksum_delta=(
                        gate_evidence.checksum_delta if gate_evidence is not None else None
                    ),
                    descriptor_order_gate_speedup_median_vs_no_order=(
                        gate_evidence.speedup_median_vs_no_order
                        if gate_evidence is not None
                        else None
                    ),
                    descriptor_order_mapping_assertion_mode=mapping_assertion.get("mode"),
                    descriptor_order_mapping_source=mapping_assertion.get("source"),
                    descriptor_order_mapping_same_multiset=mapping_assertion.get(
                        "same_multiset"
                    ),
                    descriptor_order_mapping_counts_match=mapping_assertion.get(
                        "counts_match"
                    ),
                    descriptor_order_mapping_tile_multiset_hash=mapping_assertion.get(
                        "tile_multiset_hash"
                    ),
                    descriptor_order_mapping_plan_tile_multiset_hash=mapping_assertion.get(
                        "plan_tile_multiset_hash"
                    ),
                    descriptor_order_mapping_request_count=mapping_assertion.get(
                        "request_count"
                    ),
                    descriptor_order_mapping_plan_request_count=mapping_assertion.get(
                        "plan_request_count"
                    ),
                    descriptor_order_mapping_group_count=mapping_assertion.get(
                        "group_count"
                    ),
                    descriptor_order_mapping_plan_group_count=mapping_assertion.get(
                        "plan_group_count"
                    ),
                    descriptor_order_mapping_error=mapping_assertion.get("error"),
                    candidate_construction_us=stream_build_us,
                    descriptor_order_build_us=float(descriptor_report.order_build_us),
                    counter_update_us=counter_update_us,
                    decision_us=decision_us,
                )
            )
            return
        policy = ShadowPolicyConfig(
            policy_mode="descriptor_order_shadow",
            optimization_goal="cache_locality",
            action_keep_fraction=0.0,
            metadata_score_ratio=0.0,
            full_fetch_max_extra=0,
            metadata_max_extra=0,
            premap_max_extra=0,
            policy_reason="current_router_layer_prior_descriptor_order",
            descriptor_order_policy=descriptor_report.policy,
            descriptor_order_prior_id=descriptor_report.prior_id,
            descriptor_order_prior_hash=descriptor_report.prior_hash,
            descriptor_order_top_utility_override=descriptor_report.top_utility_override,
        )
        sink.write_descriptor_order_summary(
            event_id=event_id,
            policy=policy,
            descriptor_report=descriptor_report,
            baseline_order_hash=baseline_order_hash,
            candidate_construction_us=stream_build_us,
            counter_update_us=counter_update_us,
            decision_us=decision_us,
            descriptor_order_execution_mode=str(self.shadow_descriptor_order_execution_mode),
            descriptor_group_plan_groups_per_cta=max(
                1,
                int(self.shadow_descriptor_order_groups_per_cta),
            ),
        )

    def _write_current_router_premap_summary(
        self,
        *,
        layer_id: int,
        topk_ids: torch.Tensor,
        topk_weights: torch.Tensor,
    ) -> None:
        """Emit a premap-only audit row for the current true-router top-k.

        This validates descriptor/address preparation on the real vLLM router
        path. It does not move expert payload, modify router outputs, credit
        readiness, or alter descriptor-order execution.
        """

        sink = self.shadow_outcome_sink
        if sink is None:
            return
        if not hasattr(sink, "write_premap_summary_from_descriptors"):
            msg = (
                "shadow_emit_premap_summary=True requires a sink with "
                "write_premap_summary_from_descriptors(...)."
            )
            raise TypeError(msg)
        if topk_ids.ndim != 2 or topk_weights.shape != topk_ids.shape:
            return

        total_start_ns = time.perf_counter_ns()
        build_start_ns = total_start_ns
        ids = topk_ids.detach().cpu().to(torch.long)
        weights = topk_weights.detach().cpu().to(torch.float32)
        scores_by_expert: dict[int, float] = {}
        for expert_value, weight_value in zip(
            ids.reshape(-1).tolist(),
            weights.reshape(-1).tolist(),
            strict=False,
        ):
            expert_id = int(expert_value)
            if expert_id < 0 or expert_id >= int(self.shadow_num_experts):
                continue
            score = float(weight_value)
            previous = scores_by_expert.get(expert_id)
            if previous is None or score > previous:
                scores_by_expert[expert_id] = score
        descriptors = [
            ExpertPrefetchDescriptor(
                sample_idx=int(self.sequence_id),
                layer_idx=int(layer_id),
                expert_id=int(expert_id),
                priority=int(self.shadow_premap_priority),
                source=str(self.shadow_premap_source),
                score=float(scores_by_expert[expert_id]),
            )
            for expert_id in sorted(scores_by_expert)
        ]
        candidate_construction_us = (time.perf_counter_ns() - build_start_ns) / 1000.0
        manager_start_ns = time.perf_counter_ns()
        prepared_plan, manager_snapshot = self._update_premap_address_manager(descriptors)
        manager_update_us = (time.perf_counter_ns() - manager_start_ns) / 1000.0
        address_keys = self._premap_address_keys_for_experts(
            layer_id=int(layer_id),
            expert_ids=sorted(scores_by_expert),
        )
        handle_hash = None
        handle_hash_by_address_key: dict[str, str] = {}
        if self._shadow_premap_address_manager is not None:
            handles = [
                self._shadow_premap_address_manager.resolve_address_key(key)
                for key in address_keys
            ]
            handle_hash_by_address_key = {
                key: handle.handle_hash
                for key, handle in zip(address_keys, handles, strict=False)
                if handle is not None
            }
            handle_hash = self._hash_premap_address_handles(
                handle.handle_hash for handle in handles if handle is not None
            )
        self._last_premap_address_mapping_by_layer[int(layer_id)] = {
            "source": str(self.shadow_premap_source),
            "address_namespace": str(self.shadow_premap_address_namespace),
            "address_key_hash": self._hash_premap_address_keys(address_keys),
            "descriptor_handle_hash": handle_hash,
            "descriptor_handle_hash_by_address_key": handle_hash_by_address_key,
            "address_key_count": len(address_keys),
            "prepare_plan_count": (
                int(manager_snapshot.prepared_plan_count)
                if manager_snapshot is not None
                else None
            ),
            "prepare_record_count": (
                int(manager_snapshot.prepared_record_count)
                if manager_snapshot is not None
                else None
            ),
        }
        if not self._premap_summary_sample_wanted():
            return
        decision_us = (time.perf_counter_ns() - total_start_ns) / 1000.0
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.shadow_premap_event_token_index),
            layer=int(layer_id),
        )
        sink.write_premap_summary_from_descriptors(
            event_id=event_id,
            descriptors=descriptors,
            premap_policy=str(self.shadow_premap_policy),
            premap_mode="shadow_only",
            premap_source=str(self.shadow_premap_source),
            descriptor_bytes=int(self.shadow_premap_descriptor_bytes),
            premap_build_us=candidate_construction_us,
            premap_prepared_plan=prepared_plan,
            premap_address_manager_snapshot=manager_snapshot,
            decision_us=decision_us,
            candidate_construction_us=candidate_construction_us,
            counter_update_us=(
                manager_update_us
                if self.shadow_emit_premap_address_manager_counters
                else None
            ),
        )

    def _premap_summary_sample_wanted(self) -> bool:
        sample_period = max(1, int(self.shadow_premap_summary_sample_period))
        self._premap_summary_call_count += 1
        return (self._premap_summary_call_count - 1) % sample_period == 0

    def _write_previous_token_transition_premap_summaries(
        self,
        *,
        layer_id: int,
        topk_ids: torch.Tensor,
        topk_weights: torch.Tensor,
    ) -> None:
        """Emit premap-only audit rows derived from previous-token transition.

        This is closer to the future-action premap path than the current-router
        producer smoke, but it is still shadow-only: no payload movement, no
        outcome ready credit, and no router mutation.
        """

        sink = self.shadow_outcome_sink
        if sink is None:
            return
        if not hasattr(sink, "write_premap_summary_from_descriptors"):
            msg = (
                "shadow_emit_transition_premap_summary=True requires a sink with "
                "write_premap_summary_from_descriptors(...)."
            )
            raise TypeError(msg)
        if topk_ids.ndim != 2 or topk_weights.shape != topk_ids.shape:
            return
        if int(topk_ids.shape[0]) <= 1:
            return

        mode = str(self.shadow_transition_summary_mode)
        for token_idx in range(1, int(topk_ids.shape[0])):
            total_start_ns = time.perf_counter_ns()
            try:
                base, _transition_count = self._transition_summary_base_mask(
                    layer_id=layer_id,
                    previous_topk_ids=topk_ids[token_idx - 1],
                    previous_topk_weights=topk_weights[token_idx - 1],
                    mode=mode,
                )
                descriptors = self._premap_descriptors_from_mask(
                    layer_id=layer_id,
                    mask=base,
                    priority=int(self.shadow_transition_premap_priority),
                    source=str(self.shadow_transition_premap_source),
                )
                candidate_construction_us = (
                    time.perf_counter_ns() - total_start_ns
                ) / 1000.0
                manager_start_ns = time.perf_counter_ns()
                prepared_plan, manager_snapshot = self._update_premap_address_manager(
                    descriptors
                )
                manager_update_us = (
                    time.perf_counter_ns() - manager_start_ns
                ) / 1000.0
                error = None
            except Exception as exc:  # pragma: no cover - defensive telemetry path
                descriptors = []
                prepared_plan = None
                manager_snapshot = None
                manager_update_us = 0.0
                error = f"{type(exc).__name__}: {exc}"
                candidate_construction_us = (
                    time.perf_counter_ns() - total_start_ns
                ) / 1000.0
            decision_us = (time.perf_counter_ns() - total_start_ns) / 1000.0
            event_id = ShadowEventId(
                request_id=str(self.request_id),
                sequence_id=int(self.sequence_id),
                token_index=int(self.token_offset + token_idx),
                layer=int(layer_id),
            )
            sink.write_premap_summary_from_descriptors(
                event_id=event_id,
                descriptors=descriptors,
                premap_policy=str(self.shadow_premap_policy),
                premap_mode="shadow_only",
                premap_source=str(self.shadow_transition_premap_source),
                descriptor_bytes=int(self.shadow_premap_descriptor_bytes),
                premap_build_us=candidate_construction_us,
                premap_prepared_plan=prepared_plan,
                premap_address_manager_snapshot=manager_snapshot,
                decision_us=decision_us,
                candidate_construction_us=candidate_construction_us,
                counter_update_us=(
                    manager_update_us
                    if self.shadow_emit_premap_address_manager_counters
                    else None
                ),
                premap_error=error,
            )

    def _update_premap_address_manager(
        self,
        descriptors: list[ExpertPrefetchDescriptor],
    ):
        if not self.shadow_emit_premap_address_manager_counters:
            return None, None
        if self._shadow_premap_address_manager is None:
            self._shadow_premap_address_manager = ControlledPremapAddressManager(
                capacity=self.shadow_premap_address_manager_capacity,
            )
        plan = prepare_premap_address_plan(
            descriptors,
            descriptor_bytes=int(self.shadow_premap_descriptor_bytes),
            address_namespace=str(self.shadow_premap_address_namespace),
        )
        return plan, self._shadow_premap_address_manager.prepare(plan)

    def _premap_address_keys_for_experts(
        self,
        *,
        layer_id: int,
        expert_ids: Iterable[int],
    ) -> list[str]:
        keys = []
        for expert_id in sorted({int(value) for value in expert_ids}):
            if expert_id < 0 or expert_id >= int(self.shadow_num_experts):
                continue
            keys.append(
                ControlledPremapAddressManager.address_key(
                    layer_idx=int(layer_id),
                    expert_id=int(expert_id),
                    address_namespace=str(self.shadow_premap_address_namespace),
                )
            )
        return keys

    @staticmethod
    def _hash_premap_address_keys(keys: Iterable[str]) -> str:
        payload = "\n".join(str(key) for key in sorted(keys)).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _hash_premap_address_handles(handle_hashes: Iterable[str]) -> str:
        payload = "\n".join(str(value) for value in sorted(handle_hashes)).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _premap_descriptors_from_mask(
        self,
        *,
        layer_id: int,
        mask: torch.Tensor,
        priority: int,
        source: str,
    ) -> list[ExpertPrefetchDescriptor]:
        expert_ids = torch.nonzero(mask.reshape(-1).bool(), as_tuple=False).reshape(-1)
        descriptors: list[ExpertPrefetchDescriptor] = []
        for expert_value in expert_ids.cpu().tolist():
            expert_id = int(expert_value)
            if expert_id < 0 or expert_id >= int(self.shadow_num_experts):
                continue
            descriptors.append(
                ExpertPrefetchDescriptor(
                    sample_idx=int(self.sequence_id),
                    layer_idx=int(layer_id),
                    expert_id=expert_id,
                    priority=int(priority),
                    source=str(source),
                    score=1.0,
                )
            )
        return descriptors

    def write_prelaunch_descriptor_assertion(
        self,
        *,
        layer_id: int,
        topk_ids: torch.Tensor,
    ) -> None:
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_descriptor_prelaunch_assertion"):
            return
        mode = str(self.shadow_descriptor_order_prelaunch_assertion_mode or "off")
        normalized_mode = mode.strip().lower()
        if normalized_mode in {"", "off", "none", "false", "0"}:
            return
        start_ns = time.perf_counter_ns()
        ids = topk_ids.detach().cpu().to(torch.long)
        try:
            prelaunch = _internal_group_plan_counts_from_router_topk(
                ids=ids,
                tiles_per_expert=int(self.shadow_descriptor_order_tiles_per_expert),
                token_window_size=int(self.shadow_descriptor_order_token_window_size),
            )
            router_mapping = self._last_descriptor_mapping_by_layer.get(int(layer_id), {})
            router_hash = router_mapping.get("tile_multiset_hash")
            router_request_count = router_mapping.get("request_count")
            router_group_count = router_mapping.get("group_count")
            counts_match = (
                router_request_count is not None
                and router_group_count is not None
                and int(prelaunch["request_count"]) == int(router_request_count)
                and int(prelaunch["group_count"]) == int(router_group_count)
            )
            same_multiset = (
                bool(counts_match)
                and router_hash is not None
                and str(prelaunch["tile_multiset_hash"]) == str(router_hash)
            )
            error = None
            if router_hash is None:
                error = "router_mapping_missing"
            elif not same_multiset:
                error = "prelaunch_router_multiset_mismatch"
            reorder_mvp = self._descriptor_order_reorder_mvp_decision(
                same_multiset=bool(same_multiset),
                group_count=int(prelaunch["group_count"]),
                layer_id=int(layer_id),
            )
            dump_us = (time.perf_counter_ns() - start_ns) / 1000.0
            event = ShadowDescriptorPrelaunchAssertEvent(
                event_id=ShadowEventId(
                    request_id=str(self.request_id),
                    sequence_id=int(self.sequence_id),
                    token_index=int(self.shadow_descriptor_order_event_token_index),
                    layer=int(layer_id),
                ),
                assertion_mode=normalized_mode,
                mapping_source=str(self.shadow_descriptor_order_prelaunch_mapping_source),
                router_mapping_source=(
                    str(router_mapping.get("source")) if router_mapping.get("source") else None
                ),
                same_multiset=bool(same_multiset),
                counts_match=bool(counts_match),
                prelaunch_tile_multiset_hash=str(prelaunch["tile_multiset_hash"]),
                router_derived_tile_multiset_hash=(
                    str(router_hash) if router_hash is not None else None
                ),
                prelaunch_request_count=int(prelaunch["request_count"]),
                router_derived_request_count=(
                    int(router_request_count)
                    if router_request_count is not None
                    else None
                ),
                prelaunch_group_count=int(prelaunch["group_count"]),
                router_derived_group_count=(
                    int(router_group_count) if router_group_count is not None else None
                ),
                error=error,
                dump_us=dump_us,
                **reorder_mvp,
            )
        except Exception as exc:  # pragma: no cover - defensive telemetry path
            reorder_requested = bool(self.shadow_descriptor_order_reorder_mvp_enabled)
            event = ShadowDescriptorPrelaunchAssertEvent(
                event_id=ShadowEventId(
                    request_id=str(self.request_id),
                    sequence_id=int(self.sequence_id),
                    token_index=int(self.shadow_descriptor_order_event_token_index),
                    layer=int(layer_id),
                ),
                assertion_mode=normalized_mode,
                mapping_source=str(self.shadow_descriptor_order_prelaunch_mapping_source),
                router_mapping_source=None,
                same_multiset=False,
                counts_match=False,
                prelaunch_tile_multiset_hash="",
                router_derived_tile_multiset_hash=None,
                prelaunch_request_count=0,
                router_derived_request_count=None,
                prelaunch_group_count=0,
                router_derived_group_count=None,
                error=f"{type(exc).__name__}: {exc}",
                dump_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                reorder_mvp_requested=reorder_requested,
                reorder_mvp_selected_policy="no_order",
                reorder_mvp_applied=False,
                reorder_mvp_fallback_reason=(
                    "prelaunch_assertion_error" if reorder_requested else None
                ),
            )
        sink.write_descriptor_prelaunch_assertion(event)

    def _descriptor_order_reorder_mvp_decision(
        self,
        *,
        same_multiset: bool,
        group_count: int,
        layer_id: int | None = None,
        apply_supported: bool = False,
    ) -> dict[str, Any]:
        requested = bool(self.shadow_descriptor_order_reorder_mvp_enabled)
        payload: dict[str, Any] = {
            "reorder_mvp_requested": requested,
            "reorder_mvp_selected_policy": "no_order",
            "reorder_mvp_applied": False,
        }
        if not requested:
            return payload
        layer_allowlist = self.shadow_descriptor_order_reorder_mvp_layer_allowlist
        if layer_allowlist is not None and (
            layer_id is None or int(layer_id) not in layer_allowlist
        ):
            payload.update(
                {
                    "reorder_mvp_gate_allow": False,
                    "reorder_mvp_gate_reason": "layer_not_allowed",
                    "reorder_mvp_candidate_policy": "layer_prior_frequency_two_level",
                    "reorder_mvp_candidate_speedup_median_vs_no_order": None,
                    "reorder_mvp_selected_policy": "no_order",
                    "reorder_mvp_applied": False,
                    "reorder_mvp_fallback_reason": "layer_not_allowed",
                }
            )
            return payload
        groups_per_cta = max(1, int(self.shadow_descriptor_order_groups_per_cta))
        evidence = None
        if (
            self.shadow_descriptor_order_evidence is not None
            and self.shadow_descriptor_order_device is not None
        ):
            evidence = self.shadow_descriptor_order_evidence.get(
                (
                    int(self.shadow_descriptor_order_device),
                    int(self.shadow_descriptor_order_tile_elems),
                    int(groups_per_cta),
                    int(self.shadow_descriptor_order_evidence_cache_flush_elems),
                )
            )
        checksum_delta = evidence.checksum_delta if evidence is not None else None
        gate_decision = None
        if self.shadow_descriptor_order_runtime_gate is not None:
            gate_decision = self.shadow_descriptor_order_runtime_gate.decide(
                tile_elems=int(self.shadow_descriptor_order_tile_elems),
                groups_per_cta=groups_per_cta,
                device=self.shadow_descriptor_order_device,
                execution_mode=str(self.shadow_descriptor_order_execution_mode),
                group_count=int(group_count),
                same_multiset=bool(same_multiset),
                checksum_delta=checksum_delta,
            )
        gate_allow = bool(gate_decision.allow) if gate_decision is not None else False
        gate_reason = gate_decision.reason if gate_decision is not None else "gate_missing"
        speedup = evidence.speedup_median_vs_no_order if evidence is not None else None
        profitable = speedup is not None and float(speedup) > 1.0
        candidate_policy = "layer_prior_frequency_two_level"
        selected_policy = "no_order"
        fallback_reason = None
        if not gate_allow:
            fallback_reason = gate_reason
        elif evidence is None:
            fallback_reason = "evidence_missing"
        elif self.shadow_descriptor_order_reorder_mvp_require_profitable and not profitable:
            fallback_reason = "not_profitable"
        elif str(self.shadow_descriptor_order_reorder_mvp_apply_mode).lower() != "apply":
            fallback_reason = "dry_run_no_vllm_descriptor_consumer_patch"
        elif not apply_supported:
            fallback_reason = "dry_run_no_vllm_descriptor_consumer_patch"
        else:
            selected_policy = candidate_policy
            fallback_reason = None
        payload.update(
            {
                "reorder_mvp_gate_allow": gate_allow,
                "reorder_mvp_gate_reason": gate_reason,
                "reorder_mvp_candidate_policy": candidate_policy,
                "reorder_mvp_candidate_speedup_median_vs_no_order": speedup,
                "reorder_mvp_selected_policy": selected_policy,
                "reorder_mvp_applied": bool(
                    fallback_reason is None and selected_policy == candidate_policy
                ),
                "reorder_mvp_fallback_reason": fallback_reason,
            }
        )
        return payload

    def _resolve_real_premap_descriptor_handles(
        self,
        *,
        consumer_layer: Any | None,
        expert_ids: list[int],
    ) -> tuple[
        int,
        int,
        str | None,
        bool | None,
        dict[int, str],
        dict[int, PremapRealDescriptorHandle],
        dict[str, str],
        dict[str, int],
        dict[str, int],
        dict[str, int],
    ]:
        source_attrs = {
            "packed_weight": (
                "w13_weight_packed",
                "w2_weight_packed",
                "w13_qweight",
                "w2_qweight",
            ),
            "scale_metadata": (
                "w13_weight_scale",
                "w2_weight_scale",
                "w13_scales",
                "w2_scales",
            ),
            "aux_metadata": (
                "w13_qzeros",
                "w2_qzeros",
                "w13_weight_g_idx",
                "w2_weight_g_idx",
            ),
        }
        source_names = tuple(source_attrs)
        empty_source_hashes: dict[str, str] = {}
        empty_source_hit_counts = {name: 0 for name in source_names}
        empty_source_miss_counts = {name: 0 for name in source_names}
        if not bool(self.shadow_premap_consumer_resolve_real_handles):
            return (
                0,
                0,
                None,
                None,
                {},
                {},
                empty_source_hashes,
                empty_source_hit_counts,
                empty_source_miss_counts,
                {"resolver_disabled": len(expert_ids)},
            )
        if consumer_layer is None:
            return (
                0,
                len(expert_ids),
                None,
                False,
                {},
                {},
                empty_source_hashes,
                empty_source_hit_counts,
                {name: len(expert_ids) for name in source_names},
                {"consumer_layer_missing": len(expert_ids)},
            )

        expert_map = getattr(consumer_layer, "expert_map", None)
        handle_hashes: list[str] = []
        handle_by_expert: dict[int, str] = {}
        real_handle_by_expert: dict[int, PremapRealDescriptorHandle] = {}
        source_hash_parts: dict[str, list[str]] = {name: [] for name in source_names}
        source_hit_counts: dict[str, int] = {name: 0 for name in source_names}
        source_miss_counts: dict[str, int] = {name: 0 for name in source_names}
        miss_reason_counts: dict[str, int] = {
            "resolver_disabled": 0,
            "consumer_layer_missing": 0,
            "expert_map_miss": 0,
            "no_handle_parts": 0,
        }
        miss_count = 0
        for expert_id in expert_ids:
            local_expert = int(expert_id)
            if isinstance(expert_map, torch.Tensor):
                try:
                    if 0 <= int(expert_id) < int(expert_map.numel()):
                        local_expert = int(expert_map.reshape(-1)[int(expert_id)].item())
                    else:
                        local_expert = -1
                except Exception:
                    local_expert = -1
            if local_expert < 0:
                miss_count += 1
                for source_name in source_names:
                    source_miss_counts[source_name] += 1
                miss_reason_counts["expert_map_miss"] += 1
                continue
            parts: list[str] = []
            source_parts_by_name: dict[str, list[str]] = {}
            for source_name, attr_names in source_attrs.items():
                source_parts: list[str] = []
                for attr_name in attr_names:
                    tensor = getattr(consumer_layer, attr_name, None)
                    if not isinstance(tensor, torch.Tensor) or int(tensor.numel()) <= 0:
                        continue
                    if tensor.ndim > 0 and local_expert >= int(tensor.shape[0]):
                        continue
                    try:
                        view = tensor[int(local_expert)] if tensor.ndim > 0 else tensor
                        # Runtime-address signature only.  This is not a portable
                        # semantic handle id across model reloads or tensor
                        # reallocation; it is meant to audit stability of the live
                        # descriptor/address object during one recorder lifetime.
                        source_parts.append(
                            ":".join(
                                (
                                    str(source_name),
                                    str(attr_name),
                                    str(tuple(tensor.shape)),
                                    str(tensor.dtype),
                                    str(tensor.device),
                                    str(int(view.data_ptr())),
                                )
                            )
                        )
                    except Exception:
                        continue
                if source_parts:
                    # Source hit is intentionally any-of within the source bucket:
                    # a packed/scale/aux bucket is considered resolvable when at
                    # least one of its known AWQ/vLLM handle fields is present.
                    # This audits source-class availability, not per-field
                    # completeness.
                    source_hit_counts[source_name] += 1
                    source_hash_parts[source_name].extend(source_parts)
                    source_parts_by_name[source_name] = list(source_parts)
                    parts.extend(source_parts)
                else:
                    source_miss_counts[source_name] += 1
            if not parts:
                miss_count += 1
                miss_reason_counts["no_handle_parts"] += 1
                continue
            payload = "|".join([str(expert_id), str(local_expert), *sorted(parts)])
            handle_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            handle_hashes.append(handle_hash)
            handle_by_expert[int(expert_id)] = handle_hash
            packed_parts = source_parts_by_name.get("packed_weight", [])
            scale_parts = source_parts_by_name.get("scale_metadata", [])
            packed_hash = self._hash_premap_address_handles(packed_parts)
            scale_hash = self._hash_premap_address_handles(scale_parts)
            aux_parts = source_parts_by_name.get("aux_metadata", [])
            aux_hash = self._hash_premap_address_handles(aux_parts) if aux_parts else None
            real_handle_by_expert[int(expert_id)] = PremapRealDescriptorHandle(
                expert_id=int(expert_id),
                local_expert_id=int(local_expert),
                handle_hash=handle_hash,
                packed_weight_descriptor=(
                    f"real_packed_weight://{packed_hash}" if packed_parts else None
                ),
                scale_metadata_handle=(
                    f"real_scale_metadata://{scale_hash}" if scale_parts else None
                ),
                aux_metadata_handle=(
                    f"real_aux_metadata://{aux_hash}" if aux_hash is not None else None
                ),
                payload_bytes=0,
            )
        real_hash = self._hash_premap_address_handles(handle_hashes)
        source_hashes = {
            source_name: self._hash_premap_address_handles(parts)
            for source_name, parts in source_hash_parts.items()
            if parts
        }
        return (
            len(handle_hashes),
            miss_count,
            real_hash,
            miss_count == 0,
            handle_by_expert,
            real_handle_by_expert,
            source_hashes,
            source_hit_counts,
            source_miss_counts,
            {k: v for k, v in miss_reason_counts.items() if int(v) > 0},
        )

    def _premap_consumer_mapping_wanted(self) -> bool:
        if not bool(self.shadow_emit_premap_consumer_mapping):
            return False
        mode = str(self.shadow_premap_consumer_mapping_mode or "off").strip().lower()
        return mode not in {"", "off", "none", "false", "0"}

    def _premap_consumer_mapping_sample_wanted(self) -> bool:
        sample_period = max(1, int(self.shadow_premap_consumer_mapping_sample_period))
        self._premap_consumer_mapping_call_count += 1
        return (self._premap_consumer_mapping_call_count - 1) % sample_period == 0

    def _write_premap_consumer_mapping_from_experts(
        self,
        *,
        layer_id: int,
        active_experts: list[int],
        consumer_layer: Any | None = None,
        prelaunch_boundary_source: str | None = None,
        prelaunch_handle_available: bool | None = None,
        prelaunch_block_count: int | None = None,
        prelaunch_block_size: int | None = None,
        prelaunch_expert_order_hash: str | None = None,
        prelaunch_expert_multiset_hash: str | None = None,
        lookup_start_ns: int | None = None,
        error: str | None = None,
    ) -> None:
        sink = self.shadow_outcome_sink
        if sink is None or not self._premap_consumer_mapping_wanted():
            return
        if not self._premap_consumer_mapping_sample_wanted():
            return
        if not hasattr(sink, "write_premap_consumer_mapping"):
            msg = (
                "shadow_emit_premap_consumer_mapping=True requires a sink with "
                "write_premap_consumer_mapping(event)."
            )
            raise TypeError(msg)
        start_ns = lookup_start_ns or time.perf_counter_ns()
        valid_experts = sorted(
            {
                int(expert_id)
                for expert_id in active_experts
                if 0 <= int(expert_id) < int(self.shadow_num_experts)
            }
        )
        prelaunch_boundary_aligned = None
        if prelaunch_boundary_source is not None:
            prelaunch_boundary_aligned = (
                prelaunch_handle_available is True
                and prelaunch_block_count is not None
                and len(valid_experts) > 0
                and len(valid_experts) <= int(prelaunch_block_count)
                and prelaunch_expert_order_hash is not None
                and str(prelaunch_expert_order_hash) == hash_ints(valid_experts)
                and prelaunch_expert_multiset_hash is not None
                and str(prelaunch_expert_multiset_hash)
                == hash_ints(sorted(int(value) for value in valid_experts))
            )
        address_keys = self._premap_address_keys_for_experts(
            layer_id=int(layer_id),
            expert_ids=valid_experts,
        )
        alignment_error: str | None = None
        try:
            address_expert_pairs = list(zip(address_keys, valid_experts, strict=True))
        except ValueError:
            alignment_error = (
                "premap_consumer_address_expert_length_mismatch:"
                f"address_keys={len(address_keys)}:"
                f"experts={len(valid_experts)}"
            )
            address_expert_pairs = list(zip(address_keys, valid_experts))
        manager = self._shadow_premap_address_manager
        hit_count = 0
        address_hit_keys: list[str] = []
        descriptor_handle_hashes: list[str] = []
        if manager is None:
            mapping_error = (
                error or alignment_error or "premap_address_manager_missing"
            )
            resident_count = None
            observed_prepare_plan_count = None
            observed_prepare_record_count = None
        else:
            mapping_error = error or alignment_error
            observed_snapshot = manager.snapshot()
            resident_count = observed_snapshot.resident_address_count
            observed_prepare_plan_count = int(observed_snapshot.prepared_plan_count)
            observed_prepare_record_count = int(observed_snapshot.prepared_record_count)
            for key in address_keys:
                handle = manager.resolve_address_key(key)
                if handle is None:
                    continue
                hit_count += 1
                address_hit_keys.append(key)
                descriptor_handle_hashes.append(handle.handle_hash)
        miss_count = max(0, len(address_keys) - int(hit_count))
        descriptor_handle_miss_count = max(
            0,
            len(address_keys) - len(descriptor_handle_hashes),
        )
        all_hit = len(address_keys) > 0 and miss_count == 0
        consumer_hash = self._hash_premap_address_keys(address_keys)
        consumer_handle_hash = self._hash_premap_address_handles(descriptor_handle_hashes)
        (
            real_handle_hit_count,
            real_handle_miss_count,
            real_handle_hash,
            real_handle_available,
            real_handle_by_expert,
            real_descriptor_handle_by_expert,
            real_handle_source_hashes,
            real_handle_source_hit_counts,
            real_handle_source_miss_counts,
            real_handle_miss_reason_counts,
        ) = self._resolve_real_premap_descriptor_handles(
            consumer_layer=consumer_layer,
            expert_ids=valid_experts,
        )
        address_hit_set = set(address_hit_keys)
        new_binding_count = 0
        reused_binding_count = 0
        binding_mismatch_count = 0
        real_handle_for_address_miss_count = 0
        real_descriptor_handles_by_address_key: dict[str, PremapRealDescriptorHandle] = {}
        for key, expert_id in address_expert_pairs:
            real_expert_hash = real_handle_by_expert.get(int(expert_id))
            if real_expert_hash is None:
                continue
            if key not in address_hit_set:
                real_handle_for_address_miss_count += 1
            else:
                real_descriptor_handle = real_descriptor_handle_by_expert.get(
                    int(expert_id)
                )
                if real_descriptor_handle is not None:
                    real_descriptor_handles_by_address_key[key] = replace(
                        real_descriptor_handle,
                        address_key=key,
                    )
            previous_hash = self._premap_real_handle_binding_by_address_key.get(key)
            if previous_hash is None:
                self._premap_real_handle_binding_by_address_key[key] = real_expert_hash
                new_binding_count += 1
            elif str(previous_hash) == str(real_expert_hash):
                reused_binding_count += 1
            else:
                binding_mismatch_count += 1
        expected = self._last_premap_address_mapping_by_layer.get(int(layer_id), {})
        expected_hash = expected.get("address_key_hash")
        expected_handle_hash = expected.get("descriptor_handle_hash")
        expected_handle_hash_by_key = expected.get(
            "descriptor_handle_hash_by_address_key",
            {},
        )
        if not isinstance(expected_handle_hash_by_key, dict):
            expected_handle_hash_by_key = {}
        expected_count = expected.get("address_key_count")
        expected_prepare_plan_count = expected.get("prepare_plan_count")
        expected_prepare_record_count = expected.get("prepare_record_count")
        lookup_after_prepare = (
            expected_prepare_plan_count is not None
            and observed_prepare_plan_count is not None
            and int(observed_prepare_plan_count) >= int(expected_prepare_plan_count)
            and expected_prepare_record_count is not None
            and observed_prepare_record_count is not None
            and int(observed_prepare_record_count) >= int(expected_prepare_record_count)
        )
        handle_parity_ok = (
            bool(all_hit)
            and expected_handle_hash is not None
            and str(expected_handle_hash) == str(consumer_handle_hash)
            and len(descriptor_handle_hashes) == len(address_keys)
        )
        parity_ok = (
            bool(all_hit)
            and expected_hash is not None
            and str(expected_hash) == str(consumer_hash)
            and expected_count is not None
            and int(expected_count) == len(address_keys)
            and bool(handle_parity_ok)
            and bool(lookup_after_prepare)
        )
        if mapping_error is None and expected_hash is None:
            mapping_error = "premap_router_mapping_missing"
        readonly_consumer_result = None
        if manager is not None:
            readonly_consumer_result = manager.consume_readonly(
                address_keys,
                expected_handle_hash_by_address_key={
                    str(key): str(value)
                    for key, value in expected_handle_hash_by_key.items()
                },
            )
        descriptor_prep_result = None
        descriptor_consumer_read_result = None
        descriptor_consumer_shim_result = None
        kernel_arg_shadow_table_result = None
        kernel_arg_shadow_table_object = None
        descriptor_prep_dry_run_result = None
        descriptor_prep_blocked_reason: str | None = None
        descriptor_prep_mode = _normalize_premap_descriptor_prep_execution_mode(
            self.shadow_premap_descriptor_prep_execution_mode
        )
        descriptor_prep_enabled = descriptor_prep_mode is not None
        if descriptor_prep_enabled:
            readonly_gate_ok = (
                bool(self.shadow_premap_consumer_readonly_gate_required)
                and self.shadow_premap_consumer_readonly_gate_passed is True
            )
            readonly_lookup_ok = (
                readonly_consumer_result is not None
                and int(readonly_consumer_result.lookup_count) > 0
                and int(readonly_consumer_result.handle_miss_count) == 0
                and int(readonly_consumer_result.evicted_before_consume_count) == 0
                and int(readonly_consumer_result.stale_handle_count) == 0
                and readonly_consumer_result.handle_parity_ok is not False
            )
            if manager is None:
                descriptor_prep_blocked_reason = "premap_address_manager_missing"
            elif not readonly_gate_ok:
                descriptor_prep_blocked_reason = "readonly_gate_not_passed"
            elif not readonly_lookup_ok:
                descriptor_prep_blocked_reason = "readonly_consumer_failed"
            elif not all_hit:
                descriptor_prep_blocked_reason = "address_miss"
            else:
                descriptor_prep_result = manager.execute_descriptor_prep_readonly(
                    address_keys,
                    execution_mode=descriptor_prep_mode,
                    real_descriptor_handles_by_address_key=(
                        real_descriptor_handles_by_address_key
                        if bool(self.shadow_premap_consumer_resolve_real_handles)
                        else None
                    ),
                )
                if descriptor_prep_result.execution_ok:
                    descriptor_consumer_read_result = (
                        manager.read_descriptor_consumer_objects_readonly(
                            address_keys,
                            expected_object_hash_by_address_key=(
                                descriptor_prep_result.consumer_object_hash_by_address_key
                            ),
                            real_descriptor_handles_by_address_key=(
                                real_descriptor_handles_by_address_key
                                if bool(self.shadow_premap_consumer_resolve_real_handles)
                                else None
                            ),
                        )
                    )
                    if descriptor_consumer_read_result.read_ok:
                        (
                            kernel_arg_shadow_table_result,
                            kernel_arg_shadow_table_object,
                        ) = manager.build_kernel_arg_shadow_table_object_readonly(
                            address_keys,
                            read_result=descriptor_consumer_read_result,
                            expected_object_hash_by_address_key=(
                                descriptor_prep_result.consumer_object_hash_by_address_key
                            ),
                            real_descriptor_handles_by_address_key=(
                                real_descriptor_handles_by_address_key
                                if bool(self.shadow_premap_consumer_resolve_real_handles)
                                else None
                            ),
                        )
                        descriptor_prep_dry_run_result = (
                            manager.execute_descriptor_address_prep_dry_run_readonly(
                                kernel_arg_shadow_table_object,
                                read_result=descriptor_consumer_read_result,
                                real_descriptor_handles_by_address_key=(
                                    real_descriptor_handles_by_address_key
                                    if bool(
                                        self.shadow_premap_consumer_resolve_real_handles
                                    )
                                    else None
                                ),
                            )
                        )
                        descriptor_consumer_shim_result = (
                            manager.execute_descriptor_consumer_shim_readonly(
                                descriptor_consumer_read_result,
                                kernel_arg_shadow_table_result=(
                                    kernel_arg_shadow_table_result
                                ),
                                kernel_arg_shadow_table_object=(
                                    kernel_arg_shadow_table_object
                                ),
                                descriptor_address_prep_dry_run_result=(
                                    descriptor_prep_dry_run_result
                                ),
                            )
                        )
        lookup_us = (time.perf_counter_ns() - start_ns) / 1000.0
        sink.write_premap_consumer_mapping(
            ShadowPremapConsumerMappingEvent(
                event_id=ShadowEventId(
                    request_id=str(self.request_id),
                    sequence_id=int(self.sequence_id),
                    token_index=int(self.shadow_premap_event_token_index),
                    layer=int(layer_id),
                ),
                mapping_mode=str(self.shadow_premap_consumer_mapping_mode),
                mapping_source=str(self.shadow_premap_consumer_mapping_source),
                address_namespace=str(self.shadow_premap_address_namespace),
                readonly_gate_required=bool(
                    self.shadow_premap_consumer_readonly_gate_required
                ),
                readonly_gate_id=self.shadow_premap_consumer_readonly_gate_id,
                readonly_gate_path=self.shadow_premap_consumer_readonly_gate_path,
                readonly_gate_passed=self.shadow_premap_consumer_readonly_gate_passed,
                consumer_expert_count=len(active_experts),
                consumer_unique_expert_count=len(address_keys),
                address_hit_count=int(hit_count),
                address_miss_count=int(miss_count),
                address_hit_rate=float(hit_count) / max(1, len(address_keys)),
                all_hit=bool(all_hit),
                parity_ok=bool(parity_ok),
                consumer_key_hash=consumer_hash,
                descriptor_handle_hit_count=len(descriptor_handle_hashes),
                descriptor_handle_miss_count=descriptor_handle_miss_count,
                descriptor_handle_hash=consumer_handle_hash,
                expected_descriptor_handle_hash=(
                    str(expected_handle_hash)
                    if expected_handle_hash is not None
                    else None
                ),
                descriptor_handle_parity_ok=bool(handle_parity_ok),
                prelaunch_boundary_source=prelaunch_boundary_source,
                prelaunch_handle_available=prelaunch_handle_available,
                prelaunch_block_count=prelaunch_block_count,
                prelaunch_block_size=prelaunch_block_size,
                prelaunch_expert_order_hash=prelaunch_expert_order_hash,
                prelaunch_expert_multiset_hash=prelaunch_expert_multiset_hash,
                prelaunch_unique_expert_count=len(valid_experts),
                prelaunch_boundary_aligned=prelaunch_boundary_aligned,
                expected_prepare_plan_count=(
                    int(expected_prepare_plan_count)
                    if expected_prepare_plan_count is not None
                    else None
                ),
                observed_prepare_plan_count=observed_prepare_plan_count,
                expected_prepare_record_count=(
                    int(expected_prepare_record_count)
                    if expected_prepare_record_count is not None
                    else None
                ),
                observed_prepare_record_count=observed_prepare_record_count,
                lookup_after_prepare=bool(lookup_after_prepare),
                real_descriptor_handle_hit_count=int(real_handle_hit_count),
                real_descriptor_handle_miss_count=int(real_handle_miss_count),
                real_descriptor_handle_hash=real_handle_hash,
                real_descriptor_handle_available=real_handle_available,
                real_descriptor_handle_source_hashes=real_handle_source_hashes,
                real_descriptor_handle_source_hit_counts=real_handle_source_hit_counts,
                real_descriptor_handle_source_miss_counts=real_handle_source_miss_counts,
                real_descriptor_handle_miss_reason_counts=real_handle_miss_reason_counts,
                real_descriptor_handle_new_binding_count=int(new_binding_count),
                real_descriptor_handle_reused_binding_count=int(reused_binding_count),
                real_descriptor_handle_binding_mismatch_count=int(binding_mismatch_count),
                real_descriptor_handle_for_address_miss_count=int(
                    real_handle_for_address_miss_count
                ),
                readonly_consumer_lookup_count=(
                    int(readonly_consumer_result.lookup_count)
                    if readonly_consumer_result is not None
                    else None
                ),
                readonly_consumer_handle_hit_count=(
                    int(readonly_consumer_result.handle_hit_count)
                    if readonly_consumer_result is not None
                    else None
                ),
                readonly_consumer_handle_miss_count=(
                    int(readonly_consumer_result.handle_miss_count)
                    if readonly_consumer_result is not None
                    else None
                ),
                readonly_consumer_evicted_before_consume_count=(
                    int(readonly_consumer_result.evicted_before_consume_count)
                    if readonly_consumer_result is not None
                    else None
                ),
                readonly_consumer_stale_handle_count=(
                    int(readonly_consumer_result.stale_handle_count)
                    if readonly_consumer_result is not None
                    else None
                ),
                readonly_consumer_handle_parity_ok=(
                    readonly_consumer_result.handle_parity_ok
                    if readonly_consumer_result is not None
                    else None
                ),
                descriptor_prep_execution_mode=(
                    descriptor_prep_mode if descriptor_prep_enabled else None
                ),
                descriptor_prep_lookup_count=(
                    int(descriptor_prep_result.lookup_count)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_handle_count=(
                    int(descriptor_prep_result.prepared_handle_count)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_missing_handle_count=(
                    int(descriptor_prep_result.missing_handle_count)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_descriptor_ptr_count=(
                    int(descriptor_prep_result.descriptor_ptr_count)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_packed_weight_descriptor_count=(
                    int(descriptor_prep_result.packed_weight_descriptor_count)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_scale_metadata_handle_count=(
                    int(descriptor_prep_result.scale_metadata_handle_count)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_real_handle_count=(
                    int(descriptor_prep_result.real_descriptor_handle_count)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_real_handle_miss_count=(
                    int(descriptor_prep_result.real_descriptor_handle_miss_count)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_real_handle_backed=(
                    bool(descriptor_prep_result.real_descriptor_handle_backed)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_real_handle_hash=(
                    descriptor_prep_result.real_descriptor_handle_hash
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_handle_hash=(
                    descriptor_prep_result.handle_hash
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_consumer_object_count=(
                    int(descriptor_prep_result.consumer_object_count)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_consumer_object_hash=(
                    descriptor_prep_result.consumer_object_hash
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_consumer_object_read_lookup_count=(
                    int(descriptor_consumer_read_result.lookup_count)
                    if descriptor_consumer_read_result is not None
                    else None
                ),
                descriptor_prep_consumer_object_read_hit_count=(
                    int(descriptor_consumer_read_result.object_hit_count)
                    if descriptor_consumer_read_result is not None
                    else None
                ),
                descriptor_prep_consumer_object_read_miss_count=(
                    int(descriptor_consumer_read_result.object_miss_count)
                    if descriptor_consumer_read_result is not None
                    else None
                ),
                descriptor_prep_consumer_object_stale_count=(
                    int(descriptor_consumer_read_result.stale_object_count)
                    if descriptor_consumer_read_result is not None
                    else None
                ),
                descriptor_prep_consumer_object_read_hash=(
                    descriptor_consumer_read_result.object_hash
                    if descriptor_consumer_read_result is not None
                    else None
                ),
                descriptor_prep_consumer_object_read_ok=(
                    bool(descriptor_consumer_read_result.read_ok)
                    if descriptor_consumer_read_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_mode=(
                    descriptor_consumer_shim_result.execution_mode
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_object_count=(
                    int(descriptor_consumer_shim_result.object_count)
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_object_hash=(
                    descriptor_consumer_shim_result.object_hash
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_row_count=(
                    int(descriptor_consumer_shim_result.handle_table_row_count)
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_column_count=(
                    int(descriptor_consumer_shim_result.handle_table_column_count)
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_schema_hash=(
                    descriptor_consumer_shim_result.handle_table_schema_hash
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_read_ok=(
                    descriptor_consumer_shim_result.handle_table_read_ok
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_lifecycle_ok=(
                    descriptor_consumer_shim_result.handle_table_lifecycle_ok
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count=(
                    int(
                        descriptor_consumer_shim_result.handle_table_per_row_parity_ok_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.handle_table_per_row_parity_ok_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_row_miss_count=(
                    int(descriptor_consumer_shim_result.handle_table_row_miss_count)
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.handle_table_row_miss_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_stale_row_count=(
                    int(descriptor_consumer_shim_result.handle_table_stale_row_count)
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.handle_table_stale_row_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_passed_to_kernel=(
                    bool(descriptor_consumer_shim_result.handle_table_passed_to_kernel)
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_payload_bytes=(
                    int(descriptor_consumer_shim_result.handle_table_payload_bytes)
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_ok=(
                    descriptor_consumer_shim_result.handle_table_consume_ok
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok=(
                    descriptor_consumer_shim_result.handle_table_consume_lifecycle_ok
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_row_count=(
                    int(descriptor_consumer_shim_result.handle_table_consume_row_count)
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.handle_table_consume_row_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_column_count=(
                    int(
                        descriptor_consumer_shim_result.handle_table_consume_column_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.handle_table_consume_column_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_schema_hash=(
                    descriptor_consumer_shim_result.handle_table_consume_schema_hash
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_mode=(
                    descriptor_consumer_shim_result.handle_table_consume_mode
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_source=(
                    descriptor_consumer_shim_result.handle_table_consume_source
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_row_order_hash=(
                    descriptor_consumer_shim_result.handle_table_consume_row_order_hash
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_ordered_row_hash=(
                    descriptor_consumer_shim_result.handle_table_consume_ordered_row_hash
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count=(
                    int(
                        descriptor_consumer_shim_result.handle_table_consume_per_row_parity_ok_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.handle_table_consume_per_row_parity_ok_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_row_miss_count=(
                    int(
                        descriptor_consumer_shim_result.handle_table_consume_row_miss_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.handle_table_consume_row_miss_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_stale_row_count=(
                    int(
                        descriptor_consumer_shim_result.handle_table_consume_stale_row_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.handle_table_consume_stale_row_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel=(
                    bool(
                        descriptor_consumer_shim_result.handle_table_consume_passed_to_kernel
                    )
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_consume_payload_bytes=(
                    int(
                        descriptor_consumer_shim_result.handle_table_consume_payload_bytes
                    )
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_object_consumed=(
                    descriptor_consumer_shim_result.handle_table_object_consumed
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_object_hash=(
                    descriptor_consumer_shim_result.handle_table_object_hash
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_object_row_count=(
                    int(descriptor_consumer_shim_result.handle_table_object_row_count)
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.handle_table_object_row_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok=(
                    descriptor_consumer_shim_result.handle_table_object_lifecycle_ok
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel=(
                    bool(
                        descriptor_consumer_shim_result.handle_table_object_passed_to_kernel
                    )
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_handle_table_object_payload_bytes=(
                    int(
                        descriptor_consumer_shim_result.handle_table_object_payload_bytes
                    )
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_mode=(
                    descriptor_consumer_shim_result.prep_execution_dry_run_mode
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_source=(
                    descriptor_consumer_shim_result.prep_execution_dry_run_source
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_ok=(
                    descriptor_consumer_shim_result.prep_execution_dry_run_ok
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_row_count=(
                    int(descriptor_consumer_shim_result.prep_execution_dry_run_row_count)
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.prep_execution_dry_run_row_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_column_count=(
                    int(
                        descriptor_consumer_shim_result.prep_execution_dry_run_column_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.prep_execution_dry_run_column_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash=(
                    descriptor_consumer_shim_result.prep_execution_dry_run_schema_hash
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_object_hash=(
                    descriptor_consumer_shim_result.prep_execution_dry_run_object_hash
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok=(
                    descriptor_consumer_shim_result.prep_execution_dry_run_lifecycle_ok
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count=(
                    int(
                        descriptor_consumer_shim_result.prep_execution_dry_run_row_handle_parity_ok_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.prep_execution_dry_run_row_handle_parity_ok_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count=(
                    int(
                        descriptor_consumer_shim_result.prep_execution_dry_run_descriptor_ptr_parity_ok_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.prep_execution_dry_run_descriptor_ptr_parity_ok_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count=(
                    int(
                        descriptor_consumer_shim_result.prep_execution_dry_run_packed_weight_descriptor_parity_ok_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.prep_execution_dry_run_packed_weight_descriptor_parity_ok_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count=(
                    int(
                        descriptor_consumer_shim_result.prep_execution_dry_run_scale_metadata_handle_parity_ok_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.prep_execution_dry_run_scale_metadata_handle_parity_ok_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count=(
                    int(
                        descriptor_consumer_shim_result.prep_execution_dry_run_aux_metadata_handle_parity_ok_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.prep_execution_dry_run_aux_metadata_handle_parity_ok_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count=(
                    int(
                        descriptor_consumer_shim_result.prep_execution_dry_run_row_handle_miss_count
                    )
                    if (
                        descriptor_consumer_shim_result is not None
                        and descriptor_consumer_shim_result.prep_execution_dry_run_row_handle_miss_count
                        is not None
                    )
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel=(
                    bool(
                        descriptor_consumer_shim_result.prep_execution_dry_run_passed_to_kernel
                    )
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes=(
                    int(
                        descriptor_consumer_shim_result.prep_execution_dry_run_payload_bytes
                    )
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_ok=(
                    bool(descriptor_consumer_shim_result.shim_ok)
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_consumer_shim_changes_kernel_launch_args=(
                    bool(descriptor_consumer_shim_result.changes_kernel_launch_args)
                    if descriptor_consumer_shim_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_mode=(
                    kernel_arg_shadow_table_result.execution_mode
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_row_order_source=(
                    kernel_arg_shadow_table_result.row_order_source
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_row_count=(
                    int(kernel_arg_shadow_table_result.row_count)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_column_count=(
                    int(kernel_arg_shadow_table_result.column_count)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_schema_hash=(
                    kernel_arg_shadow_table_result.schema_hash
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_row_order_hash=(
                    kernel_arg_shadow_table_result.row_order_hash
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_ordered_row_hash=(
                    kernel_arg_shadow_table_result.ordered_row_hash
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count=(
                    int(kernel_arg_shadow_table_result.per_row_parity_ok_count)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_row_miss_count=(
                    int(kernel_arg_shadow_table_result.row_miss_count)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_stale_row_count=(
                    int(kernel_arg_shadow_table_result.stale_row_count)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_lifecycle_ok=(
                    bool(kernel_arg_shadow_table_result.lifecycle_ok)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_ok=(
                    bool(kernel_arg_shadow_table_result.table_ok)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_payload_bytes=(
                    int(kernel_arg_shadow_table_result.payload_bytes)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_ready_credit=(
                    bool(kernel_arg_shadow_table_result.ready_credit)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_changes_router=(
                    bool(kernel_arg_shadow_table_result.changes_router)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_changes_descriptor_order=(
                    bool(kernel_arg_shadow_table_result.changes_descriptor_order)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_changes_kernel_launch_args=(
                    bool(kernel_arg_shadow_table_result.changes_kernel_launch_args)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_kernel_arg_shadow_table_passed_to_kernel=(
                    bool(kernel_arg_shadow_table_result.passed_to_kernel)
                    if kernel_arg_shadow_table_result is not None
                    else None
                ),
                descriptor_prep_execution_ok=(
                    bool(descriptor_prep_result.execution_ok)
                    if descriptor_prep_result is not None
                    else None
                ),
                descriptor_prep_blocked_reason=descriptor_prep_blocked_reason,
                expected_key_hash=str(expected_hash) if expected_hash is not None else None,
                resident_address_count=resident_count,
                lookup_us=lookup_us,
                error=mapping_error,
            )
        )

    def maybe_reorder_prepared_expert_assignment(
        self,
        *,
        layer_id: int,
        sorted_token_ids: torch.Tensor | None,
        expert_ids: torch.Tensor,
        num_tokens_post_padded: torch.Tensor,
        block_size: int,
    ) -> tuple[torch.Tensor | None, torch.Tensor, torch.Tensor]:
        """P0/P1 descriptor consumer handle hook.

        The true vLLM/AWQ fused-MoE visitation handle is the block-level pair
        ``sorted_token_ids``/``expert_ids`` produced by
        ``_prepare_expert_assignment``.  P0 records the handle shape/hash and
        whether a layer-prior permutation would change the order.  P1 applies
        the same-multiset block permutation only when the calibrated gate and
        checksum evidence allow it.
        """

        sink = self.shadow_outcome_sink
        wants_assertion = str(
            self.shadow_descriptor_order_prelaunch_assertion_mode or "off"
        ).strip().lower() not in {"", "off", "none", "false", "0"}
        wants_reorder = bool(self.shadow_descriptor_order_reorder_mvp_enabled)
        wants_premap_mapping = self._premap_consumer_mapping_wanted()
        wants_descriptor_handle = bool(wants_assertion or wants_reorder)
        if sink is None or (not wants_descriptor_handle and not wants_premap_mapping):
            return sorted_token_ids, expert_ids, num_tokens_post_padded
        if wants_descriptor_handle and not hasattr(
            sink,
            "write_descriptor_prelaunch_assertion",
        ):
            return sorted_token_ids, expert_ids, num_tokens_post_padded
        if wants_premap_mapping and not hasattr(sink, "write_premap_consumer_mapping"):
            msg = (
                "shadow_emit_premap_consumer_mapping=True requires a sink with "
                "write_premap_consumer_mapping(event)."
            )
            raise TypeError(msg)
        layer_allowlist = self.shadow_descriptor_order_reorder_mvp_layer_allowlist
        if (
            wants_reorder
            and layer_allowlist is not None
            and int(layer_id) not in layer_allowlist
        ):
            return sorted_token_ids, expert_ids, num_tokens_post_padded

        start_ns = time.perf_counter_ns()
        normalized_mode = str(
            self.shadow_descriptor_order_prelaunch_assertion_mode or "off"
        ).strip().lower()
        handle_source = "fused_moe_prepare_expert_assignment"
        block_size = max(1, int(block_size))
        available = (
            sorted_token_ids is not None
            and sorted_token_ids.ndim == 1
            and expert_ids.ndim == 1
            and int(sorted_token_ids.numel()) >= block_size
        )
        block_count = 0
        active_experts_cpu: list[int] = []
        expert_order_hash = ""
        expert_multiset_hash = ""
        would_reorder = False
        same_multiset = False
        fallback_reason: str | None = None
        error: str | None = None
        reordered_sorted = sorted_token_ids
        reordered_experts = expert_ids
        permutation_us: float | None = None
        plan_build_us: float | None = None
        plan_group_order_hash: str | None = None
        plan_group_offsets_hash: str | None = None
        plan_group_count: int | None = None
        plan_avg_group_size: float | None = None
        plan_p95_group_size: float | None = None
        plan_max_group_size: int | None = None
        plan_cta_count: int | None = None
        clone_us: float | None = None
        index_select_us: float | None = None
        attribution_mode = str(
            self.shadow_descriptor_order_reorder_mvp_attribution_mode or "full"
        ).strip().lower()
        decision: dict[str, Any] = {
            "reorder_mvp_requested": wants_reorder,
            "reorder_mvp_selected_policy": "no_order",
            "reorder_mvp_applied": False,
        }
        context = get_active_moe_assignment_context()
        consumer_layer = context.get("routed_layer") if context is not None else None
        if wants_premap_mapping and not wants_descriptor_handle:
            mapping_start_ns = time.perf_counter_ns()
            mapping_error = None
            try:
                if not available:
                    mapping_error = "consumer_handle_unavailable"
                    active_for_mapping: list[int] = []
                else:
                    padded_count = int(
                        num_tokens_post_padded.detach().cpu().view(-1)[0].item()
                    )
                    block_count = min(
                        int(expert_ids.numel()),
                        max(0, (padded_count + block_size - 1) // block_size),
                    )
                    active_for_mapping = (
                        expert_ids[:block_count].detach().cpu().to(torch.long).tolist()
                    )
            except Exception as exc:  # pragma: no cover - defensive telemetry path
                mapping_error = f"{type(exc).__name__}: {exc}"
                active_for_mapping = []
            resolved_for_mapping = sorted(
                {
                    int(value)
                    for value in active_for_mapping
                    if 0 <= int(value) < int(self.shadow_num_experts)
                }
            )
            self._write_premap_consumer_mapping_from_experts(
                layer_id=int(layer_id),
                active_experts=[int(value) for value in active_for_mapping],
                consumer_layer=consumer_layer,
                prelaunch_boundary_source=handle_source,
                prelaunch_handle_available=bool(available),
                prelaunch_block_count=len(active_for_mapping),
                prelaunch_block_size=int(block_size),
                prelaunch_expert_order_hash=hash_ints(resolved_for_mapping),
                prelaunch_expert_multiset_hash=hash_ints(
                    sorted(int(value) for value in resolved_for_mapping)
                ),
                lookup_start_ns=mapping_start_ns,
                error=mapping_error,
            )
            return sorted_token_ids, expert_ids, num_tokens_post_padded
        try:
            if context is not None:
                context.pop("descriptor_order_wna16_indirect_plan", None)
            if not available:
                fallback_reason = "consumer_handle_unavailable"
                raise ValueError(fallback_reason)
            padded_count = int(num_tokens_post_padded.detach().cpu().view(-1)[0].item())
            block_count = min(
                int(expert_ids.numel()),
                max(0, (padded_count + block_size - 1) // block_size),
            )
            if block_count <= 0:
                fallback_reason = "empty_consumer_handle"
                raise ValueError(fallback_reason)
            active_experts_cpu = (
                expert_ids[:block_count].detach().cpu().to(torch.long).tolist()
            )
            resolved_experts_cpu = sorted(
                {
                    int(value)
                    for value in active_experts_cpu
                    if 0 <= int(value) < int(self.shadow_num_experts)
                }
            )
            self._write_premap_consumer_mapping_from_experts(
                layer_id=int(layer_id),
                active_experts=[int(value) for value in active_experts_cpu],
                consumer_layer=consumer_layer,
                prelaunch_boundary_source=handle_source,
                prelaunch_handle_available=bool(available),
                prelaunch_block_count=int(block_count),
                prelaunch_block_size=int(block_size),
                prelaunch_expert_order_hash=hash_ints(resolved_experts_cpu),
                prelaunch_expert_multiset_hash=hash_ints(
                    sorted(int(value) for value in resolved_experts_cpu)
                ),
            )
            if not wants_descriptor_handle:
                return sorted_token_ids, expert_ids, num_tokens_post_padded
            expert_order_hash = hash_ints(active_experts_cpu)
            expert_multiset_hash = hash_ints(sorted(int(x) for x in active_experts_cpu))
            permutation_start_ns = time.perf_counter_ns()
            permutation = self._descriptor_order_expert_block_permutation(
                layer_id=int(layer_id),
                expert_ids=active_experts_cpu,
            )
            permutation_us = (time.perf_counter_ns() - permutation_start_ns) / 1000.0
            plan_start_ns = time.perf_counter_ns()
            plan = self._descriptor_order_expert_block_group_plan(
                layer_id=int(layer_id),
                expert_ids=active_experts_cpu,
            )
            plan_build_us = (time.perf_counter_ns() - plan_start_ns) / 1000.0
            plan_group_order_hash = plan["group_order_hash"]
            plan_group_offsets_hash = plan["group_offsets_hash"]
            plan_group_count = int(plan["group_count"])
            plan_avg_group_size = float(plan["avg_group_size"])
            plan_p95_group_size = float(plan["p95_group_size"])
            plan_max_group_size = int(plan["max_group_size"])
            plan_source_spans_contiguous = bool(
                plan.get("source_spans_contiguous", True)
            )
            plan_structure_valid = bool(
                self._descriptor_order_expert_block_group_plan_is_valid(
                    plan=plan,
                    block_count=block_count,
                )
            )
            groups_per_cta = max(1, int(self.shadow_descriptor_order_groups_per_cta))
            plan_cta_count = (
                (int(plan_group_count) + groups_per_cta - 1) // groups_per_cta
                if plan_group_count is not None
                else None
            )
            would_reorder = permutation != list(range(block_count))
            if (
                "source_block" in attribution_mode
                and len(permutation) != int(block_count)
            ):
                fallback_reason = "consumer_handle_source_block_count_mismatch"
                same_multiset = False
            elif any(
                int(source_idx) < 0 or int(source_idx) >= int(block_count)
                for source_idx in permutation
            ):
                fallback_reason = "consumer_handle_permutation_index_oob"
                same_multiset = False
            else:
                reordered_expert_ids_cpu = [active_experts_cpu[i] for i in permutation]
                same_multiset = sorted(active_experts_cpu) == sorted(
                    reordered_expert_ids_cpu
                )
            if fallback_reason is None and not same_multiset:
                fallback_reason = "consumer_handle_multiset_mismatch"
            elif not would_reorder:
                fallback_reason = "already_in_prior_order"
            decision = self._descriptor_order_reorder_mvp_decision(
                same_multiset=bool(same_multiset),
                group_count=int(block_count),
                layer_id=int(layer_id),
                apply_supported=True,
            )
            if fallback_reason is not None:
                decision["reorder_mvp_selected_policy"] = "no_order"
                decision["reorder_mvp_applied"] = False
                decision["reorder_mvp_fallback_reason"] = fallback_reason
            if bool(decision.get("reorder_mvp_applied", False)):
                assert sorted_token_ids is not None
                active_token_count = int(block_count * block_size)
                if attribution_mode in {
                    "permutation_compute_only",
                    "permutation_only",
                    "compute_only",
                }:
                    decision["reorder_mvp_selected_policy"] = "no_order"
                    decision["reorder_mvp_applied"] = False
                    decision["reorder_mvp_fallback_reason"] = (
                        "attribution_permutation_compute_only"
                    )
                elif attribution_mode in {
                    "indirect_plan_only",
                    "producer_plan_only",
                    "group_plan_only",
                    "indirect_only",
                }:
                    decision["reorder_mvp_selected_policy"] = "no_order"
                    decision["reorder_mvp_applied"] = False
                    decision["reorder_mvp_fallback_reason"] = (
                        "attribution_indirect_plan_only"
                    )
                elif attribution_mode in {
                    "producer_group_plan",
                    "producer_group_copy",
                    "producer_side_group_plan",
                    "producer_side_group_copy",
                    "group_plan_producer",
                }:
                    if not plan_structure_valid:
                        decision["reorder_mvp_selected_policy"] = "no_order"
                        decision["reorder_mvp_applied"] = False
                        decision["reorder_mvp_fallback_reason"] = (
                            "consumer_handle_invalid_group_plan"
                        )
                    elif not plan_source_spans_contiguous:
                        decision["reorder_mvp_selected_policy"] = "no_order"
                        decision["reorder_mvp_applied"] = False
                        decision["reorder_mvp_fallback_reason"] = (
                            "consumer_handle_noncontiguous_expert_blocks"
                        )
                    else:
                        from mtp_expert_prefetch.tracing.vllm_wna16_group_plan import (
                            reorder_prepared_expert_assignment_group_plan,
                        )

                        group_order = torch.tensor(
                            plan.get("group_order", []),
                            dtype=torch.int32,
                            device=expert_ids.device,
                        )
                        group_offsets = torch.tensor(
                            plan.get("group_offsets", [0]),
                            dtype=torch.int32,
                            device=expert_ids.device,
                        )
                        group_source_starts = torch.tensor(
                            plan.get("group_source_starts", []),
                            dtype=torch.int32,
                            device=expert_ids.device,
                        )
                        reordered_sorted, reordered_experts = (
                            reorder_prepared_expert_assignment_group_plan(
                                sorted_token_ids=sorted_token_ids,
                                expert_ids=expert_ids,
                                group_order=group_order,
                                group_offsets=group_offsets,
                                group_source_starts=group_source_starts,
                                max_group_blocks=max(1, int(plan_max_group_size or 1)),
                                block_size=block_size,
                                active_block_count=block_count,
                            )
                        )
                        decision["reorder_mvp_selected_policy"] = (
                            "layer_prior_frequency_producer_group_plan"
                        )
                        decision["reorder_mvp_applied"] = True
                elif attribution_mode in {
                    "fused_producer",
                    "producer_fused",
                    "fused_layer_prior_producer",
                    "fused_moe_align",
                    "layer_prior_fused_producer",
                }:
                    context = get_active_moe_assignment_context()
                    skip_reason = (
                        context.get("descriptor_order_fused_producer_skip_reason")
                        if context is not None
                        else None
                    )
                    decision["reorder_mvp_selected_policy"] = "no_order"
                    decision["reorder_mvp_applied"] = False
                    decision["reorder_mvp_fallback_reason"] = (
                        f"fused_producer_skip:{skip_reason or 'not_applied'}"
                    )
                elif attribution_mode in {
                    "source_block_ids_kernel",
                    "kernel_source_block_ids",
                    "source_block_kernel",
                    "source_block_ids_packed_kernel",
                    "kernel_source_block_ids_packed",
                    "source_block_packed_kernel",
                }:
                    context = get_active_moe_assignment_context()
                    if context is None:
                        decision["reorder_mvp_selected_policy"] = "no_order"
                        decision["reorder_mvp_applied"] = False
                        decision["reorder_mvp_fallback_reason"] = (
                            "missing_assignment_context"
                        )
                    elif len(permutation) != int(block_count):
                        decision["reorder_mvp_selected_policy"] = "no_order"
                        decision["reorder_mvp_applied"] = False
                        decision["reorder_mvp_fallback_reason"] = (
                            "consumer_handle_source_block_count_mismatch"
                        )
                    else:
                        use_packed_source_blocks = "packed" in attribution_mode
                        indirect_plan: dict[str, Any] = {
                            "variant": "source_block_ids",
                            "source_block_ids": torch.tensor(
                                permutation,
                                dtype=torch.int32,
                                device=expert_ids.device,
                            ),
                            "source_block_ids_packed": False,
                            "source_block_count": int(len(permutation)),
                            "active_block_count": int(block_count),
                            "max_groups": max(1, int(plan_group_count or 1)),
                        }
                        if use_packed_source_blocks:
                            packed_source_block_ids: list[int] = []
                            for source_idx in permutation:
                                source_i = int(source_idx)
                                expert_i = int(active_experts_cpu[source_i])
                                packed_expert = (
                                    1023 if expert_i < 0 else (expert_i & 1023)
                                )
                                packed_source_block_ids.append(
                                    (source_i << 10) | packed_expert
                                )
                            indirect_plan["packed_source_block_ids"] = torch.tensor(
                                packed_source_block_ids,
                                dtype=torch.int32,
                                device=expert_ids.device,
                            )
                            indirect_plan["source_block_ids_packed"] = True
                        context["descriptor_order_wna16_indirect_plan"] = indirect_plan
                        decision["reorder_mvp_selected_policy"] = (
                            "layer_prior_frequency_source_block_ids_kernel"
                        )
                        decision["reorder_mvp_applied"] = True
                elif attribution_mode in {
                    "group_plan_kernel",
                    "two_level_group_plan_kernel",
                    "kernel_group_plan",
                }:
                    context = get_active_moe_assignment_context()
                    if not plan_structure_valid:
                        decision["reorder_mvp_selected_policy"] = "no_order"
                        decision["reorder_mvp_applied"] = False
                        decision["reorder_mvp_fallback_reason"] = (
                            "consumer_handle_invalid_group_plan"
                        )
                    elif not plan_source_spans_contiguous:
                        decision["reorder_mvp_selected_policy"] = "no_order"
                        decision["reorder_mvp_applied"] = False
                        decision["reorder_mvp_fallback_reason"] = (
                            "consumer_handle_noncontiguous_expert_blocks"
                        )
                    elif context is None:
                        decision["reorder_mvp_selected_policy"] = "no_order"
                        decision["reorder_mvp_applied"] = False
                        decision["reorder_mvp_fallback_reason"] = (
                            "missing_assignment_context"
                        )
                    else:
                        context["descriptor_order_wna16_indirect_plan"] = {
                            "variant": "group_plan",
                            "group_order": torch.tensor(
                                plan.get("group_order", []),
                                dtype=torch.int32,
                                device=expert_ids.device,
                            ),
                            "group_offsets": torch.tensor(
                                plan.get("group_offsets", [0]),
                                dtype=torch.int32,
                                device=expert_ids.device,
                            ),
                            "group_source_starts": torch.tensor(
                                plan.get("group_source_starts", []),
                                dtype=torch.int32,
                                device=expert_ids.device,
                            ),
                            "max_groups": max(1, int(plan_group_count or 1)),
                            "max_group_blocks": max(1, int(plan_max_group_size or 1)),
                        }
                        decision["reorder_mvp_selected_policy"] = (
                            "layer_prior_frequency_group_plan_kernel"
                        )
                        decision["reorder_mvp_applied"] = True
                elif attribution_mode in {"clone_only", "clone"}:
                    clone_start_ns = time.perf_counter_ns()
                    _expert_clone = expert_ids.clone()
                    _sorted_clone = sorted_token_ids.clone()
                    clone_us = (time.perf_counter_ns() - clone_start_ns) / 1000.0
                    decision["reorder_mvp_selected_policy"] = "no_order"
                    decision["reorder_mvp_applied"] = False
                    decision["reorder_mvp_fallback_reason"] = "attribution_clone_only"
                elif attribution_mode in {"index_select_only", "select_only"}:
                    perm_tensor = torch.tensor(
                        permutation,
                        dtype=torch.long,
                        device=expert_ids.device,
                    )
                    index_start_ns = time.perf_counter_ns()
                    _selected_experts = expert_ids[:block_count].index_select(
                        0,
                        perm_tensor,
                    )
                    token_chunks = sorted_token_ids[:active_token_count].view(
                        block_count,
                        block_size,
                    )
                    _selected_tokens = token_chunks.index_select(
                        0,
                        perm_tensor,
                    ).reshape(-1)
                    index_select_us = (
                        time.perf_counter_ns() - index_start_ns
                    ) / 1000.0
                    decision["reorder_mvp_selected_policy"] = "no_order"
                    decision["reorder_mvp_applied"] = False
                    decision["reorder_mvp_fallback_reason"] = (
                        "attribution_index_select_only"
                    )
                elif attribution_mode in {"full", "apply"}:
                    perm_tensor = torch.tensor(
                        permutation,
                        dtype=torch.long,
                        device=expert_ids.device,
                    )
                    clone_start_ns = time.perf_counter_ns()
                    reordered_experts = expert_ids.clone()
                    reordered_sorted = sorted_token_ids.clone()
                    clone_us = (time.perf_counter_ns() - clone_start_ns) / 1000.0
                    index_start_ns = time.perf_counter_ns()
                    reordered_experts[:block_count] = expert_ids[
                        :block_count
                    ].index_select(0, perm_tensor)
                    token_chunks = sorted_token_ids[:active_token_count].view(
                        block_count,
                        block_size,
                    )
                    reordered_sorted[:active_token_count] = token_chunks.index_select(
                        0,
                        perm_tensor,
                    ).reshape(-1)
                    index_select_us = (
                        time.perf_counter_ns() - index_start_ns
                    ) / 1000.0
                else:
                    decision["reorder_mvp_selected_policy"] = "no_order"
                    decision["reorder_mvp_applied"] = False
                    decision["reorder_mvp_fallback_reason"] = (
                        f"unknown_attribution_mode:{attribution_mode}"
                    )
        except Exception as exc:
            if fallback_reason is None:
                fallback_reason = f"{type(exc).__name__}: {exc}"
            error = fallback_reason
            decision.update(
                {
                    "reorder_mvp_selected_policy": "no_order",
                    "reorder_mvp_applied": False,
                    "reorder_mvp_fallback_reason": fallback_reason,
                }
            )

        dump_us = (time.perf_counter_ns() - start_ns) / 1000.0
        event = ShadowDescriptorPrelaunchAssertEvent(
            event_id=ShadowEventId(
                request_id=str(self.request_id),
                sequence_id=int(self.sequence_id),
                token_index=int(self.shadow_descriptor_order_event_token_index),
                layer=int(layer_id),
            ),
            assertion_mode=normalized_mode or "off",
            mapping_source=handle_source,
            router_mapping_source=None,
            same_multiset=bool(same_multiset),
            counts_match=True,
            prelaunch_tile_multiset_hash=expert_multiset_hash,
            router_derived_tile_multiset_hash=expert_multiset_hash,
            prelaunch_request_count=int(block_count),
            router_derived_request_count=int(block_count),
            prelaunch_group_count=int(len(set(active_experts_cpu))) if block_count else 0,
            router_derived_group_count=(
                int(len(set(active_experts_cpu))) if block_count else 0
            ),
            error=error,
            dump_us=dump_us,
            consumer_handle_source=handle_source,
            consumer_handle_available=bool(available),
            consumer_handle_block_count=int(block_count),
            consumer_handle_block_size=int(block_size),
            consumer_handle_expert_order_hash=expert_order_hash or None,
            consumer_handle_expert_multiset_hash=expert_multiset_hash or None,
            consumer_handle_would_reorder=bool(would_reorder),
            consumer_handle_same_multiset=bool(same_multiset),
            consumer_handle_applied=bool(decision.get("reorder_mvp_applied", False)),
            consumer_handle_fallback_reason=decision.get(
                "reorder_mvp_fallback_reason"
            ),
            consumer_handle_attribution_mode=attribution_mode,
            consumer_handle_permutation_us=permutation_us,
            consumer_handle_plan_build_us=plan_build_us,
            consumer_handle_plan_group_order_hash=plan_group_order_hash,
            consumer_handle_plan_group_offsets_hash=plan_group_offsets_hash,
            consumer_handle_plan_group_count=plan_group_count,
            consumer_handle_plan_avg_group_size=plan_avg_group_size,
            consumer_handle_plan_p95_group_size=plan_p95_group_size,
            consumer_handle_plan_max_group_size=plan_max_group_size,
            consumer_handle_plan_cta_count=plan_cta_count,
            consumer_handle_clone_us=clone_us,
            consumer_handle_index_select_us=index_select_us,
            **decision,
        )
        if bool(self.shadow_descriptor_order_emit_consumer_handle_events):
            sink.write_descriptor_prelaunch_assertion(event)
        self._last_descriptor_consumer_handle_by_layer[int(layer_id)] = {
            "source": handle_source,
            "available": bool(available),
            "block_count": int(block_count),
            "block_size": int(block_size),
            "would_reorder": bool(would_reorder),
            "same_multiset": bool(same_multiset),
            "applied": bool(decision.get("reorder_mvp_applied", False)),
            "selected_policy": decision.get("reorder_mvp_selected_policy"),
            "fallback_reason": decision.get("reorder_mvp_fallback_reason"),
            "gate_allow": decision.get("reorder_mvp_gate_allow"),
            "gate_reason": decision.get("reorder_mvp_gate_reason"),
            "candidate_speedup": decision.get(
                "reorder_mvp_candidate_speedup_median_vs_no_order"
            ),
            "attribution_mode": attribution_mode,
            "permutation_us": permutation_us,
            "plan_build_us": plan_build_us,
            "plan_group_order_hash": plan_group_order_hash,
            "plan_group_offsets_hash": plan_group_offsets_hash,
            "plan_group_count": plan_group_count,
            "plan_avg_group_size": plan_avg_group_size,
            "plan_p95_group_size": plan_p95_group_size,
            "plan_max_group_size": plan_max_group_size,
            "plan_cta_count": plan_cta_count,
            "clone_us": clone_us,
            "index_select_us": index_select_us,
        }
        if bool(decision.get("reorder_mvp_applied", False)):
            return reordered_sorted, reordered_experts, num_tokens_post_padded
        return sorted_token_ids, expert_ids, num_tokens_post_padded

    def _descriptor_order_prior_rank_tensor(
        self,
        *,
        layer_id: int,
        device: torch.device,
        num_experts: int,
    ) -> torch.Tensor | None:
        prior = self.shadow_descriptor_order_prior
        if prior is None:
            return None
        num_experts = int(num_experts)
        if num_experts <= 0:
            return None
        tiles_per_expert = max(1, int(self.shadow_descriptor_order_tiles_per_expert))
        prior_order = prior.order_for_layer(int(layer_id))
        default_rank = len(prior_order) + 1
        cache_key = (
            int(layer_id),
            str(device),
            int(num_experts),
            int(tiles_per_expert),
            str(self.shadow_descriptor_order_prior_hash or ""),
            str(self.shadow_descriptor_order_prior_id or ""),
        )
        cached = self._descriptor_order_prior_rank_tensor_cache.get(cache_key)
        if cached is not None:
            return cached
        ranks = torch.full(
            (num_experts,),
            int(default_rank),
            dtype=torch.int32,
            device=device,
        )
        if prior_order:
            rank_pairs: list[tuple[int, int]] = []
            seen: set[int] = set()
            for rank, tile_id in enumerate(prior_order):
                expert = int(tile_id) // tiles_per_expert
                if 0 <= expert < num_experts and expert not in seen:
                    seen.add(expert)
                    rank_pairs.append((expert, int(rank)))
            if rank_pairs:
                indices = torch.tensor(
                    [expert for expert, _rank in rank_pairs],
                    dtype=torch.long,
                    device=device,
                )
                values = torch.tensor(
                    [_rank for _expert, _rank in rank_pairs],
                    dtype=torch.int32,
                    device=device,
                )
                ranks[indices] = values
        self._descriptor_order_prior_rank_tensor_cache[cache_key] = ranks
        return ranks

    def _descriptor_order_direct_placeholders(
        self,
        *,
        device: torch.device,
        routed_count: int,
        block_size: int,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        routed_count = int(routed_count)
        block_size = int(block_size)
        if routed_count <= 0 or block_size <= 0:
            raise ValueError("direct-topk placeholders require positive sizes")
        cache_key = (str(device), routed_count, block_size)
        cached = self._descriptor_order_direct_placeholder_cache.get(cache_key)
        if cached is not None:
            return cached
        sorted_token_ids = torch.empty(
            (routed_count * block_size,),
            dtype=torch.int32,
            device=device,
        )
        expert_ids = torch.empty((routed_count,), dtype=torch.int32, device=device)
        num_tokens_post_padded = torch.empty((1,), dtype=torch.int32, device=device)
        num_tokens_post_padded.fill_(routed_count)
        cached = (sorted_token_ids, expert_ids, num_tokens_post_padded)
        self._descriptor_order_direct_placeholder_cache[cache_key] = cached
        return cached

    def maybe_prepare_decode_expert_assignment_layer_prior(
        self,
        *,
        layer_id: int,
        topk_ids: torch.Tensor,
        config: dict[str, Any],
        num_tokens: int,
        top_k_num: int,
        global_num_experts: int,
        expert_map: torch.Tensor | None,
        use_int8_w8a16: bool,
        use_int4_w4a16: bool,
        block_shape: list[int] | None,
        ignore_invalid_experts: bool,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor] | None:
        context = get_active_moe_assignment_context()

        def skip(reason: str) -> None:
            if context is not None:
                context["descriptor_order_fused_producer_skip_reason"] = str(reason)

        attribution_mode = str(
            self.shadow_descriptor_order_reorder_mvp_attribution_mode or "full"
        ).strip().lower()
        if attribution_mode not in {
            "fused_producer",
            "producer_fused",
            "fused_layer_prior_producer",
            "fused_moe_align",
            "layer_prior_fused_producer",
            "direct_topk_kernel",
            "direct_topk_layer_prior",
            "direct_topk_identity",
            "direct_topk_identity_kernel",
            "fused_direct_topk",
            "direct_topk_consumer",
        }:
            skip("attribution_mode_not_fused")
            return None
        if not bool(self.shadow_descriptor_order_reorder_mvp_enabled):
            skip("reorder_mvp_disabled")
            return None
        if str(self.shadow_descriptor_order_reorder_mvp_apply_mode).lower() != "apply":
            skip("apply_mode_not_apply")
            return None
        layer_allowlist = self.shadow_descriptor_order_reorder_mvp_layer_allowlist
        if layer_allowlist is not None and int(layer_id) not in layer_allowlist:
            skip("layer_not_allowed")
            return None
        if int(num_tokens) != 1 or int(top_k_num) != int(topk_ids.numel()):
            skip(
                f"shape_mismatch:num_tokens={int(num_tokens)},top_k_num={int(top_k_num)},numel={int(topk_ids.numel())}"
            )
            return None
        if topk_ids.ndim != 2 or int(topk_ids.shape[0]) != 1:
            skip(f"not_single_token_topk_shape:{tuple(topk_ids.shape)}")
            return None
        if not ((use_int8_w8a16 or use_int4_w4a16) and block_shape is not None):
            skip("not_wna16_quant_path")
            return None
        block_size = int(config.get("BLOCK_SIZE_M", 0))
        if block_size <= 0:
            skip("invalid_block_size")
            return None
        if attribution_mode in {
            "direct_topk_identity",
            "direct_topk_identity_kernel",
        }:
            if context is None:
                skip("missing_assignment_context")
                return None
            if int(topk_ids.numel()) != 8 or int(top_k_num) != 8:
                skip(f"direct_topk_identity_requires_top8:top_k_num={int(top_k_num)}")
                return None
            start_ns = time.perf_counter_ns()
            context["descriptor_order_wna16_indirect_plan"] = {
                "variant": "direct_topk_identity",
                "topk_ids": topk_ids,
                "expert_map": expert_map,
                "ignore_invalid_experts": bool(ignore_invalid_experts),
                "num_tokens": int(num_tokens),
                "top_k_num": int(top_k_num),
                "global_num_experts": int(global_num_experts),
                "use_int8_w8a16": bool(use_int8_w8a16),
                "use_int4_w4a16": bool(use_int4_w4a16),
                "block_shape": block_shape,
            }
            sorted_token_ids, expert_ids, num_tokens_post_padded = (
                self._descriptor_order_direct_placeholders(
                    device=topk_ids.device,
                    routed_count=int(topk_ids.numel()),
                    block_size=block_size,
                )
            )
            setup_us = (time.perf_counter_ns() - start_ns) / 1000.0
            context.pop("descriptor_order_fused_producer_skip_reason", None)
            routed_count = int(topk_ids.numel())
            self._last_descriptor_consumer_handle_by_layer[int(layer_id)] = {
                "source": "direct_topk_identity_consumer",
                "available": True,
                "block_count": None
                if expert_map is not None and bool(ignore_invalid_experts)
                else routed_count,
                "block_size": int(block_size),
                "would_reorder": False,
                "same_multiset": True,
                "applied": True,
                "attribution_mode": attribution_mode,
                "permutation_us": setup_us,
                "plan_build_us": setup_us,
                "plan_group_order_hash": None,
                "plan_group_offsets_hash": None,
                "plan_group_count": None
                if expert_map is not None and bool(ignore_invalid_experts)
                else routed_count,
                "plan_avg_group_size": 1.0,
                "plan_p95_group_size": 1.0,
                "plan_max_group_size": 1,
                "plan_cta_count": routed_count,
                "clone_us": None,
                "index_select_us": None,
                "selected_policy": "direct_topk_identity_kernel",
                "fallback_reason": None,
                "gate_allow": True,
                "gate_reason": "identity_no_reorder",
                "candidate_speedup": None,
            }
            return sorted_token_ids, expert_ids, num_tokens_post_padded
        prior_rank = self._descriptor_order_prior_rank_tensor(
            layer_id=int(layer_id),
            device=topk_ids.device,
            num_experts=int(global_num_experts),
        )
        if prior_rank is None:
            skip("missing_prior_rank")
            return None
        decision = self._descriptor_order_reorder_mvp_decision(
            same_multiset=True,
            group_count=int(topk_ids.numel()),
            layer_id=int(layer_id),
            apply_supported=True,
        )
        if not bool(decision.get("reorder_mvp_applied", False)):
            skip(str(decision.get("reorder_mvp_fallback_reason") or "gate_not_applied"))
            return None
        if attribution_mode in {
            "direct_topk_kernel",
            "direct_topk_layer_prior",
            "direct_topk_identity",
            "direct_topk_identity_kernel",
            "fused_direct_topk",
            "direct_topk_consumer",
        }:
            if context is None:
                skip("missing_assignment_context")
                return None
            start_ns = time.perf_counter_ns()
            context["descriptor_order_wna16_indirect_plan"] = {
                "variant": "direct_topk_layer_prior",
                "topk_ids": topk_ids,
                "expert_map": expert_map,
                "prior_rank": prior_rank,
                "ignore_invalid_experts": bool(ignore_invalid_experts),
                "num_tokens": int(num_tokens),
                "top_k_num": int(top_k_num),
                "global_num_experts": int(global_num_experts),
                "use_int8_w8a16": bool(use_int8_w8a16),
                "use_int4_w4a16": bool(use_int4_w4a16),
                "block_shape": block_shape,
            }
            sorted_token_ids, expert_ids, num_tokens_post_padded = (
                self._descriptor_order_direct_placeholders(
                    device=topk_ids.device,
                    routed_count=int(topk_ids.numel()),
                    block_size=block_size,
                )
            )
            setup_us = (time.perf_counter_ns() - start_ns) / 1000.0
            context.pop("descriptor_order_fused_producer_skip_reason", None)
            routed_count = int(topk_ids.numel())
            self._last_descriptor_consumer_handle_by_layer[int(layer_id)] = {
                "source": "direct_topk_layer_prior_consumer",
                "available": True,
                "block_count": None
                if expert_map is not None and bool(ignore_invalid_experts)
                else routed_count,
                "block_size": int(block_size),
                "would_reorder": True,
                "same_multiset": True,
                "applied": True,
                "attribution_mode": attribution_mode,
                "permutation_us": setup_us,
                "plan_build_us": setup_us,
                "plan_group_order_hash": None,
                "plan_group_offsets_hash": None,
                "plan_group_count": None
                if expert_map is not None and bool(ignore_invalid_experts)
                else routed_count,
                "plan_avg_group_size": 1.0,
                "plan_p95_group_size": 1.0,
                "plan_max_group_size": 1,
                "plan_cta_count": routed_count,
                "clone_us": None,
                "index_select_us": None,
                "selected_policy": "layer_prior_frequency_direct_topk_kernel",
                "fallback_reason": None,
                "gate_allow": decision.get("reorder_mvp_gate_allow"),
                "gate_reason": decision.get("reorder_mvp_gate_reason"),
                "candidate_speedup": decision.get(
                    "reorder_mvp_candidate_speedup_median_vs_no_order"
                ),
            }
            return sorted_token_ids, expert_ids, num_tokens_post_padded

        from mtp_expert_prefetch.tracing.vllm_wna16_group_plan import (
            prepare_decode_expert_assignment_layer_prior,
        )

        start_ns = time.perf_counter_ns()
        sorted_token_ids, expert_ids, num_tokens_post_padded = (
            prepare_decode_expert_assignment_layer_prior(
                topk_ids=topk_ids,
                expert_map=expert_map,
                prior_rank=prior_rank,
                block_size=block_size,
                ignore_invalid_experts=bool(ignore_invalid_experts),
            )
        )
        producer_us = (time.perf_counter_ns() - start_ns) / 1000.0
        if context is not None:
            context.pop("descriptor_order_fused_producer_skip_reason", None)
        if not bool(self.shadow_descriptor_order_emit_consumer_handle_events):
            routed_count = int(topk_ids.numel())
            active_block_count: int | None = routed_count
            if expert_map is not None and bool(ignore_invalid_experts):
                # Avoid a GPU->CPU synchronization in the hot decode path.  The
                # exact filtered count remains available in debug mode via
                # consumer-handle events.
                active_block_count = None
            self._last_descriptor_consumer_handle_by_layer[int(layer_id)] = {
                "source": "fused_decode_layer_prior_producer",
                "available": True,
                "block_count": active_block_count,
                "block_size": int(block_size),
                "would_reorder": True,
                "same_multiset": True,
                "applied": True,
                "attribution_mode": attribution_mode,
                "permutation_us": producer_us,
                "plan_build_us": producer_us,
                "plan_group_order_hash": None,
                "plan_group_offsets_hash": None,
                "plan_group_count": active_block_count,
                "plan_avg_group_size": 1.0 if active_block_count is not None else None,
                "plan_p95_group_size": 1.0 if active_block_count is not None else None,
                "plan_max_group_size": 1 if active_block_count is not None else None,
                "plan_cta_count": active_block_count,
                "clone_us": None,
                "index_select_us": None,
                "selected_policy": "layer_prior_frequency_fused_producer",
                "fallback_reason": None,
                "gate_allow": decision.get("reorder_mvp_gate_allow"),
                "gate_reason": decision.get("reorder_mvp_gate_reason"),
                "candidate_speedup": decision.get(
                    "reorder_mvp_candidate_speedup_median_vs_no_order"
                ),
            }
            return sorted_token_ids, expert_ids, num_tokens_post_padded
        raw_experts_cpu = topk_ids.detach().view(-1).cpu().to(torch.long).tolist()
        active_experts_cpu = [
            int(expert)
            for expert in raw_experts_cpu
            if 0 <= int(expert) < int(global_num_experts)
        ]
        if expert_map is not None:
            expert_map_cpu = expert_map.detach().cpu().to(torch.long)
            mapped_experts_cpu: list[int] = []
            for expert in active_experts_cpu:
                if 0 <= int(expert) < int(expert_map_cpu.numel()):
                    mapped = int(expert_map_cpu[int(expert)].item())
                    if mapped >= 0 or not bool(ignore_invalid_experts):
                        mapped_experts_cpu.append(mapped)
                elif not bool(ignore_invalid_experts):
                    mapped_experts_cpu.append(-1)
            active_experts_cpu = mapped_experts_cpu
        active_block_count = int(len(active_experts_cpu))
        prior = self.shadow_descriptor_order_prior
        default_rank = active_block_count + 1
        rank_by_expert: dict[int, int] = {}
        if prior is not None:
            prior_order = prior.order_for_layer(int(layer_id))
            default_rank = len(prior_order) + 1
            tiles_per_expert = max(1, int(self.shadow_descriptor_order_tiles_per_expert))
            for rank, tile_id in enumerate(prior_order):
                expert = int(tile_id) // tiles_per_expert
                rank_by_expert.setdefault(expert, int(rank))
        active_experts_output_cpu = [
            expert
            for _idx, expert in sorted(
                enumerate(active_experts_cpu),
                key=lambda item: (rank_by_expert.get(int(item[1]), default_rank), item[0]),
            )
        ]
        self._last_descriptor_consumer_handle_by_layer[int(layer_id)] = {
            "source": "fused_decode_layer_prior_producer",
            "available": True,
            "block_count": active_block_count,
            "block_size": int(block_size),
            "would_reorder": True,
            "same_multiset": True,
            "applied": True,
            "attribution_mode": attribution_mode,
            "permutation_us": producer_us,
            "plan_build_us": producer_us,
            "plan_group_order_hash": hash_ints(active_experts_output_cpu),
            "plan_group_offsets_hash": hash_ints(
                list(range(0, active_block_count + 1))
            ),
            "plan_group_count": active_block_count,
            "plan_avg_group_size": 1.0,
            "plan_p95_group_size": 1.0,
            "plan_max_group_size": 1,
            "plan_cta_count": active_block_count,
            "clone_us": None,
            "index_select_us": None,
            "selected_policy": "layer_prior_frequency_fused_producer",
            "fallback_reason": None,
            "gate_allow": decision.get("reorder_mvp_gate_allow"),
            "gate_reason": decision.get("reorder_mvp_gate_reason"),
            "candidate_speedup": decision.get(
                "reorder_mvp_candidate_speedup_median_vs_no_order"
            ),
        }
        return sorted_token_ids, expert_ids, num_tokens_post_padded

    def write_descriptor_layer_timing(
        self,
        *,
        layer_id: int,
        apply_us: float,
        num_tokens: int | None = None,
        phase: str | None = None,
    ) -> None:
        if not bool(self.shadow_emit_descriptor_layer_timing):
            return
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_descriptor_layer_timing"):
            return
        handle = self._last_descriptor_consumer_handle_by_layer.get(int(layer_id), {})
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.shadow_descriptor_order_event_token_index),
            layer=int(layer_id),
        )
        sink.write_descriptor_layer_timing(
            {
                "event_type": "descriptor_layer_timing",
                **event_id.as_dict(),
                "descriptor_order_layer_apply_us": float(apply_us),
                "descriptor_order_layer_num_tokens": (
                    int(num_tokens) if num_tokens is not None else None
                ),
                "descriptor_order_layer_phase": str(phase) if phase else None,
                "descriptor_order_layer_phase_source": "num_tokens_heuristic",
                "descriptor_order_reorder_mvp_apply_mode": str(
                    self.shadow_descriptor_order_reorder_mvp_apply_mode
                ),
                "descriptor_order_reorder_mvp_enabled": bool(
                    self.shadow_descriptor_order_reorder_mvp_enabled
                ),
                "descriptor_order_consumer_handle_source": handle.get("source"),
                "descriptor_order_consumer_handle_available": handle.get("available"),
                "descriptor_order_consumer_handle_block_count": handle.get("block_count"),
                "descriptor_order_consumer_handle_block_size": handle.get("block_size"),
                "descriptor_order_consumer_handle_would_reorder": handle.get(
                    "would_reorder"
                ),
                "descriptor_order_consumer_handle_same_multiset": handle.get(
                    "same_multiset"
                ),
                "descriptor_order_consumer_handle_applied": handle.get("applied"),
                "descriptor_order_consumer_handle_attribution_mode": handle.get(
                    "attribution_mode"
                ),
                "descriptor_order_consumer_handle_permutation_us": handle.get(
                    "permutation_us"
                ),
                "descriptor_order_consumer_handle_plan_build_us": handle.get(
                    "plan_build_us"
                ),
                "descriptor_order_consumer_handle_plan_group_order_hash": handle.get(
                    "plan_group_order_hash"
                ),
                "descriptor_order_consumer_handle_plan_group_offsets_hash": handle.get(
                    "plan_group_offsets_hash"
                ),
                "descriptor_order_consumer_handle_plan_group_count": handle.get(
                    "plan_group_count"
                ),
                "descriptor_order_consumer_handle_plan_avg_group_size": handle.get(
                    "plan_avg_group_size"
                ),
                "descriptor_order_consumer_handle_plan_p95_group_size": handle.get(
                    "plan_p95_group_size"
                ),
                "descriptor_order_consumer_handle_plan_max_group_size": handle.get(
                    "plan_max_group_size"
                ),
                "descriptor_order_consumer_handle_plan_cta_count": handle.get(
                    "plan_cta_count"
                ),
                "descriptor_order_consumer_handle_clone_us": handle.get("clone_us"),
                "descriptor_order_consumer_handle_index_select_us": handle.get(
                    "index_select_us"
                ),
                "descriptor_order_reorder_mvp_selected_policy": handle.get(
                    "selected_policy"
                ),
                "descriptor_order_reorder_mvp_fallback_reason": handle.get(
                    "fallback_reason"
                ),
                "descriptor_order_reorder_mvp_gate_allow": handle.get("gate_allow"),
                "descriptor_order_reorder_mvp_gate_reason": handle.get("gate_reason"),
                "descriptor_order_reorder_mvp_candidate_speedup_median_vs_no_order": (
                    handle.get("candidate_speedup")
                ),
            }
        )

    def write_wna16_kernel_timing(
        self,
        *,
        layer_id: int | None,
        elapsed_us: float,
        gpu_elapsed_us: float | None,
        num_tokens: int,
        top_k: int,
        config: dict[str, Any],
        override_applied: bool,
        variant: str,
        status: str,
        use_int8_w8a16: bool,
        use_int4_w4a16: bool,
        block_shape: list[int] | None,
    ) -> None:
        if not self.shadow_emit_wna16_kernel_timing:
            return
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_descriptor_layer_timing"):
            return
        bucket = "other"
        if int(num_tokens) == 1 and int(top_k) == 8:
            bucket = "w1"
        elif int(num_tokens) == 8 and int(top_k) == 1:
            bucket = "w2"
        phase = "decode" if bucket in {"w1", "w2"} else "prefill_or_other"
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.shadow_descriptor_order_event_token_index),
            layer=int(layer_id) if layer_id is not None else -1,
        )
        sink.write_descriptor_layer_timing(
            {
                "event_type": "wna16_kernel_timing",
                **event_id.as_dict(),
                "wna16_kernel_elapsed_us": float(elapsed_us),
                "wna16_kernel_gpu_elapsed_us": (
                    float(gpu_elapsed_us) if gpu_elapsed_us is not None else None
                ),
                "wna16_kernel_timing_mode": str(self.shadow_wna16_kernel_timing_mode),
                "wna16_kernel_timing_kind": (
                    "gpu_event_synchronized"
                    if gpu_elapsed_us is not None
                    else "cpu_launch_enqueue"
                ),
                "wna16_bucket": bucket,
                "wna16_phase": phase,
                "wna16_phase_source": "num_tokens_topk_heuristic",
                "wna16_num_tokens": int(num_tokens),
                "wna16_top_k": int(top_k),
                "wna16_route_product": int(num_tokens) * int(top_k),
                "wna16_runtime_override_target_top_k": (
                    int(self.shadow_wna16_config_override_target_top_k)
                    if self.shadow_wna16_config_override_target_top_k is not None
                    else None
                ),
                "wna16_variant": str(variant),
                "wna16_status": str(status),
                "wna16_config_override_applied": bool(override_applied),
                "wna16_use_int8_w8a16": bool(use_int8_w8a16),
                "wna16_use_int4_w4a16": bool(use_int4_w4a16),
                "wna16_block_shape": list(block_shape) if block_shape is not None else None,
                "wna16_block_size_m": config.get("BLOCK_SIZE_M"),
                "wna16_block_size_n": config.get("BLOCK_SIZE_N"),
                "wna16_block_size_k": config.get("BLOCK_SIZE_K"),
                "wna16_group_size_m": config.get("GROUP_SIZE_M"),
                "wna16_split_k": config.get("SPLIT_K"),
                "wna16_num_warps": config.get("num_warps"),
                "wna16_num_stages": config.get("num_stages"),
            }
        )

    def write_decoder_layer_timing(
        self,
        *,
        layer_id: int | None,
        elapsed_us: float,
        num_tokens: int | None = None,
        phase: str | None = None,
    ) -> None:
        if not self.shadow_emit_decoder_layer_timing:
            return
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_descriptor_layer_timing"):
            return
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.shadow_descriptor_order_event_token_index),
            layer=int(layer_id) if layer_id is not None else -1,
        )
        sink.write_descriptor_layer_timing(
            {
                "event_type": "decoder_layer_timing",
                **event_id.as_dict(),
                "decoder_layer_elapsed_us": float(elapsed_us),
                "decoder_layer_num_tokens": (
                    int(num_tokens) if num_tokens is not None else None
                ),
                "decoder_layer_phase": str(phase) if phase else None,
                "decoder_layer_phase_source": "num_tokens_heuristic",
            }
        )

    def _should_aggregate_decoder_component(self, component: str) -> bool:
        mode = str(self.shadow_decoder_component_logging_mode or "rows").lower()
        if mode not in {
            "aggregate",
            "attention_handoff_aggregate",
            "attention_handoff_aggregate_no_write",
            "attention_handoff_counter_only",
            "attention_handoff_counter_only_no_write",
        }:
            return False
        return str(component).startswith(_ATTENTION_HANDOFF_COMPONENT_PREFIX)

    def _decoder_component_logging_mode(self) -> str:
        return str(self.shadow_decoder_component_logging_mode or "rows").lower()

    def _decoder_component_aggregate_no_write(self) -> bool:
        return self._decoder_component_logging_mode() in {
            "attention_handoff_aggregate_no_write",
            "attention_handoff_counter_only_no_write",
        }

    def _decoder_component_counter_mode(self) -> bool:
        return self._decoder_component_logging_mode() in {
            "attention_handoff_counter_only",
            "attention_handoff_counter_only_no_write",
        }

    def flush_decoder_component_aggregates(self) -> None:
        if (
            not self._decoder_component_aggregate
            and not self._decoder_component_counter_aggregate
        ):
            return
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_descriptor_layer_timing"):
            self._decoder_component_aggregate.clear()
            self._decoder_component_counter_aggregate.clear()
            return
        if self._decoder_component_aggregate_no_write():
            self._decoder_component_aggregate.clear()
            self._decoder_component_counter_aggregate.clear()
            return
        for payload in self._decoder_component_aggregate.values():
            sink.write_descriptor_layer_timing(payload)
        for record in self._decoder_component_counter_aggregate.values():
            components = {}
            sums = record["sums"]
            counts = record["counts"]
            for idx, count in enumerate(counts):
                if int(count) <= 0:
                    continue
                components[_ATTENTION_HANDOFF_COMPONENTS[idx]] = {
                    "sum_us": float(sums[idx]),
                    "count": int(count),
                }
            payload = {
                "event_type": "decoder_component_aggregate",
                **record["event_id"].as_dict(),
                "decoder_component_aggregate_mode": "attention_handoff_counter_only",
                "decoder_component_num_tokens": record["num_tokens"],
                "decoder_component_phase": record["phase"],
                "decoder_component_phase_source": "num_tokens_heuristic",
                "decoder_component_aggregate_count": int(record["total_count"]),
                "decoder_component_aggregate_components": components,
            }
            sink.write_descriptor_layer_timing(payload)
        self._decoder_component_aggregate.clear()
        self._decoder_component_counter_aggregate.clear()

    def write_decoder_component_timing(
        self,
        *,
        layer_id: int | None,
        component: str,
        elapsed_us: float,
        num_tokens: int | None = None,
        phase: str | None = None,
    ) -> None:
        if (
            not self.shadow_emit_decoder_layer_timing
            or not self.shadow_emit_decoder_component_timing
        ):
            return
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_descriptor_layer_timing"):
            return
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.shadow_descriptor_order_event_token_index),
            layer=int(layer_id) if layer_id is not None else -1,
        )
        if self._should_aggregate_decoder_component(component):
            phase_value = str(phase) if phase else None
            num_tokens_value = int(num_tokens) if num_tokens is not None else None
            key = (
                event_id.request_id,
                int(event_id.sequence_id),
                int(event_id.token_index),
                int(event_id.layer),
                phase_value,
                num_tokens_value,
            )
            if self._decoder_component_counter_mode():
                component_idx = _ATTENTION_HANDOFF_COMPONENT_INDEX.get(str(component))
                if component_idx is None:
                    if self._decoder_component_aggregate_no_write():
                        return
                    sink.write_descriptor_layer_timing(
                        {
                            "event_type": "decoder_component_timing",
                            **event_id.as_dict(),
                            "decoder_component": str(component),
                            "decoder_component_elapsed_us": float(elapsed_us),
                            "decoder_component_num_tokens": num_tokens_value,
                            "decoder_component_phase": phase_value,
                            "decoder_component_phase_source": "num_tokens_heuristic",
                            "decoder_component_logging_fallback": "unknown_handoff_component",
                        }
                    )
                    return
                record = self._decoder_component_counter_aggregate.get(key)
                if record is None:
                    record = {
                        "event_id": event_id,
                        "phase": phase_value,
                        "num_tokens": num_tokens_value,
                        "sums": [0.0] * len(_ATTENTION_HANDOFF_COMPONENTS),
                        "counts": [0] * len(_ATTENTION_HANDOFF_COMPONENTS),
                        "total_count": 0,
                    }
                    self._decoder_component_counter_aggregate[key] = record
                record["sums"][component_idx] = float(record["sums"][component_idx]) + float(
                    elapsed_us
                )
                record["counts"][component_idx] = int(record["counts"][component_idx]) + 1
                record["total_count"] = int(record["total_count"]) + 1
                return
            payload = self._decoder_component_aggregate.get(key)
            if payload is None:
                payload = {
                    "event_type": "decoder_component_aggregate",
                    **event_id.as_dict(),
                    "decoder_component_aggregate_mode": "attention_handoff",
                    "decoder_component_num_tokens": num_tokens_value,
                    "decoder_component_phase": phase_value,
                    "decoder_component_phase_source": "num_tokens_heuristic",
                    "decoder_component_aggregate_count": 0,
                    "decoder_component_aggregate_components": {},
                }
                self._decoder_component_aggregate[key] = payload
            components = payload["decoder_component_aggregate_components"]
            component_payload = components.setdefault(
                str(component),
                {"sum_us": 0.0, "count": 0},
            )
            component_payload["sum_us"] = float(component_payload["sum_us"]) + float(
                elapsed_us
            )
            component_payload["count"] = int(component_payload["count"]) + 1
            payload["decoder_component_aggregate_count"] = (
                int(payload["decoder_component_aggregate_count"]) + 1
            )
            return
        sink.write_descriptor_layer_timing(
            {
                "event_type": "decoder_component_timing",
                **event_id.as_dict(),
                "decoder_component": str(component),
                "decoder_component_elapsed_us": float(elapsed_us),
                "decoder_component_num_tokens": (
                    int(num_tokens) if num_tokens is not None else None
                ),
                "decoder_component_phase": str(phase) if phase else None,
                "decoder_component_phase_source": "num_tokens_heuristic",
            }
        )

    def write_moe_substage_timing(
        self,
        *,
        layer_id: int | None,
        substage: str,
        elapsed_us: float,
        num_tokens: int | None = None,
        phase: str | None = None,
        status: str = "ok",
        _sample_checked: bool = False,
    ) -> None:
        if (
            not self.shadow_emit_decoder_layer_timing
            or not self.shadow_emit_moe_substage_timing
        ):
            return
        if not _moe_substage_allowed(self, substage):
            return
        if not _sample_checked and not self._record_moe_substage_sample_decision(
            layer_id=layer_id,
            substage=substage,
            num_tokens=num_tokens,
            phase=phase,
        ):
            return
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_descriptor_layer_timing"):
            return
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.shadow_descriptor_order_event_token_index),
            layer=int(layer_id) if layer_id is not None else -1,
        )
        logging_mode = str(self.shadow_moe_substage_logging_mode or "rows").lower()
        if logging_mode in {
            "aggregate",
            "shared_aggregate",
            "sampled_aggregate",
            "shared_sampled_aggregate",
            "aggregate_no_write",
            "shared_aggregate_no_write",
        }:
            phase_value = str(phase) if phase else None
            num_tokens_value = int(num_tokens) if num_tokens is not None else None
            sample_multiplier = self._moe_substage_sample_multiplier(
                logging_mode=logging_mode,
                phase=phase_value,
            )
            key = (
                event_id.request_id,
                int(event_id.sequence_id),
                int(event_id.layer),
                phase_value,
                num_tokens_value,
            )
            payload = self._moe_substage_aggregate.get(key)
            if payload is None:
                aggregate_event_id = ShadowEventId(
                    request_id=event_id.request_id,
                    sequence_id=int(event_id.sequence_id),
                    token_index=-1,
                    layer=int(event_id.layer),
                )
                payload = {
                    "event_type": "moe_substage_aggregate",
                    **aggregate_event_id.as_dict(),
                    "moe_substage_aggregate_mode": logging_mode,
                    "moe_substage_num_tokens": num_tokens_value,
                    "moe_substage_phase": phase_value,
                    "moe_substage_phase_source": "num_tokens_heuristic",
                    "moe_substage_aggregate_count": 0,
                    "moe_substage_aggregate_components": {},
                    "moe_substage_sample_period": int(
                        self._moe_substage_sample_period()
                    ),
                }
                self._moe_substage_aggregate[key] = payload
            components = payload["moe_substage_aggregate_components"]
            component_payload = components.setdefault(
                str(substage),
                {
                    "sum_us": 0.0,
                    "raw_sum_us": 0.0,
                    "count": 0,
                    "estimated_count": 0,
                    "status_counts": {},
                    "estimated_status_counts": {},
                    "sample_period": int(sample_multiplier),
                },
            )
            component_payload["sum_us"] = float(component_payload["sum_us"]) + float(
                elapsed_us
            ) * float(sample_multiplier)
            component_payload["raw_sum_us"] = float(
                component_payload.get("raw_sum_us", 0.0)
            ) + float(
                elapsed_us
            )
            component_payload["count"] = int(component_payload["count"]) + 1
            component_payload["estimated_count"] = (
                int(component_payload.get("estimated_count") or 0)
                + int(sample_multiplier)
            )
            component_payload["sample_period"] = max(
                int(component_payload.get("sample_period") or 1),
                int(sample_multiplier),
            )
            status_counts = component_payload.setdefault("status_counts", {})
            status_key = str(status)
            status_counts[status_key] = int(status_counts.get(status_key, 0)) + 1
            estimated_status_counts = component_payload.setdefault(
                "estimated_status_counts",
                {},
            )
            estimated_status_counts[status_key] = int(
                estimated_status_counts.get(status_key, 0)
            ) + int(sample_multiplier)
            payload["moe_substage_aggregate_count"] = (
                int(payload["moe_substage_aggregate_count"]) + 1
            )
            return
        sink.write_descriptor_layer_timing(
            {
                "event_type": "moe_substage_timing",
                **event_id.as_dict(),
                "moe_substage": str(substage),
                "moe_substage_elapsed_us": float(elapsed_us),
                "moe_substage_num_tokens": (
                    int(num_tokens) if num_tokens is not None else None
                ),
                "moe_substage_phase": str(phase) if phase else None,
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": str(status),
            }
        )

    def flush_moe_substage_aggregates(self) -> None:
        if not self._moe_substage_aggregate:
            return
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_descriptor_layer_timing"):
            self._moe_substage_aggregate.clear()
            return
        for payload in self._moe_substage_aggregate.values():
            components = payload.get("moe_substage_aggregate_components") or {}
            component_count = 0
            if isinstance(components, dict):
                for component_payload in components.values():
                    if isinstance(component_payload, dict):
                        component_count += int(component_payload.get("count") or 0)
                        component_payload.setdefault(
                            "estimated_count",
                            int(component_payload.get("count") or 0),
                        )
                        component_payload.setdefault(
                            "estimated_status_counts",
                            dict(component_payload.get("status_counts") or {}),
                        )
            payload["moe_substage_aggregate_component_count"] = int(component_count)
            payload["moe_substage_aggregate_count_match"] = (
                int(payload.get("moe_substage_aggregate_count") or 0)
                == int(component_count)
            )
            if str(payload.get("moe_substage_aggregate_mode") or "").lower() in {
                "aggregate_no_write",
                "shared_aggregate_no_write",
            }:
                continue
            sink.write_descriptor_layer_timing(payload)
        self._moe_substage_aggregate.clear()

    def write_active_moe_substage_timing(
        self,
        *,
        substage: str,
        elapsed_us: float,
        status: str = "ok",
        _sample_checked: bool = False,
    ) -> None:
        context = get_active_moe_assignment_context()
        if context is None:
            return
        layer_id = context.get("layer_id")
        num_tokens = context.get("num_tokens")
        phase = context.get("phase")
        if layer_id is None:
            return
        if not _sample_checked and not self._record_moe_substage_sample_decision(
            layer_id=int(layer_id),
            substage=str(substage),
            num_tokens=int(num_tokens) if num_tokens is not None else None,
            phase=str(phase) if phase else None,
        ):
            return
        self.write_moe_substage_timing(
            layer_id=int(layer_id),
            substage=str(substage),
            elapsed_us=float(elapsed_us),
            num_tokens=int(num_tokens) if num_tokens is not None else None,
            phase=str(phase) if phase else None,
            status=str(status),
            _sample_checked=True,
        )

    def should_record_active_moe_substage(self, substage: str) -> bool:
        if (
            not self.shadow_emit_decoder_layer_timing
            or not self.shadow_emit_moe_substage_timing
        ):
            return False
        if not _moe_substage_allowed(self, substage):
            return False
        context = get_active_moe_assignment_context()
        if context is None:
            return False
        layer_id = context.get("layer_id")
        if layer_id is None:
            return False
        return self._record_moe_substage_sample_decision(
            layer_id=int(layer_id),
            substage=str(substage),
            num_tokens=(
                int(context["num_tokens"])
                if context.get("num_tokens") is not None
                else None
            ),
            phase=str(context.get("phase")) if context.get("phase") else None,
        )

    def _moe_substage_sample_period(self) -> int:
        try:
            period = int(self.shadow_moe_substage_sample_period)
        except Exception:
            period = 1
        return max(1, period)

    def _moe_substage_sample_multiplier(
        self,
        *,
        logging_mode: str,
        phase: str | None,
    ) -> int:
        if logging_mode not in {"sampled_aggregate", "shared_sampled_aggregate"}:
            return 1
        if phase != "decode":
            return 1
        return self._moe_substage_sample_period()

    def _record_moe_substage_sample_decision(
        self,
        *,
        layer_id: int | None,
        substage: str,
        num_tokens: int | None,
        phase: str | None,
    ) -> bool:
        period = self._moe_substage_sample_period()
        logging_mode = str(self.shadow_moe_substage_logging_mode or "rows").lower()
        if logging_mode not in {"sampled_aggregate", "shared_sampled_aggregate"}:
            return True
        if period <= 1 or str(phase) != "decode":
            return True
        key = (
            int(self.sequence_id),
            int(layer_id) if layer_id is not None else -1,
            str(phase),
            int(num_tokens) if num_tokens is not None else None,
            str(substage),
        )
        counter = int(self._moe_substage_sample_counters.get(key, 0)) + 1
        self._moe_substage_sample_counters[key] = counter
        return (counter - 1) % period == 0

    def write_engine_substage_timing(
        self,
        *,
        substage: str,
        elapsed_us: float,
        status: str = "ok",
    ) -> None:
        if not self.shadow_emit_engine_timing:
            return
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_descriptor_layer_timing"):
            return
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.shadow_descriptor_order_event_token_index),
            layer=-1,
        )
        sink.write_descriptor_layer_timing(
            {
                "event_type": "engine_substage_timing",
                **event_id.as_dict(),
                "engine_substage": str(substage),
                "engine_substage_elapsed_us": float(elapsed_us),
                "engine_substage_status": str(status),
            }
        )

    def _descriptor_order_expert_block_permutation(
        self,
        *,
        layer_id: int,
        expert_ids: list[int],
    ) -> list[int]:
        prior = self.shadow_descriptor_order_prior
        tiles_per_expert = max(1, int(self.shadow_descriptor_order_tiles_per_expert))
        if prior is None:
            return list(range(len(expert_ids)))
        rank_by_expert: dict[int, int] = {}
        for rank, tile_id in enumerate(prior.order_for_layer(int(layer_id))):
            expert = int(tile_id) // tiles_per_expert
            rank_by_expert.setdefault(expert, int(rank))
        default_rank = len(rank_by_expert) + 1
        return sorted(
            range(len(expert_ids)),
            key=lambda idx: (
                rank_by_expert.get(int(expert_ids[idx]), default_rank)
                if int(expert_ids[idx]) >= 0
                else default_rank + 1,
                idx,
            ),
        )

    def _descriptor_order_expert_block_group_plan(
        self,
        *,
        layer_id: int,
        expert_ids: list[int],
    ) -> dict[str, Any]:
        """Build a compact two-level group plan without materializing tensors.

        The plan represents the same block multiset as the vLLM consumer handle:
        a prior-ranked expert group order plus cumulative group offsets.  A
        future indirect consumer can iterate ``group_order`` and original block
        spans instead of cloning/index-selecting ``expert_ids`` or
        ``sorted_token_ids`` in Python.
        """

        if not expert_ids:
            return {
                "group_order_hash": hash_ints([]),
                "group_offsets_hash": hash_ints([0]),
                "group_count": 0,
                "avg_group_size": 0.0,
                "p95_group_size": 0.0,
                "max_group_size": 0,
            }
        prior = self.shadow_descriptor_order_prior
        tiles_per_expert = max(1, int(self.shadow_descriptor_order_tiles_per_expert))
        rank_by_expert: dict[int, int] = {}
        if prior is not None:
            for rank, tile_id in enumerate(prior.order_for_layer(int(layer_id))):
                expert = int(tile_id) // tiles_per_expert
                rank_by_expert.setdefault(expert, int(rank))
        default_rank = len(rank_by_expert) + 1
        counts_by_expert: dict[int, int] = {}
        first_index_by_expert: dict[int, int] = {}
        for idx, expert_id in enumerate(expert_ids):
            expert = int(expert_id)
            counts_by_expert[expert] = counts_by_expert.get(expert, 0) + 1
            first_index_by_expert.setdefault(expert, int(idx))
        source_spans_contiguous = True
        for expert, count in counts_by_expert.items():
            start = int(first_index_by_expert[int(expert)])
            end = start + int(count)
            if any(int(value) != int(expert) for value in expert_ids[start:end]):
                source_spans_contiguous = False
                break
        group_order = sorted(
            counts_by_expert,
            key=lambda expert: (
                rank_by_expert.get(int(expert), default_rank)
                if int(expert) >= 0
                else default_rank + 1,
                first_index_by_expert.get(int(expert), 0),
                int(expert),
            ),
        )
        group_sizes = [int(counts_by_expert[int(expert)]) for expert in group_order]
        offsets = [0]
        running = 0
        for size in group_sizes:
            running += int(size)
            offsets.append(int(running))
        sorted_sizes = sorted(group_sizes)
        p95_index = int(0.95 * (len(sorted_sizes) - 1)) if sorted_sizes else 0
        return {
            "group_order_hash": hash_ints(group_order),
            "group_offsets_hash": hash_ints(offsets),
            "group_order": [int(expert) for expert in group_order],
            "group_offsets": [int(offset) for offset in offsets],
            "group_source_starts": [
                int(first_index_by_expert[int(expert)]) for expert in group_order
            ],
            "source_spans_contiguous": bool(source_spans_contiguous),
            "group_count": len(group_order),
            "avg_group_size": float(sum(group_sizes) / max(1, len(group_sizes))),
            "p95_group_size": float(sorted_sizes[p95_index]) if sorted_sizes else 0.0,
            "max_group_size": max(group_sizes) if group_sizes else 0,
        }

    def _descriptor_order_expert_block_group_plan_is_valid(
        self,
        *,
        plan: dict[str, Any],
        block_count: int,
    ) -> bool:
        try:
            group_order = [int(value) for value in plan.get("group_order", [])]
            offsets = [int(value) for value in plan.get("group_offsets", [])]
            starts = [int(value) for value in plan.get("group_source_starts", [])]
        except (TypeError, ValueError):
            return False
        group_count = len(group_order)
        if len(offsets) != group_count + 1 or len(starts) != group_count:
            return False
        if not offsets:
            return block_count == 0
        if offsets[0] != 0 or offsets[-1] != int(block_count):
            return False
        for left, right in zip(offsets, offsets[1:], strict=False):
            if int(left) > int(right):
                return False
        for start, left, right in zip(starts, offsets, offsets[1:], strict=False):
            size = int(right) - int(left)
            if int(start) < 0 or int(start) + size > int(block_count):
                return False
        return True

    def _resolved_descriptor_order_event_mode(self) -> str:
        mode = str(self.shadow_descriptor_order_event_mode or "summary").strip().lower()
        aliases = {
            "min": "minimal",
            "flat": "minimal",
            "scalar": "minimal",
            "flat_scalar": "minimal",
            "event_minimal": "minimal",
            "full": "summary",
        }
        return aliases.get(mode, mode)

    def _write_previous_token_transition_summary(
        self,
        *,
        layer_id: int,
        token_idx: int,
        previous_topk_ids: torch.Tensor,
        previous_topk_weights: torch.Tensor,
    ) -> None:
        sink = self.shadow_outcome_sink
        if sink is None or not hasattr(sink, "write_action_summary"):
            return
        mode = str(self.shadow_transition_summary_mode)
        base, transition_count = self._transition_summary_base_mask(
            layer_id=layer_id,
            previous_topk_ids=previous_topk_ids,
            previous_topk_weights=previous_topk_weights,
            mode=mode,
        )
        empty = torch.zeros_like(base, dtype=torch.bool)
        decisions = AdmissionDecisionMasks(
            admitted_full_fetch=empty,
            admitted_metadata=empty,
            admitted_premap=empty,
            skipped_not_novel=empty,
            skipped_rank_cap=empty,
            skipped_below_threshold=empty,
            skipped_invalid_score=empty,
            skipped_policy=empty,
        )
        transition_count = (
            int(self.shadow_transition_topk_count)
            if self.shadow_transition_topk_count is not None
            else int(transition_count)
        )
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.token_offset + token_idx),
            layer=int(layer_id),
        )
        policy = ShadowPolicyConfig(
            policy_mode="transition_only_shadow",
            optimization_goal="stall_reduction",
            action_keep_fraction=0.0,
            metadata_score_ratio=1.0,
            full_fetch_max_extra=0,
            metadata_max_extra=0,
            premap_max_extra=0,
            policy_reason=f"{mode}_transition_summary",
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=False,
            allow_mtp_premap=False,
        )
        sink.write_action_summary(
            event_id=event_id,
            policy=policy,
            decisions=decisions,
            base_mask=base,
            ready_mask=base,
            transition_topk_count=transition_count,
            mtp_requested_count=0,
        )

    def _transition_summary_base_mask(
        self,
        *,
        layer_id: int,
        previous_topk_ids: torch.Tensor,
        previous_topk_weights: torch.Tensor,
        mode: str,
    ) -> tuple[torch.Tensor, int]:
        num_experts = max(1, int(self.shadow_num_experts))
        shape = (1, 1, 1, num_experts)
        if mode == "matrix_topk":
            if self.shadow_transition_matrix is None:
                msg = "matrix_topk transition summary requires shadow_transition_matrix."
                raise ValueError(msg)
            transition_scores = _transition_scores_from_topk(
                layer_id=layer_id,
                previous_topk_ids=previous_topk_ids,
                previous_topk_weights=previous_topk_weights,
                transition_matrix=self.shadow_transition_matrix,
                num_experts=num_experts,
            )
            transition_count = int(
                self.shadow_transition_topk_count
                if self.shadow_transition_topk_count is not None
                else min(32, num_experts)
            )
            topk = _stable_desc_topk_indices(
                transition_scores,
                k=max(1, min(transition_count, num_experts)),
            )
            base = torch.zeros(shape, dtype=torch.bool)
            base[..., topk] = True
            return base, transition_count
        if mode != "previous_topk":
            msg = f"Unsupported transition summary mode: {mode}"
            raise ValueError(msg)
        base = torch.zeros(shape, dtype=torch.bool)
        for expert_id in previous_topk_ids.tolist():
            expert_idx = int(expert_id)
            if 0 <= expert_idx < num_experts:
                base[..., expert_idx] = True
        return base, int(previous_topk_ids.numel())

    def to_payload(
        self,
        *,
        module_prefix: str = "model.language_model",
        source: str = "vllm_router_logits_recorder",
    ) -> dict[str, Any]:
        router_topk: dict[str, list[Any]] = {}
        router_weights: dict[str, list[Any]] = {}
        router_oracle_topk: dict[str, list[Any]] = {}
        router_oracle_weights: dict[str, list[Any]] = {}
        router_input_hidden: dict[str, list[torch.Tensor]] = {}
        router_call_meta: list[dict[str, Any]] = []
        for call in self.calls:
            if call.layer_id is None:
                name = f"{module_prefix}.layers.unknown_call_{call.call_index}.mlp.gate"
            else:
                name = f"{module_prefix}.layers.{call.layer_id}.mlp.gate"
            router_topk.setdefault(name, []).append(call.topk_ids.tolist())
            router_weights.setdefault(name, []).append(call.topk_weights.tolist())
            oracle_match_rate = None
            if call.oracle_topk_ids is not None:
                router_oracle_topk.setdefault(name, []).append(call.oracle_topk_ids.tolist())
                if call.oracle_topk_weights is not None:
                    router_oracle_weights.setdefault(name, []).append(
                        call.oracle_topk_weights.tolist()
                    )
                oracle_match_rate = float(
                    (call.oracle_topk_ids == call.topk_ids).to(torch.float32).mean().item()
                )
            if call.router_input_hidden is not None:
                router_input_hidden.setdefault(name, []).append(call.router_input_hidden)
            router_call_meta.append(
                {
                    "source": source,
                    "layer_id": call.layer_id,
                    "call_index": call.call_index,
                    "num_tokens": call.num_tokens,
                    "module_name": name,
                    "has_same_token_oracle_topk": call.oracle_topk_ids is not None,
                    "same_token_oracle_exact_match_rate": oracle_match_rate,
                    "has_router_input_hidden": call.router_input_hidden is not None,
                }
            )
        payload: dict[str, Any] = {
            "router_topk": router_topk,
            "router_weights": router_weights,
            "router_call_meta": router_call_meta,
        }
        if router_oracle_topk:
            payload["router_oracle_topk"] = router_oracle_topk
            payload["router_oracle_weights"] = router_oracle_weights
            match_values = [
                float(meta["same_token_oracle_exact_match_rate"])
                for meta in router_call_meta
                if meta["same_token_oracle_exact_match_rate"] is not None
            ]
            payload["router_oracle_summary"] = {
                "kind": "same_token_router_input_hidden_oracle",
                "topk_source": "topk(softmax(router_logits_from_true_moe_input_hidden))",
                "num_calls": len(match_values),
                "mean_exact_match_rate": (
                    sum(match_values) / len(match_values) if match_values else None
                ),
                "min_exact_match_rate": min(match_values) if match_values else None,
            }
        if router_input_hidden:
            payload["router_input_hidden"] = router_input_hidden
        return payload

    def save(self, path: str | Path, *, input_ids: list[int] | None = None) -> Path:
        payload = self.to_payload()
        if input_ids is not None:
            payload["input_ids"] = torch.tensor([input_ids], dtype=torch.int32)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(payload, path)
        return path


_ACTIVE_RECORDER: VllmRouterRecorder | None = None
_ACTIVE_RUNTIME_SHADOW_CONTROLLER: RuntimeShadowController | None = None
_ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR: contextvars.ContextVar[dict[str, Any] | None] = (
    contextvars.ContextVar("mtp_active_moe_assignment_context", default=None)
)
_ACTIVE_DECODER_COMPONENT_CONTEXT_VAR: contextvars.ContextVar[
    dict[str, Any] | None
] = contextvars.ContextVar("mtp_active_decoder_component_context", default=None)
_PATCHED = False
_FUSED_EXPERTS_OUTER_TIMING_PATCH_ATTR = (
    "_mtp_expert_prefetch_fused_experts_outer_timing"
)
_MOE_SOURCE_TIMING_LEVELS = {
    "off": 0,
    "none": 0,
    "false": 0,
    "0": 0,
    "shared": 0,
    "shared_expert": 0,
    "shared_experts": 0,
    "shared_body": 0,
    "shared_direct": 0,
    "shared_coarse": 0,
    "shared_body_regions": 0,
    "shared_direct_regions": 0,
    "shared_coarse_regions": 0,
    "outer": 1,
    "outer_only": 1,
    "outer_impl": 2,
    "impl": 2,
    "impl_total": 2,
    "outer_impl_enqueue": 3,
    "enqueue": 3,
    "launch": 3,
    "full": 4,
    "source": 4,
    "true": 4,
    "1": 4,
}


def _moe_source_timing_level(recorder: VllmRouterRecorder | None) -> int:
    if (
        recorder is None
        or not recorder.shadow_emit_decoder_layer_timing
        or not recorder.shadow_emit_moe_substage_timing
    ):
        return 0
    mode = str(recorder.shadow_moe_source_timing_mode or "full").strip().lower()
    if mode not in _MOE_SOURCE_TIMING_LEVELS:
        allowed = ", ".join(sorted(_MOE_SOURCE_TIMING_LEVELS))
        raise ValueError(f"Unsupported moe_source_timing_mode={mode!r}; allowed: {allowed}")
    return int(_MOE_SOURCE_TIMING_LEVELS[mode])


def _shared_expert_source_timing_enabled(
    recorder: VllmRouterRecorder | None,
) -> bool:
    if (
        recorder is None
        or not recorder.shadow_emit_decoder_layer_timing
        or not recorder.shadow_emit_moe_substage_timing
    ):
        return False
    mode = str(recorder.shadow_moe_source_timing_mode or "full").strip().lower()
    if mode not in _MOE_SOURCE_TIMING_LEVELS:
        allowed = ", ".join(sorted(_MOE_SOURCE_TIMING_LEVELS))
        raise ValueError(f"Unsupported moe_source_timing_mode={mode!r}; allowed: {allowed}")
    return mode in {"shared", "shared_expert", "shared_experts"} or (
        int(_MOE_SOURCE_TIMING_LEVELS[mode]) > 0
    )


def _shared_expert_body_timing_enabled(
    recorder: VllmRouterRecorder | None,
) -> bool:
    if (
        recorder is None
        or not recorder.shadow_emit_decoder_layer_timing
        or not recorder.shadow_emit_moe_substage_timing
    ):
        return False
    mode = str(recorder.shadow_moe_source_timing_mode or "full").strip().lower()
    if mode not in _MOE_SOURCE_TIMING_LEVELS:
        allowed = ", ".join(sorted(_MOE_SOURCE_TIMING_LEVELS))
        raise ValueError(f"Unsupported moe_source_timing_mode={mode!r}; allowed: {allowed}")
    return mode in {
        "shared_body",
        "shared_direct",
        "shared_coarse",
        "shared_body_regions",
        "shared_direct_regions",
        "shared_coarse_regions",
    }


def _shared_expert_body_region_timing_enabled(
    recorder: VllmRouterRecorder | None,
) -> bool:
    if (
        recorder is None
        or not recorder.shadow_emit_decoder_layer_timing
        or not recorder.shadow_emit_moe_substage_timing
    ):
        return False
    mode = str(recorder.shadow_moe_source_timing_mode or "full").strip().lower()
    if mode not in _MOE_SOURCE_TIMING_LEVELS:
        allowed = ", ".join(sorted(_MOE_SOURCE_TIMING_LEVELS))
        raise ValueError(f"Unsupported moe_source_timing_mode={mode!r}; allowed: {allowed}")
    return mode in {
        "shared_body_regions",
        "shared_direct_regions",
        "shared_coarse_regions",
    }


def _shared_expert_fused_gate_enabled(
    recorder: VllmRouterRecorder | None,
) -> bool:
    postprocess = _shared_expert_output_gate_postprocess_mode(recorder)
    return postprocess in {"fused_triton", "triton_fused"}


def _moe_substage_allowed(
    recorder: VllmRouterRecorder,
    substage: str,
) -> bool:
    mode = str(recorder.shadow_moe_source_timing_mode or "full").strip().lower()
    if mode in {"shared", "shared_expert", "shared_experts"}:
        return str(substage).startswith("experts_shared_")
    if mode in {"shared_body", "shared_direct", "shared_coarse"}:
        return str(substage) == "experts_shared_direct_layer"
    if mode in {
        "shared_body_regions",
        "shared_direct_regions",
        "shared_coarse_regions",
    }:
        return str(substage) in {
            "experts_shared_direct_layer",
            "experts_shared_body_core",
            "experts_shared_body_gate_proj",
            "experts_shared_body_gate_apply",
            "experts_shared_body_gate_fused",
        }
    return True


def _emit_active_engine_substage_timing(
    substage: str,
    start_ns: int,
    *,
    status: str = "ok",
) -> None:
    recorder = get_active_vllm_router_recorder()
    if recorder is None:
        return
    recorder.write_engine_substage_timing(
        substage=substage,
        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
        status=status,
    )


def get_active_vllm_router_recorder() -> VllmRouterRecorder | None:
    return _ACTIVE_RECORDER


def set_active_vllm_router_recorder(recorder: VllmRouterRecorder | None) -> None:
    global _ACTIVE_RECORDER
    _ACTIVE_RECORDER = recorder


def get_active_runtime_shadow_controller() -> RuntimeShadowController | None:
    return _ACTIVE_RUNTIME_SHADOW_CONTROLLER


def set_active_runtime_shadow_controller(
    controller: RuntimeShadowController | None,
) -> None:
    global _ACTIVE_RUNTIME_SHADOW_CONTROLLER
    _ACTIVE_RUNTIME_SHADOW_CONTROLLER = controller


def get_active_moe_assignment_context() -> dict[str, Any] | None:
    return _ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR.get()


def set_active_moe_assignment_context(context: dict[str, Any] | None) -> None:
    _ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR.set(context)


def push_active_moe_assignment_context(
    context: dict[str, Any] | None,
) -> contextvars.Token[dict[str, Any] | None]:
    return _ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR.set(
        dict(context) if context is not None else None
    )


def reset_active_moe_assignment_context(
    token: contextvars.Token[dict[str, Any] | None],
) -> None:
    _ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR.reset(token)


def write_active_runtime_shadow_action_summary(
    *,
    event_id: ShadowEventId,
    policy: ShadowPolicyConfig,
    decisions: AdmissionDecisionMasks,
    base_mask: torch.Tensor | None = None,
    ready_mask: torch.Tensor | None = None,
    **summary_kwargs: Any,
) -> ShadowSummaryEvent | None:
    """Write a runtime shadow summary through the active controller.

    Patched runtime code can call this hook in shadow-only mode. If runtime
    shadow logging is disabled, it is a no-op and returns `None`.
    """

    controller = get_active_runtime_shadow_controller()
    if controller is None:
        return None
    return controller.write_action_summary(
        event_id=event_id,
        policy=policy,
        decisions=decisions,
        base_mask=base_mask,
        ready_mask=ready_mask,
        **summary_kwargs,
    )


def write_active_runtime_shadow_descriptor_order_summary(
    *,
    event_id: ShadowEventId,
    policy: ShadowPolicyConfig,
    descriptor_report: DescriptorOrderReport,
    baseline_order_hash: str | None = None,
    **summary_kwargs: Any,
) -> ShadowSummaryEvent | None:
    """Write descriptor-order shadow counters through the active controller."""

    controller = get_active_runtime_shadow_controller()
    if controller is None:
        return None
    return controller.write_descriptor_order_summary(
        event_id=event_id,
        policy=policy,
        descriptor_report=descriptor_report,
        baseline_order_hash=baseline_order_hash,
        **summary_kwargs,
    )


def _transition_scores_from_topk(
    *,
    layer_id: int,
    previous_topk_ids: torch.Tensor,
    previous_topk_weights: torch.Tensor,
    transition_matrix: torch.Tensor,
    num_experts: int,
) -> torch.Tensor:
    matrix = transition_matrix.detach().cpu().float()
    if matrix.ndim != 4:
        msg = (
            "transition_matrix must have shape [delta, layers, in_experts, out_experts], "
            f"got {tuple(matrix.shape)}"
        )
        raise ValueError(msg)
    if int(layer_id) < 0 or int(layer_id) >= int(matrix.shape[1]):
        msg = f"layer_id {layer_id} out of transition matrix range {matrix.shape[1]}"
        raise ValueError(msg)
    if int(num_experts) > int(matrix.shape[2]) or int(num_experts) > int(matrix.shape[3]):
        msg = (
            f"num_experts={num_experts} exceeds transition matrix expert dims "
            f"{tuple(matrix.shape[2:])}"
        )
        raise ValueError(msg)
    feature = torch.zeros(num_experts, dtype=torch.float32)
    ids = previous_topk_ids.detach().cpu().to(torch.long)
    weights = previous_topk_weights.detach().cpu().to(torch.float32)
    if ids.shape != weights.shape:
        msg = "previous_topk_ids and previous_topk_weights must share shape."
        raise ValueError(msg)
    valid_weight_sum = 0.0
    valid_pairs: list[tuple[int, float]] = []
    for expert_id, weight in zip(ids.tolist(), weights.tolist()):
        expert_idx = int(expert_id)
        if 0 <= expert_idx < num_experts:
            clipped = max(0.0, float(weight))
            valid_pairs.append((expert_idx, clipped))
            valid_weight_sum += clipped
    if valid_weight_sum <= 0.0:
        return feature
    for expert_idx, weight in valid_pairs:
        feature[expert_idx] += float(weight) / valid_weight_sum
    return feature @ matrix[0, int(layer_id), :num_experts, :num_experts]


def _stable_desc_topk_indices(scores: torch.Tensor, *, k: int) -> torch.Tensor:
    values = scores.detach().cpu().float().flatten().tolist()
    k = max(0, min(int(k), len(values)))
    selected = sorted(range(len(values)), key=lambda idx: (-float(values[idx]), int(idx)))[:k]
    return torch.tensor(selected, dtype=torch.long)


def _tile_requests_from_router_topk(
    *,
    layer_id: int,
    token_offset: int,
    topk_ids: torch.Tensor,
    topk_weights: torch.Tensor,
    tiles_per_expert: int,
    token_window_size: int = 0,
) -> list[TileRequest]:
    """Expand true-router top-k into a current-router token/row tile stream."""

    ids = topk_ids.detach().cpu().to(torch.long)
    weights = topk_weights.detach().cpu().to(torch.float32)
    if ids.ndim != 2 or weights.shape != ids.shape:
        return []
    tiles_per_expert = max(1, int(tiles_per_expert))
    requests: list[TileRequest] = []
    request_id = 0
    token_window_size = int(token_window_size)
    for token_idx in range(int(ids.shape[0])):
        absolute_token = int(token_offset + token_idx)
        window_id = 0
        if token_window_size > 0:
            window_id = int(token_idx // token_window_size)
        for row_id, (expert_tensor, weight_tensor) in enumerate(
            zip(ids[token_idx].tolist(), weights[token_idx].tolist(), strict=True)
        ):
            expert = int(expert_tensor)
            weight = float(weight_tensor)
            if expert < 0:
                continue
            for tile_local in range(tiles_per_expert):
                tile_id = expert * tiles_per_expert + int(tile_local)
                requests.append(
                    TileRequest(
                        window_id=window_id,
                        request_id=request_id,
                        tile_id=tile_id,
                        expert_id=expert,
                        transition_score=weight,
                        mtp_score=0.0,
                        utility_score=weight,
                        token_index=absolute_token,
                        layer_idx=int(layer_id),
                        row_id=int(row_id),
                        weight=weight,
                        source_policy="current_router_topk",
                    )
                )
                request_id += 1
    return requests


def _descriptor_order_mapping_assertion_from_router_topk(
    *,
    mode: str,
    source: str,
    topk_ids: torch.Tensor,
    descriptor_report: DescriptorOrderReport,
    tiles_per_expert: int,
    token_window_size: int,
) -> dict[str, Any]:
    """Verify that internal router top-k maps to the two-level group plan.

    This is a no-op assertion for the vLLM/AWQ integration boundary. It does
    not change execution order and does not claim numeric checksum parity for a
    future kernel patch. It only checks that the current internal router output
    can be represented by the same descriptor/tile multiset consumed by the
    two-level group-plan telemetry.
    """

    normalized_mode = str(mode or "off").strip().lower()
    if normalized_mode in {"", "off", "none", "false", "0"}:
        return {}
    ids = topk_ids.detach().cpu().to(torch.long)
    if ids.ndim != 2:
        return {
            "mode": normalized_mode,
            "source": str(source),
            "same_multiset": False,
            "error": f"expected_2d_topk_ids_got_{tuple(ids.shape)}",
        }
    try:
        internal = _internal_group_plan_counts_from_router_topk(
            ids=ids,
            tiles_per_expert=max(1, int(tiles_per_expert)),
            token_window_size=int(token_window_size),
        )
        metrics = descriptor_report.metrics if descriptor_report is not None else {}
        group_plan = metrics.get("group_plan", {}) if isinstance(metrics, dict) else {}
        plan_request_count = int(descriptor_report.descriptor_count)
        plan_group_count = int(group_plan.get("group_count", 0) or 0)
        plan_tile_multiset_hash = descriptor_report.tile_multiset_hash
        counts_match = (
            int(internal["request_count"]) == plan_request_count
            and int(internal["group_count"]) == plan_group_count
        )
        same_multiset = (
            bool(counts_match)
            and plan_tile_multiset_hash is not None
            and str(internal["tile_multiset_hash"]) == str(plan_tile_multiset_hash)
        )
        error = None
        if plan_tile_multiset_hash is None:
            error = "plan_tile_multiset_hash_missing"
        elif not same_multiset:
            error = "internal_topk_group_plan_mismatch"
        return {
            "mode": normalized_mode,
            "source": str(source),
            "same_multiset": bool(same_multiset),
            "counts_match": bool(counts_match),
            "tile_multiset_hash": str(internal["tile_multiset_hash"]),
            "plan_tile_multiset_hash": (
                str(plan_tile_multiset_hash) if plan_tile_multiset_hash is not None else None
            ),
            "request_count": int(internal["request_count"]),
            "plan_request_count": plan_request_count,
            "group_count": int(internal["group_count"]),
            "plan_group_count": plan_group_count,
            "error": error,
        }
    except Exception as exc:  # pragma: no cover - defensive telemetry path
        return {
            "mode": normalized_mode,
            "source": str(source),
            "same_multiset": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _internal_group_plan_counts_from_router_topk(
    *,
    ids: torch.Tensor,
    tiles_per_expert: int,
    token_window_size: int,
) -> dict[str, int]:
    token_count = int(ids.shape[0])
    tiles_per_expert = max(1, int(tiles_per_expert))
    window_size = token_count if token_window_size <= 0 else max(1, int(token_window_size))
    request_count = 0
    group_count = 0
    tile_ids: list[int] = []
    for token_start in range(0, token_count, window_size):
        token_end = min(token_start + window_size, token_count)
        seen_tiles: set[int] = set()
        window = ids[token_start:token_end].reshape(-1)
        for expert_raw in window.tolist():
            expert = int(expert_raw)
            if expert < 0:
                continue
            for tile_local in range(tiles_per_expert):
                tile = expert * tiles_per_expert + int(tile_local)
                seen_tiles.add(tile)
                tile_ids.append(tile)
                request_count += 1
        group_count += len(seen_tiles)
    return {
        "request_count": request_count,
        "group_count": group_count,
        "tile_multiset_hash": hash_ints(sorted(tile_ids)),
    }


def patch_vllm_qwen35_moe_router_trace() -> None:
    """Patch vLLM Qwen3.5/Qwen3.6 MoE blocks to record router top-k.

    This is intentionally a runtime monkey patch so the project can keep using
    upstream vLLM as an optional backend. The patch is for offline trace smoke
    first; server/continuous batching needs stricter request-id bookkeeping.
    """
    global _PATCHED
    if _PATCHED:
        return

    from vllm.model_executor.models import qwen3_next

    try:
        qwen3_5 = importlib.import_module("vllm.model_executor.models.qwen3_5")
    except ModuleNotFoundError:
        qwen3_5 = None
    try:
        base_router = importlib.import_module(
            "vllm.model_executor.layers.fused_moe.router.base_router"
        )
    except ModuleNotFoundError:
        base_router = None
    try:
        fused_moe_layer = importlib.import_module(
            "vllm.model_executor.layers.fused_moe.layer"
        )
    except ModuleNotFoundError:
        fused_moe_layer = None

    decoder_classes = []
    qwen35_decoder = getattr(qwen3_5, "Qwen3_5DecoderLayer", None)
    if qwen35_decoder is not None:
        decoder_classes.append(qwen35_decoder)
    qwen3_next_decoder = getattr(qwen3_next, "Qwen3NextDecoderLayer", None)
    if qwen3_next_decoder is not None:
        decoder_classes.append(qwen3_next_decoder)
    if not decoder_classes:
        msg = "Could not find a supported Qwen decoder layer class to patch."
        raise RuntimeError(msg)

    original_moe_forward = qwen3_next.Qwen3NextSparseMoeBlock.forward
    original_qwen3_next_load_weights = qwen3_next.Qwen3NextForCausalLM.load_weights

    def qwen3_next_load_weights_with_text_prefix_remap(
        self,
        weights: Any,
    ) -> set[str]:
        """Remap Qwen3-Next multimodal checkpoint names for text-only loading.

        Quantized Qwen3.6-A3B checkpoints may store language weights under
        ``model.language_model.*``. The text-only vLLM Qwen3NextForCausalLM
        expects the same tensors under ``model.*``. Without this remap, the
        smoke can initialize but router gates remain effectively unloaded.
        """

        def remapped_weights() -> Any:
            prefix = "model.language_model."
            pending_linear_attn: dict[tuple[str, str], dict[str, torch.Tensor]] = {}

            def maybe_emit_fused_linear_attn(
                fused_prefix: str,
                fused_name: str,
                parts: tuple[str, ...],
            ) -> tuple[str, torch.Tensor] | None:
                key = (fused_prefix, fused_name)
                buffered = pending_linear_attn.get(key)
                if buffered is None or not all(part in buffered for part in parts):
                    return None
                tensors = [buffered.pop(part) for part in parts]
                if not buffered:
                    pending_linear_attn.pop(key, None)
                return f"{fused_prefix}.{fused_name}.weight", torch.cat(tensors, dim=0)

            for name, tensor in weights:
                if not isinstance(name, str):
                    yield name, tensor
                    continue
                if name.startswith("model.visual.") or name.startswith("visual."):
                    continue
                if name.startswith(prefix):
                    name = "model." + name[len(prefix) :]

                linear_marker = ".linear_attn."
                if linear_marker in name and name.endswith(".weight"):
                    base, leaf = name.rsplit(linear_marker, 1)
                    if leaf in {
                        "in_proj_qkv.weight",
                        "in_proj_z.weight",
                        "in_proj_b.weight",
                        "in_proj_a.weight",
                    }:
                        qkvz_key = (base + linear_marker[:-1], "in_proj_qkvz")
                        ba_key = (base + linear_marker[:-1], "in_proj_ba")
                        if leaf == "in_proj_qkv.weight":
                            pending_linear_attn.setdefault(qkvz_key, {})["qkv"] = tensor
                            fused = maybe_emit_fused_linear_attn(
                                qkvz_key[0],
                                qkvz_key[1],
                                ("qkv", "z"),
                            )
                        elif leaf == "in_proj_z.weight":
                            pending_linear_attn.setdefault(qkvz_key, {})["z"] = tensor
                            fused = maybe_emit_fused_linear_attn(
                                qkvz_key[0],
                                qkvz_key[1],
                                ("qkv", "z"),
                            )
                        elif leaf == "in_proj_b.weight":
                            pending_linear_attn.setdefault(ba_key, {})["b"] = tensor
                            fused = maybe_emit_fused_linear_attn(
                                ba_key[0],
                                ba_key[1],
                                ("b", "a"),
                            )
                        else:
                            pending_linear_attn.setdefault(ba_key, {})["a"] = tensor
                            fused = maybe_emit_fused_linear_attn(
                                ba_key[0],
                                ba_key[1],
                                ("b", "a"),
                            )
                        if fused is not None:
                            yield fused
                        continue
                yield name, tensor
            for (fused_prefix, _), buffered in pending_linear_attn.items():
                for part_name, tensor in buffered.items():
                    yield f"{fused_prefix}.{part_name}.weight", tensor

        return original_qwen3_next_load_weights(self, remapped_weights())

    def _make_decoder_init_with_trace_layer(original_init: Any) -> Any:
        def decoder_init_with_trace_layer(self, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            layer_id = getattr(self, "layer_idx", None)
            if hasattr(self, "mlp"):
                self.mlp._mtp_trace_layer_id = layer_id
                experts = getattr(self.mlp, "experts", None)
                if experts is not None:
                    experts._mtp_trace_layer_id = layer_id
                router = getattr(experts, "router", None)
                if router is not None:
                    router._mtp_trace_layer_id = layer_id
            _wrap_decoder_component_for_timing(
                getattr(self, "self_attn", None),
                component="attention",
                layer_id=layer_id,
            )
            _wrap_decoder_component_for_timing(
                getattr(self, "linear_attn", None),
                component="attention",
                layer_id=layer_id,
            )
            _wrap_decoder_component_for_timing(
                getattr(self, "mlp", None),
                component="mlp",
                layer_id=layer_id,
            )

        return decoder_init_with_trace_layer

    def _infer_component_num_tokens(args: tuple[Any, ...], kwargs: dict[str, Any]) -> int | None:
        hidden_states = kwargs.get("hidden_states")
        if hidden_states is None and args:
            hidden_states = args[0]
        if isinstance(hidden_states, torch.Tensor) and hidden_states.ndim > 0:
            return int(hidden_states.shape[0])
        return None

    def _phase_from_num_tokens(num_tokens: int | None) -> str | None:
        return (
            "decode"
            if num_tokens == 1
            else "prefill"
            if num_tokens is not None and num_tokens > 1
            else None
        )

    def _wna16_phase_from_num_tokens_topk(
        num_tokens: int | None,
        top_k: int | None,
    ) -> str | None:
        if num_tokens is None or top_k is None:
            return None
        if (int(num_tokens), int(top_k)) in {(1, 8), (8, 1)}:
            return "decode"
        return "prefill_or_other"

    def _wrap_decoder_component_for_timing(
        module: Any,
        *,
        component: str,
        layer_id: int | None,
    ) -> None:
        if module is None or getattr(module, "_mtp_component_timing_wrapped", False):
            return
        original_forward = module.forward

        def component_forward_with_timing(*args: Any, **kwargs: Any) -> Any:
            recorder = get_active_vllm_router_recorder()
            if (
                recorder is None
                or not recorder.shadow_emit_decoder_layer_timing
                or not recorder.shadow_emit_decoder_component_timing
            ):
                return original_forward(*args, **kwargs)
            num_tokens = _infer_component_num_tokens(args, kwargs)
            phase = _phase_from_num_tokens(num_tokens)
            context_token = _ACTIVE_DECODER_COMPONENT_CONTEXT_VAR.set(
                {
                    "component": str(component),
                    "layer_id": layer_id,
                    "num_tokens": num_tokens,
                    "phase": phase,
                }
            )
            start_ns = time.perf_counter_ns()
            try:
                if component == "attention" and _decoder_source_timing_enabled(
                    recorder
                ):
                    source_mode = _decoder_source_timing_mode(recorder)
                    attention_kind = (
                        "linear_attention"
                        if hasattr(module, "_forward_core")
                        or hasattr(module, "in_proj_qkvz")
                        else "full_attention"
                    )
                    if (
                        source_mode
                        in {
                            "attention_core",
                            "attention_core_deep",
                            "attention_deep",
                            "attention_methods",
                            "attention_linear_core",
                            "attention_linear_core_deep",
                            "attention_core_handoff_light",
                            "attention_linear_handoff_light",
                        }
                    ):
                        if attention_kind == "linear_attention":
                            if source_mode in {
                                "attention_core_handoff_light",
                                "attention_linear_handoff_light",
                            }:
                                _wrap_linear_attention_handoff_leaf_modules_for_timing(
                                    module,
                                    layer_id=layer_id,
                                )
                            _wrap_linear_attention_source_methods_for_timing(
                                module,
                                layer_id=layer_id,
                            )
                            _wrap_linear_attention_core_deep_functions_for_timing(
                                module,
                                layer_id=layer_id,
                            )
                    else:
                        _wrap_attention_leaf_modules_for_timing(
                            module,
                            attention_kind=attention_kind,
                            layer_id=layer_id,
                        )
                        if attention_kind == "linear_attention":
                            _wrap_linear_attention_source_methods_for_timing(
                                module,
                                layer_id=layer_id,
                            )
                return original_forward(*args, **kwargs)
            finally:
                _ACTIVE_DECODER_COMPONENT_CONTEXT_VAR.reset(context_token)
                recorder.write_decoder_component_timing(
                    layer_id=layer_id,
                    component=component,
                    elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                    num_tokens=num_tokens,
                    phase=phase,
                )

        module.forward = component_forward_with_timing
        module._mtp_component_timing_wrapped = True
        module._mtp_component_timing_name = str(component)

    def _infer_first_tensor_num_tokens(inputs: tuple[Any, ...]) -> int | None:
        for value in inputs:
            if isinstance(value, torch.Tensor) and value.ndim > 0:
                return int(value.shape[0])
            if isinstance(value, (tuple, list)):
                nested = _infer_first_tensor_num_tokens(tuple(value))
                if nested is not None:
                    return nested
        return None

    def _attention_leaf_component(attention_kind: str, name: str) -> str:
        lowered = name.lower()
        prefix = (
            "attention_linear"
            if attention_kind == "linear_attention"
            else "attention_full"
        )
        if attention_kind == "linear_attention":
            if any(token in lowered for token in ("in_proj_qkvz", "in_proj_qkv", "in_proj_z")):
                return f"{prefix}_input_proj"
            if "in_proj_ba" in lowered:
                return f"{prefix}_ba_proj"
            if "conv1d" in lowered:
                return f"{prefix}_conv1d"
            if lowered.endswith("norm") or ".norm" in lowered:
                return f"{prefix}_norm"
            if "out_proj" in lowered:
                return f"{prefix}_out_proj"
            if "chunk_gated_delta_rule" in lowered or "delta" in lowered:
                return f"{prefix}_core"
            return f"{prefix}_leaf_other"
        if "qkv_proj" in lowered:
            return f"{prefix}_qkv_proj"
        if lowered.endswith("q_norm") or lowered.endswith("k_norm"):
            return f"{prefix}_qk_norm"
        if "rotary" in lowered or "rope" in lowered:
            return f"{prefix}_rope"
        if lowered.endswith("attn") or ".attn" in lowered:
            return f"{prefix}_core"
        if "o_proj" in lowered:
            return f"{prefix}_o_proj"
        return f"{prefix}_leaf_other"

    def _wrap_attention_leaf_modules_for_timing(
        module: Any,
        *,
        attention_kind: str,
        layer_id: int | None,
    ) -> None:
        if module is None or getattr(module, "_mtp_attention_leaf_timing_wrapped", False):
            return
        hooks: list[Any] = []
        starts: dict[int, tuple[int, int | None]] = {}

        def make_pre_hook(module_id: int):
            def pre_hook(_module: torch.nn.Module, inputs: tuple[Any, ...]) -> None:
                recorder = get_active_vllm_router_recorder()
                if recorder is None or not _decoder_attention_leaf_timing_enabled(
                    recorder
                ):
                    starts.pop(module_id, None)
                    return
                starts[module_id] = (
                    time.perf_counter_ns(),
                    _infer_first_tensor_num_tokens(inputs),
                )

            return pre_hook

        def make_post_hook(module_id: int, component: str):
            def post_hook(
                _module: torch.nn.Module,
                _inputs: tuple[Any, ...],
                _output: Any,
            ) -> None:
                recorder = get_active_vllm_router_recorder()
                if recorder is None or not _decoder_attention_leaf_timing_enabled(
                    recorder
                ):
                    starts.pop(module_id, None)
                    return
                start = starts.pop(module_id, None)
                if start is None:
                    return
                start_ns, num_tokens = start
                phase = None
                parent_context = _ACTIVE_DECODER_COMPONENT_CONTEXT_VAR.get()
                if (
                    parent_context is not None
                    and str(parent_context.get("component") or "").startswith(
                        "attention"
                    )
                ):
                    num_tokens = parent_context.get("num_tokens", num_tokens)
                    phase = parent_context.get("phase")
                if num_tokens is None:
                    output_items = (
                        tuple(_output)
                        if isinstance(_output, (tuple, list))
                        else (_output,)
                    )
                    num_tokens = _infer_first_tensor_num_tokens(output_items)
                if phase is None:
                    phase = _phase_from_num_tokens(
                        int(num_tokens) if num_tokens is not None else None
                    )
                recorder.write_decoder_component_timing(
                    layer_id=layer_id,
                    component=component,
                    elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                    num_tokens=num_tokens,
                    phase=phase,
                )

            return post_hook

        for name, child in module.named_modules():
            if not name:
                continue
            if any(True for _ in child.children()):
                continue
            module_id = id(child)
            component = _attention_leaf_component(attention_kind, name)
            hooks.append(child.register_forward_pre_hook(make_pre_hook(module_id)))
            hooks.append(child.register_forward_hook(make_post_hook(module_id, component)))
        module._mtp_attention_leaf_timing_wrapped = True
        module._mtp_attention_leaf_timing_hooks = hooks

    def _linear_attention_handoff_leaf_component(name: str) -> str | None:
        lowered = name.lower()
        if any(
            token in lowered
            for token in ("in_proj_qkvz", "in_proj_qkv", "in_proj_z", "in_proj_ba")
        ):
            return "attention_linear_handoff_linear_proj_total"
        if lowered.endswith("norm") or ".norm" in lowered:
            return "attention_linear_handoff_norm"
        if "out_proj" in lowered:
            return "attention_linear_handoff_out_proj"
        return None

    def _wrap_linear_attention_handoff_leaf_modules_for_timing(
        module: Any,
        *,
        layer_id: int | None,
    ) -> None:
        if module is None or getattr(
            module,
            "_mtp_linear_attention_handoff_leaf_timing_wrapped",
            False,
        ):
            return
        hooks: list[Any] = []
        starts: dict[int, tuple[int, int | None]] = {}

        def make_pre_hook(module_id: int):
            def pre_hook(_module: torch.nn.Module, inputs: tuple[Any, ...]) -> None:
                recorder = get_active_vllm_router_recorder()
                if recorder is None or not _decoder_source_timing_enabled(recorder):
                    starts.pop(module_id, None)
                    return
                if _decoder_source_timing_mode(recorder) not in {
                    "attention_core_handoff_light",
                    "attention_linear_handoff_light",
                }:
                    starts.pop(module_id, None)
                    return
                starts[module_id] = (
                    time.perf_counter_ns(),
                    _infer_first_tensor_num_tokens(inputs),
                )

            return pre_hook

        def make_post_hook(module_id: int, component: str):
            def post_hook(
                _module: torch.nn.Module,
                _inputs: tuple[Any, ...],
                _output: Any,
            ) -> None:
                recorder = get_active_vllm_router_recorder()
                if recorder is None or not _decoder_source_timing_enabled(recorder):
                    starts.pop(module_id, None)
                    return
                if _decoder_source_timing_mode(recorder) not in {
                    "attention_core_handoff_light",
                    "attention_linear_handoff_light",
                }:
                    starts.pop(module_id, None)
                    return
                start = starts.pop(module_id, None)
                if start is None:
                    return
                start_ns, num_tokens = start
                parent_context = _ACTIVE_DECODER_COMPONENT_CONTEXT_VAR.get()
                phase = None
                if (
                    parent_context is not None
                    and str(parent_context.get("component") or "").startswith(
                        "attention"
                    )
                ):
                    num_tokens = parent_context.get("num_tokens", num_tokens)
                    phase = parent_context.get("phase")
                if num_tokens is None:
                    output_items = (
                        tuple(_output)
                        if isinstance(_output, (tuple, list))
                        else (_output,)
                    )
                    num_tokens = _infer_first_tensor_num_tokens(output_items)
                if phase is None:
                    phase = _phase_from_num_tokens(
                        int(num_tokens) if num_tokens is not None else None
                    )
                recorder.write_decoder_component_timing(
                    layer_id=layer_id,
                    component=component,
                    elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                    num_tokens=num_tokens,
                    phase=phase,
                )

            return post_hook

        for name, child in module.named_modules():
            if not name:
                continue
            if any(True for _ in child.children()):
                continue
            component = _linear_attention_handoff_leaf_component(name)
            if component is None:
                continue
            module_id = id(child)
            hooks.append(child.register_forward_pre_hook(make_pre_hook(module_id)))
            hooks.append(child.register_forward_hook(make_post_hook(module_id, component)))
        module._mtp_linear_attention_handoff_leaf_timing_wrapped = True
        module._mtp_linear_attention_handoff_leaf_timing_hooks = hooks

    def _linear_attention_method_component_for_mode(
        recorder: VllmRouterRecorder,
        component: str,
    ) -> str:
        if _decoder_source_timing_mode(recorder) not in {
            "attention_core_handoff_light",
            "attention_linear_handoff_light",
        }:
            return component
        return {
            "attention_linear_core_total": "attention_linear_handoff_core_total",
            "attention_linear_core_decode_non_spec": (
                "attention_linear_handoff_core_decode_non_spec"
            ),
            "attention_linear_layout_unpack": (
                "attention_linear_handoff_core_post_layout"
            ),
        }.get(component, component)

    def _wrap_linear_attention_source_methods_for_timing(
        module: Any,
        *,
        layer_id: int | None,
    ) -> None:
        if module is None or getattr(module, "_mtp_linear_attention_source_wrapped", False):
            return

        method_components = {
            "_forward_core": "attention_linear_core_total",
            "_forward_core_decode_non_spec": (
                "attention_linear_core_decode_non_spec"
            ),
            "fix_query_key_value_ordering": "attention_linear_layout_unpack",
        }

        def make_method_with_timing(original_method: Any, component: str):
            def method_with_timing(*args: Any, **kwargs: Any) -> Any:
                recorder = get_active_vllm_router_recorder()
                if recorder is None or not _decoder_source_timing_enabled(recorder):
                    return original_method(*args, **kwargs)
                parent_context = _ACTIVE_DECODER_COMPONENT_CONTEXT_VAR.get()
                num_tokens = None
                phase = None
                if (
                    parent_context is not None
                    and str(parent_context.get("component") or "").startswith(
                        "attention"
                    )
                ):
                    num_tokens = parent_context.get("num_tokens")
                    phase = parent_context.get("phase")
                if num_tokens is None:
                    num_tokens = _infer_first_tensor_num_tokens(args)
                if phase is None:
                    phase = _phase_from_num_tokens(
                        int(num_tokens) if num_tokens is not None else None
                    )
                start_ns = time.perf_counter_ns()
                try:
                    return original_method(*args, **kwargs)
                finally:
                    emitted_component = _linear_attention_method_component_for_mode(
                        recorder,
                        component,
                    )
                    recorder.write_decoder_component_timing(
                        layer_id=layer_id,
                        component=emitted_component,
                        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                        num_tokens=num_tokens,
                        phase=phase,
                    )

            return method_with_timing

        wrapped: list[str] = []
        for method_name, component in method_components.items():
            original_method = getattr(module, method_name, None)
            if original_method is None:
                continue
            setattr(
                module,
                method_name,
                make_method_with_timing(original_method, component),
            )
            wrapped.append(method_name)
        module._mtp_linear_attention_source_wrapped = True
        module._mtp_linear_attention_source_methods = tuple(wrapped)

    def _decoder_attention_core_deep_timing_enabled(
        recorder: VllmRouterRecorder,
    ) -> bool:
        if not _decoder_source_timing_enabled(recorder):
            return False
        return _decoder_source_timing_mode(recorder) in {
            "attention_core_deep",
            "attention_deep",
            "attention_linear_core_deep",
            "attention_core_handoff_light",
            "attention_linear_handoff_light",
        }

    def _linear_attention_core_deep_component_for_mode(
        recorder: VllmRouterRecorder,
        component: str,
    ) -> str:
        if _decoder_source_timing_mode(recorder) not in {
            "attention_core_handoff_light",
            "attention_linear_handoff_light",
        }:
            return component
        return {
            "attention_linear_core_conv_update": (
                "attention_linear_handoff_conv_update"
            ),
            "attention_linear_core_recurrent": (
                "attention_linear_handoff_recurrent"
            ),
        }.get(component, component)

    def _wrap_linear_attention_core_deep_functions_for_timing(
        module: Any,
        *,
        layer_id: int | None,
    ) -> None:
        if module is None:
            return
        try:
            source_module = importlib.import_module(module.__class__.__module__)
        except (AttributeError, ModuleNotFoundError):
            return
        if getattr(source_module, "_mtp_linear_attention_core_deep_wrapped", False):
            return

        function_components = {
            "causal_conv1d_update": "attention_linear_core_conv_update",
            "fused_recurrent_gated_delta_rule_packed_decode": (
                "attention_linear_core_recurrent"
            ),
        }

        def make_function_with_timing(original_function: Any, component: str):
            def function_with_timing(*args: Any, **kwargs: Any) -> Any:
                recorder = get_active_vllm_router_recorder()
                if recorder is None or not _decoder_attention_core_deep_timing_enabled(
                    recorder
                ):
                    return original_function(*args, **kwargs)
                parent_context = _ACTIVE_DECODER_COMPONENT_CONTEXT_VAR.get()
                num_tokens = None
                phase = None
                if parent_context is not None:
                    num_tokens = parent_context.get("num_tokens")
                    phase = parent_context.get("phase")
                if num_tokens is None:
                    num_tokens = _infer_first_tensor_num_tokens(args)
                if phase is None:
                    phase = _phase_from_num_tokens(
                        int(num_tokens) if num_tokens is not None else None
                    )
                start_ns = time.perf_counter_ns()
                try:
                    return original_function(*args, **kwargs)
                finally:
                    emitted_component = (
                        _linear_attention_core_deep_component_for_mode(
                            recorder,
                            component,
                        )
                    )
                    recorder.write_decoder_component_timing(
                        layer_id=layer_id,
                        component=emitted_component,
                        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                        num_tokens=num_tokens,
                        phase=phase,
                    )

            return function_with_timing

        wrapped: list[str] = []
        originals: dict[str, Any] = {}
        for function_name, component in function_components.items():
            original_function = getattr(source_module, function_name, None)
            if not callable(original_function):
                continue
            originals[function_name] = original_function
            setattr(
                source_module,
                function_name,
                make_function_with_timing(original_function, component),
            )
            wrapped.append(function_name)
        source_module._mtp_linear_attention_core_deep_wrapped = True
        source_module._mtp_linear_attention_core_deep_functions = tuple(wrapped)
        source_module._mtp_linear_attention_core_deep_originals = originals

    def _decoder_source_timing_enabled(recorder: VllmRouterRecorder) -> bool:
        if not recorder.shadow_emit_decoder_component_timing:
            return False
        mode = str(recorder.shadow_decoder_source_timing_mode or "off").strip().lower()
        return mode not in {"", "off", "none", "false", "0"}

    def _decoder_attention_leaf_timing_enabled(recorder: VllmRouterRecorder) -> bool:
        if not _decoder_source_timing_enabled(recorder):
            return False
        return _decoder_source_timing_mode(recorder) not in {
            "attention_core",
            "attention_methods",
            "attention_linear_core",
        }

    def _decoder_source_timing_mode(recorder: VllmRouterRecorder) -> str:
        mode = str(recorder.shadow_decoder_source_timing_mode or "off").strip().lower()
        aliases = {
            "qwen3next": "qwen3_next",
            "qwen3-next": "qwen3_next",
            "qwen3.5": "qwen3_5",
            "qwen35": "qwen3_5",
            "qwen3-5": "qwen3_5",
        }
        return aliases.get(mode, mode)

    def _decoder_source_copy_supported(
        recorder: VllmRouterRecorder,
        *,
        class_name: str,
    ) -> bool:
        mode = _decoder_source_timing_mode(recorder)
        supported = {
            "qwen3_next": "Qwen3NextDecoderLayer",
            "qwen3_5": "Qwen3_5DecoderLayer",
        }
        return supported.get(mode) == class_name

    def _emit_decoder_source_timing(
        recorder: VllmRouterRecorder,
        *,
        layer_id: int | None,
        component: str,
        start_ns: int,
        num_tokens: int | None,
        phase: str | None,
        status: str = "ok",
    ) -> None:
        recorder.write_decoder_component_timing(
            layer_id=layer_id,
            component=component,
            elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
            num_tokens=num_tokens,
            phase=phase,
        )
        if status != "ok":
            recorder.write_moe_substage_timing(
                layer_id=layer_id,
                substage=f"decoder_source_{component}",
                elapsed_us=0.0,
                num_tokens=num_tokens,
                phase=phase,
                status=status,
            )

    def _make_decoder_forward_with_timing(original_forward: Any) -> Any:
        def decoder_forward_with_timing(self, *args: Any, **kwargs: Any) -> Any:
            recorder = get_active_vllm_router_recorder()
            if recorder is None or not recorder.shadow_emit_decoder_layer_timing:
                return original_forward(self, *args, **kwargs)
            hidden_states = kwargs.get("hidden_states")
            if hidden_states is None and args:
                hidden_states = args[0]
            num_tokens = (
                int(hidden_states.shape[0])
                if isinstance(hidden_states, torch.Tensor)
                and hidden_states.ndim > 0
                else None
            )
            phase = (
                "decode"
                if num_tokens == 1
                else "prefill"
                if num_tokens is not None and num_tokens > 1
                else None
            )
            source_supported = (
                _decoder_source_timing_enabled(recorder)
                and
                _decoder_source_copy_supported(
                    recorder,
                    class_name=self.__class__.__name__,
                )
                and hidden_states is not None
                and isinstance(hidden_states, torch.Tensor)
            )
            start_ns = time.perf_counter_ns()
            try:
                if source_supported:
                    residual = kwargs.get("residual")
                    if residual is None and len(args) > 1:
                        residual = args[1]
                    positions = kwargs.get("positions")
                    if positions is None and len(args) > 2:
                        positions = args[2]
                    step_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        if residual is None:
                            residual = hidden_states
                            hidden_states = self.input_layernorm(hidden_states)
                        else:
                            hidden_states, residual = self.input_layernorm(
                                hidden_states,
                                residual,
                            )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        _emit_decoder_source_timing(
                            recorder,
                            layer_id=getattr(self, "layer_idx", None),
                            component="decoder_input_layernorm",
                            start_ns=step_start_ns,
                            num_tokens=num_tokens,
                            phase=phase,
                            status=status,
                        )

                    attention_output = torch.empty_like(hidden_states)
                    step_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        if self.layer_type == "linear_attention":
                            _wrap_attention_leaf_modules_for_timing(
                                getattr(self, "linear_attn", None),
                                attention_kind="linear_attention",
                                layer_id=getattr(self, "layer_idx", None),
                            )
                            _wrap_linear_attention_source_methods_for_timing(
                                getattr(self, "linear_attn", None),
                                layer_id=getattr(self, "layer_idx", None),
                            )
                            self.linear_attn(
                                hidden_states=hidden_states,
                                output=attention_output,
                            )
                        elif self.layer_type == "full_attention":
                            _wrap_attention_leaf_modules_for_timing(
                                getattr(self, "self_attn", None),
                                attention_kind="full_attention",
                                layer_id=getattr(self, "layer_idx", None),
                            )
                            self.self_attn(
                                hidden_states=hidden_states,
                                output=attention_output,
                                positions=positions,
                            )
                        else:
                            raise ValueError("Invalid layer_type")
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        _emit_decoder_source_timing(
                            recorder,
                            layer_id=getattr(self, "layer_idx", None),
                            component=f"decoder_{self.layer_type}",
                            start_ns=step_start_ns,
                            num_tokens=num_tokens,
                            phase=phase,
                            status=status,
                        )
                    hidden_states = attention_output

                    if self.layer_scale:
                        step_start_ns = time.perf_counter_ns()
                        status = "ok"
                        try:
                            if len(hidden_states.shape) == 2:
                                hidden_states = hidden_states * (
                                    self.attn_layer_scale.to(hidden_states.dtype)[0] + 1
                                )
                            else:
                                hidden_states = hidden_states * (
                                    self.attn_layer_scale.to(hidden_states.dtype) + 1
                                )
                        except Exception as exc:
                            status = f"error:{type(exc).__name__}"
                            raise
                        finally:
                            _emit_decoder_source_timing(
                                recorder,
                                layer_id=getattr(self, "layer_idx", None),
                                component="decoder_attention_layer_scale",
                                start_ns=step_start_ns,
                                num_tokens=num_tokens,
                                phase=phase,
                                status=status,
                            )

                    step_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        hidden_states, residual = self.post_attention_layernorm(
                            hidden_states,
                            residual,
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        _emit_decoder_source_timing(
                            recorder,
                            layer_id=getattr(self, "layer_idx", None),
                            component="decoder_post_attention_layernorm",
                            start_ns=step_start_ns,
                            num_tokens=num_tokens,
                            phase=phase,
                            status=status,
                        )

                    step_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        hidden_states = self.mlp(hidden_states)
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        _emit_decoder_source_timing(
                            recorder,
                            layer_id=getattr(self, "layer_idx", None),
                            component="decoder_mlp_call",
                            start_ns=step_start_ns,
                            num_tokens=num_tokens,
                            phase=phase,
                            status=status,
                        )

                    if self.layer_scale:
                        step_start_ns = time.perf_counter_ns()
                        status = "ok"
                        try:
                            if len(hidden_states.shape) == 2:
                                hidden_states = hidden_states * (
                                    self.ffn_layer_scale.to(hidden_states.dtype)[0] + 1
                                )
                            else:
                                assert len(hidden_states.shape) == len(
                                    self.ffn_layer_scale.shape
                                ), (
                                    f"shape must be the same {len(hidden_states.shape)}, "
                                    f"{len(self.ffn_layer_scale.shape)}"
                                )
                                hidden_states = hidden_states * (
                                    self.ffn_layer_scale.to(hidden_states.dtype) + 1
                                )
                        except Exception as exc:
                            status = f"error:{type(exc).__name__}"
                            raise
                        finally:
                            _emit_decoder_source_timing(
                                recorder,
                                layer_id=getattr(self, "layer_idx", None),
                                component="decoder_ffn_layer_scale",
                                start_ns=step_start_ns,
                                num_tokens=num_tokens,
                                phase=phase,
                                status=status,
                            )
                    return hidden_states, residual
                return original_forward(self, *args, **kwargs)
            finally:
                recorder.write_decoder_layer_timing(
                    layer_id=getattr(self, "layer_idx", None),
                    elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                    num_tokens=num_tokens,
                    phase=phase,
                )

        return decoder_forward_with_timing

    def moe_forward_with_trace(self, hidden_states: torch.Tensor) -> torch.Tensor:
        recorder = get_active_vllm_router_recorder()
        if recorder is None:
            return original_moe_forward(self, hidden_states)

        orig_shape = hidden_states.shape
        num_tokens, hidden_dim = hidden_states.shape
        layer_id = getattr(self, "_mtp_trace_layer_id", None)
        layer_phase = _phase_from_num_tokens(int(num_tokens))
        if self.experts.is_internal_router:
            experts_start_ns = time.perf_counter_ns()
            experts_status = "internal_router"
            try:
                return original_moe_forward(self, hidden_states)
            except Exception as exc:
                experts_status = f"error:{type(exc).__name__}"
                raise
            finally:
                recorder.write_moe_substage_timing(
                    layer_id=layer_id,
                    substage="experts_total",
                    elapsed_us=(time.perf_counter_ns() - experts_start_ns) / 1000.0,
                    num_tokens=int(num_tokens),
                    phase=layer_phase,
                    status=experts_status,
                )

        routed_states = hidden_states.view(-1, hidden_dim)

        if self.is_sequence_parallel:
            routed_states = qwen3_next.sequence_parallel_chunk(routed_states)

        router_start_ns = time.perf_counter_ns()
        router_logits, _ = self.gate(routed_states)
        recorder.write_moe_substage_timing(
            layer_id=layer_id,
            substage="router_logits",
            elapsed_us=(time.perf_counter_ns() - router_start_ns) / 1000.0,
            num_tokens=int(num_tokens),
            phase=layer_phase,
        )
        recorder.record(
            layer_id=layer_id,
            router_logits=router_logits,
        )
        experts_start_ns = time.perf_counter_ns()
        final_hidden_states = self.experts(
            hidden_states=routed_states,
            router_logits=router_logits,
        )
        recorder.write_moe_substage_timing(
            layer_id=layer_id,
            substage="experts_total",
            elapsed_us=(time.perf_counter_ns() - experts_start_ns) / 1000.0,
            num_tokens=int(num_tokens),
            phase=layer_phase,
        )

        if self.is_sequence_parallel:
            final_hidden_states = qwen3_next.tensor_model_parallel_all_gather(
                final_hidden_states, 0
            )
            final_hidden_states = final_hidden_states[:num_tokens]

        return final_hidden_states.view(orig_shape)

    for decoder_class in decoder_classes:
        decoder_class.__init__ = _make_decoder_init_with_trace_layer(decoder_class.__init__)
        decoder_class.forward = _make_decoder_forward_with_timing(decoder_class.forward)

    qwen3_next.Qwen3NextForCausalLM.load_weights = qwen3_next_load_weights_with_text_prefix_remap
    qwen3_next.Qwen3NextSparseMoeBlock.forward = moe_forward_with_trace

    if fused_moe_layer is not None and hasattr(fused_moe_layer.FusedMoE, "forward_impl"):
        original_fused_moe_forward_impl = fused_moe_layer.FusedMoE.forward_impl

        def fused_moe_forward_impl_with_trace(
            self,
            hidden_states: torch.Tensor,
            router_logits: torch.Tensor,
        ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
            recorder = get_active_vllm_router_recorder()
            gate = getattr(self, "gate", None)
            layer_id = getattr(self, "_mtp_trace_layer_id", None)
            num_tokens = int(hidden_states.shape[0]) if hidden_states.ndim > 0 else None
            phase = _phase_from_num_tokens(num_tokens)
            if recorder is not None and gate is not None and layer_id is not None:
                gate_start_ns = time.perf_counter_ns()
                trace_router_logits, _ = gate(hidden_states)
                recorder.write_moe_substage_timing(
                    layer_id=int(layer_id),
                    substage="router_logits",
                    elapsed_us=(time.perf_counter_ns() - gate_start_ns) / 1000.0,
                    num_tokens=num_tokens,
                    phase=phase,
                    status="trace_duplicate_gate",
                )
                recorder.record(
                    layer_id=int(layer_id),
                    router_logits=trace_router_logits,
                )
            if recorder is None or layer_id is None:
                return original_fused_moe_forward_impl(
                    self,
                    hidden_states,
                    router_logits,
                )
            experts_start_ns = time.perf_counter_ns()
            experts_status = "forward_impl"
            try:
                return original_fused_moe_forward_impl(
                    self,
                    hidden_states,
                    router_logits,
                )
            except Exception as exc:
                experts_status = f"error:{type(exc).__name__}"
                raise
            finally:
                recorder.write_moe_substage_timing(
                    layer_id=int(layer_id),
                    substage="experts_total",
                    elapsed_us=(time.perf_counter_ns() - experts_start_ns) / 1000.0,
                    num_tokens=num_tokens,
                    phase=phase,
                    status=experts_status,
                )

        fused_moe_layer.FusedMoE.forward_impl = fused_moe_forward_impl_with_trace

    try:
        moe_runner = importlib.import_module(
            "vllm.model_executor.layers.fused_moe.runner.moe_runner"
        )
    except ModuleNotFoundError:
        moe_runner = None

    if moe_runner is not None and hasattr(moe_runner, "MoERunner"):
        original_apply_quant_method = moe_runner.MoERunner._apply_quant_method

        def _emit_active_moe_substage(
            recorder: VllmRouterRecorder | None,
            *,
            substage: str,
            start_ns: int,
            status: str = "ok",
        ) -> None:
            if recorder is None:
                return
            if not recorder.should_record_active_moe_substage(substage):
                return
            recorder.write_active_moe_substage_timing(
                substage=substage,
                elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                status=status,
                _sample_checked=True,
            )

        original_forward_impl = moe_runner.MoERunner._forward_impl

        def _forced_shared_aux_stream_order(
            shared_experts_obj: Any,
            shared_experts_input: torch.Tensor | None,
            recorder: VllmRouterRecorder | None,
        ) -> tuple[Any | None, str]:
            if recorder is None or shared_experts_input is None:
                return None, "missing_recorder_or_input"
            if not bool(recorder.shadow_shared_experts_force_aux_stream):
                return None, "disabled"
            if bool(getattr(shared_experts_obj, "_disable_shared_experts_overlap", False)):
                return None, "native_overlap_disabled"
            native_order = shared_experts_obj._determine_shared_experts_order(
                shared_experts_input,
            )
            if native_order == shared_experts_module.SharedExpertsOrder.MK_INTERNAL_OVERLAPPED:
                return None, "native_mk_internal"
            if native_order == shared_experts_module.SharedExpertsOrder.MULTI_STREAM_OVERLAPPED:
                return native_order, "native_aux_stream"
            stream = getattr(shared_experts_obj, "_stream", None)
            if stream is None:
                return None, "missing_stream"
            threshold = int(
                getattr(
                    shared_experts_module.envs,
                    "VLLM_SHARED_EXPERTS_STREAM_TOKEN_THRESHOLD",
                    256,
                )
            )
            if int(shared_experts_input.shape[0]) > threshold:
                return None, "over_threshold"
            return (
                shared_experts_module.SharedExpertsOrder.MULTI_STREAM_OVERLAPPED,
                "forced_aux_stream",
            )

        def forward_impl_with_moe_context(
            self,
            layer: torch.nn.Module,
            hidden_states: torch.Tensor,
            router_logits: torch.Tensor,
            shared_experts_input: torch.Tensor | None,
            *extra_args: Any,
            **extra_kwargs: Any,
        ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
            recorder = get_active_vllm_router_recorder()
            layer_id = getattr(layer, "_mtp_trace_layer_id", None)
            if recorder is None or layer_id is None:
                return original_forward_impl(
                    self,
                    layer,
                    hidden_states,
                    router_logits,
                    shared_experts_input,
                    *extra_args,
                    **extra_kwargs,
                )
            num_tokens = int(hidden_states.shape[0]) if hidden_states.ndim > 0 else None
            context = {
                "recorder": recorder,
                "layer_id": int(layer_id),
                "num_tokens": num_tokens,
                "phase": _phase_from_num_tokens(num_tokens),
                "moe_quantize_input_call_index": 0,
                "moe_resize_cache_call_index": 0,
                "moe_tensor_alloc_call_index": 0,
            }
            context_token = push_active_moe_assignment_context(context)
            try:
                return original_forward_impl(
                    self,
                    layer,
                    hidden_states,
                    router_logits,
                    shared_experts_input,
                    *extra_args,
                    **extra_kwargs,
                )
            finally:
                reset_active_moe_assignment_context(context_token)

        moe_runner.MoERunner._forward_impl = forward_impl_with_moe_context

        if hasattr(moe_runner.MoERunner, "_maybe_sync_shared_experts_stream"):
            original_maybe_sync_shared_experts_stream = (
                moe_runner.MoERunner._maybe_sync_shared_experts_stream
            )

            def maybe_sync_shared_experts_stream_with_timing(
                self,
                shared_experts_input: torch.Tensor | None,
            ) -> Any:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_maybe_sync_shared_experts_stream(
                        self,
                        shared_experts_input,
                    )
                forced_order, force_reason = (
                    _forced_shared_aux_stream_order(
                        self._shared_experts,
                        shared_experts_input,
                        recorder,
                    )
                    if getattr(self, "_shared_experts", None) is not None
                    else (None, "missing_shared_experts")
                )
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    if (
                        forced_order
                        == shared_experts_module.SharedExpertsOrder.MULTI_STREAM_OVERLAPPED
                        and shared_experts_input is not None
                        and self._shared_experts is not None
                    ):
                        stream = self._shared_experts._stream
                        assert stream is not None
                        shared_experts_input.record_stream(stream)
                        stream.wait_stream(shared_experts_module.current_stream())
                        status = force_reason
                        return None
                    return original_maybe_sync_shared_experts_stream(
                        self,
                        shared_experts_input,
                    )
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_active_moe_substage(
                        recorder,
                        substage="experts_shared_stream_sync",
                        start_ns=start_ns,
                        status=status,
                    )

            moe_runner.MoERunner._maybe_sync_shared_experts_stream = (
                maybe_sync_shared_experts_stream_with_timing
            )

        if hasattr(moe_runner.MoERunner, "_maybe_dispatch"):
            original_maybe_dispatch = moe_runner.MoERunner._maybe_dispatch

            def maybe_dispatch_with_timing(
                self,
                layer: torch.nn.Module,
                hidden_states: torch.Tensor,
                router_logits: torch.Tensor,
            ) -> tuple[torch.Tensor, torch.Tensor]:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_maybe_dispatch(
                        self,
                        layer,
                        hidden_states,
                        router_logits,
                    )
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    return original_maybe_dispatch(
                        self,
                        layer,
                        hidden_states,
                        router_logits,
                    )
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_active_moe_substage(
                        recorder,
                        substage="experts_maybe_dispatch",
                        start_ns=start_ns,
                        status=status,
                    )

            moe_runner.MoERunner._maybe_dispatch = maybe_dispatch_with_timing

        if hasattr(moe_runner.MoERunner, "_maybe_combine"):
            original_maybe_combine = moe_runner.MoERunner._maybe_combine

            def maybe_combine_with_timing(
                self,
                shared_output: torch.Tensor | None,
                hidden_states: torch.Tensor,
            ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor | None]:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_maybe_combine(self, shared_output, hidden_states)
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    return original_maybe_combine(self, shared_output, hidden_states)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_active_moe_substage(
                        recorder,
                        substage="experts_maybe_combine",
                        start_ns=start_ns,
                        status=status,
                    )

            moe_runner.MoERunner._maybe_combine = maybe_combine_with_timing

        try:
            shared_experts_module = importlib.import_module(
                "vllm.model_executor.layers.fused_moe.runner.shared_experts"
            )
        except ModuleNotFoundError:
            shared_experts_module = None

        if shared_experts_module is not None and hasattr(
            shared_experts_module,
            "SharedExperts",
        ):
            original_shared_experts_apply = shared_experts_module.SharedExperts.apply

            def _shared_expert_substage_from_name(name: str) -> str:
                lowered = name.lower()
                if any(
                    token in lowered
                    for token in (
                        "gate_up",
                        "gateup",
                        "w13",
                        "fc1",
                        "up_proj",
                        "gate_proj",
                    )
                ):
                    return "experts_shared_w1"
                if any(
                    token in lowered
                    for token in ("act", "silu", "gelu", "activation")
                ):
                    return "experts_shared_activation"
                if any(
                    token in lowered
                    for token in ("down_proj", "down", "w2", "fc2")
                ):
                    return "experts_shared_w2"
                if any(
                    token in lowered
                    for token in (
                        "output",
                        "combine",
                        "sum",
                        "expert_gate",
                        "shared_expert_gate",
                    )
                ):
                    return "experts_shared_output_combine"
                return "experts_shared_child_other"

            def _emit_shared_source_timing(
                recorder: VllmRouterRecorder,
                *,
                substage: str,
                start_ns: int,
                status: str = "ok",
            ) -> None:
                recorder.write_active_moe_substage_timing(
                    substage=substage,
                    elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                    status=status,
                )

            def _run_qwen2_moe_mlp_with_source_split(
                layer_module: torch.nn.Module,
                shared_experts_input: torch.Tensor,
                recorder: VllmRouterRecorder,
            ) -> torch.Tensor:
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    gate_up = _unwrap_vllm_projection_output(
                        layer_module.gate_up_proj(shared_experts_input)
                    )
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_w1",
                        start_ns=start_ns,
                        status=status,
                    )

                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    out = layer_module.act_fn(gate_up)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_activation",
                        start_ns=start_ns,
                        status=status,
                    )

                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    out = _unwrap_vllm_projection_output(layer_module.down_proj(out))
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_w2",
                        start_ns=start_ns,
                        status=status,
                    )

                expert_gate = getattr(layer_module, "expert_gate", None)
                if expert_gate is None:
                    return out
                ablation = _shared_expert_output_gate_ablation_mode(recorder)
                if ablation in {"unity", "identity", "skip", "disabled"}:
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_output_gate",
                        start_ns=time.perf_counter_ns(),
                        status=f"ablation:{ablation}",
                    )
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_output_sigmoid_mul",
                        start_ns=time.perf_counter_ns(),
                        status=f"ablation:{ablation}",
                    )
                    return out

                postprocess = _shared_expert_output_gate_postprocess_mode(recorder)
                if postprocess in {"fused_triton", "triton_fused"}:
                    start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        out = _run_shared_expert_output_gate_fused_triton(
                            hidden_states=shared_experts_input,
                            out=out,
                            expert_gate=expert_gate,
                        )
                    except RuntimeError as exc:
                        if not _shared_expert_fused_gate_fallbackable(exc):
                            status = f"error:{type(exc).__name__}"
                            raise
                        status = f"fallback_default:{type(exc).__name__}"
                        try:
                            out = _run_shared_expert_output_gate_default_postprocess(
                                hidden_states=shared_experts_input,
                                out=out,
                                expert_gate=expert_gate,
                                postprocess="default",
                            )
                        except Exception as fallback_exc:
                            status = f"fallback_error:{type(fallback_exc).__name__}"
                            raise
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        _emit_shared_source_timing(
                            recorder,
                            substage="experts_shared_output_gate_fused",
                            start_ns=start_ns,
                            status=status,
                        )
                    return out

                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    gate_out = _unwrap_vllm_projection_output(
                        expert_gate(shared_experts_input)
                    )
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_output_gate",
                        start_ns=start_ns,
                        status=status,
                    )

                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    if postprocess == "inplace":
                        gate_out.sigmoid_()
                        out.mul_(gate_out)
                    else:
                        out = torch.sigmoid(gate_out) * out
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_output_sigmoid_mul",
                        start_ns=start_ns,
                        status=status,
                    )
                return out

            def _run_qwen2_moe_mlp_with_custom_gate_no_timing(
                layer_module: torch.nn.Module,
                shared_experts_input: torch.Tensor,
                recorder: VllmRouterRecorder,
            ) -> torch.Tensor:
                gate_up = _unwrap_vllm_projection_output(
                    layer_module.gate_up_proj(shared_experts_input)
                )
                out = layer_module.act_fn(gate_up)
                out = _unwrap_vllm_projection_output(layer_module.down_proj(out))

                expert_gate = getattr(layer_module, "expert_gate", None)
                if expert_gate is None:
                    return out
                ablation = _shared_expert_output_gate_ablation_mode(recorder)
                if ablation in {"unity", "identity", "skip", "disabled"}:
                    return out

                postprocess = _shared_expert_output_gate_postprocess_mode(recorder)
                if postprocess in {"fused_triton", "triton_fused"}:
                    try:
                        return _run_shared_expert_output_gate_fused_triton(
                            hidden_states=shared_experts_input,
                            out=out,
                            expert_gate=expert_gate,
                        )
                    except RuntimeError as exc:
                        if not _shared_expert_fused_gate_fallbackable(exc):
                            raise
                        return _run_shared_expert_output_gate_default_postprocess(
                            hidden_states=shared_experts_input,
                            out=out,
                            expert_gate=expert_gate,
                            postprocess="default",
                        )

                return _run_shared_expert_output_gate_default_postprocess(
                    hidden_states=shared_experts_input,
                    out=out,
                    expert_gate=expert_gate,
                    postprocess=postprocess,
                )

            def _run_qwen2_moe_mlp_with_body_region_timing(
                layer_module: torch.nn.Module,
                shared_experts_input: torch.Tensor,
                recorder: VllmRouterRecorder,
            ) -> torch.Tensor:
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    gate_up = _unwrap_vllm_projection_output(
                        layer_module.gate_up_proj(shared_experts_input)
                    )
                    out = layer_module.act_fn(gate_up)
                    out = _unwrap_vllm_projection_output(layer_module.down_proj(out))
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_body_core",
                        start_ns=start_ns,
                        status=status,
                    )

                expert_gate = getattr(layer_module, "expert_gate", None)
                if expert_gate is None:
                    return out
                ablation = _shared_expert_output_gate_ablation_mode(recorder)
                if ablation in {"unity", "identity", "skip", "disabled"}:
                    return out

                postprocess = _shared_expert_output_gate_postprocess_mode(recorder)
                if postprocess in {"fused_triton", "triton_fused"}:
                    start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        out = _run_shared_expert_output_gate_fused_triton(
                            hidden_states=shared_experts_input,
                            out=out,
                            expert_gate=expert_gate,
                        )
                    except RuntimeError as exc:
                        if not _shared_expert_fused_gate_fallbackable(exc):
                            status = f"error:{type(exc).__name__}"
                            raise
                        status = f"fallback_default:{type(exc).__name__}"
                        try:
                            out = _run_shared_expert_output_gate_default_postprocess(
                                hidden_states=shared_experts_input,
                                out=out,
                                expert_gate=expert_gate,
                                postprocess="default",
                            )
                        except Exception as fallback_exc:
                            status = f"fallback_error:{type(fallback_exc).__name__}"
                            raise
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        _emit_shared_source_timing(
                            recorder,
                            substage="experts_shared_body_gate_fused",
                            start_ns=start_ns,
                            status=status,
                        )
                    return out

                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    gate_out = _unwrap_vllm_projection_output(
                        expert_gate(shared_experts_input)
                    )
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_body_gate_proj",
                        start_ns=start_ns,
                        status=status,
                    )

                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    if postprocess == "inplace":
                        gate_out.sigmoid_()
                        out.mul_(gate_out)
                    else:
                        out = torch.sigmoid(gate_out) * out
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_shared_source_timing(
                        recorder,
                        substage="experts_shared_body_gate_apply",
                        start_ns=start_ns,
                        status=status,
                    )
                return out

            def _supports_qwen2_moe_mlp_source_split(
                layer_module: torch.nn.Module,
            ) -> bool:
                cls = layer_module.__class__
                if cls.__name__ != "Qwen2MoeMLP":
                    return False
                if cls.__module__ != "vllm.model_executor.models.qwen2_moe":
                    return False
                required_callables = (
                    "gate_up_proj",
                    "act_fn",
                    "down_proj",
                )
                if not all(
                    callable(getattr(layer_module, name, None))
                    for name in required_callables
                ):
                    return False
                expert_gate = getattr(layer_module, "expert_gate", None)
                if expert_gate is not None and not callable(expert_gate):
                    return False
                try:
                    forward_signature = inspect.signature(layer_module.forward)
                except (TypeError, ValueError):
                    return False
                forward_params = tuple(forward_signature.parameters)
                return forward_params == ("x",)

            def _run_shared_layer_with_source_split(
                layer_module: torch.nn.Module,
                shared_experts_input: torch.Tensor,
                recorder: VllmRouterRecorder,
            ) -> torch.Tensor:
                if _supports_qwen2_moe_mlp_source_split(layer_module):
                    return _run_qwen2_moe_mlp_with_source_split(
                        layer_module,
                        shared_experts_input,
                        recorder,
                    )

                hooks: list[Any] = []
                starts: dict[int, int] = {}

                def make_pre_hook(module_id: int):
                    def pre_hook(_module: torch.nn.Module, _inputs: tuple[Any, ...]) -> None:
                        starts[module_id] = time.perf_counter_ns()

                    return pre_hook

                def make_post_hook(module_id: int, substage: str, module_name: str):
                    def post_hook(
                        _module: torch.nn.Module,
                        _inputs: tuple[Any, ...],
                        _output: Any,
                    ) -> None:
                        start_ns = starts.pop(module_id, None)
                        if start_ns is None:
                            return
                        status = "ok"
                        if substage == "experts_shared_child_other":
                            safe_name = module_name.replace(":", "_")[:120]
                            status = f"leaf:{safe_name or '<unnamed>'}"
                        recorder.write_active_moe_substage_timing(
                            substage=substage,
                            elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                            status=status,
                        )

                    return post_hook

                try:
                    for name, module in layer_module.named_modules():
                        if not name:
                            continue
                        if any(True for _ in module.children()):
                            continue
                        substage = _shared_expert_substage_from_name(name)
                        module_id = id(module)
                        hooks.append(module.register_forward_pre_hook(make_pre_hook(module_id)))
                        hooks.append(
                            module.register_forward_hook(
                                make_post_hook(module_id, substage, name)
                            )
                        )
                    return layer_module(shared_experts_input)
                finally:
                    for handle in hooks:
                        handle.remove()

            def shared_experts_apply_with_timing(
                self,
                shared_experts_input: torch.Tensor,
                order: Any,
            ) -> Any:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_shared_experts_apply(
                        self,
                        shared_experts_input,
                        order,
                    )
                fused_gate_enabled = _shared_expert_fused_gate_enabled(recorder)
                custom_gate_enabled = _shared_expert_custom_gate_enabled(recorder)
                source_timing_enabled = _shared_expert_source_timing_enabled(recorder)
                body_timing_enabled = _shared_expert_body_timing_enabled(recorder)
                body_region_timing_enabled = (
                    _shared_expert_body_region_timing_enabled(recorder)
                )
                if (
                    not source_timing_enabled
                    and not body_timing_enabled
                    and not custom_gate_enabled
                    and not fused_gate_enabled
                ):
                    return original_shared_experts_apply(
                        self,
                        shared_experts_input,
                        order,
                    )
                determine_start_ns = time.perf_counter_ns()
                determine_status = "ok"
                try:
                    native_order = self._determine_shared_experts_order(
                        shared_experts_input,
                    )
                    forced_order, force_reason = _forced_shared_aux_stream_order(
                        self,
                        shared_experts_input,
                        recorder,
                    )
                    experts_order = forced_order if forced_order is not None else native_order
                    if force_reason not in ("disabled", "missing_recorder_or_input"):
                        determine_status = force_reason
                except Exception as exc:
                    determine_status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    _emit_active_moe_substage(
                        recorder,
                        substage="experts_shared_determine_order",
                        start_ns=determine_start_ns,
                        status=determine_status,
                    )
                if order != experts_order:
                    _emit_active_moe_substage(
                        recorder,
                        substage="experts_shared_apply_skipped",
                        start_ns=time.perf_counter_ns(),
                        status=f"order_mismatch:{getattr(experts_order, 'name', experts_order)}",
                    )
                    return None

                assert self._output[self._output_idx] is None

                if order == shared_experts_module.SharedExpertsOrder.MULTI_STREAM_OVERLAPPED:
                    if custom_gate_enabled:
                        if not _supports_qwen2_moe_mlp_source_split(self._layer):
                            return original_shared_experts_apply(
                                self,
                                shared_experts_input,
                                order,
                            )
                        if source_timing_enabled:
                            layer_start_ns = time.perf_counter_ns()
                            layer_status = "custom_gate_direct_from_multistream"
                            try:
                                self._output[self._output_idx] = (
                                    _run_shared_layer_with_source_split(
                                        self._layer,
                                        shared_experts_input,
                                        recorder,
                                    )
                                )
                            except Exception as exc:
                                layer_status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                _emit_active_moe_substage(
                                    recorder,
                                    substage="experts_shared_direct_layer",
                                    start_ns=layer_start_ns,
                                    status=layer_status,
                                )
                        elif body_region_timing_enabled:
                            layer_start_ns = time.perf_counter_ns()
                            layer_status = "custom_gate_body_regions_from_multistream"
                            try:
                                self._output[self._output_idx] = (
                                    _run_qwen2_moe_mlp_with_body_region_timing(
                                        self._layer,
                                        shared_experts_input,
                                        recorder,
                                    )
                                )
                            except Exception as exc:
                                layer_status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                _emit_active_moe_substage(
                                    recorder,
                                    substage="experts_shared_direct_layer",
                                    start_ns=layer_start_ns,
                                    status=layer_status,
                                )
                        else:
                            self._output[self._output_idx] = (
                                _run_qwen2_moe_mlp_with_custom_gate_no_timing(
                                    self._layer,
                                    shared_experts_input,
                                    recorder,
                                )
                            )
                        assert self._output[self._output_idx] is not None
                        return None
                    layer_start_ns = time.perf_counter_ns()
                    layer_status = "ok"
                    try:
                        self._output[self._output_idx] = self._run_in_aux_stream(
                            shared_experts_input,
                        )
                    except Exception as exc:
                        layer_status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        _emit_active_moe_substage(
                            recorder,
                            substage="experts_shared_aux_stream_layer_wait",
                            start_ns=layer_start_ns,
                            status=layer_status,
                        )
                else:
                    if custom_gate_enabled and not source_timing_enabled:
                        if not _supports_qwen2_moe_mlp_source_split(self._layer):
                            return original_shared_experts_apply(
                                self,
                                shared_experts_input,
                                order,
                            )
                        if body_region_timing_enabled:
                            layer_start_ns = time.perf_counter_ns()
                            layer_status = "custom_gate_body_regions"
                            try:
                                self._output[self._output_idx] = (
                                    _run_qwen2_moe_mlp_with_body_region_timing(
                                        self._layer,
                                        shared_experts_input,
                                        recorder,
                                    )
                                )
                            except Exception as exc:
                                layer_status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                _emit_active_moe_substage(
                                    recorder,
                                    substage="experts_shared_direct_layer",
                                    start_ns=layer_start_ns,
                                    status=layer_status,
                                )
                            assert self._output[self._output_idx] is not None
                            return None
                        self._output[self._output_idx] = (
                            _run_qwen2_moe_mlp_with_custom_gate_no_timing(
                                self._layer,
                                shared_experts_input,
                                recorder,
                            )
                        )
                        assert self._output[self._output_idx] is not None
                        return None
                    layer_start_ns = time.perf_counter_ns()
                    layer_status = "ok"
                    try:
                        self._output[self._output_idx] = (
                            _run_shared_layer_with_source_split(
                                self._layer,
                                shared_experts_input,
                                recorder,
                            )
                            if source_timing_enabled
                            else _run_qwen2_moe_mlp_with_body_region_timing(
                                self._layer,
                                shared_experts_input,
                                recorder,
                            )
                            if body_region_timing_enabled
                            and _supports_qwen2_moe_mlp_source_split(self._layer)
                            else self._layer(shared_experts_input)
                        )
                    except Exception as exc:
                        layer_status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        _emit_active_moe_substage(
                            recorder,
                            substage="experts_shared_direct_layer",
                            start_ns=layer_start_ns,
                            status=layer_status,
                        )

                assert self._output[self._output_idx] is not None
                return None

            shared_experts_module.SharedExperts.apply = shared_experts_apply_with_timing

        def apply_quant_method_with_prelaunch_assertion(
            self,
            layer: torch.nn.Module,
            hidden_states: torch.Tensor,
            router_logits: torch.Tensor,
            shared_experts_input: torch.Tensor | None,
            *extra_args: Any,
            **extra_kwargs: Any,
        ) -> tuple[torch.Tensor | None, torch.Tensor]:
            recorder = get_active_vllm_router_recorder()
            if recorder is None and not extra_args and not extra_kwargs:
                return original_apply_quant_method(
                    self,
                    layer,
                    hidden_states,
                    router_logits,
                    shared_experts_input,
                )
            remaining_extra_args, passthrough_kwargs = _split_optional_input_ids(
                extra_args,
                extra_kwargs,
            )
            input_ids = passthrough_kwargs.get("input_ids")
            if recorder is None:
                return _call_with_supported_kwargs(
                    original_apply_quant_method,
                    self,
                    layer,
                    hidden_states,
                    router_logits,
                    shared_experts_input,
                    *remaining_extra_args,
                    **passthrough_kwargs,
                )
            layer_id = getattr(layer, "_mtp_trace_layer_id", None)
            layer_num_tokens = (
                int(hidden_states.shape[0]) if hidden_states.ndim > 0 else None
            )
            layer_phase = _phase_from_num_tokens(layer_num_tokens)
            outer_context_token = None
            if layer_id is not None:
                outer_context_token = push_active_moe_assignment_context(
                    {
                        "recorder": recorder,
                        "layer_id": int(layer_id),
                        "num_tokens": layer_num_tokens,
                        "phase": layer_phase,
                        "moe_quantize_input_call_index": 0,
                        "moe_resize_cache_call_index": 0,
                        "moe_tensor_alloc_call_index": 0,
                    }
                )
            quant_method = getattr(self, "quant_method", None)
            if quant_method is None:
                quant_method = getattr(self, "_quant_method")

            def emit(substage: str, start_ns: int, status: str = "ok") -> None:
                if layer_id is None:
                    return
                recorder.write_moe_substage_timing(
                    layer_id=int(layer_id),
                    substage=substage,
                    elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                    num_tokens=layer_num_tokens,
                    phase=layer_phase,
                    status=status,
                )

            try:
                status = "ok"
                shared_no_overlap_start_ns = time.perf_counter_ns()
                try:
                    self._maybe_apply_shared_experts(
                        shared_experts_input,
                        moe_runner.SharedExpertsOrder.NO_OVERLAP,
                    )
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    emit("experts_shared_no_overlap", shared_no_overlap_start_ns, status)
                if quant_method.is_monolithic:
                    monolithic_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        fused_out = _call_with_supported_kwargs(
                            quant_method.apply_monolithic,
                            layer=layer,
                            x=hidden_states,
                            router_logits=router_logits,
                            **passthrough_kwargs,
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit("quant_method_apply_monolithic", monolithic_start_ns, status)
                else:
                    select_start_ns = time.perf_counter_ns()
                    topk_weights, topk_ids = _call_with_supported_kwargs(
                        self.router.select_experts,
                        hidden_states=hidden_states,
                        router_logits=router_logits,
                        **passthrough_kwargs,
                    )
                    if layer_id is not None:
                        recorder.write_moe_substage_timing(
                            layer_id=int(layer_id),
                            substage="select_experts",
                            elapsed_us=(
                                time.perf_counter_ns() - select_start_ns
                            )
                            / 1000.0,
                            num_tokens=layer_num_tokens,
                            phase=layer_phase,
                        )
                    if layer_id is not None:
                        pre_apply_start_ns = time.perf_counter_ns()
                        pre_apply_status = "ok"
                        try:
                            recorder.write_prelaunch_descriptor_assertion(
                                layer_id=int(layer_id),
                                topk_ids=topk_ids,
                            )
                        except Exception as exc:
                            pre_apply_status = f"error:{type(exc).__name__}"
                            raise
                        finally:
                            emit(
                                "experts_pre_quant_apply_glue",
                                pre_apply_start_ns,
                                pre_apply_status,
                            )
                    assignment_context_token = None
                    apply_start_ns = time.perf_counter_ns()
                    try:
                        if layer_id is not None:
                            assignment_context_token = push_active_moe_assignment_context(
                                {
                                    "recorder": recorder,
                                    "layer_id": int(layer_id),
                                    "num_tokens": layer_num_tokens,
                                    "phase": layer_phase,
                                    "routed_layer": layer,
                                    "moe_quantize_input_call_index": 0,
                                    "moe_resize_cache_call_index": 0,
                                    "moe_tensor_alloc_call_index": 0,
                                }
                            )
                        fused_out = _call_with_supported_kwargs(
                            quant_method.apply,
                            layer=layer,
                            x=hidden_states,
                            topk_weights=topk_weights,
                            topk_ids=topk_ids,
                            shared_experts=self._shared_experts,
                            shared_experts_input=shared_experts_input,
                        )
                    finally:
                        apply_elapsed_us = (
                            time.perf_counter_ns() - apply_start_ns
                        ) / 1000.0
                        if assignment_context_token is not None:
                            reset_active_moe_assignment_context(
                                assignment_context_token
                            )
                    if layer_id is not None:
                        recorder.write_descriptor_layer_timing(
                            layer_id=int(layer_id),
                            apply_us=apply_elapsed_us,
                            num_tokens=layer_num_tokens,
                            phase=layer_phase,
                        )
                        recorder.write_moe_substage_timing(
                            layer_id=int(layer_id),
                            substage="quant_method_apply",
                            elapsed_us=apply_elapsed_us,
                            num_tokens=layer_num_tokens,
                            phase=layer_phase,
                        )

                status = "ok"
                shared_overlap_start_ns = time.perf_counter_ns()
                try:
                    self._maybe_apply_shared_experts(
                        shared_experts_input,
                        moe_runner.SharedExpertsOrder.MULTI_STREAM_OVERLAPPED,
                    )
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    emit("experts_shared_overlap", shared_overlap_start_ns, status)
                output_fetch_start_ns = time.perf_counter_ns()
                shared_output = (
                    self._shared_experts.output
                    if self._shared_experts is not None
                    else None
                )
                emit("experts_shared_output_fetch", output_fetch_start_ns)
                return shared_output, fused_out
            finally:
                if outer_context_token is not None:
                    reset_active_moe_assignment_context(outer_context_token)

        moe_runner.MoERunner._apply_quant_method = apply_quant_method_with_prelaunch_assertion

    try:
        fused_moe_impl = importlib.import_module(
            "vllm.model_executor.layers.fused_moe.fused_moe"
        )
    except ModuleNotFoundError:
        fused_moe_impl = None

    try:
        fused_moe_package = importlib.import_module(
            "vllm.model_executor.layers.fused_moe"
        )
    except ModuleNotFoundError:
        fused_moe_package = None

    if fused_moe_impl is not None and hasattr(
        fused_moe_impl,
        "_prepare_expert_assignment",
    ):
        if hasattr(fused_moe_impl, "try_get_optimal_moe_config"):
            original_try_get_optimal_moe_config = (
                fused_moe_impl.try_get_optimal_moe_config
            )

            def try_get_optimal_moe_config_with_timing(*args: Any, **kwargs: Any) -> Any:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_try_get_optimal_moe_config(*args, **kwargs)
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    return original_try_get_optimal_moe_config(*args, **kwargs)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    recorder.write_active_moe_substage_timing(
                        substage="apply_config_lookup",
                        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                        status=status,
                    )

            fused_moe_impl.try_get_optimal_moe_config = (
                try_get_optimal_moe_config_with_timing
            )

        if hasattr(fused_moe_impl, "_resize_cache"):
            original_resize_cache = fused_moe_impl._resize_cache

            def resize_cache_with_timing(*args: Any, **kwargs: Any) -> Any:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_resize_cache(*args, **kwargs)
                call_index = int(context.get("moe_resize_cache_call_index") or 0)
                context["moe_resize_cache_call_index"] = call_index + 1
                substage = (
                    "apply_resize_cache_w1_output"
                    if call_index == 0
                    else "apply_resize_cache_activation"
                    if call_index == 1
                    else "apply_resize_cache_w2_output"
                    if call_index == 2
                    else "apply_resize_cache_other"
                )
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    return original_resize_cache(*args, **kwargs)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    recorder.write_active_moe_substage_timing(
                        substage=substage,
                        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                        status=status,
                    )

            fused_moe_impl._resize_cache = resize_cache_with_timing

        try:
            fused_moe_modular_kernel = importlib.import_module(
                "vllm.model_executor.layers.fused_moe.modular_kernel"
            )
        except ModuleNotFoundError:
            fused_moe_modular_kernel = None

        if fused_moe_modular_kernel is not None and hasattr(
            fused_moe_modular_kernel,
            "FusedMoEExpertsModular",
        ):
            original_moe_problem_size = (
                fused_moe_modular_kernel.FusedMoEExpertsModular.moe_problem_size
            )

            def moe_problem_size_with_timing(
                self,
                a1: torch.Tensor,
                w1: torch.Tensor,
                w2: torch.Tensor,
                topk_ids: torch.Tensor,
            ) -> tuple[int, int, int, int, int]:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_moe_problem_size(self, a1, w1, w2, topk_ids)
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    return original_moe_problem_size(self, a1, w1, w2, topk_ids)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    recorder.write_active_moe_substage_timing(
                        substage="apply_problem_size",
                        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                        status=status,
                    )

            fused_moe_modular_kernel.FusedMoEExpertsModular.moe_problem_size = (
                moe_problem_size_with_timing
            )

        if hasattr(fused_moe_impl, "fused_experts_impl"):
            original_fused_experts = getattr(fused_moe_impl, "fused_experts", None)
            original_fused_experts_impl = fused_moe_impl.fused_experts_impl
            fused_experts_impl_expected_params = (
                "hidden_states",
                "w1",
                "w2",
                "topk_weights",
                "topk_ids",
                "inplace",
                "activation",
                "apply_router_weight_on_input",
                "use_fp8_w8a8",
                "use_int8_w8a8",
                "use_int8_w8a16",
                "use_int4_w4a16",
                "ocp_mx_scheme",
                "per_channel_quant",
                "global_num_experts",
                "expert_map",
                "w1_scale",
                "w2_scale",
                "w1_zp",
                "w2_zp",
                "a1_scale",
                "a2_scale",
                "block_shape",
                "w1_bias",
                "w2_bias",
            )
            try:
                fused_experts_impl_signature = inspect.signature(
                    original_fused_experts_impl
                )
                fused_experts_impl_param_names = tuple(
                    fused_experts_impl_signature.parameters
                )
                fused_experts_impl_source_timing_supported = (
                    fused_experts_impl_param_names
                    == fused_experts_impl_expected_params
                )
            except (TypeError, ValueError):
                fused_experts_impl_source_timing_supported = False

            def fused_experts_impl_with_source_timing(
                hidden_states: torch.Tensor,
                w1: torch.Tensor,
                w2: torch.Tensor,
                topk_weights: torch.Tensor,
                topk_ids: torch.Tensor,
                inplace: bool,
                activation: str = "silu",
                apply_router_weight_on_input: bool = False,
                use_fp8_w8a8: bool = False,
                use_int8_w8a8: bool = False,
                use_int8_w8a16: bool = False,
                use_int4_w4a16: bool = False,
                ocp_mx_scheme: str | None = None,
                per_channel_quant: bool = False,
                global_num_experts: int = -1,
                expert_map: torch.Tensor | None = None,
                w1_scale: torch.Tensor | None = None,
                w2_scale: torch.Tensor | None = None,
                w1_zp: torch.Tensor | None = None,
                w2_zp: torch.Tensor | None = None,
                a1_scale: torch.Tensor | None = None,
                a2_scale: torch.Tensor | None = None,
                block_shape: list[int] | None = None,
                w1_bias: torch.Tensor | None = None,
                w2_bias: torch.Tensor | None = None,
            ) -> torch.Tensor:
                function_entry_ns = time.perf_counter_ns()
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                source_level = _moe_source_timing_level(recorder)
                if recorder is None or source_level <= 0:
                    return original_fused_experts_impl(
                        hidden_states=hidden_states,
                        w1=w1,
                        w2=w2,
                        topk_weights=topk_weights,
                        topk_ids=topk_ids,
                        inplace=inplace,
                        activation=activation,
                        apply_router_weight_on_input=apply_router_weight_on_input,
                        use_fp8_w8a8=use_fp8_w8a8,
                        use_int8_w8a8=use_int8_w8a8,
                        use_int8_w8a16=use_int8_w8a16,
                        use_int4_w4a16=use_int4_w4a16,
                        ocp_mx_scheme=ocp_mx_scheme,
                        per_channel_quant=per_channel_quant,
                        global_num_experts=global_num_experts,
                        expert_map=expert_map,
                        w1_scale=w1_scale,
                        w2_scale=w2_scale,
                        w1_zp=w1_zp,
                        w2_zp=w2_zp,
                        a1_scale=a1_scale,
                        a2_scale=a2_scale,
                        block_shape=block_shape,
                        w1_bias=w1_bias,
                        w2_bias=w2_bias,
                    )
                if source_level < 2:
                    return original_fused_experts_impl(
                        hidden_states=hidden_states,
                        w1=w1,
                        w2=w2,
                        topk_weights=topk_weights,
                        topk_ids=topk_ids,
                        inplace=inplace,
                        activation=activation,
                        apply_router_weight_on_input=apply_router_weight_on_input,
                        use_fp8_w8a8=use_fp8_w8a8,
                        use_int8_w8a8=use_int8_w8a8,
                        use_int8_w8a16=use_int8_w8a16,
                        use_int4_w4a16=use_int4_w4a16,
                        ocp_mx_scheme=ocp_mx_scheme,
                        per_channel_quant=per_channel_quant,
                        global_num_experts=global_num_experts,
                        expert_map=expert_map,
                        w1_scale=w1_scale,
                        w2_scale=w2_scale,
                        w1_zp=w1_zp,
                        w2_zp=w2_zp,
                        a1_scale=a1_scale,
                        a2_scale=a2_scale,
                        block_shape=block_shape,
                        w1_bias=w1_bias,
                        w2_bias=w2_bias,
                    )
                if source_level == 2:
                    recorder.write_active_moe_substage_timing(
                        substage="apply_source_impl_entry_overhead",
                        elapsed_us=(time.perf_counter_ns() - function_entry_ns)
                        / 1000.0,
                        status=f"source_level:{source_level}",
                    )
                    impl_start_ns = time.perf_counter_ns()
                    impl_status = "ok"
                    try:
                        return original_fused_experts_impl(
                            hidden_states=hidden_states,
                            w1=w1,
                            w2=w2,
                            topk_weights=topk_weights,
                            topk_ids=topk_ids,
                            inplace=inplace,
                            activation=activation,
                            apply_router_weight_on_input=apply_router_weight_on_input,
                            use_fp8_w8a8=use_fp8_w8a8,
                            use_int8_w8a8=use_int8_w8a8,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            ocp_mx_scheme=ocp_mx_scheme,
                            per_channel_quant=per_channel_quant,
                            global_num_experts=global_num_experts,
                            expert_map=expert_map,
                            w1_scale=w1_scale,
                            w2_scale=w2_scale,
                            w1_zp=w1_zp,
                            w2_zp=w2_zp,
                            a1_scale=a1_scale,
                            a2_scale=a2_scale,
                            block_shape=block_shape,
                            w1_bias=w1_bias,
                            w2_bias=w2_bias,
                        )
                    except Exception as exc:
                        impl_status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit_start_ns = time.perf_counter_ns()
                        recorder.write_active_moe_substage_timing(
                            substage="apply_source_impl_total",
                            elapsed_us=(time.perf_counter_ns() - impl_start_ns)
                            / 1000.0,
                            status=impl_status,
                        )
                        recorder.write_active_moe_substage_timing(
                            substage="apply_source_emit_overhead",
                            elapsed_us=(time.perf_counter_ns() - emit_start_ns)
                            / 1000.0,
                            status="count:1",
                        )

                recorder.write_active_moe_substage_timing(
                    substage="apply_source_impl_entry_overhead",
                    elapsed_us=(time.perf_counter_ns() - function_entry_ns) / 1000.0,
                    status=f"source_level:{source_level}",
                )
                source_emit_overhead_us = 0.0
                source_emit_count = 0

                def emit(
                    substage: str,
                    start_ns: int,
                    status: str = "ok",
                    *,
                    required_level: int = 4,
                ) -> None:
                    nonlocal source_emit_overhead_us, source_emit_count
                    if source_level < int(required_level):
                        return
                    elapsed_us = (time.perf_counter_ns() - start_ns) / 1000.0
                    emit_start_ns = time.perf_counter_ns()
                    recorder.write_active_moe_substage_timing(
                        substage=substage,
                        elapsed_us=elapsed_us,
                        status=status,
                    )
                    source_emit_overhead_us += (
                        time.perf_counter_ns() - emit_start_ns
                    ) / 1000.0
                    source_emit_count += 1

                impl_start_ns = time.perf_counter_ns()
                impl_status = "ok"
                try:
                    if ocp_mx_scheme is not None:
                        raise NotImplementedError(
                            f"Using ocp_mx_scheme={ocp_mx_scheme} in functional "
                            "fused_experts call is deprecated. Please use "
                            "OCP_MXQuantizationEmulationTritonExperts."
                        )

                    pre_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        activation_enum = fused_moe_impl.MoEActivation.from_str(
                            activation
                        )
                        if use_int4_w4a16:
                            assert hidden_states.size(1) // 2 == w1.size(2), (
                                "Hidden size mismatch"
                            )
                        else:
                            assert hidden_states.size(1) == w1.size(2), (
                                f"Hidden size mismatch {hidden_states.size(1)} != "
                                f"{w1.size(2)}"
                            )
                        assert topk_weights.size() == topk_ids.size(), (
                            "topk shape mismatch"
                        )
                        assert hidden_states.is_contiguous(), (
                            "Hidden_states must be contiguous"
                        )
                        assert w1.stride(-1) == 1, (
                            "Stride of last dimension must be 1"
                        )
                        assert w2.stride(-1) == 1, (
                            "Stride of last dimension must be 1"
                        )
                        assert hidden_states.dtype in [
                            torch.float32,
                            torch.float16,
                            torch.bfloat16,
                        ]

                        num_tokens = hidden_states.size(0)
                        e_count, n_dim, _ = w1.size()
                        k_dim = w2.size(1)
                        if global_num_experts == -1:
                            global_num_experts = e_count
                        top_k_num = topk_ids.size(1)
                        m_dim = num_tokens

                        config_dtype = fused_moe_impl._get_config_dtype_str(
                            use_fp8_w8a8=use_fp8_w8a8,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            dtype=hidden_states.dtype,
                        )
                        quant_dtype = fused_moe_impl._get_config_quant_dtype(
                            use_fp8_w8a8=use_fp8_w8a8,
                            use_int8_w8a8=use_int8_w8a8,
                            ocp_mx_scheme=None,
                        )
                        config = fused_moe_impl.try_get_optimal_moe_config(
                            w1.size(),
                            w2.size(),
                            top_k_num,
                            config_dtype,
                            m_dim,
                            block_shape=block_shape,
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit("apply_source_pre_dispatch", pre_start_ns, status)

                    alloc_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        cache13 = torch.empty(
                            m_dim * top_k_num * max(n_dim, k_dim),
                            device=hidden_states.device,
                            dtype=hidden_states.dtype,
                        )
                        intermediate_cache1 = cache13[
                            : m_dim * top_k_num * n_dim
                        ].view(m_dim, top_k_num, n_dim)
                        intermediate_cache3 = cache13[
                            : m_dim * top_k_num * k_dim
                        ].view(m_dim, top_k_num, k_dim)
                        activation_out_dim = (
                            fused_moe_impl.mk.FusedMoEExpertsModular
                            .adjust_N_for_activation(n_dim, activation_enum)
                        )
                        intermediate_cache2 = torch.empty(
                            (m_dim * top_k_num, activation_out_dim),
                            device=hidden_states.device,
                            dtype=hidden_states.dtype,
                        )
                        if hidden_states.dtype == torch.bfloat16:
                            compute_type = fused_moe_impl.tl.bfloat16
                        elif hidden_states.dtype == torch.float16:
                            compute_type = fused_moe_impl.tl.float16
                        elif hidden_states.dtype == torch.float32:
                            compute_type = fused_moe_impl.tl.float32
                        else:
                            raise ValueError(
                                f"Unsupported compute_type: {hidden_states.dtype}"
                            )
                        out_hidden_states = (
                            hidden_states
                            if inplace
                            else torch.empty_like(hidden_states)
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit("apply_source_workspace_alloc", alloc_start_ns, status)

                    quant_hidden_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        qhidden_states, a1q_scale = (
                            fused_moe_impl.moe_kernel_quantize_input(
                                A=hidden_states,
                                A_scale=a1_scale,
                                quant_dtype=quant_dtype,
                                per_act_token_quant=per_channel_quant,
                                block_shape=block_shape,
                            )
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit(
                            "apply_source_quantize_hidden",
                            quant_hidden_start_ns,
                            status,
                        )

                    prepare_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        sorted_token_ids, expert_ids, num_tokens_post_padded = (
                            fused_moe_impl._prepare_expert_assignment(
                                topk_ids,
                                config,
                                num_tokens,
                                top_k_num,
                                global_num_experts,
                                expert_map,
                                use_int8_w8a16=use_int8_w8a16,
                                use_int4_w4a16=use_int4_w4a16,
                                block_shape=block_shape,
                                ignore_invalid_experts=True,
                            )
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit(
                            "apply_source_prepare_assignment",
                            prepare_start_ns,
                            status,
                        )

                    w1_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        fused_moe_impl.dispatch_fused_moe_kernel(
                            qhidden_states,
                            w1,
                            intermediate_cache1,
                            a1q_scale,
                            w1_scale,
                            w1_zp,
                            topk_weights,
                            sorted_token_ids,
                            expert_ids,
                            num_tokens_post_padded,
                            apply_router_weight_on_input,
                            top_k_num,
                            config,
                            compute_type=compute_type,
                            use_fp8_w8a8=use_fp8_w8a8,
                            use_int8_w8a8=use_int8_w8a8,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            per_channel_quant=per_channel_quant,
                            block_shape=block_shape,
                            B_bias=w1_bias,
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit(
                            "apply_source_w1_enqueue",
                            w1_start_ns,
                            status,
                            required_level=3,
                        )

                    w1_post_start_ns = time.perf_counter_ns()
                    emit("apply_source_w1_post", w1_post_start_ns)

                    activation_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        fused_moe_impl.apply_moe_activation(
                            activation_enum,
                            intermediate_cache2,
                            intermediate_cache1.view(-1, n_dim),
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit("apply_source_activation", activation_start_ns, status)

                    quant_intermediate_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        qintermediate_cache2, a2q_scale = (
                            fused_moe_impl.moe_kernel_quantize_input(
                                A=intermediate_cache2,
                                A_scale=a2_scale,
                                quant_dtype=quant_dtype,
                                per_act_token_quant=per_channel_quant,
                                block_shape=block_shape,
                            )
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit(
                            "apply_source_quantize_intermediate",
                            quant_intermediate_start_ns,
                            status,
                        )

                    w2_pre_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        if expert_map is not None:
                            intermediate_cache3.zero_()
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit("apply_source_w2_pre", w2_pre_start_ns, status)

                    w2_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        fused_moe_impl.dispatch_fused_moe_kernel(
                            qintermediate_cache2,
                            w2,
                            intermediate_cache3,
                            a2q_scale,
                            w2_scale,
                            w2_zp,
                            topk_weights,
                            sorted_token_ids,
                            expert_ids,
                            num_tokens_post_padded,
                            not apply_router_weight_on_input,
                            1,
                            config,
                            compute_type=compute_type,
                            use_fp8_w8a8=use_fp8_w8a8,
                            use_int8_w8a8=use_int8_w8a8,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            per_channel_quant=per_channel_quant,
                            block_shape=block_shape,
                            B_bias=w2_bias,
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit(
                            "apply_source_w2_enqueue",
                            w2_start_ns,
                            status,
                            required_level=3,
                        )

                    w2_post_start_ns = time.perf_counter_ns()
                    emit("apply_source_w2_post", w2_post_start_ns)

                    combine_start_ns = time.perf_counter_ns()
                    status = "ok"
                    try:
                        fused_moe_impl.ops.moe_sum(
                            intermediate_cache3.view(*intermediate_cache3.size()),
                            out_hidden_states,
                        )
                    except Exception as exc:
                        status = f"error:{type(exc).__name__}"
                        raise
                    finally:
                        emit(
                            "apply_source_combine_scatter",
                            combine_start_ns,
                            status,
                        )

                    post_start_ns = time.perf_counter_ns()
                    emit("apply_source_post_dispatch", post_start_ns)
                    return out_hidden_states
                except Exception as exc:
                    impl_status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    emit(
                        "apply_source_impl_total",
                        impl_start_ns,
                        impl_status,
                        required_level=2,
                    )
                    if source_level >= 2:
                        recorder.write_active_moe_substage_timing(
                            substage="apply_source_emit_overhead",
                            elapsed_us=float(source_emit_overhead_us),
                            status=f"count:{source_emit_count}",
                        )

            # This wrapper intentionally copies the current vLLM functional
            # fused_experts_impl body so source-level diagnostic regions can be
            # emitted without editing site-packages.  Keep it diagnostic-only:
            # if upstream vLLM changes the function signature, leave the
            # original implementation installed rather than risking a silent
            # semantic mismatch.
            if fused_experts_impl_source_timing_supported:
                fused_moe_impl.fused_experts_impl = (
                    fused_experts_impl_with_source_timing
                )

            if original_fused_experts is not None:
                fused_experts_expected_params = (
                    "hidden_states",
                    "w1",
                    "w2",
                    "topk_weights",
                    "topk_ids",
                    "inplace",
                    "activation",
                    "apply_router_weight_on_input",
                    "global_num_experts",
                    "expert_map",
                    "quant_config",
                )
                try:
                    fused_experts_signature = inspect.signature(
                        original_fused_experts
                    )
                    fused_experts_param_names = tuple(
                        fused_experts_signature.parameters
                    )
                    fused_experts_outer_source_timing_supported = (
                        fused_experts_param_names == fused_experts_expected_params
                    )
                except (TypeError, ValueError):
                    fused_experts_outer_source_timing_supported = False

                if getattr(
                    original_fused_experts,
                    _FUSED_EXPERTS_OUTER_TIMING_PATCH_ATTR,
                    False,
                ):
                    fused_experts_with_outer_timing = original_fused_experts
                elif fused_experts_outer_source_timing_supported:

                    def fused_experts_with_outer_timing(
                        hidden_states: torch.Tensor,
                        w1: torch.Tensor,
                        w2: torch.Tensor,
                        topk_weights: torch.Tensor,
                        topk_ids: torch.Tensor,
                        inplace: bool = False,
                        activation: Any = fused_moe_impl.MoEActivation.SILU,
                        apply_router_weight_on_input: bool = False,
                        global_num_experts: int = -1,
                        expert_map: torch.Tensor | None = None,
                        quant_config: Any = None,
                    ) -> Any:
                        context = get_active_moe_assignment_context()
                        recorder = (
                            context.get("recorder") if context is not None else None
                        )
                        source_level = _moe_source_timing_level(recorder)
                        if recorder is None or source_level <= 0:
                            return original_fused_experts(
                                hidden_states=hidden_states,
                                w1=w1,
                                w2=w2,
                                topk_weights=topk_weights,
                                topk_ids=topk_ids,
                                inplace=inplace,
                                activation=activation,
                                apply_router_weight_on_input=(
                                    apply_router_weight_on_input
                                ),
                                global_num_experts=global_num_experts,
                                expert_map=expert_map,
                                quant_config=quant_config,
                            )

                        def emit(
                            substage: str,
                            start_ns: int,
                            status: str = "ok",
                            *,
                            required_level: int = 1,
                        ) -> None:
                            if source_level < int(required_level):
                                return
                            recorder.write_active_moe_substage_timing(
                                substage=substage,
                                elapsed_us=(time.perf_counter_ns() - start_ns)
                                / 1000.0,
                                status=status,
                            )

                        outer_start_ns = time.perf_counter_ns()
                        outer_status = "ok"
                        try:
                            default_start_ns = time.perf_counter_ns()
                            status = "ok"
                            try:
                                if quant_config is None:
                                    quant_config = (
                                        fused_moe_impl
                                        .FUSED_MOE_UNQUANTIZED_CONFIG
                                    )
                            except Exception as exc:
                                status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                emit(
                                    "apply_source_outer_quant_config",
                                    default_start_ns,
                                    status,
                                )

                            assert_start_ns = time.perf_counter_ns()
                            status = "ok"
                            try:
                                assert not inplace or not fused_moe_impl.disable_inplace()
                            except Exception as exc:
                                status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                emit(
                                    "apply_source_outer_inplace_assert",
                                    assert_start_ns,
                                    status,
                                )

                            dispatch_select_start_ns = time.perf_counter_ns()
                            status = "ok"
                            try:
                                dispatch_func = (
                                    fused_moe_impl.dispatch_fused_experts_func(
                                        inplace
                                    )
                                )
                            except Exception as exc:
                                status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                emit(
                                    "apply_source_outer_dispatch_select",
                                    dispatch_select_start_ns,
                                    status,
                                )

                            impl_call_start_ns = time.perf_counter_ns()
                            status = "ok"
                            try:
                                return dispatch_func(
                                    hidden_states=hidden_states,
                                    w1=w1,
                                    w2=w2,
                                    topk_weights=topk_weights,
                                    topk_ids=topk_ids,
                                    activation=activation.value,
                                    apply_router_weight_on_input=(
                                        apply_router_weight_on_input
                                    ),
                                    use_fp8_w8a8=quant_config.use_fp8_w8a8,
                                    use_int8_w8a8=quant_config.use_int8_w8a8,
                                    use_int8_w8a16=quant_config.use_int8_w8a16,
                                    use_int4_w4a16=quant_config.use_int4_w4a16,
                                    ocp_mx_scheme=quant_config.ocp_mx_scheme,
                                    per_channel_quant=(
                                        quant_config.per_act_token_quant
                                    ),
                                    global_num_experts=global_num_experts,
                                    expert_map=expert_map,
                                    w1_scale=quant_config.w1_scale,
                                    w2_scale=quant_config.w2_scale,
                                    w1_zp=quant_config.w1_zp,
                                    w2_zp=quant_config.w2_zp,
                                    a1_scale=quant_config.a1_scale,
                                    a2_scale=quant_config.a2_scale,
                                    block_shape=quant_config.block_shape,
                                    w1_bias=quant_config.w1_bias,
                                    w2_bias=quant_config.w2_bias,
                                )
                            except Exception as exc:
                                status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                emit(
                                    "apply_source_outer_impl_call",
                                    impl_call_start_ns,
                                    status,
                                )
                        except Exception as exc:
                            outer_status = f"error:{type(exc).__name__}"
                            raise
                        finally:
                            emit(
                                "apply_source_fused_experts_outer",
                                outer_start_ns,
                                outer_status,
                            )
                else:

                    def fused_experts_with_outer_timing(
                        *args: Any,
                        **kwargs: Any,
                    ) -> Any:
                        context = get_active_moe_assignment_context()
                        recorder = (
                            context.get("recorder") if context is not None else None
                        )
                        source_level = _moe_source_timing_level(recorder)
                        if recorder is None or source_level <= 0:
                            return original_fused_experts(*args, **kwargs)
                        start_ns = time.perf_counter_ns()
                        status = "ok"
                        try:
                            return original_fused_experts(*args, **kwargs)
                        except Exception as exc:
                            status = f"error:{type(exc).__name__}"
                            raise
                        finally:
                            recorder.write_active_moe_substage_timing(
                                substage="apply_source_fused_experts_outer",
                                elapsed_us=(time.perf_counter_ns() - start_ns)
                                / 1000.0,
                                status=status,
                            )

                    setattr(
                        fused_experts_with_outer_timing,
                        _FUSED_EXPERTS_OUTER_TIMING_PATCH_ATTR,
                        True,
                    )

                fused_moe_impl.fused_experts = fused_experts_with_outer_timing
                if fused_moe_package is not None and hasattr(
                    fused_moe_package,
                    "fused_experts",
                ):
                    # AWQ WNA16 imports fused_experts from the package-level
                    # export inside apply(), so patch the export handle too.
                    fused_moe_package.fused_experts = (
                        fused_experts_with_outer_timing
                    )

        original_prepare_expert_assignment = fused_moe_impl._prepare_expert_assignment

        def prepare_expert_assignment_with_descriptor_order_handle(
            topk_ids: torch.Tensor,
            config: dict[str, Any],
            num_tokens: int,
            top_k_num: int,
            global_num_experts: int,
            expert_map: torch.Tensor | None,
            *,
            use_int8_w8a16: bool = False,
            use_int4_w4a16: bool = False,
            block_shape: list[int] | None = None,
            ignore_invalid_experts: bool = False,
        ) -> tuple[torch.Tensor | None, torch.Tensor, torch.Tensor]:
            context = get_active_moe_assignment_context()
            recorder = context.get("recorder") if context is not None else None
            layer_id = context.get("layer_id") if context is not None else None
            stage_start_ns = time.perf_counter_ns()
            stage_status = "ok"
            try:
                if recorder is not None and layer_id is not None:
                    fused_prepared = (
                        recorder.maybe_prepare_decode_expert_assignment_layer_prior(
                            layer_id=int(layer_id),
                            topk_ids=topk_ids,
                            config=config,
                            num_tokens=int(num_tokens),
                            top_k_num=int(top_k_num),
                            global_num_experts=int(global_num_experts),
                            expert_map=expert_map,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            block_shape=block_shape,
                            ignore_invalid_experts=ignore_invalid_experts,
                        )
                    )
                    if fused_prepared is not None:
                        stage_status = "fused_producer"
                        return fused_prepared

                sorted_token_ids, expert_ids, num_tokens_post_padded = (
                    original_prepare_expert_assignment(
                        topk_ids,
                        config,
                        num_tokens,
                        top_k_num,
                        global_num_experts,
                        expert_map,
                        use_int8_w8a16=use_int8_w8a16,
                        use_int4_w4a16=use_int4_w4a16,
                        block_shape=block_shape,
                        ignore_invalid_experts=ignore_invalid_experts,
                    )
                )
                if recorder is None or layer_id is None:
                    stage_status = "original"
                    return sorted_token_ids, expert_ids, num_tokens_post_padded
                stage_status = "original_with_reorder_hook"
                return recorder.maybe_reorder_prepared_expert_assignment(
                    layer_id=int(layer_id),
                    sorted_token_ids=sorted_token_ids,
                    expert_ids=expert_ids,
                    num_tokens_post_padded=num_tokens_post_padded,
                    block_size=int(config.get("BLOCK_SIZE_M", 1)),
                )
            except Exception as exc:
                stage_status = f"error:{type(exc).__name__}"
                raise
            finally:
                if recorder is not None and layer_id is not None:
                    recorder.write_moe_substage_timing(
                        layer_id=int(layer_id),
                        substage="prepare_expert_assignment",
                        elapsed_us=(time.perf_counter_ns() - stage_start_ns)
                        / 1000.0,
                        num_tokens=int(num_tokens),
                        phase=_phase_from_num_tokens(int(num_tokens)),
                        status=stage_status,
                    )

        fused_moe_impl._prepare_expert_assignment = (
            prepare_expert_assignment_with_descriptor_order_handle
        )

        if hasattr(fused_moe_impl, "moe_kernel_quantize_input"):
            original_moe_kernel_quantize_input = fused_moe_impl.moe_kernel_quantize_input

            def moe_kernel_quantize_input_with_timing(*args: Any, **kwargs: Any) -> Any:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_moe_kernel_quantize_input(*args, **kwargs)
                call_index = int(context.get("moe_quantize_input_call_index") or 0)
                context["moe_quantize_input_call_index"] = call_index + 1
                substage = (
                    "apply_quantize_hidden"
                    if call_index == 0
                    else "apply_quantize_intermediate"
                )
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    return original_moe_kernel_quantize_input(*args, **kwargs)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    recorder.write_active_moe_substage_timing(
                        substage=substage,
                        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                        status=status,
                    )

            fused_moe_impl.moe_kernel_quantize_input = (
                moe_kernel_quantize_input_with_timing
            )

        if hasattr(fused_moe_impl, "dispatch_fused_moe_kernel"):
            original_dispatch_fused_moe_kernel = fused_moe_impl.dispatch_fused_moe_kernel
            try:
                dispatch_fused_moe_kernel_signature = inspect.signature(
                    original_dispatch_fused_moe_kernel
                )
                dispatch_fused_moe_kernel_source_timing_supported = True
            except (TypeError, ValueError):
                dispatch_fused_moe_kernel_signature = None
                dispatch_fused_moe_kernel_source_timing_supported = False

            def dispatch_fused_moe_kernel_with_timing(*args: Any, **kwargs: Any) -> Any:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_dispatch_fused_moe_kernel(*args, **kwargs)
                top_k_value = kwargs.get("top_k")
                if top_k_value is None and len(args) > 11:
                    top_k_value = args[11]
                try:
                    top_k_int = int(top_k_value)
                except (TypeError, ValueError):
                    top_k_int = 0
                if top_k_int == 1:
                    substage = "apply_dispatch_w2_host"
                elif top_k_int > 1:
                    substage = "apply_dispatch_w1_host"
                else:
                    substage = "apply_dispatch_other_host"
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    source_level = _moe_source_timing_level(recorder)
                    if (
                        source_level >= 3
                        and dispatch_fused_moe_kernel_source_timing_supported
                        and dispatch_fused_moe_kernel_signature is not None
                    ):
                        try:
                            bound = dispatch_fused_moe_kernel_signature.bind(
                                *args,
                                **kwargs,
                            )
                            bound.apply_defaults()
                            params = bound.arguments
                        except TypeError:
                            params = {}
                        A = params.get("A")
                        B = params.get("B")
                        C = params.get("C")
                        A_scale = params.get("A_scale")
                        B_scale = params.get("B_scale")
                        B_zp = params.get("B_zp")
                        topk_weights = params.get("topk_weights")
                        sorted_token_ids = params.get("sorted_token_ids")
                        expert_ids = params.get("expert_ids")
                        num_tokens_post_padded = params.get("num_tokens_post_padded")
                        mul_routed_weight = params.get("mul_routed_weight")
                        top_k = params.get("top_k")
                        config = params.get("config")
                        compute_type = params.get("compute_type")
                        use_fp8_w8a8 = bool(params.get("use_fp8_w8a8"))
                        use_int8_w8a8 = bool(params.get("use_int8_w8a8"))
                        use_int8_w8a16 = bool(params.get("use_int8_w8a16"))
                        use_int4_w4a16 = bool(params.get("use_int4_w4a16"))
                        per_channel_quant = bool(params.get("per_channel_quant"))
                        block_shape = params.get("block_shape")
                        B_bias = params.get("B_bias")
                        is_wna16 = (
                            isinstance(A, torch.Tensor)
                            and isinstance(B, torch.Tensor)
                            and isinstance(C, torch.Tensor)
                            and isinstance(config, dict)
                            and (use_int8_w8a16 or use_int4_w4a16)
                            and block_shape is not None
                            and int(block_shape[1]) > 0
                        )
                        if is_wna16:
                            pre_invoke_start_ns = time.perf_counter_ns()
                            pre_status = "ok"
                            try:
                                assert topk_weights is not None or not mul_routed_weight
                                assert topk_weights is None or topk_weights.stride(1) == 1
                                assert (
                                    sorted_token_ids is None
                                    or sorted_token_ids.stride(0) == 1
                                )
                                assert B_bias is None
                                M = A.size(0)
                                num_tokens = M * int(top_k)
                            except Exception as exc:
                                pre_status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                recorder.write_active_moe_substage_timing(
                                    substage=f"{substage}_pre_invoke",
                                    elapsed_us=(
                                        time.perf_counter_ns() - pre_invoke_start_ns
                                    )
                                    / 1000.0,
                                    status=pre_status,
                                )

                            cuda_decision_start_ns = time.perf_counter_ns()
                            cuda_status = "ok"
                            try:
                                use_moe_wna16_cuda = (
                                    fused_moe_impl.should_moe_wna16_use_cuda(
                                        num_valid_tokens=num_tokens,
                                        group_size=block_shape[1],
                                        num_experts=B.size(0),
                                        bit=4 if use_int4_w4a16 else 8,
                                    )
                                )
                            except Exception as exc:
                                cuda_status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                recorder.write_active_moe_substage_timing(
                                    substage=f"{substage}_cuda_decision",
                                    elapsed_us=(
                                        time.perf_counter_ns() - cuda_decision_start_ns
                                    )
                                    / 1000.0,
                                    status=cuda_status,
                                )

                            invoke_start_ns = time.perf_counter_ns()
                            invoke_status = "cuda" if use_moe_wna16_cuda else "triton"
                            try:
                                if use_moe_wna16_cuda:
                                    fused_moe_impl.invoke_fused_moe_wna16_cuda_kernel(
                                        A,
                                        B,
                                        C,
                                        B_scale,
                                        B_zp,
                                        topk_weights,
                                        sorted_token_ids,
                                        expert_ids,
                                        num_tokens_post_padded,
                                        mul_routed_weight,
                                        top_k,
                                        config,
                                        block_shape,
                                    )
                                else:
                                    fused_moe_impl.invoke_fused_moe_wna16_triton_kernel(
                                        A,
                                        B,
                                        C,
                                        B_scale,
                                        B_zp,
                                        topk_weights,
                                        sorted_token_ids,
                                        expert_ids,
                                        num_tokens_post_padded,
                                        mul_routed_weight,
                                        top_k,
                                        config,
                                        compute_type,
                                        use_int8_w8a16,
                                        use_int4_w4a16,
                                        block_shape,
                                    )
                                return None
                            except Exception as exc:
                                invoke_status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                recorder.write_active_moe_substage_timing(
                                    substage=f"{substage}_invoke_call",
                                    elapsed_us=(
                                        time.perf_counter_ns() - invoke_start_ns
                                    )
                                    / 1000.0,
                                    status=invoke_status,
                                )
                    return original_dispatch_fused_moe_kernel(*args, **kwargs)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    recorder.write_active_moe_substage_timing(
                        substage=substage,
                        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                        status=status,
                    )

            fused_moe_impl.dispatch_fused_moe_kernel = (
                dispatch_fused_moe_kernel_with_timing
            )

        if hasattr(fused_moe_impl, "apply_moe_activation"):
            original_apply_moe_activation = fused_moe_impl.apply_moe_activation

            def apply_moe_activation_with_timing(*args: Any, **kwargs: Any) -> Any:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_apply_moe_activation(*args, **kwargs)
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    return original_apply_moe_activation(*args, **kwargs)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    recorder.write_active_moe_substage_timing(
                        substage="apply_activation",
                        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                        status=status,
                    )

            fused_moe_impl.apply_moe_activation = apply_moe_activation_with_timing

        fused_moe_ops = getattr(fused_moe_impl, "ops", None)
        if fused_moe_ops is not None and hasattr(fused_moe_ops, "moe_sum"):
            original_ops_moe_sum = fused_moe_ops.moe_sum

            def moe_sum_with_timing(*args: Any, **kwargs: Any) -> Any:
                context = get_active_moe_assignment_context()
                recorder = context.get("recorder") if context is not None else None
                if recorder is None:
                    return original_ops_moe_sum(*args, **kwargs)
                start_ns = time.perf_counter_ns()
                status = "ok"
                try:
                    return original_ops_moe_sum(*args, **kwargs)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    recorder.write_active_moe_substage_timing(
                        substage="apply_moe_sum",
                        elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                        status=status,
                    )

            fused_moe_ops.moe_sum = moe_sum_with_timing

    if fused_moe_impl is not None and hasattr(
        fused_moe_impl,
        "invoke_fused_moe_wna16_triton_kernel",
    ):
        original_invoke_wna16_triton_kernel = (
            fused_moe_impl.invoke_fused_moe_wna16_triton_kernel
        )

        def invoke_wna16_triton_kernel_with_descriptor_order_plan(
            A: torch.Tensor,
            B: torch.Tensor,
            C: torch.Tensor,
            B_scale: torch.Tensor | None,
            B_zp: torch.Tensor | None,
            topk_weights: torch.Tensor | None,
            sorted_token_ids: torch.Tensor,
            expert_ids: torch.Tensor,
            num_tokens_post_padded: torch.Tensor,
            mul_routed_weight: bool,
            top_k: int,
            config: dict[str, Any],
            compute_type: Any,
            use_int8_w8a16: bool,
            use_int4_w4a16: bool,
            block_shape: list[int] | None,
        ) -> None:
            context = get_active_moe_assignment_context()
            recorder_for_config = (
                context.get("recorder") if context is not None else None
            )
            layer_id_for_timing = (
                context.get("layer_id") if context is not None else None
            )
            num_tokens_for_timing = int(A.size(0)) if A.ndim >= 1 else 0
            invoke_entry_ns = time.perf_counter_ns()
            override_applied_for_timing = False
            if recorder_for_config is not None:
                original_config_for_timing = config
                config = recorder_for_config.apply_wna16_runtime_config_override(
                    config,
                    num_tokens=num_tokens_for_timing,
                    top_k=int(top_k),
                    use_int8_w8a16=bool(use_int8_w8a16),
                    use_int4_w4a16=bool(use_int4_w4a16),
                    block_shape=block_shape,
                )
                override_applied_for_timing = config is not original_config_for_timing
            plan = (
                context.get("descriptor_order_wna16_indirect_plan")
                if context is not None
                else None
            )
            def fallback_with_original_assignment(reason: str) -> None:
                assert isinstance(plan, dict)
                if context is not None:
                    recorder = context.get("recorder")
                    layer_id = context.get("layer_id")
                    if recorder is not None and layer_id is not None:
                        handle = recorder._last_descriptor_consumer_handle_by_layer.get(
                            int(layer_id),
                        )
                        if isinstance(handle, dict):
                            handle["applied"] = False
                            handle["fallback_reason"] = reason
                fallback_sorted, fallback_experts, fallback_num_post = (
                    original_prepare_expert_assignment(
                        plan["topk_ids"],
                        config,
                        int(plan.get("num_tokens") or plan["topk_ids"].shape[0]),
                        int(plan.get("top_k_num") or top_k),
                        int(plan.get("global_num_experts") or B.size(0)),
                        plan.get("expert_map"),
                        use_int8_w8a16=bool(
                            plan.get("use_int8_w8a16", use_int8_w8a16)
                        ),
                        use_int4_w4a16=bool(
                            plan.get("use_int4_w4a16", use_int4_w4a16)
                        ),
                        block_shape=plan.get("block_shape", block_shape),
                        ignore_invalid_experts=bool(
                            plan.get("ignore_invalid_experts")
                        ),
                    )
                )
                return original_invoke_wna16_triton_kernel(
                    A,
                    B,
                    C,
                    B_scale,
                    B_zp,
                    topk_weights,
                    fallback_sorted,
                    fallback_experts,
                    fallback_num_post,
                    mul_routed_weight,
                    top_k,
                    config,
                    compute_type,
                    use_int8_w8a16,
                    use_int4_w4a16,
                    block_shape,
                )

            def emit_wna16_launch_part(
                *,
                part: str,
                elapsed_us: float,
                status: str = "ok",
            ) -> None:
                if recorder_for_config is None:
                    return
                if int(top_k) == 1:
                    bucket = "w2"
                elif int(top_k) > 1:
                    bucket = "w1"
                else:
                    bucket = "other"
                recorder_for_config.write_moe_substage_timing(
                    layer_id=(
                        int(layer_id_for_timing)
                        if layer_id_for_timing is not None
                        else None
                    ),
                    substage=f"apply_wna16_{bucket}_{part}",
                    elapsed_us=float(elapsed_us),
                    num_tokens=num_tokens_for_timing,
                    phase=_wna16_phase_from_num_tokens_topk(
                        num_tokens_for_timing,
                        int(top_k),
                    ),
                    status=status,
                )

            if (
                isinstance(plan, dict)
                and sorted_token_ids is not None
                and str(plan.get("variant") or "").strip().lower()
                in {
                    "source_block_ids",
                    "group_plan",
                    "direct_topk_layer_prior",
                    "direct_topk_identity",
                }
            ):
                try:
                    variant = str(plan.get("variant") or "").strip().lower()
                    is_packed_source_block = bool(
                        plan.get("source_block_ids_packed")
                    )
                    if variant == "direct_topk_identity":
                        from mtp_expert_prefetch.tracing.vllm_wna16_group_plan import (
                            invoke_fused_moe_wna16_triton_kernel_direct_topk_identity,
                        )

                        invoke_fused_moe_wna16_triton_kernel_direct_topk_identity(
                            fused_moe_impl=fused_moe_impl,
                            topk_ids=plan.get("topk_ids"),
                            expert_map=plan.get("expert_map"),
                            expert_count=int(plan.get("global_num_experts") or B.size(0)),
                            ignore_invalid_experts=bool(
                                plan.get("ignore_invalid_experts")
                            ),
                            A=A,
                            B=B,
                            C=C,
                            B_scale=B_scale,
                            B_zp=B_zp,
                            topk_weights=topk_weights,
                            mul_routed_weight=mul_routed_weight,
                            top_k=top_k,
                            config=config,
                            compute_type=compute_type,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            block_shape=block_shape,
                        )
                    elif variant == "direct_topk_layer_prior":
                        from mtp_expert_prefetch.tracing.vllm_wna16_group_plan import (
                            invoke_fused_moe_wna16_triton_kernel_direct_topk_layer_prior,
                        )

                        invoke_fused_moe_wna16_triton_kernel_direct_topk_layer_prior(
                            fused_moe_impl=fused_moe_impl,
                            topk_ids=plan.get("topk_ids"),
                            expert_map=plan.get("expert_map"),
                            prior_rank=plan.get("prior_rank"),
                            ignore_invalid_experts=bool(
                                plan.get("ignore_invalid_experts")
                            ),
                            A=A,
                            B=B,
                            C=C,
                            B_scale=B_scale,
                            B_zp=B_zp,
                            topk_weights=topk_weights,
                            mul_routed_weight=mul_routed_weight,
                            top_k=top_k,
                            config=config,
                            compute_type=compute_type,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            block_shape=block_shape,
                        )
                    elif variant == "source_block_ids" and not is_packed_source_block:
                        from mtp_expert_prefetch.tracing.vllm_wna16_group_plan import (
                            invoke_fused_moe_wna16_triton_kernel_source_block_ids,
                        )

                        invoke_fused_moe_wna16_triton_kernel_source_block_ids(
                            fused_moe_impl=fused_moe_impl,
                            source_block_ids=plan.get("source_block_ids"),
                            A=A,
                            B=B,
                            C=C,
                            B_scale=B_scale,
                            B_zp=B_zp,
                            topk_weights=topk_weights,
                            sorted_token_ids=sorted_token_ids,
                            expert_ids=expert_ids,
                            num_tokens_post_padded=num_tokens_post_padded,
                            mul_routed_weight=mul_routed_weight,
                            top_k=top_k,
                            config=config,
                            compute_type=compute_type,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            block_shape=block_shape,
                        )
                    elif variant == "group_plan":
                        max_group_blocks_value = plan.get("max_group_blocks")
                        if max_group_blocks_value is None:
                            raise ValueError("group_plan direct requires max_group_blocks")
                        from mtp_expert_prefetch.tracing.vllm_wna16_group_plan import (
                            invoke_fused_moe_wna16_triton_kernel_group_plan_direct,
                        )

                        invoke_fused_moe_wna16_triton_kernel_group_plan_direct(
                            fused_moe_impl=fused_moe_impl,
                            group_order=plan.get("group_order"),
                            group_offsets=plan.get("group_offsets"),
                            group_source_starts=plan.get("group_source_starts"),
                            max_group_blocks=int(max_group_blocks_value),
                            A=A,
                            B=B,
                            C=C,
                            B_scale=B_scale,
                            B_zp=B_zp,
                            topk_weights=topk_weights,
                            sorted_token_ids=sorted_token_ids,
                            num_tokens_post_padded=num_tokens_post_padded,
                            mul_routed_weight=mul_routed_weight,
                            top_k=top_k,
                            config=config,
                            compute_type=compute_type,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            block_shape=block_shape,
                        )
                    else:
                        from mtp_expert_prefetch.tracing.vllm_wna16_group_plan import (
                            invoke_fused_moe_wna16_triton_kernel_indirect,
                        )

                        invoke_fused_moe_wna16_triton_kernel_indirect(
                            fused_moe_impl=fused_moe_impl,
                            indirect_mode=str(plan.get("variant")),
                            source_block_ids=(
                                plan.get("packed_source_block_ids")
                                if plan.get("packed_source_block_ids") is not None
                                else plan.get("source_block_ids")
                            ),
                            group_order=plan.get("group_order"),
                            group_offsets=plan.get("group_offsets"),
                            group_source_starts=plan.get("group_source_starts"),
                            max_groups=int(plan.get("max_groups") or 1),
                            source_block_ids_packed=is_packed_source_block,
                            A=A,
                            B=B,
                            C=C,
                            B_scale=B_scale,
                            B_zp=B_zp,
                            topk_weights=topk_weights,
                            sorted_token_ids=sorted_token_ids,
                            expert_ids=expert_ids,
                            num_tokens_post_padded=num_tokens_post_padded,
                            mul_routed_weight=mul_routed_weight,
                            top_k=top_k,
                            config=config,
                            compute_type=compute_type,
                            use_int8_w8a16=use_int8_w8a16,
                            use_int4_w4a16=use_int4_w4a16,
                            block_shape=block_shape,
                        )
                    plan["launch_used_count"] = int(plan.get("launch_used_count") or 0) + 1
                    return
                except Exception as exc:  # pragma: no cover - runtime fallback path
                    error = f"{type(exc).__name__}: {exc}"
                    plan["launch_error"] = error
                    recorder = context.get("recorder") if context is not None else None
                    layer_id = context.get("layer_id") if context is not None else None
                    if recorder is not None and layer_id is not None:
                        handle = recorder._last_descriptor_consumer_handle_by_layer.get(
                            int(layer_id),
                        )
                        if isinstance(handle, dict):
                            handle["applied"] = False
                            handle["fallback_reason"] = (
                                f"kernel_variant_launch_error:{error}"
                            )
                    if str(plan.get("variant") or "").strip().lower() in {
                        "direct_topk_layer_prior",
                        "direct_topk_identity",
                    }:
                        return fallback_with_original_assignment(
                            f"direct_topk_launch_error:{error}"
                        )
            launch_start_ns = time.perf_counter_ns()
            emit_wna16_launch_part(
                part="invoke_setup_host",
                elapsed_us=(launch_start_ns - invoke_entry_ns) / 1000.0,
            )
            gpu_start = None
            gpu_end = None
            if (
                recorder_for_config is not None
                and str(recorder_for_config.shadow_wna16_kernel_timing_mode)
                .strip()
                .lower()
                in {"gpu_event", "event", "cuda_event", "hip_event"}
            ):
                gpu_start = torch.cuda.Event(enable_timing=True)
                gpu_end = torch.cuda.Event(enable_timing=True)
                gpu_start.record()
            launch_status = "ok"
            enqueue_elapsed_us = None
            try:
                enqueue_start_ns = time.perf_counter_ns()
                return original_invoke_wna16_triton_kernel(
                    A,
                    B,
                    C,
                    B_scale,
                    B_zp,
                    topk_weights,
                    sorted_token_ids,
                    expert_ids,
                    num_tokens_post_padded,
                    mul_routed_weight,
                    top_k,
                    config,
                    compute_type,
                    use_int8_w8a16,
                    use_int4_w4a16,
                    block_shape,
                )
                enqueue_elapsed_us = (time.perf_counter_ns() - enqueue_start_ns) / 1000.0
            except Exception as exc:
                launch_status = f"error:{type(exc).__name__}"
                raise
            finally:
                if enqueue_elapsed_us is None:
                    enqueue_elapsed_us = (
                        time.perf_counter_ns() - enqueue_start_ns
                        if "enqueue_start_ns" in locals()
                        else 0
                    ) / 1000.0
                emit_wna16_launch_part(
                    part="enqueue_host",
                    elapsed_us=enqueue_elapsed_us,
                    status=launch_status,
                )
                if recorder_for_config is not None:
                    gpu_elapsed_us = None
                    sync_wait_us = None
                    if gpu_start is not None and gpu_end is not None:
                        gpu_end.record()
                        sync_wait_start_ns = time.perf_counter_ns()
                        gpu_end.synchronize()
                        sync_wait_us = (
                            time.perf_counter_ns() - sync_wait_start_ns
                        ) / 1000.0
                        gpu_elapsed_us = float(gpu_start.elapsed_time(gpu_end)) * 1000.0
                        emit_wna16_launch_part(
                            part="event_sync_wait",
                            elapsed_us=sync_wait_us,
                            status=launch_status,
                        )
                    recorder_for_config.write_wna16_kernel_timing(
                        layer_id=(
                            int(layer_id_for_timing)
                            if layer_id_for_timing is not None
                            else None
                        ),
                        elapsed_us=(time.perf_counter_ns() - launch_start_ns) / 1000.0,
                        gpu_elapsed_us=gpu_elapsed_us,
                        num_tokens=num_tokens_for_timing,
                        top_k=int(top_k),
                        config=config,
                        override_applied=bool(override_applied_for_timing),
                        variant="original",
                        status=launch_status,
                        use_int8_w8a16=bool(use_int8_w8a16),
                        use_int4_w4a16=bool(use_int4_w4a16),
                        block_shape=block_shape,
                    )

        fused_moe_impl.invoke_fused_moe_wna16_triton_kernel = (
            invoke_wna16_triton_kernel_with_descriptor_order_plan
        )

    if base_router is not None:
        original_router_set_capture_fn = base_router.BaseRouter.set_capture_fn
        original_router_select_experts = base_router.BaseRouter.select_experts

        def router_set_capture_fn_with_trace_layer(self, capture_fn: Any) -> None:
            original_router_set_capture_fn(self, capture_fn)
            layer_id = None
            defaults = getattr(capture_fn, "__defaults__", None)
            if defaults:
                try:
                    layer_id = int(defaults[0])
                except (TypeError, ValueError):
                    layer_id = None
            self._mtp_trace_layer_id = layer_id

        def router_select_experts_with_trace(
            self,
            hidden_states: torch.Tensor,
            router_logits: torch.Tensor,
            *extra_args: Any,
            **extra_kwargs: Any,
        ) -> tuple[torch.Tensor, torch.Tensor]:
            recorder = get_active_vllm_router_recorder()
            if recorder is None and not extra_args and not extra_kwargs:
                return original_router_select_experts(
                    self,
                    hidden_states,
                    router_logits,
                )
            remaining_extra_args, passthrough_kwargs = _split_optional_input_ids(
                extra_args,
                extra_kwargs,
            )
            layer_id = getattr(self, "_mtp_trace_layer_id", None)
            if (
                recorder is None
                or layer_id is None
                or not recorder.shadow_emit_decoder_layer_timing
            ):
                topk_weights, topk_ids = _call_with_supported_kwargs(
                    original_router_select_experts,
                    self,
                    hidden_states,
                    router_logits,
                    *remaining_extra_args,
                    **passthrough_kwargs,
                )
                if (
                    recorder is not None
                    and layer_id is not None
                    and recorder.shadow_record_router_topk
                ):
                    recorder.record_topk(
                        layer_id=layer_id,
                        topk_ids=topk_ids,
                        topk_weights=topk_weights,
                        oracle_router_logits=router_logits,
                        router_input_hidden=hidden_states,
                    )
                return topk_weights, topk_ids

            num_tokens = int(hidden_states.shape[0]) if hidden_states.ndim > 0 else None
            phase = _phase_from_num_tokens(num_tokens)

            def emit(substage: str, start_ns: int, status: str = "ok") -> None:
                recorder.write_moe_substage_timing(
                    layer_id=int(layer_id),
                    substage=substage,
                    elapsed_us=(time.perf_counter_ns() - start_ns) / 1000.0,
                    num_tokens=num_tokens,
                    phase=phase,
                    status=status,
                )

            status = "ok"
            validate_start_ns = time.perf_counter_ns()
            try:
                self._validate_eplb_state()
            except Exception as exc:
                status = f"error:{type(exc).__name__}"
                raise
            finally:
                emit("select_validate_eplb", validate_start_ns, status)

            status = "ok"
            indices_start_ns = time.perf_counter_ns()
            try:
                indices_type = self._get_indices_type()
            except Exception as exc:
                status = f"error:{type(exc).__name__}"
                raise
            finally:
                emit("select_indices_type", indices_start_ns, status)

            status = "ok"
            routing_start_ns = time.perf_counter_ns()
            try:
                topk_weights, topk_ids = _call_with_supported_kwargs(
                    self._compute_routing,
                    hidden_states,
                    router_logits,
                    indices_type,
                    **passthrough_kwargs,
                )
            except Exception as exc:
                status = f"error:{type(exc).__name__}"
                raise
            finally:
                routing_method = str(type(self).__name__)
                emit("select_compute_routing", routing_start_ns, f"{routing_method}:{status}")

            if self.capture_fn is not None:
                status = "ok"
                capture_start_ns = time.perf_counter_ns()
                try:
                    self.capture_fn(topk_ids)
                except Exception as exc:
                    status = f"error:{type(exc).__name__}"
                    raise
                finally:
                    emit("select_capture_logical_ids", capture_start_ns, status)

            status = "ok"
            eplb_start_ns = time.perf_counter_ns()
            try:
                topk_ids = self._apply_eplb_mapping(topk_ids)
            except Exception as exc:
                status = f"error:{type(exc).__name__}"
                raise
            finally:
                emit("select_eplb_mapping", eplb_start_ns, status)

            status = "ok"
            convert_start_ns = time.perf_counter_ns()
            try:
                topk_ids = self._convert_indices_dtype(topk_ids, indices_type)
            except Exception as exc:
                status = f"error:{type(exc).__name__}"
                raise
            finally:
                emit("select_dtype_convert", convert_start_ns, status)

            if (
                recorder is not None
                and layer_id is not None
                and recorder.shadow_record_router_topk
            ):
                record_start_ns = time.perf_counter_ns()
                record_status = "ok"
                recorder.record_topk(
                    layer_id=layer_id,
                    topk_ids=topk_ids,
                    topk_weights=topk_weights,
                    oracle_router_logits=router_logits,
                    router_input_hidden=hidden_states,
                )
                recorder.write_moe_substage_timing(
                    layer_id=int(layer_id),
                    substage="select_record_topk",
                    elapsed_us=(time.perf_counter_ns() - record_start_ns) / 1000.0,
                    num_tokens=num_tokens,
                    phase=phase,
                    status=record_status,
                )
            elif recorder is not None and layer_id is not None:
                recorder.write_moe_substage_timing(
                    layer_id=int(layer_id),
                    substage="select_record_topk",
                    elapsed_us=0.0,
                    num_tokens=num_tokens,
                    phase=phase,
                    status="skipped",
                )
            return topk_weights, topk_ids

        base_router.BaseRouter.set_capture_fn = router_set_capture_fn_with_trace_layer
        base_router.BaseRouter.select_experts = router_select_experts_with_trace

    try:
        gpu_model_runner_module = importlib.import_module(
            "vllm.v1.worker.gpu_model_runner"
        )
    except ModuleNotFoundError:
        gpu_model_runner_module = None
    try:
        v1_sampler_module = importlib.import_module("vllm.v1.sample.sampler")
    except ModuleNotFoundError:
        v1_sampler_module = None
    try:
        logits_processor_module = importlib.import_module(
            "vllm.model_executor.layers.logits_processor"
        )
    except ModuleNotFoundError:
        logits_processor_module = None

    def _wrap_engine_method(
        owner: Any,
        method_name: str,
        substage: str,
    ) -> None:
        original = getattr(owner, method_name, None)
        if original is None or getattr(original, "_mtp_engine_timing_wrapped", False):
            return

        @functools.wraps(original)
        def wrapped(self, *args: Any, **kwargs: Any) -> Any:
            recorder = get_active_vllm_router_recorder()
            if recorder is None or not recorder.shadow_emit_engine_timing:
                return original(self, *args, **kwargs)
            start_ns = time.perf_counter_ns()
            status = "ok"
            try:
                return original(self, *args, **kwargs)
            except Exception as exc:
                status = f"error:{type(exc).__name__}"
                raise
            finally:
                _emit_active_engine_substage_timing(
                    substage,
                    start_ns,
                    status=status,
                )

        wrapped._mtp_engine_timing_wrapped = True  # type: ignore[attr-defined]
        setattr(owner, method_name, wrapped)

    if gpu_model_runner_module is not None:
        gpu_runner = getattr(gpu_model_runner_module, "GPUModelRunner", None)
        if gpu_runner is not None:
            for method_name, substage in (
                ("execute_model", "engine_execute_model"),
                ("sample_tokens", "engine_sample_tokens"),
                ("_sample", "engine_sample"),
                ("_bookkeeping_sync", "engine_bookkeeping_sync"),
                ("_update_states", "engine_update_states"),
                (
                    "_determine_batch_execution_and_padding",
                    "engine_determine_batch",
                ),
                ("_get_slot_mappings", "engine_slot_mappings"),
                ("_build_attention_metadata", "engine_attention_metadata"),
                ("_prepare_inputs", "engine_prepare_inputs"),
                ("_preprocess", "engine_preprocess"),
                ("_model_forward", "engine_model_forward"),
                ("eplb_step", "engine_eplb_step"),
            ):
                _wrap_engine_method(gpu_runner, method_name, substage)

    if v1_sampler_module is not None:
        sampler = getattr(v1_sampler_module, "Sampler", None)
        if sampler is not None:
            _wrap_engine_method(sampler, "forward", "engine_sampler_forward")
            _wrap_engine_method(sampler, "sample", "engine_sampler_sample")

    if logits_processor_module is not None:
        logits_processor = getattr(logits_processor_module, "LogitsProcessor", None)
        if logits_processor is not None:
            _wrap_engine_method(
                logits_processor,
                "forward",
                "engine_logits_processor_forward",
            )
    _PATCHED = True


def write_vllm_trace_manifest(
    output_dir: str | Path,
    *,
    sample_path: Path,
    prompt: str,
    generated_text: str,
    num_router_calls: int,
) -> Path:
    output_dir = Path(output_dir)
    manifest_path = output_dir / "manifest.jsonl"
    record = {
        "sample_idx": 0,
        "path": sample_path.name,
        "prompt": prompt,
        "generated_text": generated_text,
        "num_router_calls": num_router_calls,
        "backend": "vllm",
    }
    manifest_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest_path


def vllm_routed_experts_to_router_topk(
    routed_experts: Any,
    *,
    module_prefix: str = "model.language_model",
) -> dict[str, list[Any]]:
    routed = torch.as_tensor(routed_experts, dtype=torch.int16).detach().cpu()
    if routed.ndim != 3:
        msg = (
            "Expected vLLM routed experts with shape [tokens, layers, top_k], "
            f"got {tuple(routed.shape)}"
        )
        raise ValueError(msg)

    num_layers = int(routed.shape[1])
    router_topk: dict[str, list[Any]] = {}
    for layer_id in range(num_layers):
        module_name = f"{module_prefix}.layers.{layer_id}.mlp.gate"
        router_topk[module_name] = [routed[:, layer_id, :].tolist()]
    return router_topk


def _uniform_router_weights_from_topk(router_topk: dict[str, list[Any]]) -> dict[str, list[Any]]:
    router_weights: dict[str, list[Any]] = {}
    for module_name, calls in router_topk.items():
        weighted_calls = []
        for call in calls:
            ids = torch.as_tensor(call)
            top_k = int(ids.shape[-1])
            weighted_calls.append(torch.full(ids.shape, 1.0 / top_k, dtype=torch.float32).tolist())
        router_weights[module_name] = weighted_calls
    return router_weights


def _payload_num_tokens(payload: dict[str, Any]) -> int:
    router_topk = payload.get("router_topk")
    if not isinstance(router_topk, dict) or not router_topk:
        return 0
    first_calls = next(iter(router_topk.values()))
    if not first_calls:
        return 0
    first = torch.as_tensor(first_calls[0])
    return int(first.shape[0]) if first.ndim >= 1 else 0


def _payload_num_router_modules(payload: dict[str, Any]) -> int:
    router_topk = payload.get("router_topk")
    return len(router_topk) if isinstance(router_topk, dict) else 0


def _payload_num_router_calls(payload: dict[str, Any]) -> int:
    meta = payload.get("router_call_meta")
    if isinstance(meta, list):
        return len(meta)
    router_topk = payload.get("router_topk")
    if not isinstance(router_topk, dict):
        return 0
    return sum(len(calls) for calls in router_topk.values())


def _routed_experts_payload(
    *,
    routed_experts: Any,
    module_prefix: str,
) -> dict[str, Any]:
    routed_tensor = torch.as_tensor(
        routed_experts,
        dtype=torch.int16,
    ).detach().cpu()
    router_topk = vllm_routed_experts_to_router_topk(
        routed_tensor,
        module_prefix=module_prefix,
    )
    return {
        "vllm_routed_experts": routed_tensor,
        "vllm_routed_experts_shape": list(routed_tensor.shape),
        "router_topk": router_topk,
        "router_weights": _uniform_router_weights_from_topk(router_topk),
        "router_call_meta": [
            {
                "source": "vllm_return_routed_experts",
                "layer_id": layer_id,
                "call_index": 0,
                "num_tokens": int(routed_tensor.shape[0]),
                "module_name": f"{module_prefix}.layers.{layer_id}.mlp.gate",
            }
            for layer_id in range(int(routed_tensor.shape[1]))
        ],
    }


def _set_text_only_vllm_env() -> None:
    project_src = Path(__file__).resolve().parents[2]
    os.environ["MTP_PREFETCH_DISABLE_FLASH_ATTN_PROBE"] = "1"
    current_pythonpath = os.environ.get("PYTHONPATH")
    if current_pythonpath:
        paths = current_pythonpath.split(":")
        if str(project_src) not in paths:
            os.environ["PYTHONPATH"] = f"{project_src}:{current_pythonpath}"
    else:
        os.environ["PYTHONPATH"] = str(project_src)
    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))
    for module_name in (
        "flash_attn",
        "flash_attn.ops",
        "flash_attn.ops.triton",
        "flash_attn.ops.triton.rotary",
    ):
        sys.modules[module_name] = None

    original_find_spec = importlib.util.find_spec

    def find_spec_without_flash_attn(name: str, package: str | None = None):
        if name == "flash_attn" or name.startswith("flash_attn."):
            return None
        return original_find_spec(name, package)

    importlib.util.find_spec = find_spec_without_flash_attn


def _extract_text(record: dict[str, Any]) -> str:
    text = record.get("text")
    if isinstance(text, str) and text:
        return text
    for key in ("prompt", "inputs", "targets"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    msg = f"Trace record has no usable text field: {sorted(record)}"
    raise KeyError(msg)


def _to_token_prompt(input_ids: list[int], *, prompt: str) -> dict[str, Any]:
    return {"prompt_token_ids": input_ids, "prompt": prompt}


def _load_token_source_input_ids(
    manifest_path: str | Path | None,
    *,
    project_root: Path,
) -> dict[int, list[int]]:
    if manifest_path is None:
        return {}
    resolved = resolve_path(manifest_path, base_dir=project_root)
    source_ids: dict[int, list[int]] = {}
    with resolved.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            sample_path = resolved.parent / record["path"]
            try:
                payload = torch.load(sample_path, map_location="cpu", weights_only=False)
            except TypeError:
                payload = torch.load(sample_path, map_location="cpu")
            input_ids = torch.as_tensor(payload["input_ids"], dtype=torch.long)
            if input_ids.ndim == 2:
                input_ids = input_ids[0]
            elif input_ids.ndim != 1:
                msg = f"Unsupported token source input_ids shape: {tuple(input_ids.shape)}"
                raise ValueError(msg)
            source_ids[int(record["sample_idx"])] = [int(token) for token in input_ids.tolist()]
    return source_ids


def _write_vllm_sample_trace(
    *,
    manifest: Any,
    output_dir: Path,
    sample_idx: int,
    record: dict[str, Any],
    input_ids: list[int],
    request_output: Any,
    module_prefix: str,
    recorder: VllmRouterRecorder | None,
) -> None:
    if not request_output.outputs:
        msg = f"vLLM returned no output for sample {sample_idx}"
        raise RuntimeError(msg)

    completion = request_output.outputs[0]
    routed_experts = getattr(completion, "routed_experts", None)
    has_recorder_trace = recorder is not None and bool(recorder.calls)
    has_no_topk_recorder_trace = (
        recorder is not None
        and not recorder.shadow_record_router_topk
        and not has_recorder_trace
    )
    trace_source = (
        "vllm_router_logits_recorder"
        if has_recorder_trace
        else (
            "vllm_router_logits_recorder_no_topk"
            if has_no_topk_recorder_trace
            else "vllm_return_routed_experts"
        )
    )

    if has_recorder_trace or has_no_topk_recorder_trace:
        route_payload = recorder.to_payload(
            module_prefix=module_prefix,
            source=trace_source,
        )
        if routed_experts is not None:
            routed_tensor = torch.as_tensor(
                routed_experts,
                dtype=torch.int16,
            ).detach().cpu()
            route_payload["vllm_routed_experts"] = routed_tensor
            route_payload["vllm_routed_experts_shape"] = list(routed_tensor.shape)
    else:
        if routed_experts is None:
            msg = (
                "vLLM produced neither router logits recorder calls nor `routed_experts`. "
                "Enable `trace.use_router_logits_recorder: true` with a compatible patch, "
                "or `enable_return_routed_experts=True` in a compatible vLLM build."
            )
            raise RuntimeError(msg)
        route_payload = _routed_experts_payload(
            routed_experts=routed_experts,
            module_prefix=module_prefix,
        )

    sample_payload: dict[str, Any] = {
        "record": record,
        "backend": "vllm",
        "trace_source": trace_source,
        "input_ids": torch.tensor([input_ids], dtype=torch.int32),
        "generated_text": completion.text,
        **route_payload,
    }
    sample_file = output_dir / f"sample_{sample_idx:06d}.pt"
    torch.save(sample_payload, sample_file)
    manifest.write(
        json.dumps(
            {
                "sample_idx": sample_idx,
                "record_id": record.get("id"),
                "path": sample_file.name,
                "backend": "vllm",
                "trace_source": trace_source,
                "num_tokens": _payload_num_tokens(sample_payload),
                "num_input_tokens": len(input_ids),
                "num_router_modules": _payload_num_router_modules(sample_payload),
                "num_router_calls": _payload_num_router_calls(sample_payload),
                "has_vllm_routed_experts": "vllm_routed_experts" in sample_payload,
                "has_vllm_router_logits": has_recorder_trace,
                "has_native_mtp_router": False,
            },
            ensure_ascii=False,
        )
        + "\n"
    )
    manifest.flush()


def _runtime_shadow_options(
    trace_options: dict[str, Any],
    vllm_options: dict[str, Any],
) -> dict[str, Any]:
    raw = trace_options.get("runtime_shadow", vllm_options.get("runtime_shadow", {}))
    if raw is None:
        return {"enabled": False}
    if isinstance(raw, bool):
        return {"enabled": bool(raw)}
    if not isinstance(raw, dict):
        msg = "runtime_shadow must be a mapping or boolean."
        raise TypeError(msg)
    return {"enabled": False, **raw}


def _apply_premap_address_capacity_gate(
    options: dict[str, Any],
    *,
    project_root: Path,
) -> dict[str, Any]:
    raw_path = options.get("premap_address_capacity_gate_path")
    if raw_path is None:
        return options
    path = resolve_path(raw_path, base_dir=project_root)
    payload = load_yaml(path)
    if not isinstance(payload, dict):
        msg = f"Premap address capacity gate must be a mapping: {path}"
        raise TypeError(msg)
    gate = payload.get("capacity_gate")
    if not isinstance(gate, dict):
        msg = f"Premap address capacity gate missing `capacity_gate`: {path}"
        raise ValueError(msg)
    raw_capacity = gate.get("recommended_capacity_entries")
    if raw_capacity is None:
        msg = (
            "Premap address capacity gate missing "
            f"`capacity_gate.recommended_capacity_entries`: {path}"
        )
        raise ValueError(msg)
    recommended_capacity = int(raw_capacity)
    inline_capacity = _optional_capacity_option(options, "premap_address_manager_capacity")
    if inline_capacity is not None and int(inline_capacity) != recommended_capacity:
        msg = (
            "Inline premap_address_manager_capacity does not match gate "
            f"recommended capacity in {path}: {inline_capacity} != {recommended_capacity}"
        )
        raise ValueError(msg)
    updated = dict(options)
    updated["premap_address_manager_capacity"] = recommended_capacity
    updated["premap_address_capacity_gate_id"] = payload.get(
        "artifact_id",
        payload.get("id"),
    )
    updated["premap_address_capacity_gate_resolved_path"] = str(path)
    updated["premap_address_capacity_gate_recommended_capacity"] = recommended_capacity
    updated["premap_address_capacity_gate_evidence_paths"] = payload.get(
        "evidence_paths",
        {},
    )
    return updated


def _apply_premap_consumer_readonly_gate(
    options: dict[str, Any],
    *,
    project_root: Path,
) -> dict[str, Any]:
    require_gate = bool(options.get("premap_consumer_require_readonly_gate", False))
    descriptor_prep_mode = _normalize_premap_descriptor_prep_execution_mode(
        options.get("premap_descriptor_prep_execution_mode", "off")
    )
    if descriptor_prep_mode is not None and not require_gate:
        msg = (
            "premap_descriptor_prep_execution_mode requires "
            "premap_consumer_require_readonly_gate=True."
        )
        raise ValueError(msg)
    raw_path = options.get("premap_consumer_readonly_gate_path")
    if raw_path is None:
        if require_gate:
            msg = (
                "premap_consumer_require_readonly_gate=True requires "
                "premap_consumer_readonly_gate_path."
            )
            raise ValueError(msg)
        return options
    path = resolve_path(raw_path, base_dir=project_root)
    payload = load_yaml(path)
    if not isinstance(payload, dict):
        msg = f"Premap consumer readonly gate must be a mapping: {path}"
        raise TypeError(msg)
    gate = payload.get("gate")
    if not isinstance(gate, dict):
        msg = f"Premap consumer readonly gate missing `gate`: {path}"
        raise ValueError(msg)
    status = str(payload.get("status", "")).strip().lower()
    raw_passed = gate.get("passed")
    if raw_passed is None:
        gate_passed = status == "passed"
    elif isinstance(raw_passed, bool):
        gate_passed = raw_passed
    else:
        msg = f"Premap consumer readonly gate `gate.passed` must be boolean: {path}"
        raise TypeError(msg)
    if status and status != "passed":
        gate_passed = False
    failures = gate.get("failures", payload.get("failures", []))
    if failures is None:
        failures = []
    if not isinstance(failures, list):
        msg = f"Premap consumer readonly gate failures must be a list: {path}"
        raise TypeError(msg)
    if not gate_passed:
        msg = (
            "Premap consumer readonly gate did not pass "
            f"for {path}: failures={failures}"
        )
        raise ValueError(msg)

    contract = payload.get("contract", {})
    if not isinstance(contract, dict):
        msg = f"Premap consumer readonly gate contract must be a mapping: {path}"
        raise TypeError(msg)
    expected_contract = {
        "payload_bytes_required": 0,
        "ready_credit_required": False,
        "changes_router_required": False,
        "changes_descriptor_order_required": False,
        "address_key_scope": "layer_expert",
        "handle_resolution": "read_only",
    }
    for key, expected in expected_contract.items():
        observed = contract.get(key)
        if observed != expected:
            msg = (
                "Premap consumer readonly gate violates the no-op contract "
                f"for {path}: {key}={observed!r} != {expected!r}"
            )
            raise ValueError(msg)
    lab_precondition = payload.get("lab_precondition")
    if lab_precondition is not None and not isinstance(lab_precondition, bool):
        msg = (
            "Premap consumer readonly gate `lab_precondition` must be boolean "
            f"when present: {path}"
        )
        raise TypeError(msg)
    if descriptor_prep_mode is not None:
        if lab_precondition is not True:
            msg = (
                "premap_descriptor_prep_execution_mode requires a readonly gate "
                f"with lab_precondition=true: {path}"
            )
            raise ValueError(msg)
        descriptor_prep_contract = {
            "descriptor_prep_execution_mode": descriptor_prep_mode,
            "descriptor_prep_payload_bytes_required": 0,
            "descriptor_prep_kernel_arg_mutation_required": False,
            "kernel_arg_shadow_table_required": True,
            "consumer_shim_table_read_required": True,
            "consumer_shim_table_consume_required": True,
        }
        for key, expected in descriptor_prep_contract.items():
            observed = contract.get(key)
            if observed != expected:
                msg = (
                    "Premap consumer readonly gate violates the descriptor prep "
                    f"contract for {path}: {key}={observed!r} != {expected!r}"
                )
                raise ValueError(msg)
        check = gate.get("check", {})
        if not isinstance(check, dict):
            msg = f"Premap consumer readonly gate `gate.check` must be a mapping: {path}"
            raise TypeError(msg)
        if contract.get("real_descriptor_prep_required") is not True:
            msg = (
                "premap_descriptor_prep_execution_mode requires a readonly gate "
                f"with contract.real_descriptor_prep_required=true: {path}"
            )
            raise ValueError(msg)
        if check.get("require_real_descriptor_prep") is not True:
            msg = (
                "premap_descriptor_prep_execution_mode requires a readonly gate "
                f"checked with require_real_descriptor_prep=true: {path}"
            )
            raise ValueError(msg)
        if check.get("require_kernel_arg_shadow_table") is not True:
            msg = (
                "premap_descriptor_prep_execution_mode requires a readonly gate "
                f"checked with require_kernel_arg_shadow_table=true: {path}"
            )
            raise ValueError(msg)
        if check.get("require_consumer_shim_table_read") is not True:
            msg = (
                "premap_descriptor_prep_execution_mode requires a readonly gate "
                f"checked with require_consumer_shim_table_read=true: {path}"
            )
            raise ValueError(msg)
        if check.get("require_consumer_shim_table_consume") is not True:
            msg = (
                "premap_descriptor_prep_execution_mode requires a readonly gate "
                f"checked with require_consumer_shim_table_consume=true: {path}"
            )
            raise ValueError(msg)
    descriptor_bytes = contract.get("descriptor_bytes")
    option_descriptor_bytes = options.get("premap_descriptor_bytes", 4096)
    if (
        descriptor_bytes is not None
        and int(descriptor_bytes) != int(option_descriptor_bytes)
    ):
        msg = (
            "Premap consumer readonly gate descriptor size does not match runtime "
            f"options for {path}: {descriptor_bytes} != {option_descriptor_bytes}"
        )
        raise ValueError(msg)
    if require_gate:
        if not bool(options.get("emit_premap_consumer_mapping", False)):
            msg = (
                "premap_consumer_require_readonly_gate=True requires "
                "emit_premap_consumer_mapping=True."
            )
            raise ValueError(msg)
        if (
            str(options.get("premap_consumer_mapping_mode", "noop_assertion"))
            != "noop_assertion"
        ):
            msg = (
                "premap_consumer_require_readonly_gate=True requires "
                "premap_consumer_mapping_mode=noop_assertion."
            )
            raise ValueError(msg)
        if not bool(options.get("premap_consumer_resolve_real_handles", False)):
            msg = (
                "premap_consumer_require_readonly_gate=True requires "
                "premap_consumer_resolve_real_handles=True."
            )
            raise ValueError(msg)
        policy = str(options.get("premap_policy", "premap_only_with_consumer_mapping_noop"))
        if policy != "premap_only_with_consumer_mapping_noop":
            msg = (
                "premap_consumer_require_readonly_gate=True requires "
                "premap_policy=premap_only_with_consumer_mapping_noop."
            )
            raise ValueError(msg)

    updated = dict(options)
    updated["premap_consumer_readonly_gate_required"] = require_gate
    updated["premap_consumer_readonly_gate_id"] = payload.get(
        "artifact_id",
        payload.get("id"),
    )
    updated["premap_consumer_readonly_gate_resolved_path"] = str(path)
    updated["premap_consumer_readonly_gate_passed"] = True
    updated["premap_consumer_readonly_gate_failures"] = failures
    updated["premap_consumer_readonly_gate_metrics"] = gate.get("metrics", {})
    updated["premap_consumer_readonly_gate_evidence_paths"] = payload.get(
        "evidence_paths",
        {},
    )
    return updated


def _build_runtime_shadow_controller(
    *,
    options: dict[str, Any],
    output_dir: Path,
    project_root: Path,
) -> RuntimeShadowController | None:
    if not bool(options.get("enabled", False)):
        return None
    raw_output = options.get("output_path")
    if raw_output is None:
        output_path = output_dir / "runtime_shadow.jsonl"
    else:
        output_path = resolve_path(raw_output, base_dir=project_root)
    if bool(options.get("overwrite", False)) and output_path.exists():
        output_path.unlink()
    logger = OnlineShadowLogger(
        output_path,
        flush_every=int(options.get("flush_every", 1)),
        writer_mode=str(options.get("writer_mode", "sync_jsonl")),
    )
    return RuntimeShadowController(
        logger,
        max_pending=int(options.get("max_pending", 100_000)),
        emit_summaries=bool(options.get("emit_summaries", True)),
        emit_outcomes=bool(options.get("emit_outcomes", True)),
    )


def _load_runtime_shadow_transition_matrix(
    *,
    options: dict[str, Any],
    project_root: Path,
) -> torch.Tensor | None:
    raw_path = options.get("transition_matrix_path")
    if raw_path is None:
        return None
    path = resolve_path(raw_path, base_dir=project_root)
    payload = torch.load(path, map_location="cpu")
    key = str(options.get("transition_matrix_key", "transition_matrix"))
    if isinstance(payload, dict):
        if key in payload:
            payload = payload[key]
        elif "transition" in payload:
            payload = payload["transition"]
    return torch.as_tensor(payload, dtype=torch.float32)


def _load_runtime_shadow_descriptor_order_prior(
    *,
    options: dict[str, Any],
    project_root: Path,
) -> tuple[LayerTilePrior | None, str | None]:
    raw_path = options.get("descriptor_order_prior_path")
    if raw_path is None:
        return None, None
    path = resolve_path(raw_path, base_dir=project_root)
    prior = load_layer_tile_prior(path)
    return prior, hash_layer_tile_prior(prior)


def _load_runtime_shadow_descriptor_order_gate(
    *,
    options: dict[str, Any],
    project_root: Path,
) -> DescriptorOrderRuntimeGate | None:
    raw_path = options.get("descriptor_order_gate_path")
    if raw_path is None:
        return None
    path = resolve_path(raw_path, base_dir=project_root)
    return DescriptorOrderRuntimeGate.from_config(path, base_dir=project_root)


def _load_runtime_shadow_descriptor_order_evidence(
    *,
    options: dict[str, Any],
    project_root: Path,
) -> dict[DescriptorOrderEvidenceKey, DescriptorOrderExecutionEvidence] | None:
    raw_path = options.get("descriptor_order_consumer_evidence_path")
    if raw_path is None:
        return None
    path = resolve_path(raw_path, base_dir=project_root)
    return load_descriptor_order_consumer_evidence(
        path,
        evidence_policy=str(
            options.get("descriptor_order_evidence_policy", "layer_prior_frequency_two_level")
        ),
        cache_flush_elems=int(options.get("descriptor_order_evidence_cache_flush_elems", 0)),
        checksum_tolerance=float(options.get("descriptor_order_checksum_tolerance", 0.0)),
    )


def _load_runtime_shadow_descriptor_order_layer_allowlist(
    *,
    options: dict[str, Any],
    project_root: Path,
) -> tuple[tuple[int, ...] | None, dict[str, Any] | None]:
    raw_inline = options.get("descriptor_order_reorder_mvp_layer_allowlist")
    inline_layers = (
        tuple(int(layer) for layer in raw_inline)
        if raw_inline is not None
        else None
    )
    raw_path = options.get(
        "descriptor_order_reorder_mvp_layer_allowlist_artifact_path"
    )
    if raw_path is None:
        return inline_layers, None

    path = resolve_path(raw_path, base_dir=project_root)
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = load_yaml(path)
    if not isinstance(payload, dict):
        msg = f"Expected a mapping in allowlist artifact: {path}"
        raise TypeError(msg)

    raw_layers = payload.get("allowlist", payload.get("layers"))
    if raw_layers is None:
        msg = f"Allowlist artifact must contain `layers` or `allowlist`: {path}"
        raise ValueError(msg)
    artifact_layers = tuple(int(layer) for layer in raw_layers)
    if not artifact_layers:
        msg = f"Allowlist artifact is empty: {path}"
        raise ValueError(msg)
    if inline_layers is not None and inline_layers != artifact_layers:
        msg = (
            "Inline descriptor_order_reorder_mvp_layer_allowlist does not match "
            f"artifact layers in {path}"
        )
        raise ValueError(msg)

    artifact_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    source_split = payload.get("source_split")
    if not isinstance(source_split, dict):
        source_split = None
    threshold = payload.get("threshold")
    if not isinstance(threshold, dict):
        threshold = threshold if threshold is not None else None
    metadata = {
        "path": str(path),
        "id": payload.get("id", payload.get("artifact_id")),
        "hash": artifact_hash,
        "source_split": source_split,
        "source_max_tokens": payload.get(
            "source_max_tokens",
            source_split.get("max_tokens") if source_split is not None else None,
        ),
        "threshold": threshold,
        "evidence_paths": payload.get("evidence_paths", []),
    }
    return artifact_layers, metadata


def _int_tuple_option(
    options: dict[str, Any],
    key: str,
    default: tuple[int, ...],
) -> tuple[int, ...]:
    raw = options.get(key)
    if raw is None:
        return default
    if isinstance(raw, int):
        return (int(raw),)
    if isinstance(raw, str):
        values = [item.strip() for item in raw.split(",") if item.strip()]
        return tuple(int(item) for item in values) or default
    return tuple(int(item) for item in raw) or default


def _optional_capacity_option(options: dict[str, Any], key: str) -> int | None:
    raw = options.get(key)
    if raw is None:
        return None
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"", "none", "null", "unbounded", "inf", "infinite"}:
            return None
        return int(normalized)
    return int(raw)


def _filter_vllm_engine_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Drop options unsupported by the installed vLLM EngineArgs version."""

    try:
        from vllm.engine.arg_utils import EngineArgs
    except Exception:
        return kwargs
    signature = inspect.signature(EngineArgs)
    accepted = set(signature.parameters)
    return {key: value for key, value in kwargs.items() if key in accepted}


def _shadow_request_id(
    *,
    sample_idx: int,
    record: dict[str, Any],
    options: dict[str, Any],
) -> str:
    field = options.get("request_id_field")
    if field is not None and record.get(str(field)) is not None:
        return str(record[str(field)])
    prefix = str(options.get("request_id_prefix", "sample_"))
    return f"{prefix}{int(sample_idx)}"


def _shadow_sequence_id(record: dict[str, Any], options: dict[str, Any]) -> int:
    field = options.get("sequence_id_field")
    if field is not None and record.get(str(field)) is not None:
        return int(record[str(field)])
    return int(options.get("sequence_id", 0))


def trace_router_mtp_vllm(config_path: str | Path) -> Path:
    trace_wall_start_ns = time.perf_counter_ns()
    config_path = Path(config_path)
    project_root = find_project_root(config_path)
    trace_config = load_yaml(config_path)
    model_config = load_yaml(resolve_path(trace_config["model"], base_dir=project_root))
    trace_options = trace_config.get("trace", {})
    vllm_options = model_config.get("vllm", {})

    model_id = resolve_path(model_config["model_id"], base_dir=project_root)
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

    use_router_logits_recorder = bool(
        trace_options.get(
            "use_router_logits_recorder",
            trace_options.get(
                "capture_router_scores",
                vllm_options.get("use_router_logits_recorder", False),
            ),
        )
    )
    runtime_shadow_options = _runtime_shadow_options(trace_options, vllm_options)
    runtime_shadow_options = _apply_premap_address_capacity_gate(
        runtime_shadow_options,
        project_root=project_root,
    )
    runtime_shadow_options = _apply_premap_consumer_readonly_gate(
        runtime_shadow_options,
        project_root=project_root,
    )
    if bool(runtime_shadow_options.get("enabled", False)) and not use_router_logits_recorder:
        msg = "runtime_shadow.enabled requires use_router_logits_recorder."
        raise ValueError(msg)
    if bool(vllm_options.get("disable_flash_attn_probe", True)):
        _set_text_only_vllm_env()
    if use_router_logits_recorder and bool(
        vllm_options.get("disable_v1_multiprocessing_for_recorder", True)
    ):
        os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    patch_missing_activation_ops = bool(
        runtime_shadow_options.get("patch_missing_vllm_activation_ops", False)
    ) or str(os.environ.get("MTP_PATCH_MISSING_VLLM_ACTIVATION_OPS", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    patched_missing_activation_ops = (
        _patch_missing_vllm_activation_ops_for_trace()
        if patch_missing_activation_ops
        else False
    )

    try:
        from vllm.inputs import TokensPrompt
    except Exception:
        TokensPrompt = dict

    trust_remote_code = bool(model_config.get("trust_remote_code", True))
    local_files_only = bool(model_config.get("local_files_only", True))
    vllm_max_model_len = int(vllm_options.get("max_model_len", 128))
    max_length = int(trace_options.get("max_length", vllm_max_model_len))
    max_tokens = int(trace_options.get("max_tokens", vllm_options.get("max_tokens", 1)))
    max_input_length = min(max_length, vllm_max_model_len - max_tokens)
    if max_input_length <= 0:
        msg = (
            f"max_model_len={vllm_max_model_len} leaves no room for "
            f"max_tokens={max_tokens}."
        )
        raise ValueError(msg)
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_id),
        trust_remote_code=trust_remote_code,
        local_files_only=local_files_only,
    )

    llm_kwargs: dict[str, Any] = {
        "model": str(model_id),
        "trust_remote_code": trust_remote_code,
        "dtype": str(model_config.get("torch_dtype", "bfloat16")),
        "max_model_len": vllm_max_model_len,
        "tensor_parallel_size": int(vllm_options.get("tensor_parallel_size", 1)),
        "gpu_memory_utilization": float(vllm_options.get("gpu_memory_utilization", 0.85)),
        "enforce_eager": bool(vllm_options.get("enforce_eager", True)),
        "enable_return_routed_experts": bool(
            vllm_options.get(
                "enable_return_routed_experts_with_recorder",
                False,
            )
            if use_router_logits_recorder
            else vllm_options.get("enable_return_routed_experts", True)
        ),
    }
    if "hf_config_path" in vllm_options:
        llm_kwargs["hf_config_path"] = str(
            resolve_path(vllm_options["hf_config_path"], base_dir=project_root)
        )
    if "hf_overrides" in vllm_options:
        llm_kwargs["hf_overrides"] = vllm_options["hf_overrides"]
    if use_router_logits_recorder:
        patch_vllm_qwen35_moe_router_trace()
    if "quantization" in vllm_options:
        llm_kwargs["quantization"] = vllm_options["quantization"]
    for optional_key in ("max_num_seqs", "max_num_batched_tokens"):
        if optional_key in vllm_options:
            llm_kwargs[optional_key] = int(vllm_options[optional_key])
    if bool(vllm_options.get("language_model_only", True)):
        llm_kwargs["language_model_only"] = True
        llm_kwargs["limit_mm_per_prompt"] = vllm_options.get(
            "limit_mm_per_prompt",
            {"image": 0, "video": 0},
        )
    llm_kwargs = _filter_vllm_engine_kwargs(llm_kwargs)

    sampling = SamplingParams(max_tokens=max_tokens, temperature=0.0)
    module_prefix = str(
        trace_options.get("router_module_prefix", "model.language_model")
    )
    token_source_input_ids = _load_token_source_input_ids(
        trace_options.get("token_source_manifest"),
        project_root=project_root,
    )
    prepared_records: list[tuple[int, dict[str, Any], list[int], Any]] = []
    for local_idx, record in enumerate(texts):
        sample_idx = start_sample + local_idx
        text = _extract_text(record)
        source_input_ids = token_source_input_ids.get(sample_idx)
        if source_input_ids is None:
            encoded = tokenizer(
                text,
                return_tensors=None,
                truncation=True,
                max_length=max_input_length,
            )
            input_ids = [int(token) for token in encoded["input_ids"]]
        else:
            input_ids = source_input_ids[:max_input_length]
        prompt = TokensPrompt(_to_token_prompt(input_ids, prompt=text))
        prepared_records.append((sample_idx, record, input_ids, prompt))

    engine_chunk_size = int(vllm_options.get("engine_chunk_size", len(prepared_records)))
    if use_router_logits_recorder:
        engine_chunk_size = len(prepared_records)
    if engine_chunk_size <= 0:
        msg = f"engine_chunk_size must be positive, got {engine_chunk_size}"
        raise ValueError(msg)

    runtime_shadow_controller = _build_runtime_shadow_controller(
        options=runtime_shadow_options,
        output_dir=output_dir,
        project_root=project_root,
    )
    runtime_shadow_path = (
        runtime_shadow_controller.logger.path
        if runtime_shadow_controller is not None
        else None
    )
    runtime_shadow_transition_matrix = _load_runtime_shadow_transition_matrix(
        options=runtime_shadow_options,
        project_root=project_root,
    )
    (
        runtime_shadow_descriptor_order_prior,
        runtime_shadow_descriptor_order_prior_hash,
    ) = _load_runtime_shadow_descriptor_order_prior(
        options=runtime_shadow_options,
        project_root=project_root,
    )
    runtime_shadow_descriptor_order_gate = _load_runtime_shadow_descriptor_order_gate(
        options=runtime_shadow_options,
        project_root=project_root,
    )
    runtime_shadow_descriptor_order_evidence = (
        _load_runtime_shadow_descriptor_order_evidence(
            options=runtime_shadow_options,
            project_root=project_root,
        )
    )
    (
        runtime_shadow_descriptor_order_layer_allowlist,
        runtime_shadow_descriptor_order_layer_allowlist_artifact,
    ) = _load_runtime_shadow_descriptor_order_layer_allowlist(
        options=runtime_shadow_options,
        project_root=project_root,
    )
    manifest_path = output_dir / "manifest.jsonl"
    sample_timing_path = output_dir / "sample_timing.jsonl"
    performance = {
        "sample_count": len(prepared_records),
        "input_token_count": int(
            sum(
                len(input_ids)
                for _idx, _record, input_ids, _prompt in prepared_records
            )
        ),
        "requested_output_token_count": int(len(prepared_records) * max_tokens),
        "llm_init_wall_seconds": 0.0,
        "generate_wall_seconds": 0.0,
        "trace_write_wall_seconds": 0.0,
        "sample_timing_path": sample_timing_path.name,
        "chunk_count": 0,
        "runtime_shadow_enabled": bool(runtime_shadow_options.get("enabled", False)),
        "runtime_shadow_emit_descriptor_order_summaries": bool(
            runtime_shadow_options.get("emit_descriptor_order_summaries", False)
        ),
        "runtime_shadow_emit_premap_summaries": bool(
            runtime_shadow_options.get("emit_premap_summaries", False)
        ),
        "runtime_shadow_emit_transition_premap_summaries": bool(
            runtime_shadow_options.get("emit_transition_premap_summaries", False)
        ),
        "runtime_shadow_premap_policy": str(
            runtime_shadow_options.get("premap_policy", "premap_only")
        ),
        "runtime_shadow_premap_source": str(
            runtime_shadow_options.get(
                "premap_source",
                "current_router_topk_premap_shadow",
            )
        ),
        "runtime_shadow_premap_address_manager_capacity": _optional_capacity_option(
            runtime_shadow_options,
            "premap_address_manager_capacity",
        ),
        "runtime_shadow_premap_address_capacity_gate_id": runtime_shadow_options.get(
            "premap_address_capacity_gate_id"
        ),
        "runtime_shadow_premap_address_capacity_gate_path": runtime_shadow_options.get(
            "premap_address_capacity_gate_resolved_path"
        ),
        "runtime_shadow_premap_address_capacity_gate_recommended_capacity": (
            runtime_shadow_options.get(
                "premap_address_capacity_gate_recommended_capacity"
            )
        ),
        "runtime_shadow_premap_address_capacity_gate_evidence_paths": (
            runtime_shadow_options.get("premap_address_capacity_gate_evidence_paths")
        ),
        "runtime_shadow_premap_summary_sample_period": int(
            runtime_shadow_options.get(
                "premap_summary_sample_period",
                1,
            )
        ),
        "runtime_shadow_emit_premap_consumer_mapping": bool(
            runtime_shadow_options.get("emit_premap_consumer_mapping", False)
        ),
        "runtime_shadow_premap_consumer_mapping_mode": str(
            runtime_shadow_options.get(
                "premap_consumer_mapping_mode",
                "noop_assertion",
            )
        ),
        "runtime_shadow_premap_consumer_mapping_source": str(
            runtime_shadow_options.get(
                "premap_consumer_mapping_source",
                "fused_moe_prepare_expert_assignment",
            )
        ),
        "runtime_shadow_premap_consumer_mapping_sample_period": int(
            runtime_shadow_options.get(
                "premap_consumer_mapping_sample_period",
                1,
            )
        ),
        "runtime_shadow_premap_consumer_readonly_gate_required": bool(
            runtime_shadow_options.get(
                "premap_consumer_readonly_gate_required",
                runtime_shadow_options.get(
                    "premap_consumer_require_readonly_gate",
                    False,
                ),
            )
        ),
        "runtime_shadow_premap_consumer_readonly_gate_id": (
            runtime_shadow_options.get("premap_consumer_readonly_gate_id")
        ),
        "runtime_shadow_premap_consumer_readonly_gate_path": (
            runtime_shadow_options.get("premap_consumer_readonly_gate_resolved_path")
        ),
        "runtime_shadow_premap_consumer_readonly_gate_passed": (
            runtime_shadow_options.get("premap_consumer_readonly_gate_passed")
        ),
        "runtime_shadow_premap_consumer_readonly_gate_failures": (
            runtime_shadow_options.get("premap_consumer_readonly_gate_failures")
        ),
        "runtime_shadow_premap_consumer_readonly_gate_metrics": (
            runtime_shadow_options.get("premap_consumer_readonly_gate_metrics")
        ),
        "runtime_shadow_premap_consumer_readonly_gate_evidence_paths": (
            runtime_shadow_options.get(
                "premap_consumer_readonly_gate_evidence_paths"
            )
        ),
        "runtime_shadow_premap_descriptor_prep_execution_mode": str(
            runtime_shadow_options.get("premap_descriptor_prep_execution_mode", "off")
        ),
        "runtime_shadow_transition_premap_source": str(
            runtime_shadow_options.get(
                "transition_premap_source",
                "previous_token_transition_premap_shadow",
            )
        ),
        "runtime_shadow_emit_summaries": bool(
            runtime_shadow_options.get("emit_summaries", True)
        ),
        "runtime_shadow_emit_outcomes": bool(
            runtime_shadow_options.get("emit_outcomes", True)
        ),
        "runtime_shadow_outcome_logging_mode": str(
            runtime_shadow_options.get("outcome_logging_mode", "full")
        ),
        "runtime_shadow_writer_mode": str(
            runtime_shadow_options.get("writer_mode", "sync_jsonl")
        ),
        "runtime_shadow_descriptor_order_metrics_mode": (
            str(runtime_shadow_options.get("descriptor_order_metrics_mode"))
            if runtime_shadow_options.get("descriptor_order_metrics_mode") is not None
            else None
        ),
        "runtime_shadow_descriptor_order_event_mode": str(
            runtime_shadow_options.get("descriptor_order_event_mode", "summary")
        ),
        "runtime_shadow_descriptor_order_execution_mode": str(
            runtime_shadow_options.get(
                "descriptor_order_execution_mode",
                "two_level_group_plan",
            )
        ),
        "runtime_shadow_descriptor_order_mapping_assertion_mode": str(
            runtime_shadow_options.get("descriptor_order_mapping_assertion_mode", "off")
        ),
        "runtime_shadow_descriptor_order_mapping_source": str(
            runtime_shadow_options.get(
                "descriptor_order_mapping_source",
                "base_router_select_experts_topk",
            )
        ),
        "runtime_shadow_descriptor_order_prelaunch_assertion_mode": str(
            runtime_shadow_options.get("descriptor_order_prelaunch_assertion_mode", "off")
        ),
        "runtime_shadow_descriptor_order_prelaunch_mapping_source": str(
            runtime_shadow_options.get(
                "descriptor_order_prelaunch_mapping_source",
                "moe_runner_quant_method_apply_topk",
            )
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_enabled": bool(
            runtime_shadow_options.get("descriptor_order_reorder_mvp_enabled", False)
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_apply_mode": str(
            runtime_shadow_options.get("descriptor_order_reorder_mvp_apply_mode", "dry_run")
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_attribution_mode": str(
            runtime_shadow_options.get(
                "descriptor_order_reorder_mvp_attribution_mode",
                "full",
            )
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_require_profitable": bool(
            runtime_shadow_options.get(
                "descriptor_order_reorder_mvp_require_profitable",
                True,
            )
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_layer_allowlist_count": (
            len(runtime_shadow_descriptor_order_layer_allowlist)
            if runtime_shadow_descriptor_order_layer_allowlist is not None
            else 0
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_layer_allowlist_artifact_path": (
            runtime_shadow_descriptor_order_layer_allowlist_artifact.get("path")
            if runtime_shadow_descriptor_order_layer_allowlist_artifact is not None
            else None
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_layer_allowlist_artifact_id": (
            runtime_shadow_descriptor_order_layer_allowlist_artifact.get("id")
            if runtime_shadow_descriptor_order_layer_allowlist_artifact is not None
            else None
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_layer_allowlist_artifact_hash": (
            runtime_shadow_descriptor_order_layer_allowlist_artifact.get("hash")
            if runtime_shadow_descriptor_order_layer_allowlist_artifact is not None
            else None
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_layer_allowlist_source_split": (
            runtime_shadow_descriptor_order_layer_allowlist_artifact.get("source_split")
            if runtime_shadow_descriptor_order_layer_allowlist_artifact is not None
            else None
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_layer_allowlist_source_max_tokens": (
            runtime_shadow_descriptor_order_layer_allowlist_artifact.get(
                "source_max_tokens"
            )
            if runtime_shadow_descriptor_order_layer_allowlist_artifact is not None
            else None
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_layer_allowlist_threshold": (
            runtime_shadow_descriptor_order_layer_allowlist_artifact.get("threshold")
            if runtime_shadow_descriptor_order_layer_allowlist_artifact is not None
            else None
        ),
        "runtime_shadow_descriptor_order_reorder_mvp_layer_allowlist_evidence_paths": (
            runtime_shadow_descriptor_order_layer_allowlist_artifact.get(
                "evidence_paths",
            )
            if runtime_shadow_descriptor_order_layer_allowlist_artifact is not None
            else []
        ),
        "runtime_shadow_descriptor_order_groups_per_cta": int(
            runtime_shadow_options.get("descriptor_order_groups_per_cta", 8)
        ),
        "runtime_shadow_descriptor_order_tile_elems": int(
            runtime_shadow_options.get("descriptor_order_tile_elems", 1024)
        ),
        "runtime_shadow_descriptor_order_gate_enabled": (
            runtime_shadow_descriptor_order_gate is not None
        ),
        "runtime_shadow_descriptor_order_evidence_enabled": (
            runtime_shadow_descriptor_order_evidence is not None
        ),
        "runtime_shadow_descriptor_order_evidence_cell_count": (
            len(runtime_shadow_descriptor_order_evidence)
            if runtime_shadow_descriptor_order_evidence is not None
            else 0
        ),
        "runtime_shadow_wna16_config_override_enabled": bool(
            runtime_shadow_options.get("wna16_config_override")
        ),
        "runtime_shadow_wna16_config_override": (
            dict(runtime_shadow_options.get("wna16_config_override") or {})
        ),
        "runtime_shadow_wna16_config_override_preserve_dynamic_nk": bool(
            runtime_shadow_options.get(
                "wna16_config_override_preserve_dynamic_nk",
                True,
            )
        ),
        "runtime_shadow_wna16_config_override_max_tokens": (
            int(runtime_shadow_options["wna16_config_override_max_tokens"])
            if runtime_shadow_options.get("wna16_config_override_max_tokens") is not None
            else None
        ),
        "runtime_shadow_wna16_config_override_route_product": (
            int(runtime_shadow_options["wna16_config_override_route_product"])
            if runtime_shadow_options.get("wna16_config_override_route_product")
            is not None
            else None
        ),
        "runtime_shadow_wna16_config_override_target_top_k": (
            int(runtime_shadow_options["wna16_config_override_target_top_k"])
            if runtime_shadow_options.get("wna16_config_override_target_top_k")
            is not None
            else None
        ),
        "runtime_shadow_wna16_kernel_timing_mode": str(
            runtime_shadow_options.get("wna16_kernel_timing_mode", "host")
        ),
        "runtime_shadow_emit_wna16_kernel_timing": bool(
            runtime_shadow_options.get(
                "emit_wna16_kernel_timing",
                runtime_shadow_options.get("emit_summaries", False),
            )
        ),
        "runtime_shadow_emit_descriptor_layer_timing": bool(
            runtime_shadow_options.get("emit_descriptor_layer_timing", True)
        ),
        "runtime_shadow_emit_decoder_layer_timing": bool(
            runtime_shadow_options.get("emit_decoder_layer_timing", False)
        ),
        "runtime_shadow_emit_decoder_component_timing": bool(
            runtime_shadow_options.get("emit_decoder_component_timing", True)
        ),
        "runtime_shadow_decoder_component_logging_mode": str(
            runtime_shadow_options.get("decoder_component_logging_mode", "rows")
        ),
        "runtime_shadow_emit_moe_substage_timing": bool(
            runtime_shadow_options.get("emit_moe_substage_timing", True)
        ),
        "runtime_shadow_moe_substage_logging_mode": str(
            runtime_shadow_options.get("moe_substage_logging_mode", "rows")
        ),
        "runtime_shadow_moe_substage_sample_period": int(
            runtime_shadow_options.get("moe_substage_sample_period", 1)
        ),
        "runtime_shadow_emit_engine_timing": bool(
            runtime_shadow_options.get("emit_engine_timing", False)
        ),
        "runtime_shadow_moe_source_timing_mode": str(
            runtime_shadow_options.get("moe_source_timing_mode", "full")
        ),
        "runtime_shadow_decoder_source_timing_mode": str(
            runtime_shadow_options.get("decoder_source_timing_mode", "off")
        ),
        "runtime_shadow_shared_experts_force_aux_stream": bool(
            runtime_shadow_options.get("shared_experts_force_aux_stream", False)
        ),
        "runtime_shadow_shared_expert_output_gate_ablation": str(
            runtime_shadow_options.get("shared_expert_output_gate_ablation", "off")
        ),
        "runtime_shadow_shared_expert_output_gate_postprocess": str(
            runtime_shadow_options.get(
                "shared_expert_output_gate_postprocess",
                "default",
            )
        ),
        "runtime_shadow_record_router_topk": bool(
            runtime_shadow_options.get("record_router_topk", True)
        ),
        "runtime_shadow_patch_missing_vllm_activation_ops": (
            patch_missing_activation_ops
        ),
        "runtime_shadow_patched_missing_vllm_activation_ops": (
            patched_missing_activation_ops
        ),
        "trace_fallback_mode": (
            "vllm_activation_and_topk_ops"
            if patched_missing_activation_ops
            else None
        ),
    }
    try:
        with manifest_path.open("w", encoding="utf-8") as manifest, sample_timing_path.open(
            "w",
            encoding="utf-8",
        ) as sample_timing:
            for chunk_start in range(0, len(prepared_records), engine_chunk_size):
                chunk = prepared_records[chunk_start : chunk_start + engine_chunk_size]
                performance["chunk_count"] += 1
                llm_init_start_ns = time.perf_counter_ns()
                llm = LLM(**llm_kwargs)
                performance["llm_init_wall_seconds"] += (
                    time.perf_counter_ns() - llm_init_start_ns
                ) / 1_000_000_000.0
                try:
                    if use_router_logits_recorder:
                        recorder = VllmRouterRecorder(
                            top_k=int(model_config["architecture"].get("num_experts_per_tok", 8)),
                            capture_router_input_hidden=bool(
                                trace_options.get("capture_router_input_hidden", False)
                            ),
                            shadow_outcome_sink=runtime_shadow_controller,
                            shadow_emit_transition_summary=bool(
                                runtime_shadow_options.get("emit_transition_summaries", False)
                            ),
                            shadow_num_experts=int(
                                model_config["architecture"].get("num_experts", 256)
                            ),
                            shadow_transition_topk_count=int(
                                runtime_shadow_options.get(
                                    "transition_topk_count",
                                    model_config["architecture"].get("num_experts_per_tok", 8),
                                )
                            ),
                            shadow_transition_summary_mode=str(
                                runtime_shadow_options.get(
                                    "transition_summary_mode",
                                    "previous_topk",
                                )
                            ),
                            shadow_transition_matrix=runtime_shadow_transition_matrix,
                            shadow_emit_premap_summary=bool(
                                runtime_shadow_options.get(
                                    "emit_premap_summaries",
                                    False,
                                )
                            ),
                            shadow_emit_transition_premap_summary=bool(
                                runtime_shadow_options.get(
                                    "emit_transition_premap_summaries",
                                    False,
                                )
                            ),
                            shadow_premap_policy=str(
                                runtime_shadow_options.get(
                                    "premap_policy",
                                    "premap_only",
                                )
                            ),
                            shadow_premap_source=str(
                                runtime_shadow_options.get(
                                    "premap_source",
                                    "current_router_topk_premap_shadow",
                                )
                            ),
                            shadow_transition_premap_source=str(
                                runtime_shadow_options.get(
                                    "transition_premap_source",
                                    "previous_token_transition_premap_shadow",
                                )
                            ),
                            shadow_premap_descriptor_bytes=int(
                                runtime_shadow_options.get(
                                    "premap_descriptor_bytes",
                                    4_096,
                                )
                            ),
                            shadow_emit_premap_address_manager_counters=bool(
                                runtime_shadow_options.get(
                                    "emit_premap_address_manager_counters",
                                    False,
                                )
                            ),
                            shadow_premap_address_manager_capacity=_optional_capacity_option(
                                runtime_shadow_options,
                                "premap_address_manager_capacity",
                            ),
                            shadow_premap_summary_sample_period=max(
                                1,
                                int(
                                    runtime_shadow_options.get(
                                        "premap_summary_sample_period",
                                        1,
                                    )
                                ),
                            ),
                            shadow_emit_premap_consumer_mapping=bool(
                                runtime_shadow_options.get(
                                    "emit_premap_consumer_mapping",
                                    False,
                                )
                            ),
                            shadow_premap_consumer_mapping_mode=str(
                                runtime_shadow_options.get(
                                    "premap_consumer_mapping_mode",
                                    "noop_assertion",
                                )
                            ),
                            shadow_premap_consumer_mapping_source=str(
                                runtime_shadow_options.get(
                                    "premap_consumer_mapping_source",
                                    "fused_moe_prepare_expert_assignment",
                                )
                            ),
                            shadow_premap_consumer_resolve_real_handles=bool(
                                runtime_shadow_options.get(
                                    "premap_consumer_resolve_real_handles",
                                    False,
                                )
                            ),
                            shadow_premap_consumer_mapping_sample_period=max(
                                1,
                                int(
                                    runtime_shadow_options.get(
                                        "premap_consumer_mapping_sample_period",
                                        1,
                                    )
                                ),
                            ),
                            shadow_premap_consumer_readonly_gate_required=bool(
                                runtime_shadow_options.get(
                                    "premap_consumer_readonly_gate_required",
                                    runtime_shadow_options.get(
                                        "premap_consumer_require_readonly_gate",
                                        False,
                                    ),
                                )
                            ),
                            shadow_premap_consumer_readonly_gate_id=(
                                str(
                                    runtime_shadow_options.get(
                                        "premap_consumer_readonly_gate_id"
                                    )
                                )
                                if runtime_shadow_options.get(
                                    "premap_consumer_readonly_gate_id"
                                )
                                is not None
                                else None
                            ),
                            shadow_premap_consumer_readonly_gate_path=(
                                str(
                                    runtime_shadow_options.get(
                                        "premap_consumer_readonly_gate_resolved_path"
                                    )
                                )
                                if runtime_shadow_options.get(
                                    "premap_consumer_readonly_gate_resolved_path"
                                )
                                is not None
                                else None
                            ),
                            shadow_premap_consumer_readonly_gate_passed=(
                                None
                                if runtime_shadow_options.get(
                                    "premap_consumer_readonly_gate_passed"
                                )
                                is None
                                else bool(
                                    runtime_shadow_options.get(
                                        "premap_consumer_readonly_gate_passed"
                                    )
                                )
                            ),
                            shadow_premap_descriptor_prep_execution_mode=str(
                                runtime_shadow_options.get(
                                    "premap_descriptor_prep_execution_mode",
                                    "off",
                                )
                            ),
                            shadow_premap_address_namespace=str(
                                runtime_shadow_options.get(
                                    "premap_address_namespace",
                                    "expert_weight_descriptor",
                                )
                            ),
                            shadow_premap_priority=int(
                                runtime_shadow_options.get("premap_priority", 2)
                            ),
                            shadow_transition_premap_priority=int(
                                runtime_shadow_options.get(
                                    "transition_premap_priority",
                                    3,
                                )
                            ),
                            shadow_premap_event_token_index=int(
                                runtime_shadow_options.get(
                                    "premap_event_token_index",
                                    -1,
                                )
                            ),
                            shadow_emit_descriptor_order_summary=bool(
                                runtime_shadow_options.get(
                                    "emit_descriptor_order_summaries",
                                    False,
                                )
                            ),
                            shadow_descriptor_order_prior=runtime_shadow_descriptor_order_prior,
                            shadow_descriptor_order_prior_id=(
                                str(runtime_shadow_options.get("descriptor_order_prior_id"))
                                if runtime_shadow_options.get("descriptor_order_prior_id")
                                is not None
                                else None
                            ),
                            shadow_descriptor_order_prior_hash=(
                                str(
                                    runtime_shadow_options.get(
                                        "descriptor_order_prior_hash",
                                        runtime_shadow_descriptor_order_prior_hash,
                                    )
                                )
                                if runtime_shadow_descriptor_order_prior_hash is not None
                                or runtime_shadow_options.get("descriptor_order_prior_hash")
                                is not None
                                else None
                            ),
                            shadow_descriptor_order_tiles_per_expert=int(
                                runtime_shadow_options.get("descriptor_order_tiles_per_expert", 1)
                            ),
                            shadow_descriptor_order_token_window_size=int(
                                runtime_shadow_options.get(
                                    "descriptor_order_token_window_size",
                                    0,
                                )
                            ),
                            shadow_descriptor_order_cache_sizes=_int_tuple_option(
                                runtime_shadow_options,
                                "descriptor_order_cache_sizes",
                                (8, 16, 32),
                            ),
                            shadow_descriptor_order_top_k=int(
                                runtime_shadow_options.get("descriptor_order_top_k", 8)
                            ),
                            shadow_descriptor_order_top_utility_override=int(
                                runtime_shadow_options.get(
                                    "descriptor_order_top_utility_override",
                                    0,
                                )
                            ),
                            shadow_descriptor_order_metrics_mode=str(
                                runtime_shadow_options.get(
                                    "descriptor_order_metrics_mode",
                                    "full",
                                )
                            ),
                            shadow_descriptor_order_event_mode=str(
                                runtime_shadow_options.get(
                                    "descriptor_order_event_mode",
                                    "summary",
                                )
                            ),
                            shadow_descriptor_order_execution_mode=str(
                                runtime_shadow_options.get(
                                    "descriptor_order_execution_mode",
                                    "two_level_group_plan",
                                )
                            ),
                            shadow_descriptor_order_mapping_assertion_mode=str(
                                runtime_shadow_options.get(
                                    "descriptor_order_mapping_assertion_mode",
                                    "off",
                                )
                            ),
                            shadow_descriptor_order_mapping_source=str(
                                runtime_shadow_options.get(
                                    "descriptor_order_mapping_source",
                                    "base_router_select_experts_topk",
                                )
                            ),
                            shadow_descriptor_order_prelaunch_assertion_mode=str(
                                runtime_shadow_options.get(
                                    "descriptor_order_prelaunch_assertion_mode",
                                    "off",
                                )
                            ),
                            shadow_descriptor_order_prelaunch_mapping_source=str(
                                runtime_shadow_options.get(
                                    "descriptor_order_prelaunch_mapping_source",
                                    "moe_runner_quant_method_apply_topk",
                                )
                            ),
                            shadow_descriptor_order_reorder_mvp_enabled=bool(
                                runtime_shadow_options.get(
                                    "descriptor_order_reorder_mvp_enabled",
                                    False,
                                )
                            ),
                            shadow_descriptor_order_reorder_mvp_apply_mode=str(
                                runtime_shadow_options.get(
                                    "descriptor_order_reorder_mvp_apply_mode",
                                    "dry_run",
                                )
                            ),
                            shadow_descriptor_order_reorder_mvp_attribution_mode=str(
                                runtime_shadow_options.get(
                                    "descriptor_order_reorder_mvp_attribution_mode",
                                    "full",
                                )
                            ),
                            shadow_descriptor_order_emit_consumer_handle_events=bool(
                                runtime_shadow_options.get(
                                    "descriptor_order_emit_consumer_handle_events",
                                    True,
                                )
                            ),
                            shadow_descriptor_order_reorder_mvp_require_profitable=bool(
                                runtime_shadow_options.get(
                                    "descriptor_order_reorder_mvp_require_profitable",
                                    True,
                                )
                            ),
                            shadow_descriptor_order_reorder_mvp_layer_allowlist=(
                                runtime_shadow_descriptor_order_layer_allowlist
                            ),
                            shadow_descriptor_order_groups_per_cta=int(
                                runtime_shadow_options.get(
                                    "descriptor_order_groups_per_cta",
                                    8,
                                )
                            ),
                            shadow_descriptor_order_tile_elems=int(
                                runtime_shadow_options.get(
                                    "descriptor_order_tile_elems",
                                    1024,
                                )
                            ),
                            shadow_descriptor_order_device=(
                                int(runtime_shadow_options["descriptor_order_device"])
                                if runtime_shadow_options.get("descriptor_order_device")
                                is not None
                                else None
                            ),
                            shadow_descriptor_order_runtime_gate=(
                                runtime_shadow_descriptor_order_gate
                            ),
                            shadow_descriptor_order_evidence=(
                                runtime_shadow_descriptor_order_evidence
                            ),
                            shadow_descriptor_order_evidence_cache_flush_elems=int(
                                runtime_shadow_options.get(
                                    "descriptor_order_evidence_cache_flush_elems",
                                    0,
                                )
                            ),
                            shadow_descriptor_order_same_multiset_evidence=(
                                bool(
                                    runtime_shadow_options[
                                        "descriptor_order_same_multiset_evidence"
                                    ]
                                )
                                if runtime_shadow_options.get(
                                    "descriptor_order_same_multiset_evidence"
                                )
                                is not None
                                else None
                            ),
                            shadow_descriptor_order_checksum_delta_evidence=(
                                float(
                                    runtime_shadow_options[
                                        "descriptor_order_checksum_delta_evidence"
                                    ]
                                )
                                if runtime_shadow_options.get(
                                    "descriptor_order_checksum_delta_evidence"
                                )
                                is not None
                                else None
                            ),
                            shadow_descriptor_order_event_token_index=int(
                                runtime_shadow_options.get(
                                    "descriptor_order_event_token_index",
                                    -1,
                                )
                            ),
                            shadow_wna16_config_override=(
                                dict(runtime_shadow_options["wna16_config_override"])
                                if runtime_shadow_options.get("wna16_config_override")
                                else None
                            ),
                            shadow_wna16_config_override_preserve_dynamic_nk=bool(
                                runtime_shadow_options.get(
                                    "wna16_config_override_preserve_dynamic_nk",
                                    True,
                                )
                            ),
                            shadow_wna16_config_override_max_tokens=(
                                int(
                                    runtime_shadow_options[
                                        "wna16_config_override_max_tokens"
                                    ]
                                )
                                if runtime_shadow_options.get(
                                    "wna16_config_override_max_tokens"
                                )
                                is not None
                                else None
                            ),
                            shadow_wna16_config_override_route_product=(
                                int(
                                    runtime_shadow_options[
                                        "wna16_config_override_route_product"
                                    ]
                                )
                                if runtime_shadow_options.get(
                                    "wna16_config_override_route_product"
                                )
                                is not None
                                else None
                            ),
                            shadow_wna16_config_override_target_top_k=(
                                int(
                                    runtime_shadow_options[
                                        "wna16_config_override_target_top_k"
                                    ]
                                )
                                if runtime_shadow_options.get(
                                    "wna16_config_override_target_top_k"
                                )
                                is not None
                                else None
                            ),
                            shadow_wna16_kernel_timing_mode=str(
                                runtime_shadow_options.get(
                                    "wna16_kernel_timing_mode",
                                    "host",
                                )
                            ),
                            shadow_emit_wna16_kernel_timing=bool(
                                runtime_shadow_options.get(
                                    "emit_wna16_kernel_timing",
                                    runtime_shadow_options.get("emit_summaries", False),
                                )
                            ),
                            shadow_emit_descriptor_layer_timing=bool(
                                runtime_shadow_options.get(
                                    "emit_descriptor_layer_timing",
                                    True,
                                )
                            ),
                            shadow_emit_decoder_layer_timing=bool(
                                runtime_shadow_options.get(
                                    "emit_decoder_layer_timing",
                                    False,
                                )
                            ),
                            shadow_emit_decoder_component_timing=bool(
                                runtime_shadow_options.get(
                                    "emit_decoder_component_timing",
                                    True,
                                )
                            ),
                            shadow_decoder_component_logging_mode=str(
                                runtime_shadow_options.get(
                                    "decoder_component_logging_mode",
                                    "rows",
                                )
                            ),
                            shadow_emit_moe_substage_timing=bool(
                                runtime_shadow_options.get(
                                    "emit_moe_substage_timing",
                                    True,
                                )
                            ),
                            shadow_moe_substage_logging_mode=str(
                                runtime_shadow_options.get(
                                    "moe_substage_logging_mode",
                                    "rows",
                                )
                            ),
                            shadow_moe_substage_sample_period=int(
                                runtime_shadow_options.get(
                                    "moe_substage_sample_period",
                                    1,
                                )
                            ),
                            shadow_emit_engine_timing=bool(
                                runtime_shadow_options.get(
                                    "emit_engine_timing",
                                    False,
                                )
                            ),
                            shadow_moe_source_timing_mode=str(
                                runtime_shadow_options.get(
                                    "moe_source_timing_mode",
                                    "full",
                                )
                            ),
                            shadow_decoder_source_timing_mode=str(
                                runtime_shadow_options.get(
                                    "decoder_source_timing_mode",
                                    "off",
                                )
                            ),
                            shadow_shared_experts_force_aux_stream=bool(
                                runtime_shadow_options.get(
                                    "shared_experts_force_aux_stream",
                                    False,
                                )
                            ),
                            shadow_shared_expert_output_gate_ablation=str(
                                runtime_shadow_options.get(
                                    "shared_expert_output_gate_ablation",
                                    "off",
                                )
                            ),
                            shadow_shared_expert_output_gate_postprocess=str(
                                runtime_shadow_options.get(
                                    "shared_expert_output_gate_postprocess",
                                    "default",
                                )
                            ),
                            shadow_record_router_topk=bool(
                                runtime_shadow_options.get(
                                    "record_router_topk",
                                    True,
                                )
                            ),
                            shadow_outcome_logging_mode=str(
                                runtime_shadow_options.get(
                                    "outcome_logging_mode",
                                    "full",
                                )
                            ),
                        )
                        for sample_idx, record, input_ids, prompt in chunk:
                            recorder.clear()
                            recorder.request_id = _shadow_request_id(
                                sample_idx=sample_idx,
                                record=record,
                                options=runtime_shadow_options,
                            )
                            recorder.sequence_id = _shadow_sequence_id(
                                record,
                                runtime_shadow_options,
                            )
                            recorder.token_offset = int(
                                runtime_shadow_options.get("token_offset", 0)
                            )
                            set_active_vllm_router_recorder(recorder)
                            set_active_runtime_shadow_controller(runtime_shadow_controller)
                            generate_start_ns = time.perf_counter_ns()
                            generate_elapsed_us = 0.0
                            generate_status = "ok"
                            try:
                                outputs = llm.generate([prompt], sampling, use_tqdm=False)
                            except Exception as exc:
                                generate_status = f"error:{type(exc).__name__}"
                                raise
                            finally:
                                generate_elapsed_us = (
                                    time.perf_counter_ns() - generate_start_ns
                                ) / 1000.0
                                performance["generate_wall_seconds"] += (
                                    generate_elapsed_us / 1_000_000.0
                                )
                                recorder.write_engine_substage_timing(
                                    substage="engine_llm_generate_call",
                                    elapsed_us=generate_elapsed_us,
                                    status=generate_status,
                                )
                                recorder.flush_decoder_component_aggregates()
                                recorder.flush_moe_substage_aggregates()
                                set_active_vllm_router_recorder(None)
                                set_active_runtime_shadow_controller(None)
                            if len(outputs) != 1:
                                msg = f"vLLM returned {len(outputs)} outputs for one prompt."
                                raise RuntimeError(msg)
                            write_start_ns = time.perf_counter_ns()
                            _write_vllm_sample_trace(
                                manifest=manifest,
                                output_dir=output_dir,
                                sample_idx=sample_idx,
                                record=record,
                                input_ids=input_ids,
                                request_output=outputs[0],
                                module_prefix=module_prefix,
                                recorder=recorder,
                            )
                            write_elapsed_us = (
                                time.perf_counter_ns() - write_start_ns
                            ) / 1000.0
                            performance["trace_write_wall_seconds"] += (
                                write_elapsed_us / 1_000_000.0
                            )
                            sample_timing.write(
                                json.dumps(
                                    {
                                        "scope": "sample",
                                        "sample_idx": int(sample_idx),
                                        "record_id": record.get("id", record.get("record_id")),
                                        "input_tokens": int(len(input_ids)),
                                        "requested_output_tokens": int(max_tokens),
                                        "generate_elapsed_us": float(generate_elapsed_us),
                                        "trace_write_elapsed_us": float(write_elapsed_us),
                                        "status": generate_status,
                                    },
                                    ensure_ascii=False,
                                    sort_keys=True,
                                )
                                + "\n"
                            )
                    else:
                        generate_start_ns = time.perf_counter_ns()
                        outputs = llm.generate(
                            [prompt for *_prefix, prompt in chunk],
                            sampling,
                            use_tqdm=False,
                        )
                        chunk_generate_elapsed_us = (
                            time.perf_counter_ns() - generate_start_ns
                        ) / 1000.0
                        performance["generate_wall_seconds"] += (
                            chunk_generate_elapsed_us / 1_000_000.0
                        )
                        if len(outputs) != len(chunk):
                            msg = f"vLLM returned {len(outputs)} outputs for {len(chunk)} prompts."
                            raise RuntimeError(msg)
                        sample_timing.write(
                            json.dumps(
                                {
                                    "scope": "chunk",
                                    "chunk_start": int(chunk_start),
                                    "sample_indices": [
                                        int(sample_idx)
                                        for sample_idx, _record, _input_ids, _prompt in chunk
                                    ],
                                    "sample_count": int(len(chunk)),
                                    "requested_output_tokens": int(len(chunk) * max_tokens),
                                    "generate_elapsed_us": float(chunk_generate_elapsed_us),
                                    "status": "ok",
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                            + "\n"
                        )

                        for (sample_idx, record, input_ids, _prompt), request_output in zip(
                            chunk,
                            outputs,
                            strict=True,
                        ):
                            write_start_ns = time.perf_counter_ns()
                            _write_vllm_sample_trace(
                                manifest=manifest,
                                output_dir=output_dir,
                                sample_idx=sample_idx,
                                record=record,
                                input_ids=input_ids,
                                request_output=request_output,
                                module_prefix=module_prefix,
                                recorder=None,
                            )
                            write_elapsed_us = (
                                time.perf_counter_ns() - write_start_ns
                            ) / 1000.0
                            performance["trace_write_wall_seconds"] += (
                                write_elapsed_us / 1_000_000.0
                            )
                finally:
                    set_active_vllm_router_recorder(None)
                    set_active_runtime_shadow_controller(None)
                    shutdown = getattr(llm, "shutdown", None)
                    if callable(shutdown):
                        shutdown()
                    del llm
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
    finally:
        set_active_runtime_shadow_controller(None)
        if runtime_shadow_controller is not None:
            if bool(runtime_shadow_options.get("flush_pending_as_timeouts", True)):
                runtime_shadow_controller.flush_pending_as_timeouts()
            runtime_shadow_controller.close()

    performance["total_trace_wall_seconds"] = (
        time.perf_counter_ns() - trace_wall_start_ns
    ) / 1_000_000_000.0
    if performance["requested_output_token_count"]:
        performance["generate_seconds_per_requested_output_token"] = (
            performance["generate_wall_seconds"]
            / float(performance["requested_output_token_count"])
        )
        performance["end_to_end_seconds_per_requested_output_token"] = (
            performance["total_trace_wall_seconds"]
            / float(performance["requested_output_token_count"])
        )
    if runtime_shadow_path is not None and runtime_shadow_path.exists():
        aggregate = aggregate_shadow_events(read_shadow_jsonl(runtime_shadow_path))
        performance["runtime_shadow_aggregate"] = aggregate
        performance["runtime_shadow_size_mb"] = (
            float(runtime_shadow_path.stat().st_size) / (1024.0 * 1024.0)
        )
        _add_runtime_shadow_aggregate_to_performance(performance, aggregate)
    if runtime_shadow_controller is not None:
        performance["runtime_shadow_controller_stats"] = (
            runtime_shadow_controller.stats_dict()
        )
    performance_path = output_dir / "performance_summary.json"
    performance_path.write_text(
        json.dumps(performance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return manifest_path
