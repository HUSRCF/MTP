#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.training import (  # noqa: E402
    MtpRouterOnlyPredictor,
    TokenFrequencyTable,
    apply_token_frequency_table,
    apply_transition_matrix,
    build_token_frequency_table,
    build_mtp_router_alignment,
    mass_coverage_at_m,
    recall_at_m,
    router_topk_to_dense_feature,
    target_expert_ids_to_dense_weights,
    target_expert_ids_to_multihot,
    top1_risk_at_m,
    train_frequency_scores,
    train_transition_matrix,
)
from mtp_expert_prefetch.training.alignment_merge import (  # noqa: E402
    manifest_record_path,
    read_trace_manifest,
)
from mtp_expert_prefetch.tracing import load_trace_payload, resolve_trace_sample  # noqa: E402
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path  # noqa: E402


DEFAULT_CONFIG = Path("configs/train/mtp_predictor_smoke.yaml")


@dataclass(frozen=True)
class AlignmentSample:
    sample_idx: int
    source_path: Path
    batch: dict


@dataclass(frozen=True)
class TensorDataset:
    features: torch.Tensor
    labels: torch.Tensor
    target_mass: torch.Tensor | None
    target_layer_ids: torch.Tensor
    current_expert_feature: torch.Tensor | None
    source_token_ids: torch.Tensor | None
    target_token_ids: torch.Tensor | None
    sample_indices: list[int]
    source_paths: list[str]


@dataclass(frozen=True)
class BaselineState:
    label_frequency_logits: torch.Tensor
    mass_frequency_logits: torch.Tensor | None
    label_transition: torch.Tensor | None
    mass_transition: torch.Tensor | None
    source_token_label_table: TokenFrequencyTable | None
    source_token_mass_table: TokenFrequencyTable | None
    target_token_label_table: TokenFrequencyTable | None
    target_token_mass_table: TokenFrequencyTable | None


def _parse_recall_at_ms(training_config: dict) -> list[int]:
    configured = training_config.get("recall_at_ms", training_config.get("recall_at_m", 16))
    if isinstance(configured, int):
        values = [configured]
    elif isinstance(configured, list):
        values = [int(value) for value in configured]
    else:
        values = [int(part.strip()) for part in str(configured).split(",") if part.strip()]
    if not values:
        msg = "At least one recall@M value is required."
        raise ValueError(msg)
    return values


def _parse_int_list(value, *, name: str) -> list[int] | None:
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


def _load_alignment_samples(
    data_config: dict,
    *,
    project_root: Path,
    future_window: int,
) -> list[AlignmentSample]:
    if "alignment_path" in data_config:
        alignment_path = resolve_path(data_config["alignment_path"], base_dir=project_root)
        return [
            AlignmentSample(
                sample_idx=0,
                source_path=alignment_path,
                batch=torch.load(alignment_path, map_location="cpu", weights_only=False),
            )
        ]

    sample_path = data_config.get("trace_payload_path") or data_config.get("trace_sample")
    manifest_path = data_config.get("trace_manifest")
    if sample_path is None and manifest_path is None:
        msg = (
            "data must set either `alignment_path`, `trace_payload_path`, "
            "`trace_sample`, or `trace_manifest`."
        )
        raise KeyError(msg)

    resolved_sample = resolve_trace_sample(
        sample_path=resolve_path(sample_path, base_dir=project_root) if sample_path else None,
        manifest_path=resolve_path(manifest_path, base_dir=project_root) if manifest_path else None,
    )
    if sample_path is not None:
        records = [{"sample_idx": 0, "_resolved_path": str(resolved_sample)}]
    else:
        records = read_trace_manifest(resolve_path(manifest_path, base_dir=project_root))
        sample_indices = _parse_int_list(data_config.get("sample_indices"), name="sample_indices")
        if sample_indices is not None:
            allowed = set(sample_indices)
            records = [record for record in records if int(record["sample_idx"]) in allowed]
        max_samples = data_config.get("max_samples")
        if max_samples is not None:
            records = records[: int(max_samples)]

    samples: list[AlignmentSample] = []
    for record in records:
        path = Path(record.get("_resolved_path") or manifest_record_path(record))
        payload = load_trace_payload(path)
        alignment = build_mtp_router_alignment(
            payload,
            future_window=future_window,
            call_index=int(data_config.get("call_index", 0)),
            batch_index=int(data_config.get("batch_index", 0)),
        )
        samples.append(
            AlignmentSample(
                sample_idx=int(record.get("sample_idx", len(samples))),
                source_path=path,
                batch=alignment.as_dict(),
            )
        )
    if not samples:
        msg = "No alignment samples were loaded."
        raise RuntimeError(msg)
    return samples


