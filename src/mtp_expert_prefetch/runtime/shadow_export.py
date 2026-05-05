from __future__ import annotations

from collections.abc import Iterable

import torch

from mtp_expert_prefetch.runtime.admission import AdmissionDecisionMasks
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowOutcomeEvent,
    ShadowPolicyConfig,
    ShadowSummaryEvent,
)


def iter_shadow_summary_outcome_events(
    *,
    base_mask: torch.Tensor,
    decisions: AdmissionDecisionMasks,
    target_mass: torch.Tensor,
    policy: ShadowPolicyConfig,
    request_id: str = "offline",
    token_sample_indices: torch.Tensor | None = None,
    transition_topk_count: int = 32,
    mtp_requested_count: int = 64,
    expert_bytes: int = 1_650_000,
    metadata_bytes: int = 65_536,
    premap_bytes: int = 4_096,
    decision_us: float | None = None,
    candidate_construction_us: float | None = None,
    admission_decision_us: float | None = None,
    counter_update_us: float | None = None,
    logging_us: float | None = None,
    mtp_delay_ms: float | None = None,
    estimated_lead_ms: float | None = None,
    transition_ready_rate: float | None = None,
    mtp_ready_fraction: float | None = None,
    bandwidth_gbps: float | None = None,
    layer_ms: float | None = None,
    cache_pressure: float | None = None,
    queue_pressure: float | None = None,
) -> Iterable[ShadowSummaryEvent | ShadowOutcomeEvent]:
    """Yield action-level shadow summary/outcome events for a tensor replay.

    This helper is intentionally side-effect free. It converts the same
    canonical action masks used by the event simulator into the runtime shadow
    JSONL schema, so offline replays and online shadow logs can be compared with
    the same aggregation code.
    """
    _validate_replay_shapes(base_mask=base_mask, decisions=decisions, target_mass=target_mass)
    action_masks = decisions.action_masks()
    ready_mask = base_mask.bool() | action_masks["full_fetch"].bool()
    demand = target_mass.float().gt(0.0)
    sample_ids = _sample_ids_for_tokens(base_mask, token_sample_indices)

    token_count, future_count, layer_count, _ = base_mask.shape
    for token_idx in range(token_count):
        sequence_id = int(sample_ids[token_idx].item())
        for future_idx in range(future_count):
            logical_token_idx = int(token_idx + future_idx)
            for layer_idx in range(layer_count):
                event_id = ShadowEventId(
                    request_id=request_id,
                    sequence_id=sequence_id,
                    token_index=logical_token_idx,
                    layer=int(layer_idx),
                )
                action_slice = {
                    name: mask[token_idx, future_idx, layer_idx].bool()
                    for name, mask in action_masks.items()
                }
                summary = ShadowSummaryEvent(
                    event_id=event_id,
                    policy=policy,
                    transition_topk_count=int(transition_topk_count),
                    mtp_requested_count=int(mtp_requested_count),
                    full_fetch_count=_mask_count(action_slice["full_fetch"]),
                    metadata_count=_mask_count(action_slice["metadata"]),
                    premap_count=_mask_count(action_slice["premap"]),
                    skip_count=_mask_count(action_slice["skip"]),
                    full_fetch_payload_bytes=_mask_count(action_slice["full_fetch"])
                    * int(expert_bytes),
                    metadata_actual_bytes=_mask_count(action_slice["metadata"])
                    * int(metadata_bytes),
                    premap_actual_bytes=_mask_count(action_slice["premap"]) * int(premap_bytes),
                    decision_us=decision_us,
                    candidate_construction_us=candidate_construction_us,
                    admission_decision_us=admission_decision_us,
                    counter_update_us=counter_update_us,
                    logging_us=logging_us,
                    mtp_delay_ms=mtp_delay_ms,
                    estimated_lead_ms=estimated_lead_ms,
                    transition_ready_rate=transition_ready_rate,
                    mtp_ready_fraction=mtp_ready_fraction,
                    bandwidth_gbps=bandwidth_gbps,
                    layer_ms=layer_ms,
                    cache_pressure=cache_pressure,
                    queue_pressure=queue_pressure,
                )
                yield summary

                target_slice = target_mass[token_idx, future_idx, layer_idx].float()
                demand_slice = demand[token_idx, future_idx, layer_idx]
                ready_slice = ready_mask[token_idx, future_idx, layer_idx]
                sorted_ids = torch.argsort(target_slice, descending=True)
                true_ids = sorted_ids[demand_slice.gather(0, sorted_ids)].tolist()
                true_weights = target_slice[true_ids].tolist() if true_ids else []
                top1_id = int(true_ids[0]) if true_ids else None
                top1_weight = float(true_weights[0]) if true_weights else 0.0
                covered_mass = float(target_slice[ready_slice].sum().item())
                total_mass = float(target_slice.clamp_min(0.0).sum().item())
                top1_ready = bool(top1_id is not None and ready_slice[top1_id].item())
                outcome = ShadowOutcomeEvent(
                    event_id=event_id,
                    true_topk_experts=[int(item) for item in true_ids],
                    true_topk_weights=[float(item) for item in true_weights],
                    full_fetch_used_count=_mask_count(action_slice["full_fetch"] & demand_slice),
                    metadata_later_used_count=_mask_count(action_slice["metadata"] & demand_slice),
                    premap_later_used_count=_mask_count(action_slice["premap"] & demand_slice),
                    skip_would_have_used_count=_mask_count(action_slice["skip"] & demand_slice),
                    covered_mass=covered_mass,
                    miss_mass=max(0.0, total_mass - covered_mass),
                    top1_ready=top1_ready,
                    weighted_top1_miss=0.0 if top1_ready else top1_weight,
                )
                yield outcome


def _validate_replay_shapes(
    *,
    base_mask: torch.Tensor,
    decisions: AdmissionDecisionMasks,
    target_mass: torch.Tensor,
) -> None:
    if base_mask.shape != target_mass.shape:
        msg = (
            "base_mask and target_mass must have the same shape, got "
            f"{tuple(base_mask.shape)} and {tuple(target_mass.shape)}."
        )
        raise ValueError(msg)
    if base_mask.ndim != 4:
        msg = f"Expected [tokens, future, layers, experts], got {tuple(base_mask.shape)}."
        raise ValueError(msg)
    for action, mask in decisions.action_masks().items():
        if mask.shape != base_mask.shape:
            msg = (
                f"Action mask {action!r} must match base_mask shape, got "
                f"{tuple(mask.shape)} and {tuple(base_mask.shape)}."
            )
            raise ValueError(msg)


def _sample_ids_for_tokens(
    reference: torch.Tensor,
    token_sample_indices: torch.Tensor | None,
) -> torch.Tensor:
    token_count = int(reference.shape[0])
    if token_sample_indices is None:
        return torch.zeros(token_count, dtype=torch.long)
    sample_ids = token_sample_indices.to(dtype=torch.long, device="cpu").flatten()
    if int(sample_ids.numel()) != token_count:
        msg = (
            "token_sample_indices length must match token dimension, got "
            f"{int(sample_ids.numel())} and {token_count}."
        )
        raise ValueError(msg)
    return sample_ids


def _mask_count(mask: torch.Tensor) -> int:
    return int(mask.bool().sum().item())
