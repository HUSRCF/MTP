from __future__ import annotations

import torch

from mtp_expert_prefetch.repack import (
    GptqProjectionTensors,
    SingleExpertMlp,
    SingleExpertWeights,
    TopKExpertMlp,
    apply_dequantized_projection,
    dequantize_gptq_projection,
    unpack_cols,
    unpack_rows,
)


def _pack_rows(values: torch.Tensor, *, bits: int = 4) -> torch.Tensor:
    pack_factor = 32 // bits
    mask = (1 << bits) - 1
    rows, cols = values.shape
    assert rows % pack_factor == 0
    packed = torch.zeros(rows // pack_factor, cols, dtype=torch.int64)
    values64 = values.to(torch.int64) & mask
    for offset in range(pack_factor):
        packed |= values64[offset::pack_factor] << (offset * bits)
    return packed.to(torch.int32)


def _pack_cols(values: torch.Tensor, *, bits: int = 4) -> torch.Tensor:
    pack_factor = 32 // bits
    mask = (1 << bits) - 1
    rows, cols = values.shape
    assert cols % pack_factor == 0
    packed = torch.zeros(rows, cols // pack_factor, dtype=torch.int64)
    values64 = values.to(torch.int64) & mask
    for offset in range(pack_factor):
        packed |= values64[:, offset::pack_factor] << (offset * bits)
    return packed.to(torch.int32)


def test_unpack_rows_and_cols_round_trip_4bit():
    row_values = torch.arange(16 * 8, dtype=torch.int32).reshape(16, 8) % 16
    col_values = torch.arange(2 * 16, dtype=torch.int32).reshape(2, 16) % 16

    assert torch.equal(unpack_rows(_pack_rows(row_values), bits=4), row_values)
    assert torch.equal(unpack_cols(_pack_cols(col_values), bits=4), col_values)


def test_dequantize_gptq_projection_returns_linear_weight():
    int_weight = torch.arange(16 * 8, dtype=torch.int32).reshape(16, 8) % 16
    zeros = torch.stack(
        [
            torch.full((8,), 2, dtype=torch.int32),
            torch.full((8,), 5, dtype=torch.int32),
        ]
    )
    scales = torch.stack(
        [
            torch.linspace(0.25, 1.0, 8, dtype=torch.float32),
            torch.linspace(1.0, 1.75, 8, dtype=torch.float32),
        ]
    ).to(torch.float16)
    g_idx = torch.tensor([0] * 8 + [1] * 8, dtype=torch.int32)

    tensors = GptqProjectionTensors(
        qweight=_pack_rows(int_weight),
        qzeros=_pack_cols(zeros),
        scales=scales,
        g_idx=g_idx,
    )
    weight = dequantize_gptq_projection(tensors, dtype=torch.float32)

    expected_internal = (int_weight.float() - zeros.float()[g_idx.long()]) * scales.float()[
        g_idx.long()
    ]
    assert weight.shape == (8, 16)
    assert torch.allclose(weight, expected_internal.t().contiguous())

    input_tensor = torch.randn(3, 16)
    output = apply_dequantized_projection(input_tensor, weight)
    assert output.shape == (3, 8)
    assert torch.isfinite(output).all()


def test_single_expert_mlp_matches_manual_formula():
    weights = SingleExpertWeights(
        gate_proj=torch.tensor(
            [
                [0.5, -0.25, 0.75, 0.0],
                [0.0, 0.5, -0.5, 1.0],
                [1.0, 0.0, 0.25, -0.75],
            ],
            dtype=torch.float32,
        ),
        up_proj=torch.tensor(
            [
                [0.25, 0.5, 0.0, -0.25],
                [0.75, -0.5, 0.5, 0.0],
                [-0.25, 0.25, 1.0, 0.5],
            ],
            dtype=torch.float32,
        ),
        down_proj=torch.tensor(
            [
                [0.5, 0.25, -0.5],
                [0.0, 0.75, 0.25],
                [-0.25, 0.5, 0.5],
                [1.0, -0.5, 0.0],
            ],
            dtype=torch.float32,
        ),
    )
    mlp = SingleExpertMlp(weights)
    input_tensor = torch.randn(2, 5, 4)

    expected = torch.nn.functional.linear(
        torch.nn.functional.silu(torch.nn.functional.linear(input_tensor, weights.gate_proj))
        * torch.nn.functional.linear(input_tensor, weights.up_proj),
        weights.down_proj,
    )
    output = mlp(input_tensor)

    assert output.shape == (2, 5, 4)
    assert torch.allclose(output, expected)


def test_topk_expert_mlp_matches_weighted_sum():
    weights_a = SingleExpertWeights(
        gate_proj=torch.eye(3, 4),
        up_proj=torch.full((3, 4), 0.25),
        down_proj=torch.eye(4, 3),
    )
    weights_b = SingleExpertWeights(
        gate_proj=torch.full((3, 4), -0.2),
        up_proj=torch.eye(3, 4),
        down_proj=torch.full((4, 3), 0.5),
    )
    expert_a = SingleExpertMlp(weights_a)
    expert_b = SingleExpertMlp(weights_b)
    topk = TopKExpertMlp({3: expert_a, 7: expert_b})

    input_tensor = torch.randn(2, 4)
    expert_ids = torch.tensor([7, 3], dtype=torch.long)
    expert_weights = torch.tensor([0.25, 0.75], dtype=torch.float32)

    expected = expert_weights[0] * expert_b(input_tensor) + expert_weights[1] * expert_a(
        input_tensor
    )
    output = topk(input_tensor, expert_ids, expert_weights)

    assert output.shape == input_tensor.shape
    assert topk.loaded_expert_ids == (3, 7)
    assert torch.allclose(output, expected)
