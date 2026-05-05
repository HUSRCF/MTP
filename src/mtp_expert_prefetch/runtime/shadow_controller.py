from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import torch

from mtp_expert_prefetch.runtime.admission import AdmissionDecisionMasks
from mtp_expert_prefetch.runtime.online_shadow import OnlineShadowLogger
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowOutcomeEvent,
    ShadowPolicyConfig,
    ShadowSummaryEvent,
)


@dataclass(frozen=True)
class PendingShadowDecision:
    """Action masks needed to enrich a later true-router outcome."""

    full_fetch_mask: torch.Tensor
    metadata_mask: torch.Tensor
    premap_mask: torch.Tensor
    skip_mask: torch.Tensor
    ready_mask: torch.Tensor


class RuntimeShadowController:
    """Join runtime action summaries and true-router outcomes by event id.

    The controller is shadow-only: it records policy decisions and outcomes,
    but never performs prefetching, cache mutation, scheduling, or routing
    changes. Runtime code should call `write_action_summary` when the shadow
    action decision is made, and can pass this object as the
    `VllmRouterRecorder.shadow_outcome_sink`; the recorder's true-router
    outcome will then be enriched with later-used and ready-mask metrics.
    """

    def __init__(
        self,
        logger: OnlineShadowLogger,
        *,
        max_pending: int = 100_000,
    ) -> None:
        self.logger = logger
        self.max_pending = max(0, int(max_pending))
        self._pending: OrderedDict[str, PendingShadowDecision] = OrderedDict()

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def write_action_summary(
        self,
        *,
        event_id: ShadowEventId,
        policy: ShadowPolicyConfig,
        decisions: AdmissionDecisionMasks,
        base_mask: torch.Tensor | None = None,
        ready_mask: torch.Tensor | None = None,
        **summary_kwargs: Any,
    ) -> ShadowSummaryEvent:
        """Write a summary event and cache masks for later outcome joining.

        `ready_mask` should be the queue/cache-aware ready-before-demand mask
        when available. If it is omitted, the controller deliberately records
        no ready experts rather than treating full-fetch intent as ready. This
        preserves the semantic boundary between "issued/actioned" and "ready".
        """

        event = self.logger.write_action_summary(
            event_id=event_id,
            policy=policy,
            decisions=decisions,
            **summary_kwargs,
        )
        self._pending[event_id.key] = _pending_from_decisions(
            decisions=decisions,
            base_mask=base_mask,
            ready_mask=ready_mask,
        )
        self._pending.move_to_end(event_id.key)
        self._evict_if_needed()
        return event

    def write_outcome(self, event: ShadowOutcomeEvent) -> None:
        """Enrich and write a true-router outcome.

        This method matches the `RouterShadowOutcomeSink` protocol used by the
        vLLM router recorder. If the corresponding action summary is missing,
        the original event is written unchanged so outcome-only logging remains
        safe.
        """

        pending = self._pending.pop(event.event_id.key, None)
        if pending is None:
            self.logger.write_outcome(event)
            return
        self.logger.write_outcome(_enrich_outcome(event, pending))

    def write_router_outcome(
        self,
        *,
        event_id: ShadowEventId,
        true_topk_experts: list[int],
        true_topk_weights: list[float],
    ) -> None:
        """Convenience entry point for non-vLLM runtime hooks."""

        total = float(sum(max(0.0, float(value)) for value in true_topk_weights))
        event = ShadowOutcomeEvent(
            event_id=event_id,
            true_topk_experts=[int(value) for value in true_topk_experts],
            true_topk_weights=[float(value) for value in true_topk_weights],
            full_fetch_used_count=0,
            metadata_later_used_count=0,
            premap_later_used_count=0,
            skip_would_have_used_count=0,
            covered_mass=0.0,
            miss_mass=total,
            top1_ready=False,
            weighted_top1_miss=(
                float(true_topk_weights[0]) if true_topk_weights else 0.0
            ),
        )
        self.write_outcome(event)

    def flush(self) -> None:
        self.logger.flush()

    def close(self) -> None:
        self.logger.close()

    def aggregate(self) -> dict[str, Any]:
        return self.logger.aggregate()

    def __enter__(self) -> RuntimeShadowController:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _evict_if_needed(self) -> None:
        if self.max_pending <= 0:
            self._pending.clear()
            return
        while len(self._pending) > self.max_pending:
            self._pending.popitem(last=False)


