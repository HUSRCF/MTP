from __future__ import annotations

import torch

from mtp_expert_prefetch.mtp import MtpExtraRunner, mtp_rms_norm


def test_mtp_rms_norm_uses_qwen_offset_weight():
    x = torch.tensor([[1.0, 2.0, 3.0, 4.0]], dtype=torch.float32)
    weight = torch.tensor([0.0, 0.5, -0.25, 1.0], dtype=torch.float32)

    out = mtp_rms_norm(x, weight, eps=0.0)
    expected = x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True)) * (1.0 + weight)

    assert torch.allclose(out, expected)


def test_mtp_prefc_and_router_topk_with_dense_test_tensors():
    tensors = {
        "mtp.pre_fc_norm_embedding.weight": torch.zeros(4),
        "mtp.pre_fc_norm_hidden.weight": torch.zeros(4),
        "mtp.fc.weight": torch.eye(4, 8),
        "mtp.layers.0.mlp.gate.weight": torch.tensor(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
            ]
        ),
        "mtp.layers.0.mlp.shared_expert_gate.weight": torch.ones(1, 4),
    }
    runner = MtpExtraRunner.__new__(MtpExtraRunner)
    torch.nn.Module.__init__(runner)
    runner.bits = 4
    runner.group_size = 128
    runner.target_dtype = torch.float32
    runner.target_device = torch.device("cpu")
    runner.register_buffer(
        "pre_fc_norm_embedding",
        tensors["mtp.pre_fc_norm_embedding.weight"],
        persistent=False,
    )
    runner.register_buffer(
        "pre_fc_norm_hidden",
        tensors["mtp.pre_fc_norm_hidden.weight"],
        persistent=False,
    )
    runner.register_buffer("fc_weight", tensors["mtp.fc.weight"], persistent=False)
    runner.register_buffer(
        "router_weight",
        tensors["mtp.layers.0.mlp.gate.weight"],
        persistent=False,
    )
    runner.register_buffer(
        "shared_expert_gate_weight",
        tensors["mtp.layers.0.mlp.shared_expert_gate.weight"],
        persistent=False,
    )

    hidden = torch.randn(1, 2, 4)
    embeddings = torch.randn(1, 2, 4)
    mtp_hidden = runner.prefc(hidden, embeddings)
    router = runner.router_topk(mtp_hidden, top_k=2)

    assert mtp_hidden.shape == (1, 2, 4)
    assert router.logits.shape == (1, 2, 3)
    assert router.topk_ids.shape == (1, 2, 2)
    assert router.topk_weights.shape == (1, 2, 2)
    assert torch.allclose(router.topk_weights.sum(dim=-1), torch.ones(1, 2))


def test_mtp_prefc_concatenates_embedding_before_hidden():
    runner = MtpExtraRunner.__new__(MtpExtraRunner)
    torch.nn.Module.__init__(runner)
    runner.target_dtype = torch.float32
    runner.target_device = torch.device("cpu")
    runner.register_buffer("pre_fc_norm_embedding", torch.zeros(4), persistent=False)
    runner.register_buffer("pre_fc_norm_hidden", torch.zeros(4), persistent=False)
    runner.register_buffer("fc_weight", torch.eye(4, 8), persistent=False)

    hidden = torch.tensor([[[8.0, 7.0, 6.0, 5.0]]])
    embeddings = torch.tensor([[[1.0, 2.0, 3.0, 4.0]]])

    mtp_hidden = runner.prefc(hidden, embeddings)
    expected_embedding_prefix = mtp_rms_norm(embeddings, torch.zeros(4))

    assert torch.allclose(mtp_hidden, expected_embedding_prefix)
