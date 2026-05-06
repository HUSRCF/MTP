from __future__ import annotations

from typing import Any

import torch

from mtp_expert_prefetch.runtime.tile_order import TileRequest


def tile_requests_from_tensor_cache(
    cache: dict[str, Any],
    *,
    window_size: int,
    topk: int,
    tiles_per_expert: int,
    max_examples: int | None = None,
    start_example: int = 0,
    split_name: str | None = None,
) -> tuple[list[TileRequest], dict[str, Any]]:
    target_mass = cache["target_mass"].float()
    transition_scores = cache["transition_scores"].float()
    mtp_scores = cache["mtp_scores"].float()
    token_sample_indices = cache.get("token_sample_indices")
    if target_mass.ndim != 4:
        raise ValueError(f"expected target_mass [N,D,L,E], got {tuple(target_mass.shape)}")
    num_examples, depth, num_layers, num_experts = target_mass.shape
    if depth != 1:
        target_mass = target_mass[:, :1]
        transition_scores = transition_scores[:, :1]
        mtp_scores = mtp_scores[:, :1]
    start_example = max(0, int(start_example))
    if start_example:
        num_examples = max(0, num_examples - start_example)
        target_mass = target_mass[start_example:]
        transition_scores = transition_scores[start_example:]
        mtp_scores = mtp_scores[start_example:]
        if token_sample_indices is not None:
            token_sample_indices = token_sample_indices[start_example:]
    if max_examples is not None:
        num_examples = min(num_examples, int(max_examples))
        target_mass = target_mass[:num_examples]
        transition_scores = transition_scores[:num_examples]
        mtp_scores = mtp_scores[:num_examples]
        if token_sample_indices is not None:
            token_sample_indices = token_sample_indices[:num_examples]

    requests: list[TileRequest] = []
    request_id = 0
    windows_per_layer = (num_examples + int(window_size) - 1) // int(window_size)
    for layer in range(num_layers):
        for example_idx in range(num_examples):
            absolute_example_idx = start_example + int(example_idx)
            sample_idx = (
                int(token_sample_indices[example_idx].item())
                if token_sample_indices is not None
                else int(absolute_example_idx)
            )
            window_id = int(layer) * windows_per_layer + int(example_idx) // int(window_size)
            mass = target_mass[example_idx, 0, layer]
            values, experts = torch.topk(mass, k=min(int(topk), int(num_experts)))
            for row_offset, (value, expert_tensor) in enumerate(
                zip(values.tolist(), experts.tolist(), strict=True)
            ):
                if value <= 0:
                    continue
                expert = int(expert_tensor)
                transition_score = float(transition_scores[example_idx, 0, layer, expert])
                mtp_score = float(mtp_scores[example_idx, 0, layer, expert])
                utility_score = 0.75 * transition_score + 0.55 * mtp_score
                for tile_local in range(int(tiles_per_expert)):
                    tile_id = expert * int(tiles_per_expert) + tile_local
                    requests.append(
                        TileRequest(
                            window_id=window_id,
                            request_id=request_id,
                            tile_id=tile_id,
                            expert_id=expert,
                            transition_score=transition_score,
                            mtp_score=mtp_score,
                            utility_score=utility_score,
                            sample_idx=sample_idx,
                            token_index=int(absolute_example_idx),
                            layer_idx=int(layer),
                            row_id=row_offset,
                            weight=float(value),
                            source_policy="target_topk",
                            split=split_name,
                        )
                    )
                    request_id += 1
    metadata = {
        "num_examples": int(num_examples),
        "num_layers": int(num_layers),
        "num_experts": int(num_experts),
        "window_size": int(window_size),
        "topk": int(topk),
        "tiles_per_expert": int(tiles_per_expert),
        "start_example": int(start_example),
        "max_examples": None if max_examples is None else int(max_examples),
        "split_name": split_name,
        "schema_version": cache.get("schema_version"),
        "eval_split": cache.get("eval_split"),
    }
    return requests, metadata
