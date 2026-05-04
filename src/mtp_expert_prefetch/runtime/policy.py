from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import IntEnum
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
    layer_idx: int | None = None
    num_layers: int = 40


@dataclass(frozen=True)
class RuntimePrefetchPolicy:
    mode: PrefetchMode
    transition_topk: int
    mtp_topk: int
    max_extra: int
    tail_swap_count: int
    allow_full_mtp_fetch: bool
    allow_mtp_metadata: bool
    reason: str

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
    min_capacity_for_default: int = 128
    min_capacity_for_high_budget: int = 192
    max_mtp_delay_default_ms: float = 4.0
    max_mtp_delay_high_budget_ms: float = 2.0


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
    if signals.transition_ready_rate < thresholds.min_transition_ready_for_full_mtp:
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=True,
            reason="transition_not_ready",
        )
    if (
        int(signals.effective_capacity) < int(thresholds.min_capacity_for_default)
    ):
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=True,
            reason="resource_pressure",
        )
    if float(signals.mtp_delay_ms) > float(thresholds.max_mtp_delay_default_ms):
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=True,
            reason="mtp_delay_high",
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
            tail_swap_count=0,
            allow_full_mtp_fetch=True,
            allow_mtp_metadata=True,
            reason="capacity_and_queue_idle",
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
                tail_swap_count=2,
                allow_full_mtp_fetch=True,
                allow_mtp_metadata=True,
                reason="bandwidth_efficiency_extra2_tail_swap2",
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
                tail_swap_count=1,
                allow_full_mtp_fetch=True,
                allow_mtp_metadata=True,
                reason="bandwidth_efficiency_extra1_tail_swap1",
            )
        return RuntimePrefetchPolicy(
            mode="fallback",
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=0,
            tail_swap_count=0,
            allow_full_mtp_fetch=False,
            allow_mtp_metadata=True,
            reason="resource_pressure",
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
            tail_swap_count=0,
            allow_full_mtp_fetch=True,
            allow_mtp_metadata=True,
            reason="normal_envelope",
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
            tail_swap_count=max_extra,
            allow_full_mtp_fetch=True,
            allow_mtp_metadata=True,
            reason=f"pressure_degraded_extra{max_extra}_tail_swap{max_extra}",
        )
    return RuntimePrefetchPolicy(
        mode="fallback",
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=0,
        tail_swap_count=0,
        allow_full_mtp_fetch=False,
        allow_mtp_metadata=True,
        reason="resource_pressure",
    )


def priority_name(priority: int | PrefetchPriority) -> str:
    priority = PrefetchPriority(int(priority))
    return priority.name.lower()
