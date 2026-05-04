from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

LAYER_RE_TEMPLATE = r"(?:^|\.)layers\.{layer}\.mlp\.gate$"


@dataclass(frozen=True)
class RouterTopKSelection:
    module_name: str
    expert_ids: torch.Tensor
    expert_weights: torch.Tensor
    raw_scores: torch.Tensor | None
    call_index: int
    batch_index: int | None
    token_index: int | None


def load_trace_payload(path: str | Path) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        payload = torch.load(path, map_location="cpu")
    if not isinstance(payload, dict):
        msg = f"Expected trace payload dict in {path}, got {type(payload).__name__}"
        raise TypeError(msg)
    return payload


def resolve_trace_sample(
    *,
    sample_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
) -> Path:
    if sample_path is not None:
        path = Path(sample_path).expanduser().resolve()
        if not path.exists():
            msg = f"Missing trace sample: {path}"
            raise FileNotFoundError(msg)
        return path

    if manifest_path is None:
        msg = "Either sample_path or manifest_path is required."
        raise ValueError(msg)
    manifest_path = Path(manifest_path).expanduser().resolve()
    if not manifest_path.exists():
        msg = f"Missing trace manifest: {manifest_path}"
        raise FileNotFoundError(msg)

    with manifest_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            path = manifest_path.parent / record["path"]
            if not path.exists():
                msg = f"Manifest points to missing trace sample: {path}"
                raise FileNotFoundError(msg)
            return path.resolve()

    msg = f"Trace manifest has no sample records: {manifest_path}"
    raise RuntimeError(msg)


def select_router_topk(
    payload: dict[str, Any],
    *,
    layer: int | None = None,
    module_name: str | None = None,
    call_index: int = 0,
    batch_index: int = 0,
    token_index: int = 0,
    top_k: int | None = None,
    scores_to_weights: str = "softmax",
) -> RouterTopKSelection:
    router_topk = payload.get("router_topk")
    if not isinstance(router_topk, dict) or not router_topk:
        msg = "Trace payload has no non-empty `router_topk` dict."
        raise KeyError(msg)

    resolved_module = resolve_router_module_name(router_topk, layer=layer, module_name=module_name)
    topk_call = _select_call(router_topk[resolved_module], call_index, name="router_topk")
    expert_ids = _select_token_vector(
        torch.as_tensor(topk_call, dtype=torch.long),
        batch_index=batch_index,
        token_index=token_index,
    )
    if top_k is not None:
        expert_ids = expert_ids[:top_k]

    raw_scores = None
    router_scores = payload.get("router_scores")
    if isinstance(router_scores, dict) and resolved_module in router_scores:
        score_call = _select_call(router_scores[resolved_module], call_index, name="router_scores")
        raw_scores = _select_token_vector(
            torch.as_tensor(score_call, dtype=torch.float32),
            batch_index=batch_index,
            token_index=token_index,
        )
        if top_k is not None:
            raw_scores = raw_scores[:top_k]
        expert_weights = scores_to_router_weights(raw_scores, mode=scores_to_weights)
    else:
        expert_weights = torch.full(
            expert_ids.shape,
            1.0 / max(1, expert_ids.numel()),
            dtype=torch.float32,
        )

    return RouterTopKSelection(
        module_name=resolved_module,
        expert_ids=expert_ids.to(torch.long),
        expert_weights=expert_weights.to(torch.float32),
        raw_scores=raw_scores,
        call_index=call_index,
        batch_index=batch_index,
        token_index=token_index,
    )


def select_trace_hidden_token(
    payload: dict[str, Any],
    *,
    batch_index: int = 0,
    token_index: int = 0,
) -> torch.Tensor:
    hidden = payload.get("last_hidden_state")
    if not isinstance(hidden, torch.Tensor):
        msg = "Trace payload has no `last_hidden_state` tensor."
        raise KeyError(msg)

    if hidden.ndim == 3:
        batch = _normalize_index(batch_index, hidden.shape[0], name="batch_index")
        token = _normalize_index(token_index, hidden.shape[1], name="token_index")
        return hidden[batch : batch + 1, token : token + 1, :].contiguous()
    if hidden.ndim == 2:
        token = _normalize_index(token_index, hidden.shape[0], name="token_index")
        return hidden[token : token + 1, :].contiguous()

    msg = f"Unsupported last_hidden_state shape: {tuple(hidden.shape)}"
    raise ValueError(msg)


def resolve_router_module_name(
    router_topk: dict[str, Any],
    *,
    layer: int | None = None,
    module_name: str | None = None,
) -> str:
    if module_name is not None:
        if module_name not in router_topk:
            msg = f"Router module {module_name!r} not found. Available: {sorted(router_topk)[:16]}"
            raise KeyError(msg)
        return module_name

    names = sorted(router_topk)
    if layer is None:
        return names[0]

    pattern = re.compile(LAYER_RE_TEMPLATE.format(layer=layer))
    matches = [name for name in names if pattern.search(name)]
    if not matches:
        fallback = [name for name in names if f"layers.{layer}." in name and "mlp.gate" in name]
        matches = fallback
    if len(matches) != 1:
        msg = f"Expected exactly one router module for layer={layer}, found {matches}"
        raise KeyError(msg)
    return matches[0]


def scores_to_router_weights(scores: torch.Tensor, *, mode: str = "softmax") -> torch.Tensor:
    if scores.ndim != 1:
        msg = f"scores must be 1D, got {tuple(scores.shape)}"
        raise ValueError(msg)
    normalized = mode.lower()
    if normalized == "softmax":
        return torch.softmax(scores.float(), dim=-1)
    if normalized in {"raw", "identity"}:
        return scores.float()
    if normalized in {"uniform", "equal"}:
        return torch.full(scores.shape, 1.0 / max(1, scores.numel()), dtype=torch.float32)
    msg = f"Unsupported scores_to_weights mode {mode!r}"
    raise ValueError(msg)


def _select_call(calls: Any, call_index: int, *, name: str) -> Any:
    if not isinstance(calls, list) or not calls:
        msg = f"{name} entry is empty or not a list."
        raise ValueError(msg)
    index = _normalize_index(call_index, len(calls), name="call_index")
    return calls[index]


def _select_token_vector(
    tensor: torch.Tensor,
    *,
    batch_index: int,
    token_index: int,
) -> torch.Tensor:
    if tensor.ndim == 3:
        batch = _normalize_index(batch_index, tensor.shape[0], name="batch_index")
        token = _normalize_index(token_index, tensor.shape[1], name="token_index")
        return tensor[batch, token].contiguous()
    if tensor.ndim == 2:
        token = _normalize_index(token_index, tensor.shape[0], name="token_index")
        return tensor[token].contiguous()
    if tensor.ndim == 1:
        return tensor.contiguous()
    msg = f"Expected router top-k tensor with 1-3 dims, got {tuple(tensor.shape)}"
    raise ValueError(msg)


def _normalize_index(index: int, size: int, *, name: str) -> int:
    if size <= 0:
        msg = f"Cannot index empty dimension for {name}."
        raise IndexError(msg)
    normalized = index + size if index < 0 else index
    if normalized < 0 or normalized >= size:
        msg = f"{name}={index} out of range for size {size}"
        raise IndexError(msg)
    return normalized
