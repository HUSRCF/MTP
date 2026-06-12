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
    descriptor_order_execution_mode: str | None = None
    descriptor_group_plan_groups_per_cta: int | None = None
    descriptor_group_plan_group_count: int | None = None
    descriptor_group_plan_avg_group_size: float | None = None
    descriptor_group_plan_p95_group_size: float | None = None
    descriptor_group_plan_max_group_size: int | None = None
    descriptor_group_plan_cta_count: int | None = None
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
        _put_optional(payload, "descriptor_order_execution_mode", self.descriptor_order_execution_mode)
        _put_optional(
            payload,
            "descriptor_group_plan_groups_per_cta",
            self.descriptor_group_plan_groups_per_cta,
        )
        _put_optional(payload, "descriptor_group_plan_group_count", self.descriptor_group_plan_group_count)
        _put_optional(
            payload,
            "descriptor_group_plan_avg_group_size",
            self.descriptor_group_plan_avg_group_size,
        )
        _put_optional(
            payload,
            "descriptor_group_plan_p95_group_size",
            self.descriptor_group_plan_p95_group_size,
        )
        _put_optional(
            payload,
            "descriptor_group_plan_max_group_size",
            self.descriptor_group_plan_max_group_size,
        )
        _put_optional(payload, "descriptor_group_plan_cta_count", self.descriptor_group_plan_cta_count)
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
class ShadowDescriptorSummaryMinEvent:
    event_id: ShadowEventId
    descriptor_order_policy: str
    descriptor_order_prior_id: str | None
    descriptor_order_prior_hash: str | None
    descriptor_order_metrics_mode: str
    descriptor_tile_request_count: int
    descriptor_unique_b_tiles: int
    descriptor_window_count: int
    descriptor_order_top_utility_override: int | None = None
    descriptor_order_execution_mode: str | None = None
    descriptor_group_plan_groups_per_cta: int | None = None
    descriptor_group_plan_group_count: int | None = None
    descriptor_group_plan_avg_group_size: float | None = None
    descriptor_group_plan_p95_group_size: float | None = None
    descriptor_group_plan_max_group_size: int | None = None
    descriptor_group_plan_cta_count: int | None = None
    descriptor_order_gate_allow: bool | None = None
    descriptor_order_gate_reason: str | None = None
    descriptor_order_gate_tile_elems: int | None = None
    descriptor_order_gate_device: int | None = None
    descriptor_order_gate_evidence_found: bool | None = None
    descriptor_order_gate_checksum_delta: float | None = None
    descriptor_order_gate_speedup_median_vs_no_order: float | None = None
    descriptor_order_mapping_assertion_mode: str | None = None
    descriptor_order_mapping_source: str | None = None
    descriptor_order_mapping_same_multiset: bool | None = None
    descriptor_order_mapping_counts_match: bool | None = None
    descriptor_order_mapping_tile_multiset_hash: str | None = None
    descriptor_order_mapping_plan_tile_multiset_hash: str | None = None
    descriptor_order_mapping_request_count: int | None = None
    descriptor_order_mapping_plan_request_count: int | None = None
    descriptor_order_mapping_group_count: int | None = None
    descriptor_order_mapping_plan_group_count: int | None = None
    descriptor_order_mapping_error: str | None = None
    candidate_construction_us: float | None = None
    descriptor_order_build_us: float | None = None
    counter_update_us: float | None = None
    decision_us: float | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "event_type": "descriptor_summary_min",
            **self.event_id.as_dict(),
            "policy_mode": "descriptor_order_shadow",
            "optimization_goal": "cache_locality",
            "descriptor_order_policy": str(self.descriptor_order_policy),
            "descriptor_order_metrics_mode": str(self.descriptor_order_metrics_mode),
            "descriptor_tile_request_count": int(self.descriptor_tile_request_count),
            "descriptor_unique_b_tiles": int(self.descriptor_unique_b_tiles),
            "descriptor_window_count": int(self.descriptor_window_count),
        }
        _put_optional(payload, "descriptor_order_prior_id", self.descriptor_order_prior_id)
        _put_optional(payload, "descriptor_order_prior_hash", self.descriptor_order_prior_hash)
        _put_optional(
            payload,
            "descriptor_order_top_utility_override",
            self.descriptor_order_top_utility_override,
        )
        _put_optional(payload, "descriptor_order_execution_mode", self.descriptor_order_execution_mode)
        _put_optional(
            payload,
            "descriptor_group_plan_groups_per_cta",
            self.descriptor_group_plan_groups_per_cta,
        )
        _put_optional(payload, "descriptor_group_plan_group_count", self.descriptor_group_plan_group_count)
        _put_optional(
            payload,
            "descriptor_group_plan_avg_group_size",
            self.descriptor_group_plan_avg_group_size,
        )
        _put_optional(
            payload,
            "descriptor_group_plan_p95_group_size",
            self.descriptor_group_plan_p95_group_size,
        )
        _put_optional(
            payload,
            "descriptor_group_plan_max_group_size",
            self.descriptor_group_plan_max_group_size,
        )
        _put_optional(payload, "descriptor_group_plan_cta_count", self.descriptor_group_plan_cta_count)
        _put_optional(payload, "descriptor_order_gate_allow", self.descriptor_order_gate_allow)
        _put_optional(payload, "descriptor_order_gate_reason", self.descriptor_order_gate_reason)
        _put_optional(payload, "descriptor_order_gate_tile_elems", self.descriptor_order_gate_tile_elems)
        _put_optional(payload, "descriptor_order_gate_device", self.descriptor_order_gate_device)
        _put_optional(payload, "descriptor_order_gate_evidence_found", self.descriptor_order_gate_evidence_found)
        _put_optional(payload, "descriptor_order_gate_checksum_delta", self.descriptor_order_gate_checksum_delta)
        _put_optional(
            payload,
            "descriptor_order_gate_speedup_median_vs_no_order",
            self.descriptor_order_gate_speedup_median_vs_no_order,
        )
        _put_optional(
            payload,
            "descriptor_order_mapping_assertion_mode",
            self.descriptor_order_mapping_assertion_mode,
        )
        _put_optional(payload, "descriptor_order_mapping_source", self.descriptor_order_mapping_source)
        _put_optional(
            payload,
            "descriptor_order_mapping_same_multiset",
            self.descriptor_order_mapping_same_multiset,
        )
        _put_optional(
            payload,
            "descriptor_order_mapping_counts_match",
            self.descriptor_order_mapping_counts_match,
        )
        _put_optional(
            payload,
            "descriptor_order_mapping_tile_multiset_hash",
            self.descriptor_order_mapping_tile_multiset_hash,
        )
        _put_optional(
            payload,
            "descriptor_order_mapping_plan_tile_multiset_hash",
            self.descriptor_order_mapping_plan_tile_multiset_hash,
        )
        _put_optional(
            payload,
            "descriptor_order_mapping_request_count",
            self.descriptor_order_mapping_request_count,
        )
        _put_optional(
            payload,
            "descriptor_order_mapping_plan_request_count",
            self.descriptor_order_mapping_plan_request_count,
        )
        _put_optional(
            payload,
            "descriptor_order_mapping_group_count",
            self.descriptor_order_mapping_group_count,
        )
        _put_optional(
            payload,
            "descriptor_order_mapping_plan_group_count",
            self.descriptor_order_mapping_plan_group_count,
        )
        _put_optional(payload, "descriptor_order_mapping_error", self.descriptor_order_mapping_error)
        _put_optional(payload, "candidate_construction_us", self.candidate_construction_us)
        _put_optional(payload, "descriptor_order_build_us", self.descriptor_order_build_us)
        _put_optional(payload, "counter_update_us", self.counter_update_us)
        _put_optional(payload, "decision_us", self.decision_us)
        return payload


@dataclass(frozen=True)
class ShadowDescriptorPrelaunchAssertEvent:
    event_id: ShadowEventId
    assertion_mode: str
    mapping_source: str
    router_mapping_source: str | None
    same_multiset: bool
    counts_match: bool
    prelaunch_tile_multiset_hash: str
    router_derived_tile_multiset_hash: str | None
    prelaunch_request_count: int
    router_derived_request_count: int | None
    prelaunch_group_count: int
    router_derived_group_count: int | None
    error: str | None = None
    dump_us: float | None = None
    reorder_mvp_requested: bool | None = None
    reorder_mvp_gate_allow: bool | None = None
    reorder_mvp_gate_reason: str | None = None
    reorder_mvp_candidate_policy: str | None = None
    reorder_mvp_candidate_speedup_median_vs_no_order: float | None = None
    reorder_mvp_selected_policy: str | None = None
    reorder_mvp_applied: bool | None = None
    reorder_mvp_fallback_reason: str | None = None
    consumer_handle_source: str | None = None
    consumer_handle_available: bool | None = None
    consumer_handle_block_count: int | None = None
    consumer_handle_block_size: int | None = None
    consumer_handle_expert_order_hash: str | None = None
    consumer_handle_expert_multiset_hash: str | None = None
    consumer_handle_would_reorder: bool | None = None
    consumer_handle_same_multiset: bool | None = None
    consumer_handle_applied: bool | None = None
    consumer_handle_fallback_reason: str | None = None
    consumer_handle_attribution_mode: str | None = None
    consumer_handle_permutation_us: float | None = None
    consumer_handle_plan_build_us: float | None = None
    consumer_handle_plan_group_order_hash: str | None = None
    consumer_handle_plan_group_offsets_hash: str | None = None
    consumer_handle_plan_group_count: int | None = None
    consumer_handle_plan_avg_group_size: float | None = None
    consumer_handle_plan_p95_group_size: float | None = None
    consumer_handle_plan_max_group_size: int | None = None
    consumer_handle_plan_cta_count: int | None = None
    consumer_handle_clone_us: float | None = None
    consumer_handle_index_select_us: float | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "event_type": "descriptor_prelaunch_assertion",
            **self.event_id.as_dict(),
            "descriptor_order_prelaunch_assertion_mode": str(self.assertion_mode),
            "descriptor_order_prelaunch_mapping_source": str(self.mapping_source),
            "descriptor_order_prelaunch_same_multiset": bool(self.same_multiset),
            "descriptor_order_prelaunch_counts_match": bool(self.counts_match),
            "descriptor_order_prelaunch_tile_multiset_hash": str(
                self.prelaunch_tile_multiset_hash
            ),
            "descriptor_order_prelaunch_request_count": int(
                self.prelaunch_request_count
            ),
            "descriptor_order_prelaunch_group_count": int(self.prelaunch_group_count),
        }
        _put_optional(
            payload,
            "descriptor_order_prelaunch_router_mapping_source",
            self.router_mapping_source,
        )
        _put_optional(
            payload,
            "descriptor_order_prelaunch_router_derived_tile_multiset_hash",
            self.router_derived_tile_multiset_hash,
        )
        _put_optional(
            payload,
            "descriptor_order_prelaunch_router_derived_request_count",
            self.router_derived_request_count,
        )
        _put_optional(
            payload,
            "descriptor_order_prelaunch_router_derived_group_count",
            self.router_derived_group_count,
        )
        _put_optional(payload, "descriptor_order_prelaunch_error", self.error)
        _put_optional(payload, "descriptor_order_prelaunch_dump_us", self.dump_us)
        _put_optional(payload, "descriptor_order_reorder_mvp_requested", self.reorder_mvp_requested)
        _put_optional(payload, "descriptor_order_reorder_mvp_gate_allow", self.reorder_mvp_gate_allow)
        _put_optional(payload, "descriptor_order_reorder_mvp_gate_reason", self.reorder_mvp_gate_reason)
        _put_optional(
            payload,
            "descriptor_order_reorder_mvp_candidate_policy",
            self.reorder_mvp_candidate_policy,
        )
        _put_optional(
            payload,
            "descriptor_order_reorder_mvp_candidate_speedup_median_vs_no_order",
            self.reorder_mvp_candidate_speedup_median_vs_no_order,
        )
        _put_optional(payload, "descriptor_order_reorder_mvp_selected_policy", self.reorder_mvp_selected_policy)
        _put_optional(payload, "descriptor_order_reorder_mvp_applied", self.reorder_mvp_applied)
        _put_optional(payload, "descriptor_order_reorder_mvp_fallback_reason", self.reorder_mvp_fallback_reason)
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_source",
            self.consumer_handle_source,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_available",
            self.consumer_handle_available,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_block_count",
            self.consumer_handle_block_count,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_block_size",
            self.consumer_handle_block_size,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_expert_order_hash",
            self.consumer_handle_expert_order_hash,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_expert_multiset_hash",
            self.consumer_handle_expert_multiset_hash,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_would_reorder",
            self.consumer_handle_would_reorder,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_same_multiset",
            self.consumer_handle_same_multiset,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_applied",
            self.consumer_handle_applied,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_fallback_reason",
            self.consumer_handle_fallback_reason,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_attribution_mode",
            self.consumer_handle_attribution_mode,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_permutation_us",
            self.consumer_handle_permutation_us,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_plan_build_us",
            self.consumer_handle_plan_build_us,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_plan_group_order_hash",
            self.consumer_handle_plan_group_order_hash,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_plan_group_offsets_hash",
            self.consumer_handle_plan_group_offsets_hash,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_plan_group_count",
            self.consumer_handle_plan_group_count,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_plan_avg_group_size",
            self.consumer_handle_plan_avg_group_size,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_plan_p95_group_size",
            self.consumer_handle_plan_p95_group_size,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_plan_max_group_size",
            self.consumer_handle_plan_max_group_size,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_plan_cta_count",
            self.consumer_handle_plan_cta_count,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_clone_us",
            self.consumer_handle_clone_us,
        )
        _put_optional(
            payload,
            "descriptor_order_consumer_handle_index_select_us",
            self.consumer_handle_index_select_us,
        )
        return payload


@dataclass(frozen=True)
class ShadowPremapSummaryEvent:
    """Audit-only premap descriptor/address preparation summary.

    Premap is intentionally lighter than full_fetch: it may prepare descriptor
    or address metadata, but it must not move expert payloads, mutate router
    results, or change descriptor visitation order.
    """

    event_id: ShadowEventId
    premap_policy: str
    premap_descriptor_count: int
    premap_unique_experts: int
    premap_unique_layers: int
    premap_unique_sample_layers: int
    premap_actual_bytes: int
    premap_descriptor_hash: str
    premap_address_hash: str
    premap_mode: str = "shadow_only"
    premap_source: str | None = None
    premap_build_us: float | None = None
    decision_us: float | None = None
    candidate_construction_us: float | None = None
    counter_update_us: float | None = None
    logging_us: float | None = None
    premap_payload_bytes: int = 0
    premap_full_fetch_count: int = 0
    premap_metadata_count: int = 0
    premap_changes_router: bool = False
    premap_changes_descriptor_order: bool = False
    premap_ready_credit: bool = False
    premap_error: str | None = None
    premap_address_manager_capacity: int | None = None
    premap_address_resident_count: int | None = None
    premap_address_new_count: int | None = None
    premap_address_reused_count: int | None = None
    premap_address_evicted_count: int | None = None
    premap_address_reuse_rate: float | None = None
    premap_address_eviction_pressure: float | None = None
    premap_address_resident_descriptor_bytes: int | None = None
    premap_address_prepared_descriptor_actual_bytes: int | None = None
    premap_payload_cache_manager_id: str | None = None
    premap_payload_cache_manager_capacity: int | None = None
    premap_payload_cache_resident_count: int | None = None
    premap_payload_cache_issued_fetch_count: int | None = None
    premap_payload_cache_used_fetch_count: int | None = None
    premap_payload_cache_unused_fetch_count: int | None = None
    premap_payload_cache_demand_count: int | None = None
    premap_payload_cache_demand_hit_count: int | None = None
    premap_payload_cache_demand_miss_count: int | None = None
    premap_payload_cache_evicted_before_use_count: int | None = None
    premap_payload_cache_ready_late_miss_count: int | None = None
    premap_payload_cache_late_completion_unused_count: int | None = None
    premap_payload_cache_queue_batch_count: int | None = None
    premap_payload_cache_queue_service_us: float | None = None
    premap_payload_cache_queue_wait_us: float | None = None
    premap_payload_cache_queue_max_delay_us: float | None = None
    premap_payload_cache_queue_total_span_us: float | None = None
    premap_payload_cache_queue_deadline_us: float | None = None
    premap_payload_cache_queue_batch_size: int | None = None
    premap_payload_cache_demand_hit_rate: float | None = None
    premap_payload_cache_used_fetch_rate: float | None = None
    premap_payload_cache_eviction_pressure: float | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "event_type": "premap_summary",
            **self.event_id.as_dict(),
            "policy_mode": "premap_shadow",
            "optimization_goal": "descriptor_address_prep",
            "premap_policy": str(self.premap_policy),
            "premap_mode": str(self.premap_mode),
            "premap_descriptor_count": int(self.premap_descriptor_count),
            "premap_unique_experts": int(self.premap_unique_experts),
            "premap_unique_layers": int(self.premap_unique_layers),
            "premap_unique_sample_layers": int(self.premap_unique_sample_layers),
            "premap_actual_bytes": int(self.premap_actual_bytes),
            "premap_payload_bytes": int(self.premap_payload_bytes),
            "premap_full_fetch_count": int(self.premap_full_fetch_count),
            "premap_metadata_count": int(self.premap_metadata_count),
            "premap_changes_router": bool(self.premap_changes_router),
            "premap_changes_descriptor_order": bool(
                self.premap_changes_descriptor_order
            ),
            "premap_ready_credit": bool(self.premap_ready_credit),
            "premap_descriptor_hash": str(self.premap_descriptor_hash),
            "premap_address_hash": str(self.premap_address_hash),
        }
        _put_optional(payload, "premap_source", self.premap_source)
        _put_optional(payload, "premap_build_us", self.premap_build_us)
        _put_optional(payload, "decision_us", self.decision_us)
        _put_optional(payload, "candidate_construction_us", self.candidate_construction_us)
        _put_optional(payload, "counter_update_us", self.counter_update_us)
        _put_optional(payload, "logging_us", self.logging_us)
        _put_optional(payload, "premap_error", self.premap_error)
        _put_optional(
            payload,
            "premap_address_manager_capacity",
            self.premap_address_manager_capacity,
        )
        _put_optional(
            payload,
            "premap_address_resident_count",
            self.premap_address_resident_count,
        )
        _put_optional(payload, "premap_address_new_count", self.premap_address_new_count)
        _put_optional(
            payload,
            "premap_address_reused_count",
            self.premap_address_reused_count,
        )
        _put_optional(
            payload,
            "premap_address_evicted_count",
            self.premap_address_evicted_count,
        )
        _put_optional(payload, "premap_address_reuse_rate", self.premap_address_reuse_rate)
        _put_optional(
            payload,
            "premap_address_eviction_pressure",
            self.premap_address_eviction_pressure,
        )
        _put_optional(
            payload,
            "premap_address_resident_descriptor_bytes",
            self.premap_address_resident_descriptor_bytes,
        )
        _put_optional(
            payload,
            "premap_address_prepared_descriptor_actual_bytes",
            self.premap_address_prepared_descriptor_actual_bytes,
        )
        _put_optional(
            payload,
            "premap_payload_cache_manager_id",
            self.premap_payload_cache_manager_id,
        )
        _put_optional(
            payload,
            "premap_payload_cache_manager_capacity",
            self.premap_payload_cache_manager_capacity,
        )
        _put_optional(
            payload,
            "premap_payload_cache_resident_count",
            self.premap_payload_cache_resident_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_issued_fetch_count",
            self.premap_payload_cache_issued_fetch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_used_fetch_count",
            self.premap_payload_cache_used_fetch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_unused_fetch_count",
            self.premap_payload_cache_unused_fetch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_count",
            self.premap_payload_cache_demand_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_hit_count",
            self.premap_payload_cache_demand_hit_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_miss_count",
            self.premap_payload_cache_demand_miss_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_evicted_before_use_count",
            self.premap_payload_cache_evicted_before_use_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_ready_late_miss_count",
            self.premap_payload_cache_ready_late_miss_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_late_completion_unused_count",
            self.premap_payload_cache_late_completion_unused_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_batch_count",
            self.premap_payload_cache_queue_batch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_service_us",
            self.premap_payload_cache_queue_service_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_wait_us",
            self.premap_payload_cache_queue_wait_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_max_delay_us",
            self.premap_payload_cache_queue_max_delay_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_total_span_us",
            self.premap_payload_cache_queue_total_span_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_deadline_us",
            self.premap_payload_cache_queue_deadline_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_batch_size",
            self.premap_payload_cache_queue_batch_size,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_hit_rate",
            self.premap_payload_cache_demand_hit_rate,
        )
        _put_optional(
            payload,
            "premap_payload_cache_used_fetch_rate",
            self.premap_payload_cache_used_fetch_rate,
        )
        _put_optional(
            payload,
            "premap_payload_cache_eviction_pressure",
            self.premap_payload_cache_eviction_pressure,
        )
        return payload


