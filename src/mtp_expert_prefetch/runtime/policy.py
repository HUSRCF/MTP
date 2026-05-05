from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import IntEnum
import math
from typing import Literal


class PrefetchPriority(IntEnum):
    TRUE_ROUTER_MISS = 0
    SHARED_EXPERT = 1
    TRANSITION_HEAD = 2
    TRANSITION_TAIL = 3
    MTP_EXTRA_HEAD = 4
    MTP_EXTRA_TAIL = 5
    FALLBACK = 6


PrefetchMode = Literal["fallback", "low_budget", "default", "high_budget"]
PrefetchGoal = Literal["stall_reduction", "bandwidth_efficiency"]


@dataclass(frozen=True)
class RuntimeSignals:
    transition_ready_rate: float
    cache_pressure: float
    queue_pressure: float
    effective_capacity: int
    mtp_delay_ms: float
    mtp_ready_fraction: float | None = None
    bandwidth_gbps: float | None = None
    layer_ms: float | None = None
    layer_idx: int | None = None
    num_layers: int = 40
    lds_expected_hit_rate: float | None = None
    lds_p_min_hit_rate: float | None = None
    lds_occupancy_blocks_per_cu: int | None = None


@dataclass(frozen=True)
class RuntimePrefetchPolicy:
    mode: PrefetchMode
    transition_topk: int
    mtp_topk: int
    max_extra: int
    metadata_max_extra: int
    tail_swap_count: int
    allow_full_mtp_fetch: bool
    allow_mtp_metadata: bool
    allow_mtp_premap: bool
    allow_lds_stage: bool
    reason: str
    lds_stage_reason: str

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PolicyThresholds:
    min_transition_ready_for_full_mtp: float = 0.90
    max_cache_pressure_for_default: float = 0.80
    max_queue_pressure_for_default: float = 0.80
    max_cache_pressure_for_low_budget: float = 0.90
    max_queue_pressure_for_low_budget: float = 0.90
    max_pressure_for_low_budget_extra2: float = 0.85
    max_cache_pressure_for_high_budget: float = 0.55
    max_queue_pressure_for_high_budget: float = 0.45
    max_cache_pressure_for_metadata: float = 0.80
    max_queue_pressure_for_metadata: float = 0.80
    min_capacity_for_default: int = 128
    min_capacity_for_high_budget: int = 192
    max_mtp_delay_default_ms: float = 4.0
    max_mtp_delay_high_budget_ms: float = 2.0
    metadata_max_extra_default: int = 1
    min_mtp_ready_fraction_for_full_fetch: float = 0.05
    min_bandwidth_layer_product_for_full_fetch: float = 2.0
    lds_hit_rate_safety_margin: float = 0.05
    min_lds_occupancy_blocks_per_cu: int = 2


