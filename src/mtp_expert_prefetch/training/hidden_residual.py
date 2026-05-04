from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn.functional as F

from mtp_expert_prefetch.training.baselines import (
    apply_transition_matrix,
    train_frequency_scores,
    train_transition_matrix,
)
from mtp_expert_prefetch.training.mtp_alignment import (
    stack_backbone_router_topk,
    stack_backbone_router_weights,
)
from mtp_expert_prefetch.training.predictor import (
    router_topk_to_dense_feature,
    target_expert_ids_to_dense_weights,
    target_expert_ids_to_multihot,
)

LAYER_RE = re.compile(r"(?:^|\.)layers\.(\d+)\.mlp\.gate$")


@dataclass(frozen=True)
class PreviousTokenHiddenBatch:
    hidden: torch.Tensor
    layer_ids: torch.Tensor
    current_expert_feature: torch.Tensor
    labels: torch.Tensor
    target_mass: torch.Tensor | None
    prior_logits: torch.Tensor
    transition_logits: torch.Tensor
    frequency_logits: torch.Tensor
    num_tokens: int
    num_layers: int
    source_token_indices: torch.Tensor


class HiddenResidualExpertPredictor(torch.nn.Module):
    def __init__(
        self,
        *,
        hidden_size: int = 2048,
        num_experts: int = 256,
        num_layers: int = 40,
        future_window: int = 4,
        width: int = 256,
        dropout: float = 0.0,
        zero_init_output: bool = False,
        learnable_residual_gamma: bool = False,
        initial_residual_gamma: float = 1.0,
        residual_gamma_scope: str = "scalar",
    ) -> None:
        super().__init__()
        self.hidden_size = int(hidden_size)
        self.num_experts = int(num_experts)
        self.num_layers = int(num_layers)
        self.future_window = int(future_window)
        self.learnable_residual_gamma = bool(learnable_residual_gamma)
        self.residual_gamma_scope = str(residual_gamma_scope)
        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(self.hidden_size, width),
            torch.nn.SiLU(),
            torch.nn.LayerNorm(width),
            torch.nn.Dropout(dropout),
        )
        self.layer_embedding = torch.nn.Embedding(self.num_layers, width)
        self.delta_embedding = torch.nn.Embedding(self.future_window, width)
        self.classifier = torch.nn.Linear(width, self.num_experts)
        if zero_init_output:
            torch.nn.init.zeros_(self.classifier.weight)
            torch.nn.init.zeros_(self.classifier.bias)
        if self.learnable_residual_gamma:
            if self.residual_gamma_scope not in {"scalar", "layer"}:
                msg = "residual_gamma_scope must be 'scalar' or 'layer'."
                raise ValueError(msg)
            gamma = max(float(initial_residual_gamma), 1e-8)
            raw = _inverse_softplus(gamma)
            shape = (self.num_layers,) if self.residual_gamma_scope == "layer" else ()
            self.raw_residual_gamma = torch.nn.Parameter(torch.full(shape, raw))
        else:
            self.register_parameter("raw_residual_gamma", None)

    def forward(self, hidden: torch.Tensor, *, layer_ids: torch.Tensor) -> torch.Tensor:
        if hidden.ndim != 2 or hidden.shape[-1] != self.hidden_size:
            msg = f"Expected hidden [examples, {self.hidden_size}], got {tuple(hidden.shape)}"
            raise ValueError(msg)
        if layer_ids.ndim != 1 or layer_ids.shape[0] != hidden.shape[0]:
            msg = (
                "layer_ids must have shape [examples] matching hidden, "
                f"got {tuple(layer_ids.shape)} and {tuple(hidden.shape)}"
            )
            raise ValueError(msg)
        state = self.encoder(hidden)
        deltas = torch.arange(self.future_window, device=hidden.device)
        context = (
            state[:, None, :]
            + self.layer_embedding(layer_ids.to(device=hidden.device, dtype=torch.long))[:, None, :]
            + self.delta_embedding(deltas)[None, :, :]
        )
        return self.classifier(F.silu(context))

    def apply_residual_scale(
        self,
        residual: torch.Tensor,
        *,
        layer_ids: torch.Tensor,
        fixed_scale: float,
    ) -> torch.Tensor:
        if self.raw_residual_gamma is None:
            return float(fixed_scale) * residual
        gamma = F.softplus(self.raw_residual_gamma)
        if self.residual_gamma_scope == "layer":
            gamma = gamma[layer_ids.to(device=residual.device, dtype=torch.long)]
            return gamma[:, None, None].to(dtype=residual.dtype) * residual
        return gamma.to(device=residual.device, dtype=residual.dtype) * residual

    def residual_gamma_summary(self) -> dict[str, float | str] | None:
        if self.raw_residual_gamma is None:
            return None
        gamma = F.softplus(self.raw_residual_gamma.detach()).float().cpu()
        return {
            "scope": self.residual_gamma_scope,
            "min": float(gamma.min().item()),
            "max": float(gamma.max().item()),
            "mean": float(gamma.mean().item()),
            "std": float(gamma.std(unbiased=False).item()),
        }


