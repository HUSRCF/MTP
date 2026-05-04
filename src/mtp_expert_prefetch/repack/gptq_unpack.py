from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F

from mtp_expert_prefetch.repack.store import RepackedMoeExpertStore


@dataclass(frozen=True)
class GptqProjectionTensors:
    qweight: torch.Tensor
    qzeros: torch.Tensor
    scales: torch.Tensor
    g_idx: torch.Tensor


@dataclass(frozen=True)
class SingleExpertWeights:
    gate_proj: torch.Tensor
    up_proj: torch.Tensor
    down_proj: torch.Tensor

    @property
    def hidden_size(self) -> int:
        return int(self.gate_proj.shape[1])

    @property
    def intermediate_size(self) -> int:
        return int(self.gate_proj.shape[0])


DTYPE_NAMES = {
    "float16": torch.float16,
    "fp16": torch.float16,
    "bfloat16": torch.bfloat16,
    "bf16": torch.bfloat16,
    "float32": torch.float32,
    "fp32": torch.float32,
}


def resolve_torch_dtype(dtype: str | torch.dtype) -> torch.dtype:
    if isinstance(dtype, torch.dtype):
        return dtype
    try:
        return DTYPE_NAMES[dtype.lower()]
    except KeyError as exc:
        msg = f"Unsupported dtype {dtype!r}; expected one of {sorted(DTYPE_NAMES)}"
        raise ValueError(msg) from exc


def unpack_cols(packed: torch.Tensor, *, bits: int = 4) -> torch.Tensor:
    """Unpack GPTQ int32 values packed along the column dimension."""
    _validate_bits(bits)
    pack_bits = packed.element_size() * 8
    pack_factor = pack_bits // bits
    mask = (1 << bits) - 1
    packed_uint = packed.to(torch.int64) & ((1 << pack_bits) - 1)

    rows, cols = packed.shape
    result = torch.empty(rows, cols * pack_factor, dtype=torch.int32, device=packed.device)
    for offset in range(pack_factor):
        result[:, offset::pack_factor] = (
            (packed_uint >> (offset * bits)) & mask
        ).to(torch.int32)
    return result


def unpack_rows(packed: torch.Tensor, *, bits: int = 4) -> torch.Tensor:
    """Unpack GPTQ int32 values packed along the input-row dimension."""
    _validate_bits(bits)
    pack_bits = packed.element_size() * 8
    pack_factor = pack_bits // bits
    mask = (1 << bits) - 1
    packed_uint = packed.to(torch.int64) & ((1 << pack_bits) - 1)

    rows, cols = packed.shape
    result = torch.empty(rows * pack_factor, cols, dtype=torch.int32, device=packed.device)
    for offset in range(pack_factor):
        result[offset::pack_factor, :] = (
            (packed_uint >> (offset * bits)) & mask
        ).to(torch.int32)
    return result


def dequantize_gptq_projection(
    tensors: GptqProjectionTensors,
    *,
    bits: int = 4,
    dtype: str | torch.dtype = torch.bfloat16,
    linear_weight: bool = True,
) -> torch.Tensor:
    """Dequantize one GPTQ projection.

    Returns PyTorch Linear orientation `[out_features, in_features]` by default.
    Set `linear_weight=False` to get GPTQ internal orientation `[in_features, out_features]`.
    """
    _validate_projection_tensors(tensors)
    target_dtype = resolve_torch_dtype(dtype)

    weight_int = unpack_rows(tensors.qweight, bits=bits)
    zeros = unpack_cols(tensors.qzeros, bits=bits)
    g_idx = tensors.g_idx.to(torch.long)

    if weight_int.shape[0] != g_idx.numel():
        msg = f"qweight expands to {weight_int.shape[0]} input rows, but g_idx has {g_idx.numel()}"
        raise ValueError(msg)
    if weight_int.shape[1] != tensors.scales.shape[1]:
        msg = (
            f"qweight expands to {weight_int.shape[1]} output columns, "
            f"but scales has {tensors.scales.shape[1]}"
        )
        raise ValueError(msg)
    if zeros.shape != tensors.scales.shape:
        msg = f"qzeros expands to {tuple(zeros.shape)}, but scales is {tuple(tensors.scales.shape)}"
        raise ValueError(msg)
    if int(g_idx.min()) < 0 or int(g_idx.max()) >= tensors.scales.shape[0]:
        msg = (
            f"g_idx out of range: min={int(g_idx.min())}, max={int(g_idx.max())}, "
            f"num_groups={tensors.scales.shape[0]}"
        )
        raise ValueError(msg)

    scales_full = tensors.scales.to(torch.float32)[g_idx]
    zeros_full = zeros.to(torch.float32)[g_idx]
    weight = (weight_int.to(torch.float32) - zeros_full) * scales_full
    if linear_weight:
        weight = weight.t().contiguous()
    return weight.to(target_dtype)


