from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Literal


ShadowAction = Literal["full_fetch", "metadata", "premap", "skip"]
ShadowJoinStatus = Literal["joined", "outcome_only", "summary_only_timeout"]


@dataclass(frozen=True)
class ShadowEventId:
    request_id: str
    sequence_id: int
    token_index: int
    layer: int

    @property
    def key(self) -> str:
        return (
            f"{self.request_id}:{int(self.sequence_id)}:"
            f"{int(self.token_index)}:{int(self.layer)}"
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["shadow_event_id"] = self.key
        return payload


@dataclass(frozen=True)
class ShadowPolicyConfig:
    policy_mode: str
    optimization_goal: str
    action_keep_fraction: float
    metadata_score_ratio: float
    full_fetch_max_extra: int
    metadata_max_extra: int
    premap_max_extra: int
    threshold_metadata_id: str | None = None
    policy_reason: str | None = None
    allow_full_mtp_fetch: bool | None = None
    allow_mtp_metadata: bool | None = None
    allow_mtp_premap: bool | None = None
    descriptor_order_policy: str | None = None
    descriptor_order_prior_id: str | None = None
    descriptor_order_prior_hash: str | None = None
    descriptor_order_top_utility_override: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShadowSummaryEvent:
    event_id: ShadowEventId
    policy: ShadowPolicyConfig
    transition_topk_count: int
    mtp_requested_count: int
    full_fetch_count: int
    metadata_count: int
    premap_count: int
    skip_count: int
    full_fetch_payload_bytes: int
    metadata_actual_bytes: int
    premap_actual_bytes: int
    decision_us: float | None = None
    candidate_construction_us: float | None = None
    admission_decision_us: float | None = None
    counter_update_us: float | None = None
    logging_us: float | None = None
    mtp_delay_ms: float | None = None
    estimated_lead_ms: float | None = None
    transition_ready_rate: float | None = None
    mtp_ready_fraction: float | None = None
    bandwidth_gbps: float | None = None
    layer_ms: float | None = None
    cache_pressure: float | None = None
    queue_pressure: float | None = None
    reason_counts: dict[str, int] | None = None
    action_reason_counts: dict[str, dict[str, int]] | None = None
    descriptor_order_build_us: float | None = None
    descriptor_tile_multiset_hash: str | None = None
    descriptor_order_hash: str | None = None
    descriptor_order_metrics: dict[str, Any] | None = None
    descriptor_tile_request_count: int | None = None
    descriptor_unique_b_tiles: int | None = None
    descriptor_same_multiset: bool | None = None
    descriptor_order_changed: bool | None = None
    descriptor_order_prior_id: str | None = None
    descriptor_order_prior_hash: str | None = None
    descriptor_order_lru_at_8: float | None = None
    descriptor_order_lru_at_16: float | None = None
    descriptor_order_hit_rate: float | None = None
    descriptor_reuse_distance_mean: float | None = None
    descriptor_unique_tiles_per_window_mean: float | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "event_type": "summary",
            **self.event_id.as_dict(),
            **self.policy.as_dict(),
            "transition_topk_count": int(self.transition_topk_count),
            "mtp_requested_count": int(self.mtp_requested_count),
            "full_fetch_count": int(self.full_fetch_count),
            "metadata_count": int(self.metadata_count),
            "premap_count": int(self.premap_count),
            "skip_count": int(self.skip_count),
            "full_fetch_payload_bytes": int(self.full_fetch_payload_bytes),
            "metadata_actual_bytes": int(self.metadata_actual_bytes),
            "premap_actual_bytes": int(self.premap_actual_bytes),
        }
        _put_optional(payload, "decision_us", self.decision_us)
        _put_optional(payload, "candidate_construction_us", self.candidate_construction_us)
        _put_optional(payload, "admission_decision_us", self.admission_decision_us)
        _put_optional(payload, "counter_update_us", self.counter_update_us)
        _put_optional(payload, "logging_us", self.logging_us)
        _put_optional(payload, "mtp_delay_ms", self.mtp_delay_ms)
        _put_optional(payload, "estimated_lead_ms", self.estimated_lead_ms)
        _put_optional(payload, "transition_ready_rate", self.transition_ready_rate)
        _put_optional(payload, "mtp_ready_fraction", self.mtp_ready_fraction)
        _put_optional(payload, "bandwidth_gbps", self.bandwidth_gbps)
        _put_optional(payload, "layer_ms", self.layer_ms)
        _put_optional(payload, "cache_pressure", self.cache_pressure)
        _put_optional(payload, "queue_pressure", self.queue_pressure)
        _put_optional(payload, "descriptor_order_build_us", self.descriptor_order_build_us)
        _put_optional(payload, "descriptor_tile_multiset_hash", self.descriptor_tile_multiset_hash)
        _put_optional(payload, "descriptor_order_hash", self.descriptor_order_hash)
        _put_optional(payload, "descriptor_tile_request_count", self.descriptor_tile_request_count)
        _put_optional(payload, "descriptor_unique_b_tiles", self.descriptor_unique_b_tiles)
        _put_optional(payload, "descriptor_same_multiset", self.descriptor_same_multiset)
        _put_optional(payload, "descriptor_order_changed", self.descriptor_order_changed)
        _put_optional(payload, "descriptor_order_prior_id", self.descriptor_order_prior_id)
        _put_optional(payload, "descriptor_order_prior_hash", self.descriptor_order_prior_hash)
        _put_optional(payload, "descriptor_order_lru_at_8", self.descriptor_order_lru_at_8)
        _put_optional(payload, "descriptor_order_lru_at_16", self.descriptor_order_lru_at_16)
        _put_optional(payload, "descriptor_order_hit_rate", self.descriptor_order_hit_rate)
        _put_optional(payload, "descriptor_reuse_distance_mean", self.descriptor_reuse_distance_mean)
        _put_optional(
            payload,
            "descriptor_unique_tiles_per_window_mean",
            self.descriptor_unique_tiles_per_window_mean,
        )
        if self.descriptor_order_metrics is not None:
            payload["descriptor_order_metrics"] = self.descriptor_order_metrics
        if self.reason_counts is not None:
            payload["reason_counts"] = {
                str(key): int(value) for key, value in self.reason_counts.items()
            }
        if self.action_reason_counts is not None:
            payload["action_reason_counts"] = {
                str(reason): {
                    str(action): int(count) for action, count in row.items()
                }
                for reason, row in self.action_reason_counts.items()
            }
        return payload


