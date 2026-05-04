from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class TokenFrequencyTable:
    values: dict[tuple[int, int], torch.Tensor]
    fallback: torch.Tensor
    uses_delta_axis: bool


def train_frequency_scores(target: torch.Tensor) -> torch.Tensor:
    if target.ndim != 4:
        msg = f"target must have shape [tokens, delta, layers, experts], got {tuple(target.shape)}"
        raise ValueError(msg)
    return target.float().mean(dim=0, keepdim=True)


def train_transition_matrix(
    current_expert_scores: torch.Tensor,
    target: torch.Tensor,
    *,
    eps: float = 1e-12,
) -> torch.Tensor:
    if current_expert_scores.ndim != 3:
        msg = (
            "current_expert_scores must have shape [tokens, layers, experts], "
            f"got {tuple(current_expert_scores.shape)}"
        )
        raise ValueError(msg)
    if target.ndim != 4:
        msg = f"target must have shape [tokens, delta, layers, experts], got {tuple(target.shape)}"
        raise ValueError(msg)
    if current_expert_scores.shape[0] != target.shape[0]:
        msg = "current_expert_scores and target must share token count."
        raise ValueError(msg)
    if current_expert_scores.shape[1] != target.shape[2]:
        msg = "current_expert_scores layer count must match target layer count."
        raise ValueError(msg)
    if current_expert_scores.shape[2] != target.shape[3]:
        msg = "current_expert_scores expert count must match target expert count."
        raise ValueError(msg)

    current = current_expert_scores.float().clamp_min(0.0)
    future = target.float().clamp_min(0.0)
    numerator = torch.einsum("nli,ndlo->dlio", current, future)
    denominator = current.sum(dim=0)[None, :, :, None].clamp_min(eps)
    return numerator / denominator


def apply_transition_matrix(
    current_expert_scores: torch.Tensor,
    transition: torch.Tensor,
) -> torch.Tensor:
    if current_expert_scores.ndim != 3:
        msg = (
            "current_expert_scores must have shape [tokens, layers, experts], "
            f"got {tuple(current_expert_scores.shape)}"
        )
        raise ValueError(msg)
    if transition.ndim != 4:
        msg = (
            "transition must have shape [delta, layers, in_experts, out_experts], "
            f"got {tuple(transition.shape)}"
        )
        raise ValueError(msg)
    if current_expert_scores.shape[1:] != transition.shape[1:3]:
        msg = (
            "current_expert_scores [layers, experts] must match transition "
            f"[layers, in_experts], got {tuple(current_expert_scores.shape[1:])} "
            f"and {tuple(transition.shape[1:3])}"
        )
        raise ValueError(msg)
    return torch.einsum("nli,dlio->ndlo", current_expert_scores.float(), transition.float())


def build_token_frequency_table(
    token_ids: torch.Tensor,
    target: torch.Tensor,
    *,
    fallback: torch.Tensor | None = None,
) -> TokenFrequencyTable:
    if target.ndim != 4:
        msg = f"target must have shape [tokens, delta, layers, experts], got {tuple(target.shape)}"
        raise ValueError(msg)
    if token_ids.ndim not in {1, 2}:
        msg = f"token_ids must have shape [tokens] or [tokens, delta], got {tuple(token_ids.shape)}"
        raise ValueError(msg)
    if token_ids.shape[0] != target.shape[0]:
        msg = "token_ids and target must share token count."
        raise ValueError(msg)
    uses_delta_axis = token_ids.ndim == 2
    if uses_delta_axis and token_ids.shape[1] != target.shape[1]:
        msg = "2D token_ids must share the target delta dimension."
        raise ValueError(msg)

    fallback_scores = train_frequency_scores(target) if fallback is None else fallback.float()
    if fallback_scores.shape != (1, target.shape[1], target.shape[2], target.shape[3]):
        msg = (
            "fallback must have shape [1, delta, layers, experts], "
            f"got {tuple(fallback_scores.shape)}"
        )
        raise ValueError(msg)

    sums: dict[tuple[int, int], torch.Tensor] = {}
    counts: dict[tuple[int, int], int] = {}
    ids = token_ids.to(torch.long).cpu()
    future = target.detach().float().cpu()
    for token_index in range(int(target.shape[0])):
        for delta_index in range(int(target.shape[1])):
            token_id = int(ids[token_index, delta_index] if uses_delta_axis else ids[token_index])
            key = (delta_index, token_id)
            value = future[token_index, delta_index]
            if key in sums:
                sums[key] = sums[key] + value
                counts[key] += 1
            else:
                sums[key] = value.clone()
                counts[key] = 1

    values = {key: sums[key] / float(counts[key]) for key in sums}
    return TokenFrequencyTable(
        values=values,
        fallback=fallback_scores.detach().cpu(),
        uses_delta_axis=uses_delta_axis,
    )


def apply_token_frequency_table(
    table: TokenFrequencyTable,
    token_ids: torch.Tensor,
    *,
    device: torch.device | None = None,
) -> torch.Tensor:
    if token_ids.ndim not in {1, 2}:
        msg = f"token_ids must have shape [tokens] or [tokens, delta], got {tuple(token_ids.shape)}"
        raise ValueError(msg)
    num_tokens = int(token_ids.shape[0])
    fallback = table.fallback
    _, num_deltas, num_layers, num_experts = fallback.shape
    if token_ids.ndim == 2 and int(token_ids.shape[1]) != num_deltas:
        msg = "2D token_ids must share the fallback delta dimension."
        raise ValueError(msg)

    output = fallback.expand(num_tokens, -1, -1, -1).clone()
    ids = token_ids.to(torch.long).cpu()
    for token_index in range(num_tokens):
        for delta_index in range(num_deltas):
            token_id = int(
                ids[token_index, delta_index] if token_ids.ndim == 2 else ids[token_index]
            )
            value = table.values.get((delta_index, token_id))
            if value is not None:
                output[token_index, delta_index] = value
    target_device = device if device is not None else token_ids.device
    return output.to(device=target_device, dtype=torch.float32).reshape(
        num_tokens,
        num_deltas,
        num_layers,
        num_experts,
    )
