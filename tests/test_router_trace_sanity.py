from __future__ import annotations

import json

import pytest
import torch

from mtp_expert_prefetch.evaluation import analyze_router_trace_sanity


def test_analyze_router_trace_sanity_checks_weight_semantics(tmp_path):
    payload = {
        "trace_source": "vllm_router_logits_recorder",
        "router_topk": {
            "model.language_model.layers.0.mlp.gate": [
                torch.tensor([[1, 2], [3, 4]], dtype=torch.int16)
            ],
            "model.language_model.layers.1.mlp.gate": [
                torch.tensor([[5, 6], [7, 8]], dtype=torch.int16)
            ],
        },
        "router_weights": {
            "model.language_model.layers.0.mlp.gate": [
                torch.tensor([[0.8, 0.2], [0.6, 0.4]], dtype=torch.float32)
            ],
            "model.language_model.layers.1.mlp.gate": [
                torch.tensor([[0.7, 0.3], [0.55, 0.45]], dtype=torch.float32)
            ],
        },
    }
    sample_path = tmp_path / "sample_000000.pt"
    torch.save(payload, sample_path)
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text(
        json.dumps(
            {
                "sample_idx": 0,
                "path": sample_path.name,
                "trace_source": "vllm_router_logits_recorder",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = analyze_router_trace_sanity(
        manifest_path,
        expected_trace_source="vllm_router_logits_recorder",
        expected_layers=2,
        num_experts=16,
    )

    assert report.ok
    assert report.trace_sources == {"vllm_router_logits_recorder": 1}
    assert report.weight_sum_summary["mean"] == 1.0
    assert report.weight_value_summary["max"] == pytest.approx(0.8)
    assert report.sorted_weight_fraction == 1.0
    assert report.first_is_argmax_fraction == 1.0
    assert report.nonuniform_sample_fraction == 1.0
