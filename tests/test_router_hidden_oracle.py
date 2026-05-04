from __future__ import annotations

import json

import torch

from mtp_expert_prefetch.evaluation import analyze_router_hidden_oracle


def test_analyze_router_hidden_oracle_reports_exact_match(tmp_path):
    module_name = "model.language_model.layers.0.mlp.gate"
    payload = {
        "router_topk": {
            module_name: [torch.tensor([[1, 2], [3, 4]], dtype=torch.int16)]
        },
        "router_oracle_topk": {
            module_name: [torch.tensor([[1, 2], [3, 4]], dtype=torch.int16)]
        },
        "router_input_hidden": {
            module_name: [torch.randn(2, 8, dtype=torch.bfloat16)]
        },
    }
    sample_path = tmp_path / "sample_000000.pt"
    torch.save(payload, sample_path)
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text(
        json.dumps({"sample_idx": 0, "path": sample_path.name}) + "\n",
        encoding="utf-8",
    )

    report = analyze_router_hidden_oracle(manifest_path)

    assert report.ok
    assert report.num_calls == 1
    assert report.ordered_element_match_rate == 1.0
    assert report.set_recall == 1.0
    assert report.exact_set_match_rate == 1.0
    assert report.top1_match_rate == 1.0
    assert report.hidden_tensor_count == 1
    assert report.hidden_shapes[module_name] == [2, 8]