def _pending_from_decisions(
    *,
    decisions: AdmissionDecisionMasks,
    base_mask: torch.Tensor | None,
    ready_mask: torch.Tensor | None,
) -> PendingShadowDecision:
    action_masks = decisions.action_masks()
    full_fetch = _expert_mask(action_masks["full_fetch"])
    metadata = _expert_mask(action_masks["metadata"])
    premap = _expert_mask(action_masks["premap"])
    skipped = _expert_mask(action_masks["skip"])
    if ready_mask is None:
        ready = torch.zeros_like(full_fetch, dtype=torch.bool)
    else:
        ready = _expert_mask(ready_mask)
    if base_mask is not None and ready_mask is not None:
        # A provided ready mask is authoritative but often already includes the
        # protected transition base. OR-ing the base keeps callers robust when
        # they pass only a ready MTP-extra mask.
        ready = ready | _expert_mask(base_mask)
    return PendingShadowDecision(
        full_fetch_mask=full_fetch,
        metadata_mask=metadata,
        premap_mask=premap,
        skip_mask=skipped,
        ready_mask=ready,
    )


def _enrich_outcome(
    event: ShadowOutcomeEvent,
    pending: PendingShadowDecision,
) -> ShadowOutcomeEvent:
    true_ids = [int(value) for value in event.true_topk_experts]
    true_weights = [float(value) for value in event.true_topk_weights]
    full_fetch_used = 0
    metadata_later_used = 0
    premap_later_used = 0
    skip_would_have_used = 0
    covered_mass = 0.0
    total_mass = 0.0
    for expert_id, weight in zip(true_ids, true_weights):
        nonnegative_weight = max(0.0, float(weight))
        total_mass += nonnegative_weight
        if _mask_contains(pending.full_fetch_mask, expert_id):
            full_fetch_used += 1
        if _mask_contains(pending.metadata_mask, expert_id):
            metadata_later_used += 1
        if _mask_contains(pending.premap_mask, expert_id):
            premap_later_used += 1
        if _mask_contains(pending.skip_mask, expert_id):
            skip_would_have_used += 1
        if _mask_contains(pending.ready_mask, expert_id):
            covered_mass += nonnegative_weight
    top1_ready = bool(true_ids and _mask_contains(pending.ready_mask, true_ids[0]))
    weighted_top1_miss = (
        0.0 if top1_ready or not true_weights else float(true_weights[0])
    )
    return ShadowOutcomeEvent(
        event_id=event.event_id,
        true_topk_experts=true_ids,
        true_topk_weights=true_weights,
        full_fetch_used_count=full_fetch_used,
        metadata_later_used_count=metadata_later_used,
        premap_later_used_count=premap_later_used,
        skip_would_have_used_count=skip_would_have_used,
        covered_mass=covered_mass,
        miss_mass=max(0.0, total_mass - covered_mass),
        top1_ready=top1_ready,
        weighted_top1_miss=weighted_top1_miss,
    )


def _expert_mask(mask: torch.Tensor) -> torch.Tensor:
    bool_mask = mask.detach().to(dtype=torch.bool, device="cpu")
    if bool_mask.ndim == 0:
        return bool_mask.reshape(1)
    if bool_mask.ndim == 1:
        return bool_mask.clone()
    return bool_mask.reshape(-1, bool_mask.shape[-1]).any(dim=0)


def _mask_contains(mask: torch.Tensor, expert_id: int) -> bool:
    return 0 <= int(expert_id) < int(mask.numel()) and bool(mask[int(expert_id)].item())
