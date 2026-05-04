from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import torch

LAYER_RE = re.compile(r"(?:^|\.)layers\.(\d+)\.mlp\.gate$")


@dataclass(frozen=True)
class MtpRouterAlignmentBatch:
    mtp_expert_ids: torch.Tensor
    mtp_expert_weights: torch.Tensor
    current_expert_ids: torch.Tensor
    current_expert_weights: torch.Tensor | None
    target_expert_ids: torch.Tensor
    target_expert_weights: torch.Tensor | None
    target_layer_ids: torch.Tensor
    source_token_ids: torch.Tensor | None
    target_token_ids: torch.Tensor | None
    source_token_indices: torch.Tensor
    target_token_indices: torch.Tensor

    def as_dict(self) -> dict[str, torch.Tensor]:
        payload = {
            "mtp_expert_ids": self.mtp_expert_ids,
            "mtp_expert_weights": self.mtp_expert_weights,
            "current_expert_ids": self.current_expert_ids,
            "target_expert_ids": self.target_expert_ids,
            "target_layer_ids": self.target_layer_ids,
            "source_token_indices": self.source_token_indices,
            "target_token_indices": self.target_token_indices,
        }
        if self.current_expert_weights is not None:
            payload["current_expert_weights"] = self.current_expert_weights
        if self.target_expert_weights is not None:
            payload["target_expert_weights"] = self.target_expert_weights
        if self.source_token_ids is not None:
            payload["source_token_ids"] = self.source_token_ids
        if self.target_token_ids is not None:
            payload["target_token_ids"] = self.target_token_ids
        return payload


def build_mtp_router_alignment(
    payload: dict[str, Any],
    *,
    future_window: int = 4,
    call_index: int = 0,
    batch_index: int = 0,
) -> MtpRouterAlignmentBatch:
    if future_window <= 0:
        msg = f"future_window must be positive, got {future_window}"
        raise ValueError(msg)

    mtp_ids = _as_token_topk(payload["native_mtp_router_topk"], batch_index=batch_index).to(
        torch.long
    )
    mtp_weights = _as_token_topk(payload["native_mtp_router_weights"], batch_index=batch_index).to(
        torch.float32
    )
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
    elif isinstance(payload.get("router_scores"), dict) and payload["router_scores"]:
        target_scores_by_layer, score_layer_ids = stack_backbone_router_scores(
            payload,
            call_index=call_index,
            batch_index=batch_index,
        )
        if not torch.equal(layer_ids, score_layer_ids):
            msg = "router_topk and router_scores must have matching layer ids."
            raise ValueError(msg)
        target_weights_by_layer = torch.softmax(target_scores_by_layer.float(), dim=-1)

    num_tokens = min(int(mtp_ids.shape[0]), int(target_by_layer.shape[1]))
    valid_tokens = num_tokens - future_window
    if valid_tokens <= 0:
        msg = f"Need more than future_window={future_window} tokens, got {num_tokens}"
        raise ValueError(msg)

    source_token_indices = torch.arange(valid_tokens, dtype=torch.long)
    deltas = torch.arange(1, future_window + 1, dtype=torch.long)
    target_token_indices = source_token_indices[:, None] + deltas[None, :]
    target_expert_ids = target_by_layer[:, target_token_indices, :]
    target_expert_ids = target_expert_ids.permute(1, 2, 0, 3).contiguous()
    current_expert_ids = target_by_layer[:, source_token_indices, :]
    current_expert_ids = current_expert_ids.permute(1, 0, 2).contiguous()
    target_expert_weights = None
    current_expert_weights = None
    if target_weights_by_layer is not None:
        target_expert_weights = target_weights_by_layer[:, target_token_indices, :]
        target_expert_weights = target_expert_weights.permute(1, 2, 0, 3).contiguous()
        current_expert_weights = target_weights_by_layer[:, source_token_indices, :]
        current_expert_weights = current_expert_weights.permute(1, 0, 2).contiguous()

    source_token_ids = None
    target_token_ids = None
    if "input_ids" in payload:
        input_ids = _as_token_ids(payload["input_ids"], batch_index=batch_index)
        input_ids = input_ids[:num_tokens].to(torch.long)
        source_token_ids = input_ids[source_token_indices].contiguous()
        target_token_ids = input_ids[target_token_indices].contiguous()

    return MtpRouterAlignmentBatch(
        mtp_expert_ids=mtp_ids[:valid_tokens].contiguous(),
        mtp_expert_weights=mtp_weights[:valid_tokens].contiguous(),
        current_expert_ids=current_expert_ids,
        current_expert_weights=current_expert_weights,
        target_expert_ids=target_expert_ids,
        target_expert_weights=target_expert_weights,
        target_layer_ids=layer_ids,
        source_token_ids=source_token_ids,
        target_token_ids=target_token_ids,
        source_token_indices=source_token_indices,
        target_token_indices=target_token_indices,
    )


