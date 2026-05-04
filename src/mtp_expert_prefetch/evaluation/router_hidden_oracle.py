from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from mtp_expert_prefetch.tracing.router_trace_bridge import load_trace_payload
from mtp_expert_prefetch.training.alignment_merge import manifest_record_path, read_trace_manifest


@dataclass(frozen=True)
class RouterHiddenOracleReport:
    ok: bool
    manifest_path: str
    num_samples: int
    num_calls: int
    num_layers: int
    total_elements: int
    matched_elements: int
    ordered_element_match_rate: float
    set_recall: float
    exact_set_match_rate: float
    top1_match_rate: float
    per_layer_ordered_element_match_rate: dict[str, float]
    per_layer_set_recall: dict[str, float]
    missing_oracle_count: int
    shape_error_count: int
    hidden_tensor_count: int
    hidden_shapes: dict[str, list[int]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "manifest_path": self.manifest_path,
            "num_samples": self.num_samples,
            "num_calls": self.num_calls,
            "num_layers": self.num_layers,
            "total_elements": self.total_elements,
            "matched_elements": self.matched_elements,
            "ordered_element_match_rate": self.ordered_element_match_rate,
            "set_recall": self.set_recall,
            "exact_set_match_rate": self.exact_set_match_rate,
            "top1_match_rate": self.top1_match_rate,
            "per_layer_ordered_element_match_rate": self.per_layer_ordered_element_match_rate,
            "per_layer_set_recall": self.per_layer_set_recall,
            "missing_oracle_count": self.missing_oracle_count,
            "shape_error_count": self.shape_error_count,
            "hidden_tensor_count": self.hidden_tensor_count,
            "hidden_shapes": self.hidden_shapes,
        }