def synthesize_g_idx(
    qweight: torch.Tensor,
    *,
    bits: int = 4,
    group_size: int = 128,
) -> torch.Tensor:
    """Create GPTQ group indices for checkpoints that omit static `g_idx`."""
    _validate_bits(bits)
    if qweight.ndim != 2:
        raise ValueError(f"qweight must be 2D, got {tuple(qweight.shape)}")
    if group_size <= 0:
        raise ValueError(f"group_size must be positive, got {group_size}")
    pack_factor = qweight.element_size() * 8 // bits
    in_features = int(qweight.shape[0]) * pack_factor
    return torch.arange(in_features, dtype=torch.int32, device=qweight.device) // int(group_size)


def load_repacked_projection_tensors(
    store: RepackedMoeExpertStore,
    *,
    layer: int,
    expert: int,
    projection: str,
    device: str | torch.device = "cpu",
) -> GptqProjectionTensors:
    return GptqProjectionTensors(
        qweight=store.get_expert_tensor(layer, expert, projection, "qweight").to(device=device),
        qzeros=store.get_expert_tensor(layer, expert, projection, "qzeros").to(device=device),
        scales=store.get_expert_tensor(layer, expert, projection, "scales").to(device=device),
        g_idx=store.get_expert_tensor(layer, expert, projection, "g_idx").to(device=device),
    )


def dequantize_repacked_projection(
    store: RepackedMoeExpertStore,
    *,
    layer: int,
    expert: int,
    projection: str,
    bits: int = 4,
    dtype: str | torch.dtype = torch.bfloat16,
    device: str | torch.device = "cpu",
) -> torch.Tensor:
    tensors = load_repacked_projection_tensors(
        store,
        layer=layer,
        expert=expert,
        projection=projection,
        device=device,
    )
    return dequantize_gptq_projection(tensors, bits=bits, dtype=dtype)


def apply_dequantized_projection(input_tensor: torch.Tensor, weight: torch.Tensor) -> torch.Tensor:
    return F.linear(input_tensor, weight)


def load_single_expert_weights(
    store: RepackedMoeExpertStore,
    *,
    layer: int,
    expert: int,
    bits: int = 4,
    dtype: str | torch.dtype = torch.bfloat16,
    device: str | torch.device = "cpu",
) -> SingleExpertWeights:
    gate_proj = dequantize_repacked_projection(
        store,
        layer=layer,
        expert=expert,
        projection="gate_proj",
        bits=bits,
        dtype=dtype,
        device=device,
    )
    up_proj = dequantize_repacked_projection(
        store,
        layer=layer,
        expert=expert,
        projection="up_proj",
        bits=bits,
        dtype=dtype,
        device=device,
    )
    down_proj = dequantize_repacked_projection(
        store,
        layer=layer,
        expert=expert,
        projection="down_proj",
        bits=bits,
        dtype=dtype,
        device=device,
    )
    _validate_single_expert_weights(SingleExpertWeights(gate_proj, up_proj, down_proj))
    return SingleExpertWeights(gate_proj=gate_proj, up_proj=up_proj, down_proj=down_proj)


class SingleExpertMlp(torch.nn.Module):
    def __init__(self, weights: SingleExpertWeights) -> None:
        super().__init__()
        _validate_single_expert_weights(weights)
        self.register_buffer("gate_proj", weights.gate_proj.contiguous(), persistent=False)
        self.register_buffer("up_proj", weights.up_proj.contiguous(), persistent=False)
        self.register_buffer("down_proj", weights.down_proj.contiguous(), persistent=False)

    @property
    def hidden_size(self) -> int:
        return int(self.gate_proj.shape[1])

    @property
    def intermediate_size(self) -> int:
        return int(self.gate_proj.shape[0])

    def forward(self, input_tensor: torch.Tensor) -> torch.Tensor:
        if input_tensor.shape[-1] != self.hidden_size:
            msg = (
                f"Expected input last dim {self.hidden_size}, "
                f"got {input_tensor.shape[-1]}"
            )
            raise ValueError(msg)
        gate = F.linear(input_tensor, self.gate_proj)
        up = F.linear(input_tensor, self.up_proj)
        return F.linear(F.silu(gate) * up, self.down_proj)