@dataclass(frozen=True)
class ShadowCandidateEvent:
    event_id: ShadowEventId
    expert_id: int
    source: str
    action: ShadowAction
    reason: str
    is_novel: bool
    in_transition_topk: bool
    mtp_score: float | None = None
    rank: int | None = None
    utility_score: float | None = None
    threshold: float | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "event_type": "candidate",
            **self.event_id.as_dict(),
            "expert_id": int(self.expert_id),
            "source": self.source,
            "action": self.action,
            "reason": self.reason,
            "is_novel": bool(self.is_novel),
            "in_transition_topk": bool(self.in_transition_topk),
        }
        _put_optional(payload, "mtp_score", self.mtp_score)
        _put_optional(payload, "rank", self.rank)
        _put_optional(payload, "utility_score", self.utility_score)
        _put_optional(payload, "threshold", self.threshold)
        return payload


@dataclass(frozen=True)
class ShadowOutcomeEvent:
    event_id: ShadowEventId
    true_topk_experts: list[int]
    true_topk_weights: list[float]
    full_fetch_used_count: int
    metadata_later_used_count: int
    premap_later_used_count: int
    skip_would_have_used_count: int
    covered_mass: float
    miss_mass: float
    top1_ready: bool
    weighted_top1_miss: float
    join_status: ShadowJoinStatus | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "event_type": "outcome",
            **self.event_id.as_dict(),
            "true_topk_experts": [int(value) for value in self.true_topk_experts],
            "true_topk_weights": [float(value) for value in self.true_topk_weights],
            "true_top1_expert": (
                int(self.true_topk_experts[0]) if self.true_topk_experts else None
            ),
            "true_top1_weight": (
                float(self.true_topk_weights[0]) if self.true_topk_weights else None
            ),
            "full_fetch_used_count": int(self.full_fetch_used_count),
            "metadata_later_used_count": int(self.metadata_later_used_count),
            "premap_later_used_count": int(self.premap_later_used_count),
            "skip_would_have_used_count": int(self.skip_would_have_used_count),
            "covered_mass": float(self.covered_mass),
            "miss_mass": float(self.miss_mass),
            "top1_ready": bool(self.top1_ready),
            "weighted_top1_miss": float(self.weighted_top1_miss),
        }
        _put_optional(payload, "join_status", self.join_status)
        return payload


