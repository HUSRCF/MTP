from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch


@dataclass(frozen=True)
class TransitionMatrixMetadata:
    source_manifest: str
    train_sample_positions: list[int]
    heldout_sample_positions: list[int]
    train_sample_ids: list[int]
    heldout_sample_ids: list[int]
    num_layers: int
    num_experts: int
    delta_values: list[int] = field(default_factory=lambda: [1])
    smoothing: str = "none"
    freq_prior_blend: float = 0.0
    weight_semantics: str = "recorder_topk_weights_renormalized"
    transition_target: str = "recorder_target_topk_weights"
    model_id: str | None = None
    router_trace_model_id: str | None = None
    prefc_fixed: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    schema_version: int = 1
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_transition_matrix_artifact(
    *,
    transition_matrix: torch.Tensor,
    frequency_scores: torch.Tensor | None,
    metadata: TransitionMatrixMetadata,
) -> dict[str, Any]:
    if transition_matrix.ndim != 4:
        msg = (
            "transition_matrix must have shape [delta, layers, in_experts, out_experts], "
            f"got {tuple(transition_matrix.shape)}"
        )
        raise ValueError(msg)
    if int(transition_matrix.shape[1]) != int(metadata.num_layers):
        msg = "transition_matrix layer dimension does not match metadata.num_layers."
        raise ValueError(msg)
    if (
        int(transition_matrix.shape[2]) != int(metadata.num_experts)
        or int(transition_matrix.shape[3]) != int(metadata.num_experts)
    ):
        msg = "transition_matrix expert dimensions do not match metadata.num_experts."
        raise ValueError(msg)
    artifact: dict[str, Any] = {
        "transition_matrix": transition_matrix.detach().cpu().to(torch.float32),
        "metadata": metadata.as_dict(),
    }
    if frequency_scores is not None:
        artifact["frequency_scores"] = frequency_scores.detach().cpu().to(torch.float32)
    return artifact


def save_transition_matrix_artifact(
    artifact: dict[str, Any],
    path: str | Path,
) -> Path:
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(artifact, output)
    return output


def load_transition_matrix_artifact(path: str | Path) -> dict[str, Any]:
    payload = torch.load(Path(path).expanduser().resolve(), map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or "transition_matrix" not in payload:
        msg = f"Expected transition matrix artifact dict at {path}"
        raise ValueError(msg)
    return payload