@dataclass(frozen=True)
class ShadowPremapConsumerMappingEvent:
    """No-op consumer-side address mapping assertion.

    This event is emitted at the fused-MoE/AWQ consumer handle, after expert
    assignment has been prepared and before launch-time tensors are consumed.
    It validates that the true consumer's `(layer, expert)` handles resolve to
    already prepared premap address keys, without moving payloads, mutating the
    router, or changing descriptor visitation order.
    """

    event_id: ShadowEventId
    mapping_mode: str
    mapping_source: str
    address_namespace: str
    consumer_expert_count: int
    consumer_unique_expert_count: int
    address_hit_count: int
    address_miss_count: int
    address_hit_rate: float
    all_hit: bool
    parity_ok: bool
    consumer_key_hash: str
    readonly_gate_required: bool = False
    readonly_gate_id: str | None = None
    readonly_gate_path: str | None = None
    readonly_gate_passed: bool | None = None
    descriptor_handle_hit_count: int = 0
    descriptor_handle_miss_count: int = 0
    descriptor_handle_hash: str | None = None
    expected_descriptor_handle_hash: str | None = None
    descriptor_handle_parity_ok: bool | None = None
    prelaunch_boundary_source: str | None = None
    prelaunch_handle_available: bool | None = None
    prelaunch_block_count: int | None = None
    prelaunch_block_size: int | None = None
    prelaunch_expert_order_hash: str | None = None
    prelaunch_expert_multiset_hash: str | None = None
    prelaunch_unique_expert_count: int | None = None
    prelaunch_boundary_aligned: bool | None = None
    expected_prepare_plan_count: int | None = None
    observed_prepare_plan_count: int | None = None
    expected_prepare_record_count: int | None = None
    observed_prepare_record_count: int | None = None
    lookup_after_prepare: bool | None = None
    real_descriptor_handle_hit_count: int = 0
    real_descriptor_handle_miss_count: int = 0
    real_descriptor_handle_hash: str | None = None
    real_descriptor_handle_available: bool | None = None
    real_descriptor_handle_source_hashes: dict[str, str] | None = None
    real_descriptor_handle_source_hit_counts: dict[str, int] | None = None
    real_descriptor_handle_source_miss_counts: dict[str, int] | None = None
    real_descriptor_handle_miss_reason_counts: dict[str, int] | None = None
    real_descriptor_handle_new_binding_count: int = 0
    real_descriptor_handle_reused_binding_count: int = 0
    real_descriptor_handle_binding_mismatch_count: int = 0
    real_descriptor_handle_for_address_miss_count: int = 0
    readonly_consumer_lookup_count: int | None = None
    readonly_consumer_handle_hit_count: int | None = None
    readonly_consumer_handle_miss_count: int | None = None
    readonly_consumer_evicted_before_consume_count: int | None = None
    readonly_consumer_stale_handle_count: int | None = None
    readonly_consumer_handle_parity_ok: bool | None = None
    premap_payload_cache_manager_id: str | None = None
    premap_payload_cache_manager_capacity: int | None = None
    premap_payload_cache_resident_count: int | None = None
    premap_payload_cache_issued_fetch_count: int | None = None
    premap_payload_cache_used_fetch_count: int | None = None
    premap_payload_cache_unused_fetch_count: int | None = None
    premap_payload_cache_demand_count: int | None = None
    premap_payload_cache_demand_hit_count: int | None = None
    premap_payload_cache_demand_miss_count: int | None = None
    premap_payload_cache_evicted_before_use_count: int | None = None
    premap_payload_cache_ready_late_miss_count: int | None = None
    premap_payload_cache_late_completion_unused_count: int | None = None
    premap_payload_cache_queue_batch_count: int | None = None
    premap_payload_cache_queue_service_us: float | None = None
    premap_payload_cache_queue_wait_us: float | None = None
    premap_payload_cache_queue_max_delay_us: float | None = None
    premap_payload_cache_queue_total_span_us: float | None = None
    premap_payload_cache_queue_deadline_us: float | None = None
    premap_payload_cache_queue_batch_size: int | None = None
    premap_payload_cache_demand_hit_rate: float | None = None
    premap_payload_cache_used_fetch_rate: float | None = None
    premap_payload_cache_eviction_pressure: float | None = None
    descriptor_prep_execution_mode: str | None = None
    descriptor_prep_lookup_count: int | None = None
    descriptor_prep_handle_count: int | None = None
    descriptor_prep_missing_handle_count: int | None = None
    descriptor_prep_descriptor_ptr_count: int | None = None
    descriptor_prep_packed_weight_descriptor_count: int | None = None
    descriptor_prep_scale_metadata_handle_count: int | None = None
    descriptor_prep_real_handle_count: int | None = None
    descriptor_prep_real_handle_miss_count: int | None = None
    descriptor_prep_real_handle_backed: bool | None = None
    descriptor_prep_real_handle_hash: str | None = None
    descriptor_prep_handle_hash: str | None = None
    descriptor_prep_consumer_object_count: int | None = None
    descriptor_prep_consumer_object_hash: str | None = None
    descriptor_prep_consumer_object_read_lookup_count: int | None = None
    descriptor_prep_consumer_object_read_hit_count: int | None = None
    descriptor_prep_consumer_object_read_miss_count: int | None = None
    descriptor_prep_consumer_object_stale_count: int | None = None
    descriptor_prep_consumer_object_read_hash: str | None = None
    descriptor_prep_consumer_object_read_ok: bool | None = None
    descriptor_prep_consumer_shim_mode: str | None = None
    descriptor_prep_consumer_shim_object_count: int | None = None
    descriptor_prep_consumer_shim_object_hash: str | None = None
    descriptor_prep_consumer_shim_handle_table_row_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_column_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_schema_hash: str | None = None
    descriptor_prep_consumer_shim_handle_table_read_ok: bool | None = None
    descriptor_prep_consumer_shim_handle_table_lifecycle_ok: bool | None = None
    descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_row_miss_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_stale_row_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_passed_to_kernel: bool | None = None
    descriptor_prep_consumer_shim_handle_table_payload_bytes: int | None = None
    descriptor_prep_consumer_shim_handle_table_consume_ok: bool | None = None
    descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok: bool | None = None
    descriptor_prep_consumer_shim_handle_table_consume_row_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_consume_column_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_consume_schema_hash: str | None = None
    descriptor_prep_consumer_shim_handle_table_consume_mode: str | None = None
    descriptor_prep_consumer_shim_handle_table_consume_source: str | None = None
    descriptor_prep_consumer_shim_handle_table_consume_row_order_hash: str | None = None
    descriptor_prep_consumer_shim_handle_table_consume_ordered_row_hash: str | None = None
    descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_consume_row_miss_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_consume_stale_row_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_source_hit_counts: (
        dict[str, int] | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_source_miss_counts: (
        dict[str, int] | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel: bool | None = None
    descriptor_prep_consumer_shim_handle_table_consume_payload_bytes: int | None = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_name: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_field_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_name: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_source: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_field_name: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_source: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_semantic_adapter_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_nonzero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_zero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_semantic_field_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_handle_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_mismatch_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_current_wna16_arg_compatible: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_live_enabled: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_blocked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_block_reason: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready_credit: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_adapter_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_launch_schema_mirror_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_name: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_field_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_schema_present: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_connected: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_enabled: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_eligible: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_blocked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_compatible_with_current_wna16_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_kernel_side_adapter_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_semantic_adapter_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_launch_schema_mirror_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_table_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_semantic_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_kernel_side_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_typed_consumer_schema_name: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_typed_consumer_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_typed_consumer_field_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_required_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_required_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_optional_source_hit_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_optional_source_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_consumer_object_present: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_consumer_connected: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_live_enabled: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_live_eligible: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_blocked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_block_reason: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_checked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_ok: bool | None = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_input_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_required_handle_nonzero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_required_handle_zero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_optional_handle_nonzero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_optional_handle_zero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_expert_id_valid_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_expert_id_invalid_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_address_key_hash_nonzero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_address_key_hash_zero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_failure_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_failures: (
        tuple[str, ...] | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_ready_credit: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_router: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_descriptor_order: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_checked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_ok: bool | None = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_native_checker_invoked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_native_bridge_ok: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_package_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_input_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_required_handle_nonzero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_required_handle_zero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_optional_handle_nonzero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_optional_handle_zero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_expert_id_valid_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_expert_id_invalid_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_address_key_hash_nonzero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_address_key_hash_zero_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_requested: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_native_stub_invoked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_blocked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_block_reason: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_failure_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_failures: (
        tuple[str, ...] | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_ready_credit: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_changes_router: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_changes_descriptor_order: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_native_stub_online_invocation_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_mode: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_name: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_source: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_checked: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_ready: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_input_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_column_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_row_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_error_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_hash_accumulator: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_failure_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_failures: (
        tuple[str, ...] | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_current_wna16_arg_compatible: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_name: str | None = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_mode: str | None = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_source: str | None = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_checked: bool | None = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_ready: bool | None = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_input_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_table_object_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_schema_hash: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_error_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_all_handle_fields_read: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_packet_chain_depth: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_field_mask: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_descriptor_ptr_read_row_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_packed_weight_descriptor_read_row_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_scale_metadata_handle_read_row_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_aux_metadata_handle_read_row_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_expert_id_read_row_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_address_key_hash_read_row_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_metadata_read_row_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_hash_accumulator: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_field_read_hash_accumulator: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_metadata_hash_accumulator: (
        str | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_failure_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_failures: (
        tuple[str, ...] | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_payload_bytes: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_changes_kernel_launch_args: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_current_wna16_arg_compatible: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_explicit_typed_abi_slot: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_object_consumed: bool | None = None
    descriptor_prep_consumer_shim_handle_table_object_hash: str | None = None
    descriptor_prep_consumer_shim_handle_table_object_row_count: int | None = None
    descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok: bool | None = None
    descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_handle_table_object_payload_bytes: int | None = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_mode: str | None = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_source: str | None = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_ok: bool | None = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_row_count: int | None = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_column_count: int | None = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash: str | None = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_object_hash: str | None = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count: (
        int | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel: (
        bool | None
    ) = None
    descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes: int | None = None
    descriptor_prep_consumer_shim_ok: bool | None = None
    descriptor_prep_consumer_shim_changes_kernel_launch_args: bool | None = None
    descriptor_prep_kernel_arg_shadow_table_mode: str | None = None
    descriptor_prep_kernel_arg_shadow_table_row_order_source: str | None = None
    descriptor_prep_kernel_arg_shadow_table_row_count: int | None = None
    descriptor_prep_kernel_arg_shadow_table_column_count: int | None = None
    descriptor_prep_kernel_arg_shadow_table_schema_hash: str | None = None
    descriptor_prep_kernel_arg_shadow_table_row_order_hash: str | None = None
    descriptor_prep_kernel_arg_shadow_table_ordered_row_hash: str | None = None
    descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count: int | None = None
    descriptor_prep_kernel_arg_shadow_table_row_miss_count: int | None = None
    descriptor_prep_kernel_arg_shadow_table_stale_row_count: int | None = None
    descriptor_prep_kernel_arg_shadow_table_lifecycle_ok: bool | None = None
    descriptor_prep_kernel_arg_shadow_table_ok: bool | None = None
    descriptor_prep_kernel_arg_shadow_table_payload_bytes: int | None = None
    descriptor_prep_kernel_arg_shadow_table_ready_credit: bool | None = None
    descriptor_prep_kernel_arg_shadow_table_changes_router: bool | None = None
    descriptor_prep_kernel_arg_shadow_table_changes_descriptor_order: bool | None = None
    descriptor_prep_kernel_arg_shadow_table_changes_kernel_launch_args: bool | None = None
    descriptor_prep_kernel_arg_shadow_table_passed_to_kernel: bool | None = None
    descriptor_prep_execution_ok: bool | None = None
    descriptor_prep_blocked_reason: str | None = None
    expected_key_hash: str | None = None
    resident_address_count: int | None = None
    lookup_us: float | None = None
    error: str | None = None
    changes_router: bool = False
    changes_descriptor_order: bool = False
    payload_bytes: int = 0
    ready_credit: bool = False

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "event_type": "premap_consumer_mapping",
            **self.event_id.as_dict(),
            "policy_mode": "premap_shadow",
            "optimization_goal": "descriptor_address_prep",
            "premap_consumer_mapping_mode": str(self.mapping_mode),
            "premap_consumer_mapping_source": str(self.mapping_source),
            "premap_address_namespace": str(self.address_namespace),
            "premap_consumer_readonly_gate_required": bool(
                self.readonly_gate_required
            ),
            "premap_consumer_expert_count": int(self.consumer_expert_count),
            "premap_consumer_unique_expert_count": int(
                self.consumer_unique_expert_count
            ),
            "premap_consumer_address_hit_count": int(self.address_hit_count),
            "premap_consumer_address_miss_count": int(self.address_miss_count),
            "premap_consumer_address_hit_rate": float(self.address_hit_rate),
            "premap_consumer_all_hit": bool(self.all_hit),
            "premap_consumer_parity_ok": bool(self.parity_ok),
            "premap_consumer_key_hash": str(self.consumer_key_hash),
            "premap_consumer_descriptor_handle_hit_count": int(
                self.descriptor_handle_hit_count
            ),
            "premap_consumer_descriptor_handle_miss_count": int(
                self.descriptor_handle_miss_count
            ),
            "premap_consumer_changes_router": bool(self.changes_router),
            "premap_consumer_changes_descriptor_order": bool(
                self.changes_descriptor_order
            ),
            "premap_consumer_payload_bytes": int(self.payload_bytes),
            "premap_consumer_ready_credit": bool(self.ready_credit),
        }
        _put_optional(
            payload,
            "premap_consumer_readonly_gate_id",
            self.readonly_gate_id,
        )
        _put_optional(
            payload,
            "premap_consumer_readonly_gate_path",
            self.readonly_gate_path,
        )
        _put_optional(
            payload,
            "premap_consumer_readonly_gate_passed",
            self.readonly_gate_passed,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_handle_hash",
            self.descriptor_handle_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_expected_descriptor_handle_hash",
            self.expected_descriptor_handle_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_handle_parity_ok",
            self.descriptor_handle_parity_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_prelaunch_boundary_source",
            self.prelaunch_boundary_source,
        )
        _put_optional(
            payload,
            "premap_consumer_prelaunch_handle_available",
            self.prelaunch_handle_available,
        )
        _put_optional(
            payload,
            "premap_consumer_prelaunch_block_count",
            self.prelaunch_block_count,
        )
        _put_optional(
            payload,
            "premap_consumer_prelaunch_block_size",
            self.prelaunch_block_size,
        )
        _put_optional(
            payload,
            "premap_consumer_prelaunch_expert_order_hash",
            self.prelaunch_expert_order_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_prelaunch_expert_multiset_hash",
            self.prelaunch_expert_multiset_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_prelaunch_unique_expert_count",
            self.prelaunch_unique_expert_count,
        )
        _put_optional(
            payload,
            "premap_consumer_prelaunch_boundary_aligned",
            self.prelaunch_boundary_aligned,
        )
        _put_optional(
            payload,
            "premap_consumer_expected_prepare_plan_count",
            self.expected_prepare_plan_count,
        )
        _put_optional(
            payload,
            "premap_consumer_observed_prepare_plan_count",
            self.observed_prepare_plan_count,
        )
        _put_optional(
            payload,
            "premap_consumer_expected_prepare_record_count",
            self.expected_prepare_record_count,
        )
        _put_optional(
            payload,
            "premap_consumer_observed_prepare_record_count",
            self.observed_prepare_record_count,
        )
        _put_optional(
            payload,
            "premap_consumer_lookup_after_prepare",
            self.lookup_after_prepare,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_hit_count",
            self.real_descriptor_handle_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_miss_count",
            self.real_descriptor_handle_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_hash",
            self.real_descriptor_handle_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_available",
            self.real_descriptor_handle_available,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_source_hashes",
            self.real_descriptor_handle_source_hashes,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_source_hit_counts",
            self.real_descriptor_handle_source_hit_counts,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_source_miss_counts",
            self.real_descriptor_handle_source_miss_counts,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_miss_reason_counts",
            self.real_descriptor_handle_miss_reason_counts,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_new_binding_count",
            self.real_descriptor_handle_new_binding_count,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_reused_binding_count",
            self.real_descriptor_handle_reused_binding_count,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_binding_mismatch_count",
            self.real_descriptor_handle_binding_mismatch_count,
        )
        _put_optional(
            payload,
            "premap_consumer_real_descriptor_handle_for_address_miss_count",
            self.real_descriptor_handle_for_address_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_readonly_lookup_count",
            self.readonly_consumer_lookup_count,
        )
        _put_optional(
            payload,
            "premap_consumer_readonly_handle_hit_count",
            self.readonly_consumer_handle_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_readonly_handle_miss_count",
            self.readonly_consumer_handle_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_readonly_evicted_before_consume_count",
            self.readonly_consumer_evicted_before_consume_count,
        )
        _put_optional(
            payload,
            "premap_consumer_readonly_stale_handle_count",
            self.readonly_consumer_stale_handle_count,
        )
        _put_optional(
            payload,
            "premap_consumer_readonly_handle_parity_ok",
            self.readonly_consumer_handle_parity_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_execution_mode",
            self.descriptor_prep_execution_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_lookup_count",
            self.descriptor_prep_lookup_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_handle_count",
            self.descriptor_prep_handle_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_missing_handle_count",
            self.descriptor_prep_missing_handle_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_descriptor_ptr_count",
            self.descriptor_prep_descriptor_ptr_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_packed_weight_descriptor_count",
            self.descriptor_prep_packed_weight_descriptor_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_scale_metadata_handle_count",
            self.descriptor_prep_scale_metadata_handle_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_real_handle_count",
            self.descriptor_prep_real_handle_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_real_handle_miss_count",
            self.descriptor_prep_real_handle_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_real_handle_backed",
            self.descriptor_prep_real_handle_backed,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_real_handle_hash",
            self.descriptor_prep_real_handle_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_handle_hash",
            self.descriptor_prep_handle_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_object_count",
            self.descriptor_prep_consumer_object_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_object_hash",
            self.descriptor_prep_consumer_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_object_read_lookup_count",
            self.descriptor_prep_consumer_object_read_lookup_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_object_read_hit_count",
            self.descriptor_prep_consumer_object_read_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_object_read_miss_count",
            self.descriptor_prep_consumer_object_read_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_object_stale_count",
            self.descriptor_prep_consumer_object_stale_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_object_read_hash",
            self.descriptor_prep_consumer_object_read_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_object_read_ok",
            self.descriptor_prep_consumer_object_read_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_mode",
            self.descriptor_prep_consumer_shim_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_object_count",
            self.descriptor_prep_consumer_shim_object_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_object_hash",
            self.descriptor_prep_consumer_shim_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count",
            self.descriptor_prep_consumer_shim_handle_table_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count",
            self.descriptor_prep_consumer_shim_handle_table_column_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_schema_hash",
            self.descriptor_prep_consumer_shim_handle_table_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok",
            self.descriptor_prep_consumer_shim_handle_table_read_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok",
            self.descriptor_prep_consumer_shim_handle_table_lifecycle_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count",
            self.descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count",
            self.descriptor_prep_consumer_shim_handle_table_row_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count",
            self.descriptor_prep_consumer_shim_handle_table_stale_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel",
            self.descriptor_prep_consumer_shim_handle_table_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes",
            self.descriptor_prep_consumer_shim_handle_table_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok",
            self.descriptor_prep_consumer_shim_handle_table_consume_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok",
            self.descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_column_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash",
            self.descriptor_prep_consumer_shim_handle_table_consume_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode",
            self.descriptor_prep_consumer_shim_handle_table_consume_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source",
            self.descriptor_prep_consumer_shim_handle_table_consume_source,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_order_hash",
            self.descriptor_prep_consumer_shim_handle_table_consume_row_order_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ordered_row_hash",
            self.descriptor_prep_consumer_shim_handle_table_consume_ordered_row_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_row_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_stale_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count",
            self.descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_hit_counts",
            self.descriptor_prep_consumer_shim_handle_table_consume_source_hit_counts,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_miss_counts",
            self.descriptor_prep_consumer_shim_handle_table_consume_source_miss_counts,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel",
            self.descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes",
            self.descriptor_prep_consumer_shim_handle_table_consume_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_table_object_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_table_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_changes_kernel_launch_args",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_changes_kernel_launch_args,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_table_object_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_table_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_changes_kernel_launch_args",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_changes_kernel_launch_args,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_object_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_changes_kernel_launch_args",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_changes_kernel_launch_args,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_table_object_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_table_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_changes_kernel_launch_args",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_changes_kernel_launch_args,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_changes_kernel_launch_args",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_changes_kernel_launch_args,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff",
            self.descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff,
        )
        for key, value in (
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_ready",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_ready,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_hash",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_object_hash",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_object_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_row_count",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_row_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_column_count",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_column_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_name",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_name,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_field_count",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_field_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_hit_count",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_hit_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_miss_count",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_miss_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_hit_count",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_hit_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_miss_count",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_miss_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_handle_field_read_count",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_handle_field_read_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_payload_bytes",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_payload_bytes,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_passed_to_kernel",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_passed_to_kernel,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_changes_kernel_launch_args",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_changes_kernel_launch_args,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args",
                self.descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args,
            ),
        ):
            _put_optional(payload, key, value)
        for key, value in (
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mode",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mode,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_hash",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_name",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_name,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_source",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_source,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_mode",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_mode,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_ready",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_ready,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_field_name",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_field_name,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_source",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_source,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_table_object_hash",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_table_object_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_semantic_adapter_hash",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_semantic_adapter_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_row_count",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_row_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_count",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_nonzero_count",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_nonzero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_zero_count",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_zero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_hash",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_semantic_field_hash",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_semantic_field_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_handle_hash",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_handle_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_schema_hash",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_ok_count",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_mismatch_count",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_mismatch_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_current_wna16_arg_compatible",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_current_wna16_arg_compatible,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_live_enabled",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_live_enabled,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_blocked",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_blocked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_block_reason",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_block_reason,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_payload_bytes",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_payload_bytes,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready_credit",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready_credit,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_passed_to_kernel",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_passed_to_kernel,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_changes_kernel_launch_args",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_changes_kernel_launch_args,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args",
                self.descriptor_prep_consumer_shim_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args,
            ),
        ):
            _put_optional(payload, key, value)
        for key, value in (
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_ready",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_ready,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_hash",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_adapter_hash",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_adapter_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_object_hash",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_object_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_launch_schema_mirror_hash",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_launch_schema_mirror_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_row_count",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_row_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_column_count",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_column_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_name",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_name,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_field_count",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_field_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_hit_count",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_hit_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_miss_count",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_miss_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_hit_count",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_hit_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_miss_count",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_miss_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_handle_field_read_count",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_handle_field_read_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_schema_present",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_schema_present,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_connected",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_connected,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_enabled",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_enabled,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_eligible",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_eligible,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_blocked",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_blocked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_payload_bytes",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_payload_bytes,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_passed_to_kernel",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_passed_to_kernel,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_changes_kernel_launch_args",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_changes_kernel_launch_args,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_compatible_with_current_wna16_args",
                self.descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_compatible_with_current_wna16_args,
            ),
        ):
            _put_optional(payload, key, value)
        for key, value in (
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_mode",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_mode,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_ready",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_ready,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_kernel_side_adapter_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_kernel_side_adapter_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_semantic_adapter_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_semantic_adapter_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_table_object_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_table_object_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_launch_schema_mirror_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_launch_schema_mirror_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_row_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_row_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_column_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_column_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_table_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_table_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_semantic_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_semantic_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_kernel_side_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_kernel_side_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_typed_consumer_schema_name",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_typed_consumer_schema_name,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_typed_consumer_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_typed_consumer_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_typed_consumer_field_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_typed_consumer_field_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_required_source_hit_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_required_source_hit_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_required_source_miss_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_required_source_miss_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_optional_source_hit_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_optional_source_hit_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_optional_source_miss_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_optional_source_miss_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_handle_field_read_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_handle_field_read_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_consumer_object_present",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_consumer_object_present,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_consumer_connected",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_consumer_connected,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_live_enabled",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_live_enabled,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_live_eligible",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_live_eligible,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_blocked",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_blocked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_block_reason",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_block_reason,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_payload_bytes",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_payload_bytes,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_passed_to_kernel",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_passed_to_kernel,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_changes_kernel_launch_args",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_changes_kernel_launch_args,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args",
                self.descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args,
            ),
        ):
            _put_optional(payload, key, value)
        for key, value in (
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_mode",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_mode,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_checked",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_checked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_ok",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_ok,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_input_hash",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_input_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_table_object_hash",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_table_object_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_schema_hash",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_row_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_row_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_column_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_column_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_required_handle_nonzero_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_required_handle_nonzero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_required_handle_zero_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_required_handle_zero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_optional_handle_nonzero_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_optional_handle_nonzero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_optional_handle_zero_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_optional_handle_zero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_expert_id_valid_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_expert_id_valid_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_expert_id_invalid_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_expert_id_invalid_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_address_key_hash_nonzero_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_address_key_hash_nonzero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_address_key_hash_zero_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_address_key_hash_zero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_failure_count",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_failure_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_failures",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_failures,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_payload_bytes",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_payload_bytes,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_ready_credit",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_ready_credit,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_router",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_router,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_descriptor_order",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_descriptor_order,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_passed_to_kernel",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_passed_to_kernel,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_kernel_launch_args",
                self.descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_kernel_launch_args,
            ),
        ):
            _put_optional(payload, key, value)
        for key, value in (
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_mode",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_mode,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_checked",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_checked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_ready",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_ready,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_ok",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_ok,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_native_checker_invoked",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_native_checker_invoked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_native_bridge_ok",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_native_bridge_ok,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_package_hash",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_package_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_input_hash",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_input_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_table_object_hash",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_table_object_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_schema_hash",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_row_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_row_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_column_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_column_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_required_handle_nonzero_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_required_handle_nonzero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_required_handle_zero_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_required_handle_zero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_optional_handle_nonzero_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_optional_handle_nonzero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_optional_handle_zero_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_optional_handle_zero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_expert_id_valid_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_expert_id_valid_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_expert_id_invalid_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_expert_id_invalid_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_address_key_hash_nonzero_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_address_key_hash_nonzero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_address_key_hash_zero_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_address_key_hash_zero_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_requested",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_requested,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_native_stub_invoked",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_native_stub_invoked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_blocked",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_blocked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_block_reason",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_block_reason,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_failure_count",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_failure_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_failures",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_failures,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_payload_bytes",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_payload_bytes,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_ready_credit",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_ready_credit,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_changes_router",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_changes_router,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_changes_descriptor_order",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_changes_descriptor_order,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_passed_to_kernel",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_passed_to_kernel,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_changes_kernel_launch_args",
                self.descriptor_prep_consumer_shim_native_stub_online_invocation_changes_kernel_launch_args,
            ),
        ):
            _put_optional(payload, key, value)
        for key, value in (
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_mode",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_mode,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_name",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_name,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_source",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_source,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_checked",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_checked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_ready",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_ready,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_input_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_input_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_table_object_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_table_object_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_schema_hash",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_row_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_row_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_column_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_column_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_row_ok_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_row_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_error_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_error_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_hash_accumulator",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_hash_accumulator,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_failure_count",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_failure_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_failures",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_failures,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_payload_bytes",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_payload_bytes,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_passed_to_kernel",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_passed_to_kernel,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_changes_kernel_launch_args",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_changes_kernel_launch_args,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_current_wna16_arg_compatible",
                self.descriptor_prep_consumer_shim_kernel_side_typed_row_consumer_path_current_wna16_arg_compatible,
            ),
        ):
            _put_optional(payload, key, value)
        for key, value in (
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_name",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_name,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_mode",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_mode,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_source",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_source,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_checked",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_checked,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_ready",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_ready,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_input_hash",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_input_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_table_object_hash",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_table_object_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_schema_hash",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_schema_hash,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_ok_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_error_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_error_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_all_handle_fields_read",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_all_handle_fields_read,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_packet_chain_depth",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_packet_chain_depth,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_field_mask",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_field_mask,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_descriptor_ptr_read_row_ok_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_descriptor_ptr_read_row_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_packed_weight_descriptor_read_row_ok_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_packed_weight_descriptor_read_row_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_scale_metadata_handle_read_row_ok_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_scale_metadata_handle_read_row_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_aux_metadata_handle_read_row_ok_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_aux_metadata_handle_read_row_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_expert_id_read_row_ok_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_expert_id_read_row_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_address_key_hash_read_row_ok_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_address_key_hash_read_row_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_metadata_read_row_ok_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_metadata_read_row_ok_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_hash_accumulator",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_hash_accumulator,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_field_read_hash_accumulator",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_field_read_hash_accumulator,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_metadata_hash_accumulator",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_metadata_hash_accumulator,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_failure_count",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_failure_count,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_failures",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_failures,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_payload_bytes",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_payload_bytes,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_passed_to_kernel",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_passed_to_kernel,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_changes_kernel_launch_args",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_changes_kernel_launch_args,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_current_wna16_arg_compatible",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_current_wna16_arg_compatible,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_explicit_typed_abi_slot",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_explicit_typed_abi_slot,
            ),
            (
                "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot",
                self.descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot,
            ),
        ):
            _put_optional(payload, key, value)
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed",
            self.descriptor_prep_consumer_shim_handle_table_object_consumed,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_hash",
            self.descriptor_prep_consumer_shim_handle_table_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count",
            self.descriptor_prep_consumer_shim_handle_table_object_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok",
            self.descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel",
            self.descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_bytes",
            self.descriptor_prep_consumer_shim_handle_table_object_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_mode",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_source",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_source,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_column_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_object_hash",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_object_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes",
            self.descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_ok",
            self.descriptor_prep_consumer_shim_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_consumer_shim_changes_kernel_launch_args",
            self.descriptor_prep_consumer_shim_changes_kernel_launch_args,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_mode",
            self.descriptor_prep_kernel_arg_shadow_table_mode,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_order_source",
            self.descriptor_prep_kernel_arg_shadow_table_row_order_source,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count",
            self.descriptor_prep_kernel_arg_shadow_table_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count",
            self.descriptor_prep_kernel_arg_shadow_table_column_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash",
            self.descriptor_prep_kernel_arg_shadow_table_schema_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_order_hash",
            self.descriptor_prep_kernel_arg_shadow_table_row_order_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ordered_row_hash",
            self.descriptor_prep_kernel_arg_shadow_table_ordered_row_hash,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count",
            self.descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count",
            self.descriptor_prep_kernel_arg_shadow_table_row_miss_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count",
            self.descriptor_prep_kernel_arg_shadow_table_stale_row_count,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok",
            self.descriptor_prep_kernel_arg_shadow_table_lifecycle_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok",
            self.descriptor_prep_kernel_arg_shadow_table_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes",
            self.descriptor_prep_kernel_arg_shadow_table_payload_bytes,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit",
            self.descriptor_prep_kernel_arg_shadow_table_ready_credit,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_router",
            self.descriptor_prep_kernel_arg_shadow_table_changes_router,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_descriptor_order",
            self.descriptor_prep_kernel_arg_shadow_table_changes_descriptor_order,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_kernel_launch_args",
            self.descriptor_prep_kernel_arg_shadow_table_changes_kernel_launch_args,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel",
            self.descriptor_prep_kernel_arg_shadow_table_passed_to_kernel,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_execution_ok",
            self.descriptor_prep_execution_ok,
        )
        _put_optional(
            payload,
            "premap_consumer_descriptor_prep_blocked_reason",
            self.descriptor_prep_blocked_reason,
        )
        _put_optional(payload, "premap_consumer_expected_key_hash", self.expected_key_hash)
        _put_optional(
            payload,
            "premap_consumer_resident_address_count",
            self.resident_address_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_manager_id",
            self.premap_payload_cache_manager_id,
        )
        _put_optional(
            payload,
            "premap_payload_cache_manager_capacity",
            self.premap_payload_cache_manager_capacity,
        )
        _put_optional(
            payload,
            "premap_payload_cache_resident_count",
            self.premap_payload_cache_resident_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_issued_fetch_count",
            self.premap_payload_cache_issued_fetch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_used_fetch_count",
            self.premap_payload_cache_used_fetch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_unused_fetch_count",
            self.premap_payload_cache_unused_fetch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_count",
            self.premap_payload_cache_demand_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_hit_count",
            self.premap_payload_cache_demand_hit_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_miss_count",
            self.premap_payload_cache_demand_miss_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_evicted_before_use_count",
            self.premap_payload_cache_evicted_before_use_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_ready_late_miss_count",
            self.premap_payload_cache_ready_late_miss_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_late_completion_unused_count",
            self.premap_payload_cache_late_completion_unused_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_batch_count",
            self.premap_payload_cache_queue_batch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_service_us",
            self.premap_payload_cache_queue_service_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_wait_us",
            self.premap_payload_cache_queue_wait_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_max_delay_us",
            self.premap_payload_cache_queue_max_delay_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_total_span_us",
            self.premap_payload_cache_queue_total_span_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_deadline_us",
            self.premap_payload_cache_queue_deadline_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_batch_size",
            self.premap_payload_cache_queue_batch_size,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_hit_rate",
            self.premap_payload_cache_demand_hit_rate,
        )
        _put_optional(
            payload,
            "premap_payload_cache_used_fetch_rate",
            self.premap_payload_cache_used_fetch_rate,
        )
        _put_optional(
            payload,
            "premap_payload_cache_eviction_pressure",
            self.premap_payload_cache_eviction_pressure,
        )
        _put_optional(payload, "premap_consumer_lookup_us", self.lookup_us)
        _put_optional(payload, "premap_consumer_error", self.error)
        return payload