def _inverse_softplus(value: float) -> float:
    if value > 20.0:
        return value
    return math.log(math.expm1(value))


def build_previous_token_hidden_batch(
    payload: dict[str, Any],
    *,
    frequency_scores: torch.Tensor,
    transition_matrix: torch.Tensor,
    future_window: int = 4,
    num_experts: int = 256,
    call_index: int = 0,
    batch_index: int = 0,
    prior_epsilon: float = 1e-6,
) -> PreviousTokenHiddenBatch:
    target_by_layer, layer_ids = stack_backbone_router_topk(
        payload,
        call_index=call_index,
        batch_index=batch_index,
    )
    target_weights_by_layer = None
    if isinstance(payload.get("router_weights"), dict) and payload["router_weights"]:
        target_weights_by_layer, weight_layer_ids = stack_backbone_router_weights(
            payload,
            call_index=call_index,
            batch_index=batch_index,
        )
        if not torch.equal(layer_ids, weight_layer_ids):
            msg = "router_topk and router_weights must have matching layer ids."
            raise ValueError(msg)

    hidden_by_layer, hidden_layer_ids = stack_router_input_hidden(payload, call_index=call_index)
    if not torch.equal(layer_ids, hidden_layer_ids):
        msg = "router_topk and router_input_hidden must have matching layer ids."
        raise ValueError(msg)

    num_tokens = min(int(target_by_layer.shape[1]), int(hidden_by_layer.shape[1]))
    valid_tokens = num_tokens - future_window
    if valid_tokens <= 0:
        msg = f"Need more than future_window={future_window} tokens, got {num_tokens}"
        raise ValueError(msg)

    source_token_indices = torch.arange(valid_tokens, dtype=torch.long)
    deltas = torch.arange(1, future_window + 1, dtype=torch.long)
    target_token_indices = source_token_indices[:, None] + deltas[None, :]

    current_ids = target_by_layer[:, source_token_indices, :].permute(1, 0, 2).contiguous()
    current_weights = None
    if target_weights_by_layer is not None:
        current_weights = target_weights_by_layer[:, source_token_indices, :]
        current_weights = current_weights.permute(1, 0, 2).contiguous()
    current_feature = router_topk_to_dense_feature(
        current_ids,
        current_weights,
        num_experts=num_experts,
    )

    target_ids = target_by_layer[:, target_token_indices, :]
    target_ids = target_ids.permute(1, 2, 0, 3).contiguous()
    labels_by_token = target_expert_ids_to_multihot(target_ids, num_experts=num_experts)

    target_mass_by_token = None
    if target_weights_by_layer is not None:
        target_weights = target_weights_by_layer[:, target_token_indices, :]
        target_weights = target_weights.permute(1, 2, 0, 3).contiguous()
        target_mass_by_token = target_expert_ids_to_dense_weights(
            target_ids,
            target_weights,
            num_experts=num_experts,
        )

    hidden = hidden_by_layer[:, source_token_indices, :]
    hidden = hidden.permute(1, 0, 2).contiguous()
    num_valid, num_layers, hidden_size = hidden.shape

    transition_scores = apply_transition_matrix(current_feature, transition_matrix)
    frequency = frequency_scores.to(dtype=torch.float32)
    if frequency.shape != (1, future_window, num_layers, num_experts):
        msg = (
            "frequency_scores must have shape [1, future_window, layers, experts], "
            f"got {tuple(frequency.shape)}"
        )
        raise ValueError(msg)
    frequency_scores_by_token = frequency.expand(num_valid, -1, -1, -1)
    prior_by_token = (
        torch.log(frequency_scores_by_token.clamp_min(prior_epsilon))
        + torch.log(transition_scores.clamp_min(prior_epsilon))
    )

    return PreviousTokenHiddenBatch(
        hidden=hidden.reshape(num_valid * num_layers, hidden_size).to(torch.float32),
        layer_ids=layer_ids.repeat(num_valid),
        current_expert_feature=current_feature.reshape(num_valid * num_layers, num_experts),
        labels=labels_by_token.permute(0, 2, 1, 3)
        .reshape(num_valid * num_layers, future_window, num_experts)
        .to(torch.float32),
        target_mass=(
            target_mass_by_token.permute(0, 2, 1, 3)
            .reshape(num_valid * num_layers, future_window, num_experts)
            .to(torch.float32)
            if target_mass_by_token is not None
            else None
        ),
        prior_logits=prior_by_token.permute(0, 2, 1, 3)
        .reshape(num_valid * num_layers, future_window, num_experts)
        .to(torch.float32),
        transition_logits=transition_scores.permute(0, 2, 1, 3)
        .reshape(num_valid * num_layers, future_window, num_experts)
        .to(torch.float32),
        frequency_logits=frequency_scores_by_token.permute(0, 2, 1, 3)
        .reshape(num_valid * num_layers, future_window, num_experts)
        .to(torch.float32),
        num_tokens=num_valid,
        num_layers=num_layers,
        source_token_indices=source_token_indices,
    )


