from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch

from mtp_expert_prefetch.runtime.descriptor_order import (
    DescriptorOrderReport,
    build_layer_prior_plan_report_from_router_topk,
)
from mtp_expert_prefetch.runtime.tile_order import LayerTilePrior
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path


@dataclass(frozen=True)
class DescriptorOrderGateDecision:
    allow: bool
    reason: str
    execution_mode: str
    policy: str
    tile_elems: int
    groups_per_cta: int
    device: int | None = None
    group_count: int | None = None
    avg_group_size: float | None = None
    p95_group_size: float | None = None
    max_group_size: int | None = None
    cta_count: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow": bool(self.allow),
            "reason": self.reason,
            "execution_mode": self.execution_mode,
            "policy": self.policy,
            "tile_elems": int(self.tile_elems),
            "groups_per_cta": int(self.groups_per_cta),
            "device": self.device,
            "group_count": self.group_count,
            "avg_group_size": self.avg_group_size,
            "p95_group_size": self.p95_group_size,
            "max_group_size": self.max_group_size,
            "cta_count": self.cta_count,
        }


@dataclass(frozen=True)
class DescriptorOrderRuntimeGate:
    policy: str
    execution_mode: str
    tile_elems: tuple[int, ...]
    groups_per_cta: tuple[int, ...]
    devices: tuple[int, ...]
    diagnostic_groups_per_cta: tuple[int, ...]
    disable_groups_per_cta_min: int | None
    disable_unmeasured_tile_elems: bool = True
    disable_unmeasured_devices: bool = True
    disable_checksum_mismatch: bool = True
    disable_same_multiset_false: bool = True
    checksum_delta_required: float | None = 0.0
    same_multiset_required: bool = True
    prior_id: str | None = None
    prior_path: Path | None = None
    source_path: Path | None = None

    @classmethod
    def from_config(cls, path: str | Path, *, base_dir: str | Path | None = None) -> "DescriptorOrderRuntimeGate":
        source = Path(path).expanduser().resolve()
        payload = load_yaml(source)
        contract = _mapping(payload.get("contract"))
        initial = _mapping(payload.get("initial_runtime_gate"))
        diagnostic = _mapping(payload.get("diagnostic_only"))
        disable = _mapping(payload.get("disable"))
        resolved_base = (
            Path(base_dir).expanduser().resolve()
            if base_dir is not None
            else find_project_root(source)
        )
        prior_path = contract.get("prior_path")
        return cls(
            policy=str(payload.get("policy", "layer_prior_frequency")),
            execution_mode=str(payload.get("execution_mode", "two_level_group_plan")),
            tile_elems=_int_tuple(initial.get("tile_elems")),
            groups_per_cta=_int_tuple(initial.get("groups_per_cta")),
            devices=_int_tuple(initial.get("devices")),
            diagnostic_groups_per_cta=_int_tuple(diagnostic.get("groups_per_cta")),
            disable_groups_per_cta_min=(
                int(disable["groups_per_cta_min"])
                if disable.get("groups_per_cta_min") is not None
                else None
            ),
            disable_unmeasured_tile_elems=bool(disable.get("unmeasured_tile_elems", True)),
            disable_unmeasured_devices=bool(disable.get("unmeasured_devices", True)),
            disable_checksum_mismatch=bool(disable.get("checksum_mismatch", True)),
            disable_same_multiset_false=bool(disable.get("same_multiset_false", True)),
            checksum_delta_required=(
                float(contract["checksum_delta_required"])
                if contract.get("checksum_delta_required") is not None
                else None
            ),
            same_multiset_required=bool(contract.get("same_multiset_required", True)),
            prior_id=str(contract.get("prior_id")) if contract.get("prior_id") else None,
            prior_path=(
                resolve_path(str(prior_path), base_dir=resolved_base)
                if prior_path is not None
                else None
            ),
            source_path=source,
        )

    def decide(
        self,
        *,
        tile_elems: int,
        groups_per_cta: int,
        device: int | None = None,
        execution_mode: str | None = None,
        group_count: int | None = None,
        avg_group_size: float | None = None,
        p95_group_size: float | None = None,
        max_group_size: int | None = None,
        same_multiset: bool | None = None,
        checksum_delta: float | None = None,
    ) -> DescriptorOrderGateDecision:
        """Return whether a descriptor-order execution attempt is allowed.

        The gate is intentionally closed when required correctness evidence is
        absent.  Callers that only want an envelope check should either pass the
        evidence from a no-op assertion wrapper or use a config that disables
        the corresponding contract checks.
        """

        mode = str(execution_mode or self.execution_mode)
        tile = int(tile_elems)
        groups = int(groups_per_cta)
        dev = int(device) if device is not None else None
        cta_count = (
            int((int(group_count) + groups - 1) // groups)
            if group_count is not None and groups > 0
            else None
        )
        allow = True
        reason = "allowed"
        if mode != self.execution_mode:
            allow = False
            reason = "execution_mode_mismatch"
        elif self.disable_groups_per_cta_min is not None and groups >= self.disable_groups_per_cta_min:
            allow = False
            reason = "groups_per_cta_disabled"
        elif self.disable_unmeasured_tile_elems and tile not in self.tile_elems:
            allow = False
            reason = "tile_elems_unmeasured"
        elif groups not in self.groups_per_cta:
            allow = False
            reason = (
                "groups_per_cta_diagnostic_only"
                if groups in self.diagnostic_groups_per_cta
                else "groups_per_cta_unmeasured"
            )
        elif self.disable_unmeasured_devices and self.devices and dev is None:
            allow = False
            reason = "device_missing"
        elif self.disable_unmeasured_devices and dev is not None and self.devices and dev not in self.devices:
            allow = False
            reason = "device_unmeasured"
        if allow and self.disable_same_multiset_false and self.same_multiset_required:
            if same_multiset is None:
                allow = False
                reason = "same_multiset_missing"
            elif same_multiset is False:
                allow = False
                reason = "same_multiset_false"
        if allow and self.disable_checksum_mismatch and self.checksum_delta_required is not None:
            if checksum_delta is None:
                allow = False
                reason = "checksum_delta_missing"
            elif float(checksum_delta) != float(self.checksum_delta_required):
                allow = False
                reason = "checksum_mismatch"
        return DescriptorOrderGateDecision(
            allow=allow,
            reason=reason,
            execution_mode=mode,
            policy=self.policy,
            tile_elems=tile,
            groups_per_cta=groups,
            device=dev,
            group_count=group_count,
            avg_group_size=avg_group_size,
            p95_group_size=p95_group_size,
            max_group_size=max_group_size,
            cta_count=cta_count,
        )


def build_noop_descriptor_order_assertion(
    *,
    layer_id: int,
    topk_ids: torch.Tensor,
    topk_weights: torch.Tensor,
    prior: LayerTilePrior,
    gate: DescriptorOrderRuntimeGate,
    tile_elems: int,
    groups_per_cta: int,
    device: int | None = None,
    prior_id: str | None = None,
    prior_hash: str | None = None,
    tiles_per_expert: int = 1,
    token_window_size: int = 64,
    metrics_mode: str = "count_only",
    same_multiset_evidence: bool | None = None,
    checksum_delta_evidence: float | None = None,
) -> tuple[DescriptorOrderReport | None, DescriptorOrderGateDecision]:
    """Map current-router top-k to a group-plan report without changing execution.

    This is the first vLLM/HIP patch boundary: the true router remains
    authoritative, the top-k tensors are returned to vLLM unchanged, and this
    helper only verifies whether the current layer/request would be eligible for
    the measured two-level group-plan consumer.

    Correctness evidence is intentionally explicit.  Count-only telemetry can
    build a group-plan report cheaply, but it is not evidence that a future
    execution patch preserved the descriptor multiset or checksum.  Callers
    must pass those values after a no-op assertion or consumer parity check;
    otherwise the runtime gate stays closed.
    """

    report, _ = build_layer_prior_plan_report_from_router_topk(
        layer_id=int(layer_id),
        topk_ids=topk_ids,
        topk_weights=topk_weights,
        prior=prior,
        prior_id=prior_id or gate.prior_id,
        prior_hash=prior_hash,
        tiles_per_expert=int(tiles_per_expert),
        token_window_size=int(token_window_size),
        metrics_mode=metrics_mode,
    )
    group_plan = report.metrics.get("group_plan", {}) if report is not None else {}
    decision = gate.decide(
        tile_elems=int(tile_elems),
        groups_per_cta=int(groups_per_cta),
        device=device,
        execution_mode=gate.execution_mode,
        group_count=_optional_int(group_plan.get("group_count")),
        avg_group_size=_optional_float(group_plan.get("avg_group_size")),
        p95_group_size=_optional_float(group_plan.get("p95_group_size")),
        max_group_size=_optional_int(group_plan.get("max_group_size")),
        same_multiset=same_multiset_evidence,
        checksum_delta=checksum_delta_evidence,
    )
    return report, decision


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_tuple(value: Any) -> tuple[int, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(int(item) for item in value.split(",") if item.strip())
    if isinstance(value, Sequence):
        return tuple(int(item) for item in value)
    return (int(value),)


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None
