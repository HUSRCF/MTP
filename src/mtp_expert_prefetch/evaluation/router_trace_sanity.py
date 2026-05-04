from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from mtp_expert_prefetch.tracing import load_trace_payload
from mtp_expert_prefetch.training import (
    stack_backbone_router_topk,
    stack_backbone_router_weights,
)
from mtp_expert_prefetch.training.alignment_merge import manifest_record_path, read_trace_manifest


@dataclass(frozen=True)
class RouterTraceSanityReport:
    manifest_path: str
    num_samples: int
    expected_trace_source: str | None
    trace_sources: dict[str, int]
    num_layers_summary: dict[str, float]
    top_k_summary: dict[str, float]
    weight_sum_summary: dict[str, float]
    weight_value_summary: dict[str, float]
    weight_std_summary: dict[str, float]
    sorted_weight_fraction: float
    first_is_argmax_fraction: float
    nonuniform_sample_fraction: float
    source_mismatch_count: int
    shape_error_count: int
    id_range_error_count: int
    missing_weight_count: int
    ok: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "num_samples": self.num_samples,
            "expected_trace_source": self.expected_trace_source,
            "trace_sources": self.trace_sources,
            "num_layers_summary": self.num_layers_summary,
            "top_k_summary": self.top_k_summary,
            "weight_sum_summary": self.weight_sum_summary,
            "weight_value_summary": self.weight_value_summary,
            "weight_std_summary": self.weight_std_summary,
            "sorted_weight_fraction": self.sorted_weight_fraction,
            "first_is_argmax_fraction": self.first_is_argmax_fraction,
            "nonuniform_sample_fraction": self.nonuniform_sample_fraction,
            "source_mismatch_count": self.source_mismatch_count,
            "shape_error_count": self.shape_error_count,
            "id_range_error_count": self.id_range_error_count,
            "missing_weight_count": self.missing_weight_count,
            "ok": self.ok,
        }


def analyze_router_trace_sanity(
    manifest_path: str | Path,
    *,
    expected_trace_source: str | None = None,
    expected_layers: int | None = 40,
    num_experts: int = 256,
    max_samples: int | None = None,
    nonuniform_std_threshold: float = 1e-6,
) -> RouterTraceSanityReport:
    manifest_path = Path(manifest_path).expanduser().resolve()
    records = read_trace_manifest(manifest_path)
    if max_samples is not None:
        records = records[:max_samples]
    if not records:
        msg = f"No trace records in {manifest_path}"
        raise RuntimeError(msg)

    trace_sources: dict[str, int] = {}
    layer_counts: list[float] = []
    topk_counts: list[float] = []
    weight_sums: list[torch.Tensor] = []
    weight_values: list[torch.Tensor] = []
    weight_stds: list[float] = []
    sorted_numerator = 0.0
    sorted_denominator = 0.0
    first_argmax_numerator = 0.0
    first_argmax_denominator = 0.0
    nonuniform_count = 0
    source_mismatch_count = 0
    shape_error_count = 0
    id_range_error_count = 0
    missing_weight_count = 0

    for record in records:
        payload = load_trace_payload(manifest_record_path(record))
        source = str(payload.get("trace_source") or record.get("trace_source") or "unknown")
        trace_sources[source] = trace_sources.get(source, 0) + 1
        if expected_trace_source is not None and source != expected_trace_source:
            source_mismatch_count += 1

        try:
            router_topk, _layer_ids = stack_backbone_router_topk(payload)
        except (KeyError, ValueError):
            shape_error_count += 1
            continue
        try:
            router_weights, weight_layer_ids = stack_backbone_router_weights(payload)
        except (KeyError, ValueError):
            missing_weight_count += 1
            continue
        if (
            not torch.equal(_layer_ids, weight_layer_ids)
            or router_topk.shape != router_weights.shape
        ):
            shape_error_count += 1
            continue

        ids = router_topk.to(torch.long)
        weights = router_weights.to(torch.float32)
        layer_counts.append(float(ids.shape[0]))
        topk_counts.append(float(ids.shape[-1]))
        if expected_layers is not None and int(ids.shape[0]) != expected_layers:
            shape_error_count += 1
        if int(ids.min().item()) < 0 or int(ids.max().item()) >= num_experts:
            id_range_error_count += 1

        sums = weights.sum(dim=-1).reshape(-1).detach().cpu()
        flat_weights = weights.reshape(-1).detach().cpu()
        weight_sums.append(sums)
        weight_values.append(flat_weights)
        std = float(flat_weights.std().item())
        weight_stds.append(std)
        if std > nonuniform_std_threshold:
            nonuniform_count += 1

        if weights.shape[-1] > 1:
            sorted_mask = weights[..., :-1] >= (weights[..., 1:] - 1e-7)
            sorted_numerator += float(sorted_mask.to(torch.float32).sum().item())
            sorted_denominator += float(sorted_mask.numel())
        argmax_is_first = torch.argmax(weights, dim=-1) == 0
        first_argmax_numerator += float(argmax_is_first.to(torch.float32).sum().item())
        first_argmax_denominator += float(argmax_is_first.numel())

    weight_sum_tensor = _cat_or_empty(weight_sums)
    weight_value_tensor = _cat_or_empty(weight_values)
    report = RouterTraceSanityReport(
        manifest_path=str(manifest_path),
        num_samples=len(records),
        expected_trace_source=expected_trace_source,
        trace_sources=trace_sources,
        num_layers_summary=_summary(torch.tensor(layer_counts, dtype=torch.float32)),
        top_k_summary=_summary(torch.tensor(topk_counts, dtype=torch.float32)),
        weight_sum_summary=_summary(weight_sum_tensor),
        weight_value_summary=_summary(weight_value_tensor),
        weight_std_summary=_summary(torch.tensor(weight_stds, dtype=torch.float32)),
        sorted_weight_fraction=sorted_numerator / max(1.0, sorted_denominator),
        first_is_argmax_fraction=first_argmax_numerator / max(1.0, first_argmax_denominator),
        nonuniform_sample_fraction=nonuniform_count / max(1, len(records)),
        source_mismatch_count=source_mismatch_count,
        shape_error_count=shape_error_count,
        id_range_error_count=id_range_error_count,
        missing_weight_count=missing_weight_count,
        ok=(
            source_mismatch_count == 0
            and shape_error_count == 0
            and id_range_error_count == 0
            and missing_weight_count == 0
        ),
    )
    return report


def write_router_trace_sanity_report(report: RouterTraceSanityReport, output: str | Path) -> Path:
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return output


def _cat_or_empty(parts: list[torch.Tensor]) -> torch.Tensor:
    if not parts:
        return torch.empty(0, dtype=torch.float32)
    return torch.cat([part.detach().float().reshape(-1).cpu() for part in parts], dim=0)


def _summary(values: torch.Tensor) -> dict[str, float]:
    values = values.detach().float().cpu()
    if values.numel() == 0:
        return {"mean": 0.0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "max": 0.0, "min": 0.0}
    return {
        "mean": float(values.mean().item()),
        "p50": float(torch.quantile(values, 0.50).item()),
        "p90": float(torch.quantile(values, 0.90).item()),
        "p95": float(torch.quantile(values, 0.95).item()),
        "max": float(values.max().item()),
        "min": float(values.min().item()),
    }
