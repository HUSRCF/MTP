#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PROJECT_SRC))

from mtp_expert_prefetch.tracing import load_trace_payload  # noqa: E402
from mtp_expert_prefetch.training import (  # noqa: E402
    HiddenResidualExpertPredictor,
    build_previous_token_hidden_batch,
    fit_prior_tables,
    mass_coverage_at_m,
    recall_at_m,
    top1_risk_at_m,
)
from mtp_expert_prefetch.training.alignment_merge import (  # noqa: E402
    manifest_record_path,
    read_trace_manifest,
)
from mtp_expert_prefetch.utils.config import (  # noqa: E402
    find_project_root,
    load_yaml,
    resolve_path,
)

DEFAULT_CONFIG = Path("configs/train/hidden_residual_predictor_smoke.yaml")


@dataclass(frozen=True)
class HiddenDataset:
    hidden: torch.Tensor
    layer_ids: torch.Tensor
    labels: torch.Tensor
    target_mass: torch.Tensor | None
    prior_logits: torch.Tensor
    transition_logits: torch.Tensor
    frequency_logits: torch.Tensor
    sample_indices: list[int]
    source_paths: list[str]


def _parse_int_list(value: Any, *, name: str) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, int):
        return [int(value)]
    if isinstance(value, list):
        return [int(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        return [int(part.strip()) for part in stripped.split(",") if part.strip()]
    msg = f"{name} must be an int, list[int], comma string, or null."
    raise TypeError(msg)


def _parse_recall_ms(training_config: dict) -> list[int]:
    value = training_config.get("recall_at_ms", [8, 16, 32])
    if isinstance(value, int):
        return [int(value)]
    if isinstance(value, list):
        return [int(item) for item in value]
    return [int(part.strip()) for part in str(value).split(",") if part.strip()]


def _split_positions(num_samples: int, training_config: dict) -> tuple[list[int], list[int]]:
    train_positions = _parse_int_list(
        training_config.get("train_sample_indices"),
        name="train_sample_indices",
    )
    val_positions = _parse_int_list(
        training_config.get("val_sample_indices"),
        name="val_sample_indices",
    )
    if train_positions is not None or val_positions is not None:
        train_positions = train_positions if train_positions is not None else []
        val_positions = val_positions if val_positions is not None else []
    elif num_samples == 1:
        train_positions = [0]
        val_positions = []
    else:
        val_fraction = float(training_config.get("val_fraction", 0.25))
        val_count = int(round(num_samples * val_fraction))
        val_count = min(num_samples - 1, max(1, val_count))
        train_positions = list(range(num_samples - val_count))
        val_positions = list(range(num_samples - val_count, num_samples))
    if not train_positions:
        msg = "At least one training sample is required."
        raise ValueError(msg)
    if len(set(train_positions + val_positions)) != len(train_positions + val_positions):
        msg = "Train and validation sample positions must not overlap."
        raise ValueError(msg)
    for position in train_positions + val_positions:
        if position < 0 or position >= num_samples:
            msg = f"Sample position {position} out of range for {num_samples} samples."
            raise IndexError(msg)
    return train_positions, val_positions


def _load_payloads(
    data_config: dict,
    *,
    project_root: Path,
) -> list[tuple[int, Path, dict[str, Any]]]:
    manifest_path = resolve_path(data_config["trace_manifest"], base_dir=project_root)
    records = read_trace_manifest(manifest_path)
    sample_indices = _parse_int_list(data_config.get("sample_indices"), name="sample_indices")
    if sample_indices is not None:
        allowed = set(sample_indices)
        records = [record for record in records if int(record["sample_idx"]) in allowed]
    max_samples = data_config.get("max_samples")
    if max_samples is not None:
        records = records[: int(max_samples)]
    payloads = []
    for record in records:
        path = manifest_record_path(record)
        payloads.append((int(record["sample_idx"]), path, load_trace_payload(path)))
    if not payloads:
        msg = "No hidden trace payloads were loaded."
        raise RuntimeError(msg)
    return payloads


def _make_dataset(
    payloads: list[tuple[int, Path, dict[str, Any]]],
    positions: list[int],
    *,
    frequency_scores: torch.Tensor,
    transition_matrix: torch.Tensor,
    future_window: int,
    num_experts: int,
    max_tokens: int | None,
    device: torch.device,
) -> HiddenDataset | None:
    if not positions:
        return None
    hidden_parts = []
    layer_id_parts = []
    label_parts = []
    target_mass_parts = []
    prior_parts = []
    transition_parts = []
    frequency_parts = []
    sample_indices = []
    source_paths = []
    has_target_mass: bool | None = None
    for position in positions:
        sample_idx, path, payload = payloads[position]
        batch = build_previous_token_hidden_batch(
            payload,
            frequency_scores=frequency_scores,
            transition_matrix=transition_matrix,
            future_window=future_window,
            num_experts=num_experts,
        )
        token_limit = int(max_tokens) if max_tokens is not None else batch.num_tokens
        example_limit = min(token_limit, batch.num_tokens) * batch.num_layers
        hidden_parts.append(batch.hidden[:example_limit])
        layer_id_parts.append(batch.layer_ids[:example_limit])
        label_parts.append(batch.labels[:example_limit])
        prior_parts.append(batch.prior_logits[:example_limit])
        transition_parts.append(batch.transition_logits[:example_limit])
        frequency_parts.append(batch.frequency_logits[:example_limit])
        if batch.target_mass is not None:
            if has_target_mass is False:
                msg = "Either all samples or no samples must include target mass."
                raise ValueError(msg)
            has_target_mass = True
            target_mass_parts.append(batch.target_mass[:example_limit])
        else:
            if has_target_mass is True:
                msg = "Either all samples or no samples must include target mass."
                raise ValueError(msg)
            has_target_mass = False
        sample_indices.append(sample_idx)
        source_paths.append(str(path))

    target_mass = torch.cat(target_mass_parts, dim=0).to(device) if has_target_mass else None
    return HiddenDataset(
        hidden=torch.cat(hidden_parts, dim=0).to(device),
        layer_ids=torch.cat(layer_id_parts, dim=0).to(device),
        labels=torch.cat(label_parts, dim=0).to(device),
        target_mass=target_mass,
        prior_logits=torch.cat(prior_parts, dim=0).to(device),
        transition_logits=torch.cat(transition_parts, dim=0).to(device),
        frequency_logits=torch.cat(frequency_parts, dim=0).to(device),
        sample_indices=sample_indices,
        source_paths=source_paths,
    )


def _metric_for_logits(
    logits: torch.Tensor,
    dataset: HiddenDataset,
    recall_ms: list[int],
) -> dict:
    recalls = {m: recall_at_m(logits, dataset.labels, m=m) for m in recall_ms}
    metrics = {
        "recall_at": {
            str(m): {
                "recall": recalls[m].recall,
                "numerator": recalls[m].numerator,
                "denominator": recalls[m].denominator,
            }
            for m in recall_ms
        },
    }
    if dataset.target_mass is not None:
        coverages = {m: mass_coverage_at_m(logits, dataset.target_mass, m=m) for m in recall_ms}
        risks = {m: top1_risk_at_m(logits, dataset.target_mass, m=m) for m in recall_ms}
        metrics["mass_coverage_at"] = {
            str(m): {
                "coverage": coverages[m].coverage,
                "numerator": coverages[m].numerator,
                "denominator": coverages[m].denominator,
            }
            for m in recall_ms
        }
        metrics["top1_risk_at"] = {
            str(m): {
                "top1_hit_rate": risks[m].top1_hit_rate,
                "weighted_top1_miss": risks[m].weighted_top1_miss,
                "hit_count": risks[m].hit_count,
                "total_count": risks[m].total_count,
                "weighted_miss_numerator": risks[m].weighted_miss_numerator,
            }
            for m in recall_ms
        }
    for m in recall_ms:
        metrics[f"recall_at_{m}"] = metrics["recall_at"][str(m)]["recall"]
        if "mass_coverage_at" in metrics:
            metrics[f"mass_coverage_at_{m}"] = metrics["mass_coverage_at"][str(m)]["coverage"]
            metrics[f"top1_hit_at_{m}"] = metrics["top1_risk_at"][str(m)]["top1_hit_rate"]
            metrics[f"weighted_top1_miss_at_{m}"] = metrics["top1_risk_at"][str(m)][
                "weighted_top1_miss"
            ]
    return metrics


def _metric_for_layer_logits(
    logits: torch.Tensor,
    labels: torch.Tensor,
    target_mass: torch.Tensor | None,
    recall_ms: list[int],
) -> dict:
    recalls = {m: recall_at_m(logits, labels, m=m) for m in recall_ms}
    metrics: dict[str, Any] = {
        "recall_at": {str(m): recalls[m].recall for m in recall_ms},
    }
    if target_mass is not None:
        coverages = {m: mass_coverage_at_m(logits, target_mass, m=m) for m in recall_ms}
        risks = {m: top1_risk_at_m(logits, target_mass, m=m) for m in recall_ms}
        metrics["mass_coverage_at"] = {str(m): coverages[m].coverage for m in recall_ms}
        metrics["top1_hit_at"] = {str(m): risks[m].top1_hit_rate for m in recall_ms}
        metrics["weighted_top1_miss_at"] = {
            str(m): risks[m].weighted_top1_miss for m in recall_ms
        }
    return metrics


def _per_layer_delta_vs_transition(
    *,
    logits: torch.Tensor,
    transition_logits: torch.Tensor,
    dataset: HiddenDataset,
    recall_ms: list[int],
) -> dict:
    report = {}
    for layer_id in torch.unique(dataset.layer_ids).detach().cpu().tolist():
        layer = int(layer_id)
        mask = dataset.layer_ids == layer
        if not bool(mask.any()):
            continue
        model_metrics = _metric_for_layer_logits(
            logits[mask],
            dataset.labels[mask],
            dataset.target_mass[mask] if dataset.target_mass is not None else None,
            recall_ms,
        )
        transition_metrics = _metric_for_layer_logits(
            transition_logits[mask],
            dataset.labels[mask],
            dataset.target_mass[mask] if dataset.target_mass is not None else None,
            recall_ms,
        )
        layer_report: dict[str, Any] = {
            "num_examples": int(mask.sum().detach().cpu().item()),
            "model": model_metrics,
            "transition": transition_metrics,
        }
        if dataset.target_mass is not None:
            layer_report["delta_mass_coverage_at"] = {
                str(m): model_metrics["mass_coverage_at"][str(m)]
                - transition_metrics["mass_coverage_at"][str(m)]
                for m in recall_ms
            }
            layer_report["delta_top1_hit_at"] = {
                str(m): model_metrics["top1_hit_at"][str(m)]
                - transition_metrics["top1_hit_at"][str(m)]
                for m in recall_ms
            }
            layer_report["delta_weighted_top1_miss_at"] = {
                str(m): model_metrics["weighted_top1_miss_at"][str(m)]
                - transition_metrics["weighted_top1_miss_at"][str(m)]
                for m in recall_ms
            }
        report[str(layer)] = layer_report
    return report


def _training_loss(
    logits: torch.Tensor,
    dataset: HiddenDataset,
    *,
    pos_weight: torch.Tensor,
) -> torch.Tensor:
    if dataset.target_mass is None:
        return F.binary_cross_entropy_with_logits(
            logits,
            dataset.labels,
            pos_weight=pos_weight,
        )
    target = dataset.target_mass.float().clamp_min(0.0)
    target = target / target.sum(dim=-1, keepdim=True).clamp_min(1e-12)
    log_probs = F.log_softmax(logits.float(), dim=-1)
    return -(target * log_probs).sum(dim=-1).mean()


def _topk_overlap_at_m(logits_a: torch.Tensor, logits_b: torch.Tensor, *, m: int) -> float:
    top_a = torch.topk(logits_a.float(), k=m, dim=-1).indices
    top_b = torch.topk(logits_b.float(), k=m, dim=-1).indices
    predicted = torch.zeros_like(logits_a, dtype=torch.bool)
    reference = torch.zeros_like(logits_a, dtype=torch.bool)
    predicted.scatter_(-1, top_a, True)
    reference.scatter_(-1, top_b, True)
    overlap = (predicted & reference).sum().to(torch.float32)
    denominator = torch.tensor(float(top_a.numel()), dtype=torch.float32, device=logits_a.device)
    return float((overlap / denominator.clamp_min(1.0)).item())


def _mask_logits_to_candidate_topk(
    logits: torch.Tensor,
    candidate_logits: torch.Tensor,
    *,
    candidate_topk: int,
) -> torch.Tensor:
    if logits.shape != candidate_logits.shape:
        msg = (
            "logits and candidate_logits must share shape for constrained reranking; "
            f"got {tuple(logits.shape)} and {tuple(candidate_logits.shape)}"
        )
        raise ValueError(msg)
    if not 0 < candidate_topk <= logits.shape[-1]:
        msg = f"candidate_topk must be in [1, {logits.shape[-1]}], got {candidate_topk}"
        raise ValueError(msg)
    candidate_ids = torch.topk(candidate_logits.float(), k=candidate_topk, dim=-1).indices
    mask = torch.zeros_like(logits, dtype=torch.bool)
    mask.scatter_(-1, candidate_ids, True)
    floor = torch.finfo(logits.dtype).min if logits.dtype.is_floating_point else -1e30
    return torch.where(mask, logits, torch.full_like(logits, floor))


def _candidate_logits_by_name(dataset: HiddenDataset, name: str) -> torch.Tensor:
    if name == "transition":
        return dataset.transition_logits
    if name in {"prior", "frequency_plus_transition"}:
        return dataset.prior_logits
    if name == "frequency":
        return dataset.frequency_logits
    msg = "candidate_source must be one of: transition, prior, frequency."
    raise ValueError(msg)


def _logit_diagnostics(
    *,
    prior_logits: torch.Tensor,
    residual: torch.Tensor,
    effective_residual: torch.Tensor,
    logits: torch.Tensor,
    recall_ms: list[int],
    gamma_summary: dict[str, float | str] | None = None,
) -> dict:
    diagnostics = {
        "prior_std": float(prior_logits.float().std().detach().cpu().item()),
        "residual_std": float(residual.float().std().detach().cpu().item()),
        "effective_residual_std": float(effective_residual.float().std().detach().cpu().item()),
        "prior_mean_abs": float(prior_logits.float().abs().mean().detach().cpu().item()),
        "residual_mean_abs": float(residual.float().abs().mean().detach().cpu().item()),
        "effective_residual_mean_abs": float(
            effective_residual.float().abs().mean().detach().cpu().item()
        ),
    }
    diagnostics["topk_overlap_prior_vs_model"] = {
        str(m): _topk_overlap_at_m(logits, prior_logits, m=m) for m in recall_ms
    }
    if gamma_summary is not None:
        diagnostics["learnable_gamma"] = gamma_summary
    return diagnostics


def _effective_residual(
    model: HiddenResidualExpertPredictor,
    residual: torch.Tensor,
    *,
    layer_ids: torch.Tensor,
    residual_scale: float,
) -> torch.Tensor:
    return model.apply_residual_scale(
        residual,
        layer_ids=layer_ids,
        fixed_scale=residual_scale,
    )


def _evaluate(
    *,
    model: HiddenResidualExpertPredictor,
    dataset: HiddenDataset,
    recall_ms: list[int],
    residual_scale: float,
    pos_weight: torch.Tensor,
    constrained_candidate_topks: list[int] | None = None,
    constrained_candidate_source: str = "transition",
) -> dict:
    residual = model(dataset.hidden, layer_ids=dataset.layer_ids)
    effective_residual = _effective_residual(
        model,
        residual,
        layer_ids=dataset.layer_ids,
        residual_scale=residual_scale,
    )
    logits = dataset.prior_logits + effective_residual
    loss = _training_loss(logits, dataset, pos_weight=pos_weight)
    prior_only_logits = dataset.prior_logits + 0.0 * residual
    metrics = {
        "loss": float(loss.detach().cpu().item()),
        "num_examples": int(dataset.hidden.shape[0]),
        "hidden_shape": list(dataset.hidden.shape),
        "label_shape": list(dataset.labels.shape),
        "sample_indices": dataset.sample_indices,
        "source_paths": dataset.source_paths,
        "baselines": {
            "frequency_prior": _metric_for_logits(dataset.frequency_logits, dataset, recall_ms),
            "transition_prior": _metric_for_logits(dataset.transition_logits, dataset, recall_ms),
            "frequency_plus_transition_prior": _metric_for_logits(
                dataset.prior_logits,
                dataset,
                recall_ms,
            ),
            "prior_only_codepath": _metric_for_logits(
                prior_only_logits,
                dataset,
                recall_ms,
            ),
        },
        "model": _metric_for_logits(logits, dataset, recall_ms),
        "logit_diagnostics": _logit_diagnostics(
            prior_logits=dataset.prior_logits,
            residual=residual,
            effective_residual=effective_residual,
            logits=logits,
            recall_ms=recall_ms,
            gamma_summary=model.residual_gamma_summary(),
        ),
    }
    if constrained_candidate_topks:
        candidate_logits = _candidate_logits_by_name(dataset, constrained_candidate_source)
        metrics["constrained_rerankers"] = {}
        for candidate_topk in constrained_candidate_topks:
            constrained_logits = _mask_logits_to_candidate_topk(
                logits,
                candidate_logits,
                candidate_topk=int(candidate_topk),
            )
            reranker_metrics = _metric_for_logits(constrained_logits, dataset, recall_ms)
            key = f"{constrained_candidate_source}_top{int(candidate_topk)}"
            item: dict[str, Any] = {
                "candidate_source": constrained_candidate_source,
                "candidate_topk": int(candidate_topk),
                "metrics": reranker_metrics,
                "topk_overlap_candidate_vs_reranker": {
                    str(m): _topk_overlap_at_m(constrained_logits, candidate_logits, m=m)
                    for m in recall_ms
                    if m <= int(candidate_topk)
                },
            }
            if dataset.target_mass is not None:
                transition_metrics = metrics["baselines"]["transition_prior"]
                item["mass_coverage_delta_vs_transition"] = {
                    str(m): reranker_metrics["mass_coverage_at"][str(m)]["coverage"]
                    - transition_metrics["mass_coverage_at"][str(m)]["coverage"]
                    for m in recall_ms
                }
                item["top1_hit_delta_vs_transition"] = {
                    str(m): reranker_metrics["top1_risk_at"][str(m)]["top1_hit_rate"]
                    - transition_metrics["top1_risk_at"][str(m)]["top1_hit_rate"]
                    for m in recall_ms
                }
                item["weighted_top1_miss_delta_vs_transition"] = {
                    str(m): reranker_metrics["top1_risk_at"][str(m)]["weighted_top1_miss"]
                    - transition_metrics["top1_risk_at"][str(m)]["weighted_top1_miss"]
                    for m in recall_ms
                }
                item["per_layer_delta_vs_transition"] = _per_layer_delta_vs_transition(
                    logits=constrained_logits,
                    transition_logits=dataset.transition_logits,
                    dataset=dataset,
                    recall_ms=recall_ms,
                )
            metrics["constrained_rerankers"][key] = item
    metrics.update({f"model_{key}": value for key, value in metrics["model"].items()})
    if dataset.target_mass is not None:
        metrics["mass_coverage_delta_vs_transition"] = {
            str(m): metrics["model"]["mass_coverage_at"][str(m)]["coverage"]
            - metrics["baselines"]["transition_prior"]["mass_coverage_at"][str(m)]["coverage"]
            for m in recall_ms
        }
        metrics["top1_hit_delta_vs_transition"] = {
            str(m): metrics["model"]["top1_risk_at"][str(m)]["top1_hit_rate"]
            - metrics["baselines"]["transition_prior"]["top1_risk_at"][str(m)]["top1_hit_rate"]
            for m in recall_ms
        }
        metrics["weighted_top1_miss_delta_vs_transition"] = {
            str(m): metrics["model"]["top1_risk_at"][str(m)]["weighted_top1_miss"]
            - metrics["baselines"]["transition_prior"]["top1_risk_at"][str(m)][
                "weighted_top1_miss"
            ]
            for m in recall_ms
        }
        metrics["per_layer_delta_vs_transition"] = _per_layer_delta_vs_transition(
            logits=logits,
            transition_logits=dataset.transition_logits,
            dataset=dataset,
            recall_ms=recall_ms,
        )
    return metrics


def _set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a previous-token MoE input hidden residual predictor smoke."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    config = load_yaml(resolve_path(args.config, base_dir=project_root))
    data_config = config.get("data", {})
    model_config = config.get("model", {})
    training_config = config.get("training", {})
    evaluation_config = config.get("evaluation", {})
    output_dir = resolve_path(
        config.get("output_dir", "outputs/checkpoints/hidden_residual_predictor_smoke"),
        base_dir=project_root,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device(training_config.get("device", "cpu"))
    num_experts = int(model_config.get("num_experts", 256))
    num_layers = int(model_config.get("num_layers", 40))
    hidden_size = int(model_config.get("hidden_size", 2048))
    future_window = int(model_config.get("future_window", 4))
    width = int(model_config.get("predictor_width", 256))
    dropout = float(model_config.get("dropout", 0.0))
    residual_scale = float(model_config.get("residual_scale", 1.0))
    zero_init_output = bool(model_config.get("zero_init_output", False))
    learnable_residual_gamma = bool(model_config.get("learnable_residual_gamma", False))
    initial_residual_gamma = float(model_config.get("initial_residual_gamma", residual_scale))
    residual_gamma_scope = str(model_config.get("residual_gamma_scope", "scalar"))
    steps = int(training_config.get("max_steps", 80))
    learning_rate = float(training_config.get("learning_rate", 1e-3))
    residual_l2 = float(training_config.get("residual_l2", 0.0))
    early_stopping_patience = int(training_config.get("early_stopping_patience", 0))
    eval_interval = int(training_config.get("eval_interval", 10))
    max_tokens = training_config.get("max_tokens")
    max_tokens = int(max_tokens) if max_tokens is not None else None
    recall_ms = _parse_recall_ms(training_config)
    constrained_candidate_topks = _parse_int_list(
        evaluation_config.get("constrained_candidate_topks"),
        name="constrained_candidate_topks",
    )
    constrained_candidate_source = str(
        evaluation_config.get("constrained_candidate_source", "transition")
    )
    seed = int(training_config.get("seed", 0))
    _set_seed(seed)

    payloads = _load_payloads(data_config, project_root=project_root)
    train_positions, val_positions = _split_positions(len(payloads), training_config)
    train_payloads = [payloads[position][2] for position in train_positions]
    frequency_scores, transition_matrix = fit_prior_tables(
        train_payloads,
        future_window=future_window,
        num_experts=num_experts,
    )
    train_data = _make_dataset(
        payloads,
        train_positions,
        frequency_scores=frequency_scores,
        transition_matrix=transition_matrix,
        future_window=future_window,
        num_experts=num_experts,
        max_tokens=max_tokens,
        device=device,
    )
    val_data = _make_dataset(
        payloads,
        val_positions,
        frequency_scores=frequency_scores,
        transition_matrix=transition_matrix,
        future_window=future_window,
        num_experts=num_experts,
        max_tokens=max_tokens,
        device=device,
    )
    assert train_data is not None

    model = HiddenResidualExpertPredictor(
        hidden_size=hidden_size,
        num_experts=num_experts,
        num_layers=num_layers,
        future_window=future_window,
        width=width,
        dropout=dropout,
        zero_init_output=zero_init_output,
        learnable_residual_gamma=learnable_residual_gamma,
        initial_residual_gamma=initial_residual_gamma,
        residual_gamma_scope=residual_gamma_scope,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    positive_fraction = float(train_data.labels.mean().item())
    pos_weight_config = training_config.get("pos_weight", "auto")
    if str(pos_weight_config).lower() == "auto":
        pos_weight_value = min(
            64.0,
            max(1.0, (1.0 - positive_fraction) / max(positive_fraction, 1e-6)),
        )
    else:
        pos_weight_value = float(pos_weight_config)
    pos_weight = torch.tensor(pos_weight_value, device=device)

    model.train()
    first_loss = None
    last_loss = None
    best_state_dict = copy.deepcopy(model.state_dict())
    best_step = 0
    best_val_loss = float("inf")
    bad_steps = 0
    stopped_early = False
    history: list[dict[str, float | int]] = []
    for step in range(steps):
        optimizer.zero_grad(set_to_none=True)
        residual = model(train_data.hidden, layer_ids=train_data.layer_ids)
        effective_residual = _effective_residual(
            model,
            residual,
            layer_ids=train_data.layer_ids,
            residual_scale=residual_scale,
        )
        logits = train_data.prior_logits + effective_residual
        loss = _training_loss(logits, train_data, pos_weight=pos_weight)
        if residual_l2 > 0.0:
            loss = loss + residual_l2 * effective_residual.float().square().mean()
        loss.backward()
        optimizer.step()
        value = float(loss.detach().cpu().item())
        if first_loss is None:
            first_loss = value
        last_loss = value
        if early_stopping_patience > 0 and val_data is not None and (
            (step + 1) % eval_interval == 0 or step == steps - 1
        ):
            model.eval()
            with torch.inference_mode():
                val_residual = model(val_data.hidden, layer_ids=val_data.layer_ids)
                val_logits = val_data.prior_logits + _effective_residual(
                    model,
                    val_residual,
                    layer_ids=val_data.layer_ids,
                    residual_scale=residual_scale,
                )
                val_loss = float(
                    _training_loss(val_logits, val_data, pos_weight=pos_weight)
                    .detach()
                    .cpu()
                    .item()
                )
            model.train()
            history.append({"step": step + 1, "train_loss": value, "val_loss": val_loss})
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_step = step + 1
                best_state_dict = copy.deepcopy(model.state_dict())
                bad_steps = 0
            else:
                bad_steps += 1
                if bad_steps >= early_stopping_patience:
                    stopped_early = True
                    break

    if early_stopping_patience > 0 and val_data is not None:
        model.load_state_dict(best_state_dict)

    model.eval()
    with torch.inference_mode():
        train_metrics = _evaluate(
            model=model,
            dataset=train_data,
            recall_ms=recall_ms,
            residual_scale=residual_scale,
            pos_weight=pos_weight,
            constrained_candidate_topks=constrained_candidate_topks,
            constrained_candidate_source=constrained_candidate_source,
        )
        val_metrics = None
        if val_data is not None:
            val_metrics = _evaluate(
                model=model,
                dataset=val_data,
                recall_ms=recall_ms,
                residual_scale=residual_scale,
                pos_weight=pos_weight,
                constrained_candidate_topks=constrained_candidate_topks,
                constrained_candidate_source=constrained_candidate_source,
            )

    checkpoint_path = output_dir / "model.pt"
    metrics_path = output_dir / "metrics.json"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": config,
            "frequency_scores": frequency_scores,
            "transition_matrix": transition_matrix,
        },
        checkpoint_path,
    )
    metrics = {
        "ok": True,
        "num_samples": len(payloads),
        "train_sample_positions": train_positions,
        "val_sample_positions": val_positions,
        "checkpoint_path": str(checkpoint_path),
        "metrics_path": str(metrics_path),
        "device": str(device),
        "seed": seed,
        "steps": steps,
        "trained_steps": step + 1,
        "stopped_early": stopped_early,
        "best_step": best_step,
        "best_val_loss": best_val_loss if best_val_loss != float("inf") else None,
        "early_stopping_history": history,
        "first_loss": first_loss,
        "last_train_loss": last_loss,
        "pos_weight": pos_weight_value,
        "positive_fraction": positive_fraction,
        "evaluation": {
            "constrained_candidate_topks": constrained_candidate_topks,
            "constrained_candidate_source": constrained_candidate_source,
        },
        "train": train_metrics,
        "val": val_metrics,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