def _split_sample_positions(num_samples: int, training_config: dict) -> tuple[list[int], list[int]]:
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
        train_positions = list(range(0, num_samples - val_count))
        val_positions = list(range(num_samples - val_count, num_samples))

    all_positions = train_positions + val_positions
    if len(set(all_positions)) != len(all_positions):
        msg = "Train and validation sample indices must not overlap."
        raise ValueError(msg)
    for position in all_positions:
        if position < 0 or position >= num_samples:
            msg = f"Sample index {position} out of range for {num_samples} samples."
            raise IndexError(msg)
    if not train_positions:
        msg = "At least one training sample is required."
        raise ValueError(msg)
    return train_positions, val_positions


def _samples_to_tensor_dataset(
    samples: list[AlignmentSample],
    positions: list[int],
    *,
    num_experts: int,
    max_tokens: int | None,
    device: torch.device,
) -> TensorDataset | None:
    if not positions:
        return None

    feature_parts: list[torch.Tensor] = []
    label_parts: list[torch.Tensor] = []
    target_mass_parts: list[torch.Tensor] = []
    current_feature_parts: list[torch.Tensor] = []
    source_token_id_parts: list[torch.Tensor] = []
    target_token_id_parts: list[torch.Tensor] = []
    has_target_mass: bool | None = None
    has_current_feature: bool | None = None
    has_token_ids: bool | None = None
    target_layer_ids: torch.Tensor | None = None
    sample_indices: list[int] = []
    source_paths: list[str] = []
    for position in positions:
        sample = samples[position]
        batch = sample.batch
        mtp_ids = batch["mtp_expert_ids"].to(torch.long)
        mtp_weights = batch["mtp_expert_weights"].to(torch.float32)
        target_ids = batch["target_expert_ids"].to(torch.long)
        layer_ids = batch["target_layer_ids"].to(torch.long)
        current_ids = batch.get("current_expert_ids")
        current_weights = batch.get("current_expert_weights")
        source_token_ids = batch.get("source_token_ids")
        target_token_ids = batch.get("target_token_ids")
        if max_tokens is not None:
            mtp_ids = mtp_ids[:max_tokens]
            mtp_weights = mtp_weights[:max_tokens]
            target_ids = target_ids[:max_tokens]
            if current_ids is not None:
                current_ids = current_ids[:max_tokens]
            if current_weights is not None:
                current_weights = current_weights[:max_tokens]
            if source_token_ids is not None:
                source_token_ids = source_token_ids[:max_tokens]
            if target_token_ids is not None:
                target_token_ids = target_token_ids[:max_tokens]
        features = router_topk_to_dense_feature(
            mtp_ids,
            mtp_weights,
            num_experts=num_experts,
        )
        labels = target_expert_ids_to_multihot(
            target_ids,
            num_experts=num_experts,
        )
        if "target_expert_weights" in batch:
            target_weights = batch["target_expert_weights"].to(torch.float32)
            if max_tokens is not None:
                target_weights = target_weights[:max_tokens]
            target_mass = target_expert_ids_to_dense_weights(
                target_ids,
                target_weights,
                num_experts=num_experts,
            )
            if has_target_mass is False:
                msg = "Either all samples or no samples must include target_expert_weights."
                raise ValueError(msg)
            has_target_mass = True
            target_mass_parts.append(target_mass)
        else:
            if has_target_mass is True:
                msg = "Either all samples or no samples must include target_expert_weights."
                raise ValueError(msg)
            has_target_mass = False
        if current_ids is not None:
            current_feature = router_topk_to_dense_feature(
                current_ids.to(torch.long),
                current_weights.to(torch.float32) if current_weights is not None else None,
                num_experts=num_experts,
            )
            if has_current_feature is False:
                msg = "Either all samples or no samples must include current_expert_ids."
                raise ValueError(msg)
            has_current_feature = True
            current_feature_parts.append(current_feature)
        else:
            if has_current_feature is True:
                msg = "Either all samples or no samples must include current_expert_ids."
                raise ValueError(msg)
            has_current_feature = False
        if source_token_ids is not None and target_token_ids is not None:
            if has_token_ids is False:
                msg = "Either all samples or no samples must include source/target token ids."
                raise ValueError(msg)
            has_token_ids = True
            source_token_id_parts.append(source_token_ids.to(torch.long))
            target_token_id_parts.append(target_token_ids.to(torch.long))
        else:
            if has_token_ids is True:
                msg = "Either all samples or no samples must include source/target token ids."
                raise ValueError(msg)
            has_token_ids = False
        if target_layer_ids is None:
            target_layer_ids = layer_ids
        elif not torch.equal(target_layer_ids, layer_ids):
            msg = "All samples must share target_layer_ids."
            raise ValueError(msg)
        feature_parts.append(features)
        label_parts.append(labels)
        sample_indices.append(sample.sample_idx)
        source_paths.append(str(sample.source_path))

    assert target_layer_ids is not None
    target_mass_tensor = None
    if has_target_mass:
        target_mass_tensor = torch.cat(target_mass_parts, dim=0).to(device)
    current_feature_tensor = None
    if has_current_feature:
        current_feature_tensor = torch.cat(current_feature_parts, dim=0).to(device)
    source_token_ids_tensor = None
    target_token_ids_tensor = None
    if has_token_ids:
        source_token_ids_tensor = torch.cat(source_token_id_parts, dim=0).to(device)
        target_token_ids_tensor = torch.cat(target_token_id_parts, dim=0).to(device)
    return TensorDataset(
        features=torch.cat(feature_parts, dim=0).to(device),
        labels=torch.cat(label_parts, dim=0).to(device),
        target_mass=target_mass_tensor,
        target_layer_ids=target_layer_ids.to(device),
        current_expert_feature=current_feature_tensor,
        source_token_ids=source_token_ids_tensor,
        target_token_ids=target_token_ids_tensor,
        sample_indices=sample_indices,
        source_paths=source_paths,
    )


