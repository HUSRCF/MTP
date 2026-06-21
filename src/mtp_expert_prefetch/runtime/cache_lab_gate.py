from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence


@dataclass(frozen=True)
class CacheLabGateConfig:
    """Replay-derived admission envelope for full-fetch MTP extras.

    The units intentionally match the bounded-cache replay reports:
    capacity is a global `(layer, expert)` payload residency count, not the
    older per-layer candidate budget used by `RuntimeSignals.effective_capacity`.
    """

    min_payload_capacity: int = 10240
    min_overlap_factor: float = 0.5
    max_manager_us_per_issue: float = 50.0
    min_bandwidth_gbps: float = 3.0
    max_bandwidth_gbps: float | None = 12.0
    require_stress_fallback_clear: bool = True

    def as_dict(self) -> dict[str, bool | float | int | None]:
        return asdict(self)


@dataclass(frozen=True)
class CacheLabRuntimeSignals:
    payload_capacity: int
    overlap_factor: float
    manager_us_per_issue: float
    bandwidth_gbps: float
    stress_fallback_active: bool = False
    ready_time_allow_full_fetch: bool | None = None

    def as_dict(self) -> dict[str, bool | float | int | None]:
        return asdict(self)


@dataclass(frozen=True)
class CacheLabGateDecision:
    allow_full_fetch_mtp: bool
    reason: str
    payload_capacity: int
    overlap_factor: float
    manager_us_per_issue: float
    bandwidth_gbps: float
    stress_fallback_active: bool
    ready_time_allow_full_fetch: bool | None = None

    def as_dict(self) -> dict[str, bool | float | int | str | None]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheRuntimeParticipation:
    """Payload-cache runtime participation contract before live transfer.

    This object is intentionally payloadless. It records that the online path
    has a manager snapshot and enough issue/demand accounting to be considered
    by a future cache-manager runtime, while keeping all side-effectful gates
    closed: no payload transfer, no ready credit, and no kernel argument
    mutation.
    """

    present: bool
    stage: str
    status: str
    consumes_manager_snapshot: bool
    manager_mode: str
    issue_sources: tuple[str, ...]
    demand_on_consumer: bool
    payload_bytes: int = 0
    ready_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    payload_transfer_runtime_enabled: bool = False
    issued_fetch_count: int = 0
    used_fetch_count: int = 0
    demand_count: int = 0
    demand_hit_count: int = 0
    ready_late_miss_count: int = 0
    queue_batch_size: int | None = None
    queue_deadline_us: float | None = None
    candidate_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.payload_bytes, int) or isinstance(
            self.payload_bytes,
            bool,
        ):
            raise TypeError("payload_bytes must be an integer")
        if self.payload_bytes != 0:
            raise ValueError("payload-cache runtime participation must be payloadless")
        for field_name in (
            "ready_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "payload_transfer_runtime_enabled",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str | tuple[str, ...] | None]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheRuntimePlan:
    """Payload-cache runtime plan dry-run before live payload execution.

    This object is the next lab-gated contract after runtime participation.
    It consumes the participation evidence and records the plan state that a
    future payload/cache-manager runtime would inspect, while still forbidding
    payload movement, ready credit, kernel argument handoff, and live full
    fetch execution.
    """

    present: bool
    stage: str
    status: str
    consumes_participation: bool
    participation_status: str
    live_payload_runtime_enabled: bool = False
    planned_issue_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    kernel_arg_pass_allowed: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("runtime plan must be present")
        if self.stage != "payload_cache_runtime_plan_lab_gate_dry_run":
            raise ValueError("runtime plan stage mismatch")
        if not isinstance(self.participation_status, str) or not self.participation_status:
            raise TypeError("participation_status must be a nonempty string")
        if self.participation_status == "ready_time_candidate_requires_lab_gate":
            expected_status = (
                "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
            )
        else:
            expected_status = (
                f"participation_not_full_fetch_candidate:{self.participation_status}"
            )
        if self.status != expected_status:
            raise ValueError("runtime plan status does not match participation status")
        for field_name in ("planned_issue_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero in dry-run")
        for field_name in (
            "live_payload_runtime_enabled",
            "ready_credit",
            "kernel_arg_pass_allowed",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")
        if self.consumes_participation is not True:
            raise ValueError("runtime plan must consume participation evidence")

    def as_dict(self) -> dict[str, bool | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheRuntimeExecutionDryRun:
    """Payload-cache execution dry-run before any live payload side effect.

    This is the next contract after ``PayloadCacheRuntimePlan``. It records
    that a runtime consumer has inspected the plan and reached an execution
    decision, while still forbidding all side effects: no payload movement, no
    ready credit, no kernel argument handoff, and no full-fetch runtime enable.
    """

    present: bool
    stage: str
    status: str
    consumes_plan: bool
    plan_status: str
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    decision: str = "blocked"
    block_reason: str = ""
    execution_mode: str = "payloadless_lab_gate_dry_run"

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("runtime execution dry-run must be present")
        if self.stage != "payload_cache_runtime_execution_lab_gate_dry_run":
            raise ValueError("runtime execution dry-run stage mismatch")
        if not isinstance(self.plan_status, str) or not self.plan_status:
            raise TypeError("plan_status must be a nonempty string")
        expected_status = f"blocked_by_runtime_plan:{self.plan_status}"
        if self.status != expected_status:
            raise ValueError("runtime execution status does not match plan status")
        if self.block_reason == "":
            object.__setattr__(self, "block_reason", self.plan_status)
        elif not isinstance(self.block_reason, str):
            raise TypeError("block_reason must be a string")
        if self.decision != "blocked":
            raise ValueError("runtime execution dry-run decision must stay blocked")
        if self.block_reason != self.plan_status:
            raise ValueError("runtime execution block reason must match plan status")
        if self.execution_mode != "payloadless_lab_gate_dry_run":
            raise ValueError("runtime execution mode mismatch")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero in dry-run")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "ready_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")
        if self.consumes_plan is not True:
            raise ValueError("runtime execution dry-run must consume runtime plan")

    def as_dict(self) -> dict[str, bool | int | str]:
        return asdict(self)


def select_cache_lab_prefetch_gate(
    signals: CacheLabRuntimeSignals,
    *,
    config: CacheLabGateConfig | None = None,
) -> CacheLabGateDecision:
    """Apply the bounded-cache replay gate for MTP full-fetch admission.

    This is a contract for controlled cache-manager prototypes. It does not
    perform routing, issue DMA, or change descriptor/tile execution order.
    """

    config = config or CacheLabGateConfig()
    reason = _gate_reason(signals, config)
    return CacheLabGateDecision(
        allow_full_fetch_mtp=reason == "cache_lab_envelope_allowed",
        reason=reason,
        payload_capacity=int(signals.payload_capacity),
        overlap_factor=float(signals.overlap_factor),
        manager_us_per_issue=float(signals.manager_us_per_issue),
        bandwidth_gbps=float(signals.bandwidth_gbps),
        stress_fallback_active=bool(signals.stress_fallback_active),
        ready_time_allow_full_fetch=signals.ready_time_allow_full_fetch,
    )


def build_payload_cache_runtime_participation(
    *,
    manager_mode: str,
    issue_sources: Sequence[str],
    demand_on_consumer: bool,
    issued_fetch_count: int,
    used_fetch_count: int,
    demand_count: int,
    demand_hit_count: int,
    ready_late_miss_count: int,
    candidate_reason: str | None,
    queue_batch_size: int | None = None,
    queue_deadline_us: float | None = None,
) -> PayloadCacheRuntimeParticipation:
    """Build the payloadless runtime-participation object for online summaries."""

    mode = str(manager_mode)
    stage = (
        "online_ready_time_payload_cache_runtime_participation_dry_run"
        if mode == "ready_time"
        else "online_payload_cache_runtime_participation_dry_run"
    )
    reason = str(candidate_reason or "unknown")
    if mode != "ready_time":
        status = f"accounting_only_not_ready_time_manager:{mode}"
    elif reason == "candidate_requires_ready_time_gate":
        status = "ready_time_candidate_requires_lab_gate"
    else:
        status = f"accounting_only_{reason}"
    return PayloadCacheRuntimeParticipation(
        present=True,
        stage=stage,
        status=status,
        consumes_manager_snapshot=True,
        manager_mode=mode,
        issue_sources=tuple(str(source) for source in issue_sources),
        demand_on_consumer=bool(demand_on_consumer),
        issued_fetch_count=int(issued_fetch_count),
        used_fetch_count=int(used_fetch_count),
        demand_count=int(demand_count),
        demand_hit_count=int(demand_hit_count),
        ready_late_miss_count=int(ready_late_miss_count),
        queue_batch_size=(
            None if queue_batch_size is None else int(queue_batch_size)
        ),
        queue_deadline_us=(
            None if queue_deadline_us is None else float(queue_deadline_us)
        ),
        candidate_reason=reason,
    )


def runtime_plan_status_from_participation(status: str) -> str:
    if status == "ready_time_candidate_requires_lab_gate":
        return "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    return f"participation_not_full_fetch_candidate:{status}"


def build_payload_cache_runtime_plan(
    participation: PayloadCacheRuntimeParticipation,
) -> PayloadCacheRuntimePlan:
    """Build the payloadless runtime-plan dry-run object."""

    status = runtime_plan_status_from_participation(str(participation.status))
    return PayloadCacheRuntimePlan(
        present=bool(participation.present),
        stage="payload_cache_runtime_plan_lab_gate_dry_run",
        status=status,
        consumes_participation=True,
        participation_status=str(participation.status),
    )


def build_payload_cache_runtime_execution_dry_run(
    plan: PayloadCacheRuntimePlan,
) -> PayloadCacheRuntimeExecutionDryRun:
    """Build the payloadless execution dry-run object from a runtime plan."""

    plan_status = str(plan.status)
    return PayloadCacheRuntimeExecutionDryRun(
        present=True,
        stage="payload_cache_runtime_execution_lab_gate_dry_run",
        status=f"blocked_by_runtime_plan:{plan_status}",
        consumes_plan=True,
        plan_status=plan_status,
        decision="blocked",
        block_reason=plan_status,
        execution_mode="payloadless_lab_gate_dry_run",
    )


def _gate_reason(
    signals: CacheLabRuntimeSignals,
    config: CacheLabGateConfig,
) -> str:
    if signals.ready_time_allow_full_fetch is False:
        return "ready_time_payload_cache_gate_blocked"
    if (
        bool(config.require_stress_fallback_clear)
        and bool(signals.stress_fallback_active)
    ):
        return "stress_fallback_active"
    if int(signals.payload_capacity) < int(config.min_payload_capacity):
        return "payload_capacity_below_gate"
    if float(signals.overlap_factor) < float(config.min_overlap_factor):
        return "overlap_below_gate"
    if float(signals.manager_us_per_issue) > float(config.max_manager_us_per_issue):
        return "manager_overhead_above_gate"
    if float(signals.bandwidth_gbps) < float(config.min_bandwidth_gbps):
        return "bandwidth_below_calibrated_range"
    if (
        config.max_bandwidth_gbps is not None
        and float(signals.bandwidth_gbps) > float(config.max_bandwidth_gbps)
    ):
        return "bandwidth_above_calibrated_range"
    return "cache_lab_envelope_allowed"
