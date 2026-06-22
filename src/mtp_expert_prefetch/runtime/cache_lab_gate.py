from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Sequence

from mtp_expert_prefetch.runtime.cache_manager import (
    PayloadCacheRuntimeAdapterAccountingDryRun,
    PayloadCacheRuntimeAdapterPayloadlessLive,
    PayloadCacheRuntimeAdapterShell,
    ReadyTimeExpertCacheManager,
)


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


@dataclass(frozen=True)
class PayloadCacheQueueBudgetRuntimeEnvelope:
    """Payloadless queue-budget runtime envelope before live full-fetch.

    This object records that the token-index issue stream has a model-passing
    queue-budget cell under the lab gate.  It is intentionally not an execution
    permit: payload movement, ready credit, kernel argument handoff, and TPOT
    measurement remain disabled until a separate live payload/cache-manager
    stage provides strict evidence.
    """

    present: bool
    stage: str
    status: str
    consumes_queue_budget_sweep: bool
    event_timing_mode: str
    cell_count: int
    first_model_passing_capacity: int
    first_model_passing_issue_lead_tokens: int
    first_model_passing_queue_deadline_us: float
    first_model_passing_lookahead_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    execution_mode: str = "payloadless_queue_budget_lab_gate"
    payload_bytes: int = 0
    payload_transfer_enabled: bool = False
    payload_deref_allowed: bool = False
    full_fetch_allowed: bool = False
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("queue-budget runtime envelope must be present")
        if self.stage != "payload_cache_queue_budget_runtime_envelope_lab_gate":
            raise ValueError("queue-budget runtime envelope stage mismatch")
        if self.status != "model_queue_budget_satisfied_runtime_disabled":
            raise ValueError("queue-budget runtime envelope status mismatch")
        if self.consumes_queue_budget_sweep is not True:
            raise ValueError("queue-budget runtime envelope must consume sweep")
        if self.execution_mode != "payloadless_queue_budget_lab_gate":
            raise ValueError("queue-budget runtime envelope mode mismatch")
        if self.event_timing_mode != "token_index":
            raise ValueError("queue-budget runtime envelope requires token_index timing")
        for field_name in (
            "cell_count",
            "first_model_passing_capacity",
            "first_model_passing_issue_lead_tokens",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
            "payload_bytes",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
        for field_name in (
            "cell_count",
            "first_model_passing_capacity",
            "first_model_passing_issue_lead_tokens",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "first_model_passing_queue_deadline_us",
            "first_model_passing_lookahead_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        if self.payload_bytes != 0:
            raise ValueError("queue-budget runtime envelope must be payloadless")
        for field_name in (
            "payload_transfer_enabled",
            "payload_deref_allowed",
            "full_fetch_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLivePayloadStagePreflight:
    """Blocked preflight for the future live payload/cache-manager stage.

    This is the contract immediately after the queue-budget runtime envelope.
    It proves that the next stage has consumed the envelope, but it keeps live
    payload transfer and all execution side effects disabled until a separate
    payload/cache-manager implementation has strict evidence.
    """

    present: bool
    stage: str
    status: str
    consumes_queue_budget_runtime_envelope: bool
    queue_budget_envelope_status: str
    queue_budget_capacity_entries: int
    queue_budget_issue_lead_tokens: int
    queue_budget_queue_deadline_us: float
    queue_budget_lookahead_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_payload_runtime_disabled"
    execution_mode: str = "payloadless_live_payload_stage_preflight"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("live payload stage preflight must be present")
        if self.stage != "payload_cache_live_payload_stage_preflight":
            raise ValueError("live payload stage preflight stage mismatch")
        if self.consumes_queue_budget_runtime_envelope is not True:
            raise ValueError("live payload stage must consume queue-budget envelope")
        if (
            not isinstance(self.queue_budget_envelope_status, str)
            or not self.queue_budget_envelope_status
        ):
            raise TypeError("queue_budget_envelope_status must be a nonempty string")
        expected_status = (
            "blocked_by_queue_budget_runtime_envelope:"
            f"{self.queue_budget_envelope_status}"
        )
        if self.status != expected_status:
            raise ValueError("live payload stage status mismatch")
        if self.decision != "blocked":
            raise ValueError("live payload stage decision must stay blocked")
        if self.block_reason != "live_payload_runtime_disabled":
            raise ValueError("live payload stage block reason mismatch")
        if self.execution_mode != "payloadless_live_payload_stage_preflight":
            raise ValueError("live payload stage execution mode mismatch")
        for field_name in (
            "queue_budget_capacity_entries",
            "queue_budget_issue_lead_tokens",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in ("queue_budget_queue_deadline_us", "queue_budget_lookahead_us"):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLivePayloadRuntimeDisabledCanary:
    """Blocked canary for the future live payload runtime implementation.

    This contract sits after ``PayloadCacheLivePayloadStagePreflight``.  It is
    the last payloadless object before a real cache-manager runtime can be
    implemented.  It proves that the runtime entry point sees the live-stage
    preflight, but it still forbids payload dereference, ready credit, kernel
    argument handoff, WNA16 argument compatibility claims, and TPOT claims.
    """

    present: bool
    stage: str
    status: str
    consumes_live_payload_stage_preflight: bool
    live_payload_stage_status: str
    queue_budget_capacity_entries: int
    queue_budget_issue_lead_tokens: int
    queue_budget_queue_deadline_us: float
    queue_budget_lookahead_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_payload_runtime_disabled"
    execution_mode: str = "payloadless_live_payload_runtime_disabled_canary"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("live payload runtime canary must be present")
        if self.stage != "payload_cache_live_payload_runtime_disabled_canary":
            raise ValueError("live payload runtime canary stage mismatch")
        if self.consumes_live_payload_stage_preflight is not True:
            raise ValueError("live payload runtime canary must consume live-stage preflight")
        if (
            not isinstance(self.live_payload_stage_status, str)
            or not self.live_payload_stage_status
        ):
            raise TypeError("live_payload_stage_status must be a nonempty string")
        expected_status = f"blocked_by_live_payload_stage:{self.live_payload_stage_status}"
        if self.status != expected_status:
            raise ValueError("live payload runtime canary status mismatch")
        if self.decision != "blocked":
            raise ValueError("live payload runtime canary decision must stay blocked")
        if self.block_reason != "live_payload_runtime_disabled":
            raise ValueError("live payload runtime canary block reason mismatch")
        if self.execution_mode != "payloadless_live_payload_runtime_disabled_canary":
            raise ValueError("live payload runtime canary execution mode mismatch")
        for field_name in (
            "queue_budget_capacity_entries",
            "queue_budget_issue_lead_tokens",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in ("queue_budget_queue_deadline_us", "queue_budget_lookahead_us"):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheManagerImplementationArtifact:
    """Concrete payload/cache-manager implementation artifact, still disabled.

    This is the first object after the disabled live-runtime canary that names
    an actual runtime primitive and its queue-budget envelope.  It is not a
    live payload runtime permit: the implementation remains default-disabled
    and cannot dereference payload, grant ready credit, pass kernel args, or
    claim endpoint latency.
    """

    present: bool
    stage: str
    status: str
    consumes_live_payload_runtime_canary: bool
    live_payload_runtime_status: str
    manager_backend: str
    manager_contract: str
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "implementation_artifact_default_disabled"
    execution_mode: str = "payload_cache_manager_implementation_artifact_disabled"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("payload cache manager artifact must be present")
        if self.stage != "payload_cache_manager_implementation_artifact":
            raise ValueError("payload cache manager artifact stage mismatch")
        if self.consumes_live_payload_runtime_canary is not True:
            raise ValueError("payload cache manager artifact must consume runtime canary")
        if (
            not isinstance(self.live_payload_runtime_status, str)
            or not self.live_payload_runtime_status
        ):
            raise TypeError("live_payload_runtime_status must be a nonempty string")
        expected_status = f"blocked_by_live_payload_runtime:{self.live_payload_runtime_status}"
        if self.status != expected_status:
            raise ValueError("payload cache manager artifact status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("payload cache manager backend mismatch")
        if self.manager_contract != "event_driven_queue_budget_cache_manager_v1":
            raise ValueError("payload cache manager contract mismatch")
        if self.decision != "blocked":
            raise ValueError("payload cache manager artifact decision must stay blocked")
        if self.block_reason != "implementation_artifact_default_disabled":
            raise ValueError("payload cache manager artifact block reason mismatch")
        if self.execution_mode != "payload_cache_manager_implementation_artifact_disabled":
            raise ValueError("payload cache manager artifact execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in ("queue_deadline_us", "lookahead_us"):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheManagerRuntimeSkeleton:
    """Default-disabled skeleton for the future payload/cache-manager runtime.

    The skeleton consumes the concrete manager implementation artifact and
    names the issue/demand accounting contract that a future runtime will use.
    It is intentionally not a live manager instance: no payload is
    dereferenced, no ready credit is granted, no kernel arguments are changed,
    and no endpoint timing claim is made.
    """

    present: bool
    stage: str
    status: str
    consumes_manager_implementation_artifact: bool
    manager_artifact_status: str
    manager_backend: str
    manager_contract: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    runtime_instantiated: bool = False
    decision: str = "blocked"
    block_reason: str = "runtime_skeleton_default_disabled"
    execution_mode: str = "payload_cache_manager_runtime_skeleton_disabled"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("payload cache runtime skeleton must be present")
        if self.stage != "payload_cache_manager_runtime_skeleton":
            raise ValueError("payload cache runtime skeleton stage mismatch")
        if self.consumes_manager_implementation_artifact is not True:
            raise ValueError("runtime skeleton must consume manager artifact")
        if (
            not isinstance(self.manager_artifact_status, str)
            or not self.manager_artifact_status
        ):
            raise TypeError("manager_artifact_status must be a nonempty string")
        expected_status = f"blocked_by_manager_artifact:{self.manager_artifact_status}"
        if self.status != expected_status:
            raise ValueError("payload cache runtime skeleton status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("payload cache runtime skeleton backend mismatch")
        if self.manager_contract != "event_driven_queue_budget_cache_manager_v1":
            raise ValueError("payload cache runtime skeleton manager contract mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("payload cache runtime skeleton runtime contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("payload cache runtime skeleton mode mismatch")
        if self.runtime_instantiated is not False:
            raise ValueError("runtime skeleton must not instantiate live runtime")
        if self.decision != "blocked":
            raise ValueError("runtime skeleton decision must stay blocked")
        if self.block_reason != "runtime_skeleton_default_disabled":
            raise ValueError("runtime skeleton block reason mismatch")
        if self.execution_mode != "payload_cache_manager_runtime_skeleton_disabled":
            raise ValueError("runtime skeleton execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in ("queue_deadline_us", "lookahead_us"):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheManagerRuntimeSnapshotArtifact:
    """Default-disabled ready-time manager snapshot behind the skeleton.

    This artifact is the first step that touches the real
    ``ReadyTimeExpertCacheManager`` state shape.  It snapshots an empty
    accounting manager to prove the future runtime state contract is available,
    but it still does not issue transfers, grant ready credit, dereference
    payload, mutate kernel arguments, or measure endpoint latency.
    """

    present: bool
    stage: str
    status: str
    consumes_runtime_skeleton: bool
    runtime_skeleton_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    snapshot_source: str
    accounting_snapshot_instantiated: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "runtime_snapshot_default_disabled"
    execution_mode: str = "payload_cache_manager_runtime_snapshot_disabled"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("payload cache runtime snapshot must be present")
        if self.stage != "payload_cache_manager_runtime_snapshot_artifact":
            raise ValueError("payload cache runtime snapshot stage mismatch")
        if self.consumes_runtime_skeleton is not True:
            raise ValueError("runtime snapshot must consume runtime skeleton")
        if (
            not isinstance(self.runtime_skeleton_status, str)
            or not self.runtime_skeleton_status
        ):
            raise TypeError("runtime_skeleton_status must be a nonempty string")
        expected_status = f"blocked_by_runtime_skeleton:{self.runtime_skeleton_status}"
        if self.status != expected_status:
            raise ValueError("payload cache runtime snapshot status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("payload cache runtime snapshot backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("payload cache runtime snapshot contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("payload cache runtime snapshot mode mismatch")
        if self.snapshot_source != "ReadyTimeExpertCacheManager.empty_snapshot":
            raise ValueError("payload cache runtime snapshot source mismatch")
        if self.accounting_snapshot_instantiated is not True:
            raise ValueError("accounting snapshot must be instantiated")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("runtime snapshot decision must stay blocked")
        if self.block_reason != "runtime_snapshot_default_disabled":
            raise ValueError("runtime snapshot block reason mismatch")
        if self.execution_mode != "payload_cache_manager_runtime_snapshot_disabled":
            raise ValueError("runtime snapshot execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheSnapshotBackedLiveRuntimePreflight:
    """Still-disabled live-runtime preflight backed by the manager snapshot."""

    present: bool
    stage: str
    status: str
    consumes_runtime_snapshot: bool
    runtime_snapshot_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    snapshot_source: str
    live_runtime_preflight_instantiated: bool
    accounting_snapshot_instantiated: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "snapshot_backed_live_runtime_preflight_disabled"
    execution_mode: str = "payload_cache_snapshot_backed_live_runtime_preflight_disabled"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("snapshot-backed live-runtime preflight must be present")
        if self.stage != "payload_cache_snapshot_backed_live_runtime_preflight":
            raise ValueError("snapshot-backed live-runtime preflight stage mismatch")
        if self.consumes_runtime_snapshot is not True:
            raise ValueError("live-runtime preflight must consume runtime snapshot")
        if (
            not isinstance(self.runtime_snapshot_status, str)
            or not self.runtime_snapshot_status
        ):
            raise TypeError("runtime_snapshot_status must be a nonempty string")
        expected_status = f"blocked_by_runtime_snapshot:{self.runtime_snapshot_status}"
        if self.status != expected_status:
            raise ValueError("snapshot-backed live-runtime preflight status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("snapshot-backed live-runtime preflight backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("snapshot-backed live-runtime preflight contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("snapshot-backed live-runtime preflight mode mismatch")
        if self.snapshot_source != "PayloadCacheManagerRuntimeSnapshotArtifact":
            raise ValueError("snapshot-backed live-runtime preflight source mismatch")
        if self.live_runtime_preflight_instantiated is not True:
            raise ValueError("live-runtime preflight object must be instantiated")
        if self.accounting_snapshot_instantiated is not True:
            raise ValueError("accounting snapshot must be instantiated")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("live-runtime preflight decision must stay blocked")
        if self.block_reason != "snapshot_backed_live_runtime_preflight_disabled":
            raise ValueError("live-runtime preflight block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_snapshot_backed_live_runtime_preflight_disabled"
        ):
            raise ValueError("live-runtime preflight execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary:
    """Blocked canary behind the snapshot-backed live-runtime preflight."""

    present: bool
    stage: str
    status: str
    consumes_live_runtime_preflight: bool
    live_runtime_preflight_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    live_runtime_canary_instantiated: bool
    live_runtime_preflight_instantiated: bool
    accounting_snapshot_instantiated: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "snapshot_backed_live_runtime_canary_disabled"
    execution_mode: str = "payload_cache_snapshot_backed_live_runtime_canary_disabled"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("snapshot-backed live-runtime canary must be present")
        if self.stage != "payload_cache_snapshot_backed_live_runtime_disabled_canary":
            raise ValueError("snapshot-backed live-runtime canary stage mismatch")
        if self.consumes_live_runtime_preflight is not True:
            raise ValueError("live-runtime canary must consume preflight")
        if (
            not isinstance(self.live_runtime_preflight_status, str)
            or not self.live_runtime_preflight_status
        ):
            raise TypeError("live_runtime_preflight_status must be a nonempty string")
        expected_status = (
            f"blocked_by_live_runtime_preflight:{self.live_runtime_preflight_status}"
        )
        if self.status != expected_status:
            raise ValueError("snapshot-backed live-runtime canary status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("snapshot-backed live-runtime canary backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("snapshot-backed live-runtime canary contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("snapshot-backed live-runtime canary mode mismatch")
        if self.live_runtime_canary_instantiated is not True:
            raise ValueError("live-runtime canary object must be instantiated")
        if self.live_runtime_preflight_instantiated is not True:
            raise ValueError("live-runtime preflight object must be instantiated")
        if self.accounting_snapshot_instantiated is not True:
            raise ValueError("accounting snapshot must be instantiated")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("live-runtime canary decision must stay blocked")
        if self.block_reason != "snapshot_backed_live_runtime_canary_disabled":
            raise ValueError("live-runtime canary block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_snapshot_backed_live_runtime_canary_disabled"
        ):
            raise ValueError("live-runtime canary execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeStateShapeCheck:
    """Blocked shape check for the future live payload cache runtime."""

    present: bool
    stage: str
    status: str
    consumes_live_runtime_canary: bool
    live_runtime_canary_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    state_shape_schema: str
    live_runtime_state_shape_checked: bool
    issue_queue_shape_checked: bool
    demand_state_shape_checked: bool
    resident_index_shape_checked: bool
    queue_timing_shape_checked: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_state_shape_only"
    execution_mode: str = "payload_cache_live_runtime_state_shape_check_disabled"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("live-runtime state-shape check must be present")
        if self.stage != "payload_cache_live_runtime_state_shape_check":
            raise ValueError("live-runtime state-shape check stage mismatch")
        if self.consumes_live_runtime_canary is not True:
            raise ValueError("state-shape check must consume live-runtime canary")
        if (
            not isinstance(self.live_runtime_canary_status, str)
            or not self.live_runtime_canary_status
        ):
            raise TypeError("live_runtime_canary_status must be a nonempty string")
        expected_status = f"blocked_by_live_runtime_canary:{self.live_runtime_canary_status}"
        if self.status != expected_status:
            raise ValueError("live-runtime state-shape status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("live-runtime state-shape backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("live-runtime state-shape contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("live-runtime state-shape mode mismatch")
        if self.state_shape_schema != "ready_time_issue_demand_state_shape_v1":
            raise ValueError("live-runtime state-shape schema mismatch")
        for field_name in (
            "live_runtime_state_shape_checked",
            "issue_queue_shape_checked",
            "demand_state_shape_checked",
            "resident_index_shape_checked",
            "queue_timing_shape_checked",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be checked")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("live-runtime state-shape decision must stay blocked")
        if self.block_reason != "live_runtime_state_shape_only":
            raise ValueError("live-runtime state-shape block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_state_shape_check_disabled"
        ):
            raise ValueError("live-runtime state-shape execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeObjectConstructionPreflight:
    """Blocked preflight for future typed live-runtime state containers."""

    present: bool
    stage: str
    status: str
    consumes_state_shape_check: bool
    state_shape_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    state_shape_schema: str
    object_construction_preflight_instantiated: bool
    typed_issue_queue_container_declared: bool
    typed_demand_state_container_declared: bool
    typed_resident_index_container_declared: bool
    typed_queue_timing_container_declared: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_object_construction_preflight_only"
    execution_mode: str = (
        "payload_cache_live_runtime_object_construction_preflight_disabled"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("live-runtime object preflight must be present")
        if self.stage != "payload_cache_live_runtime_object_construction_preflight":
            raise ValueError("live-runtime object preflight stage mismatch")
        if self.consumes_state_shape_check is not True:
            raise ValueError("object preflight must consume state-shape check")
        if not isinstance(self.state_shape_status, str) or not self.state_shape_status:
            raise TypeError("state_shape_status must be a nonempty string")
        expected_status = f"blocked_by_state_shape_check:{self.state_shape_status}"
        if self.status != expected_status:
            raise ValueError("live-runtime object preflight status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("live-runtime object preflight backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("live-runtime object preflight contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("live-runtime object preflight mode mismatch")
        if self.state_shape_schema != "ready_time_issue_demand_state_shape_v1":
            raise ValueError("live-runtime object preflight schema mismatch")
        for field_name in (
            "object_construction_preflight_instantiated",
            "typed_issue_queue_container_declared",
            "typed_demand_state_container_declared",
            "typed_resident_index_container_declared",
            "typed_queue_timing_container_declared",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be declared")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("live-runtime object preflight decision must stay blocked")
        if self.block_reason != "live_runtime_object_construction_preflight_only":
            raise ValueError("live-runtime object preflight block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_object_construction_preflight_disabled"
        ):
            raise ValueError("live-runtime object preflight execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeObjectAdapterPreflight:
    """Blocked preflight for future typed live-runtime object adapters."""

    present: bool
    stage: str
    status: str
    consumes_object_construction_preflight: bool
    object_preflight_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    state_shape_schema: str
    runtime_adapter_schema: str
    object_construction_preflight_instantiated: bool
    runtime_object_adapter_declared: bool
    issue_queue_adapter_bound: bool
    demand_state_adapter_bound: bool
    resident_index_adapter_bound: bool
    queue_timing_adapter_bound: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_object_adapter_preflight_only"
    execution_mode: str = "payload_cache_live_runtime_object_adapter_preflight_disabled"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("live-runtime object adapter preflight must be present")
        if self.stage != "payload_cache_live_runtime_object_adapter_preflight":
            raise ValueError("live-runtime object adapter preflight stage mismatch")
        if self.consumes_object_construction_preflight is not True:
            raise ValueError("object adapter must consume object-construction preflight")
        if (
            not isinstance(self.object_preflight_status, str)
            or not self.object_preflight_status
        ):
            raise TypeError("object_preflight_status must be a nonempty string")
        expected_status = (
            "blocked_by_object_construction_preflight:"
            f"{self.object_preflight_status}"
        )
        if self.status != expected_status:
            raise ValueError("live-runtime object adapter preflight status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("live-runtime object adapter backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("live-runtime object adapter contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("live-runtime object adapter mode mismatch")
        if self.state_shape_schema != "ready_time_issue_demand_state_shape_v1":
            raise ValueError("live-runtime object adapter state-shape schema mismatch")
        if self.runtime_adapter_schema != "ready_time_payload_cache_runtime_adapter_v1":
            raise ValueError("live-runtime object adapter schema mismatch")
        for field_name in (
            "object_construction_preflight_instantiated",
            "runtime_object_adapter_declared",
            "issue_queue_adapter_bound",
            "demand_state_adapter_bound",
            "resident_index_adapter_bound",
            "queue_timing_adapter_bound",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be declared")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("live-runtime object adapter decision must stay blocked")
        if self.block_reason != "live_runtime_object_adapter_preflight_only":
            raise ValueError("live-runtime object adapter block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_object_adapter_preflight_disabled"
        ):
            raise ValueError("live-runtime object adapter execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterMaterializationPreflight:
    """Blocked preflight for future live-runtime adapter materialization checks."""

    present: bool
    stage: str
    status: str
    consumes_object_adapter_preflight: bool
    object_adapter_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    state_shape_schema: str
    runtime_adapter_schema: str
    object_construction_preflight_instantiated: bool
    adapter_materialization_preflight_instantiated: bool
    runtime_object_adapter_declared: bool
    issue_queue_materialization_checked: bool
    demand_state_materialization_checked: bool
    resident_index_materialization_checked: bool
    queue_timing_materialization_checked: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_materialization_preflight_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_materialization_preflight_disabled"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("adapter materialization preflight must be present")
        if self.stage != "payload_cache_live_runtime_adapter_materialization_preflight":
            raise ValueError("adapter materialization preflight stage mismatch")
        if self.consumes_object_adapter_preflight is not True:
            raise ValueError("materialization preflight must consume adapter preflight")
        if not isinstance(self.object_adapter_status, str) or not self.object_adapter_status:
            raise TypeError("object_adapter_status must be a nonempty string")
        expected_status = (
            "blocked_by_object_adapter_preflight:"
            f"{self.object_adapter_status}"
        )
        if self.status != expected_status:
            raise ValueError("adapter materialization preflight status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("adapter materialization backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("adapter materialization contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("adapter materialization mode mismatch")
        if self.state_shape_schema != "ready_time_issue_demand_state_shape_v1":
            raise ValueError("adapter materialization state-shape schema mismatch")
        if self.runtime_adapter_schema != "ready_time_payload_cache_runtime_adapter_v1":
            raise ValueError("adapter materialization schema mismatch")
        for field_name in (
            "object_construction_preflight_instantiated",
            "adapter_materialization_preflight_instantiated",
            "runtime_object_adapter_declared",
            "issue_queue_materialization_checked",
            "demand_state_materialization_checked",
            "resident_index_materialization_checked",
            "queue_timing_materialization_checked",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be checked")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("adapter materialization decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_materialization_preflight_only":
            raise ValueError("adapter materialization block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_materialization_preflight_disabled"
        ):
            raise ValueError("adapter materialization execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterStateObjectPreflight:
    """Blocked preflight for the future runtime adapter state object."""

    present: bool
    stage: str
    status: str
    consumes_adapter_materialization_preflight: bool
    adapter_materialization_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    state_shape_schema: str
    runtime_adapter_schema: str
    adapter_state_object_schema: str
    adapter_materialization_preflight_instantiated: bool
    adapter_state_object_declared: bool
    issue_queue_state_object_declared: bool
    demand_state_object_declared: bool
    resident_index_state_object_declared: bool
    queue_timing_state_object_declared: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_state_object_preflight_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_state_object_preflight_disabled"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("adapter state-object preflight must be present")
        if self.stage != "payload_cache_live_runtime_adapter_state_object_preflight":
            raise ValueError("adapter state-object preflight stage mismatch")
        if self.consumes_adapter_materialization_preflight is not True:
            raise ValueError("state-object preflight must consume materialization")
        if (
            not isinstance(self.adapter_materialization_status, str)
            or not self.adapter_materialization_status
        ):
            raise TypeError("adapter_materialization_status must be a nonempty string")
        expected_status = (
            "blocked_by_adapter_materialization_preflight:"
            f"{self.adapter_materialization_status}"
        )
        if self.status != expected_status:
            raise ValueError("adapter state-object preflight status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("adapter state-object backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("adapter state-object contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("adapter state-object mode mismatch")
        if self.state_shape_schema != "ready_time_issue_demand_state_shape_v1":
            raise ValueError("adapter state-object state-shape schema mismatch")
        if self.runtime_adapter_schema != "ready_time_payload_cache_runtime_adapter_v1":
            raise ValueError("adapter state-object runtime adapter schema mismatch")
        if self.adapter_state_object_schema != "ready_time_payload_cache_adapter_state_v1":
            raise ValueError("adapter state-object schema mismatch")
        for field_name in (
            "adapter_materialization_preflight_instantiated",
            "adapter_state_object_declared",
            "issue_queue_state_object_declared",
            "demand_state_object_declared",
            "resident_index_state_object_declared",
            "queue_timing_state_object_declared",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be declared")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("adapter state-object decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_state_object_preflight_only":
            raise ValueError("adapter state-object block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_state_object_preflight_disabled"
        ):
            raise ValueError("adapter state-object execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterStateValidationPreflight:
    """Blocked preflight for validating the future adapter state object."""

    present: bool
    stage: str
    status: str
    consumes_adapter_state_object_preflight: bool
    adapter_state_object_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    state_shape_schema: str
    runtime_adapter_schema: str
    adapter_state_object_schema: str
    adapter_state_validation_schema: str
    adapter_state_object_declared: bool
    adapter_state_validation_preflight_instantiated: bool
    issue_queue_state_object_validated: bool
    demand_state_object_validated: bool
    resident_index_state_object_validated: bool
    queue_timing_state_object_validated: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_state_validation_preflight_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_state_validation_preflight_disabled"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("adapter state-validation preflight must be present")
        if self.stage != "payload_cache_live_runtime_adapter_state_validation_preflight":
            raise ValueError("adapter state-validation preflight stage mismatch")
        if self.consumes_adapter_state_object_preflight is not True:
            raise ValueError("state-validation preflight must consume state object")
        if (
            not isinstance(self.adapter_state_object_status, str)
            or not self.adapter_state_object_status
        ):
            raise TypeError("adapter_state_object_status must be a nonempty string")
        expected_status = (
            "blocked_by_adapter_state_object_preflight:"
            f"{self.adapter_state_object_status}"
        )
        if self.status != expected_status:
            raise ValueError("adapter state-validation preflight status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("adapter state-validation backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("adapter state-validation contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("adapter state-validation mode mismatch")
        if self.state_shape_schema != "ready_time_issue_demand_state_shape_v1":
            raise ValueError("adapter state-validation state-shape schema mismatch")
        if self.runtime_adapter_schema != "ready_time_payload_cache_runtime_adapter_v1":
            raise ValueError("adapter state-validation runtime adapter schema mismatch")
        if self.adapter_state_object_schema != "ready_time_payload_cache_adapter_state_v1":
            raise ValueError("adapter state-validation object schema mismatch")
        if (
            self.adapter_state_validation_schema
            != "ready_time_payload_cache_adapter_state_validation_v1"
        ):
            raise ValueError("adapter state-validation schema mismatch")
        for field_name in (
            "adapter_state_object_declared",
            "adapter_state_validation_preflight_instantiated",
            "issue_queue_state_object_validated",
            "demand_state_object_validated",
            "resident_index_state_object_validated",
            "queue_timing_state_object_validated",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be validated")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("adapter state-validation decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_state_validation_preflight_only":
            raise ValueError("adapter state-validation block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_state_validation_preflight_disabled"
        ):
            raise ValueError("adapter state-validation execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterStateValidationArtifact:
    """Blocked artifact for the validated future adapter state contract."""

    present: bool
    stage: str
    status: str
    consumes_adapter_state_validation_preflight: bool
    adapter_state_validation_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    state_shape_schema: str
    runtime_adapter_schema: str
    adapter_state_object_schema: str
    adapter_state_validation_schema: str
    validated_state_artifact_schema: str
    adapter_state_validation_preflight_instantiated: bool
    adapter_state_validation_artifact_instantiated: bool
    issue_queue_state_object_ready_for_runtime_adapter: bool
    demand_state_object_ready_for_runtime_adapter: bool
    resident_index_state_object_ready_for_runtime_adapter: bool
    queue_timing_state_object_ready_for_runtime_adapter: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_state_validation_artifact_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_state_validation_artifact_disabled"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("adapter state-validation artifact must be present")
        if self.stage != "payload_cache_live_runtime_adapter_state_validation_artifact":
            raise ValueError("adapter state-validation artifact stage mismatch")
        if self.consumes_adapter_state_validation_preflight is not True:
            raise ValueError("state-validation artifact must consume preflight")
        if (
            not isinstance(self.adapter_state_validation_status, str)
            or not self.adapter_state_validation_status
        ):
            raise TypeError("adapter_state_validation_status must be nonempty")
        expected_status = (
            "blocked_by_adapter_state_validation_preflight:"
            f"{self.adapter_state_validation_status}"
        )
        if self.status != expected_status:
            raise ValueError("adapter state-validation artifact status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("adapter state-validation artifact backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("adapter state-validation artifact contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("adapter state-validation artifact mode mismatch")
        if self.state_shape_schema != "ready_time_issue_demand_state_shape_v1":
            raise ValueError("adapter state-validation artifact state schema mismatch")
        if self.runtime_adapter_schema != "ready_time_payload_cache_runtime_adapter_v1":
            raise ValueError("adapter state-validation artifact adapter schema mismatch")
        if self.adapter_state_object_schema != "ready_time_payload_cache_adapter_state_v1":
            raise ValueError("adapter state-validation artifact object schema mismatch")
        if (
            self.adapter_state_validation_schema
            != "ready_time_payload_cache_adapter_state_validation_v1"
        ):
            raise ValueError("adapter state-validation artifact validation schema mismatch")
        if (
            self.validated_state_artifact_schema
            != "ready_time_payload_cache_validated_adapter_state_artifact_v1"
        ):
            raise ValueError("validated_state_artifact_schema mismatch")
        for field_name in (
            "adapter_state_validation_preflight_instantiated",
            "adapter_state_validation_artifact_instantiated",
            "issue_queue_state_object_ready_for_runtime_adapter",
            "demand_state_object_ready_for_runtime_adapter",
            "resident_index_state_object_ready_for_runtime_adapter",
            "queue_timing_state_object_ready_for_runtime_adapter",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be ready")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("adapter state-validation artifact decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_state_validation_artifact_only":
            raise ValueError("adapter state-validation artifact block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_state_validation_artifact_disabled"
        ):
            raise ValueError("adapter state-validation artifact execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterInstantiationCanary:
    """Blocked canary for resolving the future live-runtime adapter entry."""

    present: bool
    stage: str
    status: str
    consumes_state_validation_artifact: bool
    state_validation_artifact_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    validated_state_artifact_schema: str
    runtime_adapter_instantiation_schema: str
    adapter_factory_declared: bool
    adapter_constructor_resolved: bool
    adapter_instance_created: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_instantiation_canary_only"
    execution_mode: str = "payload_cache_live_runtime_adapter_instantiation_canary_disabled"
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("adapter instantiation canary must be present")
        if self.stage != "payload_cache_live_runtime_adapter_instantiation_canary":
            raise ValueError("adapter instantiation canary stage mismatch")
        if self.consumes_state_validation_artifact is not True:
            raise ValueError("adapter instantiation canary must consume artifact")
        if (
            not isinstance(self.state_validation_artifact_status, str)
            or not self.state_validation_artifact_status
        ):
            raise TypeError("state_validation_artifact_status must be nonempty")
        expected_status = (
            "blocked_by_state_validation_artifact:"
            f"{self.state_validation_artifact_status}"
        )
        if self.status != expected_status:
            raise ValueError("adapter instantiation canary status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("adapter instantiation canary backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("adapter instantiation canary contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("adapter instantiation canary mode mismatch")
        if (
            self.validated_state_artifact_schema
            != "ready_time_payload_cache_validated_adapter_state_artifact_v1"
        ):
            raise ValueError("validated_state_artifact_schema mismatch")
        if (
            self.runtime_adapter_instantiation_schema
            != "ready_time_payload_cache_runtime_adapter_instantiation_v1"
        ):
            raise ValueError("runtime_adapter_instantiation_schema mismatch")
        if self.adapter_factory_declared is not True:
            raise ValueError("adapter_factory_declared must be true")
        if self.adapter_constructor_resolved is not True:
            raise ValueError("adapter_constructor_resolved must be true")
        if self.adapter_instance_created is not False:
            raise ValueError("adapter instance must not be created")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("adapter instantiation canary decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_instantiation_canary_only":
            raise ValueError("adapter instantiation canary block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_instantiation_canary_disabled"
        ):
            raise ValueError("adapter instantiation canary execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight:
    """Blocked preflight for binding future adapter constructor inputs."""

    present: bool
    stage: str
    status: str
    consumes_instantiation_canary: bool
    instantiation_canary_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    runtime_adapter_instantiation_schema: str
    constructor_binding_schema: str
    adapter_factory_declared: bool
    adapter_constructor_resolved: bool
    constructor_inputs_bound: bool
    binds_validated_state_artifact: bool
    binds_queue_budget_parameters: bool
    binds_shifted_issue_accounting: bool
    adapter_instance_created: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_constructor_binding_preflight_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_constructor_binding_preflight_disabled"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("adapter constructor-binding preflight must be present")
        if self.stage != "payload_cache_live_runtime_adapter_constructor_binding_preflight":
            raise ValueError("adapter constructor-binding preflight stage mismatch")
        if self.consumes_instantiation_canary is not True:
            raise ValueError("constructor-binding preflight must consume canary")
        if (
            not isinstance(self.instantiation_canary_status, str)
            or not self.instantiation_canary_status
        ):
            raise TypeError("instantiation_canary_status must be nonempty")
        expected_status = (
            "blocked_by_instantiation_canary:"
            f"{self.instantiation_canary_status}"
        )
        if self.status != expected_status:
            raise ValueError("adapter constructor-binding preflight status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("adapter constructor-binding backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("adapter constructor-binding contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("adapter constructor-binding mode mismatch")
        if (
            self.runtime_adapter_instantiation_schema
            != "ready_time_payload_cache_runtime_adapter_instantiation_v1"
        ):
            raise ValueError("runtime_adapter_instantiation_schema mismatch")
        if (
            self.constructor_binding_schema
            != "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
        ):
            raise ValueError("constructor_binding_schema mismatch")
        for field_name in (
            "adapter_factory_declared",
            "adapter_constructor_resolved",
            "constructor_inputs_bound",
            "binds_validated_state_artifact",
            "binds_queue_budget_parameters",
            "binds_shifted_issue_accounting",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be true")
        if self.adapter_instance_created is not False:
            raise ValueError("adapter instance must not be created")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("adapter constructor-binding decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_constructor_binding_preflight_only":
            raise ValueError("adapter constructor-binding block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_constructor_binding_preflight_disabled"
        ):
            raise ValueError("adapter constructor-binding execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan:
    """Blocked plan for future adapter instance construction.

    This is deliberately not an adapter construction side effect.  It records
    that the constructor inputs are sealed and a future construction call can
    be planned, while still preventing an adapter instance, live runtime,
    payload movement, ready credit, and kernel argument handoff.
    """

    present: bool
    stage: str
    status: str
    consumes_constructor_binding_preflight: bool
    constructor_binding_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    constructor_binding_schema: str
    instance_construction_plan_schema: str
    constructor_inputs_bound: bool
    construction_plan_sealed: bool
    adapter_constructor_call_prepared: bool
    adapter_instance_construction_planned: bool
    adapter_instance_created: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_instance_construction_plan_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_instance_construction_plan_disabled"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("adapter instance-construction plan must be present")
        if self.stage != "payload_cache_live_runtime_adapter_instance_construction_plan":
            raise ValueError("adapter instance-construction plan stage mismatch")
        if self.consumes_constructor_binding_preflight is not True:
            raise ValueError("instance-construction plan must consume binding")
        if (
            not isinstance(self.constructor_binding_status, str)
            or not self.constructor_binding_status
        ):
            raise TypeError("constructor_binding_status must be nonempty")
        expected_status = (
            "blocked_by_constructor_binding_preflight:"
            f"{self.constructor_binding_status}"
        )
        if self.status != expected_status:
            raise ValueError("adapter instance-construction plan status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("adapter instance-construction backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("adapter instance-construction contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("adapter instance-construction mode mismatch")
        if (
            self.constructor_binding_schema
            != "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
        ):
            raise ValueError("constructor_binding_schema mismatch")
        if (
            self.instance_construction_plan_schema
            != "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
        ):
            raise ValueError("instance_construction_plan_schema mismatch")
        for field_name in (
            "constructor_inputs_bound",
            "construction_plan_sealed",
            "adapter_constructor_call_prepared",
            "adapter_instance_construction_planned",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be true")
        if self.adapter_instance_created is not False:
            raise ValueError("adapter instance must not be created")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("adapter instance-construction decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_instance_construction_plan_only":
            raise ValueError("adapter instance-construction block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_instance_construction_plan_disabled"
        ):
            raise ValueError("adapter instance-construction execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterObjectShellEvidence:
    """Evidence that a disabled adapter object shell can be constructed.

    The shell owns a private empty ``ReadyTimeExpertCacheManager`` and exposes
    only a no-side-effect snapshot.  This is still not live runtime
    instantiation, does not issue/demand payloads, and cannot mutate kernel
    launch arguments.
    """

    present: bool
    stage: str
    status: str
    consumes_instance_construction_plan: bool
    instance_construction_plan_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    instance_construction_plan_schema: str
    adapter_object_shell_created: bool
    disabled_adapter_shell_snapshot_created: bool
    shell_enabled: bool
    adapter_instance_created: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_object_shell_evidence_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_object_shell_evidence_disabled"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("adapter object-shell evidence must be present")
        if self.stage != "payload_cache_live_runtime_adapter_object_shell_evidence":
            raise ValueError("adapter object-shell evidence stage mismatch")
        if self.consumes_instance_construction_plan is not True:
            raise ValueError("adapter object shell must consume construction plan")
        if (
            not isinstance(self.instance_construction_plan_status, str)
            or not self.instance_construction_plan_status
        ):
            raise TypeError("instance_construction_plan_status must be nonempty")
        expected_status = (
            "blocked_by_instance_construction_plan:"
            f"{self.instance_construction_plan_status}"
        )
        if self.status != expected_status:
            raise ValueError("adapter object-shell evidence status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("adapter object-shell backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("adapter object-shell contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("adapter object-shell mode mismatch")
        if (
            self.instance_construction_plan_schema
            != "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
        ):
            raise ValueError("instance_construction_plan_schema mismatch")
        if self.adapter_object_shell_created is not True:
            raise ValueError("adapter_object_shell_created must be true")
        if self.disabled_adapter_shell_snapshot_created is not True:
            raise ValueError("disabled_adapter_shell_snapshot_created must be true")
        if self.shell_enabled is not False:
            raise ValueError("adapter object shell must remain disabled")
        if self.adapter_instance_created is not False:
            raise ValueError("adapter instance must not be created")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("adapter object-shell decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_object_shell_evidence_only":
            raise ValueError("adapter object-shell block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_object_shell_evidence_disabled"
        ):
            raise ValueError("adapter object-shell execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterOperationRejectionCanary:
    """Evidence that a disabled adapter shell rejects runtime operations.

    This is the first gate that actually calls the object-shell runtime
    methods.  The shell must reject both issue and demand paths while keeping
    the enclosed manager empty.  It is still not live runtime instantiation and
    cannot transfer payloads, grant ready credit, or mutate kernel arguments.
    """

    present: bool
    stage: str
    status: str
    consumes_object_shell_evidence: bool
    object_shell_evidence_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    operation_rejection_schema: str
    adapter_object_shell_created: bool
    operation_rejection_canary_ran: bool
    issue_prefetch_rejected: bool
    demand_rejected: bool
    shell_enabled: bool
    adapter_instance_created: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_operation_rejection_canary_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_operation_rejection_canary_disabled"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("operation-rejection canary must be present")
        if self.stage != "payload_cache_live_runtime_adapter_operation_rejection_canary":
            raise ValueError("operation-rejection canary stage mismatch")
        if self.consumes_object_shell_evidence is not True:
            raise ValueError("operation-rejection canary must consume object shell")
        if (
            not isinstance(self.object_shell_evidence_status, str)
            or not self.object_shell_evidence_status
        ):
            raise TypeError("object_shell_evidence_status must be nonempty")
        expected_status = (
            "blocked_by_object_shell_evidence:"
            f"{self.object_shell_evidence_status}"
        )
        if self.status != expected_status:
            raise ValueError("operation-rejection canary status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("operation-rejection canary backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("operation-rejection canary contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("operation-rejection canary mode mismatch")
        if (
            self.operation_rejection_schema
            != "ready_time_payload_cache_runtime_adapter_operation_rejection_canary_v1"
        ):
            raise ValueError("operation_rejection_schema mismatch")
        for field_name in (
            "adapter_object_shell_created",
            "operation_rejection_canary_ran",
            "issue_prefetch_rejected",
            "demand_rejected",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be true")
        if self.shell_enabled is not False:
            raise ValueError("adapter operation shell must remain disabled")
        if self.adapter_instance_created is not False:
            raise ValueError("adapter instance must not be created")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("operation-rejection canary decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_operation_rejection_canary_only":
            raise ValueError("operation-rejection canary block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_operation_rejection_canary_disabled"
        ):
            raise ValueError("operation-rejection canary execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "resident_count",
            "issued_fetch_count",
            "used_fetch_count",
            "unused_fetch_count",
            "demand_count",
            "demand_hit_count",
            "demand_miss_count",
            "evicted_before_use_count",
            "ready_late_miss_count",
            "late_completion_unused_count",
            "queue_batch_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary:
    """Evidence that the future adapter API can drive manager accounting.

    This canary creates a payloadless accounting dry-run adapter and executes a
    deterministic issue/demand sequence against its private manager.  It is the
    first adapter gate with nonzero manager counters, but still forbids payload
    transfer, ready credit, kernel argument mutation, current WNA16 args, and
    endpoint timing claims.
    """

    present: bool
    stage: str
    status: str
    consumes_operation_rejection_canary: bool
    operation_rejection_canary_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    accounting_dry_run_schema: str
    accounting_dry_run_adapter_created: bool
    accounting_dry_run_operations_ran: bool
    accounting_dry_run_enabled: bool
    issue_prefetch_accepted: bool
    duplicate_issue_suppressed: bool
    demand_hit: bool
    live_adapter_instance_created: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_accounting_dry_run_canary_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_accounting_dry_run_canary_payloadless"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("accounting dry-run canary must be present")
        if self.stage != "payload_cache_live_runtime_adapter_accounting_dry_run_canary":
            raise ValueError("accounting dry-run canary stage mismatch")
        if self.consumes_operation_rejection_canary is not True:
            raise ValueError("accounting dry-run must consume rejection canary")
        if (
            not isinstance(self.operation_rejection_canary_status, str)
            or not self.operation_rejection_canary_status
        ):
            raise TypeError("operation_rejection_canary_status must be nonempty")
        expected_status = (
            "blocked_by_operation_rejection_canary:"
            f"{self.operation_rejection_canary_status}"
        )
        if self.status != expected_status:
            raise ValueError("accounting dry-run canary status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("accounting dry-run canary backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("accounting dry-run canary contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("accounting dry-run canary mode mismatch")
        if (
            self.accounting_dry_run_schema
            != "ready_time_payload_cache_runtime_adapter_accounting_dry_run_canary_v1"
        ):
            raise ValueError("accounting_dry_run_schema mismatch")
        for field_name in (
            "accounting_dry_run_adapter_created",
            "accounting_dry_run_operations_ran",
            "accounting_dry_run_enabled",
            "issue_prefetch_accepted",
            "duplicate_issue_suppressed",
            "demand_hit",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be true")
        if self.live_adapter_instance_created is not False:
            raise ValueError("live adapter instance must not be created")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("accounting dry-run canary decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_accounting_dry_run_canary_only":
            raise ValueError("accounting dry-run canary block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_accounting_dry_run_canary_payloadless"
        ):
            raise ValueError("accounting dry-run canary execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        expected_counts = {
            "resident_count": 1,
            "issued_fetch_count": 1,
            "used_fetch_count": 1,
            "unused_fetch_count": 0,
            "demand_count": 1,
            "demand_hit_count": 1,
            "demand_miss_count": 0,
            "evicted_before_use_count": 0,
            "ready_late_miss_count": 0,
            "late_completion_unused_count": 0,
            "queue_batch_count": 1,
        }
        for field_name, expected in expected_counts.items():
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != expected:
                raise ValueError(f"{field_name} mismatch")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary:
    """Payloadless adapter canary covering both a ready hit and a demand miss."""

    present: bool
    stage: str
    status: str
    consumes_accounting_dry_run_canary: bool
    accounting_dry_run_canary_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    mixed_outcome_schema: str
    mixed_outcome_adapter_created: bool
    mixed_outcome_operations_ran: bool
    accounting_dry_run_enabled: bool
    issue_prefetch_accepted: bool
    duplicate_issue_suppressed: bool
    prefetched_demand_hit: bool
    unprefetched_demand_hit: bool
    unprefetched_demand_missed: bool
    live_adapter_instance_created: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_mixed_outcome_dry_run_canary_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary_payloadless"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("mixed-outcome dry-run canary must be present")
        if self.stage != "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary":
            raise ValueError("mixed-outcome dry-run canary stage mismatch")
        if self.consumes_accounting_dry_run_canary is not True:
            raise ValueError("mixed-outcome dry-run must consume accounting canary")
        if (
            not isinstance(self.accounting_dry_run_canary_status, str)
            or not self.accounting_dry_run_canary_status
        ):
            raise TypeError("accounting_dry_run_canary_status must be nonempty")
        expected_status = (
            "blocked_by_accounting_dry_run_canary:"
            f"{self.accounting_dry_run_canary_status}"
        )
        if self.status != expected_status:
            raise ValueError("mixed-outcome dry-run canary status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("mixed-outcome dry-run canary backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("mixed-outcome dry-run canary contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("mixed-outcome dry-run canary mode mismatch")
        if (
            self.mixed_outcome_schema
            != "ready_time_payload_cache_runtime_adapter_mixed_outcome_dry_run_canary_v1"
        ):
            raise ValueError("mixed_outcome_schema mismatch")
        for field_name in (
            "mixed_outcome_adapter_created",
            "mixed_outcome_operations_ran",
            "accounting_dry_run_enabled",
            "issue_prefetch_accepted",
            "duplicate_issue_suppressed",
            "prefetched_demand_hit",
            "unprefetched_demand_missed",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be true")
        if self.unprefetched_demand_hit is not False:
            raise ValueError("unprefetched demand must miss")
        if self.live_adapter_instance_created is not False:
            raise ValueError("live adapter instance must not be created")
        if self.live_runtime_instantiated is not False:
            raise ValueError("live runtime must not be instantiated")
        if self.decision != "blocked":
            raise ValueError("mixed-outcome dry-run canary decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_mixed_outcome_dry_run_canary_only":
            raise ValueError("mixed-outcome dry-run canary block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary_payloadless"
        ):
            raise ValueError("mixed-outcome dry-run canary execution mode mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        expected_counts = {
            "resident_count": 2,
            "issued_fetch_count": 1,
            "used_fetch_count": 1,
            "unused_fetch_count": 0,
            "demand_count": 2,
            "demand_hit_count": 1,
            "demand_miss_count": 1,
            "evicted_before_use_count": 0,
            "ready_late_miss_count": 0,
            "late_completion_unused_count": 0,
            "queue_batch_count": 1,
        }
        for field_name, expected in expected_counts.items():
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != expected:
                raise ValueError(f"{field_name} mismatch")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class PayloadCacheLiveRuntimeAdapterPayloadlessInstanceCanary:
    """Payloadless live-style adapter instance canary.

    This is the first gate that permits constructing the adapter object that
    owns the issue/demand surface.  It still blocks payload transfer, ready
    credit, kernel argument handoff, current WNA16 argument use, and endpoint
    timing claims.
    """

    present: bool
    stage: str
    status: str
    consumes_mixed_outcome_dry_run_canary: bool
    mixed_outcome_dry_run_canary_status: str
    manager_backend: str
    manager_runtime_contract: str
    manager_runtime_mode: str
    payloadless_instance_schema: str
    payloadless_live_adapter_created: bool
    payloadless_live_operations_ran: bool
    accounting_dry_run_enabled: bool
    issue_prefetch_accepted: bool
    duplicate_issue_suppressed: bool
    prefetched_demand_hit: bool
    unprefetched_demand_hit: bool
    unprefetched_demand_missed: bool
    live_adapter_instance_created: bool
    live_runtime_instantiated: bool
    capacity_entries: int
    issue_lead_tokens: int
    queue_deadline_us: float
    lookahead_us: float
    queue_batch_size: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int
    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    shifted_issue_accounting_enabled: bool
    shifted_issue_accounted_packet_count: int
    shifted_issue_unique_issue_key_count: int
    decision: str = "blocked"
    block_reason: str = "live_runtime_adapter_payloadless_instance_canary_only"
    execution_mode: str = (
        "payload_cache_live_runtime_adapter_payloadless_instance_canary_payloadless"
    )
    live_payload_runtime_enabled: bool = False
    payload_transfer_runtime_enabled: bool = False
    payload_deref_allowed: bool = False
    payload_deref_runtime_allowed: bool = False
    issued_payload_count: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    ready_before_demand_credit: bool = False
    real_ready_credit_granted: bool = False
    kernel_arg_pass_allowed: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    full_fetch_runtime_allowed: bool = False
    uses_current_wna16_args: bool = False
    passes_current_wna16_args: bool = False
    measures_tpot: bool = False
    measures_vllm_latency: bool = False

    def __post_init__(self) -> None:
        if self.present is not True:
            raise ValueError("payloadless instance canary must be present")
        if self.stage != "payload_cache_live_runtime_adapter_payloadless_instance_canary":
            raise ValueError("payloadless instance canary stage mismatch")
        if self.consumes_mixed_outcome_dry_run_canary is not True:
            raise ValueError("payloadless instance must consume mixed-outcome canary")
        if (
            not isinstance(self.mixed_outcome_dry_run_canary_status, str)
            or not self.mixed_outcome_dry_run_canary_status
        ):
            raise TypeError("mixed_outcome_dry_run_canary_status must be nonempty")
        expected_status = (
            "blocked_by_mixed_outcome_dry_run_canary:"
            f"{self.mixed_outcome_dry_run_canary_status}"
        )
        if self.status != expected_status:
            raise ValueError("payloadless instance canary status mismatch")
        if self.manager_backend != "ReadyTimeExpertCacheManager":
            raise ValueError("payloadless instance backend mismatch")
        if self.manager_runtime_contract != "ready_time_issue_demand_skeleton_v1":
            raise ValueError("payloadless instance contract mismatch")
        if self.manager_runtime_mode != "ready_time_payload_cache_skeleton":
            raise ValueError("payloadless instance mode mismatch")
        if (
            self.payloadless_instance_schema
            != "ready_time_payload_cache_runtime_adapter_payloadless_instance_canary_v1"
        ):
            raise ValueError("payloadless_instance_schema mismatch")
        for field_name in (
            "payloadless_live_adapter_created",
            "payloadless_live_operations_ran",
            "accounting_dry_run_enabled",
            "issue_prefetch_accepted",
            "duplicate_issue_suppressed",
            "prefetched_demand_hit",
            "unprefetched_demand_missed",
            "live_adapter_instance_created",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be true")
        for field_name in (
            "unprefetched_demand_hit",
            "live_runtime_instantiated",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must be false")
        if self.decision != "blocked":
            raise ValueError("payloadless instance canary decision must stay blocked")
        if self.block_reason != "live_runtime_adapter_payloadless_instance_canary_only":
            raise ValueError("payloadless instance block reason mismatch")
        if (
            self.execution_mode
            != "payload_cache_live_runtime_adapter_payloadless_instance_canary_payloadless"
        ):
            raise ValueError("payloadless instance execution mode mismatch")
        expected_counts = {
            "resident_count": 2,
            "issued_fetch_count": 1,
            "used_fetch_count": 1,
            "unused_fetch_count": 0,
            "demand_count": 2,
            "demand_hit_count": 1,
            "demand_miss_count": 1,
            "evicted_before_use_count": 0,
            "ready_late_miss_count": 0,
            "late_completion_unused_count": 0,
            "queue_batch_count": 1,
        }
        for field_name, expected in expected_counts.items():
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != expected:
                raise ValueError(f"{field_name} mismatch")
        for field_name in (
            "capacity_entries",
            "issue_lead_tokens",
            "queue_batch_size",
            "shifted_issue_accounted_packet_count",
            "shifted_issue_unique_issue_key_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        for field_name in (
            "queue_deadline_us",
            "lookahead_us",
            "queue_service_us",
            "queue_total_span_us",
            "queue_wait_us",
            "queue_max_delay_us",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{field_name} must be finite")
            if field_name in ("queue_deadline_us", "lookahead_us") and numeric <= 0.0:
                raise ValueError(f"{field_name} must be positive")
            if field_name not in ("queue_deadline_us", "lookahead_us") and numeric != 0.0:
                raise ValueError(f"{field_name} must remain zero")
        if self.shifted_issue_accounting_enabled is not True:
            raise ValueError("shifted issue accounting must be enabled")
        for field_name in ("issued_payload_count", "payload_bytes"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value != 0:
                raise ValueError(f"{field_name} must remain zero")
        for field_name in (
            "live_payload_runtime_enabled",
            "payload_transfer_runtime_enabled",
            "payload_deref_allowed",
            "payload_deref_runtime_allowed",
            "ready_credit",
            "ready_before_demand_credit",
            "real_ready_credit_granted",
            "kernel_arg_pass_allowed",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "full_fetch_runtime_allowed",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} must remain disabled")

    def as_dict(self) -> dict[str, bool | float | int | str]:
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


def build_payload_cache_queue_budget_runtime_envelope(
    *,
    cell_count: int,
    event_timing_mode: str,
    first_model_passing_capacity: int,
    first_model_passing_issue_lead_tokens: int,
    first_model_passing_queue_deadline_us: float,
    first_model_passing_lookahead_us: float,
    shifted_issue_accounting_enabled: bool,
    shifted_issue_accounted_packet_count: int,
    shifted_issue_unique_issue_key_count: int,
) -> PayloadCacheQueueBudgetRuntimeEnvelope:
    """Build the payloadless runtime envelope from queue-budget sweep evidence."""

    def require_int(name: str, value: int) -> int:
        if type(value) is not int:
            raise TypeError(f"{name} must be an integer")
        return value

    def require_bool(name: str, value: bool) -> bool:
        if type(value) is not bool:
            raise TypeError(f"{name} must be a boolean")
        return value

    def require_positive_number(name: str, value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= 0.0:
            raise ValueError(f"{name} must be positive")
        return numeric

    if type(event_timing_mode) is not str:
        raise TypeError("event_timing_mode must be a string")
    return PayloadCacheQueueBudgetRuntimeEnvelope(
        present=True,
        stage="payload_cache_queue_budget_runtime_envelope_lab_gate",
        status="model_queue_budget_satisfied_runtime_disabled",
        consumes_queue_budget_sweep=True,
        event_timing_mode=event_timing_mode,
        cell_count=require_int("cell_count", cell_count),
        first_model_passing_capacity=require_int(
            "first_model_passing_capacity",
            first_model_passing_capacity,
        ),
        first_model_passing_issue_lead_tokens=require_int(
            "first_model_passing_issue_lead_tokens",
            first_model_passing_issue_lead_tokens,
        ),
        first_model_passing_queue_deadline_us=require_positive_number(
            "first_model_passing_queue_deadline_us",
            first_model_passing_queue_deadline_us,
        ),
        first_model_passing_lookahead_us=require_positive_number(
            "first_model_passing_lookahead_us",
            first_model_passing_lookahead_us,
        ),
        shifted_issue_accounting_enabled=require_bool(
            "shifted_issue_accounting_enabled",
            shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=require_int(
            "shifted_issue_accounted_packet_count",
            shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=require_int(
            "shifted_issue_unique_issue_key_count",
            shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_payload_stage_preflight(
    envelope: PayloadCacheQueueBudgetRuntimeEnvelope,
) -> PayloadCacheLivePayloadStagePreflight:
    """Build the blocked preflight for the future live payload stage."""

    if not isinstance(envelope, PayloadCacheQueueBudgetRuntimeEnvelope):
        raise TypeError("envelope must be a PayloadCacheQueueBudgetRuntimeEnvelope")
    status = str(envelope.status)
    return PayloadCacheLivePayloadStagePreflight(
        present=True,
        stage="payload_cache_live_payload_stage_preflight",
        status=f"blocked_by_queue_budget_runtime_envelope:{status}",
        consumes_queue_budget_runtime_envelope=True,
        queue_budget_envelope_status=status,
        queue_budget_capacity_entries=int(envelope.first_model_passing_capacity),
        queue_budget_issue_lead_tokens=int(
            envelope.first_model_passing_issue_lead_tokens,
        ),
        queue_budget_queue_deadline_us=float(
            envelope.first_model_passing_queue_deadline_us,
        ),
        queue_budget_lookahead_us=float(envelope.first_model_passing_lookahead_us),
        shifted_issue_accounting_enabled=bool(envelope.shifted_issue_accounting_enabled),
        shifted_issue_accounted_packet_count=int(
            envelope.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            envelope.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_payload_runtime_disabled_canary(
    preflight: PayloadCacheLivePayloadStagePreflight,
    envelope: PayloadCacheQueueBudgetRuntimeEnvelope,
) -> PayloadCacheLivePayloadRuntimeDisabledCanary:
    """Build the blocked canary for the future live payload runtime."""

    if not isinstance(preflight, PayloadCacheLivePayloadStagePreflight):
        raise TypeError("preflight must be a PayloadCacheLivePayloadStagePreflight")
    if not isinstance(envelope, PayloadCacheQueueBudgetRuntimeEnvelope):
        raise TypeError("envelope must be a PayloadCacheQueueBudgetRuntimeEnvelope")
    if preflight.queue_budget_envelope_status != envelope.status:
        raise ValueError("preflight and envelope status mismatch")
    if int(envelope.first_model_passing_capacity) != preflight.queue_budget_capacity_entries:
        raise ValueError("preflight and envelope capacity mismatch")
    if (
        int(envelope.first_model_passing_issue_lead_tokens)
        != preflight.queue_budget_issue_lead_tokens
    ):
        raise ValueError("preflight and envelope issue lead mismatch")
    if (
        float(envelope.first_model_passing_queue_deadline_us)
        != float(preflight.queue_budget_queue_deadline_us)
    ):
        raise ValueError("preflight and envelope queue deadline mismatch")
    if float(envelope.first_model_passing_lookahead_us) != float(
        preflight.queue_budget_lookahead_us,
    ):
        raise ValueError("preflight and envelope lookahead mismatch")
    if (
        bool(envelope.shifted_issue_accounting_enabled)
        is not bool(preflight.shifted_issue_accounting_enabled)
    ):
        raise ValueError("preflight and envelope shifted issue accounting mismatch")
    if (
        int(envelope.shifted_issue_accounted_packet_count)
        != preflight.shifted_issue_accounted_packet_count
    ):
        raise ValueError("preflight and envelope shifted packet count mismatch")
    if (
        int(envelope.shifted_issue_unique_issue_key_count)
        != preflight.shifted_issue_unique_issue_key_count
    ):
        raise ValueError("preflight and envelope shifted unique issue count mismatch")
    status = str(preflight.status)
    return PayloadCacheLivePayloadRuntimeDisabledCanary(
        present=True,
        stage="payload_cache_live_payload_runtime_disabled_canary",
        status=f"blocked_by_live_payload_stage:{status}",
        consumes_live_payload_stage_preflight=True,
        live_payload_stage_status=status,
        queue_budget_capacity_entries=int(envelope.first_model_passing_capacity),
        queue_budget_issue_lead_tokens=int(
            envelope.first_model_passing_issue_lead_tokens,
        ),
        queue_budget_queue_deadline_us=float(
            envelope.first_model_passing_queue_deadline_us,
        ),
        queue_budget_lookahead_us=float(envelope.first_model_passing_lookahead_us),
        shifted_issue_accounting_enabled=bool(envelope.shifted_issue_accounting_enabled),
        shifted_issue_accounted_packet_count=int(
            envelope.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            envelope.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_manager_implementation_artifact(
    canary: PayloadCacheLivePayloadRuntimeDisabledCanary,
    envelope: PayloadCacheQueueBudgetRuntimeEnvelope,
) -> PayloadCacheManagerImplementationArtifact:
    """Build the disabled concrete manager artifact behind the runtime canary."""

    if not isinstance(canary, PayloadCacheLivePayloadRuntimeDisabledCanary):
        raise TypeError("canary must be a PayloadCacheLivePayloadRuntimeDisabledCanary")
    if not isinstance(envelope, PayloadCacheQueueBudgetRuntimeEnvelope):
        raise TypeError("envelope must be a PayloadCacheQueueBudgetRuntimeEnvelope")
    expected_live_stage_status = f"blocked_by_queue_budget_runtime_envelope:{envelope.status}"
    if canary.live_payload_stage_status != expected_live_stage_status:
        raise ValueError("canary and envelope live-stage status mismatch")
    if canary.status != f"blocked_by_live_payload_stage:{expected_live_stage_status}":
        raise ValueError("canary and envelope runtime status mismatch")
    if int(envelope.first_model_passing_capacity) != canary.queue_budget_capacity_entries:
        raise ValueError("canary and envelope capacity mismatch")
    if (
        int(envelope.first_model_passing_issue_lead_tokens)
        != canary.queue_budget_issue_lead_tokens
    ):
        raise ValueError("canary and envelope issue lead mismatch")
    if (
        float(envelope.first_model_passing_queue_deadline_us)
        != float(canary.queue_budget_queue_deadline_us)
    ):
        raise ValueError("canary and envelope queue deadline mismatch")
    if float(envelope.first_model_passing_lookahead_us) != float(
        canary.queue_budget_lookahead_us,
    ):
        raise ValueError("canary and envelope lookahead mismatch")
    if (
        bool(envelope.shifted_issue_accounting_enabled)
        is not bool(canary.shifted_issue_accounting_enabled)
    ):
        raise ValueError("canary and envelope shifted issue accounting mismatch")
    if (
        int(envelope.shifted_issue_accounted_packet_count)
        != canary.shifted_issue_accounted_packet_count
    ):
        raise ValueError("canary and envelope shifted packet count mismatch")
    if (
        int(envelope.shifted_issue_unique_issue_key_count)
        != canary.shifted_issue_unique_issue_key_count
    ):
        raise ValueError("canary and envelope shifted unique issue count mismatch")
    return PayloadCacheManagerImplementationArtifact(
        present=True,
        stage="payload_cache_manager_implementation_artifact",
        status=f"blocked_by_live_payload_runtime:{canary.status}",
        consumes_live_payload_runtime_canary=True,
        live_payload_runtime_status=str(canary.status),
        manager_backend="ReadyTimeExpertCacheManager",
        manager_contract="event_driven_queue_budget_cache_manager_v1",
        capacity_entries=int(envelope.first_model_passing_capacity),
        issue_lead_tokens=int(envelope.first_model_passing_issue_lead_tokens),
        queue_deadline_us=float(envelope.first_model_passing_queue_deadline_us),
        lookahead_us=float(envelope.first_model_passing_lookahead_us),
        shifted_issue_accounting_enabled=bool(envelope.shifted_issue_accounting_enabled),
        shifted_issue_accounted_packet_count=int(
            envelope.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            envelope.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_manager_runtime_skeleton(
    artifact: PayloadCacheManagerImplementationArtifact,
) -> PayloadCacheManagerRuntimeSkeleton:
    """Build the default-disabled runtime skeleton behind a manager artifact."""

    if not isinstance(artifact, PayloadCacheManagerImplementationArtifact):
        raise TypeError("artifact must be a PayloadCacheManagerImplementationArtifact")
    if artifact.decision != "blocked":
        raise ValueError("manager artifact must stay blocked")
    if artifact.execution_mode != "payload_cache_manager_implementation_artifact_disabled":
        raise ValueError("manager artifact execution mode mismatch")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(artifact, field_name) is not False:
            raise ValueError(f"manager artifact {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(artifact, field_name) != 0:
            raise ValueError(f"manager artifact {field_name} must remain zero")
    return PayloadCacheManagerRuntimeSkeleton(
        present=True,
        stage="payload_cache_manager_runtime_skeleton",
        status=f"blocked_by_manager_artifact:{artifact.status}",
        consumes_manager_implementation_artifact=True,
        manager_artifact_status=str(artifact.status),
        manager_backend=str(artifact.manager_backend),
        manager_contract=str(artifact.manager_contract),
        manager_runtime_contract="ready_time_issue_demand_skeleton_v1",
        manager_runtime_mode="ready_time_payload_cache_skeleton",
        capacity_entries=int(artifact.capacity_entries),
        issue_lead_tokens=int(artifact.issue_lead_tokens),
        queue_deadline_us=float(artifact.queue_deadline_us),
        lookahead_us=float(artifact.lookahead_us),
        shifted_issue_accounting_enabled=bool(
            artifact.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            artifact.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            artifact.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_manager_runtime_snapshot_artifact(
    skeleton: PayloadCacheManagerRuntimeSkeleton,
) -> PayloadCacheManagerRuntimeSnapshotArtifact:
    """Build the default-disabled runtime snapshot artifact behind a skeleton."""

    if not isinstance(skeleton, PayloadCacheManagerRuntimeSkeleton):
        raise TypeError("skeleton must be a PayloadCacheManagerRuntimeSkeleton")
    if skeleton.decision != "blocked":
        raise ValueError("runtime skeleton must stay blocked")
    if skeleton.runtime_instantiated is not False:
        raise ValueError("runtime skeleton must not instantiate live runtime")
    if skeleton.execution_mode != "payload_cache_manager_runtime_skeleton_disabled":
        raise ValueError("runtime skeleton execution mode mismatch")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(skeleton, field_name) is not False:
            raise ValueError(f"runtime skeleton {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(skeleton, field_name) != 0:
            raise ValueError(f"runtime skeleton {field_name} must remain zero")

    manager = ReadyTimeExpertCacheManager(
        capacity=int(skeleton.capacity_entries),
        service_us_per_issue=0.0,
        service_us_per_batch=0.0,
        queue_batch_size=1,
        queue_deadline_us=float(skeleton.queue_deadline_us),
    )
    snapshot = manager.snapshot()
    return PayloadCacheManagerRuntimeSnapshotArtifact(
        present=True,
        stage="payload_cache_manager_runtime_snapshot_artifact",
        status=f"blocked_by_runtime_skeleton:{skeleton.status}",
        consumes_runtime_skeleton=True,
        runtime_skeleton_status=str(skeleton.status),
        manager_backend=str(skeleton.manager_backend),
        manager_runtime_contract=str(skeleton.manager_runtime_contract),
        manager_runtime_mode=str(skeleton.manager_runtime_mode),
        snapshot_source="ReadyTimeExpertCacheManager.empty_snapshot",
        accounting_snapshot_instantiated=True,
        live_runtime_instantiated=False,
        capacity_entries=int(snapshot.capacity),
        issue_lead_tokens=int(skeleton.issue_lead_tokens),
        queue_deadline_us=float(snapshot.queue_deadline_us),
        lookahead_us=float(skeleton.lookahead_us),
        queue_batch_size=int(snapshot.queue_batch_size),
        resident_count=int(snapshot.resident_count),
        issued_fetch_count=int(snapshot.issued_fetch_count),
        used_fetch_count=int(snapshot.used_fetch_count),
        unused_fetch_count=int(snapshot.unused_fetch_count),
        demand_count=int(snapshot.demand_count),
        demand_hit_count=int(snapshot.demand_hit_count),
        demand_miss_count=int(snapshot.demand_miss_count),
        evicted_before_use_count=int(snapshot.evicted_before_use_count),
        ready_late_miss_count=int(snapshot.ready_late_miss_count),
        late_completion_unused_count=int(snapshot.late_completion_unused_count),
        queue_batch_count=int(snapshot.queue_batch_count),
        queue_service_us=float(snapshot.queue_service_us),
        queue_total_span_us=float(snapshot.queue_total_span_us),
        queue_wait_us=float(snapshot.queue_wait_us),
        queue_max_delay_us=float(snapshot.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            skeleton.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            skeleton.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            skeleton.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_snapshot_backed_live_runtime_preflight(
    snapshot: PayloadCacheManagerRuntimeSnapshotArtifact,
) -> PayloadCacheSnapshotBackedLiveRuntimePreflight:
    """Build the still-disabled live-runtime preflight from a manager snapshot."""

    if not isinstance(snapshot, PayloadCacheManagerRuntimeSnapshotArtifact):
        raise TypeError("snapshot must be a PayloadCacheManagerRuntimeSnapshotArtifact")
    if snapshot.decision != "blocked":
        raise ValueError("runtime snapshot must stay blocked")
    if snapshot.accounting_snapshot_instantiated is not True:
        raise ValueError("runtime snapshot must instantiate accounting snapshot")
    if snapshot.live_runtime_instantiated is not False:
        raise ValueError("runtime snapshot must not instantiate live runtime")
    if snapshot.execution_mode != "payload_cache_manager_runtime_snapshot_disabled":
        raise ValueError("runtime snapshot execution mode mismatch")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(snapshot, field_name) != 0:
            raise ValueError(f"runtime snapshot {field_name} must remain zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(snapshot, field_name)) != 0.0:
            raise ValueError(f"runtime snapshot {field_name} must remain zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(snapshot, field_name) is not False:
            raise ValueError(f"runtime snapshot {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(snapshot, field_name) != 0:
            raise ValueError(f"runtime snapshot {field_name} must remain zero")

    return PayloadCacheSnapshotBackedLiveRuntimePreflight(
        present=True,
        stage="payload_cache_snapshot_backed_live_runtime_preflight",
        status=f"blocked_by_runtime_snapshot:{snapshot.status}",
        consumes_runtime_snapshot=True,
        runtime_snapshot_status=str(snapshot.status),
        manager_backend=str(snapshot.manager_backend),
        manager_runtime_contract=str(snapshot.manager_runtime_contract),
        manager_runtime_mode=str(snapshot.manager_runtime_mode),
        snapshot_source="PayloadCacheManagerRuntimeSnapshotArtifact",
        live_runtime_preflight_instantiated=True,
        accounting_snapshot_instantiated=bool(
            snapshot.accounting_snapshot_instantiated,
        ),
        live_runtime_instantiated=False,
        capacity_entries=int(snapshot.capacity_entries),
        issue_lead_tokens=int(snapshot.issue_lead_tokens),
        queue_deadline_us=float(snapshot.queue_deadline_us),
        lookahead_us=float(snapshot.lookahead_us),
        queue_batch_size=int(snapshot.queue_batch_size),
        resident_count=int(snapshot.resident_count),
        issued_fetch_count=int(snapshot.issued_fetch_count),
        used_fetch_count=int(snapshot.used_fetch_count),
        unused_fetch_count=int(snapshot.unused_fetch_count),
        demand_count=int(snapshot.demand_count),
        demand_hit_count=int(snapshot.demand_hit_count),
        demand_miss_count=int(snapshot.demand_miss_count),
        evicted_before_use_count=int(snapshot.evicted_before_use_count),
        ready_late_miss_count=int(snapshot.ready_late_miss_count),
        late_completion_unused_count=int(snapshot.late_completion_unused_count),
        queue_batch_count=int(snapshot.queue_batch_count),
        queue_service_us=float(snapshot.queue_service_us),
        queue_total_span_us=float(snapshot.queue_total_span_us),
        queue_wait_us=float(snapshot.queue_wait_us),
        queue_max_delay_us=float(snapshot.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            snapshot.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            snapshot.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            snapshot.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_snapshot_backed_live_runtime_disabled_canary(
    preflight: PayloadCacheSnapshotBackedLiveRuntimePreflight,
) -> PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary:
    """Build the blocked live-runtime canary from the snapshot-backed preflight."""

    if not isinstance(preflight, PayloadCacheSnapshotBackedLiveRuntimePreflight):
        raise TypeError(
            "preflight must be a PayloadCacheSnapshotBackedLiveRuntimePreflight",
        )
    if preflight.decision != "blocked":
        raise ValueError("live-runtime preflight must stay blocked")
    if preflight.live_runtime_preflight_instantiated is not True:
        raise ValueError("live-runtime preflight object must be instantiated")
    if preflight.accounting_snapshot_instantiated is not True:
        raise ValueError("live-runtime preflight must consume accounting snapshot")
    if preflight.live_runtime_instantiated is not False:
        raise ValueError("live-runtime preflight must not instantiate live runtime")
    if (
        preflight.execution_mode
        != "payload_cache_snapshot_backed_live_runtime_preflight_disabled"
    ):
        raise ValueError("live-runtime preflight execution mode mismatch")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(preflight, field_name) != 0:
            raise ValueError(f"live-runtime preflight {field_name} must remain zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(preflight, field_name)) != 0.0:
            raise ValueError(f"live-runtime preflight {field_name} must remain zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(preflight, field_name) is not False:
            raise ValueError(f"live-runtime preflight {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(preflight, field_name) != 0:
            raise ValueError(f"live-runtime preflight {field_name} must remain zero")

    return PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary(
        present=True,
        stage="payload_cache_snapshot_backed_live_runtime_disabled_canary",
        status=f"blocked_by_live_runtime_preflight:{preflight.status}",
        consumes_live_runtime_preflight=True,
        live_runtime_preflight_status=str(preflight.status),
        manager_backend=str(preflight.manager_backend),
        manager_runtime_contract=str(preflight.manager_runtime_contract),
        manager_runtime_mode=str(preflight.manager_runtime_mode),
        live_runtime_canary_instantiated=True,
        live_runtime_preflight_instantiated=bool(
            preflight.live_runtime_preflight_instantiated,
        ),
        accounting_snapshot_instantiated=bool(
            preflight.accounting_snapshot_instantiated,
        ),
        live_runtime_instantiated=False,
        capacity_entries=int(preflight.capacity_entries),
        issue_lead_tokens=int(preflight.issue_lead_tokens),
        queue_deadline_us=float(preflight.queue_deadline_us),
        lookahead_us=float(preflight.lookahead_us),
        queue_batch_size=int(preflight.queue_batch_size),
        resident_count=int(preflight.resident_count),
        issued_fetch_count=int(preflight.issued_fetch_count),
        used_fetch_count=int(preflight.used_fetch_count),
        unused_fetch_count=int(preflight.unused_fetch_count),
        demand_count=int(preflight.demand_count),
        demand_hit_count=int(preflight.demand_hit_count),
        demand_miss_count=int(preflight.demand_miss_count),
        evicted_before_use_count=int(preflight.evicted_before_use_count),
        ready_late_miss_count=int(preflight.ready_late_miss_count),
        late_completion_unused_count=int(preflight.late_completion_unused_count),
        queue_batch_count=int(preflight.queue_batch_count),
        queue_service_us=float(preflight.queue_service_us),
        queue_total_span_us=float(preflight.queue_total_span_us),
        queue_wait_us=float(preflight.queue_wait_us),
        queue_max_delay_us=float(preflight.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            preflight.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            preflight.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            preflight.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_state_shape_check(
    canary: PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary,
) -> PayloadCacheLiveRuntimeStateShapeCheck:
    """Build the blocked state-shape check behind the live-runtime canary."""

    if not isinstance(canary, PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary):
        raise TypeError(
            "canary must be a PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary",
        )
    if canary.decision != "blocked":
        raise ValueError("live-runtime canary must stay blocked")
    if canary.live_runtime_canary_instantiated is not True:
        raise ValueError("live-runtime canary object must be instantiated")
    if canary.live_runtime_instantiated is not False:
        raise ValueError("live-runtime canary must not instantiate live runtime")
    if (
        canary.execution_mode
        != "payload_cache_snapshot_backed_live_runtime_canary_disabled"
    ):
        raise ValueError("live-runtime canary execution mode mismatch")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(canary, field_name) != 0:
            raise ValueError(f"live-runtime canary {field_name} must remain zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(canary, field_name)) != 0.0:
            raise ValueError(f"live-runtime canary {field_name} must remain zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(canary, field_name) is not False:
            raise ValueError(f"live-runtime canary {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(canary, field_name) != 0:
            raise ValueError(f"live-runtime canary {field_name} must remain zero")

    return PayloadCacheLiveRuntimeStateShapeCheck(
        present=True,
        stage="payload_cache_live_runtime_state_shape_check",
        status=f"blocked_by_live_runtime_canary:{canary.status}",
        consumes_live_runtime_canary=True,
        live_runtime_canary_status=str(canary.status),
        manager_backend=str(canary.manager_backend),
        manager_runtime_contract=str(canary.manager_runtime_contract),
        manager_runtime_mode=str(canary.manager_runtime_mode),
        state_shape_schema="ready_time_issue_demand_state_shape_v1",
        live_runtime_state_shape_checked=True,
        issue_queue_shape_checked=True,
        demand_state_shape_checked=True,
        resident_index_shape_checked=True,
        queue_timing_shape_checked=True,
        live_runtime_instantiated=False,
        capacity_entries=int(canary.capacity_entries),
        issue_lead_tokens=int(canary.issue_lead_tokens),
        queue_deadline_us=float(canary.queue_deadline_us),
        lookahead_us=float(canary.lookahead_us),
        queue_batch_size=int(canary.queue_batch_size),
        resident_count=int(canary.resident_count),
        issued_fetch_count=int(canary.issued_fetch_count),
        used_fetch_count=int(canary.used_fetch_count),
        unused_fetch_count=int(canary.unused_fetch_count),
        demand_count=int(canary.demand_count),
        demand_hit_count=int(canary.demand_hit_count),
        demand_miss_count=int(canary.demand_miss_count),
        evicted_before_use_count=int(canary.evicted_before_use_count),
        ready_late_miss_count=int(canary.ready_late_miss_count),
        late_completion_unused_count=int(canary.late_completion_unused_count),
        queue_batch_count=int(canary.queue_batch_count),
        queue_service_us=float(canary.queue_service_us),
        queue_total_span_us=float(canary.queue_total_span_us),
        queue_wait_us=float(canary.queue_wait_us),
        queue_max_delay_us=float(canary.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            canary.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            canary.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            canary.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_object_construction_preflight(
    state_shape: PayloadCacheLiveRuntimeStateShapeCheck,
) -> PayloadCacheLiveRuntimeObjectConstructionPreflight:
    """Build the blocked typed-container preflight behind state-shape checks."""

    if not isinstance(state_shape, PayloadCacheLiveRuntimeStateShapeCheck):
        raise TypeError("state_shape must be a PayloadCacheLiveRuntimeStateShapeCheck")
    if state_shape.decision != "blocked":
        raise ValueError("state-shape check must stay blocked")
    for field_name in (
        "live_runtime_state_shape_checked",
        "issue_queue_shape_checked",
        "demand_state_shape_checked",
        "resident_index_shape_checked",
        "queue_timing_shape_checked",
    ):
        if getattr(state_shape, field_name) is not True:
            raise ValueError(f"state-shape {field_name} must be checked")
    if state_shape.live_runtime_instantiated is not False:
        raise ValueError("state-shape check must not instantiate live runtime")
    if (
        state_shape.execution_mode
        != "payload_cache_live_runtime_state_shape_check_disabled"
    ):
        raise ValueError("state-shape execution mode mismatch")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(state_shape, field_name) != 0:
            raise ValueError(f"state-shape {field_name} must remain zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(state_shape, field_name)) != 0.0:
            raise ValueError(f"state-shape {field_name} must remain zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(state_shape, field_name) is not False:
            raise ValueError(f"state-shape {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(state_shape, field_name) != 0:
            raise ValueError(f"state-shape {field_name} must remain zero")

    return PayloadCacheLiveRuntimeObjectConstructionPreflight(
        present=True,
        stage="payload_cache_live_runtime_object_construction_preflight",
        status=f"blocked_by_state_shape_check:{state_shape.status}",
        consumes_state_shape_check=True,
        state_shape_status=str(state_shape.status),
        manager_backend=str(state_shape.manager_backend),
        manager_runtime_contract=str(state_shape.manager_runtime_contract),
        manager_runtime_mode=str(state_shape.manager_runtime_mode),
        state_shape_schema=str(state_shape.state_shape_schema),
        object_construction_preflight_instantiated=True,
        typed_issue_queue_container_declared=True,
        typed_demand_state_container_declared=True,
        typed_resident_index_container_declared=True,
        typed_queue_timing_container_declared=True,
        live_runtime_instantiated=False,
        capacity_entries=int(state_shape.capacity_entries),
        issue_lead_tokens=int(state_shape.issue_lead_tokens),
        queue_deadline_us=float(state_shape.queue_deadline_us),
        lookahead_us=float(state_shape.lookahead_us),
        queue_batch_size=int(state_shape.queue_batch_size),
        resident_count=int(state_shape.resident_count),
        issued_fetch_count=int(state_shape.issued_fetch_count),
        used_fetch_count=int(state_shape.used_fetch_count),
        unused_fetch_count=int(state_shape.unused_fetch_count),
        demand_count=int(state_shape.demand_count),
        demand_hit_count=int(state_shape.demand_hit_count),
        demand_miss_count=int(state_shape.demand_miss_count),
        evicted_before_use_count=int(state_shape.evicted_before_use_count),
        ready_late_miss_count=int(state_shape.ready_late_miss_count),
        late_completion_unused_count=int(state_shape.late_completion_unused_count),
        queue_batch_count=int(state_shape.queue_batch_count),
        queue_service_us=float(state_shape.queue_service_us),
        queue_total_span_us=float(state_shape.queue_total_span_us),
        queue_wait_us=float(state_shape.queue_wait_us),
        queue_max_delay_us=float(state_shape.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            state_shape.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            state_shape.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            state_shape.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_object_adapter_preflight(
    object_preflight: PayloadCacheLiveRuntimeObjectConstructionPreflight,
) -> PayloadCacheLiveRuntimeObjectAdapterPreflight:
    """Build the blocked runtime adapter preflight behind object construction."""

    if not isinstance(
        object_preflight,
        PayloadCacheLiveRuntimeObjectConstructionPreflight,
    ):
        raise TypeError(
            "object_preflight must be a "
            "PayloadCacheLiveRuntimeObjectConstructionPreflight",
        )
    if object_preflight.decision != "blocked":
        raise ValueError("object preflight must stay blocked")
    for field_name in (
        "object_construction_preflight_instantiated",
        "typed_issue_queue_container_declared",
        "typed_demand_state_container_declared",
        "typed_resident_index_container_declared",
        "typed_queue_timing_container_declared",
    ):
        if getattr(object_preflight, field_name) is not True:
            raise ValueError(f"object preflight {field_name} must be declared")
    if object_preflight.live_runtime_instantiated is not False:
        raise ValueError("object preflight must not instantiate live runtime")
    if (
        object_preflight.execution_mode
        != "payload_cache_live_runtime_object_construction_preflight_disabled"
    ):
        raise ValueError("object preflight execution mode mismatch")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(object_preflight, field_name) != 0:
            raise ValueError(f"object preflight {field_name} must remain zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(object_preflight, field_name)) != 0.0:
            raise ValueError(f"object preflight {field_name} must remain zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(object_preflight, field_name) is not False:
            raise ValueError(f"object preflight {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(object_preflight, field_name) != 0:
            raise ValueError(f"object preflight {field_name} must remain zero")

    return PayloadCacheLiveRuntimeObjectAdapterPreflight(
        present=True,
        stage="payload_cache_live_runtime_object_adapter_preflight",
        status=(
            "blocked_by_object_construction_preflight:"
            f"{object_preflight.status}"
        ),
        consumes_object_construction_preflight=True,
        object_preflight_status=str(object_preflight.status),
        manager_backend=str(object_preflight.manager_backend),
        manager_runtime_contract=str(object_preflight.manager_runtime_contract),
        manager_runtime_mode=str(object_preflight.manager_runtime_mode),
        state_shape_schema=str(object_preflight.state_shape_schema),
        runtime_adapter_schema="ready_time_payload_cache_runtime_adapter_v1",
        object_construction_preflight_instantiated=bool(
            object_preflight.object_construction_preflight_instantiated,
        ),
        runtime_object_adapter_declared=True,
        issue_queue_adapter_bound=True,
        demand_state_adapter_bound=True,
        resident_index_adapter_bound=True,
        queue_timing_adapter_bound=True,
        live_runtime_instantiated=False,
        capacity_entries=int(object_preflight.capacity_entries),
        issue_lead_tokens=int(object_preflight.issue_lead_tokens),
        queue_deadline_us=float(object_preflight.queue_deadline_us),
        lookahead_us=float(object_preflight.lookahead_us),
        queue_batch_size=int(object_preflight.queue_batch_size),
        resident_count=int(object_preflight.resident_count),
        issued_fetch_count=int(object_preflight.issued_fetch_count),
        used_fetch_count=int(object_preflight.used_fetch_count),
        unused_fetch_count=int(object_preflight.unused_fetch_count),
        demand_count=int(object_preflight.demand_count),
        demand_hit_count=int(object_preflight.demand_hit_count),
        demand_miss_count=int(object_preflight.demand_miss_count),
        evicted_before_use_count=int(object_preflight.evicted_before_use_count),
        ready_late_miss_count=int(object_preflight.ready_late_miss_count),
        late_completion_unused_count=int(
            object_preflight.late_completion_unused_count,
        ),
        queue_batch_count=int(object_preflight.queue_batch_count),
        queue_service_us=float(object_preflight.queue_service_us),
        queue_total_span_us=float(object_preflight.queue_total_span_us),
        queue_wait_us=float(object_preflight.queue_wait_us),
        queue_max_delay_us=float(object_preflight.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            object_preflight.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            object_preflight.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            object_preflight.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_materialization_preflight(
    object_adapter: PayloadCacheLiveRuntimeObjectAdapterPreflight,
) -> PayloadCacheLiveRuntimeAdapterMaterializationPreflight:
    """Build the blocked adapter materialization preflight behind adapter binding."""

    if not isinstance(object_adapter, PayloadCacheLiveRuntimeObjectAdapterPreflight):
        raise TypeError(
            "object_adapter must be a PayloadCacheLiveRuntimeObjectAdapterPreflight",
        )
    if object_adapter.decision != "blocked":
        raise ValueError("object adapter preflight must stay blocked")
    if object_adapter.object_construction_preflight_instantiated is not True:
        raise ValueError(
            "object adapter object_construction_preflight_instantiated must be true",
        )
    for field_name in (
        "runtime_object_adapter_declared",
        "issue_queue_adapter_bound",
        "demand_state_adapter_bound",
        "resident_index_adapter_bound",
        "queue_timing_adapter_bound",
    ):
        if getattr(object_adapter, field_name) is not True:
            raise ValueError(f"object adapter {field_name} must be bound")
    if object_adapter.live_runtime_instantiated is not False:
        raise ValueError("object adapter must not instantiate live runtime")
    if (
        object_adapter.execution_mode
        != "payload_cache_live_runtime_object_adapter_preflight_disabled"
    ):
        raise ValueError("object adapter execution mode mismatch")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(object_adapter, field_name) != 0:
            raise ValueError(f"object adapter {field_name} must remain zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(object_adapter, field_name)) != 0.0:
            raise ValueError(f"object adapter {field_name} must remain zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(object_adapter, field_name) is not False:
            raise ValueError(f"object adapter {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(object_adapter, field_name) != 0:
            raise ValueError(f"object adapter {field_name} must remain zero")

    return PayloadCacheLiveRuntimeAdapterMaterializationPreflight(
        present=True,
        stage="payload_cache_live_runtime_adapter_materialization_preflight",
        status=f"blocked_by_object_adapter_preflight:{object_adapter.status}",
        consumes_object_adapter_preflight=True,
        object_adapter_status=str(object_adapter.status),
        manager_backend=str(object_adapter.manager_backend),
        manager_runtime_contract=str(object_adapter.manager_runtime_contract),
        manager_runtime_mode=str(object_adapter.manager_runtime_mode),
        state_shape_schema=str(object_adapter.state_shape_schema),
        runtime_adapter_schema=str(object_adapter.runtime_adapter_schema),
        object_construction_preflight_instantiated=bool(
            object_adapter.object_construction_preflight_instantiated,
        ),
        adapter_materialization_preflight_instantiated=True,
        runtime_object_adapter_declared=bool(
            object_adapter.runtime_object_adapter_declared,
        ),
        issue_queue_materialization_checked=True,
        demand_state_materialization_checked=True,
        resident_index_materialization_checked=True,
        queue_timing_materialization_checked=True,
        live_runtime_instantiated=False,
        capacity_entries=int(object_adapter.capacity_entries),
        issue_lead_tokens=int(object_adapter.issue_lead_tokens),
        queue_deadline_us=float(object_adapter.queue_deadline_us),
        lookahead_us=float(object_adapter.lookahead_us),
        queue_batch_size=int(object_adapter.queue_batch_size),
        resident_count=int(object_adapter.resident_count),
        issued_fetch_count=int(object_adapter.issued_fetch_count),
        used_fetch_count=int(object_adapter.used_fetch_count),
        unused_fetch_count=int(object_adapter.unused_fetch_count),
        demand_count=int(object_adapter.demand_count),
        demand_hit_count=int(object_adapter.demand_hit_count),
        demand_miss_count=int(object_adapter.demand_miss_count),
        evicted_before_use_count=int(object_adapter.evicted_before_use_count),
        ready_late_miss_count=int(object_adapter.ready_late_miss_count),
        late_completion_unused_count=int(object_adapter.late_completion_unused_count),
        queue_batch_count=int(object_adapter.queue_batch_count),
        queue_service_us=float(object_adapter.queue_service_us),
        queue_total_span_us=float(object_adapter.queue_total_span_us),
        queue_wait_us=float(object_adapter.queue_wait_us),
        queue_max_delay_us=float(object_adapter.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            object_adapter.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            object_adapter.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            object_adapter.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_state_object_preflight(
    materialization: PayloadCacheLiveRuntimeAdapterMaterializationPreflight,
) -> PayloadCacheLiveRuntimeAdapterStateObjectPreflight:
    """Build the blocked adapter state-object preflight behind materialization."""

    if not isinstance(
        materialization,
        PayloadCacheLiveRuntimeAdapterMaterializationPreflight,
    ):
        raise TypeError(
            "materialization must be a "
            "PayloadCacheLiveRuntimeAdapterMaterializationPreflight",
        )
    if materialization.present is not True:
        raise ValueError("adapter materialization preflight must be present")
    if (
        materialization.stage
        != "payload_cache_live_runtime_adapter_materialization_preflight"
    ):
        raise ValueError("adapter materialization stage mismatch")
    if materialization.consumes_object_adapter_preflight is not True:
        raise ValueError("adapter materialization must consume object adapter")
    if (
        not isinstance(materialization.object_adapter_status, str)
        or not materialization.object_adapter_status
    ):
        raise TypeError("adapter materialization object_adapter_status invalid")
    expected_materialization_status = (
        "blocked_by_object_adapter_preflight:"
        f"{materialization.object_adapter_status}"
    )
    if materialization.status != expected_materialization_status:
        raise ValueError("adapter materialization status mismatch")
    if materialization.decision != "blocked":
        raise ValueError("adapter materialization preflight must stay blocked")
    if (
        materialization.block_reason
        != "live_runtime_adapter_materialization_preflight_only"
    ):
        raise ValueError("adapter materialization block reason mismatch")
    for field_name in (
        "object_construction_preflight_instantiated",
        "adapter_materialization_preflight_instantiated",
        "runtime_object_adapter_declared",
        "issue_queue_materialization_checked",
        "demand_state_materialization_checked",
        "resident_index_materialization_checked",
        "queue_timing_materialization_checked",
    ):
        if getattr(materialization, field_name) is not True:
            raise ValueError(f"adapter materialization {field_name} must be checked")
    if materialization.live_runtime_instantiated is not False:
        raise ValueError("adapter materialization must not instantiate live runtime")
    if (
        materialization.execution_mode
        != "payload_cache_live_runtime_adapter_materialization_preflight_disabled"
    ):
        raise ValueError("adapter materialization execution mode mismatch")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(materialization, field_name) != 0:
            raise ValueError(f"adapter materialization {field_name} must remain zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(materialization, field_name)) != 0.0:
            raise ValueError(f"adapter materialization {field_name} must remain zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(materialization, field_name) is not False:
            raise ValueError(f"adapter materialization {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(materialization, field_name) != 0:
            raise ValueError(f"adapter materialization {field_name} must remain zero")

    return PayloadCacheLiveRuntimeAdapterStateObjectPreflight(
        present=True,
        stage="payload_cache_live_runtime_adapter_state_object_preflight",
        status=(
            "blocked_by_adapter_materialization_preflight:"
            f"{materialization.status}"
        ),
        consumes_adapter_materialization_preflight=True,
        adapter_materialization_status=str(materialization.status),
        manager_backend=str(materialization.manager_backend),
        manager_runtime_contract=str(materialization.manager_runtime_contract),
        manager_runtime_mode=str(materialization.manager_runtime_mode),
        state_shape_schema=str(materialization.state_shape_schema),
        runtime_adapter_schema=str(materialization.runtime_adapter_schema),
        adapter_state_object_schema="ready_time_payload_cache_adapter_state_v1",
        adapter_materialization_preflight_instantiated=bool(
            materialization.adapter_materialization_preflight_instantiated,
        ),
        adapter_state_object_declared=True,
        issue_queue_state_object_declared=True,
        demand_state_object_declared=True,
        resident_index_state_object_declared=True,
        queue_timing_state_object_declared=True,
        live_runtime_instantiated=False,
        capacity_entries=int(materialization.capacity_entries),
        issue_lead_tokens=int(materialization.issue_lead_tokens),
        queue_deadline_us=float(materialization.queue_deadline_us),
        lookahead_us=float(materialization.lookahead_us),
        queue_batch_size=int(materialization.queue_batch_size),
        resident_count=int(materialization.resident_count),
        issued_fetch_count=int(materialization.issued_fetch_count),
        used_fetch_count=int(materialization.used_fetch_count),
        unused_fetch_count=int(materialization.unused_fetch_count),
        demand_count=int(materialization.demand_count),
        demand_hit_count=int(materialization.demand_hit_count),
        demand_miss_count=int(materialization.demand_miss_count),
        evicted_before_use_count=int(materialization.evicted_before_use_count),
        ready_late_miss_count=int(materialization.ready_late_miss_count),
        late_completion_unused_count=int(materialization.late_completion_unused_count),
        queue_batch_count=int(materialization.queue_batch_count),
        queue_service_us=float(materialization.queue_service_us),
        queue_total_span_us=float(materialization.queue_total_span_us),
        queue_wait_us=float(materialization.queue_wait_us),
        queue_max_delay_us=float(materialization.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            materialization.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            materialization.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            materialization.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_state_validation_preflight(
    state_object: PayloadCacheLiveRuntimeAdapterStateObjectPreflight,
) -> PayloadCacheLiveRuntimeAdapterStateValidationPreflight:
    """Build the blocked state-validation preflight behind state-object checks."""

    if not isinstance(state_object, PayloadCacheLiveRuntimeAdapterStateObjectPreflight):
        raise TypeError(
            "state_object must be a PayloadCacheLiveRuntimeAdapterStateObjectPreflight",
        )
    if state_object.present is not True:
        raise ValueError("adapter state-object preflight must be present")
    if state_object.stage != "payload_cache_live_runtime_adapter_state_object_preflight":
        raise ValueError("adapter state-object stage mismatch")
    if state_object.consumes_adapter_materialization_preflight is not True:
        raise ValueError("adapter state-object must consume materialization")
    if (
        not isinstance(state_object.adapter_materialization_status, str)
        or not state_object.adapter_materialization_status
    ):
        raise TypeError("adapter state-object materialization status invalid")
    if not state_object.adapter_materialization_status.startswith(
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("adapter state-object materialization status chain mismatch")
    expected_state_object_status = (
        "blocked_by_adapter_materialization_preflight:"
        f"{state_object.adapter_materialization_status}"
    )
    if state_object.status != expected_state_object_status:
        raise ValueError("adapter state-object status mismatch")
    if state_object.decision != "blocked":
        raise ValueError("adapter state-object preflight must stay blocked")
    if state_object.block_reason != "live_runtime_adapter_state_object_preflight_only":
        raise ValueError("adapter state-object block reason mismatch")
    for field_name in (
        "adapter_materialization_preflight_instantiated",
        "adapter_state_object_declared",
        "issue_queue_state_object_declared",
        "demand_state_object_declared",
        "resident_index_state_object_declared",
        "queue_timing_state_object_declared",
    ):
        if getattr(state_object, field_name) is not True:
            raise ValueError(f"adapter state-object {field_name} must be declared")
    if state_object.live_runtime_instantiated is not False:
        raise ValueError("adapter state-object must not instantiate live runtime")
    if (
        state_object.execution_mode
        != "payload_cache_live_runtime_adapter_state_object_preflight_disabled"
    ):
        raise ValueError("adapter state-object execution mode mismatch")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(state_object, field_name) != 0:
            raise ValueError(f"adapter state-object {field_name} must remain zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(state_object, field_name)) != 0.0:
            raise ValueError(f"adapter state-object {field_name} must remain zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(state_object, field_name) is not False:
            raise ValueError(f"adapter state-object {field_name} must remain disabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(state_object, field_name) != 0:
            raise ValueError(f"adapter state-object {field_name} must remain zero")

    return PayloadCacheLiveRuntimeAdapterStateValidationPreflight(
        present=True,
        stage="payload_cache_live_runtime_adapter_state_validation_preflight",
        status=f"blocked_by_adapter_state_object_preflight:{state_object.status}",
        consumes_adapter_state_object_preflight=True,
        adapter_state_object_status=str(state_object.status),
        manager_backend=str(state_object.manager_backend),
        manager_runtime_contract=str(state_object.manager_runtime_contract),
        manager_runtime_mode=str(state_object.manager_runtime_mode),
        state_shape_schema=str(state_object.state_shape_schema),
        runtime_adapter_schema=str(state_object.runtime_adapter_schema),
        adapter_state_object_schema=str(state_object.adapter_state_object_schema),
        adapter_state_validation_schema=(
            "ready_time_payload_cache_adapter_state_validation_v1"
        ),
        adapter_state_object_declared=bool(state_object.adapter_state_object_declared),
        adapter_state_validation_preflight_instantiated=True,
        issue_queue_state_object_validated=True,
        demand_state_object_validated=True,
        resident_index_state_object_validated=True,
        queue_timing_state_object_validated=True,
        live_runtime_instantiated=False,
        capacity_entries=int(state_object.capacity_entries),
        issue_lead_tokens=int(state_object.issue_lead_tokens),
        queue_deadline_us=float(state_object.queue_deadline_us),
        lookahead_us=float(state_object.lookahead_us),
        queue_batch_size=int(state_object.queue_batch_size),
        resident_count=int(state_object.resident_count),
        issued_fetch_count=int(state_object.issued_fetch_count),
        used_fetch_count=int(state_object.used_fetch_count),
        unused_fetch_count=int(state_object.unused_fetch_count),
        demand_count=int(state_object.demand_count),
        demand_hit_count=int(state_object.demand_hit_count),
        demand_miss_count=int(state_object.demand_miss_count),
        evicted_before_use_count=int(state_object.evicted_before_use_count),
        ready_late_miss_count=int(state_object.ready_late_miss_count),
        late_completion_unused_count=int(state_object.late_completion_unused_count),
        queue_batch_count=int(state_object.queue_batch_count),
        queue_service_us=float(state_object.queue_service_us),
        queue_total_span_us=float(state_object.queue_total_span_us),
        queue_wait_us=float(state_object.queue_wait_us),
        queue_max_delay_us=float(state_object.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            state_object.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            state_object.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            state_object.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_state_validation_artifact(
    state_validation: PayloadCacheLiveRuntimeAdapterStateValidationPreflight,
) -> PayloadCacheLiveRuntimeAdapterStateValidationArtifact:
    """Build the blocked validated-state artifact behind validation checks."""

    if not isinstance(
        state_validation,
        PayloadCacheLiveRuntimeAdapterStateValidationPreflight,
    ):
        raise TypeError(
            "state_validation must be a "
            "PayloadCacheLiveRuntimeAdapterStateValidationPreflight",
        )
    if state_validation.present is not True:
        raise ValueError("adapter state-validation preflight must be present")
    if (
        state_validation.stage
        != "payload_cache_live_runtime_adapter_state_validation_preflight"
    ):
        raise ValueError("adapter state-validation stage mismatch")
    if state_validation.consumes_adapter_state_object_preflight is not True:
        raise ValueError("adapter state-validation must consume state object")
    if (
        not isinstance(state_validation.adapter_state_object_status, str)
        or not state_validation.adapter_state_object_status
    ):
        raise TypeError("adapter state-validation state-object status invalid")
    if not state_validation.adapter_state_object_status.startswith(
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("adapter state-validation state-object chain mismatch")
    expected_state_validation_status = (
        "blocked_by_adapter_state_object_preflight:"
        f"{state_validation.adapter_state_object_status}"
    )
    if state_validation.status != expected_state_validation_status:
        raise ValueError("adapter state-validation status mismatch")
    if state_validation.decision != "blocked":
        raise ValueError("adapter state-validation preflight must stay blocked")
    if (
        state_validation.block_reason
        != "live_runtime_adapter_state_validation_preflight_only"
    ):
        raise ValueError("adapter state-validation block reason mismatch")
    for field_name in (
        "adapter_state_object_declared",
        "adapter_state_validation_preflight_instantiated",
        "issue_queue_state_object_validated",
        "demand_state_object_validated",
        "resident_index_state_object_validated",
        "queue_timing_state_object_validated",
    ):
        if getattr(state_validation, field_name) is not True:
            raise ValueError(f"adapter state-validation {field_name} must be true")
    if state_validation.live_runtime_instantiated is not False:
        raise ValueError("adapter state-validation must not instantiate live runtime")
    if (
        state_validation.execution_mode
        != "payload_cache_live_runtime_adapter_state_validation_preflight_disabled"
    ):
        raise ValueError("adapter state-validation execution mode mismatch")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(state_validation, field_name) != 0:
            raise ValueError(f"adapter state-validation {field_name} must remain zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(state_validation, field_name)) != 0.0:
            raise ValueError(f"adapter state-validation {field_name} must remain zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(state_validation, field_name) is not False:
            raise ValueError(
                f"adapter state-validation {field_name} must remain disabled",
            )
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(state_validation, field_name) != 0:
            raise ValueError(f"adapter state-validation {field_name} must remain zero")

    return PayloadCacheLiveRuntimeAdapterStateValidationArtifact(
        present=True,
        stage="payload_cache_live_runtime_adapter_state_validation_artifact",
        status=f"blocked_by_adapter_state_validation_preflight:{state_validation.status}",
        consumes_adapter_state_validation_preflight=True,
        adapter_state_validation_status=str(state_validation.status),
        manager_backend=str(state_validation.manager_backend),
        manager_runtime_contract=str(state_validation.manager_runtime_contract),
        manager_runtime_mode=str(state_validation.manager_runtime_mode),
        state_shape_schema=str(state_validation.state_shape_schema),
        runtime_adapter_schema=str(state_validation.runtime_adapter_schema),
        adapter_state_object_schema=str(state_validation.adapter_state_object_schema),
        adapter_state_validation_schema=str(
            state_validation.adapter_state_validation_schema,
        ),
        validated_state_artifact_schema=(
            "ready_time_payload_cache_validated_adapter_state_artifact_v1"
        ),
        adapter_state_validation_preflight_instantiated=bool(
            state_validation.adapter_state_validation_preflight_instantiated,
        ),
        adapter_state_validation_artifact_instantiated=True,
        issue_queue_state_object_ready_for_runtime_adapter=True,
        demand_state_object_ready_for_runtime_adapter=True,
        resident_index_state_object_ready_for_runtime_adapter=True,
        queue_timing_state_object_ready_for_runtime_adapter=True,
        live_runtime_instantiated=False,
        capacity_entries=int(state_validation.capacity_entries),
        issue_lead_tokens=int(state_validation.issue_lead_tokens),
        queue_deadline_us=float(state_validation.queue_deadline_us),
        lookahead_us=float(state_validation.lookahead_us),
        queue_batch_size=int(state_validation.queue_batch_size),
        resident_count=int(state_validation.resident_count),
        issued_fetch_count=int(state_validation.issued_fetch_count),
        used_fetch_count=int(state_validation.used_fetch_count),
        unused_fetch_count=int(state_validation.unused_fetch_count),
        demand_count=int(state_validation.demand_count),
        demand_hit_count=int(state_validation.demand_hit_count),
        demand_miss_count=int(state_validation.demand_miss_count),
        evicted_before_use_count=int(state_validation.evicted_before_use_count),
        ready_late_miss_count=int(state_validation.ready_late_miss_count),
        late_completion_unused_count=int(state_validation.late_completion_unused_count),
        queue_batch_count=int(state_validation.queue_batch_count),
        queue_service_us=float(state_validation.queue_service_us),
        queue_total_span_us=float(state_validation.queue_total_span_us),
        queue_wait_us=float(state_validation.queue_wait_us),
        queue_max_delay_us=float(state_validation.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            state_validation.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            state_validation.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            state_validation.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_instantiation_canary(
    artifact: PayloadCacheLiveRuntimeAdapterStateValidationArtifact,
) -> PayloadCacheLiveRuntimeAdapterInstantiationCanary:
    """Build the blocked canary for resolving the future adapter entry."""

    if not isinstance(artifact, PayloadCacheLiveRuntimeAdapterStateValidationArtifact):
        raise TypeError(
            "artifact must be a PayloadCacheLiveRuntimeAdapterStateValidationArtifact",
        )
    if artifact.present is not True:
        raise ValueError("adapter state-validation artifact must be present")
    if artifact.stage != "payload_cache_live_runtime_adapter_state_validation_artifact":
        raise ValueError("adapter state-validation artifact stage mismatch")
    if artifact.consumes_adapter_state_validation_preflight is not True:
        raise ValueError("adapter state-validation artifact must consume validation")
    if (
        not isinstance(artifact.adapter_state_validation_status, str)
        or not artifact.adapter_state_validation_status
    ):
        raise TypeError("adapter state-validation artifact status invalid")
    if not artifact.adapter_state_validation_status.startswith(
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("adapter state-validation artifact status chain mismatch")
    expected_artifact_status = (
        "blocked_by_adapter_state_validation_preflight:"
        f"{artifact.adapter_state_validation_status}"
    )
    if artifact.status != expected_artifact_status:
        raise ValueError("adapter state-validation artifact status mismatch")
    if artifact.decision != "blocked":
        raise ValueError("adapter state-validation artifact must stay blocked")
    if artifact.block_reason != "live_runtime_adapter_state_validation_artifact_only":
        raise ValueError("adapter state-validation artifact block reason mismatch")
    if (
        artifact.execution_mode
        != "payload_cache_live_runtime_adapter_state_validation_artifact_disabled"
    ):
        raise ValueError("adapter state-validation artifact execution mode mismatch")
    for field_name in (
        "adapter_state_validation_preflight_instantiated",
        "adapter_state_validation_artifact_instantiated",
        "issue_queue_state_object_ready_for_runtime_adapter",
        "demand_state_object_ready_for_runtime_adapter",
        "resident_index_state_object_ready_for_runtime_adapter",
        "queue_timing_state_object_ready_for_runtime_adapter",
    ):
        if getattr(artifact, field_name) is not True:
            raise ValueError(f"adapter state-validation artifact {field_name} invalid")
    if artifact.live_runtime_instantiated is not False:
        raise ValueError("adapter state-validation artifact must not instantiate runtime")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(artifact, field_name) != 0:
            raise ValueError(f"adapter state-validation artifact {field_name} must be zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(artifact, field_name)) != 0.0:
            raise ValueError(f"adapter state-validation artifact {field_name} must be zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(artifact, field_name) is not False:
            raise ValueError(f"adapter state-validation artifact {field_name} enabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(artifact, field_name) != 0:
            raise ValueError(f"adapter state-validation artifact {field_name} must be zero")

    return PayloadCacheLiveRuntimeAdapterInstantiationCanary(
        present=True,
        stage="payload_cache_live_runtime_adapter_instantiation_canary",
        status=f"blocked_by_state_validation_artifact:{artifact.status}",
        consumes_state_validation_artifact=True,
        state_validation_artifact_status=str(artifact.status),
        manager_backend=str(artifact.manager_backend),
        manager_runtime_contract=str(artifact.manager_runtime_contract),
        manager_runtime_mode=str(artifact.manager_runtime_mode),
        validated_state_artifact_schema=str(artifact.validated_state_artifact_schema),
        runtime_adapter_instantiation_schema=(
            "ready_time_payload_cache_runtime_adapter_instantiation_v1"
        ),
        adapter_factory_declared=True,
        adapter_constructor_resolved=True,
        adapter_instance_created=False,
        live_runtime_instantiated=False,
        capacity_entries=int(artifact.capacity_entries),
        issue_lead_tokens=int(artifact.issue_lead_tokens),
        queue_deadline_us=float(artifact.queue_deadline_us),
        lookahead_us=float(artifact.lookahead_us),
        queue_batch_size=int(artifact.queue_batch_size),
        resident_count=int(artifact.resident_count),
        issued_fetch_count=int(artifact.issued_fetch_count),
        used_fetch_count=int(artifact.used_fetch_count),
        unused_fetch_count=int(artifact.unused_fetch_count),
        demand_count=int(artifact.demand_count),
        demand_hit_count=int(artifact.demand_hit_count),
        demand_miss_count=int(artifact.demand_miss_count),
        evicted_before_use_count=int(artifact.evicted_before_use_count),
        ready_late_miss_count=int(artifact.ready_late_miss_count),
        late_completion_unused_count=int(artifact.late_completion_unused_count),
        queue_batch_count=int(artifact.queue_batch_count),
        queue_service_us=float(artifact.queue_service_us),
        queue_total_span_us=float(artifact.queue_total_span_us),
        queue_wait_us=float(artifact.queue_wait_us),
        queue_max_delay_us=float(artifact.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            artifact.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            artifact.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            artifact.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_constructor_binding_preflight(
    canary: PayloadCacheLiveRuntimeAdapterInstantiationCanary,
) -> PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight:
    """Bind future adapter constructor inputs without creating an instance."""

    if not isinstance(canary, PayloadCacheLiveRuntimeAdapterInstantiationCanary):
        raise TypeError(
            "canary must be a PayloadCacheLiveRuntimeAdapterInstantiationCanary",
        )
    if canary.present is not True:
        raise ValueError("adapter instantiation canary must be present")
    if canary.stage != "payload_cache_live_runtime_adapter_instantiation_canary":
        raise ValueError("adapter instantiation canary stage mismatch")
    if canary.consumes_state_validation_artifact is not True:
        raise ValueError("adapter instantiation canary must consume artifact")
    if (
        not isinstance(canary.state_validation_artifact_status, str)
        or not canary.state_validation_artifact_status
    ):
        raise TypeError("adapter instantiation canary artifact status invalid")
    if not canary.state_validation_artifact_status.startswith(
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("adapter instantiation canary artifact status chain mismatch")
    expected_canary_status = (
        "blocked_by_state_validation_artifact:"
        f"{canary.state_validation_artifact_status}"
    )
    if canary.status != expected_canary_status:
        raise ValueError("adapter instantiation canary status mismatch")
    if canary.decision != "blocked":
        raise ValueError("adapter instantiation canary must stay blocked")
    if canary.block_reason != "live_runtime_adapter_instantiation_canary_only":
        raise ValueError("adapter instantiation canary block reason mismatch")
    if (
        canary.execution_mode
        != "payload_cache_live_runtime_adapter_instantiation_canary_disabled"
    ):
        raise ValueError("adapter instantiation canary execution mode mismatch")
    for field_name in (
        "adapter_factory_declared",
        "adapter_constructor_resolved",
    ):
        if getattr(canary, field_name) is not True:
            raise ValueError(f"adapter instantiation canary {field_name} invalid")
    if canary.adapter_instance_created is not False:
        raise ValueError("adapter instantiation canary must not create instance")
    if canary.live_runtime_instantiated is not False:
        raise ValueError("adapter instantiation canary must not instantiate runtime")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(canary, field_name) != 0:
            raise ValueError(f"adapter instantiation canary {field_name} must be zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(canary, field_name)) != 0.0:
            raise ValueError(f"adapter instantiation canary {field_name} must be zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(canary, field_name) is not False:
            raise ValueError(f"adapter instantiation canary {field_name} enabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(canary, field_name) != 0:
            raise ValueError(f"adapter instantiation canary {field_name} must be zero")

    return PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight(
        present=True,
        stage="payload_cache_live_runtime_adapter_constructor_binding_preflight",
        status=f"blocked_by_instantiation_canary:{canary.status}",
        consumes_instantiation_canary=True,
        instantiation_canary_status=str(canary.status),
        manager_backend=str(canary.manager_backend),
        manager_runtime_contract=str(canary.manager_runtime_contract),
        manager_runtime_mode=str(canary.manager_runtime_mode),
        runtime_adapter_instantiation_schema=str(
            canary.runtime_adapter_instantiation_schema,
        ),
        constructor_binding_schema=(
            "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
        ),
        adapter_factory_declared=bool(canary.adapter_factory_declared),
        adapter_constructor_resolved=bool(canary.adapter_constructor_resolved),
        constructor_inputs_bound=True,
        binds_validated_state_artifact=True,
        binds_queue_budget_parameters=True,
        binds_shifted_issue_accounting=True,
        adapter_instance_created=False,
        live_runtime_instantiated=False,
        capacity_entries=int(canary.capacity_entries),
        issue_lead_tokens=int(canary.issue_lead_tokens),
        queue_deadline_us=float(canary.queue_deadline_us),
        lookahead_us=float(canary.lookahead_us),
        queue_batch_size=int(canary.queue_batch_size),
        resident_count=int(canary.resident_count),
        issued_fetch_count=int(canary.issued_fetch_count),
        used_fetch_count=int(canary.used_fetch_count),
        unused_fetch_count=int(canary.unused_fetch_count),
        demand_count=int(canary.demand_count),
        demand_hit_count=int(canary.demand_hit_count),
        demand_miss_count=int(canary.demand_miss_count),
        evicted_before_use_count=int(canary.evicted_before_use_count),
        ready_late_miss_count=int(canary.ready_late_miss_count),
        late_completion_unused_count=int(canary.late_completion_unused_count),
        queue_batch_count=int(canary.queue_batch_count),
        queue_service_us=float(canary.queue_service_us),
        queue_total_span_us=float(canary.queue_total_span_us),
        queue_wait_us=float(canary.queue_wait_us),
        queue_max_delay_us=float(canary.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            canary.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            canary.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            canary.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_instance_construction_plan(
    binding: PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight,
) -> PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan:
    """Plan future adapter instance construction without creating an instance."""

    if not isinstance(binding, PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight):
        raise TypeError(
            "binding must be a "
            "PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight",
        )
    if binding.present is not True:
        raise ValueError("adapter constructor-binding preflight must be present")
    if binding.stage != "payload_cache_live_runtime_adapter_constructor_binding_preflight":
        raise ValueError("adapter constructor-binding preflight stage mismatch")
    if binding.consumes_instantiation_canary is not True:
        raise ValueError("adapter constructor-binding preflight must consume canary")
    if (
        not isinstance(binding.instantiation_canary_status, str)
        or not binding.instantiation_canary_status
    ):
        raise TypeError("adapter constructor-binding canary status invalid")
    if not binding.instantiation_canary_status.startswith(
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("adapter constructor-binding canary status chain mismatch")
    expected_binding_status = (
        "blocked_by_instantiation_canary:"
        f"{binding.instantiation_canary_status}"
    )
    if binding.status != expected_binding_status:
        raise ValueError("adapter constructor-binding preflight status mismatch")
    if binding.decision != "blocked":
        raise ValueError("adapter constructor-binding preflight must stay blocked")
    if binding.block_reason != "live_runtime_adapter_constructor_binding_preflight_only":
        raise ValueError("adapter constructor-binding preflight block reason mismatch")
    if (
        binding.execution_mode
        != "payload_cache_live_runtime_adapter_constructor_binding_preflight_disabled"
    ):
        raise ValueError("adapter constructor-binding preflight execution mode mismatch")
    for field_name in (
        "adapter_factory_declared",
        "adapter_constructor_resolved",
        "constructor_inputs_bound",
        "binds_validated_state_artifact",
        "binds_queue_budget_parameters",
        "binds_shifted_issue_accounting",
    ):
        if getattr(binding, field_name) is not True:
            raise ValueError(f"adapter constructor-binding {field_name} invalid")
    if binding.adapter_instance_created is not False:
        raise ValueError("adapter constructor-binding must not create instance")
    if binding.live_runtime_instantiated is not False:
        raise ValueError("adapter constructor-binding must not instantiate runtime")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(binding, field_name) != 0:
            raise ValueError(f"adapter constructor-binding {field_name} must be zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(binding, field_name)) != 0.0:
            raise ValueError(f"adapter constructor-binding {field_name} must be zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(binding, field_name) is not False:
            raise ValueError(f"adapter constructor-binding {field_name} enabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(binding, field_name) != 0:
            raise ValueError(f"adapter constructor-binding {field_name} must be zero")

    return PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan(
        present=True,
        stage="payload_cache_live_runtime_adapter_instance_construction_plan",
        status=f"blocked_by_constructor_binding_preflight:{binding.status}",
        consumes_constructor_binding_preflight=True,
        constructor_binding_status=str(binding.status),
        manager_backend=str(binding.manager_backend),
        manager_runtime_contract=str(binding.manager_runtime_contract),
        manager_runtime_mode=str(binding.manager_runtime_mode),
        constructor_binding_schema=str(binding.constructor_binding_schema),
        instance_construction_plan_schema=(
            "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
        ),
        constructor_inputs_bound=bool(binding.constructor_inputs_bound),
        construction_plan_sealed=True,
        adapter_constructor_call_prepared=True,
        adapter_instance_construction_planned=True,
        adapter_instance_created=False,
        live_runtime_instantiated=False,
        capacity_entries=int(binding.capacity_entries),
        issue_lead_tokens=int(binding.issue_lead_tokens),
        queue_deadline_us=float(binding.queue_deadline_us),
        lookahead_us=float(binding.lookahead_us),
        queue_batch_size=int(binding.queue_batch_size),
        resident_count=int(binding.resident_count),
        issued_fetch_count=int(binding.issued_fetch_count),
        used_fetch_count=int(binding.used_fetch_count),
        unused_fetch_count=int(binding.unused_fetch_count),
        demand_count=int(binding.demand_count),
        demand_hit_count=int(binding.demand_hit_count),
        demand_miss_count=int(binding.demand_miss_count),
        evicted_before_use_count=int(binding.evicted_before_use_count),
        ready_late_miss_count=int(binding.ready_late_miss_count),
        late_completion_unused_count=int(binding.late_completion_unused_count),
        queue_batch_count=int(binding.queue_batch_count),
        queue_service_us=float(binding.queue_service_us),
        queue_total_span_us=float(binding.queue_total_span_us),
        queue_wait_us=float(binding.queue_wait_us),
        queue_max_delay_us=float(binding.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            binding.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            binding.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            binding.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_object_shell_evidence(
    plan: PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan,
) -> PayloadCacheLiveRuntimeAdapterObjectShellEvidence:
    """Construct a disabled adapter object shell and return no-op evidence."""

    if not isinstance(plan, PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan):
        raise TypeError(
            "plan must be a PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan",
        )
    if plan.present is not True:
        raise ValueError("adapter instance-construction plan must be present")
    if plan.stage != "payload_cache_live_runtime_adapter_instance_construction_plan":
        raise ValueError("adapter instance-construction plan stage mismatch")
    if plan.consumes_constructor_binding_preflight is not True:
        raise ValueError("adapter instance-construction plan must consume binding")
    if (
        not isinstance(plan.constructor_binding_status, str)
        or not plan.constructor_binding_status
    ):
        raise TypeError("adapter instance-construction binding status invalid")
    if not plan.constructor_binding_status.startswith(
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("adapter instance-construction binding status chain mismatch")
    expected_plan_status = (
        "blocked_by_constructor_binding_preflight:"
        f"{plan.constructor_binding_status}"
    )
    if plan.status != expected_plan_status:
        raise ValueError("adapter instance-construction plan status mismatch")
    if plan.decision != "blocked":
        raise ValueError("adapter instance-construction plan must stay blocked")
    if plan.block_reason != "live_runtime_adapter_instance_construction_plan_only":
        raise ValueError("adapter instance-construction plan block reason mismatch")
    if (
        plan.execution_mode
        != "payload_cache_live_runtime_adapter_instance_construction_plan_disabled"
    ):
        raise ValueError("adapter instance-construction plan execution mode mismatch")
    for field_name in (
        "constructor_inputs_bound",
        "construction_plan_sealed",
        "adapter_constructor_call_prepared",
        "adapter_instance_construction_planned",
    ):
        if getattr(plan, field_name) is not True:
            raise ValueError(f"adapter instance-construction plan {field_name} invalid")
    if plan.adapter_instance_created is not False:
        raise ValueError("adapter instance-construction plan must not create instance")
    if plan.live_runtime_instantiated is not False:
        raise ValueError("adapter instance-construction plan must not instantiate runtime")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(plan, field_name) != 0:
            raise ValueError(f"adapter instance-construction plan {field_name} must be zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(plan, field_name)) != 0.0:
            raise ValueError(f"adapter instance-construction plan {field_name} must be zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(plan, field_name) is not False:
            raise ValueError(f"adapter instance-construction plan {field_name} enabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(plan, field_name) != 0:
            raise ValueError(f"adapter instance-construction plan {field_name} must be zero")

    shell = PayloadCacheRuntimeAdapterShell(
        capacity=int(plan.capacity_entries),
        service_us_per_issue=0.0,
        service_us_per_batch=0.0,
        queue_batch_size=int(plan.queue_batch_size),
        queue_deadline_us=float(plan.queue_deadline_us),
        enabled=False,
    )
    snapshot = shell.snapshot()

    return PayloadCacheLiveRuntimeAdapterObjectShellEvidence(
        present=True,
        stage="payload_cache_live_runtime_adapter_object_shell_evidence",
        status=f"blocked_by_instance_construction_plan:{plan.status}",
        consumes_instance_construction_plan=True,
        instance_construction_plan_status=str(plan.status),
        manager_backend=str(plan.manager_backend),
        manager_runtime_contract=str(plan.manager_runtime_contract),
        manager_runtime_mode=str(plan.manager_runtime_mode),
        instance_construction_plan_schema=str(plan.instance_construction_plan_schema),
        adapter_object_shell_created=True,
        disabled_adapter_shell_snapshot_created=True,
        shell_enabled=bool(snapshot.enabled),
        adapter_instance_created=False,
        live_runtime_instantiated=False,
        capacity_entries=int(snapshot.capacity),
        issue_lead_tokens=int(plan.issue_lead_tokens),
        queue_deadline_us=float(snapshot.queue_deadline_us),
        lookahead_us=float(plan.lookahead_us),
        queue_batch_size=int(snapshot.queue_batch_size),
        resident_count=int(snapshot.resident_count),
        issued_fetch_count=int(snapshot.issued_fetch_count),
        used_fetch_count=int(snapshot.used_fetch_count),
        unused_fetch_count=int(plan.unused_fetch_count),
        demand_count=int(snapshot.demand_count),
        demand_hit_count=int(snapshot.demand_hit_count),
        demand_miss_count=int(snapshot.demand_miss_count),
        evicted_before_use_count=int(plan.evicted_before_use_count),
        ready_late_miss_count=int(snapshot.ready_late_miss_count),
        late_completion_unused_count=int(plan.late_completion_unused_count),
        queue_batch_count=int(plan.queue_batch_count),
        queue_service_us=float(plan.queue_service_us),
        queue_total_span_us=float(plan.queue_total_span_us),
        queue_wait_us=float(plan.queue_wait_us),
        queue_max_delay_us=float(plan.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            plan.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            plan.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            plan.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_operation_rejection_canary(
    evidence: PayloadCacheLiveRuntimeAdapterObjectShellEvidence,
) -> PayloadCacheLiveRuntimeAdapterOperationRejectionCanary:
    """Call disabled adapter operations and verify they reject without effects."""

    if not isinstance(evidence, PayloadCacheLiveRuntimeAdapterObjectShellEvidence):
        raise TypeError(
            "evidence must be a PayloadCacheLiveRuntimeAdapterObjectShellEvidence",
        )
    if evidence.present is not True:
        raise ValueError("adapter object-shell evidence must be present")
    if evidence.stage != "payload_cache_live_runtime_adapter_object_shell_evidence":
        raise ValueError("adapter object-shell evidence stage mismatch")
    if evidence.consumes_instance_construction_plan is not True:
        raise ValueError("adapter object-shell evidence must consume construction plan")
    if (
        not isinstance(evidence.instance_construction_plan_status, str)
        or not evidence.instance_construction_plan_status
    ):
        raise TypeError("adapter object-shell plan status invalid")
    if not evidence.instance_construction_plan_status.startswith(
        "blocked_by_constructor_binding_preflight:"
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("adapter object-shell plan status chain mismatch")
    expected_evidence_status = (
        "blocked_by_instance_construction_plan:"
        f"{evidence.instance_construction_plan_status}"
    )
    if evidence.status != expected_evidence_status:
        raise ValueError("adapter object-shell evidence status mismatch")
    if evidence.decision != "blocked":
        raise ValueError("adapter object-shell evidence must stay blocked")
    if evidence.block_reason != "live_runtime_adapter_object_shell_evidence_only":
        raise ValueError("adapter object-shell evidence block reason mismatch")
    if (
        evidence.execution_mode
        != "payload_cache_live_runtime_adapter_object_shell_evidence_disabled"
    ):
        raise ValueError("adapter object-shell evidence execution mode mismatch")
    if evidence.adapter_object_shell_created is not True:
        raise ValueError("adapter object-shell must be created")
    if evidence.disabled_adapter_shell_snapshot_created is not True:
        raise ValueError("adapter object-shell snapshot must be created")
    if evidence.shell_enabled is not False:
        raise ValueError("adapter object-shell must remain disabled")
    if evidence.adapter_instance_created is not False:
        raise ValueError("adapter object-shell must not create adapter instance")
    if evidence.live_runtime_instantiated is not False:
        raise ValueError("adapter object-shell must not instantiate live runtime")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(evidence, field_name) != 0:
            raise ValueError(f"adapter object-shell evidence {field_name} must be zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(evidence, field_name)) != 0.0:
            raise ValueError(f"adapter object-shell evidence {field_name} must be zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(evidence, field_name) is not False:
            raise ValueError(f"adapter object-shell evidence {field_name} enabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(evidence, field_name) != 0:
            raise ValueError(f"adapter object-shell evidence {field_name} must be zero")

    shell = PayloadCacheRuntimeAdapterShell(
        capacity=int(evidence.capacity_entries),
        service_us_per_issue=0.0,
        service_us_per_batch=0.0,
        queue_batch_size=int(evidence.queue_batch_size),
        queue_deadline_us=float(evidence.queue_deadline_us),
        enabled=False,
    )

    issue_prefetch_rejected = False
    try:
        shell.issue_prefetch(0, 0, arrival_us=0.0)
    except RuntimeError:
        issue_prefetch_rejected = True

    demand_rejected = False
    try:
        shell.demand(0, 0, arrival_us=0.0)
    except RuntimeError:
        demand_rejected = True

    if not issue_prefetch_rejected:
        raise ValueError("disabled adapter shell must reject issue_prefetch")
    if not demand_rejected:
        raise ValueError("disabled adapter shell must reject demand")

    snapshot = shell.snapshot()

    return PayloadCacheLiveRuntimeAdapterOperationRejectionCanary(
        present=True,
        stage="payload_cache_live_runtime_adapter_operation_rejection_canary",
        status=f"blocked_by_object_shell_evidence:{evidence.status}",
        consumes_object_shell_evidence=True,
        object_shell_evidence_status=str(evidence.status),
        manager_backend=str(evidence.manager_backend),
        manager_runtime_contract=str(evidence.manager_runtime_contract),
        manager_runtime_mode=str(evidence.manager_runtime_mode),
        operation_rejection_schema=(
            "ready_time_payload_cache_runtime_adapter_operation_rejection_canary_v1"
        ),
        adapter_object_shell_created=True,
        operation_rejection_canary_ran=True,
        issue_prefetch_rejected=issue_prefetch_rejected,
        demand_rejected=demand_rejected,
        shell_enabled=bool(snapshot.enabled),
        adapter_instance_created=False,
        live_runtime_instantiated=False,
        capacity_entries=int(snapshot.capacity),
        issue_lead_tokens=int(evidence.issue_lead_tokens),
        queue_deadline_us=float(snapshot.queue_deadline_us),
        lookahead_us=float(evidence.lookahead_us),
        queue_batch_size=int(snapshot.queue_batch_size),
        resident_count=int(snapshot.resident_count),
        issued_fetch_count=int(snapshot.issued_fetch_count),
        used_fetch_count=int(snapshot.used_fetch_count),
        unused_fetch_count=int(evidence.unused_fetch_count),
        demand_count=int(snapshot.demand_count),
        demand_hit_count=int(snapshot.demand_hit_count),
        demand_miss_count=int(snapshot.demand_miss_count),
        evicted_before_use_count=int(evidence.evicted_before_use_count),
        ready_late_miss_count=int(snapshot.ready_late_miss_count),
        late_completion_unused_count=int(evidence.late_completion_unused_count),
        queue_batch_count=int(evidence.queue_batch_count),
        queue_service_us=float(evidence.queue_service_us),
        queue_total_span_us=float(evidence.queue_total_span_us),
        queue_wait_us=float(evidence.queue_wait_us),
        queue_max_delay_us=float(evidence.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            evidence.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            evidence.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            evidence.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(
    canary: PayloadCacheLiveRuntimeAdapterOperationRejectionCanary,
) -> PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary:
    """Run a payloadless adapter issue/demand sequence against a private manager."""

    if not isinstance(canary, PayloadCacheLiveRuntimeAdapterOperationRejectionCanary):
        raise TypeError(
            "canary must be a PayloadCacheLiveRuntimeAdapterOperationRejectionCanary",
        )
    if canary.present is not True:
        raise ValueError("operation-rejection canary must be present")
    if canary.stage != "payload_cache_live_runtime_adapter_operation_rejection_canary":
        raise ValueError("operation-rejection canary stage mismatch")
    if canary.consumes_object_shell_evidence is not True:
        raise ValueError("operation-rejection canary must consume object shell")
    if (
        not isinstance(canary.object_shell_evidence_status, str)
        or not canary.object_shell_evidence_status
    ):
        raise TypeError("operation-rejection object-shell status invalid")
    if not canary.object_shell_evidence_status.startswith(
        "blocked_by_instance_construction_plan:"
        "blocked_by_constructor_binding_preflight:"
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("operation-rejection object-shell status chain mismatch")
    expected_canary_status = (
        "blocked_by_object_shell_evidence:"
        f"{canary.object_shell_evidence_status}"
    )
    if canary.status != expected_canary_status:
        raise ValueError("operation-rejection canary status mismatch")
    if canary.decision != "blocked":
        raise ValueError("operation-rejection canary must stay blocked")
    if canary.block_reason != "live_runtime_adapter_operation_rejection_canary_only":
        raise ValueError("operation-rejection canary block reason mismatch")
    if (
        canary.execution_mode
        != "payload_cache_live_runtime_adapter_operation_rejection_canary_disabled"
    ):
        raise ValueError("operation-rejection canary execution mode mismatch")
    for field_name in (
        "adapter_object_shell_created",
        "operation_rejection_canary_ran",
        "issue_prefetch_rejected",
        "demand_rejected",
    ):
        if getattr(canary, field_name) is not True:
            raise ValueError(f"operation-rejection canary {field_name} invalid")
    if canary.shell_enabled is not False:
        raise ValueError("operation-rejection shell must remain disabled")
    if canary.adapter_instance_created is not False:
        raise ValueError("operation-rejection canary must not create adapter instance")
    if canary.live_runtime_instantiated is not False:
        raise ValueError("operation-rejection canary must not instantiate live runtime")
    for field_name in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        if getattr(canary, field_name) != 0:
            raise ValueError(f"operation-rejection canary {field_name} must be zero")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(canary, field_name)) != 0.0:
            raise ValueError(f"operation-rejection canary {field_name} must be zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(canary, field_name) is not False:
            raise ValueError(f"operation-rejection canary {field_name} enabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(canary, field_name) != 0:
            raise ValueError(f"operation-rejection canary {field_name} must be zero")

    adapter = PayloadCacheRuntimeAdapterAccountingDryRun(
        capacity=int(canary.capacity_entries),
        service_us_per_issue=0.0,
        service_us_per_batch=0.0,
        queue_batch_size=int(canary.queue_batch_size),
        queue_deadline_us=float(canary.queue_deadline_us),
    )
    issue_accepted = adapter.issue_prefetch(0, 0, arrival_us=0.0)
    duplicate_suppressed = not adapter.issue_prefetch(0, 0, arrival_us=1.0)
    demand_hit = adapter.demand(0, 0, arrival_us=2.0)
    snapshot = adapter.snapshot()

    return PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary(
        present=True,
        stage="payload_cache_live_runtime_adapter_accounting_dry_run_canary",
        status=f"blocked_by_operation_rejection_canary:{canary.status}",
        consumes_operation_rejection_canary=True,
        operation_rejection_canary_status=str(canary.status),
        manager_backend=str(canary.manager_backend),
        manager_runtime_contract=str(canary.manager_runtime_contract),
        manager_runtime_mode=str(canary.manager_runtime_mode),
        accounting_dry_run_schema=(
            "ready_time_payload_cache_runtime_adapter_accounting_dry_run_canary_v1"
        ),
        accounting_dry_run_adapter_created=True,
        accounting_dry_run_operations_ran=True,
        accounting_dry_run_enabled=bool(snapshot.accounting_dry_run_enabled),
        issue_prefetch_accepted=issue_accepted,
        duplicate_issue_suppressed=duplicate_suppressed,
        demand_hit=demand_hit,
        live_adapter_instance_created=False,
        live_runtime_instantiated=False,
        capacity_entries=int(snapshot.capacity),
        issue_lead_tokens=int(canary.issue_lead_tokens),
        queue_deadline_us=float(snapshot.queue_deadline_us),
        lookahead_us=float(canary.lookahead_us),
        queue_batch_size=int(snapshot.queue_batch_size),
        resident_count=int(snapshot.resident_count),
        issued_fetch_count=int(snapshot.issued_fetch_count),
        used_fetch_count=int(snapshot.used_fetch_count),
        unused_fetch_count=int(snapshot.unused_fetch_count),
        demand_count=int(snapshot.demand_count),
        demand_hit_count=int(snapshot.demand_hit_count),
        demand_miss_count=int(snapshot.demand_miss_count),
        evicted_before_use_count=int(snapshot.evicted_before_use_count),
        ready_late_miss_count=int(snapshot.ready_late_miss_count),
        late_completion_unused_count=int(snapshot.late_completion_unused_count),
        queue_batch_count=int(snapshot.queue_batch_count),
        queue_service_us=float(snapshot.queue_service_us),
        queue_total_span_us=float(snapshot.queue_total_span_us),
        queue_wait_us=float(snapshot.queue_wait_us),
        queue_max_delay_us=float(snapshot.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            canary.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            canary.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            canary.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(
    canary: PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary,
) -> PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary:
    """Run a payloadless adapter sequence with both a hit and a miss outcome."""

    if not isinstance(canary, PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary):
        raise TypeError(
            "canary must be a PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary",
        )
    if canary.present is not True:
        raise ValueError("accounting dry-run canary must be present")
    if canary.stage != "payload_cache_live_runtime_adapter_accounting_dry_run_canary":
        raise ValueError("accounting dry-run canary stage mismatch")
    if canary.consumes_operation_rejection_canary is not True:
        raise ValueError("accounting dry-run canary must consume rejection canary")
    if (
        not isinstance(canary.operation_rejection_canary_status, str)
        or not canary.operation_rejection_canary_status
    ):
        raise TypeError("accounting dry-run rejection status invalid")
    if not canary.operation_rejection_canary_status.startswith(
        "blocked_by_object_shell_evidence:"
        "blocked_by_instance_construction_plan:"
        "blocked_by_constructor_binding_preflight:"
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("accounting dry-run rejection status chain mismatch")
    expected_canary_status = (
        "blocked_by_operation_rejection_canary:"
        f"{canary.operation_rejection_canary_status}"
    )
    if canary.status != expected_canary_status:
        raise ValueError("accounting dry-run canary status mismatch")
    if canary.decision != "blocked":
        raise ValueError("accounting dry-run canary must stay blocked")
    if canary.block_reason != "live_runtime_adapter_accounting_dry_run_canary_only":
        raise ValueError("accounting dry-run canary block reason mismatch")
    if (
        canary.execution_mode
        != "payload_cache_live_runtime_adapter_accounting_dry_run_canary_payloadless"
    ):
        raise ValueError("accounting dry-run canary execution mode mismatch")
    for field_name in (
        "accounting_dry_run_adapter_created",
        "accounting_dry_run_operations_ran",
        "accounting_dry_run_enabled",
        "issue_prefetch_accepted",
        "duplicate_issue_suppressed",
        "demand_hit",
    ):
        if getattr(canary, field_name) is not True:
            raise ValueError(f"accounting dry-run canary {field_name} invalid")
    if canary.live_adapter_instance_created is not False:
        raise ValueError("accounting dry-run canary must not create live adapter")
    if canary.live_runtime_instantiated is not False:
        raise ValueError("accounting dry-run canary must not instantiate live runtime")
    expected_counts = {
        "resident_count": 1,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 1,
        "demand_hit_count": 1,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
    }
    for field_name, expected in expected_counts.items():
        if getattr(canary, field_name) != expected:
            raise ValueError(f"accounting dry-run canary {field_name} mismatch")
    for field_name in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if float(getattr(canary, field_name)) != 0.0:
            raise ValueError(f"accounting dry-run canary {field_name} must be zero")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(canary, field_name) is not False:
            raise ValueError(f"accounting dry-run canary {field_name} enabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(canary, field_name) != 0:
            raise ValueError(f"accounting dry-run canary {field_name} must be zero")

    adapter = PayloadCacheRuntimeAdapterAccountingDryRun(
        capacity=int(canary.capacity_entries),
        service_us_per_issue=0.0,
        service_us_per_batch=0.0,
        queue_batch_size=int(canary.queue_batch_size),
        queue_deadline_us=float(canary.queue_deadline_us),
    )
    issue_accepted = adapter.issue_prefetch(0, 0, arrival_us=0.0)
    duplicate_suppressed = not adapter.issue_prefetch(0, 0, arrival_us=1.0)
    prefetched_demand_hit = adapter.demand(0, 0, arrival_us=2.0)
    unprefetched_demand_hit = adapter.demand(0, 1, arrival_us=3.0)
    snapshot = adapter.snapshot()

    return PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary(
        present=True,
        stage="payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary",
        status=f"blocked_by_accounting_dry_run_canary:{canary.status}",
        consumes_accounting_dry_run_canary=True,
        accounting_dry_run_canary_status=str(canary.status),
        manager_backend=str(canary.manager_backend),
        manager_runtime_contract=str(canary.manager_runtime_contract),
        manager_runtime_mode=str(canary.manager_runtime_mode),
        mixed_outcome_schema=(
            "ready_time_payload_cache_runtime_adapter_mixed_outcome_dry_run_canary_v1"
        ),
        mixed_outcome_adapter_created=True,
        mixed_outcome_operations_ran=True,
        accounting_dry_run_enabled=bool(snapshot.accounting_dry_run_enabled),
        issue_prefetch_accepted=issue_accepted,
        duplicate_issue_suppressed=duplicate_suppressed,
        prefetched_demand_hit=prefetched_demand_hit,
        unprefetched_demand_hit=unprefetched_demand_hit,
        unprefetched_demand_missed=not unprefetched_demand_hit,
        live_adapter_instance_created=False,
        live_runtime_instantiated=False,
        capacity_entries=int(snapshot.capacity),
        issue_lead_tokens=int(canary.issue_lead_tokens),
        queue_deadline_us=float(snapshot.queue_deadline_us),
        lookahead_us=float(canary.lookahead_us),
        queue_batch_size=int(snapshot.queue_batch_size),
        resident_count=int(snapshot.resident_count),
        issued_fetch_count=int(snapshot.issued_fetch_count),
        used_fetch_count=int(snapshot.used_fetch_count),
        unused_fetch_count=int(snapshot.unused_fetch_count),
        demand_count=int(snapshot.demand_count),
        demand_hit_count=int(snapshot.demand_hit_count),
        demand_miss_count=int(snapshot.demand_miss_count),
        evicted_before_use_count=int(snapshot.evicted_before_use_count),
        ready_late_miss_count=int(snapshot.ready_late_miss_count),
        late_completion_unused_count=int(snapshot.late_completion_unused_count),
        queue_batch_count=int(snapshot.queue_batch_count),
        queue_service_us=float(snapshot.queue_service_us),
        queue_total_span_us=float(snapshot.queue_total_span_us),
        queue_wait_us=float(snapshot.queue_wait_us),
        queue_max_delay_us=float(snapshot.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            canary.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            canary.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            canary.shifted_issue_unique_issue_key_count,
        ),
    )


def build_payload_cache_live_runtime_adapter_payloadless_instance_canary(
    canary: PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary,
) -> PayloadCacheLiveRuntimeAdapterPayloadlessInstanceCanary:
    """Instantiate the payloadless live-style adapter under mixed-outcome gate."""

    if not isinstance(canary, PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary):
        raise TypeError(
            "canary must be a PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary",
        )
    if canary.present is not True:
        raise ValueError("mixed-outcome canary must be present")
    if canary.stage != "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary":
        raise ValueError("mixed-outcome canary stage mismatch")
    if canary.consumes_accounting_dry_run_canary is not True:
        raise ValueError("mixed-outcome canary must consume accounting canary")
    if (
        not isinstance(canary.accounting_dry_run_canary_status, str)
        or not canary.accounting_dry_run_canary_status
    ):
        raise TypeError("mixed-outcome accounting status invalid")
    if not canary.accounting_dry_run_canary_status.startswith(
        "blocked_by_operation_rejection_canary:"
        "blocked_by_object_shell_evidence:"
        "blocked_by_instance_construction_plan:"
        "blocked_by_constructor_binding_preflight:"
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:",
    ):
        raise ValueError("mixed-outcome accounting status chain mismatch")
    expected_status = (
        "blocked_by_accounting_dry_run_canary:"
        f"{canary.accounting_dry_run_canary_status}"
    )
    if canary.status != expected_status:
        raise ValueError("mixed-outcome canary status mismatch")
    if canary.decision != "blocked":
        raise ValueError("mixed-outcome canary must stay blocked")
    if canary.block_reason != "live_runtime_adapter_mixed_outcome_dry_run_canary_only":
        raise ValueError("mixed-outcome canary block reason mismatch")
    if (
        canary.execution_mode
        != "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary_payloadless"
    ):
        raise ValueError("mixed-outcome canary execution mode mismatch")
    for field_name in (
        "mixed_outcome_adapter_created",
        "mixed_outcome_operations_ran",
        "accounting_dry_run_enabled",
        "issue_prefetch_accepted",
        "duplicate_issue_suppressed",
        "prefetched_demand_hit",
        "unprefetched_demand_missed",
    ):
        if getattr(canary, field_name) is not True:
            raise ValueError(f"mixed-outcome canary {field_name} invalid")
    if canary.unprefetched_demand_hit is not False:
        raise ValueError("mixed-outcome canary unprefetched demand must miss")
    if canary.live_adapter_instance_created is not False:
        raise ValueError("mixed-outcome canary must not create live adapter")
    if canary.live_runtime_instantiated is not False:
        raise ValueError("mixed-outcome canary must not instantiate live runtime")
    expected_counts = {
        "resident_count": 2,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
    }
    for field_name, expected in expected_counts.items():
        if getattr(canary, field_name) != expected:
            raise ValueError(f"mixed-outcome canary {field_name} mismatch")
    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if getattr(canary, field_name) is not False:
            raise ValueError(f"mixed-outcome canary {field_name} enabled")
    for field_name in ("issued_payload_count", "payload_bytes"):
        if getattr(canary, field_name) != 0:
            raise ValueError(f"mixed-outcome canary {field_name} must be zero")

    adapter = PayloadCacheRuntimeAdapterPayloadlessLive(
        capacity=int(canary.capacity_entries),
        service_us_per_issue=0.0,
        service_us_per_batch=0.0,
        queue_batch_size=int(canary.queue_batch_size),
        queue_deadline_us=float(canary.queue_deadline_us),
        payload_transfer_enabled=False,
        kernel_arg_pass_allowed=False,
    )
    issue_accepted = adapter.issue_prefetch(0, 0, arrival_us=0.0)
    duplicate_suppressed = not adapter.issue_prefetch(0, 0, arrival_us=1.0)
    prefetched_demand_hit = adapter.demand(0, 0, arrival_us=2.0)
    unprefetched_demand_hit = adapter.demand(0, 1, arrival_us=3.0)
    snapshot = adapter.snapshot()

    return PayloadCacheLiveRuntimeAdapterPayloadlessInstanceCanary(
        present=True,
        stage="payload_cache_live_runtime_adapter_payloadless_instance_canary",
        status=f"blocked_by_mixed_outcome_dry_run_canary:{canary.status}",
        consumes_mixed_outcome_dry_run_canary=True,
        mixed_outcome_dry_run_canary_status=str(canary.status),
        manager_backend=str(canary.manager_backend),
        manager_runtime_contract=str(canary.manager_runtime_contract),
        manager_runtime_mode=str(canary.manager_runtime_mode),
        payloadless_instance_schema=(
            "ready_time_payload_cache_runtime_adapter_payloadless_instance_canary_v1"
        ),
        payloadless_live_adapter_created=True,
        payloadless_live_operations_ran=True,
        accounting_dry_run_enabled=bool(snapshot.accounting_dry_run_enabled),
        issue_prefetch_accepted=issue_accepted,
        duplicate_issue_suppressed=duplicate_suppressed,
        prefetched_demand_hit=prefetched_demand_hit,
        unprefetched_demand_hit=unprefetched_demand_hit,
        unprefetched_demand_missed=not unprefetched_demand_hit,
        live_adapter_instance_created=True,
        live_runtime_instantiated=False,
        capacity_entries=int(snapshot.capacity),
        issue_lead_tokens=int(canary.issue_lead_tokens),
        queue_deadline_us=float(snapshot.queue_deadline_us),
        lookahead_us=float(canary.lookahead_us),
        queue_batch_size=int(snapshot.queue_batch_size),
        resident_count=int(snapshot.resident_count),
        issued_fetch_count=int(snapshot.issued_fetch_count),
        used_fetch_count=int(snapshot.used_fetch_count),
        unused_fetch_count=int(snapshot.unused_fetch_count),
        demand_count=int(snapshot.demand_count),
        demand_hit_count=int(snapshot.demand_hit_count),
        demand_miss_count=int(snapshot.demand_miss_count),
        evicted_before_use_count=int(snapshot.evicted_before_use_count),
        ready_late_miss_count=int(snapshot.ready_late_miss_count),
        late_completion_unused_count=int(snapshot.late_completion_unused_count),
        queue_batch_count=int(snapshot.queue_batch_count),
        queue_service_us=float(snapshot.queue_service_us),
        queue_total_span_us=float(snapshot.queue_total_span_us),
        queue_wait_us=float(snapshot.queue_wait_us),
        queue_max_delay_us=float(snapshot.queue_max_delay_us),
        shifted_issue_accounting_enabled=bool(
            canary.shifted_issue_accounting_enabled,
        ),
        shifted_issue_accounted_packet_count=int(
            canary.shifted_issue_accounted_packet_count,
        ),
        shifted_issue_unique_issue_key_count=int(
            canary.shifted_issue_unique_issue_key_count,
        ),
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
