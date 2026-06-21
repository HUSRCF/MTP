from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Sequence

from mtp_expert_prefetch.runtime.cache_manager import ReadyTimeExpertCacheManager


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