def stack_backbone_router_topk(
    payload: dict[str, Any],
    *,
    call_index: int = 0,
    batch_index: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    router_topk = payload.get("router_topk")
    if not isinstance(router_topk, dict) or not router_topk:
        msg = "Trace payload has no non-empty `router_topk` dict."
        raise KeyError(msg)

    layer_items = []
    for module_name, calls in router_topk.items():
        layer = _parse_layer_id(module_name)
        if layer is None:
            continue
        call = _select_call(calls, call_index, name=module_name)
        layer_items.append((layer, _as_token_topk(call, batch_index=batch_index).to(torch.long)))
    if not layer_items:
        msg = "No layer router top-k tensors matched `layers.<n>.mlp.gate`."
        raise KeyError(msg)

    layer_items.sort(key=lambda item: item[0])
    layer_ids = torch.tensor([layer for layer, _tensor in layer_items], dtype=torch.long)
    tensors = [tensor for _layer, tensor in layer_items]
    token_counts = {int(tensor.shape[0]) for tensor in tensors}
    topk_counts = {int(tensor.shape[-1]) for tensor in tensors}
    if len(token_counts) != 1 or len(topk_counts) != 1:
        msg = (
            "Router tensors must share token/top-k shapes; "
            f"got tokens={token_counts}, topk={topk_counts}"
        )
        raise ValueError(msg)
    return torch.stack(tensors, dim=0).contiguous(), layer_ids


def stack_backbone_router_weights(
    payload: dict[str, Any],
    *,
    call_index: int = 0,
    batch_index: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    router_weights = payload.get("router_weights")
    if not isinstance(router_weights, dict) or not router_weights:
        msg = "Trace payload has no non-empty `router_weights` dict."
        raise KeyError(msg)

    layer_items = []
    for module_name, calls in router_weights.items():
        layer = _parse_layer_id(module_name)
        if layer is None:
            continue
        call = _select_call(calls, call_index, name=module_name)
        layer_items.append((layer, _as_token_topk(call, batch_index=batch_index).to(torch.float32)))
    if not layer_items:
        msg = "No layer router weight tensors matched `layers.<n>.mlp.gate`."
        raise KeyError(msg)

    layer_items.sort(key=lambda item: item[0])
    layer_ids = torch.tensor([layer for layer, _tensor in layer_items], dtype=torch.long)
    tensors = [tensor for _layer, tensor in layer_items]
    token_counts = {int(tensor.shape[0]) for tensor in tensors}
    topk_counts = {int(tensor.shape[-1]) for tensor in tensors}
    if len(token_counts) != 1 or len(topk_counts) != 1:
        msg = (
            "Router weight tensors must share token/top-k shapes; "
            f"got tokens={token_counts}, topk={topk_counts}"
        )
        raise ValueError(msg)
    return torch.stack(tensors, dim=0).contiguous(), layer_ids


def stack_backbone_router_scores(
    payload: dict[str, Any],
    *,
    call_index: int = 0,
    batch_index: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    router_scores = payload.get("router_scores")
    if not isinstance(router_scores, dict) or not router_scores:
        msg = "Trace payload has no non-empty `router_scores` dict."
        raise KeyError(msg)

    layer_items = []
    for module_name, calls in router_scores.items():
        layer = _parse_layer_id(module_name)
        if layer is None:
            continue
        call = _select_call(calls, call_index, name="router_scores")
        layer_items.append((layer, _as_token_topk(call, batch_index=batch_index).to(torch.float32)))
    if not layer_items:
        msg = "No layer router score tensors matched `layers.<n>.mlp.gate`."
        raise KeyError(msg)

    layer_items.sort(key=lambda item: item[0])
    layer_ids = torch.tensor([layer for layer, _tensor in layer_items], dtype=torch.long)
    tensors = [tensor for _layer, tensor in layer_items]
    token_counts = {int(tensor.shape[0]) for tensor in tensors}
    topk_counts = {int(tensor.shape[-1]) for tensor in tensors}
    if len(token_counts) != 1 or len(topk_counts) != 1:
        msg = (
            "Router score tensors must share token/top-k shapes; "
            f"got tokens={token_counts}, topk={topk_counts}"
        )
        raise ValueError(msg)
    return torch.stack(tensors, dim=0).contiguous(), layer_ids


def _as_token_topk(value: Any, *, batch_index: int = 0) -> torch.Tensor:
    tensor = torch.as_tensor(value)
    if tensor.ndim == 3:
        batch = _normalize_index(batch_index, tensor.shape[0], name="batch_index")
        return tensor[batch].contiguous()
    if tensor.ndim == 2:
        return tensor.contiguous()
    msg = f"Expected token top-k tensor with 2 or 3 dims, got {tuple(tensor.shape)}"
    raise ValueError(msg)


def _as_token_ids(value: Any, *, batch_index: int = 0) -> torch.Tensor:
    tensor = torch.as_tensor(value)
    if tensor.ndim == 2:
        batch = _normalize_index(batch_index, tensor.shape[0], name="batch_index")
        return tensor[batch].contiguous()
    if tensor.ndim == 1:
        return tensor.contiguous()
    msg = f"Expected input_ids with 1 or 2 dims, got {tuple(tensor.shape)}"
    raise ValueError(msg)


def _select_call(calls: Any, call_index: int, *, name: str) -> Any:
    if not isinstance(calls, list) or not calls:
        msg = f"{name} entry is empty or not a list."
        raise ValueError(msg)
    index = _normalize_index(call_index, len(calls), name="call_index")
    return calls[index]


def _parse_layer_id(module_name: str) -> int | None:
    match = LAYER_RE.search(module_name)
    if match:
        return int(match.group(1))
    if "layers." in module_name and ".mlp.gate" in module_name:
        fallback = re.search(r"layers\.(\d+)\.", module_name)
        if fallback:
            return int(fallback.group(1))
    return None


def _normalize_index(index: int, size: int, *, name: str) -> int:
    if size <= 0:
        msg = f"Cannot index empty dimension for {name}."
        raise IndexError(msg)
    normalized = index + size if index < 0 else index
    if normalized < 0 or normalized >= size:
        msg = f"{name}={index} out of range for size {size}"
        raise IndexError(msg)
    return normalized
