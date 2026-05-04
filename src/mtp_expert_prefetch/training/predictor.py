from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class RecallAtM:
    recall: float
    numerator: float
    denominator: float


@dataclass(frozen=True)
class MassCoverageAtM:
    coverage: float
    numerator: float
    denominator: float


@dataclass(frozen=True)
class Top1RiskAtM:
    top1_hit_rate: float
    weighted_top1_miss: float
    hit_count: float
    total_count: float
    weighted_miss_numerator: float


def target_expert_ids_to_multihot(
    target_expert_ids: torch.Tensor,
    *,
    num_experts: int = 256,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    ids = target_expert_ids.to(torch.long)
    if ids.ndim < 1:
        msg = f"target_expert_ids must have at least 1 dim, got {tuple(ids.shape)}"
        raise ValueError(msg)
    if int(ids.min()) < 0 or int(ids.max()) >= num_experts:
        msg = f"Expert ids out of range [0, {num_experts - 1}]"
        raise ValueError(msg)
    labels = torch.zeros(*ids.shape[:-1], num_experts, dtype=dtype, device=ids.device)
    labels.scatter_(-1, ids, 1.0)
    return labels


def target_expert_ids_to_dense_weights(
    target_expert_ids: torch.Tensor,
    target_expert_weights: torch.Tensor,
    *,
    num_experts: int = 256,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    ids = target_expert_ids.to(torch.long)
    weights = target_expert_weights.to(device=ids.device, dtype=dtype)
    if ids.shape != weights.shape:
        msg = (
            f"target_expert_weights shape {tuple(weights.shape)} "
            f"does not match ids {tuple(ids.shape)}"
        )
        raise ValueError(msg)
    if ids.ndim < 1:
        msg = f"target_expert_ids must have at least 1 dim, got {tuple(ids.shape)}"
        raise ValueError(msg)
    if int(ids.min()) < 0 or int(ids.max()) >= num_experts:
        msg = f"Expert ids out of range [0, {num_experts - 1}]"
        raise ValueError(msg)
    dense = torch.zeros(*ids.shape[:-1], num_experts, dtype=dtype, device=ids.device)
    dense.scatter_add_(-1, ids, weights)
    return dense


def router_topk_to_dense_feature(
    expert_ids: torch.Tensor,
    expert_weights: torch.Tensor | None = None,
    *,
    num_experts: int = 256,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    ids = expert_ids.to(torch.long)
    if ids.ndim < 1:
        msg = f"expert_ids must have at least 1 dim, got {tuple(ids.shape)}"
        raise ValueError(msg)
    if int(ids.min()) < 0 or int(ids.max()) >= num_experts:
        msg = f"Expert ids out of range [0, {num_experts - 1}]"
        raise ValueError(msg)
    if expert_weights is None:
        weights = torch.full(ids.shape, 1.0 / ids.shape[-1], dtype=dtype, device=ids.device)
    else:
        weights = expert_weights.to(device=ids.device, dtype=dtype)
        if weights.shape != ids.shape:
            msg = (
                f"expert_weights shape {tuple(weights.shape)} "
                f"does not match ids {tuple(ids.shape)}"
            )
            raise ValueError(msg)
    features = torch.zeros(*ids.shape[:-1], num_experts, dtype=dtype, device=ids.device)
    features.scatter_add_(-1, ids, weights)
    return features


def recall_at_m(logits: torch.Tensor, labels: torch.Tensor, *, m: int) -> RecallAtM:
    if logits.shape != labels.shape:
        msg = (
            f"logits and labels must share shape; "
            f"got {tuple(logits.shape)} and {tuple(labels.shape)}"
        )
        raise ValueError(msg)
    if not 0 < m <= logits.shape[-1]:
        msg = f"m must be in [1, {logits.shape[-1]}], got {m}"
        raise ValueError(msg)

    topm = torch.topk(logits.float(), k=m, dim=-1).indices
    predicted = torch.zeros_like(labels, dtype=torch.bool)
    predicted.scatter_(-1, topm, True)
    truth = labels > 0
    numerator = (predicted & truth).sum().to(torch.float32)
    denominator = truth.sum().to(torch.float32)
    recall = numerator / denominator.clamp_min(1.0)
    return RecallAtM(
        recall=float(recall.item()),
        numerator=float(numerator.item()),
        denominator=float(denominator.item()),
    )


def mass_coverage_at_m(
    logits: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    m: int,
) -> MassCoverageAtM:
    if logits.shape != target_mass.shape:
        msg = (
            f"logits and target_mass must share shape; "
            f"got {tuple(logits.shape)} and {tuple(target_mass.shape)}"
        )
        raise ValueError(msg)
    if not 0 < m <= logits.shape[-1]:
        msg = f"m must be in [1, {logits.shape[-1]}], got {m}"
        raise ValueError(msg)

    topm = torch.topk(logits.float(), k=m, dim=-1).indices
    predicted = torch.zeros_like(target_mass, dtype=torch.bool)
    predicted.scatter_(-1, topm, True)
    mass = target_mass.float().clamp_min(0.0)
    numerator = mass[predicted].sum().to(torch.float32)
    denominator = mass.sum().to(torch.float32)
    coverage = numerator / denominator.clamp_min(1e-12)
    return MassCoverageAtM(
        coverage=float(coverage.item()),
        numerator=float(numerator.item()),
        denominator=float(denominator.item()),
    )


def top1_risk_at_m(
    logits: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    m: int,
) -> Top1RiskAtM:
    if logits.shape != target_mass.shape:
        msg = (
            f"logits and target_mass must share shape; "
            f"got {tuple(logits.shape)} and {tuple(target_mass.shape)}"
        )
        raise ValueError(msg)
    if not 0 < m <= logits.shape[-1]:
        msg = f"m must be in [1, {logits.shape[-1]}], got {m}"
        raise ValueError(msg)

    topm = torch.topk(logits.float(), k=m, dim=-1).indices
    target = target_mass.float().clamp_min(0.0)
    true_top1 = torch.argmax(target, dim=-1, keepdim=True)
    true_top1_weight = torch.gather(target, -1, true_top1).squeeze(-1)
    hit = (topm == true_top1).any(dim=-1)
    hit_count = hit.to(torch.float32).sum()
    total_count = torch.tensor(float(hit.numel()), dtype=torch.float32, device=logits.device)
    weighted_miss = ((~hit).to(torch.float32) * true_top1_weight).sum()
    return Top1RiskAtM(
        top1_hit_rate=float((hit_count / total_count.clamp_min(1.0)).item()),
        weighted_top1_miss=float((weighted_miss / total_count.clamp_min(1.0)).item()),
        hit_count=float(hit_count.item()),
        total_count=float(total_count.item()),
        weighted_miss_numerator=float(weighted_miss.item()),
    )


class MtpRouterOnlyPredictor(torch.nn.Module):
    def __init__(
        self,
        *,
        num_experts: int = 256,
        num_layers: int = 40,
        future_window: int = 4,
        width: int = 128,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.num_experts = int(num_experts)
        self.num_layers = int(num_layers)
        self.future_window = int(future_window)
        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(self.num_experts, width),
            torch.nn.SiLU(),
            torch.nn.LayerNorm(width),
            torch.nn.Dropout(dropout),
        )
        self.delta_embedding = torch.nn.Embedding(self.future_window, width)
        self.layer_embedding = torch.nn.Embedding(self.num_layers, width)
        self.classifier = torch.nn.Linear(width, self.num_experts)

    def forward(
        self,
        mtp_router_feature: torch.Tensor,
        *,
        target_layer_ids: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if mtp_router_feature.ndim != 2 or mtp_router_feature.shape[-1] != self.num_experts:
            msg = (
                f"Expected mtp_router_feature [tokens, {self.num_experts}], "
                f"got {tuple(mtp_router_feature.shape)}"
            )
            raise ValueError(msg)
        token_state = self.encoder(mtp_router_feature)
        deltas = torch.arange(self.future_window, device=mtp_router_feature.device)
        if target_layer_ids is None:
            layer_ids = torch.arange(self.num_layers, device=mtp_router_feature.device)
        else:
            layer_ids = target_layer_ids.to(device=mtp_router_feature.device, dtype=torch.long)

        context = (
            token_state[:, None, None, :]
            + self.delta_embedding(deltas)[None, :, None, :]
            + self.layer_embedding(layer_ids)[None, None, :, :]
        )
        return self.classifier(F.silu(context))