def _build_baseline_state(train_data: TensorDataset) -> BaselineState:
    label_frequency_logits = train_frequency_scores(train_data.labels)
    mass_frequency_logits = (
        train_frequency_scores(train_data.target_mass)
        if train_data.target_mass is not None
        else None
    )
    label_transition = None
    mass_transition = None
    if train_data.current_expert_feature is not None:
        label_transition = train_transition_matrix(
            train_data.current_expert_feature,
            train_data.labels,
        )
        if train_data.target_mass is not None:
            mass_transition = train_transition_matrix(
                train_data.current_expert_feature,
                train_data.target_mass,
            )

    source_token_label_table = None
    source_token_mass_table = None
    target_token_label_table = None
    target_token_mass_table = None
    if train_data.source_token_ids is not None and train_data.target_token_ids is not None:
        source_token_label_table = build_token_frequency_table(
            train_data.source_token_ids,
            train_data.labels,
            fallback=label_frequency_logits,
        )
        target_token_label_table = build_token_frequency_table(
            train_data.target_token_ids,
            train_data.labels,
            fallback=label_frequency_logits,
        )
        if train_data.target_mass is not None and mass_frequency_logits is not None:
            source_token_mass_table = build_token_frequency_table(
                train_data.source_token_ids,
                train_data.target_mass,
                fallback=mass_frequency_logits,
            )
            target_token_mass_table = build_token_frequency_table(
                train_data.target_token_ids,
                train_data.target_mass,
                fallback=mass_frequency_logits,
            )

    return BaselineState(
        label_frequency_logits=label_frequency_logits,
        mass_frequency_logits=mass_frequency_logits,
        label_transition=label_transition,
        mass_transition=mass_transition,
        source_token_label_table=source_token_label_table,
        source_token_mass_table=source_token_mass_table,
        target_token_label_table=target_token_label_table,
        target_token_mass_table=target_token_mass_table,
    )


