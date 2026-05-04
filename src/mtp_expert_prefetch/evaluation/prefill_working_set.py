from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from mtp_expert_prefetch.tracing import load_trace_payload
from mtp_expert_prefetch.training import stack_backbone_router_topk
from mtp_expert_prefetch.training.alignment_merge import manifest_record_path, read_trace_manifest


@dataclass(frozen=True)
class PrefillWorkingSetReport:
    manifest_path: str
    num_samples: int
    num_layers: int
    top_k: int
    total_tokens: int
    budgets: list[int]
    layer_unique_summary: dict[str, float]
    sample_unique_summary: dict[str, float]
    hot_cache: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "num_samples": self.num_samples,
            "num_layers": self.num_layers,
            "top_k": self.top_k,
            "total_tokens": self.total_tokens,
            "budgets": self.budgets,
            "layer_unique_summary": self.layer_unique_summary,
            "sample_unique_summary": self.sample_unique_summary,
            "hot_cache": self.hot_cache,
        }


def analyze_prefill_working_set(
    manifest_path: str | Path,
    *,
    budgets: list[int],
    max_samples: int | None = None,
) -> PrefillWorkingSetReport:
    manifest_path = Path(manifest_path).expanduser().resolve()
    records = read_trace_manifest(manifest_path)
    if max_samples is not None:
        records = records[:max_samples]
    if not records:
        msg = f"No trace records in {manifest_path}"
        raise RuntimeError(msg)

    layer_token_counts: torch.Tensor | None = None
    layer_unique_counts: list[torch.Tensor] = []
    sample_unique_counts: list[int] = []
    token_counts: list[int] = []
    num_layers = 0
    top_k = 0

    for record in records:
        payload = load_trace_payload(manifest_record_path(record))
        router_by_layer, _layer_ids = stack_backbone_router_topk(payload)
        router_by_layer = router_by_layer.to(torch.long)
        if router_by_layer.ndim != 3:
            msg = (
                "Expected router tensor [layers, tokens, top_k], got "
                f"{tuple(router_by_layer.shape)}"
            )
            raise ValueError(msg)

        if layer_token_counts is None:
            num_layers = int(router_by_layer.shape[0])
            top_k = int(router_by_layer.shape[-1])
            num_experts = int(router_by_layer.max().item()) + 1
            layer_token_counts = torch.zeros((num_layers, max(256, num_experts)), dtype=torch.long)
        elif int(router_by_layer.shape[0]) != num_layers or int(router_by_layer.shape[-1]) != top_k:
            msg = "All traces must share [layers, top_k] dimensions."
            raise ValueError(msg)

        token_counts.append(int(router_by_layer.shape[1]))
        layer_unique = []
        for layer_idx in range(num_layers):
            ids = router_by_layer[layer_idx].reshape(-1)
            layer_unique.append(int(torch.unique(ids).numel()))
            layer_token_counts[layer_idx].scatter_add_(
                0,
                ids,
                torch.ones_like(ids, dtype=torch.long),
            )
        layer_unique_tensor = torch.tensor(layer_unique, dtype=torch.float32)
        layer_unique_counts.append(layer_unique_tensor)
        sample_unique_counts.append(int(torch.unique(router_by_layer.reshape(-1)).numel()))

    assert layer_token_counts is not None
    layer_unique_matrix = torch.stack(layer_unique_counts, dim=0)
    sample_unique_tensor = torch.tensor(sample_unique_counts, dtype=torch.float32)

    hot_cache = _hot_cache_report(
        layer_token_counts=layer_token_counts,
        layer_unique_matrix=layer_unique_matrix,
        budgets=budgets,
        records=records,
    )

    return PrefillWorkingSetReport(
        manifest_path=str(manifest_path),
        num_samples=len(records),
        num_layers=num_layers,
        top_k=top_k,
        total_tokens=sum(token_counts),
        budgets=budgets,
        layer_unique_summary=_summary(layer_unique_matrix.reshape(-1)),
        sample_unique_summary=_summary(sample_unique_tensor),
        hot_cache=hot_cache,
    )


def write_prefill_working_set_report(report: PrefillWorkingSetReport, output: str | Path) -> Path:
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return output


def _hot_cache_report(
    *,
    layer_token_counts: torch.Tensor,
    layer_unique_matrix: torch.Tensor,
    budgets: list[int],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    total_selections = int(layer_token_counts.sum().item())
    per_budget: dict[str, Any] = {}
    max_budget = int(layer_token_counts.shape[1])
    sorted_experts = torch.argsort(layer_token_counts, dim=-1, descending=True)

    for budget in budgets:
        budget = min(max_budget, int(budget))
        hot_mask = torch.zeros_like(layer_token_counts, dtype=torch.bool)
        hot_mask.scatter_(1, sorted_experts[:, :budget], True)
        hot_hits = int(layer_token_counts[hot_mask].sum().item())

        sample_layer_misses = []
        sample_layer_hot_fits = []
        sample_layer_budget_fits = []
        for record in records:
            payload = load_trace_payload(manifest_record_path(record))
            router_by_layer, _layer_ids = stack_backbone_router_topk(payload)
            router_by_layer = router_by_layer.to(torch.long)
            for layer_idx in range(int(router_by_layer.shape[0])):
                unique_ids = torch.unique(router_by_layer[layer_idx].reshape(-1))
                misses = int((~hot_mask[layer_idx, unique_ids]).sum().item())
                sample_layer_misses.append(misses)
                sample_layer_hot_fits.append(misses == 0)
                sample_layer_budget_fits.append(int(unique_ids.numel()) <= budget)

        miss_tensor = torch.tensor(sample_layer_misses, dtype=torch.float32)
        hot_fit_tensor = torch.tensor(sample_layer_hot_fits, dtype=torch.float32)
        budget_fit_tensor = torch.tensor(sample_layer_budget_fits, dtype=torch.float32)
        per_budget[str(budget)] = {
            "selection_hit_rate": hot_hits / max(1, total_selections),
            "sample_layer_fully_resident_fraction": float(hot_fit_tensor.mean().item()),
            "sample_layer_budget_can_fit_fraction": float(budget_fit_tensor.mean().item()),
            "sample_layer_missing_unique_summary": _summary(miss_tensor),
        }
    return per_budget


def _summary(values: torch.Tensor) -> dict[str, float]:
    values = values.detach().float().cpu()
    if values.numel() == 0:
        return {"mean": 0.0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "mean": float(values.mean().item()),
        "p50": float(torch.quantile(values, 0.50).item()),
        "p90": float(torch.quantile(values, 0.90).item()),
        "p95": float(torch.quantile(values, 0.95).item()),
        "max": float(values.max().item()),
    }