@dataclass(frozen=True)
class ShadowPremapPayloadCacheManagerEvent:
    """Accounting-only payload cache-manager runtime snapshot.

    This event records the controlled expert-payload cache manager's issue and
    demand counters. It is intentionally not a payload transfer event: it grants
    no ready credit, moves no expert weights, and does not alter router,
    descriptor order, or kernel arguments.
    """

    event_id: ShadowEventId
    cache_mode: str
    source: str
    consumer_expert_count: int
    consumer_unique_expert_count: int
    premap_payload_cache_manager_id: str | None = None
    premap_payload_cache_manager_capacity: int | None = None
    premap_payload_cache_resident_count: int | None = None
    premap_payload_cache_issued_fetch_count: int | None = None
    premap_payload_cache_used_fetch_count: int | None = None
    premap_payload_cache_unused_fetch_count: int | None = None
    premap_payload_cache_demand_count: int | None = None
    premap_payload_cache_demand_hit_count: int | None = None
    premap_payload_cache_demand_miss_count: int | None = None
    premap_payload_cache_evicted_before_use_count: int | None = None
    premap_payload_cache_ready_late_miss_count: int | None = None
    premap_payload_cache_late_completion_unused_count: int | None = None
    premap_payload_cache_queue_batch_count: int | None = None
    premap_payload_cache_queue_service_us: float | None = None
    premap_payload_cache_queue_wait_us: float | None = None
    premap_payload_cache_queue_max_delay_us: float | None = None
    premap_payload_cache_queue_total_span_us: float | None = None
    premap_payload_cache_queue_deadline_us: float | None = None
    premap_payload_cache_queue_batch_size: int | None = None
    premap_payload_cache_demand_hit_rate: float | None = None
    premap_payload_cache_used_fetch_rate: float | None = None
    premap_payload_cache_eviction_pressure: float | None = None
    payload_bytes: int = 0
    ready_credit: bool = False
    changes_router: bool = False
    changes_descriptor_order: bool = False
    changes_kernel_launch_args: bool = False
    passed_to_kernel: bool = False

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "event_type": "premap_payload_cache_manager",
            **self.event_id.as_dict(),
            "policy_mode": "premap_payload_cache_accounting",
            "optimization_goal": "payload_cache_manager_runtime",
            "premap_payload_cache_mode": str(self.cache_mode),
            "premap_payload_cache_source": str(self.source),
            "premap_payload_cache_consumer_expert_count": int(
                self.consumer_expert_count
            ),
            "premap_payload_cache_consumer_unique_expert_count": int(
                self.consumer_unique_expert_count
            ),
            "premap_payload_cache_payload_bytes": int(self.payload_bytes),
            "premap_payload_cache_ready_credit": bool(self.ready_credit),
            "premap_payload_cache_changes_router": bool(self.changes_router),
            "premap_payload_cache_changes_descriptor_order": bool(
                self.changes_descriptor_order
            ),
            "premap_payload_cache_changes_kernel_launch_args": bool(
                self.changes_kernel_launch_args
            ),
            "premap_payload_cache_passed_to_kernel": bool(self.passed_to_kernel),
        }
        _put_optional(
            payload,
            "premap_payload_cache_manager_id",
            self.premap_payload_cache_manager_id,
        )
        _put_optional(
            payload,
            "premap_payload_cache_manager_capacity",
            self.premap_payload_cache_manager_capacity,
        )
        _put_optional(
            payload,
            "premap_payload_cache_resident_count",
            self.premap_payload_cache_resident_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_issued_fetch_count",
            self.premap_payload_cache_issued_fetch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_used_fetch_count",
            self.premap_payload_cache_used_fetch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_unused_fetch_count",
            self.premap_payload_cache_unused_fetch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_count",
            self.premap_payload_cache_demand_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_hit_count",
            self.premap_payload_cache_demand_hit_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_miss_count",
            self.premap_payload_cache_demand_miss_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_evicted_before_use_count",
            self.premap_payload_cache_evicted_before_use_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_ready_late_miss_count",
            self.premap_payload_cache_ready_late_miss_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_late_completion_unused_count",
            self.premap_payload_cache_late_completion_unused_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_batch_count",
            self.premap_payload_cache_queue_batch_count,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_service_us",
            self.premap_payload_cache_queue_service_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_wait_us",
            self.premap_payload_cache_queue_wait_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_max_delay_us",
            self.premap_payload_cache_queue_max_delay_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_total_span_us",
            self.premap_payload_cache_queue_total_span_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_deadline_us",
            self.premap_payload_cache_queue_deadline_us,
        )
        _put_optional(
            payload,
            "premap_payload_cache_queue_batch_size",
            self.premap_payload_cache_queue_batch_size,
        )
        _put_optional(
            payload,
            "premap_payload_cache_demand_hit_rate",
            self.premap_payload_cache_demand_hit_rate,
        )
        _put_optional(
            payload,
            "premap_payload_cache_used_fetch_rate",
            self.premap_payload_cache_used_fetch_rate,
        )
        _put_optional(
            payload,
            "premap_payload_cache_eviction_pressure",
            self.premap_payload_cache_eviction_pressure,
        )
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