def _transition_logits_for_dataset(
    dataset: TensorDataset,
    transition: torch.Tensor | None,
) -> torch.Tensor | None:
    if transition is None or dataset.current_expert_feature is None:
        return None
    return apply_transition_matrix(dataset.current_expert_feature, transition)


def _token_frequency_logits_for_dataset(
    dataset: TensorDataset,
    table: TokenFrequencyTable | None,
    token_ids: torch.Tensor | None,
) -> torch.Tensor | None:
    if table is None or token_ids is None:
        return None
    return apply_token_frequency_table(table, token_ids, device=dataset.labels.device)


def _extra_baseline_logits(
    *,
    dataset: TensorDataset,
    baseline_state: BaselineState,
    use_mass: bool,
) -> dict[str, torch.Tensor]:
    logits_by_name: dict[str, torch.Tensor] = {}
    transition = baseline_state.mass_transition if use_mass else baseline_state.label_transition
    source_table = (
        baseline_state.source_token_mass_table
        if use_mass
        else baseline_state.source_token_label_table
    )
    target_table = (
        baseline_state.target_token_mass_table
        if use_mass
        else baseline_state.target_token_label_table
    )
    transition_logits = _transition_logits_for_dataset(dataset, transition)
    source_token_logits = _token_frequency_logits_for_dataset(
        dataset,
        source_table,
        dataset.source_token_ids,
    )
    target_token_logits = _token_frequency_logits_for_dataset(
        dataset,
        target_table,
        dataset.target_token_ids,
    )
    if transition_logits is not None:
        logits_by_name["train_transition_delta_layer"] = transition_logits
    if source_token_logits is not None:
        logits_by_name["train_source_token_frequency_delta_layer"] = source_token_logits
    if target_token_logits is not None:
        logits_by_name["train_target_token_frequency_delta_layer"] = target_token_logits
    if transition_logits is not None and target_token_logits is not None:
        frequency = (
            baseline_state.mass_frequency_logits
            if use_mass
            else baseline_state.label_frequency_logits
        ).to(device=dataset.labels.device, dtype=torch.float32)
        logits_by_name["train_freq_plus_transition_plus_target_token"] = (
            frequency.expand_as(transition_logits) + transition_logits + target_token_logits
        )
    return logits_by_name


def _baseline_recalls(
    *,
    features: torch.Tensor,
    labels: torch.Tensor,
    recall_ms: list[int],
    num_experts: int,
    frequency_logits: torch.Tensor | None = None,
    extra_logits_by_name: dict[str, torch.Tensor] | None = None,
) -> dict[str, dict[str, float]]:
    copy_logits = features[:, None, None, :].expand_as(labels)
    if frequency_logits is None:
        frequency_logits = labels.float().mean(dim=0, keepdim=True)
    frequency_logits = frequency_logits.to(
        device=labels.device,
        dtype=torch.float32,
    ).expand_as(labels)
    baselines: dict[str, dict[str, float]] = {
        "random_expected": {
            str(m): min(1.0, float(m) / float(num_experts))
            for m in recall_ms
        },
        "copy_mtp_router": {},
        "train_frequency_delta_layer": {},
    }
    for m in recall_ms:
        baselines["copy_mtp_router"][str(m)] = recall_at_m(copy_logits, labels, m=m).recall
        baselines["train_frequency_delta_layer"][str(m)] = recall_at_m(
            frequency_logits,
            labels,
            m=m,
        ).recall
    for name, logits in (extra_logits_by_name or {}).items():
        baselines[name] = {}
        for m in recall_ms:
            baselines[name][str(m)] = recall_at_m(logits, labels, m=m).recall
    return baselines


