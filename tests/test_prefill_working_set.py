from __future__ import annotations

import json

import pytest
import torch

from mtp_expert_prefetch.evaluation import (
    analyze_prefill_working_set,
    write_prefill_working_set_report,
)


def test_analyze_prefill_working_set_reports_hot_cache(tmp_path):
    manifest_path = tmp_path / "manifest.jsonl"
    samples = [
        {
            "router_topk": {
                "model.language_model.layers.0.mlp.gate": [
                    torch.tensor([[0, 1], [0, 2], [0, 3]], dtype=torch.int16)
                ],
                "model.language_model.layers.1.mlp.gate": [
                    torch.tensor([[4, 5], [4, 5], [6, 7]], dtype=torch.int16)
                ],
            }
        },
        {
            "router_topk": {
                "model.language_model.layers.0.mlp.gate": [
                    torch.tensor([[0, 1], [0, 1]], dtype=torch.int16)
                ],
                "model.language_model.layers.1.mlp.gate": [
                    torch.tensor([[4, 8], [4, 9]], dtype=torch.int16)
                ],
            }
        },
    ]

    with manifest_path.open("w", encoding="utf-8") as manifest:
        for sample_idx, payload in enumerate(samples):
            sample_path = tmp_path / f"sample_{sample_idx:06d}.pt"
            torch.save(payload, sample_path)
            manifest.write(
                json.dumps(
                    {
                        "sample_idx": sample_idx,
                        "path": sample_path.name,
                    }
                )
                + "\n"
            )

    report = analyze_prefill_working_set(manifest_path, budgets=[2, 4])

    assert report.num_samples == 2
    assert report.num_layers == 2
    assert report.top_k == 2
    assert report.total_tokens == 5
    assert report.layer_unique_summary["max"] == 4
    assert report.sample_unique_summary["max"] == 8
    assert report.hot_cache["2"]["selection_hit_rate"] == pytest.approx(0.7)
    assert report.hot_cache["2"]["sample_layer_fully_resident_fraction"] == pytest.approx(0.25)
    assert report.hot_cache["2"]["sample_layer_budget_can_fit_fraction"] == pytest.approx(0.25)

    output_path = write_prefill_working_set_report(report, tmp_path / "report.json")
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["num_samples"] == 2
    assert written["hot_cache"]["4"]["selection_hit_rate"] >= 0.8
