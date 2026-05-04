from __future__ import annotations

import json

import torch
from safetensors.torch import load_file, save_file

from mtp_expert_prefetch.repack.qwen3_moe_gptq import (
    repack_qwen3_moe_gptq,
    verify_random_repacked_slices,
)
from mtp_expert_prefetch.repack.store import RepackedMoeExpertStore


def test_repack_qwen3_moe_gptq_stacks_experts(tmp_path):
    snapshot = tmp_path / "snapshot"
    output = tmp_path / "out"
    snapshot.mkdir()

    tensors = {}
    weight_map = {}
    shard_name = "model-00001-of-00001.safetensors"
    for expert in range(2):
        for projection in ("down_proj", "gate_proj", "up_proj"):
            for kind in ("g_idx", "qweight", "qzeros", "scales"):
                key = f"model.language_model.layers.0.mlp.experts.{expert}.{projection}.{kind}"
                tensors[key] = torch.full((2, 3), expert + len(kind), dtype=torch.float32)
                weight_map[key] = shard_name

    save_file(tensors, snapshot / shard_name)
    (snapshot / "model.safetensors.index.json").write_text(
        json.dumps({"metadata": {"total_size": 1}, "weight_map": weight_map}),
        encoding="utf-8",
    )

    manifest_path = repack_qwen3_moe_gptq(
        snapshot,
        output,
        layers="0",
        num_experts=2,
        verify=True,
    )

    records = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["num_source_tensors"] == 24
    assert records[0]["num_output_tensors"] == 12

    repacked = load_file(output / "layer_00.safetensors")
    assert repacked["experts.gate_proj.qweight"].shape == (2, 2, 3)
    assert torch.equal(
        repacked["experts.gate_proj.qweight"][1],
        tensors["model.language_model.layers.0.mlp.experts.1.gate_proj.qweight"],
    )


def test_verify_random_repacked_slices(tmp_path):
    snapshot = tmp_path / "snapshot"
    output = tmp_path / "out"
    snapshot.mkdir()

    tensors = {}
    weight_map = {}
    shard_name = "model-00001-of-00001.safetensors"
    for expert in range(2):
        for projection in ("down_proj", "gate_proj", "up_proj"):
            for kind in ("g_idx", "qweight", "qzeros", "scales"):
                key = f"model.language_model.layers.0.mlp.experts.{expert}.{projection}.{kind}"
                tensors[key] = torch.arange(6, dtype=torch.float32).reshape(2, 3) + expert
                weight_map[key] = shard_name

    save_file(tensors, snapshot / shard_name)
    (snapshot / "model.safetensors.index.json").write_text(
        json.dumps({"metadata": {"total_size": 1}, "weight_map": weight_map}),
        encoding="utf-8",
    )
    repack_qwen3_moe_gptq(snapshot, output, layers="0", num_experts=2)

    result = verify_random_repacked_slices(
        snapshot,
        output,
        samples=16,
        seed=7,
        num_experts=2,
    )
    assert result["ok"] is True
    assert result["samples_checked"] == 16


def test_repacked_moe_expert_store_inspects_and_slices(tmp_path):
    snapshot = tmp_path / "snapshot"
    output = tmp_path / "out"
    snapshot.mkdir()

    tensors = {}
    weight_map = {}
    shard_name = "model-00001-of-00001.safetensors"
    for expert in range(2):
        for projection in ("down_proj", "gate_proj", "up_proj"):
            for kind in ("g_idx", "qweight", "qzeros", "scales"):
                key = f"model.language_model.layers.0.mlp.experts.{expert}.{projection}.{kind}"
                tensors[key] = torch.arange(6, dtype=torch.int32).reshape(2, 3) + expert
                weight_map[key] = shard_name

    save_file(tensors, snapshot / shard_name)
    (snapshot / "model.safetensors.index.json").write_text(
        json.dumps({"metadata": {"total_size": 1}, "weight_map": weight_map}),
        encoding="utf-8",
    )
    repack_qwen3_moe_gptq(snapshot, output, layers="0", num_experts=2)

    with RepackedMoeExpertStore(output) as store:
        result = store.inspect()
        assert result["ok"] is True
        assert result["num_layers"] == 1
        assert result["total_output_tensors"] == 12

        info = store.tensor_info(0, "gate_proj", "qweight")
        assert info.shape == (2, 2, 3)
        assert info.dtype == "int32"

        expert = store.get_expert_tensor(0, 1, "gate_proj", "qweight")
        assert torch.equal(
            expert,
            tensors["model.language_model.layers.0.mlp.experts.1.gate_proj.qweight"],
        )