class TopKExpertMlp(torch.nn.Module):
    def __init__(self, experts: dict[int, SingleExpertMlp]) -> None:
        super().__init__()
        if not experts:
            msg = "TopKExpertMlp requires at least one expert"
            raise ValueError(msg)

        hidden_sizes = {expert.hidden_size for expert in experts.values()}
        intermediate_sizes = {expert.intermediate_size for expert in experts.values()}
        if len(hidden_sizes) != 1 or len(intermediate_sizes) != 1:
            msg = (
                f"All experts must share dimensions; got hidden={hidden_sizes}, "
                f"intermediate={intermediate_sizes}"
            )
            raise ValueError(msg)

        self.experts = torch.nn.ModuleDict(
            {str(int(expert_id)): expert for expert_id, expert in sorted(experts.items())}
        )

    @property
    def loaded_expert_ids(self) -> tuple[int, ...]:
        return tuple(int(expert_id) for expert_id in self.experts.keys())

    @property
    def hidden_size(self) -> int:
        first = next(iter(self.experts.values()))
        return first.hidden_size

    @property
    def intermediate_size(self) -> int:
        first = next(iter(self.experts.values()))
        return first.intermediate_size

    def forward(
        self,
        input_tensor: torch.Tensor,
        expert_ids: torch.Tensor,
        expert_weights: torch.Tensor,
    ) -> torch.Tensor:
        if input_tensor.shape[-1] != self.hidden_size:
            msg = (
                f"Expected input last dim {self.hidden_size}, "
                f"got {input_tensor.shape[-1]}"
            )
            raise ValueError(msg)
        if expert_ids.ndim != 1:
            msg = f"expert_ids must be 1D for this smoke path, got {tuple(expert_ids.shape)}"
            raise ValueError(msg)
        if expert_weights.ndim != 1:
            msg = f"expert_weights must be 1D for this smoke path, got {tuple(expert_weights.shape)}"
            raise ValueError(msg)
        if expert_ids.shape != expert_weights.shape:
            msg = (
                f"expert_ids and expert_weights must have same shape; "
                f"got {tuple(expert_ids.shape)} and {tuple(expert_weights.shape)}"
            )
            raise ValueError(msg)

        output = torch.zeros_like(input_tensor)
        weights = expert_weights.to(device=input_tensor.device, dtype=input_tensor.dtype)
        for offset, expert_id in enumerate(expert_ids.to(device="cpu", dtype=torch.long).tolist()):
            key = str(int(expert_id))
            if key not in self.experts:
                msg = f"Expert {expert_id} is not loaded; loaded={self.loaded_expert_ids}"
                raise KeyError(msg)
            expert_output = self.experts[key](input_tensor)
            output = output + weights[offset] * expert_output
        return output


def load_single_expert_mlp(
    store: RepackedMoeExpertStore,
    *,
    layer: int,
    expert: int,
    bits: int = 4,
    dtype: str | torch.dtype = torch.bfloat16,
    device: str | torch.device = "cpu",
) -> SingleExpertMlp:
    weights = load_single_expert_weights(
        store,
        layer=layer,
        expert=expert,
        bits=bits,
        dtype=dtype,
        device=device,
    )
    return SingleExpertMlp(weights)


def load_topk_expert_mlp(
    store: RepackedMoeExpertStore,
    *,
    layer: int,
    expert_ids: list[int] | tuple[int, ...],
    bits: int = 4,
    dtype: str | torch.dtype = torch.bfloat16,
    device: str | torch.device = "cpu",
) -> TopKExpertMlp:
    unique_expert_ids = tuple(dict.fromkeys(int(expert_id) for expert_id in expert_ids))
    experts = {
        expert_id: load_single_expert_mlp(
            store,
            layer=layer,
            expert=expert_id,
            bits=bits,
            dtype=dtype,
            device=device,
        )
        for expert_id in unique_expert_ids
    }
    return TopKExpertMlp(experts)


def _validate_projection_tensors(tensors: GptqProjectionTensors) -> None:
    for name in ("qweight", "qzeros", "scales", "g_idx"):
        value = getattr(tensors, name)
        if not isinstance(value, torch.Tensor):
            msg = f"{name} must be a torch.Tensor"
            raise TypeError(msg)
    if tensors.qweight.ndim != 2:
        raise ValueError(f"qweight must be 2D, got {tuple(tensors.qweight.shape)}")
    if tensors.qzeros.ndim != 2:
        raise ValueError(f"qzeros must be 2D, got {tuple(tensors.qzeros.shape)}")
    if tensors.scales.ndim != 2:
        raise ValueError(f"scales must be 2D, got {tuple(tensors.scales.shape)}")
    if tensors.g_idx.ndim != 1:
        raise ValueError(f"g_idx must be 1D, got {tuple(tensors.g_idx.shape)}")


def _validate_bits(bits: int) -> None:
    if bits not in (2, 4, 8):
        msg = f"This unpacker supports 2/4/8-bit GPTQ rows/cols; got bits={bits}"
        raise ValueError(msg)


def _validate_single_expert_weights(weights: SingleExpertWeights) -> None:
    gate_shape = tuple(weights.gate_proj.shape)
    up_shape = tuple(weights.up_proj.shape)
    down_shape = tuple(weights.down_proj.shape)
    if weights.gate_proj.ndim != 2 or weights.up_proj.ndim != 2 or weights.down_proj.ndim != 2:
        msg = f"SingleExpertMlp weights must be 2D; got gate={gate_shape}, up={up_shape}, down={down_shape}"
        raise ValueError(msg)
    if gate_shape != up_shape:
        msg = f"gate_proj and up_proj shapes must match; got gate={gate_shape}, up={up_shape}"
        raise ValueError(msg)
    if down_shape != (gate_shape[1], gate_shape[0]):
        msg = (
            f"down_proj must have shape [hidden, intermediate]; "
            f"got down={down_shape}, gate={gate_shape}"
        )
        raise ValueError(msg)
    if weights.gate_proj.dtype != weights.up_proj.dtype or weights.gate_proj.dtype != weights.down_proj.dtype:
        msg = (
            f"SingleExpertMlp weights must share dtype; got "
            f"gate={weights.gate_proj.dtype}, up={weights.up_proj.dtype}, down={weights.down_proj.dtype}"
        )
        raise ValueError(msg)