def select_runtime_prefetch_policy(
    signals: RuntimeSignals,
    *,
    thresholds: PolicyThresholds | None = None,
    transition_topk: int = 32,
    mtp_topk: int = 64,
    optimization_goal: PrefetchGoal = "stall_reduction",
) -> RuntimePrefetchPolicy:
    """Choose the conservative runtime prefetch mode from online signals.

    This policy never authorizes predicted experts to replace true routing. It
    only controls pre-map / prefetch admission for future-token candidates.
    """
    thresholds = thresholds or PolicyThresholds()
    if optimization_goal not in ("stall_reduction", "bandwidth_efficiency"):
        msg = f"Unknown optimization_goal={optimization_goal!r}."
        raise ValueError(msg)
    allow_lds_stage, lds_stage_reason = select_lds_stage_gate(
        signals,
        thresholds=thresholds,
    )
    metadata_allowed = (
        signals.cache_pressure <= thresholds.max_cache_pressure_for_metadata
        and signals.queue_pressure <= thresholds.max_queue_pressure_for_metadata
        and float(signals.mtp_delay_ms) <= float(thresholds.max_mtp_delay_default_ms)
    )
    metadata_max_extra = (
        int(thresholds.metadata_max_extra_default) if metadata_allowed else 0
    )
    if signals.transition_ready_rate < thresholds.min_transition_ready_for_full_mtp:
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            metadata_max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=False,
            allow_mtp_premap=True,
            allow_lds_stage=allow_lds_stage,
            reason="transition_not_ready",
            lds_stage_reason=lds_stage_reason,
        )
    if (
        signals.mtp_ready_fraction is not None
        and float(signals.mtp_ready_fraction)
        < float(thresholds.min_mtp_ready_fraction_for_full_fetch)
    ):
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            metadata_max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=False,
            allow_mtp_premap=True,
            allow_lds_stage=allow_lds_stage,
            reason="mtp_not_ready",
            lds_stage_reason=lds_stage_reason,
        )
    if (
        signals.bandwidth_gbps is not None
        and signals.layer_ms is not None
        and float(signals.bandwidth_gbps) * float(signals.layer_ms)
        < float(thresholds.min_bandwidth_layer_product_for_full_fetch)
    ):
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            metadata_max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=False,
            allow_mtp_premap=True,
            allow_lds_stage=allow_lds_stage,
            reason="transfer_envelope_tight",
            lds_stage_reason=lds_stage_reason,
        )
    if (
        int(signals.effective_capacity) < int(thresholds.min_capacity_for_default)
    ):
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            metadata_max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=False,
            allow_mtp_premap=True,
            allow_lds_stage=allow_lds_stage,
            reason="resource_pressure",
            lds_stage_reason=lds_stage_reason,
        )
    if float(signals.mtp_delay_ms) > float(thresholds.max_mtp_delay_default_ms):
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            metadata_max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=False,
            allow_mtp_premap=True,
            allow_lds_stage=allow_lds_stage,
            reason="mtp_delay_high",
            lds_stage_reason=lds_stage_reason,
        )
    if (
        optimization_goal == "stall_reduction"
        and
        int(signals.effective_capacity) >= int(thresholds.min_capacity_for_high_budget)
        and signals.cache_pressure <= thresholds.max_cache_pressure_for_high_budget
        and signals.queue_pressure <= thresholds.max_queue_pressure_for_high_budget
        and float(signals.mtp_delay_ms) <= float(thresholds.max_mtp_delay_high_budget_ms)
    ):
        return RuntimePrefetchPolicy(
            mode="high_budget",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=8,
            metadata_max_extra=metadata_max_extra,
            tail_swap_count=0,
            allow_full_mtp_fetch=True,
            allow_mtp_metadata=metadata_allowed,
            allow_mtp_premap=True,
            allow_lds_stage=allow_lds_stage,
            reason="capacity_and_queue_idle",
            lds_stage_reason=lds_stage_reason,
        )
    if optimization_goal == "bandwidth_efficiency":
        if (
            signals.cache_pressure <= thresholds.max_cache_pressure_for_default
            and signals.queue_pressure <= thresholds.max_queue_pressure_for_default
        ):
            return RuntimePrefetchPolicy(
                mode="low_budget",
                transition_topk=transition_topk,
                mtp_topk=mtp_topk,
                max_extra=2,
                metadata_max_extra=metadata_max_extra,
                tail_swap_count=2,
                allow_full_mtp_fetch=True,
                allow_mtp_metadata=metadata_allowed,
                allow_mtp_premap=True,
                allow_lds_stage=allow_lds_stage,
                reason="bandwidth_efficiency_extra2_tail_swap2",
                lds_stage_reason=lds_stage_reason,
            )
        if (
            signals.cache_pressure <= thresholds.max_cache_pressure_for_low_budget
            and signals.queue_pressure <= thresholds.max_queue_pressure_for_low_budget
        ):
            return RuntimePrefetchPolicy(
                mode="low_budget",
                transition_topk=transition_topk,
                mtp_topk=mtp_topk,
                max_extra=1,
                metadata_max_extra=0,
                tail_swap_count=1,
                allow_full_mtp_fetch=True,
                allow_mtp_metadata=False,
                allow_mtp_premap=True,
                allow_lds_stage=allow_lds_stage,
                reason="bandwidth_efficiency_extra1_tail_swap1",
                lds_stage_reason=lds_stage_reason,
            )
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            metadata_max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=False,
            allow_mtp_premap=True,
            allow_lds_stage=allow_lds_stage,
            reason="resource_pressure",
            lds_stage_reason=lds_stage_reason,
        )
    if (
        signals.cache_pressure <= thresholds.max_cache_pressure_for_default
        and signals.queue_pressure <= thresholds.max_queue_pressure_for_default
    ):
        return RuntimePrefetchPolicy(
            mode="default",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=4,
            metadata_max_extra=metadata_max_extra,
            tail_swap_count=0,
            allow_full_mtp_fetch=True,
            allow_mtp_metadata=metadata_allowed,
            allow_mtp_premap=True,
            allow_lds_stage=allow_lds_stage,
            reason="normal_envelope",
            lds_stage_reason=lds_stage_reason,
        )
    if (
        signals.cache_pressure <= thresholds.max_cache_pressure_for_low_budget
        and signals.queue_pressure <= thresholds.max_queue_pressure_for_low_budget
    ):
        worst_pressure = max(float(signals.cache_pressure), float(signals.queue_pressure))
        max_extra = (
            2
            if worst_pressure <= float(thresholds.max_pressure_for_low_budget_extra2)
            else 1
        )
        return RuntimePrefetchPolicy(
            mode="low_budget",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
            metadata_max_extra=0,
            tail_swap_count=max_extra,
            allow_full_mtp_fetch=True,
            allow_mtp_metadata=False,
            allow_mtp_premap=True,
            allow_lds_stage=allow_lds_stage,
            reason=f"pressure_degraded_extra{max_extra}_tail_swap{max_extra}",
            lds_stage_reason=lds_stage_reason,
        )
    return RuntimePrefetchPolicy(
        mode="fallback",
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=0,
        metadata_max_extra=0,
        tail_swap_count=0,
        allow_full_mtp_fetch=False,
        allow_mtp_metadata=False,
        allow_mtp_premap=True,
        allow_lds_stage=allow_lds_stage,
        reason="resource_pressure",
        lds_stage_reason=lds_stage_reason,
    )