def _baseline_mass_coverages(
    *,
    features: torch.Tensor,
    target_mass: torch.Tensor,
    recall_ms: list[int],
    num_experts: int,
    frequency_logits: torch.Tensor | None = None,
    extra_logits_by_name: dict[str, torch.Tensor] | None = None,
) -> dict[str, dict[str, float]]:
    copy_logits = features[:, None, None, :].expand_as(target_mass)
    if frequency_logits is None:
        frequency_logits = target_mass.float().mean(dim=0, keepdim=True)
    frequency_logits = frequency_logits.to(
        device=target_mass.device,
        dtype=torch.float32,
    ).expand_as(target_mass)
    baselines: dict[str, dict[str, float]] = {
        "random_expected": {str(m): min(1.0, float(m) / float(num_experts)) for m in recall_ms},
        "copy_mtp_router": {},
        "train_frequency_delta_layer": {},
    }
    for m in recall_ms:
        baselines["copy_mtp_router"][str(m)] = mass_coverage_at_m(
            copy_logits,
            target_mass,
            m=m,
        ).coverage
        baselines["train_frequency_delta_layer"][str(m)] = mass_coverage_at_m(
            frequency_logits,
            target_mass,
            m=m,
        ).coverage
    for name, logits in (extra_logits_by_name or {}).items():
        baselines[name] = {}
        for m in recall_ms:
            baselines[name][str(m)] = mass_coverage_at_m(logits, target_mass, m=m).coverage
    return baselines


def _baseline_top1_risks(
    *,
    target_mass: torch.Tensor,
    recall_ms: list[int],
    frequency_logits: torch.Tensor,
    extra_logits_by_name: dict[str, torch.Tensor] | None = None,
) -> dict[str, dict[str, dict[str, float]]]:
    all_logits = {"train_frequency_delta_layer": frequency_logits}
    all_logits.update(extra_logits_by_name or {})
    baselines: dict[str, dict[str, dict[str, float]]] = {}
    for name, logits in all_logits.items():
        baselines[name] = {}
        for m in recall_ms:
            risk = top1_risk_at_m(logits, target_mass, m=m)
            baselines[name][str(m)] = {
                "top1_hit_rate": risk.top1_hit_rate,
                "weighted_top1_miss": risk.weighted_top1_miss,
                "hit_count": risk.hit_count,
                "total_count": risk.total_count,
                "weighted_miss_numerator": risk.weighted_miss_numerator,
            }
    return baselines