@dataclass(frozen=True)
class ShadowOutcomeAggregateEvent:
    event_id: ShadowEventId
    token_start: int
    token_end: int
    token_count: int
    top_k: int
    topk_entry_count: int
    routed_expert_count: int
    topk_weight_mass_sum: float
    top1_weight_sum: float
    top1_weight_mean: float
    outcome_logging_mode: str = "aggregate"

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": "outcome_aggregate",
            **self.event_id.as_dict(),
            "outcome_logging_mode": str(self.outcome_logging_mode),
            "token_start": int(self.token_start),
            "token_end": int(self.token_end),
            "token_count": int(self.token_count),
            "top_k": int(self.top_k),
            "topk_entry_count": int(self.topk_entry_count),
            "routed_expert_count": int(self.routed_expert_count),
            "topk_weight_mass_sum": float(self.topk_weight_mass_sum),
            "top1_weight_sum": float(self.top1_weight_sum),
            "top1_weight_mean": float(self.top1_weight_mean),
        }


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
        "descriptor_summary_min_count": 0,
        "descriptor_summary_full_count": 0,
        "premap_summary_count": 0,
        "premap_summary_descriptor_count": 0,
        "premap_summary_unique_experts_sum": 0,
        "premap_summary_unique_layers_sum": 0,
        "premap_summary_unique_sample_layers_sum": 0,
        "premap_summary_actual_bytes": 0,
        "premap_summary_payload_bytes": 0,
        "premap_summary_build_us_sum": 0.0,
        "premap_summary_build_us_count": 0,
        "premap_summary_payload_violation_count": 0,
        "premap_summary_full_fetch_violation_count": 0,
        "premap_summary_metadata_violation_count": 0,
        "premap_summary_router_change_violation_count": 0,
        "premap_summary_descriptor_order_change_violation_count": 0,
        "premap_summary_ready_credit_violation_count": 0,
        "premap_summary_error_count": 0,
        "premap_address_manager_count": 0,
        "premap_address_new_count": 0,
        "premap_address_reused_count": 0,
        "premap_address_evicted_count": 0,
        "premap_address_resident_count_max": 0,
        "premap_address_resident_descriptor_bytes_max": 0,
        "premap_address_prepared_descriptor_actual_bytes_max": 0,
        "premap_address_reuse_rate_sum": 0.0,
        "premap_address_eviction_pressure_sum": 0.0,
        "_premap_address_new_count_prev": None,
        "_premap_address_reused_count_prev": None,
        "_premap_address_evicted_count_prev": None,
        "premap_payload_cache_manager_count": 0,
        "premap_payload_cache_resident_count_max": 0,
        "premap_payload_cache_unused_fetch_count_max": 0,
        "premap_payload_cache_issued_fetch_count": 0,
        "premap_payload_cache_used_fetch_count": 0,
        "premap_payload_cache_demand_count": 0,
        "premap_payload_cache_demand_hit_count": 0,
        "premap_payload_cache_demand_miss_count": 0,
        "premap_payload_cache_evicted_before_use_count": 0,
        "premap_payload_cache_ready_late_miss_count": 0,
        "premap_payload_cache_late_completion_unused_count": 0,
        "premap_payload_cache_queue_batch_count": 0,
        "premap_payload_cache_queue_service_us": 0.0,
        "premap_payload_cache_queue_wait_us": 0.0,
        "premap_payload_cache_queue_max_delay_us_max": 0.0,
        "premap_payload_cache_queue_total_span_us_max": 0.0,
        "premap_payload_cache_queue_deadline_us_max": 0.0,
        "premap_payload_cache_queue_batch_size_max": 0,
        "premap_payload_cache_demand_hit_rate_sum": 0.0,
        "premap_payload_cache_used_fetch_rate_sum": 0.0,
        "premap_payload_cache_eviction_pressure_sum": 0.0,
        "_premap_payload_cache_issued_fetch_count_prev_by_manager": {},
        "_premap_payload_cache_used_fetch_count_prev_by_manager": {},
        "_premap_payload_cache_demand_count_prev_by_manager": {},
        "_premap_payload_cache_demand_hit_count_prev_by_manager": {},
        "_premap_payload_cache_demand_miss_count_prev_by_manager": {},
        "_premap_payload_cache_evicted_before_use_count_prev_by_manager": {},
        "_premap_payload_cache_ready_late_miss_count_prev_by_manager": {},
        "_premap_payload_cache_late_completion_unused_count_prev_by_manager": {},
        "_premap_payload_cache_queue_batch_count_prev_by_manager": {},
        "_premap_payload_cache_queue_service_us_prev_by_manager": {},
        "_premap_payload_cache_queue_wait_us_prev_by_manager": {},
        "premap_consumer_mapping_count": 0,
        "premap_consumer_address_hit_count": 0,
        "premap_consumer_address_miss_count": 0,
        "premap_consumer_descriptor_handle_hit_count": 0,
        "premap_consumer_descriptor_handle_miss_count": 0,
        "premap_consumer_descriptor_handle_parity_ok_count": 0,
        "premap_consumer_prelaunch_boundary_checked_count": 0,
        "premap_consumer_prelaunch_boundary_aligned_count": 0,
        "premap_consumer_prelaunch_handle_available_count": 0,
        "premap_consumer_prelaunch_block_count": 0,
        "premap_consumer_prelaunch_block_size_max": 0,
        "premap_consumer_prelaunch_unique_expert_count": 0,
        "premap_consumer_lookup_after_prepare_count": 0,
        "premap_consumer_real_descriptor_handle_hit_count": 0,
        "premap_consumer_real_descriptor_handle_miss_count": 0,
        "premap_consumer_real_descriptor_handle_available_count": 0,
        "premap_consumer_real_descriptor_handle_packed_weight_hit_count": 0,
        "premap_consumer_real_descriptor_handle_packed_weight_miss_count": 0,
        "premap_consumer_real_descriptor_handle_scale_metadata_hit_count": 0,
        "premap_consumer_real_descriptor_handle_scale_metadata_miss_count": 0,
        "premap_consumer_real_descriptor_handle_aux_metadata_hit_count": 0,
        "premap_consumer_real_descriptor_handle_aux_metadata_miss_count": 0,
        "premap_consumer_real_descriptor_handle_resolver_disabled_count": 0,
        "premap_consumer_real_descriptor_handle_consumer_layer_missing_count": 0,
        "premap_consumer_real_descriptor_handle_expert_map_miss_count": 0,
        "premap_consumer_real_descriptor_handle_no_handle_parts_count": 0,
        "premap_consumer_real_descriptor_handle_new_binding_count": 0,
        "premap_consumer_real_descriptor_handle_reused_binding_count": 0,
        "premap_consumer_real_descriptor_handle_binding_mismatch_count": 0,
        "premap_consumer_real_descriptor_handle_for_address_miss_count": 0,
        "premap_consumer_readonly_lookup_count": 0,
        "premap_consumer_readonly_handle_hit_count": 0,
        "premap_consumer_readonly_handle_miss_count": 0,
        "premap_consumer_readonly_evicted_before_consume_count": 0,
        "premap_consumer_readonly_stale_handle_count": 0,
        "premap_consumer_readonly_handle_parity_ok_count": 0,
        "premap_consumer_readonly_handle_parity_checked_count": 0,
        "premap_consumer_descriptor_prep_lookup_count": 0,
        "premap_consumer_descriptor_prep_attempted_count": 0,
        "premap_consumer_descriptor_prep_executed_count": 0,
        "premap_consumer_descriptor_prep_handle_count": 0,
        "premap_consumer_descriptor_prep_missing_handle_count": 0,
        "premap_consumer_descriptor_prep_descriptor_ptr_count": 0,
        "premap_consumer_descriptor_prep_packed_weight_descriptor_count": 0,
        "premap_consumer_descriptor_prep_scale_metadata_handle_count": 0,
        "premap_consumer_descriptor_prep_real_handle_count": 0,
        "premap_consumer_descriptor_prep_real_handle_miss_count": 0,
        "premap_consumer_descriptor_prep_real_handle_backed_count": 0,
        "premap_consumer_descriptor_prep_consumer_object_count": 0,
        "premap_consumer_descriptor_prep_consumer_object_read_lookup_count": 0,
        "premap_consumer_descriptor_prep_consumer_object_read_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_object_read_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_object_stale_count": 0,
        "premap_consumer_descriptor_prep_consumer_object_read_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_object_read_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_executed_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_object_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source": "",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_min": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_min": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_min": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_object_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_object_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_column_count_min": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_name": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_name_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_name_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_name_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_field_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_handle_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_adapter_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_adapter_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_object_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_object_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_launch_schema_mirror_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_launch_schema_mirror_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_column_count_min": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_name": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_name_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_name_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_name_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_field_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_hit_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_handle_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_schema_present_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_connected_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_enabled_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_eligible_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_blocked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_compatible_with_current_wna16_args_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_min": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason": "",
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash": "",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash": "",
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_execution_ok_count": 0,
        "premap_consumer_descriptor_prep_checked_count": 0,
        "premap_consumer_descriptor_prep_blocked_count": 0,
        "premap_consumer_all_hit_count": 0,
        "premap_consumer_parity_ok_count": 0,
        "premap_consumer_error_count": 0,
        "premap_consumer_payload_violation_count": 0,
        "premap_consumer_router_change_violation_count": 0,
        "premap_consumer_descriptor_order_change_violation_count": 0,
        "premap_consumer_ready_credit_violation_count": 0,
        "premap_consumer_lookup_us_sum": 0.0,
        "premap_consumer_lookup_us_count": 0,
        "candidate_count": 0,
        "outcome_count": 0,
        "outcome_aggregate_count": 0,
        "outcome_aggregate_token_count": 0,
        "outcome_aggregate_topk_entry_count": 0,
        "outcome_aggregate_routed_expert_count_sum": 0,
        "outcome_aggregate_topk_weight_mass_sum": 0.0,
        "outcome_aggregate_top1_weight_sum": 0.0,
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
        "descriptor_window_count_sum": 0,
        "descriptor_order_lru_at_8_sum": 0.0,
        "descriptor_order_lru_at_8_count": 0,
        "descriptor_order_lru_at_16_sum": 0.0,
        "descriptor_order_lru_at_16_count": 0,
        "descriptor_order_hit_rate_sum": 0.0,
        "descriptor_order_hit_rate_count": 0,
        "descriptor_reuse_distance_mean_sum": 0.0,
        "descriptor_reuse_distance_mean_count": 0,
        "descriptor_unique_tiles_per_window_mean_sum": 0.0,
        "descriptor_unique_tiles_per_window_mean_count": 0,
        "descriptor_group_plan_group_count_sum": 0,
        "descriptor_group_plan_avg_group_size_sum": 0.0,
        "descriptor_group_plan_avg_group_size_count": 0,
        "descriptor_group_plan_p95_group_size_sum": 0.0,
        "descriptor_group_plan_p95_group_size_count": 0,
        "descriptor_group_plan_max_group_size_max": 0,
        "descriptor_group_plan_cta_count_sum": 0,
        "descriptor_group_plan_cta_count_count": 0,
        "descriptor_order_gate_allow_count": 0,
        "descriptor_order_gate_evidence_found_count": 0,
        "descriptor_order_mapping_assertion_count": 0,
        "descriptor_order_mapping_same_multiset_count": 0,
        "descriptor_order_mapping_error_count": 0,
        "descriptor_prelaunch_assertion_count": 0,
        "descriptor_prelaunch_same_multiset_count": 0,
        "descriptor_prelaunch_error_count": 0,
        "descriptor_order_reorder_mvp_requested_count": 0,
        "descriptor_order_reorder_mvp_applied_count": 0,
        "descriptor_order_reorder_mvp_fallback_count": 0,
        "descriptor_same_multiset_count": 0,
        "descriptor_order_changed_count": 0,
        "joined_outcome_count": 0,
        "outcome_only_count": 0,
        "summary_only_timeout_count": 0,
    }
    for event in events:
        event_type = event.get("event_type")
        if "premap_payload_cache_resident_count" in event:
            totals["premap_payload_cache_manager_count"] += 1
            manager_id = str(
                event.get("premap_payload_cache_manager_id") or "__global__"
            )
            for key in (
                "premap_payload_cache_issued_fetch_count",
                "premap_payload_cache_used_fetch_count",
                "premap_payload_cache_demand_count",
                "premap_payload_cache_demand_hit_count",
                "premap_payload_cache_demand_miss_count",
                "premap_payload_cache_evicted_before_use_count",
                "premap_payload_cache_ready_late_miss_count",
                "premap_payload_cache_late_completion_unused_count",
                "premap_payload_cache_queue_batch_count",
            ):
                _accumulate_monotonic_snapshot_delta(
                    totals,
                    key,
                    int(event.get(key, 0) or 0),
                    stream_key=manager_id,
                )
            for key in (
                "premap_payload_cache_queue_service_us",
                "premap_payload_cache_queue_wait_us",
            ):
                _accumulate_monotonic_snapshot_float_delta(
                    totals,
                    key,
                    float(event.get(key, 0.0) or 0.0),
                    stream_key=manager_id,
                )
            totals["premap_payload_cache_resident_count_max"] = max(
                int(totals["premap_payload_cache_resident_count_max"]),
                int(event.get("premap_payload_cache_resident_count", 0) or 0),
            )
            totals["premap_payload_cache_unused_fetch_count_max"] = max(
                int(totals["premap_payload_cache_unused_fetch_count_max"]),
                int(event.get("premap_payload_cache_unused_fetch_count", 0) or 0),
            )
            totals["premap_payload_cache_queue_max_delay_us_max"] = max(
                float(totals["premap_payload_cache_queue_max_delay_us_max"]),
                float(event.get("premap_payload_cache_queue_max_delay_us", 0.0) or 0.0),
            )
            totals["premap_payload_cache_queue_total_span_us_max"] = max(
                float(totals["premap_payload_cache_queue_total_span_us_max"]),
                float(event.get("premap_payload_cache_queue_total_span_us", 0.0) or 0.0),
            )
            totals["premap_payload_cache_queue_deadline_us_max"] = max(
                float(totals["premap_payload_cache_queue_deadline_us_max"]),
                float(event.get("premap_payload_cache_queue_deadline_us", 0.0) or 0.0),
            )
            totals["premap_payload_cache_queue_batch_size_max"] = max(
                int(totals["premap_payload_cache_queue_batch_size_max"]),
                int(event.get("premap_payload_cache_queue_batch_size", 0) or 0),
            )
            totals["premap_payload_cache_demand_hit_rate_sum"] += float(
                event.get("premap_payload_cache_demand_hit_rate", 0.0) or 0.0
            )
            totals["premap_payload_cache_used_fetch_rate_sum"] += float(
                event.get("premap_payload_cache_used_fetch_rate", 0.0) or 0.0
            )
            totals["premap_payload_cache_eviction_pressure_sum"] += float(
                event.get("premap_payload_cache_eviction_pressure", 0.0) or 0.0
            )
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
                totals["descriptor_summary_full_count"] += 1
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
                for value_key, sum_key, count_key in (
                    (
                        "descriptor_order_lru_at_8",
                        "descriptor_order_lru_at_8_sum",
                        "descriptor_order_lru_at_8_count",
                    ),
                    (
                        "descriptor_order_lru_at_16",
                        "descriptor_order_lru_at_16_sum",
                        "descriptor_order_lru_at_16_count",
                    ),
                    (
                        "descriptor_order_hit_rate",
                        "descriptor_order_hit_rate_sum",
                        "descriptor_order_hit_rate_count",
                    ),
                    (
                        "descriptor_reuse_distance_mean",
                        "descriptor_reuse_distance_mean_sum",
                        "descriptor_reuse_distance_mean_count",
                    ),
                    (
                        "descriptor_unique_tiles_per_window_mean",
                        "descriptor_unique_tiles_per_window_mean_sum",
                        "descriptor_unique_tiles_per_window_mean_count",
                    ),
                ):
                    if value_key in event:
                        totals[sum_key] += float(event.get(value_key, 0.0) or 0.0)
                        totals[count_key] += 1
                _accumulate_group_plan_totals(totals, event)
                totals["descriptor_same_multiset_count"] += int(
                    bool(event.get("descriptor_same_multiset", False))
                )
                totals["descriptor_order_changed_count"] += int(
                    bool(event.get("descriptor_order_changed", False))
                )
        elif event_type == "descriptor_summary_min":
            totals["descriptor_summary_min_count"] += 1
            totals["descriptor_order_summary_count"] += 1
            totals["descriptor_order_build_us_sum"] += float(
                event.get("descriptor_order_build_us", 0.0) or 0.0
            )
            totals["descriptor_tile_request_count"] += int(
                event.get("descriptor_tile_request_count", 0) or 0
            )
            totals["descriptor_unique_b_tiles_sum"] += int(
                event.get("descriptor_unique_b_tiles", 0) or 0
            )
            totals["descriptor_window_count_sum"] += int(
                event.get("descriptor_window_count", 0) or 0
            )
            totals["decision_us_sum"] += float(event.get("decision_us", 0.0) or 0.0)
            totals["candidate_construction_us_sum"] += float(
                event.get("candidate_construction_us", 0.0) or 0.0
            )
            totals["counter_update_us_sum"] += float(
                event.get("counter_update_us", 0.0) or 0.0
            )
            _accumulate_group_plan_totals(totals, event)
            totals["descriptor_order_gate_allow_count"] += int(
                bool(event.get("descriptor_order_gate_allow", False))
            )
            totals["descriptor_order_gate_evidence_found_count"] += int(
                bool(event.get("descriptor_order_gate_evidence_found", False))
            )
            if "descriptor_order_mapping_assertion_mode" in event:
                totals["descriptor_order_mapping_assertion_count"] += 1
                totals["descriptor_order_mapping_same_multiset_count"] += int(
                    bool(event.get("descriptor_order_mapping_same_multiset", False))
                )
                totals["descriptor_order_mapping_error_count"] += int(
                    bool(event.get("descriptor_order_mapping_error"))
                )
        elif event_type == "descriptor_prelaunch_assertion":
            totals["descriptor_prelaunch_assertion_count"] += 1
            totals["descriptor_prelaunch_same_multiset_count"] += int(
                bool(event.get("descriptor_order_prelaunch_same_multiset", False))
            )
            totals["descriptor_prelaunch_error_count"] += int(
                bool(event.get("descriptor_order_prelaunch_error"))
            )
            totals["descriptor_order_reorder_mvp_requested_count"] += int(
                bool(event.get("descriptor_order_reorder_mvp_requested", False))
            )
            totals["descriptor_order_reorder_mvp_applied_count"] += int(
                bool(event.get("descriptor_order_reorder_mvp_applied", False))
            )
            totals["descriptor_order_reorder_mvp_fallback_count"] += int(
                bool(event.get("descriptor_order_reorder_mvp_fallback_reason"))
            )
        elif event_type == "premap_summary":
            totals["premap_summary_count"] += 1
            totals["premap_summary_descriptor_count"] += int(
                event.get("premap_descriptor_count", 0) or 0
            )
            totals["premap_summary_unique_experts_sum"] += int(
                event.get("premap_unique_experts", 0) or 0
            )
            totals["premap_summary_unique_layers_sum"] += int(
                event.get("premap_unique_layers", 0) or 0
            )
            totals["premap_summary_unique_sample_layers_sum"] += int(
                event.get("premap_unique_sample_layers", 0) or 0
            )
            totals["premap_summary_actual_bytes"] += int(
                event.get("premap_actual_bytes", 0) or 0
            )
            totals["premap_summary_payload_bytes"] += int(
                event.get("premap_payload_bytes", 0) or 0
            )
            if "premap_build_us" in event:
                totals["premap_summary_build_us_sum"] += float(
                    event.get("premap_build_us", 0.0) or 0.0
                )
                totals["premap_summary_build_us_count"] += 1
            totals["decision_us_sum"] += float(event.get("decision_us", 0.0) or 0.0)
            totals["candidate_construction_us_sum"] += float(
                event.get("candidate_construction_us", 0.0) or 0.0
            )
            totals["counter_update_us_sum"] += float(
                event.get("counter_update_us", 0.0) or 0.0
            )
            totals["logging_us_sum"] += float(event.get("logging_us", 0.0) or 0.0)
            totals["premap_summary_payload_violation_count"] += int(
                int(event.get("premap_payload_bytes", 0) or 0) != 0
            )
            totals["premap_summary_full_fetch_violation_count"] += int(
                int(event.get("premap_full_fetch_count", 0) or 0) != 0
            )
            totals["premap_summary_metadata_violation_count"] += int(
                int(event.get("premap_metadata_count", 0) or 0) != 0
            )
            totals["premap_summary_router_change_violation_count"] += int(
                bool(event.get("premap_changes_router", False))
            )
            totals["premap_summary_descriptor_order_change_violation_count"] += int(
                bool(event.get("premap_changes_descriptor_order", False))
            )
            totals["premap_summary_ready_credit_violation_count"] += int(
                bool(event.get("premap_ready_credit", False))
            )
            totals["premap_summary_error_count"] += int(
                bool(event.get("premap_error"))
            )
            if "premap_address_resident_count" in event:
                totals["premap_address_manager_count"] += 1
                _accumulate_monotonic_snapshot_delta(
                    totals,
                    "premap_address_new_count",
                    int(event.get("premap_address_new_count", 0) or 0),
                )
                _accumulate_monotonic_snapshot_delta(
                    totals,
                    "premap_address_reused_count",
                    int(event.get("premap_address_reused_count", 0) or 0),
                )
                _accumulate_monotonic_snapshot_delta(
                    totals,
                    "premap_address_evicted_count",
                    int(event.get("premap_address_evicted_count", 0) or 0),
                )
                totals["premap_address_resident_count_max"] = max(
                    int(totals["premap_address_resident_count_max"]),
                    int(event.get("premap_address_resident_count", 0) or 0),
                )
                totals["premap_address_resident_descriptor_bytes_max"] = max(
                    int(totals["premap_address_resident_descriptor_bytes_max"]),
                    int(event.get("premap_address_resident_descriptor_bytes", 0) or 0),
                )
                totals["premap_address_prepared_descriptor_actual_bytes_max"] = max(
                    int(totals["premap_address_prepared_descriptor_actual_bytes_max"]),
                    int(
                        event.get(
                            "premap_address_prepared_descriptor_actual_bytes",
                            0,
                        )
                        or 0
                    ),
                )
                totals["premap_address_reuse_rate_sum"] += float(
                    event.get("premap_address_reuse_rate", 0.0) or 0.0
                )
                totals["premap_address_eviction_pressure_sum"] += float(
                    event.get("premap_address_eviction_pressure", 0.0) or 0.0
                )
        elif event_type == "premap_consumer_mapping":
            totals["premap_consumer_mapping_count"] += 1
            totals["premap_consumer_address_hit_count"] += int(
                event.get("premap_consumer_address_hit_count", 0) or 0
            )
            totals["premap_consumer_address_miss_count"] += int(
                event.get("premap_consumer_address_miss_count", 0) or 0
            )
            totals["premap_consumer_descriptor_handle_hit_count"] += int(
                event.get("premap_consumer_descriptor_handle_hit_count", 0) or 0
            )
            totals["premap_consumer_descriptor_handle_miss_count"] += int(
                event.get("premap_consumer_descriptor_handle_miss_count", 0) or 0
            )
            totals["premap_consumer_descriptor_handle_parity_ok_count"] += int(
                bool(event.get("premap_consumer_descriptor_handle_parity_ok", False))
            )
            if "premap_consumer_prelaunch_boundary_source" in event:
                totals["premap_consumer_prelaunch_boundary_checked_count"] += 1
                totals["premap_consumer_prelaunch_boundary_aligned_count"] += int(
                    bool(event.get("premap_consumer_prelaunch_boundary_aligned", False))
                )
                totals["premap_consumer_prelaunch_handle_available_count"] += int(
                    bool(event.get("premap_consumer_prelaunch_handle_available", False))
                )
                totals["premap_consumer_prelaunch_block_count"] += int(
                    event.get("premap_consumer_prelaunch_block_count", 0) or 0
                )
                totals["premap_consumer_prelaunch_block_size_max"] = max(
                    int(totals["premap_consumer_prelaunch_block_size_max"]),
                    int(event.get("premap_consumer_prelaunch_block_size", 0) or 0),
                )
                totals["premap_consumer_prelaunch_unique_expert_count"] += int(
                    event.get("premap_consumer_prelaunch_unique_expert_count", 0) or 0
                )
            totals["premap_consumer_lookup_after_prepare_count"] += int(
                bool(event.get("premap_consumer_lookup_after_prepare", False))
            )
            totals["premap_consumer_real_descriptor_handle_hit_count"] += int(
                event.get("premap_consumer_real_descriptor_handle_hit_count", 0) or 0
            )
            totals["premap_consumer_real_descriptor_handle_miss_count"] += int(
                event.get("premap_consumer_real_descriptor_handle_miss_count", 0) or 0
            )
            totals["premap_consumer_real_descriptor_handle_available_count"] += int(
                bool(event.get("premap_consumer_real_descriptor_handle_available", False))
            )
            source_hit_counts = event.get(
                "premap_consumer_real_descriptor_handle_source_hit_counts",
                {},
            )
            source_miss_counts = event.get(
                "premap_consumer_real_descriptor_handle_source_miss_counts",
                {},
            )
            if isinstance(source_hit_counts, dict):
                for source in ("packed_weight", "scale_metadata", "aux_metadata"):
                    totals[
                        f"premap_consumer_real_descriptor_handle_{source}_hit_count"
                    ] += int(source_hit_counts.get(source, 0) or 0)
            if isinstance(source_miss_counts, dict):
                for source in ("packed_weight", "scale_metadata", "aux_metadata"):
                    totals[
                        f"premap_consumer_real_descriptor_handle_{source}_miss_count"
                    ] += int(source_miss_counts.get(source, 0) or 0)
            miss_reason_counts = event.get(
                "premap_consumer_real_descriptor_handle_miss_reason_counts",
                {},
            )
            if isinstance(miss_reason_counts, dict):
                for reason in (
                    "resolver_disabled",
                    "consumer_layer_missing",
                    "expert_map_miss",
                    "no_handle_parts",
                ):
                    totals[
                        f"premap_consumer_real_descriptor_handle_{reason}_count"
                    ] += int(miss_reason_counts.get(reason, 0) or 0)
            totals["premap_consumer_real_descriptor_handle_new_binding_count"] += int(
                event.get("premap_consumer_real_descriptor_handle_new_binding_count", 0) or 0
            )
            totals["premap_consumer_real_descriptor_handle_reused_binding_count"] += int(
                event.get("premap_consumer_real_descriptor_handle_reused_binding_count", 0) or 0
            )
            totals["premap_consumer_real_descriptor_handle_binding_mismatch_count"] += int(
                event.get("premap_consumer_real_descriptor_handle_binding_mismatch_count", 0) or 0
            )
            totals["premap_consumer_real_descriptor_handle_for_address_miss_count"] += int(
                event.get("premap_consumer_real_descriptor_handle_for_address_miss_count", 0) or 0
            )
            totals["premap_consumer_readonly_lookup_count"] += int(
                event.get("premap_consumer_readonly_lookup_count", 0) or 0
            )
            totals["premap_consumer_readonly_handle_hit_count"] += int(
                event.get("premap_consumer_readonly_handle_hit_count", 0) or 0
            )
            totals["premap_consumer_readonly_handle_miss_count"] += int(
                event.get("premap_consumer_readonly_handle_miss_count", 0) or 0
            )
            totals["premap_consumer_readonly_evicted_before_consume_count"] += int(
                event.get("premap_consumer_readonly_evicted_before_consume_count", 0) or 0
            )
            totals["premap_consumer_readonly_stale_handle_count"] += int(
                event.get("premap_consumer_readonly_stale_handle_count", 0) or 0
            )
            if "premap_consumer_readonly_handle_parity_ok" in event:
                totals["premap_consumer_readonly_handle_parity_checked_count"] += 1
                totals["premap_consumer_readonly_handle_parity_ok_count"] += int(
                    bool(event.get("premap_consumer_readonly_handle_parity_ok", False))
                )
            totals["premap_consumer_descriptor_prep_lookup_count"] += int(
                event.get("premap_consumer_descriptor_prep_lookup_count", 0) or 0
            )
            totals["premap_consumer_descriptor_prep_handle_count"] += int(
                event.get("premap_consumer_descriptor_prep_handle_count", 0) or 0
            )
            totals["premap_consumer_descriptor_prep_missing_handle_count"] += int(
                event.get("premap_consumer_descriptor_prep_missing_handle_count", 0) or 0
            )
            totals["premap_consumer_descriptor_prep_descriptor_ptr_count"] += int(
                event.get("premap_consumer_descriptor_prep_descriptor_ptr_count", 0) or 0
            )
            totals["premap_consumer_descriptor_prep_packed_weight_descriptor_count"] += int(
                event.get(
                    "premap_consumer_descriptor_prep_packed_weight_descriptor_count",
                    0,
                )
                or 0
            )
            totals["premap_consumer_descriptor_prep_scale_metadata_handle_count"] += int(
                event.get(
                    "premap_consumer_descriptor_prep_scale_metadata_handle_count",
                    0,
                )
                or 0
            )
            totals["premap_consumer_descriptor_prep_real_handle_count"] += int(
                event.get("premap_consumer_descriptor_prep_real_handle_count", 0) or 0
            )
            totals["premap_consumer_descriptor_prep_real_handle_miss_count"] += int(
                event.get("premap_consumer_descriptor_prep_real_handle_miss_count", 0)
                or 0
            )
            totals["premap_consumer_descriptor_prep_real_handle_backed_count"] += int(
                bool(
                    event.get(
                        "premap_consumer_descriptor_prep_real_handle_backed",
                        False,
                    )
                )
            )
            totals["premap_consumer_descriptor_prep_consumer_object_count"] += int(
                event.get(
                    "premap_consumer_descriptor_prep_consumer_object_count",
                    0,
                )
                or 0
            )
            totals[
                "premap_consumer_descriptor_prep_consumer_object_read_lookup_count"
            ] += int(
                event.get(
                    "premap_consumer_descriptor_prep_consumer_object_read_lookup_count",
                    0,
                )
                or 0
            )
            totals[
                "premap_consumer_descriptor_prep_consumer_object_read_hit_count"
            ] += int(
                event.get(
                    "premap_consumer_descriptor_prep_consumer_object_read_hit_count",
                    0,
                )
                or 0
            )
            totals[
                "premap_consumer_descriptor_prep_consumer_object_read_miss_count"
            ] += int(
                event.get(
                    "premap_consumer_descriptor_prep_consumer_object_read_miss_count",
                    0,
                )
                or 0
            )
            totals[
                "premap_consumer_descriptor_prep_consumer_object_stale_count"
            ] += int(
                event.get(
                    "premap_consumer_descriptor_prep_consumer_object_stale_count",
                    0,
                )
                or 0
            )
            if "premap_consumer_descriptor_prep_consumer_object_read_ok" in event:
                totals[
                    "premap_consumer_descriptor_prep_consumer_object_read_checked_count"
                ] += 1
                totals[
                    "premap_consumer_descriptor_prep_consumer_object_read_ok_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_object_read_ok",
                            False,
                        )
                    )
                )
            if "premap_consumer_descriptor_prep_consumer_shim_mode" in event:
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_executed_count"
                ] += 1
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_object_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_object_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max"
                ] = max(
                    int(
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max"
                        ]
                    ),
                    int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count",
                            0,
                        )
                        or 0
                    ),
                )
                if (
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok"
                    in event
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok",
                                False,
                            )
                        )
                    )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count"
                ] += int(
                    int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes",
                            0,
                        )
                        or 0
                    )
                    != 0
                )
                if (
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                    in event
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok",
                                False,
                            )
                        )
                    )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max"
                ] = max(
                    int(
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max"
                        ]
                    ),
                    int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count",
                            0,
                        )
                        or 0
                    ),
                )
                consume_schema_hash = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash"
                )
                if consume_schema_hash:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_checked_count"
                    ] += 1
                    if not totals[
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash"
                        ] = str(consume_schema_hash)
                    elif (
                        str(consume_schema_hash)
                        != totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash"
                        ]
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_mismatch_count"
                        ] += 1
                elif (
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                    in event
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_missing_count"
                    ] += 1
                if (
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                    in event
                ):
                    consume_mode = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
                    )
                    if consume_mode:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
                            ] = str(consume_mode)
                        if (
                            str(consume_mode)
                            != "readonly_consume_kernel_arg_shadow_table"
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_missing_count"
                        ] += 1
                    consume_source = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
                    )
                    expected_source = event.get(
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_order_source"
                    )
                    if consume_source:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
                            ] = str(consume_source)
                        if not expected_source or str(consume_source) != str(
                            expected_source
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_missing_count"
                        ] += 1
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count",
                        0,
                    )
                    or 0
                )
                for field in (
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count",
                ):
                    totals[field] += int(event.get(field, 0) or 0)
                table_consume_source_hits = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_hit_counts",
                    {},
                )
                table_consume_source_misses = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_miss_counts",
                    {},
                )
                if isinstance(table_consume_source_hits, dict):
                    for source in (
                        "descriptor_ptr",
                        "packed_weight_descriptor",
                        "scale_metadata_handle",
                        "aux_metadata_handle",
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_"
                            f"{source}_hit_count"
                        ] += int(table_consume_source_hits.get(source, 0) or 0)
                if isinstance(table_consume_source_misses, dict):
                    for source in (
                        "descriptor_ptr",
                        "packed_weight_descriptor",
                        "scale_metadata_handle",
                        "aux_metadata_handle",
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_"
                            f"{source}_miss_count"
                        ] += int(table_consume_source_misses.get(source, 0) or 0)
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_violation_count"
                ] += int(
                    int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes",
                            0,
                        )
                        or 0
                    )
                    != 0
                )
                handoff_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode"
                )
                if handoff_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_checked_count"
                    ] += 1
                    if not totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode"
                        ] = str(handoff_mode)
                    elif (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode"
                        ]
                        != str(handoff_mode)
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_mismatch_count"
                        ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready",
                                False,
                            )
                        )
                    )
                    handoff_column_count = int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count",
                            0,
                        )
                        or 0
                    )
                    if handoff_column_count > totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max"
                        ] = handoff_column_count
                    if (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min"
                        ]
                        == 0
                        or handoff_column_count
                        < totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min"
                        ]
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min"
                        ] = handoff_column_count
                    handoff_schema_hash = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
                    )
                    if handoff_schema_hash:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
                            ] = str(handoff_schema_hash)
                        elif (
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
                            ]
                            != str(handoff_schema_hash)
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count"
                        ] += 1
                    for field in (
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_violation_count"
                    ] += int(
                        int(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes",
                                0,
                            )
                            or 0
                        )
                        != 0
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel",
                                False,
                            )
                        )
                    )
                elif event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_missing_count"
                    ] += 1
                slot_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode"
                )
                if slot_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_checked_count"
                    ] += 1
                    if not totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode"
                        ] = str(slot_mode)
                    elif (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode"
                        ]
                        != str(slot_mode)
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_mismatch_count"
                        ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready",
                                False,
                            )
                        )
                    )
                    slot_hash = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash"
                    )
                    if slot_hash:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_checked_count"
                        ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_missing_count"
                        ] += 1
                    slot_column_count = int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count",
                            0,
                        )
                        or 0
                    )
                    if slot_column_count > totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_max"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_max"
                        ] = slot_column_count
                    if (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_min"
                        ]
                        == 0
                        or slot_column_count
                        < totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_min"
                        ]
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_min"
                        ] = slot_column_count
                    slot_schema_hash = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash"
                    )
                    if slot_schema_hash:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash"
                            ] = str(slot_schema_hash)
                        elif (
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash"
                            ]
                            != str(slot_schema_hash)
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_missing_count"
                        ] += 1
                    for field in (
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_violation_count"
                    ] += int(
                        int(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes",
                                0,
                            )
                            or 0
                        )
                        != 0
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_kernel_arg_violation_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                elif event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_missing_count"
                    ] += 1
                mirror_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode"
                )
                if mirror_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_checked_count"
                    ] += 1
                    if not totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode"
                        ] = str(mirror_mode)
                    elif (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode"
                        ]
                        != str(mirror_mode)
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_mismatch_count"
                        ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready",
                                False,
                            )
                        )
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    mirror_column_count = int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count",
                            0,
                        )
                        or 0
                    )
                    if mirror_column_count > totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_max"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_max"
                        ] = mirror_column_count
                    if (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_min"
                        ]
                        == 0
                        or mirror_column_count
                        < totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_min"
                        ]
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_min"
                        ] = mirror_column_count
                    mirror_schema_hash = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash"
                    )
                    if mirror_schema_hash:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash"
                            ] = str(mirror_schema_hash)
                        elif (
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash"
                            ]
                            != str(mirror_schema_hash)
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_missing_count"
                        ] += 1
                    for field in (
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_violation_count"
                    ] += int(
                        int(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes",
                                0,
                            )
                            or 0
                        )
                        != 0
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_kernel_arg_violation_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                elif event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_missing_count"
                    ] += 1
                launch_schema_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode"
                )
                if launch_schema_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_checked_count"
                    ] += 1
                    if not totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode"
                        ] = str(launch_schema_mode)
                    elif (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode"
                        ]
                        != str(launch_schema_mode)
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_mismatch_count"
                        ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready",
                                False,
                            )
                        )
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    launch_column_count = int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count",
                            0,
                        )
                        or 0
                    )
                    if launch_column_count > totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_max"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_max"
                        ] = launch_column_count
                    if (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_min"
                        ]
                        == 0
                        or launch_column_count
                        < totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_min"
                        ]
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_min"
                        ] = launch_column_count
                    for value_field, base_key in (
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash",
                        ),
                    ):
                        value = event.get(value_field)
                        if value:
                            totals[f"{base_key}_checked_count"] += 1
                            if not totals[base_key]:
                                totals[base_key] = str(value)
                            elif totals[base_key] != str(value):
                                totals[f"{base_key}_mismatch_count"] += 1
                        else:
                            totals[f"{base_key}_missing_count"] += 1
                    for field in (
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_violation_count"
                    ] += int(
                        int(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes",
                                0,
                            )
                            or 0
                        )
                        != 0
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_kernel_arg_violation_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                elif event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_missing_count"
                    ] += 1
                semantic_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode"
                )
                if semantic_mode is not None:
                    semantic_prefix = (
                        "premap_consumer_descriptor_prep_consumer_shim_"
                        "kernel_arg_semantic_handle_adapter"
                    )
                    totals[f"{semantic_prefix}_checked_count"] += 1
                    totals[f"{semantic_prefix}_mode_checked_count"] += 1
                    if not totals[f"{semantic_prefix}_mode"]:
                        totals[f"{semantic_prefix}_mode"] = str(semantic_mode)
                    elif totals[f"{semantic_prefix}_mode"] != str(semantic_mode):
                        totals[f"{semantic_prefix}_mode_mismatch_count"] += 1
                    totals[f"{semantic_prefix}_ready_count"] += int(
                        bool(
                            event.get(
                                f"{semantic_prefix}_ready",
                                False,
                            )
                        )
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            f"{semantic_prefix}_hash",
                            f"{semantic_prefix}_hash_checked_count",
                            f"{semantic_prefix}_hash_missing_count",
                        ),
                        (
                            f"{semantic_prefix}_table_object_hash",
                            f"{semantic_prefix}_table_object_hash_checked_count",
                            f"{semantic_prefix}_table_object_hash_missing_count",
                        ),
                        (
                            f"{semantic_prefix}_launch_schema_mirror_hash",
                            f"{semantic_prefix}_launch_schema_mirror_hash_checked_count",
                            f"{semantic_prefix}_launch_schema_mirror_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    semantic_column_count = int(
                        event.get(f"{semantic_prefix}_column_count", 0) or 0
                    )
                    if (
                        semantic_column_count
                        > totals[f"{semantic_prefix}_column_count_max"]
                    ):
                        totals[
                            f"{semantic_prefix}_column_count_max"
                        ] = semantic_column_count
                    if (
                        totals[f"{semantic_prefix}_column_count_min"] == 0
                        or semantic_column_count
                        < totals[f"{semantic_prefix}_column_count_min"]
                    ):
                        totals[
                            f"{semantic_prefix}_column_count_min"
                        ] = semantic_column_count
                    for value_field, base_key in (
                        (
                            f"{semantic_prefix}_table_schema_hash",
                            f"{semantic_prefix}_table_schema_hash",
                        ),
                        (
                            f"{semantic_prefix}_semantic_schema_name",
                            f"{semantic_prefix}_semantic_schema_name",
                        ),
                        (
                            f"{semantic_prefix}_semantic_schema_hash",
                            f"{semantic_prefix}_semantic_schema_hash",
                        ),
                    ):
                        value = event.get(value_field)
                        if value:
                            totals[f"{base_key}_checked_count"] += 1
                            if not totals[base_key]:
                                totals[base_key] = str(value)
                            elif totals[base_key] != str(value):
                                totals[f"{base_key}_mismatch_count"] += 1
                        else:
                            totals[f"{base_key}_missing_count"] += 1
                    for field in (
                        f"{semantic_prefix}_row_count",
                        f"{semantic_prefix}_semantic_field_count",
                        f"{semantic_prefix}_required_source_hit_count",
                        f"{semantic_prefix}_required_source_miss_count",
                        f"{semantic_prefix}_optional_source_hit_count",
                        f"{semantic_prefix}_optional_source_miss_count",
                        f"{semantic_prefix}_handle_field_read_count",
                        f"{semantic_prefix}_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    semantic_payload_bytes = int(
                        event.get(f"{semantic_prefix}_payload_bytes", 0) or 0
                    )
                    totals[f"{semantic_prefix}_payload_violation_count"] += int(
                        semantic_payload_bytes != 0
                    )
                    totals[f"{semantic_prefix}_passed_to_kernel_count"] += int(
                        bool(event.get(f"{semantic_prefix}_passed_to_kernel", False))
                    )
                    totals[f"{semantic_prefix}_kernel_arg_violation_count"] += int(
                        bool(
                            event.get(
                                f"{semantic_prefix}_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                    totals[
                        f"{semantic_prefix}_live_compatible_with_current_wna16_args_count"
                    ] += int(
                        bool(
                            event.get(
                                f"{semantic_prefix}_live_compatible_with_current_wna16_args",
                                False,
                            )
                        )
                    )
                elif launch_schema_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode_missing_count"
                    ] += 1
                single_field_prefix = (
                    "premap_consumer_descriptor_prep_consumer_shim_"
                    "single_field_handle_handoff_canary"
                )
                single_field_mode = event.get(f"{single_field_prefix}_mode")
                if single_field_mode is not None:
                    for key, default in (
                        (f"{single_field_prefix}_checked_count", 0),
                        (f"{single_field_prefix}_ready_count", 0),
                        (f"{single_field_prefix}_mode", ""),
                        (f"{single_field_prefix}_mode_checked_count", 0),
                        (f"{single_field_prefix}_mode_mismatch_count", 0),
                        (f"{single_field_prefix}_hash_checked_count", 0),
                        (f"{single_field_prefix}_hash_missing_count", 0),
                        (f"{single_field_prefix}_field_name", ""),
                        (f"{single_field_prefix}_field_name_checked_count", 0),
                        (f"{single_field_prefix}_field_name_missing_count", 0),
                        (f"{single_field_prefix}_field_name_mismatch_count", 0),
                        (f"{single_field_prefix}_source", ""),
                        (f"{single_field_prefix}_source_checked_count", 0),
                        (f"{single_field_prefix}_source_missing_count", 0),
                        (f"{single_field_prefix}_source_mismatch_count", 0),
                        (f"{single_field_prefix}_mirror_mode", ""),
                        (f"{single_field_prefix}_mirror_mode_checked_count", 0),
                        (f"{single_field_prefix}_mirror_mode_missing_count", 0),
                        (f"{single_field_prefix}_mirror_mode_mismatch_count", 0),
                        (f"{single_field_prefix}_mirror_ready_count", 0),
                        (f"{single_field_prefix}_mirror_field_name", ""),
                        (
                            f"{single_field_prefix}_mirror_field_name_checked_count",
                            0,
                        ),
                        (
                            f"{single_field_prefix}_mirror_field_name_missing_count",
                            0,
                        ),
                        (
                            f"{single_field_prefix}_mirror_field_name_mismatch_count",
                            0,
                        ),
                        (f"{single_field_prefix}_mirror_source", ""),
                        (f"{single_field_prefix}_mirror_source_checked_count", 0),
                        (f"{single_field_prefix}_mirror_source_missing_count", 0),
                        (f"{single_field_prefix}_mirror_source_mismatch_count", 0),
                        (f"{single_field_prefix}_table_object_hash_checked_count", 0),
                        (f"{single_field_prefix}_table_object_hash_missing_count", 0),
                        (
                            f"{single_field_prefix}_semantic_adapter_hash_checked_count",
                            0,
                        ),
                        (
                            f"{single_field_prefix}_semantic_adapter_hash_missing_count",
                            0,
                        ),
                        (f"{single_field_prefix}_field_handle_hash_checked_count", 0),
                        (f"{single_field_prefix}_field_handle_hash_missing_count", 0),
                        (
                            f"{single_field_prefix}_semantic_field_hash_checked_count",
                            0,
                        ),
                        (
                            f"{single_field_prefix}_semantic_field_hash_missing_count",
                            0,
                        ),
                        (f"{single_field_prefix}_mirror_handle_hash_checked_count", 0),
                        (f"{single_field_prefix}_mirror_handle_hash_missing_count", 0),
                        (f"{single_field_prefix}_mirror_schema_hash_checked_count", 0),
                        (f"{single_field_prefix}_mirror_schema_hash_missing_count", 0),
                        (f"{single_field_prefix}_block_reason", ""),
                        (f"{single_field_prefix}_block_reason_checked_count", 0),
                        (f"{single_field_prefix}_block_reason_missing_count", 0),
                        (f"{single_field_prefix}_block_reason_mismatch_count", 0),
                        (f"{single_field_prefix}_row_count", 0),
                        (f"{single_field_prefix}_field_handle_count", 0),
                        (f"{single_field_prefix}_field_handle_nonzero_count", 0),
                        (f"{single_field_prefix}_field_handle_zero_count", 0),
                        (f"{single_field_prefix}_parity_ok_count", 0),
                        (f"{single_field_prefix}_parity_mismatch_count", 0),
                        (f"{single_field_prefix}_live_enabled_count", 0),
                        (f"{single_field_prefix}_blocked_count", 0),
                        (
                            f"{single_field_prefix}_kernel_side_typed_consumer_compatible_count",
                            0,
                        ),
                        (
                            f"{single_field_prefix}_current_wna16_arg_compatible_count",
                            0,
                        ),
                        (f"{single_field_prefix}_payload_bytes", 0),
                        (f"{single_field_prefix}_payload_violation_count", 0),
                        (f"{single_field_prefix}_ready_credit_count", 0),
                        (f"{single_field_prefix}_passed_to_kernel_count", 0),
                        (
                            f"{single_field_prefix}_changes_kernel_launch_args_count",
                            0,
                        ),
                        (f"{single_field_prefix}_kernel_arg_violation_count", 0),
                        (
                            f"{single_field_prefix}_live_compatible_with_current_wna16_args_count",
                            0,
                        ),
                    ):
                        totals.setdefault(key, default)
                    totals[f"{single_field_prefix}_checked_count"] += 1
                    totals[f"{single_field_prefix}_mode_checked_count"] += 1
                    if not totals[f"{single_field_prefix}_mode"]:
                        totals[f"{single_field_prefix}_mode"] = str(single_field_mode)
                    elif totals[f"{single_field_prefix}_mode"] != str(
                        single_field_mode
                    ):
                        totals[f"{single_field_prefix}_mode_mismatch_count"] += 1
                    totals[f"{single_field_prefix}_ready_count"] += int(
                        bool(event.get(f"{single_field_prefix}_ready", False))
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            f"{single_field_prefix}_hash",
                            f"{single_field_prefix}_hash_checked_count",
                            f"{single_field_prefix}_hash_missing_count",
                        ),
                        (
                            f"{single_field_prefix}_table_object_hash",
                            f"{single_field_prefix}_table_object_hash_checked_count",
                            f"{single_field_prefix}_table_object_hash_missing_count",
                        ),
                        (
                            f"{single_field_prefix}_semantic_adapter_hash",
                            f"{single_field_prefix}_semantic_adapter_hash_checked_count",
                            f"{single_field_prefix}_semantic_adapter_hash_missing_count",
                        ),
                        (
                            f"{single_field_prefix}_field_handle_hash",
                            f"{single_field_prefix}_field_handle_hash_checked_count",
                            f"{single_field_prefix}_field_handle_hash_missing_count",
                        ),
                        (
                            f"{single_field_prefix}_semantic_field_hash",
                            f"{single_field_prefix}_semantic_field_hash_checked_count",
                            f"{single_field_prefix}_semantic_field_hash_missing_count",
                        ),
                        (
                            f"{single_field_prefix}_mirror_handle_hash",
                            f"{single_field_prefix}_mirror_handle_hash_checked_count",
                            f"{single_field_prefix}_mirror_handle_hash_missing_count",
                        ),
                        (
                            f"{single_field_prefix}_mirror_schema_hash",
                            f"{single_field_prefix}_mirror_schema_hash_checked_count",
                            f"{single_field_prefix}_mirror_schema_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    for value_field, base_key in (
                        (f"{single_field_prefix}_field_name", f"{single_field_prefix}_field_name"),
                        (f"{single_field_prefix}_source", f"{single_field_prefix}_source"),
                        (
                            f"{single_field_prefix}_mirror_mode",
                            f"{single_field_prefix}_mirror_mode",
                        ),
                        (
                            f"{single_field_prefix}_mirror_field_name",
                            f"{single_field_prefix}_mirror_field_name",
                        ),
                        (
                            f"{single_field_prefix}_mirror_source",
                            f"{single_field_prefix}_mirror_source",
                        ),
                        (f"{single_field_prefix}_block_reason", f"{single_field_prefix}_block_reason"),
                    ):
                        value = event.get(value_field)
                        if value:
                            totals[f"{base_key}_checked_count"] += 1
                            if not totals[base_key]:
                                totals[base_key] = str(value)
                            elif totals[base_key] != str(value):
                                totals[f"{base_key}_mismatch_count"] += 1
                        else:
                            totals[f"{base_key}_missing_count"] += 1
                    for field in (
                        f"{single_field_prefix}_row_count",
                        f"{single_field_prefix}_field_handle_count",
                        f"{single_field_prefix}_field_handle_nonzero_count",
                        f"{single_field_prefix}_field_handle_zero_count",
                        f"{single_field_prefix}_parity_ok_count",
                        f"{single_field_prefix}_parity_mismatch_count",
                        f"{single_field_prefix}_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    for flag_field, count_key in (
                        (
                            f"{single_field_prefix}_live_enabled",
                            f"{single_field_prefix}_live_enabled_count",
                        ),
                        (
                            f"{single_field_prefix}_blocked",
                            f"{single_field_prefix}_blocked_count",
                        ),
                        (
                            f"{single_field_prefix}_mirror_ready",
                            f"{single_field_prefix}_mirror_ready_count",
                        ),
                        (
                            f"{single_field_prefix}_kernel_side_typed_consumer_compatible",
                            f"{single_field_prefix}_kernel_side_typed_consumer_compatible_count",
                        ),
                        (
                            f"{single_field_prefix}_current_wna16_arg_compatible",
                            f"{single_field_prefix}_current_wna16_arg_compatible_count",
                        ),
                        (
                            f"{single_field_prefix}_ready_credit",
                            f"{single_field_prefix}_ready_credit_count",
                        ),
                        (
                            f"{single_field_prefix}_passed_to_kernel",
                            f"{single_field_prefix}_passed_to_kernel_count",
                        ),
                        (
                            f"{single_field_prefix}_changes_kernel_launch_args",
                            f"{single_field_prefix}_changes_kernel_launch_args_count",
                        ),
                        (
                            f"{single_field_prefix}_live_compatible_with_current_wna16_args",
                            f"{single_field_prefix}_live_compatible_with_current_wna16_args_count",
                        ),
                    ):
                        totals[count_key] += int(bool(event.get(flag_field, False)))
                    single_field_payload_bytes = int(
                        event.get(f"{single_field_prefix}_payload_bytes", 0) or 0
                    )
                    totals[f"{single_field_prefix}_payload_violation_count"] += int(
                        single_field_payload_bytes != 0
                    )
                    totals[f"{single_field_prefix}_kernel_arg_violation_count"] += int(
                        bool(
                            event.get(
                                f"{single_field_prefix}_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                kernel_side_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode"
                )
                if kernel_side_mode is not None:
                    kernel_side_prefix = (
                        "premap_consumer_descriptor_prep_consumer_shim_"
                        "kernel_side_consumer_schema_adapter"
                    )
                    totals[f"{kernel_side_prefix}_checked_count"] += 1
                    totals[f"{kernel_side_prefix}_mode_checked_count"] += 1
                    if not totals[f"{kernel_side_prefix}_mode"]:
                        totals[f"{kernel_side_prefix}_mode"] = str(kernel_side_mode)
                    elif totals[f"{kernel_side_prefix}_mode"] != str(kernel_side_mode):
                        totals[f"{kernel_side_prefix}_mode_mismatch_count"] += 1
                    totals[f"{kernel_side_prefix}_ready_count"] += int(
                        bool(event.get(f"{kernel_side_prefix}_ready", False))
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            f"{kernel_side_prefix}_hash",
                            f"{kernel_side_prefix}_hash_checked_count",
                            f"{kernel_side_prefix}_hash_missing_count",
                        ),
                        (
                            f"{kernel_side_prefix}_semantic_adapter_hash",
                            f"{kernel_side_prefix}_semantic_adapter_hash_checked_count",
                            f"{kernel_side_prefix}_semantic_adapter_hash_missing_count",
                        ),
                        (
                            f"{kernel_side_prefix}_table_object_hash",
                            f"{kernel_side_prefix}_table_object_hash_checked_count",
                            f"{kernel_side_prefix}_table_object_hash_missing_count",
                        ),
                        (
                            f"{kernel_side_prefix}_launch_schema_mirror_hash",
                            f"{kernel_side_prefix}_launch_schema_mirror_hash_checked_count",
                            f"{kernel_side_prefix}_launch_schema_mirror_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    kernel_side_column_count = int(
                        event.get(f"{kernel_side_prefix}_column_count", 0) or 0
                    )
                    if (
                        kernel_side_column_count
                        > totals[f"{kernel_side_prefix}_column_count_max"]
                    ):
                        totals[
                            f"{kernel_side_prefix}_column_count_max"
                        ] = kernel_side_column_count
                    if (
                        totals[f"{kernel_side_prefix}_column_count_min"] == 0
                        or kernel_side_column_count
                        < totals[f"{kernel_side_prefix}_column_count_min"]
                    ):
                        totals[
                            f"{kernel_side_prefix}_column_count_min"
                        ] = kernel_side_column_count
                    for value_field, base_key in (
                        (
                            f"{kernel_side_prefix}_table_schema_hash",
                            f"{kernel_side_prefix}_table_schema_hash",
                        ),
                        (
                            f"{kernel_side_prefix}_semantic_schema_hash",
                            f"{kernel_side_prefix}_semantic_schema_hash",
                        ),
                        (
                            f"{kernel_side_prefix}_kernel_side_schema_name",
                            f"{kernel_side_prefix}_kernel_side_schema_name",
                        ),
                        (
                            f"{kernel_side_prefix}_kernel_side_schema_hash",
                            f"{kernel_side_prefix}_kernel_side_schema_hash",
                        ),
                        (
                            f"{kernel_side_prefix}_block_reason",
                            f"{kernel_side_prefix}_block_reason",
                        ),
                    ):
                        value = event.get(value_field)
                        if value:
                            totals[f"{base_key}_checked_count"] += 1
                            if not totals[base_key]:
                                totals[base_key] = str(value)
                            elif totals[base_key] != str(value):
                                totals[f"{base_key}_mismatch_count"] += 1
                        else:
                            totals[f"{base_key}_missing_count"] += 1
                    for field in (
                        f"{kernel_side_prefix}_row_count",
                        f"{kernel_side_prefix}_kernel_side_field_count",
                        f"{kernel_side_prefix}_required_source_hit_count",
                        f"{kernel_side_prefix}_required_source_miss_count",
                        f"{kernel_side_prefix}_optional_source_hit_count",
                        f"{kernel_side_prefix}_optional_source_miss_count",
                        f"{kernel_side_prefix}_handle_field_read_count",
                        f"{kernel_side_prefix}_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    for flag_field, count_key in (
                        (
                            f"{kernel_side_prefix}_consumer_schema_present",
                            f"{kernel_side_prefix}_consumer_schema_present_count",
                        ),
                        (
                            f"{kernel_side_prefix}_consumer_connected",
                            f"{kernel_side_prefix}_consumer_connected_count",
                        ),
                        (
                            f"{kernel_side_prefix}_live_enabled",
                            f"{kernel_side_prefix}_live_enabled_count",
                        ),
                        (
                            f"{kernel_side_prefix}_live_eligible",
                            f"{kernel_side_prefix}_live_eligible_count",
                        ),
                        (
                            f"{kernel_side_prefix}_blocked",
                            f"{kernel_side_prefix}_blocked_count",
                        ),
                    ):
                        totals[count_key] += int(bool(event.get(flag_field, False)))
                    kernel_side_payload_bytes = int(
                        event.get(f"{kernel_side_prefix}_payload_bytes", 0) or 0
                    )
                    totals[f"{kernel_side_prefix}_payload_violation_count"] += int(
                        kernel_side_payload_bytes != 0
                    )
                    totals[f"{kernel_side_prefix}_passed_to_kernel_count"] += int(
                        bool(event.get(f"{kernel_side_prefix}_passed_to_kernel", False))
                    )
                    totals[f"{kernel_side_prefix}_kernel_arg_violation_count"] += int(
                        bool(
                            event.get(
                                f"{kernel_side_prefix}_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                    totals[
                        f"{kernel_side_prefix}_live_compatible_with_current_wna16_args_count"
                    ] += int(
                        bool(
                            event.get(
                                f"{kernel_side_prefix}_live_compatible_with_current_wna16_args",
                                False,
                            )
                        )
                    )
                elif semantic_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode_missing_count"
                    ] += 1
                typed_consumer_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_side_typed_consumer_object_mode"
                )
                if typed_consumer_mode is not None:
                    typed_prefix = (
                        "premap_consumer_descriptor_prep_consumer_shim_"
                        "kernel_side_typed_consumer_object"
                    )
                    for key, default in (
                        (f"{typed_prefix}_checked_count", 0),
                        (f"{typed_prefix}_ready_count", 0),
                        (f"{typed_prefix}_mode", ""),
                        (f"{typed_prefix}_mode_checked_count", 0),
                        (f"{typed_prefix}_mode_mismatch_count", 0),
                        (f"{typed_prefix}_hash_checked_count", 0),
                        (f"{typed_prefix}_hash_missing_count", 0),
                        (f"{typed_prefix}_kernel_side_adapter_hash_checked_count", 0),
                        (f"{typed_prefix}_kernel_side_adapter_hash_missing_count", 0),
                        (f"{typed_prefix}_semantic_adapter_hash_checked_count", 0),
                        (f"{typed_prefix}_semantic_adapter_hash_missing_count", 0),
                        (f"{typed_prefix}_table_object_hash_checked_count", 0),
                        (f"{typed_prefix}_table_object_hash_missing_count", 0),
                        (f"{typed_prefix}_launch_schema_mirror_hash_checked_count", 0),
                        (f"{typed_prefix}_launch_schema_mirror_hash_missing_count", 0),
                        (f"{typed_prefix}_column_count_max", 0),
                        (f"{typed_prefix}_column_count_min", 0),
                        (f"{typed_prefix}_table_schema_hash", ""),
                        (f"{typed_prefix}_table_schema_hash_checked_count", 0),
                        (f"{typed_prefix}_table_schema_hash_missing_count", 0),
                        (f"{typed_prefix}_table_schema_hash_mismatch_count", 0),
                        (f"{typed_prefix}_semantic_schema_hash", ""),
                        (f"{typed_prefix}_semantic_schema_hash_checked_count", 0),
                        (f"{typed_prefix}_semantic_schema_hash_missing_count", 0),
                        (f"{typed_prefix}_semantic_schema_hash_mismatch_count", 0),
                        (f"{typed_prefix}_kernel_side_schema_hash", ""),
                        (f"{typed_prefix}_kernel_side_schema_hash_checked_count", 0),
                        (f"{typed_prefix}_kernel_side_schema_hash_missing_count", 0),
                        (f"{typed_prefix}_kernel_side_schema_hash_mismatch_count", 0),
                        (f"{typed_prefix}_typed_consumer_schema_name", ""),
                        (f"{typed_prefix}_typed_consumer_schema_name_checked_count", 0),
                        (f"{typed_prefix}_typed_consumer_schema_name_missing_count", 0),
                        (f"{typed_prefix}_typed_consumer_schema_name_mismatch_count", 0),
                        (f"{typed_prefix}_typed_consumer_schema_hash", ""),
                        (f"{typed_prefix}_typed_consumer_schema_hash_checked_count", 0),
                        (f"{typed_prefix}_typed_consumer_schema_hash_missing_count", 0),
                        (f"{typed_prefix}_typed_consumer_schema_hash_mismatch_count", 0),
                        (f"{typed_prefix}_block_reason", ""),
                        (f"{typed_prefix}_block_reason_checked_count", 0),
                        (f"{typed_prefix}_block_reason_missing_count", 0),
                        (f"{typed_prefix}_block_reason_mismatch_count", 0),
                        (f"{typed_prefix}_row_count", 0),
                        (f"{typed_prefix}_typed_consumer_field_count", 0),
                        (f"{typed_prefix}_required_source_hit_count", 0),
                        (f"{typed_prefix}_required_source_miss_count", 0),
                        (f"{typed_prefix}_optional_source_hit_count", 0),
                        (f"{typed_prefix}_optional_source_miss_count", 0),
                        (f"{typed_prefix}_handle_field_read_count", 0),
                        (f"{typed_prefix}_consumer_object_present_count", 0),
                        (f"{typed_prefix}_consumer_connected_count", 0),
                        (f"{typed_prefix}_live_enabled_count", 0),
                        (f"{typed_prefix}_live_eligible_count", 0),
                        (f"{typed_prefix}_blocked_count", 0),
                        (f"{typed_prefix}_payload_bytes", 0),
                        (f"{typed_prefix}_payload_violation_count", 0),
                        (f"{typed_prefix}_passed_to_kernel_count", 0),
                        (f"{typed_prefix}_kernel_arg_violation_count", 0),
                        (
                            f"{typed_prefix}_live_compatible_with_current_wna16_args_count",
                            0,
                        ),
                    ):
                        totals.setdefault(key, default)
                    totals[f"{typed_prefix}_checked_count"] += 1
                    totals[f"{typed_prefix}_mode_checked_count"] += 1
                    if not totals[f"{typed_prefix}_mode"]:
                        totals[f"{typed_prefix}_mode"] = str(typed_consumer_mode)
                    elif totals[f"{typed_prefix}_mode"] != str(typed_consumer_mode):
                        totals[f"{typed_prefix}_mode_mismatch_count"] += 1
                    totals[f"{typed_prefix}_ready_count"] += int(
                        bool(event.get(f"{typed_prefix}_ready", False))
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            f"{typed_prefix}_hash",
                            f"{typed_prefix}_hash_checked_count",
                            f"{typed_prefix}_hash_missing_count",
                        ),
                        (
                            f"{typed_prefix}_kernel_side_adapter_hash",
                            f"{typed_prefix}_kernel_side_adapter_hash_checked_count",
                            f"{typed_prefix}_kernel_side_adapter_hash_missing_count",
                        ),
                        (
                            f"{typed_prefix}_semantic_adapter_hash",
                            f"{typed_prefix}_semantic_adapter_hash_checked_count",
                            f"{typed_prefix}_semantic_adapter_hash_missing_count",
                        ),
                        (
                            f"{typed_prefix}_table_object_hash",
                            f"{typed_prefix}_table_object_hash_checked_count",
                            f"{typed_prefix}_table_object_hash_missing_count",
                        ),
                        (
                            f"{typed_prefix}_launch_schema_mirror_hash",
                            f"{typed_prefix}_launch_schema_mirror_hash_checked_count",
                            f"{typed_prefix}_launch_schema_mirror_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    typed_column_count = int(
                        event.get(f"{typed_prefix}_column_count", 0) or 0
                    )
                    if typed_column_count > totals[f"{typed_prefix}_column_count_max"]:
                        totals[f"{typed_prefix}_column_count_max"] = typed_column_count
                    if (
                        totals[f"{typed_prefix}_column_count_min"] == 0
                        or typed_column_count
                        < totals[f"{typed_prefix}_column_count_min"]
                    ):
                        totals[f"{typed_prefix}_column_count_min"] = typed_column_count
                    for value_field, base_key in (
                        (
                            f"{typed_prefix}_table_schema_hash",
                            f"{typed_prefix}_table_schema_hash",
                        ),
                        (
                            f"{typed_prefix}_semantic_schema_hash",
                            f"{typed_prefix}_semantic_schema_hash",
                        ),
                        (
                            f"{typed_prefix}_kernel_side_schema_hash",
                            f"{typed_prefix}_kernel_side_schema_hash",
                        ),
                        (
                            f"{typed_prefix}_typed_consumer_schema_name",
                            f"{typed_prefix}_typed_consumer_schema_name",
                        ),
                        (
                            f"{typed_prefix}_typed_consumer_schema_hash",
                            f"{typed_prefix}_typed_consumer_schema_hash",
                        ),
                        (
                            f"{typed_prefix}_block_reason",
                            f"{typed_prefix}_block_reason",
                        ),
                    ):
                        value = event.get(value_field)
                        if value:
                            totals[f"{base_key}_checked_count"] += 1
                            if not totals[base_key]:
                                totals[base_key] = str(value)
                            elif totals[base_key] != str(value):
                                totals[f"{base_key}_mismatch_count"] += 1
                        else:
                            totals[f"{base_key}_missing_count"] += 1
                    for field in (
                        f"{typed_prefix}_row_count",
                        f"{typed_prefix}_typed_consumer_field_count",
                        f"{typed_prefix}_required_source_hit_count",
                        f"{typed_prefix}_required_source_miss_count",
                        f"{typed_prefix}_optional_source_hit_count",
                        f"{typed_prefix}_optional_source_miss_count",
                        f"{typed_prefix}_handle_field_read_count",
                        f"{typed_prefix}_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    for flag_field, count_key in (
                        (
                            f"{typed_prefix}_consumer_object_present",
                            f"{typed_prefix}_consumer_object_present_count",
                        ),
                        (
                            f"{typed_prefix}_consumer_connected",
                            f"{typed_prefix}_consumer_connected_count",
                        ),
                        (
                            f"{typed_prefix}_live_enabled",
                            f"{typed_prefix}_live_enabled_count",
                        ),
                        (
                            f"{typed_prefix}_live_eligible",
                            f"{typed_prefix}_live_eligible_count",
                        ),
                        (
                            f"{typed_prefix}_blocked",
                            f"{typed_prefix}_blocked_count",
                        ),
                    ):
                        totals[count_key] += int(bool(event.get(flag_field, False)))
                    typed_payload_bytes = int(
                        event.get(f"{typed_prefix}_payload_bytes", 0) or 0
                    )
                    totals[f"{typed_prefix}_payload_violation_count"] += int(
                        typed_payload_bytes != 0
                    )
                    totals[f"{typed_prefix}_passed_to_kernel_count"] += int(
                        bool(event.get(f"{typed_prefix}_passed_to_kernel", False))
                    )
                    totals[f"{typed_prefix}_kernel_arg_violation_count"] += int(
                        bool(
                            event.get(
                                f"{typed_prefix}_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                    totals[
                        f"{typed_prefix}_live_compatible_with_current_wna16_args_count"
                    ] += int(
                        bool(
                            event.get(
                                f"{typed_prefix}_live_compatible_with_current_wna16_args",
                                False,
                            )
                        )
                    )
                native_bridge_prefix = (
                    "premap_consumer_descriptor_prep_consumer_shim_"
                    "native_typed_consumer_bridge"
                )
                native_bridge_mode = event.get(f"{native_bridge_prefix}_mode")
                if native_bridge_mode is not None:
                    for key, default in (
                        (f"{native_bridge_prefix}_checked_count", 0),
                        (f"{native_bridge_prefix}_ok_count", 0),
                        (f"{native_bridge_prefix}_mode", ""),
                        (f"{native_bridge_prefix}_mode_checked_count", 0),
                        (f"{native_bridge_prefix}_mode_mismatch_count", 0),
                        (f"{native_bridge_prefix}_input_hash_checked_count", 0),
                        (f"{native_bridge_prefix}_input_hash_missing_count", 0),
                        (f"{native_bridge_prefix}_table_object_hash_checked_count", 0),
                        (f"{native_bridge_prefix}_table_object_hash_missing_count", 0),
                        (f"{native_bridge_prefix}_schema_hash", ""),
                        (f"{native_bridge_prefix}_schema_hash_checked_count", 0),
                        (f"{native_bridge_prefix}_schema_hash_missing_count", 0),
                        (f"{native_bridge_prefix}_schema_hash_mismatch_count", 0),
                        (f"{native_bridge_prefix}_row_count", 0),
                        (f"{native_bridge_prefix}_column_count_max", 0),
                        (f"{native_bridge_prefix}_column_count_min", 0),
                        (f"{native_bridge_prefix}_required_handle_nonzero_count", 0),
                        (f"{native_bridge_prefix}_required_handle_zero_count", 0),
                        (f"{native_bridge_prefix}_optional_handle_nonzero_count", 0),
                        (f"{native_bridge_prefix}_optional_handle_zero_count", 0),
                        (f"{native_bridge_prefix}_expert_id_valid_count", 0),
                        (f"{native_bridge_prefix}_expert_id_invalid_count", 0),
                        (f"{native_bridge_prefix}_address_key_hash_nonzero_count", 0),
                        (f"{native_bridge_prefix}_address_key_hash_zero_count", 0),
                        (f"{native_bridge_prefix}_failure_count", 0),
                        (f"{native_bridge_prefix}_payload_bytes", 0),
                        (f"{native_bridge_prefix}_payload_violation_count", 0),
                        (f"{native_bridge_prefix}_ready_credit_count", 0),
                        (f"{native_bridge_prefix}_changes_router_count", 0),
                        (
                            f"{native_bridge_prefix}_changes_descriptor_order_count",
                            0,
                        ),
                        (f"{native_bridge_prefix}_passed_to_kernel_count", 0),
                        (f"{native_bridge_prefix}_kernel_arg_violation_count", 0),
                    ):
                        totals.setdefault(key, default)
                    totals[f"{native_bridge_prefix}_checked_count"] += 1
                    totals[f"{native_bridge_prefix}_mode_checked_count"] += 1
                    if not totals[f"{native_bridge_prefix}_mode"]:
                        totals[f"{native_bridge_prefix}_mode"] = str(
                            native_bridge_mode
                        )
                    elif totals[f"{native_bridge_prefix}_mode"] != str(
                        native_bridge_mode
                    ):
                        totals[f"{native_bridge_prefix}_mode_mismatch_count"] += 1
                    totals[f"{native_bridge_prefix}_ok_count"] += int(
                        bool(event.get(f"{native_bridge_prefix}_ok", False))
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            f"{native_bridge_prefix}_input_hash",
                            f"{native_bridge_prefix}_input_hash_checked_count",
                            f"{native_bridge_prefix}_input_hash_missing_count",
                        ),
                        (
                            f"{native_bridge_prefix}_table_object_hash",
                            f"{native_bridge_prefix}_table_object_hash_checked_count",
                            f"{native_bridge_prefix}_table_object_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    native_schema_hash = event.get(f"{native_bridge_prefix}_schema_hash")
                    if native_schema_hash:
                        totals[f"{native_bridge_prefix}_schema_hash_checked_count"] += 1
                        if not totals[f"{native_bridge_prefix}_schema_hash"]:
                            totals[f"{native_bridge_prefix}_schema_hash"] = str(
                                native_schema_hash
                            )
                        elif totals[f"{native_bridge_prefix}_schema_hash"] != str(
                            native_schema_hash
                        ):
                            totals[f"{native_bridge_prefix}_schema_hash_mismatch_count"] += 1
                    else:
                        totals[f"{native_bridge_prefix}_schema_hash_missing_count"] += 1
                    native_column_count = int(
                        event.get(f"{native_bridge_prefix}_column_count", 0) or 0
                    )
                    if (
                        native_column_count
                        > totals[f"{native_bridge_prefix}_column_count_max"]
                    ):
                        totals[f"{native_bridge_prefix}_column_count_max"] = (
                            native_column_count
                        )
                    if (
                        totals[f"{native_bridge_prefix}_column_count_min"] == 0
                        or native_column_count
                        < totals[f"{native_bridge_prefix}_column_count_min"]
                    ):
                        totals[f"{native_bridge_prefix}_column_count_min"] = (
                            native_column_count
                        )
                    for field in (
                        f"{native_bridge_prefix}_row_count",
                        f"{native_bridge_prefix}_required_handle_nonzero_count",
                        f"{native_bridge_prefix}_required_handle_zero_count",
                        f"{native_bridge_prefix}_optional_handle_nonzero_count",
                        f"{native_bridge_prefix}_optional_handle_zero_count",
                        f"{native_bridge_prefix}_expert_id_valid_count",
                        f"{native_bridge_prefix}_expert_id_invalid_count",
                        f"{native_bridge_prefix}_address_key_hash_nonzero_count",
                        f"{native_bridge_prefix}_address_key_hash_zero_count",
                        f"{native_bridge_prefix}_failure_count",
                        f"{native_bridge_prefix}_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    native_payload_bytes = int(
                        event.get(f"{native_bridge_prefix}_payload_bytes", 0) or 0
                    )
                    totals[f"{native_bridge_prefix}_payload_violation_count"] += int(
                        native_payload_bytes != 0
                    )
                    totals[f"{native_bridge_prefix}_ready_credit_count"] += int(
                        bool(event.get(f"{native_bridge_prefix}_ready_credit", False))
                    )
                    totals[f"{native_bridge_prefix}_changes_router_count"] += int(
                        bool(event.get(f"{native_bridge_prefix}_changes_router", False))
                    )
                    totals[
                        f"{native_bridge_prefix}_changes_descriptor_order_count"
                    ] += int(
                        bool(
                            event.get(
                                f"{native_bridge_prefix}_changes_descriptor_order",
                                False,
                            )
                        )
                    )
                    totals[f"{native_bridge_prefix}_passed_to_kernel_count"] += int(
                        bool(event.get(f"{native_bridge_prefix}_passed_to_kernel", False))
                    )
                    totals[f"{native_bridge_prefix}_kernel_arg_violation_count"] += int(
                        bool(
                            event.get(
                                f"{native_bridge_prefix}_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                native_stub_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation_mode"
                )
                if native_stub_mode is not None:
                    native_stub_prefix = (
                        "premap_consumer_descriptor_prep_consumer_shim_"
                        "native_stub_online_invocation"
                    )
                    for key, default in (
                        (f"{native_stub_prefix}_checked_count", 0),
                        (f"{native_stub_prefix}_ready_count", 0),
                        (f"{native_stub_prefix}_ok_count", 0),
                        (f"{native_stub_prefix}_mode", ""),
                        (f"{native_stub_prefix}_mode_checked_count", 0),
                        (f"{native_stub_prefix}_mode_mismatch_count", 0),
                        (f"{native_stub_prefix}_package_hash_checked_count", 0),
                        (f"{native_stub_prefix}_package_hash_missing_count", 0),
                        (f"{native_stub_prefix}_input_hash_checked_count", 0),
                        (f"{native_stub_prefix}_input_hash_missing_count", 0),
                        (f"{native_stub_prefix}_table_object_hash_checked_count", 0),
                        (f"{native_stub_prefix}_table_object_hash_missing_count", 0),
                        (f"{native_stub_prefix}_schema_hash", ""),
                        (f"{native_stub_prefix}_schema_hash_checked_count", 0),
                        (f"{native_stub_prefix}_schema_hash_missing_count", 0),
                        (f"{native_stub_prefix}_schema_hash_mismatch_count", 0),
                        (f"{native_stub_prefix}_column_count_max", 0),
                        (f"{native_stub_prefix}_column_count_min", 0),
                        (f"{native_stub_prefix}_block_reason", ""),
                        (f"{native_stub_prefix}_block_reason_checked_count", 0),
                        (f"{native_stub_prefix}_block_reason_missing_count", 0),
                        (f"{native_stub_prefix}_block_reason_mismatch_count", 0),
                        (f"{native_stub_prefix}_row_count", 0),
                        (f"{native_stub_prefix}_required_handle_nonzero_count", 0),
                        (f"{native_stub_prefix}_required_handle_zero_count", 0),
                        (f"{native_stub_prefix}_optional_handle_nonzero_count", 0),
                        (f"{native_stub_prefix}_optional_handle_zero_count", 0),
                        (f"{native_stub_prefix}_expert_id_valid_count", 0),
                        (f"{native_stub_prefix}_expert_id_invalid_count", 0),
                        (f"{native_stub_prefix}_address_key_hash_nonzero_count", 0),
                        (f"{native_stub_prefix}_address_key_hash_zero_count", 0),
                        (f"{native_stub_prefix}_failure_count", 0),
                        (f"{native_stub_prefix}_payload_bytes", 0),
                        (f"{native_stub_prefix}_payload_violation_count", 0),
                        (f"{native_stub_prefix}_ready_credit_count", 0),
                        (f"{native_stub_prefix}_changes_router_count", 0),
                        (
                            f"{native_stub_prefix}_changes_descriptor_order_count",
                            0,
                        ),
                        (f"{native_stub_prefix}_passed_to_kernel_count", 0),
                        (f"{native_stub_prefix}_kernel_arg_violation_count", 0),
                        (f"{native_stub_prefix}_native_checker_invoked_count", 0),
                        (f"{native_stub_prefix}_native_bridge_ok_count", 0),
                        (f"{native_stub_prefix}_requested_count", 0),
                        (f"{native_stub_prefix}_native_stub_invoked_count", 0),
                        (f"{native_stub_prefix}_blocked_count", 0),
                    ):
                        totals.setdefault(key, default)
                    totals[f"{native_stub_prefix}_checked_count"] += 1
                    totals[f"{native_stub_prefix}_mode_checked_count"] += 1
                    if not totals[f"{native_stub_prefix}_mode"]:
                        totals[f"{native_stub_prefix}_mode"] = str(native_stub_mode)
                    elif totals[f"{native_stub_prefix}_mode"] != str(native_stub_mode):
                        totals[f"{native_stub_prefix}_mode_mismatch_count"] += 1
                    totals[f"{native_stub_prefix}_ready_count"] += int(
                        bool(event.get(f"{native_stub_prefix}_ready", False))
                    )
                    totals[f"{native_stub_prefix}_ok_count"] += int(
                        bool(event.get(f"{native_stub_prefix}_ok", False))
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            f"{native_stub_prefix}_package_hash",
                            f"{native_stub_prefix}_package_hash_checked_count",
                            f"{native_stub_prefix}_package_hash_missing_count",
                        ),
                        (
                            f"{native_stub_prefix}_input_hash",
                            f"{native_stub_prefix}_input_hash_checked_count",
                            f"{native_stub_prefix}_input_hash_missing_count",
                        ),
                        (
                            f"{native_stub_prefix}_table_object_hash",
                            f"{native_stub_prefix}_table_object_hash_checked_count",
                            f"{native_stub_prefix}_table_object_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    native_stub_schema_hash = event.get(
                        f"{native_stub_prefix}_schema_hash"
                    )
                    if native_stub_schema_hash:
                        totals[
                            f"{native_stub_prefix}_schema_hash_checked_count"
                        ] += 1
                        if not totals[f"{native_stub_prefix}_schema_hash"]:
                            totals[f"{native_stub_prefix}_schema_hash"] = str(
                                native_stub_schema_hash
                            )
                        elif totals[f"{native_stub_prefix}_schema_hash"] != str(
                            native_stub_schema_hash
                        ):
                            totals[
                                f"{native_stub_prefix}_schema_hash_mismatch_count"
                            ] += 1
                    else:
                        totals[f"{native_stub_prefix}_schema_hash_missing_count"] += 1
                    block_reason = event.get(f"{native_stub_prefix}_block_reason")
                    if block_reason:
                        totals[f"{native_stub_prefix}_block_reason_checked_count"] += 1
                        if not totals[f"{native_stub_prefix}_block_reason"]:
                            totals[f"{native_stub_prefix}_block_reason"] = str(
                                block_reason
                            )
                        elif totals[f"{native_stub_prefix}_block_reason"] != str(
                            block_reason
                        ):
                            totals[
                                f"{native_stub_prefix}_block_reason_mismatch_count"
                            ] += 1
                    else:
                        totals[f"{native_stub_prefix}_block_reason_missing_count"] += 1
                    native_stub_column_count = int(
                        event.get(f"{native_stub_prefix}_column_count", 0) or 0
                    )
                    if (
                        native_stub_column_count
                        > totals[f"{native_stub_prefix}_column_count_max"]
                    ):
                        totals[f"{native_stub_prefix}_column_count_max"] = (
                            native_stub_column_count
                        )
                    if (
                        totals[f"{native_stub_prefix}_column_count_min"] == 0
                        or native_stub_column_count
                        < totals[f"{native_stub_prefix}_column_count_min"]
                    ):
                        totals[f"{native_stub_prefix}_column_count_min"] = (
                            native_stub_column_count
                        )
                    for field in (
                        f"{native_stub_prefix}_row_count",
                        f"{native_stub_prefix}_required_handle_nonzero_count",
                        f"{native_stub_prefix}_required_handle_zero_count",
                        f"{native_stub_prefix}_optional_handle_nonzero_count",
                        f"{native_stub_prefix}_optional_handle_zero_count",
                        f"{native_stub_prefix}_expert_id_valid_count",
                        f"{native_stub_prefix}_expert_id_invalid_count",
                        f"{native_stub_prefix}_address_key_hash_nonzero_count",
                        f"{native_stub_prefix}_address_key_hash_zero_count",
                        f"{native_stub_prefix}_failure_count",
                        f"{native_stub_prefix}_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    for flag_field, count_key in (
                        (
                            f"{native_stub_prefix}_native_checker_invoked",
                            f"{native_stub_prefix}_native_checker_invoked_count",
                        ),
                        (
                            f"{native_stub_prefix}_native_bridge_ok",
                            f"{native_stub_prefix}_native_bridge_ok_count",
                        ),
                        (
                            f"{native_stub_prefix}_requested",
                            f"{native_stub_prefix}_requested_count",
                        ),
                        (
                            f"{native_stub_prefix}_native_stub_invoked",
                            f"{native_stub_prefix}_native_stub_invoked_count",
                        ),
                        (
                            f"{native_stub_prefix}_blocked",
                            f"{native_stub_prefix}_blocked_count",
                        ),
                    ):
                        totals[count_key] += int(bool(event.get(flag_field, False)))
                    native_stub_payload_bytes = int(
                        event.get(f"{native_stub_prefix}_payload_bytes", 0) or 0
                    )
                    totals[f"{native_stub_prefix}_payload_violation_count"] += int(
                        native_stub_payload_bytes != 0
                    )
                    totals[f"{native_stub_prefix}_ready_credit_count"] += int(
                        bool(event.get(f"{native_stub_prefix}_ready_credit", False))
                    )
                    totals[f"{native_stub_prefix}_changes_router_count"] += int(
                        bool(event.get(f"{native_stub_prefix}_changes_router", False))
                    )
                    totals[
                        f"{native_stub_prefix}_changes_descriptor_order_count"
                    ] += int(
                        bool(
                            event.get(
                                f"{native_stub_prefix}_changes_descriptor_order",
                                False,
                            )
                        )
                    )
                    totals[f"{native_stub_prefix}_passed_to_kernel_count"] += int(
                        bool(event.get(f"{native_stub_prefix}_passed_to_kernel", False))
                    )
                    totals[f"{native_stub_prefix}_kernel_arg_violation_count"] += int(
                        bool(
                            event.get(
                                f"{native_stub_prefix}_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                typed_row_prefix = (
                    "premap_consumer_descriptor_prep_consumer_shim_"
                    "kernel_side_typed_row_consumer_path"
                )
                typed_row_mode = event.get(f"{typed_row_prefix}_mode")
                if typed_row_mode is not None:
                    for key, default in (
                        (f"{typed_row_prefix}_checked_count", 0),
                        (f"{typed_row_prefix}_ready_count", 0),
                        (f"{typed_row_prefix}_mode", ""),
                        (f"{typed_row_prefix}_mode_checked_count", 0),
                        (f"{typed_row_prefix}_mode_mismatch_count", 0),
                        (f"{typed_row_prefix}_name", ""),
                        (f"{typed_row_prefix}_name_checked_count", 0),
                        (f"{typed_row_prefix}_name_missing_count", 0),
                        (f"{typed_row_prefix}_name_mismatch_count", 0),
                        (f"{typed_row_prefix}_source", ""),
                        (f"{typed_row_prefix}_source_checked_count", 0),
                        (f"{typed_row_prefix}_source_missing_count", 0),
                        (f"{typed_row_prefix}_source_mismatch_count", 0),
                        (f"{typed_row_prefix}_input_hash_checked_count", 0),
                        (f"{typed_row_prefix}_input_hash_missing_count", 0),
                        (f"{typed_row_prefix}_table_object_hash_checked_count", 0),
                        (f"{typed_row_prefix}_table_object_hash_missing_count", 0),
                        (f"{typed_row_prefix}_schema_hash", ""),
                        (f"{typed_row_prefix}_schema_hash_checked_count", 0),
                        (f"{typed_row_prefix}_schema_hash_missing_count", 0),
                        (f"{typed_row_prefix}_schema_hash_mismatch_count", 0),
                        (f"{typed_row_prefix}_column_count_max", 0),
                        (f"{typed_row_prefix}_column_count_min", 0),
                        (f"{typed_row_prefix}_row_count", 0),
                        (f"{typed_row_prefix}_row_ok_count", 0),
                        (f"{typed_row_prefix}_error_count", 0),
                        (f"{typed_row_prefix}_hash_accumulator_checked_count", 0),
                        (f"{typed_row_prefix}_hash_accumulator_missing_count", 0),
                        (f"{typed_row_prefix}_failure_count", 0),
                        (f"{typed_row_prefix}_payload_bytes", 0),
                        (f"{typed_row_prefix}_payload_violation_count", 0),
                        (f"{typed_row_prefix}_passed_to_kernel_count", 0),
                        (f"{typed_row_prefix}_kernel_arg_violation_count", 0),
                        (
                            f"{typed_row_prefix}_current_wna16_arg_compatible_count",
                            0,
                        ),
                    ):
                        totals.setdefault(key, default)
                    totals[f"{typed_row_prefix}_checked_count"] += 1
                    totals[f"{typed_row_prefix}_mode_checked_count"] += 1
                    if not totals[f"{typed_row_prefix}_mode"]:
                        totals[f"{typed_row_prefix}_mode"] = str(typed_row_mode)
                    elif totals[f"{typed_row_prefix}_mode"] != str(typed_row_mode):
                        totals[f"{typed_row_prefix}_mode_mismatch_count"] += 1
                    totals[f"{typed_row_prefix}_ready_count"] += int(
                        bool(event.get(f"{typed_row_prefix}_ready", False))
                    )
                    for field_name, expected_key in (
                        ("name", "name"),
                        ("source", "source"),
                    ):
                        value = event.get(f"{typed_row_prefix}_{field_name}")
                        if value:
                            totals[f"{typed_row_prefix}_{expected_key}_checked_count"] += 1
                            if not totals[f"{typed_row_prefix}_{expected_key}"]:
                                totals[f"{typed_row_prefix}_{expected_key}"] = str(value)
                            elif totals[f"{typed_row_prefix}_{expected_key}"] != str(
                                value
                            ):
                                totals[
                                    f"{typed_row_prefix}_{expected_key}_mismatch_count"
                                ] += 1
                        else:
                            totals[f"{typed_row_prefix}_{expected_key}_missing_count"] += 1
                    for hash_field, checked_key, missing_key in (
                        (
                            f"{typed_row_prefix}_input_hash",
                            f"{typed_row_prefix}_input_hash_checked_count",
                            f"{typed_row_prefix}_input_hash_missing_count",
                        ),
                        (
                            f"{typed_row_prefix}_table_object_hash",
                            f"{typed_row_prefix}_table_object_hash_checked_count",
                            f"{typed_row_prefix}_table_object_hash_missing_count",
                        ),
                        (
                            f"{typed_row_prefix}_hash_accumulator",
                            f"{typed_row_prefix}_hash_accumulator_checked_count",
                            f"{typed_row_prefix}_hash_accumulator_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    typed_row_schema_hash = event.get(f"{typed_row_prefix}_schema_hash")
                    if typed_row_schema_hash:
                        totals[f"{typed_row_prefix}_schema_hash_checked_count"] += 1
                        if not totals[f"{typed_row_prefix}_schema_hash"]:
                            totals[f"{typed_row_prefix}_schema_hash"] = str(
                                typed_row_schema_hash
                            )
                        elif totals[f"{typed_row_prefix}_schema_hash"] != str(
                            typed_row_schema_hash
                        ):
                            totals[
                                f"{typed_row_prefix}_schema_hash_mismatch_count"
                            ] += 1
                    else:
                        totals[f"{typed_row_prefix}_schema_hash_missing_count"] += 1
                    typed_row_column_count = int(
                        event.get(f"{typed_row_prefix}_column_count", 0) or 0
                    )
                    if (
                        typed_row_column_count
                        > totals[f"{typed_row_prefix}_column_count_max"]
                    ):
                        totals[f"{typed_row_prefix}_column_count_max"] = (
                            typed_row_column_count
                        )
                    if (
                        totals[f"{typed_row_prefix}_column_count_min"] == 0
                        or typed_row_column_count
                        < totals[f"{typed_row_prefix}_column_count_min"]
                    ):
                        totals[f"{typed_row_prefix}_column_count_min"] = (
                            typed_row_column_count
                        )
                    for field in (
                        f"{typed_row_prefix}_row_count",
                        f"{typed_row_prefix}_row_ok_count",
                        f"{typed_row_prefix}_error_count",
                        f"{typed_row_prefix}_failure_count",
                        f"{typed_row_prefix}_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    typed_row_payload_bytes = int(
                        event.get(f"{typed_row_prefix}_payload_bytes", 0) or 0
                    )
                    totals[f"{typed_row_prefix}_payload_violation_count"] += int(
                        typed_row_payload_bytes != 0
                    )
                    totals[f"{typed_row_prefix}_passed_to_kernel_count"] += int(
                        bool(event.get(f"{typed_row_prefix}_passed_to_kernel", False))
                    )
                    totals[f"{typed_row_prefix}_kernel_arg_violation_count"] += int(
                        bool(
                            event.get(
                                f"{typed_row_prefix}_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                    totals[
                        f"{typed_row_prefix}_current_wna16_arg_compatible_count"
                    ] += int(
                        bool(
                            event.get(
                                f"{typed_row_prefix}_current_wna16_arg_compatible",
                                False,
                            )
                        )
                    )
                wna16_slot_prefix = (
                    "premap_consumer_descriptor_prep_consumer_shim_"
                    "wna16_adjacent_typed_slot"
                )
                wna16_slot_mode = event.get(f"{wna16_slot_prefix}_mode")
                if wna16_slot_mode is not None:
                    for key, default in (
                        (f"{wna16_slot_prefix}_checked_count", 0),
                        (f"{wna16_slot_prefix}_ready_count", 0),
                        (f"{wna16_slot_prefix}_name", ""),
                        (f"{wna16_slot_prefix}_name_checked_count", 0),
                        (f"{wna16_slot_prefix}_name_missing_count", 0),
                        (f"{wna16_slot_prefix}_name_mismatch_count", 0),
                        (f"{wna16_slot_prefix}_mode", ""),
                        (f"{wna16_slot_prefix}_mode_checked_count", 0),
                        (f"{wna16_slot_prefix}_mode_mismatch_count", 0),
                        (f"{wna16_slot_prefix}_source", ""),
                        (f"{wna16_slot_prefix}_source_checked_count", 0),
                        (f"{wna16_slot_prefix}_source_missing_count", 0),
                        (f"{wna16_slot_prefix}_source_mismatch_count", 0),
                        (f"{wna16_slot_prefix}_input_hash_checked_count", 0),
                        (f"{wna16_slot_prefix}_input_hash_missing_count", 0),
                        (f"{wna16_slot_prefix}_table_object_hash_checked_count", 0),
                        (f"{wna16_slot_prefix}_table_object_hash_missing_count", 0),
                        (f"{wna16_slot_prefix}_schema_hash", ""),
                        (f"{wna16_slot_prefix}_schema_hash_checked_count", 0),
                        (f"{wna16_slot_prefix}_schema_hash_missing_count", 0),
                        (f"{wna16_slot_prefix}_schema_hash_mismatch_count", 0),
                        (f"{wna16_slot_prefix}_row_count", 0),
                        (f"{wna16_slot_prefix}_row_ok_count", 0),
                        (f"{wna16_slot_prefix}_error_count", 0),
                        (f"{wna16_slot_prefix}_all_handle_fields_read_count", 0),
                        (f"{wna16_slot_prefix}_packet_chain_depth", 0),
                        (f"{wna16_slot_prefix}_packet_chain_depth_checked_count", 0),
                        (f"{wna16_slot_prefix}_packet_chain_depth_mismatch_count", 0),
                        (f"{wna16_slot_prefix}_field_mask", 0),
                        (f"{wna16_slot_prefix}_field_mask_checked_count", 0),
                        (f"{wna16_slot_prefix}_field_mask_mismatch_count", 0),
                        (f"{wna16_slot_prefix}_descriptor_ptr_read_row_ok_count", 0),
                        (
                            f"{wna16_slot_prefix}_packed_weight_descriptor_read_row_ok_count",
                            0,
                        ),
                        (
                            f"{wna16_slot_prefix}_scale_metadata_handle_read_row_ok_count",
                            0,
                        ),
                        (f"{wna16_slot_prefix}_aux_metadata_handle_read_row_ok_count", 0),
                        (f"{wna16_slot_prefix}_expert_id_read_row_ok_count", 0),
                        (f"{wna16_slot_prefix}_address_key_hash_read_row_ok_count", 0),
                        (f"{wna16_slot_prefix}_row_metadata_read_row_ok_count", 0),
                        (f"{wna16_slot_prefix}_row_hash_accumulator_checked_count", 0),
                        (f"{wna16_slot_prefix}_row_hash_accumulator_missing_count", 0),
                        (
                            f"{wna16_slot_prefix}_field_read_hash_accumulator_checked_count",
                            0,
                        ),
                        (
                            f"{wna16_slot_prefix}_field_read_hash_accumulator_missing_count",
                            0,
                        ),
                        (
                            f"{wna16_slot_prefix}_row_metadata_hash_accumulator_checked_count",
                            0,
                        ),
                        (
                            f"{wna16_slot_prefix}_row_metadata_hash_accumulator_missing_count",
                            0,
                        ),
                        (f"{wna16_slot_prefix}_failure_count", 0),
                        (f"{wna16_slot_prefix}_payload_bytes", 0),
                        (f"{wna16_slot_prefix}_payload_violation_count", 0),
                        (f"{wna16_slot_prefix}_passed_to_kernel_count", 0),
                        (f"{wna16_slot_prefix}_kernel_arg_violation_count", 0),
                        (f"{wna16_slot_prefix}_current_wna16_arg_compatible_count", 0),
                        (
                            f"{wna16_slot_prefix}_requires_wna16_arg_reinterpretation_count",
                            0,
                        ),
                        (f"{wna16_slot_prefix}_explicit_typed_abi_slot_count", 0),
                        (f"{wna16_slot_prefix}_reuses_current_wna16_arg_slot_count", 0),
                    ):
                        totals.setdefault(key, default)
                    totals[f"{wna16_slot_prefix}_checked_count"] += 1
                    totals[f"{wna16_slot_prefix}_mode_checked_count"] += 1
                    totals[f"{wna16_slot_prefix}_ready_count"] += int(
                        bool(event.get(f"{wna16_slot_prefix}_ready", False))
                    )
                    for field_name in ("name", "mode", "source"):
                        value = event.get(f"{wna16_slot_prefix}_{field_name}")
                        if value:
                            totals[
                                f"{wna16_slot_prefix}_{field_name}_checked_count"
                            ] += 1
                            if not totals[f"{wna16_slot_prefix}_{field_name}"]:
                                totals[f"{wna16_slot_prefix}_{field_name}"] = str(
                                    value
                                )
                            elif totals[f"{wna16_slot_prefix}_{field_name}"] != str(
                                value
                            ):
                                totals[
                                    f"{wna16_slot_prefix}_{field_name}_mismatch_count"
                                ] += 1
                        else:
                            totals[
                                f"{wna16_slot_prefix}_{field_name}_missing_count"
                            ] += 1
                    for hash_field, checked_key, missing_key in (
                        (
                            f"{wna16_slot_prefix}_input_hash",
                            f"{wna16_slot_prefix}_input_hash_checked_count",
                            f"{wna16_slot_prefix}_input_hash_missing_count",
                        ),
                        (
                            f"{wna16_slot_prefix}_table_object_hash",
                            f"{wna16_slot_prefix}_table_object_hash_checked_count",
                            f"{wna16_slot_prefix}_table_object_hash_missing_count",
                        ),
                        (
                            f"{wna16_slot_prefix}_row_hash_accumulator",
                            f"{wna16_slot_prefix}_row_hash_accumulator_checked_count",
                            f"{wna16_slot_prefix}_row_hash_accumulator_missing_count",
                        ),
                        (
                            f"{wna16_slot_prefix}_field_read_hash_accumulator",
                            f"{wna16_slot_prefix}_field_read_hash_accumulator_checked_count",
                            f"{wna16_slot_prefix}_field_read_hash_accumulator_missing_count",
                        ),
                        (
                            f"{wna16_slot_prefix}_row_metadata_hash_accumulator",
                            f"{wna16_slot_prefix}_row_metadata_hash_accumulator_checked_count",
                            f"{wna16_slot_prefix}_row_metadata_hash_accumulator_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    slot_schema_hash = event.get(f"{wna16_slot_prefix}_schema_hash")
                    if slot_schema_hash:
                        totals[f"{wna16_slot_prefix}_schema_hash_checked_count"] += 1
                        if not totals[f"{wna16_slot_prefix}_schema_hash"]:
                            totals[f"{wna16_slot_prefix}_schema_hash"] = str(
                                slot_schema_hash
                            )
                        elif totals[f"{wna16_slot_prefix}_schema_hash"] != str(
                            slot_schema_hash
                        ):
                            totals[
                                f"{wna16_slot_prefix}_schema_hash_mismatch_count"
                            ] += 1
                    else:
                        totals[f"{wna16_slot_prefix}_schema_hash_missing_count"] += 1
                    packet_chain_depth = int(
                        event.get(f"{wna16_slot_prefix}_packet_chain_depth", 0) or 0
                    )
                    if packet_chain_depth:
                        totals[
                            f"{wna16_slot_prefix}_packet_chain_depth_checked_count"
                        ] += 1
                    if (
                        packet_chain_depth
                        != 14
                    ):
                        totals[
                            f"{wna16_slot_prefix}_packet_chain_depth_mismatch_count"
                        ] += 1
                    if not totals[f"{wna16_slot_prefix}_packet_chain_depth"]:
                        totals[f"{wna16_slot_prefix}_packet_chain_depth"] = (
                            packet_chain_depth
                        )
                    field_mask = int(
                        event.get(f"{wna16_slot_prefix}_field_mask", 0) or 0
                    )
                    if field_mask:
                        totals[f"{wna16_slot_prefix}_field_mask_checked_count"] += 1
                    if field_mask != 15:
                        totals[f"{wna16_slot_prefix}_field_mask_mismatch_count"] += 1
                    if not totals[f"{wna16_slot_prefix}_field_mask"]:
                        totals[f"{wna16_slot_prefix}_field_mask"] = field_mask
                    for field in (
                        f"{wna16_slot_prefix}_row_count",
                        f"{wna16_slot_prefix}_row_ok_count",
                        f"{wna16_slot_prefix}_error_count",
                        f"{wna16_slot_prefix}_descriptor_ptr_read_row_ok_count",
                        f"{wna16_slot_prefix}_packed_weight_descriptor_read_row_ok_count",
                        f"{wna16_slot_prefix}_scale_metadata_handle_read_row_ok_count",
                        f"{wna16_slot_prefix}_aux_metadata_handle_read_row_ok_count",
                        f"{wna16_slot_prefix}_expert_id_read_row_ok_count",
                        f"{wna16_slot_prefix}_address_key_hash_read_row_ok_count",
                        f"{wna16_slot_prefix}_row_metadata_read_row_ok_count",
                        f"{wna16_slot_prefix}_failure_count",
                        f"{wna16_slot_prefix}_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    totals[f"{wna16_slot_prefix}_all_handle_fields_read_count"] += int(
                        bool(
                            event.get(
                                f"{wna16_slot_prefix}_all_handle_fields_read",
                                False,
                            )
                        )
                    )
                    slot_payload_bytes = int(
                        event.get(f"{wna16_slot_prefix}_payload_bytes", 0) or 0
                    )
                    totals[f"{wna16_slot_prefix}_payload_violation_count"] += int(
                        slot_payload_bytes != 0
                    )
                    totals[f"{wna16_slot_prefix}_passed_to_kernel_count"] += int(
                        bool(event.get(f"{wna16_slot_prefix}_passed_to_kernel", False))
                    )
                    totals[f"{wna16_slot_prefix}_kernel_arg_violation_count"] += int(
                        bool(
                            event.get(
                                f"{wna16_slot_prefix}_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                    totals[
                        f"{wna16_slot_prefix}_current_wna16_arg_compatible_count"
                    ] += int(
                        bool(
                            event.get(
                                f"{wna16_slot_prefix}_current_wna16_arg_compatible",
                                False,
                            )
                        )
                    )
                    totals[
                        f"{wna16_slot_prefix}_requires_wna16_arg_reinterpretation_count"
                    ] += int(
                        bool(
                            event.get(
                                f"{wna16_slot_prefix}_requires_wna16_arg_reinterpretation",
                                False,
                            )
                        )
                    )
                    totals[f"{wna16_slot_prefix}_explicit_typed_abi_slot_count"] += int(
                        bool(
                            event.get(
                                f"{wna16_slot_prefix}_explicit_typed_abi_slot",
                                False,
                            )
                        )
                    )
                    totals[
                        f"{wna16_slot_prefix}_reuses_current_wna16_arg_slot_count"
                    ] += int(
                        bool(
                            event.get(
                                f"{wna16_slot_prefix}_reuses_current_wna16_arg_slot",
                                False,
                            )
                        )
                    )
                attempt_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode"
                )
                if attempt_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_checked_count"
                    ] += 1
                    if not totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode"
                        ] = str(attempt_mode)
                    elif (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode"
                        ]
                        != str(attempt_mode)
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_mismatch_count"
                        ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked",
                                False,
                            )
                        )
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    attempt_reason = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason"
                    )
                    if attempt_reason:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason"
                            ] = str(attempt_reason)
                        elif (
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason"
                            ]
                            != str(attempt_reason)
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_missing_count"
                        ] += 1
                    attempt_column_count = int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count",
                            0,
                        )
                        or 0
                    )
                    if attempt_column_count > totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_max"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_max"
                        ] = attempt_column_count
                    if (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_min"
                        ]
                        == 0
                        or attempt_column_count
                        < totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_min"
                        ]
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_min"
                        ] = attempt_column_count
                    attempt_schema_hash = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash"
                    )
                    if attempt_schema_hash:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash"
                            ] = str(attempt_schema_hash)
                        elif (
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash"
                            ]
                            != str(attempt_schema_hash)
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_missing_count"
                        ] += 1
                    for field in (
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count",
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes",
                    ):
                        totals[field] += int(event.get(field, 0) or 0)
                    attempt_payload_bytes = int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes",
                            0,
                        )
                        or 0
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_violation_count"
                    ] += int(attempt_payload_bytes != 0)
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_kernel_arg_violation_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                elif event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_missing_count"
                    ] += 1
                live_toggle_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode"
                )
                if live_toggle_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_checked_count"
                    ] += 1
                    if not totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode"
                        ] = str(live_toggle_mode)
                    elif (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode"
                        ]
                        != str(live_toggle_mode)
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_mismatch_count"
                        ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked",
                                False,
                            )
                        )
                    )
                    for hash_field, checked_key, missing_key in (
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    live_toggle_reason = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
                    )
                    if live_toggle_reason:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
                            ] = str(live_toggle_reason)
                        elif (
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
                            ]
                            != str(live_toggle_reason)
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_missing_count"
                        ] += 1
                    live_toggle_payload_bytes = int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes",
                            0,
                        )
                        or 0
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes"
                    ] += live_toggle_payload_bytes
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_violation_count"
                    ] += int(live_toggle_payload_bytes != 0)
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_kernel_arg_violation_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                elif event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_missing_count"
                    ] += 1
                live_noop_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode"
                )
                if live_noop_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_checked_count"
                    ] += 1
                    if not totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode"
                        ] = str(live_noop_mode)
                    elif (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode"
                        ]
                        != str(live_noop_mode)
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_mismatch_count"
                        ] += 1
                    for field, count_key in (
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked_count",
                        ),
                    ):
                        totals[count_key] += int(bool(event.get(field, False)))
                    for hash_field, checked_key, missing_key in (
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    live_noop_reason = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason"
                    )
                    if live_noop_reason:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason"
                            ] = str(live_noop_reason)
                        elif (
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason"
                            ]
                            != str(live_noop_reason)
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_missing_count"
                        ] += 1
                    live_noop_payload_bytes = int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes",
                            0,
                        )
                        or 0
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes"
                    ] += live_noop_payload_bytes
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_violation_count"
                    ] += int(live_noop_payload_bytes != 0)
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel",
                                False,
                            )
                        )
                    )
                    live_noop_changes_kernel_args = int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_kernel_arg_violation_count"
                    ] += live_noop_changes_kernel_args
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count"
                    ] += live_noop_changes_kernel_args
                elif event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_missing_count"
                    ] += 1
                adapter_mode = event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode"
                )
                if adapter_mode is not None:
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_checked_count"
                    ] += 1
                    if not totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode"
                    ]:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode"
                        ] = str(adapter_mode)
                    elif (
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode"
                        ]
                        != str(adapter_mode)
                    ):
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_mismatch_count"
                        ] += 1
                    for field, count_key in (
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked_count",
                        ),
                    ):
                        totals[count_key] += int(bool(event.get(field, False)))
                    for hash_field, checked_key, missing_key in (
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash_missing_count",
                        ),
                        (
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash_checked_count",
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash_missing_count",
                        ),
                    ):
                        if event.get(hash_field):
                            totals[checked_key] += 1
                        else:
                            totals[missing_key] += 1
                    adapter_reason = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
                    )
                    if adapter_reason:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
                            ] = str(adapter_reason)
                        elif (
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
                            ]
                            != str(adapter_reason)
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_missing_count"
                        ] += 1
                    integration_reason = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason"
                    )
                    if integration_reason:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason"
                            ] = str(integration_reason)
                        elif (
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason"
                            ]
                            != str(integration_reason)
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_missing_count"
                        ] += 1
                    adapter_payload_bytes = int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes",
                            0,
                        )
                        or 0
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes"
                    ] += adapter_payload_bytes
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_violation_count"
                    ] += int(adapter_payload_bytes != 0)
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel",
                                False,
                            )
                        )
                    )
                    adapter_changes_kernel_args = int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_kernel_arg_violation_count"
                    ] += adapter_changes_kernel_args
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
                    ] += adapter_changes_kernel_args
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass",
                                False,
                            )
                        )
                    )
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff",
                                False,
                            )
                        )
                    )
                elif event.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode"
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_missing_count"
                    ] += 1
                if (
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed"
                    in event
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed",
                                False,
                            )
                        )
                    )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count",
                        0,
                    )
                    or 0
                )
                object_payload_bytes = int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_bytes",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_bytes"
                ] += object_payload_bytes
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_violation_count"
                ] += int(object_payload_bytes != 0)
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel",
                            False,
                        )
                    )
                )
                if (
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok"
                    in event
                ):
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count"
                    ] += 1
                    totals[
                        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_count"
                    ] += int(
                        bool(
                            event.get(
                                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok",
                                False,
                            )
                        )
                    )
                    dry_schema_hash = event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash"
                    )
                    if dry_schema_hash:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_checked_count"
                        ] += 1
                        if not totals[
                            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash"
                        ]:
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash"
                            ] = str(dry_schema_hash)
                        elif (
                            str(dry_schema_hash)
                            != totals[
                                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash"
                            ]
                        ):
                            totals[
                                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_mismatch_count"
                            ] += 1
                    else:
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_missing_count"
                        ] += 1
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max"
                ] = max(
                    int(
                        totals[
                            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max"
                        ]
                    ),
                    int(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count",
                            0,
                        )
                        or 0
                    ),
                )
                for field in (
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count",
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count",
                ):
                    totals[field] += int(event.get(field, 0) or 0)
                dry_payload_bytes = int(
                    event.get(
                        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes"
                ] += dry_payload_bytes
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_violation_count"
                ] += int(dry_payload_bytes != 0)
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel",
                            False,
                        )
                    )
                )
                totals["premap_consumer_descriptor_prep_consumer_shim_ok_count"] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_ok",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_consumer_shim_changes_kernel_launch_args",
                            False,
                        )
                    )
                )
            if "premap_consumer_descriptor_prep_kernel_arg_shadow_table_mode" in event:
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count"
                ] += 1
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max"
                ] = max(
                    int(
                        totals[
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max"
                        ]
                    ),
                    int(
                        event.get(
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count",
                            0,
                        )
                        or 0
                    ),
                )
                table_column_count = int(
                    event.get(
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count",
                        0,
                    )
                    or 0
                )
                table_column_min_key = (
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min"
                )
                current_column_min = int(totals[table_column_min_key] or 0)
                totals[table_column_min_key] = (
                    table_column_count
                    if current_column_min <= 0
                    else min(current_column_min, table_column_count)
                )
                table_schema_hash = str(
                    event.get(
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash",
                        "",
                    )
                    or ""
                )
                if table_schema_hash:
                    totals[
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count"
                    ] += 1
                    aggregate_schema_hash = str(
                        totals[
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
                        ]
                        or ""
                    )
                    if not aggregate_schema_hash:
                        totals[
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
                        ] = table_schema_hash
                    elif aggregate_schema_hash != table_schema_hash:
                        totals[
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count"
                        ] += 1
                else:
                    totals[
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count"
                    ] += 1
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count"
                ] += int(
                    event.get(
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count",
                        0,
                    )
                    or 0
                )
                table_payload_bytes = int(
                    event.get(
                        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes",
                        0,
                    )
                    or 0
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes"
                ] += table_payload_bytes
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_violation_count"
                ] += int(table_payload_bytes != 0)
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_router",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_descriptor_order",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_kernel_launch_args",
                            False,
                        )
                    )
                )
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count"
                ] += int(
                    bool(
                        event.get(
                            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel",
                            False,
                        )
                    )
                )
            if "premap_consumer_descriptor_prep_execution_ok" in event:
                totals["premap_consumer_descriptor_prep_executed_count"] += 1
                totals["premap_consumer_descriptor_prep_checked_count"] += 1
                totals["premap_consumer_descriptor_prep_execution_ok_count"] += int(
                    bool(event.get("premap_consumer_descriptor_prep_execution_ok", False))
                )
            # Attempted means the lab/runtime config activated descriptor prep
            # execution for this consumer event.  It intentionally includes
            # gated/blocked events; executed_count is the stricter count of
            # events that actually resolved descriptor/address objects.
            if "premap_consumer_descriptor_prep_execution_mode" in event:
                totals["premap_consumer_descriptor_prep_attempted_count"] += 1
            totals["premap_consumer_descriptor_prep_blocked_count"] += int(
                bool(event.get("premap_consumer_descriptor_prep_blocked_reason"))
            )
            totals["premap_consumer_all_hit_count"] += int(
                bool(event.get("premap_consumer_all_hit", False))
            )
            totals["premap_consumer_parity_ok_count"] += int(
                bool(event.get("premap_consumer_parity_ok", False))
            )
            totals["premap_consumer_error_count"] += int(
                bool(event.get("premap_consumer_error"))
            )
            totals["premap_consumer_payload_violation_count"] += int(
                int(event.get("premap_consumer_payload_bytes", 0) or 0) != 0
            )
            totals["premap_consumer_router_change_violation_count"] += int(
                bool(event.get("premap_consumer_changes_router", False))
            )
            totals["premap_consumer_descriptor_order_change_violation_count"] += int(
                bool(event.get("premap_consumer_changes_descriptor_order", False))
            )
            totals["premap_consumer_ready_credit_violation_count"] += int(
                bool(event.get("premap_consumer_ready_credit", False))
            )
            if "premap_consumer_lookup_us" in event:
                totals["premap_consumer_lookup_us_sum"] += float(
                    event.get("premap_consumer_lookup_us", 0.0) or 0.0
                )
                totals["premap_consumer_lookup_us_count"] += 1
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
        elif event_type == "outcome_aggregate":
            totals["outcome_aggregate_count"] += 1
            totals["outcome_aggregate_token_count"] += int(event.get("token_count", 0) or 0)
            totals["outcome_aggregate_topk_entry_count"] += int(
                event.get("topk_entry_count", 0) or 0
            )
            totals["outcome_aggregate_routed_expert_count_sum"] += int(
                event.get("routed_expert_count", 0) or 0
            )
            totals["outcome_aggregate_topk_weight_mass_sum"] += float(
                event.get("topk_weight_mass_sum", 0.0) or 0.0
            )
            totals["outcome_aggregate_top1_weight_sum"] += float(
                event.get("top1_weight_sum", 0.0) or 0.0
            )

    outcome_count = max(1, int(totals["outcome_count"]))
    summary_event_count = int(totals["summary_count"]) + int(
        totals["descriptor_summary_min_count"]
    ) + int(totals["premap_summary_count"])
    summary_count = max(1, summary_event_count)
    totals["top1_ready_rate"] = totals["top1_ready_count"] / outcome_count
    totals["weighted_top1_miss_mean"] = totals["weighted_top1_miss_sum"] / outcome_count
    totals["covered_mass_mean"] = totals["covered_mass_sum"] / outcome_count
    totals["miss_mass_mean"] = totals["miss_mass_sum"] / outcome_count
    totals["decision_summary_count"] = summary_event_count
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
    totals["descriptor_window_count_mean"] = (
        totals["descriptor_window_count_sum"] / descriptor_count
    )
    lru8_count = max(1, int(totals["descriptor_order_lru_at_8_count"]))
    lru16_count = max(1, int(totals["descriptor_order_lru_at_16_count"]))
    hit_count = max(1, int(totals["descriptor_order_hit_rate_count"]))
    reuse_count = max(1, int(totals["descriptor_reuse_distance_mean_count"]))
    unique_window_count = max(
        1, int(totals["descriptor_unique_tiles_per_window_mean_count"])
    )
    totals["descriptor_order_lru_at_8_mean"] = (
        totals["descriptor_order_lru_at_8_sum"] / lru8_count
    )
    totals["descriptor_order_lru_at_16_mean"] = (
        totals["descriptor_order_lru_at_16_sum"] / lru16_count
    )
    totals["descriptor_order_hit_rate_mean"] = (
        totals["descriptor_order_hit_rate_sum"] / hit_count
    )
    totals["descriptor_reuse_distance_mean"] = (
        totals["descriptor_reuse_distance_mean_sum"] / reuse_count
    )
    totals["descriptor_unique_tiles_per_window_mean"] = (
        totals["descriptor_unique_tiles_per_window_mean_sum"] / unique_window_count
    )
    avg_group_count = max(1, int(totals["descriptor_group_plan_avg_group_size_count"]))
    p95_group_count = max(1, int(totals["descriptor_group_plan_p95_group_size_count"]))
    cta_count = max(1, int(totals["descriptor_group_plan_cta_count_count"]))
    totals["descriptor_group_plan_group_count_mean"] = (
        totals["descriptor_group_plan_group_count_sum"] / descriptor_count
    )
    totals["descriptor_group_plan_avg_group_size_mean"] = (
        totals["descriptor_group_plan_avg_group_size_sum"] / avg_group_count
    )
    totals["descriptor_group_plan_p95_group_size_mean"] = (
        totals["descriptor_group_plan_p95_group_size_sum"] / p95_group_count
    )
    totals["descriptor_group_plan_cta_count_mean"] = (
        totals["descriptor_group_plan_cta_count_sum"] / cta_count
    )
    premap_summary_count = max(1, int(totals["premap_summary_count"]))
    premap_build_count = max(1, int(totals["premap_summary_build_us_count"]))
    totals["premap_summary_unique_experts_mean"] = (
        totals["premap_summary_unique_experts_sum"] / premap_summary_count
    )
    totals["premap_summary_unique_layers_mean"] = (
        totals["premap_summary_unique_layers_sum"] / premap_summary_count
    )
    totals["premap_summary_unique_sample_layers_mean"] = (
        totals["premap_summary_unique_sample_layers_sum"] / premap_summary_count
    )
    totals["premap_summary_build_us_mean"] = (
        totals["premap_summary_build_us_sum"] / premap_build_count
    )
    premap_address_manager_count = max(1, int(totals["premap_address_manager_count"]))
    totals["premap_address_reuse_rate_mean"] = (
        totals["premap_address_reuse_rate_sum"] / premap_address_manager_count
    )
    totals["premap_address_eviction_pressure_mean"] = (
        totals["premap_address_eviction_pressure_sum"] / premap_address_manager_count
    )
    premap_payload_cache_manager_count = max(
        1, int(totals["premap_payload_cache_manager_count"])
    )
    totals["premap_payload_cache_demand_hit_rate_mean"] = (
        totals["premap_payload_cache_demand_hit_rate_sum"]
        / premap_payload_cache_manager_count
    )
    totals["premap_payload_cache_used_fetch_rate_mean"] = (
        totals["premap_payload_cache_used_fetch_rate_sum"]
        / premap_payload_cache_manager_count
    )
    totals["premap_payload_cache_eviction_pressure_mean"] = (
        totals["premap_payload_cache_eviction_pressure_sum"]
        / premap_payload_cache_manager_count
    )
    premap_consumer_mapping_count = max(
        1, int(totals["premap_consumer_mapping_count"])
    )
    premap_consumer_lookup_count = max(
        1, int(totals["premap_consumer_lookup_us_count"])
    )
    totals["premap_consumer_address_hit_rate"] = (
        totals["premap_consumer_address_hit_count"]
        / max(
            1,
            int(totals["premap_consumer_address_hit_count"])
            + int(totals["premap_consumer_address_miss_count"]),
        )
    )
    totals["premap_consumer_descriptor_handle_hit_rate"] = (
        totals["premap_consumer_descriptor_handle_hit_count"]
        / max(
            1,
            int(totals["premap_consumer_descriptor_handle_hit_count"])
            + int(totals["premap_consumer_descriptor_handle_miss_count"]),
        )
    )
    totals["premap_consumer_all_hit_rate"] = (
        totals["premap_consumer_all_hit_count"] / premap_consumer_mapping_count
    )
    totals["premap_consumer_parity_ok_rate"] = (
        totals["premap_consumer_parity_ok_count"] / premap_consumer_mapping_count
    )
    totals["premap_consumer_descriptor_handle_parity_ok_rate"] = (
        totals["premap_consumer_descriptor_handle_parity_ok_count"]
        / premap_consumer_mapping_count
    )
    totals["premap_consumer_prelaunch_boundary_aligned_rate"] = (
        totals["premap_consumer_prelaunch_boundary_aligned_count"]
        / max(1, int(totals["premap_consumer_prelaunch_boundary_checked_count"]))
    )
    totals["premap_consumer_prelaunch_handle_available_rate"] = (
        totals["premap_consumer_prelaunch_handle_available_count"]
        / max(1, int(totals["premap_consumer_prelaunch_boundary_checked_count"]))
    )
    totals["premap_consumer_lookup_after_prepare_rate"] = (
        totals["premap_consumer_lookup_after_prepare_count"]
        / premap_consumer_mapping_count
    )
    totals["premap_consumer_real_descriptor_handle_hit_rate"] = (
        totals["premap_consumer_real_descriptor_handle_hit_count"]
        / max(
            1,
            int(totals["premap_consumer_real_descriptor_handle_hit_count"])
            + int(totals["premap_consumer_real_descriptor_handle_miss_count"]),
        )
    )
    totals["premap_consumer_real_descriptor_handle_available_rate"] = (
        totals["premap_consumer_real_descriptor_handle_available_count"]
        / premap_consumer_mapping_count
    )
    totals["premap_consumer_readonly_handle_hit_rate"] = (
        totals["premap_consumer_readonly_handle_hit_count"]
        / max(
            1,
            int(totals["premap_consumer_readonly_handle_hit_count"])
            + int(totals["premap_consumer_readonly_handle_miss_count"]),
        )
    )
    totals["premap_consumer_readonly_evicted_before_consume_rate"] = (
        totals["premap_consumer_readonly_evicted_before_consume_count"]
        / max(1, int(totals["premap_consumer_readonly_lookup_count"]))
    )
    totals["premap_consumer_readonly_stale_handle_rate"] = (
        totals["premap_consumer_readonly_stale_handle_count"]
        / max(1, int(totals["premap_consumer_readonly_lookup_count"]))
    )
    totals["premap_consumer_readonly_handle_parity_ok_rate"] = (
        totals["premap_consumer_readonly_handle_parity_ok_count"]
        / max(1, int(totals["premap_consumer_readonly_handle_parity_checked_count"]))
    )
    totals["premap_consumer_descriptor_prep_handle_hit_rate"] = (
        totals["premap_consumer_descriptor_prep_handle_count"]
        / max(
            1,
            int(totals["premap_consumer_descriptor_prep_handle_count"])
            + int(totals["premap_consumer_descriptor_prep_missing_handle_count"]),
        )
    )
    totals["premap_consumer_descriptor_prep_execution_ok_rate"] = (
        totals["premap_consumer_descriptor_prep_execution_ok_count"]
        / max(1, int(totals["premap_consumer_descriptor_prep_checked_count"]))
    )
    totals["premap_consumer_descriptor_prep_execution_ok_attempted_rate"] = (
        totals["premap_consumer_descriptor_prep_execution_ok_count"]
        / max(1, int(totals["premap_consumer_descriptor_prep_attempted_count"]))
    )
    totals["premap_consumer_descriptor_prep_real_handle_hit_rate"] = (
        totals["premap_consumer_descriptor_prep_real_handle_count"]
        / max(
            1,
            int(totals["premap_consumer_descriptor_prep_real_handle_count"])
            + int(totals["premap_consumer_descriptor_prep_real_handle_miss_count"])
            + int(totals["premap_consumer_descriptor_prep_missing_handle_count"]),
        )
    )
    totals["premap_consumer_descriptor_prep_real_handle_backed_rate"] = (
        totals["premap_consumer_descriptor_prep_real_handle_backed_count"]
        / max(1, int(totals["premap_consumer_descriptor_prep_attempted_count"]))
    )
    # Consumer objects are a stricter executable-view projection of lookups,
    # so this rate intentionally uses all descriptor-prep lookup requests as
    # the denominator rather than the real-handle hit-rate denominator above.
    totals["premap_consumer_descriptor_prep_consumer_object_rate"] = (
        totals["premap_consumer_descriptor_prep_consumer_object_count"]
        / max(1, int(totals["premap_consumer_descriptor_prep_lookup_count"]))
    )
    totals["premap_consumer_descriptor_prep_consumer_object_read_hit_rate"] = (
        totals["premap_consumer_descriptor_prep_consumer_object_read_hit_count"]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_object_read_lookup_count"
                ]
            ),
        )
    )
    totals["premap_consumer_descriptor_prep_consumer_object_stale_rate"] = (
        totals["premap_consumer_descriptor_prep_consumer_object_stale_count"]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_object_read_lookup_count"
                ]
            ),
        )
    )
    totals["premap_consumer_descriptor_prep_consumer_object_read_ok_rate"] = (
        totals["premap_consumer_descriptor_prep_consumer_object_read_ok_count"]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_object_read_checked_count"
                ]
            ),
        )
    )
    totals["premap_consumer_descriptor_prep_consumer_shim_ok_rate"] = (
        totals["premap_consumer_descriptor_prep_consumer_shim_ok_count"]
        / max(
            1,
            int(totals["premap_consumer_descriptor_prep_consumer_shim_executed_count"]),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count"
        ]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
                ]
            ),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count"
    ] = max(
        0,
        int(totals["premap_consumer_descriptor_prep_consumer_shim_executed_count"])
        - int(
            totals[
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
            ]
        ),
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count"
        ]
        / max(
            1,
            int(totals["premap_consumer_descriptor_prep_consumer_shim_executed_count"]),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count"
        ]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
                ]
            ),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_count"
        ]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
                ]
            ),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_count"
        ]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
                ]
            ),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_count"
        ]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count"
                ]
            ),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_count"
        ]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count"
                ]
            ),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_count"
        ]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count"
                ]
            ),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_count"
        ]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count"
                ]
            ),
        )
    )
    totals["premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate"] = (
        totals["premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_count"]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count"
                ]
            ),
        )
    )
    totals[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate"
    ] = (
        totals[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_count"
        ]
        / max(
            1,
            int(
                totals[
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count"
                ]
            ),
        )
    )
    totals["premap_consumer_descriptor_prep_blocked_rate"] = (
        totals["premap_consumer_descriptor_prep_blocked_count"]
        / premap_consumer_mapping_count
    )
    totals["premap_consumer_descriptor_prep_blocked_attempted_rate"] = (
        totals["premap_consumer_descriptor_prep_blocked_count"]
        / max(1, int(totals["premap_consumer_descriptor_prep_attempted_count"]))
    )
    totals["premap_consumer_lookup_us_mean"] = (
        totals["premap_consumer_lookup_us_sum"] / premap_consumer_lookup_count
    )
    aggregate_count = max(1, int(totals["outcome_aggregate_count"]))
    aggregate_token_count = max(1, int(totals["outcome_aggregate_token_count"]))
    totals["outcome_aggregate_routed_expert_count_mean"] = (
        totals["outcome_aggregate_routed_expert_count_sum"] / aggregate_count
    )
    totals["outcome_aggregate_top1_weight_mean"] = (
        totals["outcome_aggregate_top1_weight_sum"] / aggregate_token_count
    )
    for key in (
        "_premap_address_new_count_prev",
        "_premap_address_reused_count_prev",
        "_premap_address_evicted_count_prev",
        "_premap_payload_cache_issued_fetch_count_prev_by_manager",
        "_premap_payload_cache_used_fetch_count_prev_by_manager",
        "_premap_payload_cache_demand_count_prev_by_manager",
        "_premap_payload_cache_demand_hit_count_prev_by_manager",
        "_premap_payload_cache_demand_miss_count_prev_by_manager",
        "_premap_payload_cache_evicted_before_use_count_prev_by_manager",
        "_premap_payload_cache_ready_late_miss_count_prev_by_manager",
        "_premap_payload_cache_late_completion_unused_count_prev_by_manager",
        "_premap_payload_cache_queue_batch_count_prev_by_manager",
        "_premap_payload_cache_queue_service_us_prev_by_manager",
        "_premap_payload_cache_queue_wait_us_prev_by_manager",
    ):
        totals.pop(key, None)
    return totals


