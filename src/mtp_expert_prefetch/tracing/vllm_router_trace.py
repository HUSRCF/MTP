from __future__ import annotations

import gc
import importlib.util
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import torch

from mtp_expert_prefetch.runtime.admission import AdmissionDecisionMasks
from mtp_expert_prefetch.runtime.online_shadow import OnlineShadowLogger
from mtp_expert_prefetch.runtime.shadow_controller import RuntimeShadowController
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowOutcomeEvent,
    ShadowPolicyConfig,
    ShadowSummaryEvent,
)
from mtp_expert_prefetch.tracing.router_mtp import _load_trace_texts
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path


class RouterShadowOutcomeSink(Protocol):
    def write_outcome(self, event: ShadowOutcomeEvent) -> None: ...


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
    request_id: str = "vllm"
    sequence_id: int = 0
    token_offset: int = 0
    calls: list[VllmRouterCall] = field(default_factory=list)

    def clear(self) -> None:
        self.calls.clear()

    def record(self, *, layer_id: int | None, router_logits: torch.Tensor) -> None:
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

        ids = topk_ids.detach().cpu().to(torch.long)
        weights = topk_weights.detach().cpu().to(torch.float32)
        if ids.ndim != 2 or weights.shape != ids.shape:
            return
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
        num_experts = max(int(self.shadow_num_experts), int(previous_topk_ids.max().item()) + 1)
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
            topk = torch.topk(
                transition_scores,
                k=max(1, min(transition_count, num_experts)),
                dim=-1,
            ).indices
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
_PATCHED = False


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
    for expert_id, weight in zip(ids.tolist(), weights.tolist()):
        expert_idx = int(expert_id)
        if 0 <= expert_idx < num_experts:
            feature[expert_idx] += max(0.0, float(weight))
    return feature @ matrix[0, int(layer_id), :num_experts, :num_experts]


def patch_vllm_qwen35_moe_router_trace() -> None:
    """Patch vLLM Qwen3.5/Qwen3.6 MoE blocks to record router top-k.

    This is intentionally a runtime monkey patch so the project can keep using
    upstream vLLM as an optional backend. The patch is for offline trace smoke
    first; server/continuous batching needs stricter request-id bookkeeping.
    """
    global _PATCHED
    if _PATCHED:
        return

    from vllm.model_executor.layers.fused_moe.router import base_router
    from vllm.model_executor.models import qwen3_5, qwen3_next

    original_decoder_init = qwen3_5.Qwen3_5DecoderLayer.__init__
    original_moe_forward = qwen3_next.Qwen3NextSparseMoeBlock.forward
    original_router_set_capture_fn = base_router.BaseRouter.set_capture_fn
    original_router_select_experts = base_router.BaseRouter.select_experts

    def decoder_init_with_trace_layer(self, *args: Any, **kwargs: Any) -> None:
        original_decoder_init(self, *args, **kwargs)
        if hasattr(self, "mlp"):
            layer_id = getattr(self, "layer_idx", None)
            self.mlp._mtp_trace_layer_id = layer_id
            experts = getattr(self.mlp, "experts", None)
            router = getattr(experts, "router", None)
            if router is not None:
                router._mtp_trace_layer_id = layer_id

    def moe_forward_with_trace(self, hidden_states: torch.Tensor) -> torch.Tensor:
        recorder = get_active_vllm_router_recorder()
        if recorder is None or self.experts.is_internal_router:
            return original_moe_forward(self, hidden_states)

        orig_shape = hidden_states.shape
        num_tokens, hidden_dim = hidden_states.shape
        routed_states = hidden_states.view(-1, hidden_dim)

        if self.is_sequence_parallel:
            routed_states = qwen3_next.sequence_parallel_chunk(routed_states)

        router_logits, _ = self.gate(routed_states)
        recorder.record(
            layer_id=getattr(self, "_mtp_trace_layer_id", None),
            router_logits=router_logits,
        )
        final_hidden_states = self.experts(
            hidden_states=routed_states,
            router_logits=router_logits,
        )

        if self.is_sequence_parallel:
            final_hidden_states = qwen3_next.tensor_model_parallel_all_gather(
                final_hidden_states, 0
            )
            final_hidden_states = final_hidden_states[:num_tokens]

        return final_hidden_states.view(orig_shape)

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
    ) -> tuple[torch.Tensor, torch.Tensor]:
        topk_weights, topk_ids = original_router_select_experts(
            self,
            hidden_states,
            router_logits,
        )
        recorder = get_active_vllm_router_recorder()
        layer_id = getattr(self, "_mtp_trace_layer_id", None)
        if recorder is not None and layer_id is not None:
            recorder.record_topk(
                layer_id=layer_id,
                topk_ids=topk_ids,
                topk_weights=topk_weights,
                oracle_router_logits=router_logits,
                router_input_hidden=hidden_states,
            )
        return topk_weights, topk_ids

    qwen3_5.Qwen3_5DecoderLayer.__init__ = decoder_init_with_trace_layer
    qwen3_next.Qwen3NextSparseMoeBlock.forward = moe_forward_with_trace
    base_router.BaseRouter.set_capture_fn = router_set_capture_fn_with_trace_layer
    base_router.BaseRouter.select_experts = router_select_experts_with_trace
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
    trace_source = (
        "vllm_router_logits_recorder" if has_recorder_trace else "vllm_return_routed_experts"
    )

    if has_recorder_trace:
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
    )
    return RuntimeShadowController(
        logger,
        max_pending=int(options.get("max_pending", 100_000)),
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

    sampling = SamplingParams(max_tokens=max_tokens, temperature=0.0)
    module_prefix = str(
        trace_options.get("router_module_prefix", "model.language_model")
    )
    token_source_input_ids = _load_token_source_input_ids(
        trace_options.get("token_source_manifest"),
        project_root=project_root,
    )
    prepared_records: list[tuple[int, dict[str, Any], list[int], Any]] = []
    for sample_idx, record in enumerate(texts):
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
    runtime_shadow_transition_matrix = _load_runtime_shadow_transition_matrix(
        options=runtime_shadow_options,
        project_root=project_root,
    )
    manifest_path = output_dir / "manifest.jsonl"
    try:
        with manifest_path.open("w", encoding="utf-8") as manifest:
            for chunk_start in range(0, len(prepared_records), engine_chunk_size):
                chunk = prepared_records[chunk_start : chunk_start + engine_chunk_size]
                llm = LLM(**llm_kwargs)
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
                            try:
                                outputs = llm.generate([prompt], sampling, use_tqdm=False)
                            finally:
                                set_active_vllm_router_recorder(None)
                                set_active_runtime_shadow_controller(None)
                            if len(outputs) != 1:
                                msg = f"vLLM returned {len(outputs)} outputs for one prompt."
                                raise RuntimeError(msg)
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
                    else:
                        outputs = llm.generate(
                            [prompt for *_prefix, prompt in chunk],
                            sampling,
                            use_tqdm=False,
                        )
                        if len(outputs) != len(chunk):
                            msg = f"vLLM returned {len(outputs)} outputs for {len(chunk)} prompts."
                            raise RuntimeError(msg)

                        for (sample_idx, record, input_ids, _prompt), request_output in zip(
                            chunk,
                            outputs,
                            strict=True,
                        ):
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

    return manifest_path