def select_lds_stage_gate(
    signals: RuntimeSignals,
    *,
    thresholds: PolicyThresholds | None = None,
) -> tuple[bool, str]:
    """Decide whether on-chip speculative LDS tile staging is eligible.

    This gate is intentionally independent from H2D expert full-fetch admission:
    LDS staging is a kernel-internal action. It is allowed only when the
    expected tile hit rate beats the microbench break-even `p_min` with a safety
    margin and the occupancy budget is not obviously too low.
    """
    thresholds = thresholds or PolicyThresholds()
    if signals.transition_ready_rate < thresholds.min_transition_ready_for_full_mtp:
        return False, "transition_not_ready"
    if signals.lds_expected_hit_rate is None or signals.lds_p_min_hit_rate is None:
        return False, "lds_missing_calibration"
    if not math.isfinite(float(signals.lds_p_min_hit_rate)):
        return False, "lds_p_min_not_profitable"
    if signals.lds_occupancy_blocks_per_cu is not None and int(
        signals.lds_occupancy_blocks_per_cu
    ) < int(thresholds.min_lds_occupancy_blocks_per_cu):
        return False, "lds_occupancy_low"
    required_hit_rate = float(signals.lds_p_min_hit_rate) + float(
        thresholds.lds_hit_rate_safety_margin
    )
    if float(signals.lds_expected_hit_rate) < required_hit_rate:
        return False, "lds_hit_rate_below_p_min"
    return True, "lds_hit_rate_above_p_min"


def priority_name(priority: int | PrefetchPriority) -> str:
    priority = PrefetchPriority(int(priority))
    return priority.name.lower()
