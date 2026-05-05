from __future__ import annotations

import torch

from mtp_expert_prefetch.runtime.transition_matrix import (
    TransitionMatrixMetadata,
    build_transition_matrix_artifact,
    load_transition_matrix_artifact,
    save_transition_matrix_artifact,
)


def test_transition_matrix_artifact_round_trip(tmp_path):
    transition = torch.zeros(1, 2, 3, 3)
    transition[0, 1, 2, 0] = 1.0
    frequency = torch.ones(1, 1, 2, 3) / 3.0
    metadata = TransitionMatrixMetadata(
        source_manifest="manifest.jsonl",
        train_sample_positions=[0, 1],
        heldout_sample_positions=[2],
        train_sample_ids=[10, 11],
        heldout_sample_ids=[12],
        num_layers=2,
        num_experts=3,
        model_id="model",
        router_trace_model_id="router",
        extra={"config_path": "config.yaml"},
    )

    artifact = build_transition_matrix_artifact(
        transition_matrix=transition,
        frequency_scores=frequency,
        metadata=metadata,
    )
    output = save_transition_matrix_artifact(artifact, tmp_path / "transition.pt")
    loaded = load_transition_matrix_artifact(output)

    assert torch.equal(loaded["transition_matrix"], transition.float())
    assert torch.equal(loaded["frequency_scores"], frequency.float())
    assert loaded["metadata"]["num_layers"] == 2
    assert loaded["metadata"]["num_experts"] == 3
    assert loaded["metadata"]["delta_values"] == [1]
    assert loaded["metadata"]["weight_semantics"] == "recorder_topk_weights_renormalized"