def _accumulate_monotonic_snapshot_delta(
    totals: dict[str, Any],
    key: str,
    current: int,
    *,
    stream_key: str | None = None,
) -> None:
    if stream_key is None:
        prev_key = f"_{key}_prev"
        previous = totals.get(prev_key)
    else:
        prev_key = f"_{key}_prev_by_manager"
        previous_by_stream = totals.setdefault(prev_key, {})
        previous = previous_by_stream.get(str(stream_key))
    if previous is None:
        delta = int(current)
    elif int(current) >= int(previous):
        delta = int(current) - int(previous)
    else:
        # A lower snapshot means a new manager/request stream started.
        delta = int(current)
    totals[key] += delta
    if stream_key is None:
        totals[prev_key] = int(current)
    else:
        previous_by_stream[str(stream_key)] = int(current)


def _accumulate_monotonic_snapshot_float_delta(
    totals: dict[str, Any],
    key: str,
    current: float,
    *,
    stream_key: str | None = None,
) -> None:
    if stream_key is None:
        prev_key = f"_{key}_prev"
        previous = totals.get(prev_key)
    else:
        prev_key = f"_{key}_prev_by_manager"
        previous_by_stream = totals.setdefault(prev_key, {})
        previous = previous_by_stream.get(str(stream_key))
    current_value = float(current)
    if previous is None:
        delta = current_value
    elif current_value >= float(previous):
        delta = current_value - float(previous)
    else:
        delta = current_value
    totals[key] += delta
    if stream_key is None:
        totals[prev_key] = current_value
    else:
        previous_by_stream[str(stream_key)] = current_value