def analyze_router_hidden_oracle(manifest_path: str | Path) -> RouterHiddenOracleReport:
    manifest_path = Path(manifest_path).expanduser().resolve()
    records = read_trace_manifest(manifest_path)
    matched_elements = 0
    set_matched_elements = 0
    total_elements = 0
    exact_set_matches = 0
    total_sets = 0
    top1_matches = 0
    num_calls = 0
    missing_oracle_count = 0
    shape_error_count = 0
    per_layer_matched: dict[str, int] = {}
    per_layer_set_matched: dict[str, int] = {}
    per_layer_total: dict[str, int] = {}
    hidden_tensor_count = 0
    hidden_shapes: dict[str, list[int]] = {}

    for record in records:
        payload = load_trace_payload(manifest_record_path(record))
        router_topk = payload.get("router_topk")
        router_weights = payload.get("router_weights")
        oracle_topk = payload.get("router_oracle_topk")
        oracle_weights = payload.get("router_oracle_weights")
        if not isinstance(router_topk, dict) or not router_topk:
            continue
        if not isinstance(oracle_topk, dict) or not oracle_topk:
            missing_oracle_count += len(router_topk)
            continue
        for module_name, calls in router_topk.items():
            oracle_calls = oracle_topk.get(module_name)
            weight_calls = (
                router_weights.get(module_name) if isinstance(router_weights, dict) else None
            )
            oracle_weight_calls = (
                oracle_weights.get(module_name) if isinstance(oracle_weights, dict) else None
            )
            if not isinstance(calls, list) or not isinstance(oracle_calls, list):
                missing_oracle_count += 1
                continue
            if len(calls) != len(oracle_calls):
                shape_error_count += 1
                continue
            if weight_calls is not None and len(weight_calls) != len(calls):
                shape_error_count += 1
                continue
            if oracle_weight_calls is not None and len(oracle_weight_calls) != len(calls):
                shape_error_count += 1
                continue
            for call_index, (call, oracle_call) in enumerate(zip(calls, oracle_calls, strict=True)):
                topk = torch.as_tensor(call, dtype=torch.long)
                oracle = torch.as_tensor(oracle_call, dtype=torch.long)
                if topk.shape != oracle.shape:
                    shape_error_count += 1
                    continue
                weights = (
                    torch.as_tensor(weight_calls[call_index], dtype=torch.float32)
                    if weight_calls is not None
                    else None
                )
                oracle_w = (
                    torch.as_tensor(oracle_weight_calls[call_index], dtype=torch.float32)
                    if oracle_weight_calls is not None
                    else None
                )
                matches = int((topk == oracle).sum().item())
                count = int(topk.numel())
                set_matches = _count_set_matches(topk, oracle)
                exact_sets, top1 = _count_exact_sets_and_top1_matches(
                    topk,
                    oracle,
                    weights=weights,
                    oracle_weights=oracle_w,
                )
                matched_elements += matches
                set_matched_elements += set_matches
                total_elements += count
                exact_set_matches += exact_sets
                top1_matches += top1
                total_sets += int(topk.shape[0])
                per_layer_matched[module_name] = per_layer_matched.get(module_name, 0) + matches
                per_layer_set_matched[module_name] = (
                    per_layer_set_matched.get(module_name, 0) + set_matches
                )
                per_layer_total[module_name] = per_layer_total.get(module_name, 0) + count
                num_calls += 1

        hidden = payload.get("router_input_hidden")
        if isinstance(hidden, dict):
            for module_name, hidden_calls in hidden.items():
                if not isinstance(hidden_calls, list):
                    continue
                for tensor in hidden_calls:
                    hidden_tensor = torch.as_tensor(tensor)
                    hidden_tensor_count += 1
                    hidden_shapes.setdefault(module_name, list(hidden_tensor.shape))

    ordered_element_match_rate = float(matched_elements / total_elements) if total_elements else 0.0
    set_recall = float(set_matched_elements / total_elements) if total_elements else 0.0
    exact_set_match_rate = float(exact_set_matches / total_sets) if total_sets else 0.0
    top1_match_rate = float(top1_matches / total_sets) if total_sets else 0.0
    per_layer_ordered_element_match_rate = {
        module_name: float(per_layer_matched[module_name] / per_layer_total[module_name])
        for module_name in sorted(per_layer_total)
    }
    per_layer_set_recall = {
        module_name: float(per_layer_set_matched[module_name] / per_layer_total[module_name])
        for module_name in sorted(per_layer_total)
    }
    ok = (
        bool(records)
        and total_elements > 0
        and missing_oracle_count == 0
        and shape_error_count == 0
        and set_recall == 1.0
        and exact_set_match_rate == 1.0
    )
    return RouterHiddenOracleReport(
        ok=ok,
        manifest_path=str(manifest_path),
        num_samples=len(records),
        num_calls=num_calls,
        num_layers=len(per_layer_total),
        total_elements=total_elements,
        matched_elements=matched_elements,
        ordered_element_match_rate=ordered_element_match_rate,
        set_recall=set_recall,
        exact_set_match_rate=exact_set_match_rate,
        top1_match_rate=top1_match_rate,
        per_layer_ordered_element_match_rate=per_layer_ordered_element_match_rate,
        per_layer_set_recall=per_layer_set_recall,
        missing_oracle_count=missing_oracle_count,
        shape_error_count=shape_error_count,
        hidden_tensor_count=hidden_tensor_count,
        hidden_shapes=hidden_shapes,
    )


def write_router_hidden_oracle_report(
    report: RouterHiddenOracleReport,
    output: str | Path,
) -> Path:
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return output


def _count_set_matches(topk: torch.Tensor, oracle: torch.Tensor) -> int:
    matches = 0
    for token_index in range(int(topk.shape[0])):
        matches += len(set(topk[token_index].tolist()) & set(oracle[token_index].tolist()))
    return matches


def _count_exact_sets_and_top1_matches(
    topk: torch.Tensor,
    oracle: torch.Tensor,
    *,
    weights: torch.Tensor | None,
    oracle_weights: torch.Tensor | None,
) -> tuple[int, int]:
    exact_sets = 0
    top1_matches = 0
    for token_index in range(int(topk.shape[0])):
        topk_row = topk[token_index]
        oracle_row = oracle[token_index]
        if set(topk_row.tolist()) == set(oracle_row.tolist()):
            exact_sets += 1
        if weights is not None:
            top1 = int(topk_row[int(torch.argmax(weights[token_index]).item())].item())
        else:
            top1 = int(topk_row[0].item())
        if oracle_weights is not None:
            oracle_top1 = int(
                oracle_row[int(torch.argmax(oracle_weights[token_index]).item())].item()
            )
        else:
            oracle_top1 = int(oracle_row[0].item())
        top1_matches += int(top1 == oracle_top1)
    return exact_sets, top1_matches