def fit_prior_tables(
    payloads: list[dict[str, Any]],
    *,
    future_window: int = 4,
    num_experts: int = 256,
    call_index: int = 0,
    batch_index: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    current_parts: list[torch.Tensor] = []
    label_parts: list[torch.Tensor] = []
    for payload in payloads:
        current_feature, labels = _payload_current_and_target_dense(
            payload,
            future_window=future_window,
            num_experts=num_experts,
            call_index=call_index,
            batch_index=batch_index,
        )
        current_parts.append(current_feature)
        label_parts.append(labels)
    current = torch.cat(current_parts, dim=0)
    labels = torch.cat(label_parts, dim=0)
    return train_frequency_scores(labels), train_transition_matrix(current, labels)


def stack_router_input_hidden(
    payload: dict[str, Any],
    *,
    call_index: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    hidden_dict = payload.get("router_input_hidden")
    if not isinstance(hidden_dict, dict) or not hidden_dict:
        msg = "Trace payload has no non-empty `router_input_hidden` dict."
        raise KeyError(msg)

    layer_items = []
    for module_name, calls in hidden_dict.items():
        layer = _parse_layer_id(module_name)
        if layer is None:
            continue
        if not isinstance(calls, list) or not calls:
            msg = f"Router hidden entry {module_name!r} is empty or not a list."
            raise ValueError(msg)
        index = call_index + len(calls) if call_index < 0 else call_index
        if index < 0 or index >= len(calls):
            msg = f"call_index={call_index} out of range for {module_name!r}."
            raise IndexError(msg)
        tensor = torch.as_tensor(calls[index]).detach().cpu()
        if tensor.ndim != 2:
            msg = f"Expected router input hidden [tokens, hidden], got {tuple(tensor.shape)}"
            raise ValueError(msg)
        layer_items.append((layer, tensor.to(torch.float32)))
    if not layer_items:
        msg = "No router input hidden tensors matched `layers.<n>.mlp.gate`."
        raise KeyError(msg)

    layer_items.sort(key=lambda item: item[0])
    layer_ids = torch.tensor([layer for layer, _tensor in layer_items], dtype=torch.long)
    tensors = [tensor for _layer, tensor in layer_items]
    token_counts = {int(tensor.shape[0]) for tensor in tensors}
    hidden_sizes = {int(tensor.shape[-1]) for tensor in tensors}
    if len(token_counts) != 1 or len(hidden_sizes) != 1:
        msg = (
            "Router hidden tensors must share token/hidden shapes; "
            f"got tokens={token_counts}, hidden={hidden_sizes}"
        )
        raise ValueError(msg)
    return torch.stack(tensors, dim=0).contiguous(), layer_ids


def _payload_current_and_target_dense(
    payload: dict[str, Any],
    *,
    future_window: int,
    num_experts: int,
    call_index: int,
    batch_index: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    target_by_layer, _layer_ids = stack_backbone_router_topk(
        payload,
        call_index=call_index,
        batch_index=batch_index,
    )
    target_weights_by_layer = None
    if isinstance(payload.get("router_weights"), dict) and payload["router_weights"]:
        target_weights_by_layer, _weight_layer_ids = stack_backbone_router_weights(
            payload,
            call_index=call_index,
            batch_index=batch_index,
        )
    num_tokens = int(target_by_layer.shape[1])
    valid_tokens = num_tokens - future_window
    if valid_tokens <= 0:
        msg = f"Need more than future_window={future_window} tokens, got {num_tokens}"
        raise ValueError(msg)
    source_token_indices = torch.arange(valid_tokens, dtype=torch.long)
    deltas = torch.arange(1, future_window + 1, dtype=torch.long)
    target_token_indices = source_token_indices[:, None] + deltas[None, :]
    current_ids = target_by_layer[:, source_token_indices, :].permute(1, 0, 2).contiguous()
    current_weights = None
    if target_weights_by_layer is not None:
        current_weights = target_weights_by_layer[:, source_token_indices, :]
        current_weights = current_weights.permute(1, 0, 2).contiguous()
    target_ids = target_by_layer[:, target_token_indices, :]
    target_ids = target_ids.permute(1, 2, 0, 3).contiguous()
    return (
        router_topk_to_dense_feature(
            current_ids,
            current_weights,
            num_experts=num_experts,
        ),
        target_expert_ids_to_multihot(target_ids, num_experts=num_experts),
    )


def _parse_layer_id(module_name: str) -> int | None:
    match = LAYER_RE.search(module_name)
    if match:
        return int(match.group(1))
    if "layers." in module_name and ".mlp.gate" in module_name:
        fallback = re.search(r"layers\.(\d+)\.", module_name)
        if fallback:
            return int(fallback.group(1))
    return None