def _evaluate_split(
    *,
    model: MtpRouterOnlyPredictor,
    dataset: TensorDataset,
    pos_weight: torch.Tensor,
    recall_ms: list[int],
    num_experts: int,
    train_frequency_logits: torch.Tensor,
    train_frequency_mass_logits: torch.Tensor | None = None,
    baseline_state: BaselineState | None = None,
) -> dict:
    logits = model(dataset.features, target_layer_ids=dataset.target_layer_ids)
    loss = F.binary_cross_entropy_with_logits(logits, dataset.labels, pos_weight=pos_weight)
    recalls = {m: recall_at_m(logits, dataset.labels, m=m) for m in recall_ms}
    mass_coverages = None
    top1_risks = None
    if dataset.target_mass is not None:
        mass_coverages = {
            m: mass_coverage_at_m(logits, dataset.target_mass, m=m) for m in recall_ms
        }
        top1_risks = {m: top1_risk_at_m(logits, dataset.target_mass, m=m) for m in recall_ms}
    extra_label_logits = (
        _extra_baseline_logits(dataset=dataset, baseline_state=baseline_state, use_mass=False)
        if baseline_state is not None
        else {}
    )
    metrics = {
        "loss": float(loss.detach().cpu().item()),
        "num_tokens": int(dataset.features.shape[0]),
        "feature_shape": list(dataset.features.shape),
        "label_shape": list(dataset.labels.shape),
        "sample_indices": dataset.sample_indices,
        "source_paths": dataset.source_paths,
        "positive_fraction": float(dataset.labels.mean().detach().cpu().item()),
        "baseline_recall_at": _baseline_recalls(
            features=dataset.features,
            labels=dataset.labels,
            recall_ms=recall_ms,
            num_experts=num_experts,
            frequency_logits=train_frequency_logits,
            extra_logits_by_name=extra_label_logits,
        ),
        "recall_at": {
            str(m): {
                "recall": recalls[m].recall,
                "numerator": recalls[m].numerator,
                "denominator": recalls[m].denominator,
            }
            for m in recall_ms
        },
    }
    if dataset.target_mass is not None and mass_coverages is not None and top1_risks is not None:
        extra_mass_logits = (
            _extra_baseline_logits(dataset=dataset, baseline_state=baseline_state, use_mass=True)
            if baseline_state is not None
            else {}
        )
        frequency_mass_logits = (
            train_frequency_mass_logits
            if train_frequency_mass_logits is not None
            else train_frequency_logits
        )
        frequency_mass_logits = frequency_mass_logits.to(
            device=dataset.target_mass.device,
            dtype=torch.float32,
        ).expand_as(dataset.target_mass)
        metrics["target_mass_shape"] = list(dataset.target_mass.shape)
        metrics["target_mass_sum"] = float(dataset.target_mass.sum().detach().cpu().item())
        metrics["baseline_mass_coverage_at"] = _baseline_mass_coverages(
            features=dataset.features,
            target_mass=dataset.target_mass,
            recall_ms=recall_ms,
            num_experts=num_experts,
            frequency_logits=train_frequency_mass_logits,
            extra_logits_by_name=extra_mass_logits,
        )
        metrics["baseline_top1_risk_at"] = _baseline_top1_risks(
            target_mass=dataset.target_mass,
            recall_ms=recall_ms,
            frequency_logits=frequency_mass_logits,
            extra_logits_by_name=extra_mass_logits,
        )
        metrics["mass_coverage_at"] = {
            str(m): {
                "coverage": mass_coverages[m].coverage,
                "numerator": mass_coverages[m].numerator,
                "denominator": mass_coverages[m].denominator,
            }
            for m in recall_ms
        }
        metrics["top1_risk_at"] = {
            str(m): {
                "top1_hit_rate": top1_risks[m].top1_hit_rate,
                "weighted_top1_miss": top1_risks[m].weighted_top1_miss,
                "hit_count": top1_risks[m].hit_count,
                "total_count": top1_risks[m].total_count,
                "weighted_miss_numerator": top1_risks[m].weighted_miss_numerator,
            }
            for m in recall_ms
        }
        metrics["mass_coverage_delta_vs_baseline"] = {
            baseline_name: {
                str(m): metrics["mass_coverage_at"][str(m)]["coverage"] - baseline_values[str(m)]
                for m in recall_ms
            }
            for baseline_name, baseline_values in metrics["baseline_mass_coverage_at"].items()
        }
        metrics["top1_hit_delta_vs_baseline"] = {
            baseline_name: {
                str(m): metrics["top1_risk_at"][str(m)]["top1_hit_rate"]
                - baseline_values[str(m)]["top1_hit_rate"]
                for m in recall_ms
            }
            for baseline_name, baseline_values in metrics["baseline_top1_risk_at"].items()
        }
    for m, recall in recalls.items():
        metrics[f"recall_at_{m}"] = recall.recall
    if mass_coverages is not None:
        for m, coverage in mass_coverages.items():
            metrics[f"mass_coverage_at_{m}"] = coverage.coverage
    if top1_risks is not None:
        for m, risk in top1_risks.items():
            metrics[f"top1_hit_at_{m}"] = risk.top1_hit_rate
            metrics[f"weighted_top1_miss_at_{m}"] = risk.weighted_top1_miss
    metrics["recall_delta_vs_baseline"] = {
        baseline_name: {
            str(m): metrics["recall_at"][str(m)]["recall"] - baseline_values[str(m)]
            for m in recall_ms
        }
        for baseline_name, baseline_values in metrics["baseline_recall_at"].items()
    }
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a minimal MTP-router expert predictor smoke."
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

    output_dir = resolve_path(
        config.get("output_dir", "outputs/checkpoints/mtp_predictor_smoke"),
        base_dir=project_root,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device(training_config.get("device", "cpu"))
    num_experts = int(model_config.get("num_experts", 256))
    future_window = int(model_config.get("future_window", 4))
    num_layers = int(model_config.get("num_layers", 40))
    width = int(model_config.get("predictor_width", 128))
    dropout = float(model_config.get("dropout", 0.0))
    steps = int(training_config.get("max_steps", 40))
    learning_rate = float(training_config.get("learning_rate", 1e-3))
    recall_ms = _parse_recall_at_ms(training_config)
    max_tokens_config = training_config.get("max_tokens")
    max_tokens = int(max_tokens_config) if max_tokens_config is not None else None

    samples = _load_alignment_samples(
        data_config,
        project_root=project_root,
        future_window=future_window,
    )
    train_positions, val_positions = _split_sample_positions(len(samples), training_config)
    train_data = _samples_to_tensor_dataset(
        samples,
        train_positions,
        num_experts=num_experts,
        max_tokens=max_tokens,
        device=device,
    )
    val_data = _samples_to_tensor_dataset(
        samples,
        val_positions,
        num_experts=num_experts,
        max_tokens=max_tokens,
        device=device,
    )
    assert train_data is not None

    model = MtpRouterOnlyPredictor(
        num_experts=num_experts,
        num_layers=num_layers,
        future_window=future_window,
        width=width,
        dropout=dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    positive_fraction = float(train_data.labels.mean().item())
    pos_weight_config = training_config.get("pos_weight", 1.0)
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
    for _step in range(steps):
        optimizer.zero_grad(set_to_none=True)
        logits = model(train_data.features, target_layer_ids=train_data.target_layer_ids)
        loss = F.binary_cross_entropy_with_logits(logits, train_data.labels, pos_weight=pos_weight)
        loss.backward()
        optimizer.step()
        loss_value = float(loss.detach().cpu().item())
        if first_loss is None:
            first_loss = loss_value
        last_loss = loss_value

    model.eval()
    with torch.inference_mode():
        train_frequency_logits = train_data.labels.float().mean(dim=0, keepdim=True)
        train_frequency_mass_logits = (
            train_data.target_mass.float().mean(dim=0, keepdim=True)
            if train_data.target_mass is not None
            else None
        )
        baseline_state = _build_baseline_state(train_data)
        train_metrics = _evaluate_split(
            model=model,
            dataset=train_data,
            pos_weight=pos_weight,
            recall_ms=recall_ms,
            num_experts=num_experts,
            train_frequency_logits=train_frequency_logits,
            train_frequency_mass_logits=train_frequency_mass_logits,
            baseline_state=baseline_state,
        )
        val_metrics = None
        if val_data is not None:
            val_metrics = _evaluate_split(
                model=model,
                dataset=val_data,
                pos_weight=pos_weight,
                recall_ms=recall_ms,
                num_experts=num_experts,
                train_frequency_logits=train_frequency_logits,
                train_frequency_mass_logits=train_frequency_mass_logits,
                baseline_state=baseline_state,
            )

    checkpoint_path = output_dir / "model.pt"
    metrics_path = output_dir / "metrics.json"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": config,
            "num_experts": num_experts,
            "num_layers": num_layers,
            "future_window": future_window,
        },
        checkpoint_path,
    )
    metrics = {
        "ok": True,
        "num_samples": len(samples),
        "train_sample_positions": train_positions,
        "val_sample_positions": val_positions,
        "checkpoint_path": str(checkpoint_path),
        "metrics_path": str(metrics_path),
        "device": str(device),
        "steps": steps,
        "pos_weight": pos_weight_value,
        "first_loss": first_loss,
        "last_train_loss": last_loss,
        "train": train_metrics,
        "val": val_metrics,
    }
    metrics["final_loss"] = train_metrics["loss"]
    metrics["num_tokens"] = train_metrics["num_tokens"]
    metrics["feature_shape"] = train_metrics["feature_shape"]
    metrics["label_shape"] = train_metrics["label_shape"]
    metrics["positive_fraction"] = positive_fraction
    metrics["baseline_recall_at"] = train_metrics["baseline_recall_at"]
    metrics["recall_at"] = train_metrics["recall_at"]
    if "mass_coverage_at" in train_metrics:
        metrics["baseline_mass_coverage_at"] = train_metrics["baseline_mass_coverage_at"]
        metrics["mass_coverage_at"] = train_metrics["mass_coverage_at"]
        metrics["top1_risk_at"] = train_metrics["top1_risk_at"]
    for m in recall_ms:
        metrics[f"recall_at_{m}"] = train_metrics[f"recall_at_{m}"]
        if f"mass_coverage_at_{m}" in train_metrics:
            metrics[f"mass_coverage_at_{m}"] = train_metrics[f"mass_coverage_at_{m}"]
        if f"top1_hit_at_{m}" in train_metrics:
            metrics[f"top1_hit_at_{m}"] = train_metrics[f"top1_hit_at_{m}"]
            metrics[f"weighted_top1_miss_at_{m}"] = train_metrics[
                f"weighted_top1_miss_at_{m}"
            ]
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