def write_shadow_jsonl(events: Iterable[Any], output: str | Path) -> Path:
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            payload = event.as_dict() if hasattr(event, "as_dict") else dict(event)
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def read_shadow_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def aggregate_shadow_events(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "summary_count": 0,
        "candidate_count": 0,
        "outcome_count": 0,
        "full_fetch_count": 0,
        "metadata_count": 0,
        "premap_count": 0,
        "skip_count": 0,
        "full_fetch_payload_bytes": 0,
        "metadata_actual_bytes": 0,
        "premap_actual_bytes": 0,
        "full_fetch_used_count": 0,
        "metadata_later_used_count": 0,
        "premap_later_used_count": 0,
        "skip_would_have_used_count": 0,
        "top1_ready_count": 0,
        "weighted_top1_miss_sum": 0.0,
        "covered_mass_sum": 0.0,
        "miss_mass_sum": 0.0,
        "decision_us_sum": 0.0,
        "candidate_construction_us_sum": 0.0,
        "admission_decision_us_sum": 0.0,
        "counter_update_us_sum": 0.0,
        "logging_us_sum": 0.0,
        "descriptor_order_build_us_sum": 0.0,
        "descriptor_order_summary_count": 0,
        "descriptor_tile_request_count": 0,
        "descriptor_unique_b_tiles_sum": 0,
        "descriptor_order_lru_at_8_sum": 0.0,
        "descriptor_order_lru_at_16_sum": 0.0,
        "descriptor_order_hit_rate_sum": 0.0,
        "descriptor_reuse_distance_mean_sum": 0.0,
        "descriptor_unique_tiles_per_window_mean_sum": 0.0,
        "descriptor_same_multiset_count": 0,
        "descriptor_order_changed_count": 0,
        "joined_outcome_count": 0,
        "outcome_only_count": 0,
        "summary_only_timeout_count": 0,
    }
    for event in events:
        event_type = event.get("event_type")
        if event_type == "summary":
            totals["summary_count"] += 1
            for key in (
                "full_fetch_count",
                "metadata_count",
                "premap_count",
                "skip_count",
                "full_fetch_payload_bytes",
                "metadata_actual_bytes",
                "premap_actual_bytes",
            ):
                totals[key] += int(event.get(key, 0) or 0)
            for key in (
                "decision_us",
                "candidate_construction_us",
                "admission_decision_us",
                "counter_update_us",
                "logging_us",
            ):
                totals[f"{key}_sum"] += float(event.get(key, 0.0) or 0.0)
            if "descriptor_order_build_us" in event:
                totals["descriptor_order_build_us_sum"] += float(
                    event.get("descriptor_order_build_us", 0.0) or 0.0
                )
                totals["descriptor_order_summary_count"] += 1
                totals["descriptor_tile_request_count"] += int(
                    event.get("descriptor_tile_request_count", 0) or 0
                )
                totals["descriptor_unique_b_tiles_sum"] += int(
                    event.get("descriptor_unique_b_tiles", 0) or 0
                )
                totals["descriptor_order_lru_at_8_sum"] += float(
                    event.get("descriptor_order_lru_at_8", 0.0) or 0.0
                )
                totals["descriptor_order_lru_at_16_sum"] += float(
                    event.get("descriptor_order_lru_at_16", 0.0) or 0.0
                )
                totals["descriptor_order_hit_rate_sum"] += float(
                    event.get("descriptor_order_hit_rate", 0.0) or 0.0
                )
                totals["descriptor_reuse_distance_mean_sum"] += float(
                    event.get("descriptor_reuse_distance_mean", 0.0) or 0.0
                )
                totals["descriptor_unique_tiles_per_window_mean_sum"] += float(
                    event.get("descriptor_unique_tiles_per_window_mean", 0.0) or 0.0
                )
                totals["descriptor_same_multiset_count"] += int(
                    bool(event.get("descriptor_same_multiset", False))
                )
                totals["descriptor_order_changed_count"] += int(
                    bool(event.get("descriptor_order_changed", False))
                )
        elif event_type == "candidate":
            totals["candidate_count"] += 1
        elif event_type == "outcome":
            totals["outcome_count"] += 1
            join_status = event.get("join_status")
            if join_status == "joined":
                totals["joined_outcome_count"] += 1
            elif join_status == "outcome_only":
                totals["outcome_only_count"] += 1
            elif join_status == "summary_only_timeout":
                totals["summary_only_timeout_count"] += 1
            for key in (
                "full_fetch_used_count",
                "metadata_later_used_count",
                "premap_later_used_count",
                "skip_would_have_used_count",
            ):
                totals[key] += int(event.get(key, 0) or 0)
            totals["top1_ready_count"] += int(bool(event.get("top1_ready", False)))
            totals["weighted_top1_miss_sum"] += float(event.get("weighted_top1_miss", 0.0))
            totals["covered_mass_sum"] += float(event.get("covered_mass", 0.0))
            totals["miss_mass_sum"] += float(event.get("miss_mass", 0.0))

    outcome_count = max(1, int(totals["outcome_count"]))
    summary_count = max(1, int(totals["summary_count"]))
    totals["top1_ready_rate"] = totals["top1_ready_count"] / outcome_count
    totals["weighted_top1_miss_mean"] = totals["weighted_top1_miss_sum"] / outcome_count
    totals["covered_mass_mean"] = totals["covered_mass_sum"] / outcome_count
    totals["miss_mass_mean"] = totals["miss_mass_sum"] / outcome_count
    totals["decision_summary_count"] = summary_count
    for key in (
        "decision_us",
        "candidate_construction_us",
        "admission_decision_us",
        "counter_update_us",
        "logging_us",
    ):
        totals[f"{key}_mean"] = totals[f"{key}_sum"] / summary_count
    descriptor_count = max(1, int(totals["descriptor_order_summary_count"]))
    totals["descriptor_order_build_us_mean"] = (
        totals["descriptor_order_build_us_sum"] / descriptor_count
    )
    totals["descriptor_unique_b_tiles_mean"] = (
        totals["descriptor_unique_b_tiles_sum"] / descriptor_count
    )
    totals["descriptor_order_lru_at_8_mean"] = (
        totals["descriptor_order_lru_at_8_sum"] / descriptor_count
    )
    totals["descriptor_order_lru_at_16_mean"] = (
        totals["descriptor_order_lru_at_16_sum"] / descriptor_count
    )
    totals["descriptor_order_hit_rate_mean"] = (
        totals["descriptor_order_hit_rate_sum"] / descriptor_count
    )
    totals["descriptor_reuse_distance_mean"] = (
        totals["descriptor_reuse_distance_mean_sum"] / descriptor_count
    )
    totals["descriptor_unique_tiles_per_window_mean"] = (
        totals["descriptor_unique_tiles_per_window_mean_sum"] / descriptor_count
    )
    return totals


def _put_optional(payload: dict[str, Any], key: str, value: Any | None) -> None:
    if value is not None:
        payload[key] = value
