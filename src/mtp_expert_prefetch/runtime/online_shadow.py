from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mtp_expert_prefetch.runtime.admission import AdmissionDecisionMasks
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowOutcomeEvent,
    ShadowPolicyConfig,
    ShadowSummaryEvent,
    aggregate_shadow_events,
    read_shadow_jsonl,
)


class OnlineShadowLogger:
    """Append-only runtime shadow logger using the canonical JSONL schema.

    Serving/runtime integrations should write one `ShadowSummaryEvent` when an
    action decision is made and one `ShadowOutcomeEvent` after the true router
    result is known. This class intentionally does not make policy decisions;
    it only preserves the schema used by offline replay.
    """

    def __init__(self, path: str | Path, *, flush_every: int = 1) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.flush_every = max(1, int(flush_every))
        self._handle = self.path.open("a", encoding="utf-8")
        self._pending = 0
        self._closed = False

    def write_summary(self, event: ShadowSummaryEvent) -> None:
        self.write_event(event)

    def write_action_summary(
        self,
        *,
        event_id: ShadowEventId,
        policy: ShadowPolicyConfig,
        decisions: AdmissionDecisionMasks,
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
    ) -> ShadowSummaryEvent:
        event = build_shadow_summary_from_decisions(
            event_id=event_id,
            policy=policy,
            decisions=decisions,
            transition_topk_count=transition_topk_count,
            mtp_requested_count=mtp_requested_count,
            expert_bytes=expert_bytes,
            metadata_bytes=metadata_bytes,
            premap_bytes=premap_bytes,
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
        self.write_summary(event)
        return event

    def write_outcome(self, event: ShadowOutcomeEvent) -> None:
        self.write_event(event)

    def write_event(self, event: ShadowSummaryEvent | ShadowOutcomeEvent | dict[str, Any]) -> None:
        if self._closed:
            msg = "Cannot write to a closed OnlineShadowLogger."
            raise RuntimeError(msg)
        payload = event.as_dict() if hasattr(event, "as_dict") else dict(event)
        self._handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        self._pending += 1
        if self._pending >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        if self._closed:
            return
        self._handle.flush()
        self._pending = 0

    def close(self) -> None:
        if self._closed:
            return
        self.flush()
        self._handle.close()
        self._closed = True

    def aggregate(self) -> dict[str, Any]:
        self.flush()
        return aggregate_shadow_events(read_shadow_jsonl(self.path))

    def __enter__(self) -> OnlineShadowLogger:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()


def build_shadow_summary_from_decisions(
    *,
    event_id: ShadowEventId,
    policy: ShadowPolicyConfig,
    decisions: AdmissionDecisionMasks,
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
) -> ShadowSummaryEvent:
    action_masks = decisions.action_masks()
    action_counts = {
        action: _mask_count(mask) for action, mask in action_masks.items()
    }
    reason_counts = {
        reason: _mask_count(mask) for reason, mask in decisions.reason_masks().items()
    }
    action_reason_counts = {}
    for reason, reason_mask in decisions.reason_masks().items():
        action_reason_counts[str(reason)] = {
            str(action): _mask_count(reason_mask & action_mask)
            for action, action_mask in action_masks.items()
        }
    return ShadowSummaryEvent(
        event_id=event_id,
        policy=policy,
        transition_topk_count=int(transition_topk_count),
        mtp_requested_count=int(mtp_requested_count),
        full_fetch_count=action_counts["full_fetch"],
        metadata_count=action_counts["metadata"],
        premap_count=action_counts["premap"],
        skip_count=action_counts["skip"],
        full_fetch_payload_bytes=action_counts["full_fetch"] * int(expert_bytes),
        metadata_actual_bytes=action_counts["metadata"] * int(metadata_bytes),
        premap_actual_bytes=action_counts["premap"] * int(premap_bytes),
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
        reason_counts=reason_counts,
        action_reason_counts=action_reason_counts,
    )


def _mask_count(mask: Any) -> int:
    return int(mask.bool().sum().item())
