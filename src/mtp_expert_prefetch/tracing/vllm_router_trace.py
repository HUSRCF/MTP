from __future__ import annotations

import gc
import importlib.util
import importlib
import inspect
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Any, Protocol

import torch

from mtp_expert_prefetch.runtime.admission import AdmissionDecisionMasks
from mtp_expert_prefetch.runtime.descriptor_order import (
    DescriptorOrderReport,
    build_layer_prior_plan_report_from_router_topk,
    hash_layer_tile_prior,
)
from mtp_expert_prefetch.runtime.online_shadow import OnlineShadowLogger
from mtp_expert_prefetch.runtime.shadow_controller import RuntimeShadowController
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowOutcomeAggregateEvent,
    ShadowOutcomeEvent,
    ShadowPolicyConfig,
    ShadowSummaryEvent,
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
    shadow_descriptor_order_event_token_index: int = -1
    shadow_outcome_logging_mode: str = "full"
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
        outcome_mode = self._resolved_outcome_logging_mode()
        if self.shadow_emit_transition_summary:
            # Transition summaries require per-token outcomes for same-event
            # ready-mask joins. Keep the debug/full path in that mode.
            outcome_mode = "full"
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
        if sink is None or prior is None or not hasattr(sink, "write_descriptor_order_summary"):
            return
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
        event_id = ShadowEventId(
            request_id=str(self.request_id),
            sequence_id=int(self.sequence_id),
            token_index=int(self.shadow_descriptor_order_event_token_index),
            layer=int(layer_id),
        )
        sink.write_descriptor_order_summary(
            event_id=event_id,
            policy=policy,
            descriptor_report=descriptor_report,
            baseline_order_hash=baseline_order_hash,
            candidate_construction_us=stream_build_us,
            counter_update_us=counter_update_us,
            decision_us=decision_us,
        )

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
            if hasattr(self, "mlp"):
                layer_id = getattr(self, "layer_idx", None)
                self.mlp._mtp_trace_layer_id = layer_id
                experts = getattr(self.mlp, "experts", None)
                if experts is not None:
                    experts._mtp_trace_layer_id = layer_id
                router = getattr(experts, "router", None)
                if router is not None:
                    router._mtp_trace_layer_id = layer_id

        return decoder_init_with_trace_layer

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

    for decoder_class in decoder_classes:
        decoder_class.__init__ = _make_decoder_init_with_trace_layer(decoder_class.__init__)

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
            if recorder is not None and gate is not None and layer_id is not None:
                trace_router_logits, _ = gate(hidden_states)
                recorder.record(
                    layer_id=int(layer_id),
                    router_logits=trace_router_logits,
                )
            return original_fused_moe_forward_impl(
                self,
                hidden_states,
                router_logits,
            )

        fused_moe_layer.FusedMoE.forward_impl = fused_moe_forward_impl_with_trace

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
    manifest_path = output_dir / "manifest.jsonl"
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
        "chunk_count": 0,
        "runtime_shadow_enabled": bool(runtime_shadow_options.get("enabled", False)),
        "runtime_shadow_emit_descriptor_order_summaries": bool(
            runtime_shadow_options.get("emit_descriptor_order_summaries", False)
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
        "runtime_shadow_descriptor_order_metrics_mode": (
            str(runtime_shadow_options.get("descriptor_order_metrics_mode"))
            if runtime_shadow_options.get("descriptor_order_metrics_mode") is not None
            else None
        ),
    }
    try:
        with manifest_path.open("w", encoding="utf-8") as manifest:
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
                            shadow_descriptor_order_event_token_index=int(
                                runtime_shadow_options.get(
                                    "descriptor_order_event_token_index",
                                    -1,
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
                            try:
                                outputs = llm.generate([prompt], sampling, use_tqdm=False)
                            finally:
                                performance["generate_wall_seconds"] += (
                                    time.perf_counter_ns() - generate_start_ns
                                ) / 1_000_000_000.0
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
                            performance["trace_write_wall_seconds"] += (
                                time.perf_counter_ns() - write_start_ns
                            ) / 1_000_000_000.0
                    else:
                        generate_start_ns = time.perf_counter_ns()
                        outputs = llm.generate(
                            [prompt for *_prefix, prompt in chunk],
                            sampling,
                            use_tqdm=False,
                        )
                        performance["generate_wall_seconds"] += (
                            time.perf_counter_ns() - generate_start_ns
                        ) / 1_000_000_000.0
                        if len(outputs) != len(chunk):
                            msg = f"vLLM returned {len(outputs)} outputs for {len(chunk)} prompts."
                            raise RuntimeError(msg)

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
                            performance["trace_write_wall_seconds"] += (
                                time.perf_counter_ns() - write_start_ns
                            ) / 1_000_000_000.0
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
    performance_path = output_dir / "performance_summary.json"
    performance_path.write_text(
        json.dumps(performance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return manifest_path
