from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import torch

from mtp_expert_prefetch.runtime.premap import ExpertPrefetchDescriptor


@dataclass(frozen=True)
class LeadTimeReport:
    num_layers: int
    layer_ms: float
    sampling_ms: float
    mtp_delay_ms: float
    bandwidth_gbps: float
    expert_bytes: int
    num_descriptors: int
    by_source: dict[str, dict[str, float]]
    by_priority: dict[str, dict[str, float]]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def analyze_descriptor_lead_time(
    descriptors: list[ExpertPrefetchDescriptor],
    *,
    num_layers: int = 40,
    layer_ms: float = 1.0,
    sampling_ms: float = 0.0,
    mtp_delay_ms: float = 0.0,
    bandwidth_gbps: float = 16.0,
    expert_bytes: int = 1_650_000,
) -> LeadTimeReport:
    """Estimate whether descriptor groups can be fetched before demand.

    This is an envelope model, not a scheduler. It groups descriptors by
    sample/layer/source and checks how many experts could fit inside the
    available lead-time window:

    - transition_* is produced when token t layer l routing finishes and targets
      token t+1 layer l, so its lead is roughly one full forward pass.
    - mtp_token_* is produced after token t MTP/token prediction is available,
      so its lead to token t+1 layer l is roughly l layers minus MTP delay.
    """
    bandwidth_bytes_per_ms = float(bandwidth_gbps) * 1_000_000_000.0 / 1000.0
    source_groups: dict[tuple[str, int, int], int] = {}
    priority_groups: dict[tuple[str, int, int], int] = {}
    for descriptor in descriptors:
        source_key = (descriptor.source, descriptor.sample_idx, descriptor.layer_idx)
        source_groups[source_key] = source_groups.get(source_key, 0) + 1
        priority_key = (str(descriptor.priority), descriptor.sample_idx, descriptor.layer_idx)
        priority_groups[priority_key] = priority_groups.get(priority_key, 0) + 1

    return LeadTimeReport(
        num_layers=int(num_layers),
        layer_ms=float(layer_ms),
        sampling_ms=float(sampling_ms),
        mtp_delay_ms=float(mtp_delay_ms),
        bandwidth_gbps=float(bandwidth_gbps),
        expert_bytes=int(expert_bytes),
        num_descriptors=len(descriptors),
        by_source=_summarize_groups(
            source_groups,
            num_layers=num_layers,
            layer_ms=layer_ms,
            sampling_ms=sampling_ms,
            mtp_delay_ms=mtp_delay_ms,
            bandwidth_bytes_per_ms=bandwidth_bytes_per_ms,
            expert_bytes=expert_bytes,
            key_kind="source",
        ),
        by_priority=_summarize_groups(
            priority_groups,
            num_layers=num_layers,
            layer_ms=layer_ms,
            sampling_ms=sampling_ms,
            mtp_delay_ms=mtp_delay_ms,
            bandwidth_bytes_per_ms=bandwidth_bytes_per_ms,
            expert_bytes=expert_bytes,
            key_kind="priority",
        ),
    )


def write_lead_time_report(report: LeadTimeReport, output: str | Path) -> Path:
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def _summarize_groups(
    groups: dict[tuple[str, int, int], int],
    *,
    num_layers: int,
    layer_ms: float,
    sampling_ms: float,
    mtp_delay_ms: float,
    bandwidth_bytes_per_ms: float,
    expert_bytes: int,
    key_kind: str,
) -> dict[str, dict[str, float]]:
    by_name: dict[str, list[tuple[int, int]]] = {}
    for (name, _sample_idx, layer_idx), count in groups.items():
        by_name.setdefault(name, []).append((int(layer_idx), int(count)))

    result = {}
    for name, items in by_name.items():
        counts = []
        lead_ms_values = []
        fetchable = []
        for layer_idx, count in items:
            lead_ms = _lead_ms_for_name(
                name,
                layer_idx=layer_idx,
                num_layers=num_layers,
                layer_ms=layer_ms,
                sampling_ms=sampling_ms,
                mtp_delay_ms=mtp_delay_ms,
                key_kind=key_kind,
            )
            capacity = max(0, math.floor(lead_ms * bandwidth_bytes_per_ms / expert_bytes))
            counts.append(float(count))
            lead_ms_values.append(float(lead_ms))
            fetchable.append(float(min(count, capacity)))
        count_tensor = torch.tensor(counts, dtype=torch.float32)
        lead_tensor = torch.tensor(lead_ms_values, dtype=torch.float32)
        fetch_tensor = torch.tensor(fetchable, dtype=torch.float32)
        total = count_tensor.sum().clamp_min(1.0)
        result[name] = {
            "groups": float(len(items)),
            "total_experts": float(count_tensor.sum().item()),
            "fetchable_experts": float(fetch_tensor.sum().item()),
            "fetchable_fraction": float((fetch_tensor.sum() / total).item()),
            "mean_group_experts": float(count_tensor.mean().item()),
            "p95_group_experts": float(torch.quantile(count_tensor, 0.95).item()),
            "mean_lead_ms": float(lead_tensor.mean().item()),
            "min_lead_ms": float(lead_tensor.min().item()),
            "p50_lead_ms": float(torch.quantile(lead_tensor, 0.50).item()),
        }
    return result


def _lead_ms_for_name(
    name: str,
    *,
    layer_idx: int,
    num_layers: int,
    layer_ms: float,
    sampling_ms: float,
    mtp_delay_ms: float,
    key_kind: str,
) -> float:
    if key_kind == "priority":
        if name in {"2", "3"}:
            return float(num_layers) * float(layer_ms) + float(sampling_ms)
        return max(0.0, float(layer_idx) * float(layer_ms) + float(sampling_ms) - float(mtp_delay_ms))
    if name.startswith("transition"):
        return float(num_layers) * float(layer_ms) + float(sampling_ms)
    return max(0.0, float(layer_idx) * float(layer_ms) + float(sampling_ms) - float(mtp_delay_ms))