def _accumulate_group_plan_totals(totals: dict[str, Any], event: dict[str, Any]) -> None:
    if "descriptor_group_plan_group_count" in event:
        totals["descriptor_group_plan_group_count_sum"] += int(
            event.get("descriptor_group_plan_group_count", 0) or 0
        )
    if "descriptor_group_plan_avg_group_size" in event:
        totals["descriptor_group_plan_avg_group_size_sum"] += float(
            event.get("descriptor_group_plan_avg_group_size", 0.0) or 0.0
        )
        totals["descriptor_group_plan_avg_group_size_count"] += 1
    if "descriptor_group_plan_p95_group_size" in event:
        totals["descriptor_group_plan_p95_group_size_sum"] += float(
            event.get("descriptor_group_plan_p95_group_size", 0.0) or 0.0
        )
        totals["descriptor_group_plan_p95_group_size_count"] += 1
    if "descriptor_group_plan_max_group_size" in event:
        totals["descriptor_group_plan_max_group_size_max"] = max(
            int(totals["descriptor_group_plan_max_group_size_max"]),
            int(event.get("descriptor_group_plan_max_group_size", 0) or 0),
        )
    if "descriptor_group_plan_cta_count" in event:
        totals["descriptor_group_plan_cta_count_sum"] += int(
            event.get("descriptor_group_plan_cta_count", 0) or 0
        )
        totals["descriptor_group_plan_cta_count_count"] += 1


def _put_optional(payload: dict[str, Any], key: str, value: Any | None) -> None:
    if value is not None:
        payload[key] = value
