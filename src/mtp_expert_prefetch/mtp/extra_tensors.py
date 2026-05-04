from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn.functional as F
from safetensors import safe_open
from safetensors.torch import load_file

from mtp_expert_prefetch.repack import (
    GptqProjectionTensors,
    SingleExpertMlp,
    SingleExpertWeights,
    TopKExpertMlp,
    dequantize_gptq_projection,
    resolve_torch_dtype,
    synthesize_g_idx,
)


@dataclass(frozen=True)
class MtpRouterOutput:
    logits: torch.Tensor
    topk_ids: torch.Tensor
    topk_weights: torch.Tensor


@dataclass(frozen=True)
class MtpAttentionConfig:
    num_attention_heads: int = 16
    num_key_value_heads: int = 2
    head_dim: int = 256
    rope_theta: float = 10_000_000.0
    partial_rotary_factor: float = 0.25
    rms_norm_eps: float = 1e-6


def mtp_rms_norm(
    input_tensor: torch.Tensor,
    weight: torch.Tensor,
    *,
    eps: float = 1e-6,
) -> torch.Tensor:
    variance = input_tensor.to(torch.float32).pow(2).mean(dim=-1, keepdim=True)
    output = input_tensor * torch.rsqrt(variance + eps)
    return (output.to(torch.float32) * (1.0 + weight.to(torch.float32))).to(input_tensor.dtype)


def rotate_half(input_tensor: torch.Tensor) -> torch.Tensor:
    left = input_tensor[..., : input_tensor.shape[-1] // 2]
    right = input_tensor[..., input_tensor.shape[-1] // 2 :]
    return torch.cat((-right, left), dim=-1)


def apply_rotary_pos_emb(
    query: torch.Tensor,
    key: torch.Tensor,
    cos: torch.Tensor,
    sin: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    cos = cos.unsqueeze(1)
    sin = sin.unsqueeze(1)
    rotary_dim = cos.shape[-1]

    query_rot, query_pass = query[..., :rotary_dim], query[..., rotary_dim:]
    key_rot, key_pass = key[..., :rotary_dim], key[..., rotary_dim:]
    query_embed = (query_rot * cos) + (rotate_half(query_rot) * sin)
    key_embed = (key_rot * cos) + (rotate_half(key_rot) * sin)
    return torch.cat((query_embed, query_pass), dim=-1), torch.cat((key_embed, key_pass), dim=-1)


def repeat_kv(hidden_states: torch.Tensor, repeats: int) -> torch.Tensor:
    batch, num_key_value_heads, seq_len, head_dim = hidden_states.shape
    if repeats == 1:
        return hidden_states
    hidden_states = hidden_states[:, :, None, :, :].expand(
        batch,
        num_key_value_heads,
        repeats,
        seq_len,
        head_dim,
    )
    return hidden_states.reshape(batch, num_key_value_heads * repeats, seq_len, head_dim)


def dequantize_extra_projection(
    tensors: dict[str, torch.Tensor],
    *,
    prefix: str,
    bits: int = 4,
    group_size: int = 128,
    dtype: str | torch.dtype = torch.bfloat16,
) -> torch.Tensor:
    qweight = tensors[f"{prefix}.qweight"]
    return dequantize_gptq_projection(
        GptqProjectionTensors(
            qweight=qweight,
            qzeros=tensors[f"{prefix}.qzeros"],
            scales=tensors[f"{prefix}.scales"],
            g_idx=synthesize_g_idx(qweight, bits=bits, group_size=group_size),
        ),
        bits=bits,
        dtype=dtype,
    )


def locate_weight_shard(model_dir: str | Path, weight_name: str) -> Path:
    model_dir = Path(model_dir)
    index_path = model_dir / "model.safetensors.index.json"
    with index_path.open("r", encoding="utf-8") as handle:
        index = json.load(handle)
    try:
        shard_name = index["weight_map"][weight_name]
    except KeyError as exc:
        msg = f"{weight_name!r} is not present in {index_path}"
        raise KeyError(msg) from exc
    return model_dir / shard_name


def load_token_embeddings_from_model_dir(
    model_dir: str | Path,
    input_ids: torch.Tensor,
    *,
    weight_name: str = "model.language_model.embed_tokens.weight",
    dtype: str | torch.dtype = torch.bfloat16,
    device: str | torch.device = "cpu",
) -> torch.Tensor:
    shard_path = locate_weight_shard(model_dir, weight_name)
    flat_ids = input_ids.to(device="cpu", dtype=torch.long).reshape(-1)
    target_dtype = resolve_torch_dtype(dtype)
    target_device = torch.device(device)
    with safe_open(shard_path, framework="pt", device="cpu") as handle:
        embedding_slice = handle.get_slice(weight_name)
        rows = embedding_slice[flat_ids]
    return rows.reshape(*input_ids.shape, rows.shape[-1]).to(
        device=target_device,
        dtype=target_dtype,
    )


def load_lm_head_from_model_dir(
    model_dir: str | Path,
    *,
    weight_name: str = "lm_head.weight",
    dtype: str | torch.dtype = torch.bfloat16,
    device: str | torch.device = "cpu",
) -> torch.Tensor:
    shard_path = locate_weight_shard(model_dir, weight_name)
    target_dtype = resolve_torch_dtype(dtype)
    target_device = torch.device(device)
    with safe_open(shard_path, framework="pt", device="cpu") as handle:
        weight = handle.get_tensor(weight_name)
    return weight.to(device=target_device, dtype=target_dtype).contiguous()


class MtpExtraRunner(torch.nn.Module):
    """Minimal runner for Qwen3.6 AutoRound `model_extra_tensors.safetensors`.

    This runner intentionally bypasses Transformers' model loader. It covers the
    MTP pre-fc path, MTP router top-k, and a one-token TopK MoE smoke path.
    """

    def __init__(
        self,
        tensors: dict[str, torch.Tensor],
        *,
        expert_ids: list[int] | tuple[int, ...] = (),
        bits: int = 4,
        group_size: int = 128,
        dtype: str | torch.dtype = torch.bfloat16,
        device: str | torch.device = "cpu",
        attention_config: MtpAttentionConfig | None = None,
        load_moe: bool = True,
    ) -> None:
        super().__init__()
        self.bits = int(bits)
        self.group_size = int(group_size)
        self.target_dtype = resolve_torch_dtype(dtype)
        self.target_device = torch.device(device)
        self.attention_config = attention_config or MtpAttentionConfig()
        self.num_attention_heads = int(self.attention_config.num_attention_heads)
        self.num_key_value_heads = int(self.attention_config.num_key_value_heads)
        self.num_key_value_groups = self.num_attention_heads // self.num_key_value_heads
        self.head_dim = int(self.attention_config.head_dim)
        self.scaling = self.head_dim**-0.5
        self.rotary_dim = int(self.head_dim * self.attention_config.partial_rotary_factor)

        self.register_buffer(
            "pre_fc_norm_embedding",
            self._dense(tensors["mtp.pre_fc_norm_embedding.weight"]),
            persistent=False,
        )
        self.register_buffer(
            "pre_fc_norm_hidden",
            self._dense(tensors["mtp.pre_fc_norm_hidden.weight"]),
            persistent=False,
        )
        self.register_buffer("fc_weight", self._dense(tensors["mtp.fc.weight"]), persistent=False)
        self.register_buffer(
            "router_weight",
            self._dense(tensors["mtp.layers.0.mlp.gate.weight"]),
            persistent=False,
        )
        self.register_buffer(
            "shared_expert_gate_weight",
            self._dense(tensors["mtp.layers.0.mlp.shared_expert_gate.weight"]),
            persistent=False,
        )
        self.register_buffer(
            "input_layernorm",
            self._dense(tensors["mtp.layers.0.input_layernorm.weight"]),
            persistent=False,
        )
        self.register_buffer(
            "post_attention_layernorm",
            self._dense(tensors["mtp.layers.0.post_attention_layernorm.weight"]),
            persistent=False,
        )
        self.register_buffer("norm", self._dense(tensors["mtp.norm.weight"]), persistent=False)
        self.register_buffer(
            "q_norm",
            self._dense(tensors["mtp.layers.0.self_attn.q_norm.weight"]),
            persistent=False,
        )
        self.register_buffer(
            "k_norm",
            self._dense(tensors["mtp.layers.0.self_attn.k_norm.weight"]),
            persistent=False,
        )
        self.register_buffer(
            "q_proj",
            dequantize_extra_projection(
                tensors,
                prefix="mtp.layers.0.self_attn.q_proj",
                bits=self.bits,
                group_size=self.group_size,
                dtype=self.target_dtype,
            ).to(device=self.target_device),
            persistent=False,
        )
        self.register_buffer(
            "k_proj",
            dequantize_extra_projection(
                tensors,
                prefix="mtp.layers.0.self_attn.k_proj",
                bits=self.bits,
                group_size=self.group_size,
                dtype=self.target_dtype,
            ).to(device=self.target_device),
            persistent=False,
        )
        self.register_buffer(
            "v_proj",
            dequantize_extra_projection(
                tensors,
                prefix="mtp.layers.0.self_attn.v_proj",
                bits=self.bits,
                group_size=self.group_size,
                dtype=self.target_dtype,
            ).to(device=self.target_device),
            persistent=False,
        )
        self.register_buffer(
            "o_proj",
            dequantize_extra_projection(
                tensors,
                prefix="mtp.layers.0.self_attn.o_proj",
                bits=self.bits,
                group_size=self.group_size,
                dtype=self.target_dtype,
            ).to(device=self.target_device),
            persistent=False,
        )

        self.shared_expert = None
        self.topk_mlp = None
        if load_moe:
            self.shared_expert = SingleExpertMlp(
                self._load_single_expert_weights(tensors, "mtp.layers.0.mlp.shared_expert")
            )
            self.topk_mlp = self._load_topk_mlp(tensors, expert_ids)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        expert_ids: list[int] | tuple[int, ...] = (),
        bits: int = 4,
        group_size: int = 128,
        dtype: str | torch.dtype = torch.bfloat16,
        device: str | torch.device = "cpu",
        attention_config: MtpAttentionConfig | None = None,
        load_moe: bool = True,
    ) -> MtpExtraRunner:
        tensors = load_file(str(path), device="cpu")
        return cls(
            tensors,
            expert_ids=expert_ids,
            bits=bits,
            group_size=group_size,
            dtype=dtype,
            device=device,
            attention_config=attention_config,
            load_moe=load_moe,
        )

    @property
    def hidden_size(self) -> int:
        return int(self.fc_weight.shape[0])

    @property
    def num_experts(self) -> int:
        return int(self.router_weight.shape[0])

    @property
    def loaded_expert_ids(self) -> tuple[int, ...]:
        if self.topk_mlp is None:
            return ()
        return self.topk_mlp.loaded_expert_ids

    def prefc(self, hidden_states: torch.Tensor, token_embeddings: torch.Tensor) -> torch.Tensor:
        if hidden_states.shape != token_embeddings.shape:
            msg = (
                "hidden_states and token_embeddings must have the same shape; "
                f"got {tuple(hidden_states.shape)} and {tuple(token_embeddings.shape)}"
            )
            raise ValueError(msg)
        if hidden_states.shape[-1] != self.hidden_size:
            msg = f"Expected hidden size {self.hidden_size}, got {hidden_states.shape[-1]}"
            raise ValueError(msg)

        hidden_states = hidden_states.to(device=self.target_device, dtype=self.target_dtype)
        token_embeddings = token_embeddings.to(device=self.target_device, dtype=self.target_dtype)
        hidden_norm = mtp_rms_norm(hidden_states, self.pre_fc_norm_hidden)
        embedding_norm = mtp_rms_norm(token_embeddings, self.pre_fc_norm_embedding)
        return F.linear(torch.cat((embedding_norm, hidden_norm), dim=-1), self.fc_weight)

    def router_topk(self, mtp_hidden_states: torch.Tensor, *, top_k: int = 8) -> MtpRouterOutput:
        if mtp_hidden_states.shape[-1] != self.hidden_size:
            msg = f"Expected hidden size {self.hidden_size}, got {mtp_hidden_states.shape[-1]}"
            raise ValueError(msg)
        if not 0 < top_k <= self.num_experts:
            msg = f"top_k must be in [1, {self.num_experts}], got {top_k}"
            raise ValueError(msg)

        mtp_hidden_states = mtp_hidden_states.to(
            device=self.target_device,
            dtype=self.target_dtype,
        )
        logits = F.linear(mtp_hidden_states, self.router_weight)
        topk_values, topk_ids = torch.topk(logits.float(), top_k, dim=-1)
        topk_weights = F.softmax(topk_values, dim=-1).to(self.target_dtype)
        return MtpRouterOutput(logits=logits, topk_ids=topk_ids, topk_weights=topk_weights)

    def attention(
        self,
        hidden_states: torch.Tensor,
        *,
        position_ids: torch.Tensor | None = None,
        causal: bool = True,
    ) -> torch.Tensor:
        input_shape = hidden_states.shape[:-1]
        batch_size, seq_len = int(input_shape[0]), int(input_shape[1])
        hidden_states = hidden_states.to(device=self.target_device, dtype=self.target_dtype)

        query_states, gate = torch.chunk(
            F.linear(hidden_states, self.q_proj).view(
                *input_shape,
                self.num_attention_heads,
                self.head_dim * 2,
            ),
            2,
            dim=-1,
        )
        gate = gate.reshape(*input_shape, self.num_attention_heads * self.head_dim)

        query_states = mtp_rms_norm(
            query_states,
            self.q_norm,
            eps=self.attention_config.rms_norm_eps,
        )
        key_states = mtp_rms_norm(
            F.linear(hidden_states, self.k_proj).view(
                *input_shape,
                self.num_key_value_heads,
                self.head_dim,
            ),
            self.k_norm,
            eps=self.attention_config.rms_norm_eps,
        )
        value_states = F.linear(hidden_states, self.v_proj).view(
            *input_shape,
            self.num_key_value_heads,
            self.head_dim,
        )

        query_states = query_states.transpose(1, 2)
        key_states = key_states.transpose(1, 2)
        value_states = value_states.transpose(1, 2)
        cos, sin = self.position_embeddings(
            batch_size=batch_size,
            seq_len=seq_len,
            position_ids=position_ids,
            dtype=query_states.dtype,
        )
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)

        key_states = repeat_kv(key_states, self.num_key_value_groups)
        value_states = repeat_kv(value_states, self.num_key_value_groups)
        attn_weights = (
            torch.matmul(query_states, key_states.transpose(2, 3)).to(torch.float32)
            * self.scaling
        )
        if causal:
            causal_mask = torch.triu(
                torch.ones(seq_len, seq_len, dtype=torch.bool, device=self.target_device),
                diagonal=1,
            )
            attn_weights = attn_weights.masked_fill(
                causal_mask[None, None, :, :],
                torch.finfo(torch.float32).min,
            )
        attn_weights = F.softmax(attn_weights, dim=-1, dtype=torch.float32).to(query_states.dtype)
        attn_output = torch.matmul(attn_weights, value_states).transpose(1, 2).contiguous()
        attn_output = attn_output.reshape(*input_shape, self.num_attention_heads * self.head_dim)
        attn_output = attn_output * torch.sigmoid(gate)
        return F.linear(attn_output, self.o_proj)

    def position_embeddings(
        self,
        *,
        batch_size: int,
        seq_len: int,
        position_ids: torch.Tensor | None = None,
        dtype: torch.dtype | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if position_ids is None:
            position_ids = torch.arange(seq_len, device=self.target_device, dtype=torch.long)
            position_ids = position_ids.unsqueeze(0).expand(batch_size, -1)
        else:
            position_ids = position_ids.to(device=self.target_device, dtype=torch.long)
            if position_ids.ndim == 1:
                position_ids = position_ids.unsqueeze(0).expand(batch_size, -1)
        inv_freq = 1.0 / (
            self.attention_config.rope_theta
            ** (
                torch.arange(0, self.rotary_dim, 2, device=self.target_device, dtype=torch.float32)
                / self.rotary_dim
            )
        )
        freqs = torch.einsum("bs,d->bsd", position_ids.to(torch.float32), inv_freq)
        emb = torch.cat((freqs, freqs), dim=-1)
        target_dtype = dtype or self.target_dtype
        return emb.cos().to(target_dtype), emb.sin().to(target_dtype)

    def attention_states(
        self,
        hidden_states: torch.Tensor,
        token_embeddings: torch.Tensor,
        *,
        position_ids: torch.Tensor | None = None,
        causal: bool = True,
    ) -> torch.Tensor:
        hidden_states = self.prefc(hidden_states, token_embeddings)
        residual = hidden_states
        hidden_states = mtp_rms_norm(
            hidden_states,
            self.input_layernorm,
            eps=self.attention_config.rms_norm_eps,
        )
        hidden_states = self.attention(hidden_states, position_ids=position_ids, causal=causal)
        return residual + hidden_states

    def moe_inputs(
        self,
        hidden_states: torch.Tensor,
        token_embeddings: torch.Tensor,
        *,
        position_ids: torch.Tensor | None = None,
        causal: bool = True,
    ) -> torch.Tensor:
        attention_states = self.attention_states(
            hidden_states,
            token_embeddings,
            position_ids=position_ids,
            causal=causal,
        )
        return self.normalize_moe_inputs(attention_states)

    def normalize_moe_inputs(self, attention_states: torch.Tensor) -> torch.Tensor:
        return mtp_rms_norm(
            attention_states,
            self.post_attention_layernorm,
            eps=self.attention_config.rms_norm_eps,
        )

    def finalize_token(
        self,
        attention_state: torch.Tensor,
        moe_output: torch.Tensor,
    ) -> torch.Tensor:
        layer_output = attention_state + moe_output
        return mtp_rms_norm(layer_output, self.norm, eps=self.attention_config.rms_norm_eps)

    def finalize_tokens(
        self,
        attention_states: torch.Tensor,
        moe_outputs: torch.Tensor,
    ) -> torch.Tensor:
        if attention_states.shape != moe_outputs.shape:
            msg = (
                "attention_states and moe_outputs must have the same shape; "
                f"got {tuple(attention_states.shape)} and {tuple(moe_outputs.shape)}"
            )
            raise ValueError(msg)
        layer_output = attention_states + moe_outputs
        return mtp_rms_norm(layer_output, self.norm, eps=self.attention_config.rms_norm_eps)

    def moe_token(
        self,
        mtp_hidden_state: torch.Tensor,
        expert_ids: torch.Tensor,
        expert_weights: torch.Tensor,
    ) -> torch.Tensor:
        if mtp_hidden_state.ndim != 1:
            msg = (
                "mtp_hidden_state must be 1D for this smoke path, "
                f"got {tuple(mtp_hidden_state.shape)}"
            )
            raise ValueError(msg)
        if self.topk_mlp is None or self.shared_expert is None:
            msg = "MTP MoE weights are not loaded; instantiate MtpExtraRunner with load_moe=True."
            raise RuntimeError(msg)
        x = mtp_hidden_state.to(device=self.target_device, dtype=self.target_dtype).unsqueeze(0)
        ids = expert_ids.to(device=self.target_device, dtype=torch.long).reshape(-1)
        weights = expert_weights.to(device=self.target_device, dtype=self.target_dtype).reshape(-1)
        expert_output = self.topk_mlp(x, ids, weights)
        shared_gate = torch.sigmoid(F.linear(x, self.shared_expert_gate_weight))
        return (expert_output + shared_gate * self.shared_expert(x)).squeeze(0)

    def moe_tokens(
        self,
        mtp_hidden_states: torch.Tensor,
        expert_ids: torch.Tensor,
        expert_weights: torch.Tensor,
    ) -> torch.Tensor:
        if self.topk_mlp is None or self.shared_expert is None:
            msg = "MTP MoE weights are not loaded; instantiate MtpExtraRunner with load_moe=True."
            raise RuntimeError(msg)
        if mtp_hidden_states.ndim != 3:
            msg = (
                "mtp_hidden_states must be [batch, seq, hidden] for batched MTP MoE, "
                f"got {tuple(mtp_hidden_states.shape)}"
            )
            raise ValueError(msg)
        if expert_ids.shape != expert_weights.shape:
            msg = (
                f"expert_ids and expert_weights must have same shape; "
                f"got {tuple(expert_ids.shape)} and {tuple(expert_weights.shape)}"
            )
            raise ValueError(msg)
        if expert_ids.shape[:2] != mtp_hidden_states.shape[:2]:
            msg = (
                "expert ids/weights must share [batch, seq] with mtp_hidden_states; "
                f"got {tuple(expert_ids.shape)} and {tuple(mtp_hidden_states.shape)}"
            )
            raise ValueError(msg)

        x = mtp_hidden_states.to(device=self.target_device, dtype=self.target_dtype)
        flat_x = x.reshape(-1, x.shape[-1])
        flat_ids = expert_ids.to(device=self.target_device, dtype=torch.long).reshape(
            flat_x.shape[0],
            -1,
        )
        flat_weights = expert_weights.to(
            device=self.target_device,
            dtype=self.target_dtype,
        ).reshape(flat_x.shape[0], -1)
        output = torch.zeros_like(flat_x)
        for slot in range(flat_ids.shape[1]):
            slot_ids = flat_ids[:, slot]
            slot_weights = flat_weights[:, slot]
            for expert_id in torch.unique(slot_ids).to(device="cpu", dtype=torch.long).tolist():
                key = str(int(expert_id))
                if key not in self.topk_mlp.experts:
                    msg = f"Expert {expert_id} is not loaded; loaded={self.loaded_expert_ids}"
                    raise KeyError(msg)
                mask = slot_ids == int(expert_id)
                if not bool(mask.any()):
                    continue
                expert_output = self.topk_mlp.experts[key](flat_x[mask])
                output[mask] = output[mask] + slot_weights[mask, None] * expert_output
        shared_gate = torch.sigmoid(F.linear(flat_x, self.shared_expert_gate_weight))
        output = output + shared_gate * self.shared_expert(flat_x)
        return output.reshape_as(x)

    def _dense(self, tensor: torch.Tensor) -> torch.Tensor:
        return tensor.to(device=self.target_device, dtype=self.target_dtype).contiguous()

    def _load_topk_mlp(
        self,
        tensors: dict[str, torch.Tensor],
        expert_ids: list[int] | tuple[int, ...],
    ) -> TopKExpertMlp:
        unique_expert_ids = tuple(dict.fromkeys(int(expert_id) for expert_id in expert_ids))
        if not unique_expert_ids:
            unique_expert_ids = (0,)
        experts = {
            expert_id: SingleExpertMlp(
                self._load_single_expert_weights(
                    tensors,
                    f"mtp.layers.0.mlp.experts.{expert_id}",
                )
            )
            for expert_id in unique_expert_ids
        }
        return TopKExpertMlp(experts)

    def _load_single_expert_weights(
        self,
        tensors: dict[str, torch.Tensor],
        prefix: str,
    ) -> SingleExpertWeights:
        return SingleExpertWeights(
            gate_proj=dequantize_extra_projection(
                tensors,
                prefix=f"{prefix}.gate_proj",
                bits=self.bits,
                group_size=self.group_size,
                dtype=self.target_dtype,
            ).to(device=self.target_device),
            up_proj=dequantize_extra_projection(
                tensors,
                prefix=f"{prefix}.up_proj",
                bits=self.bits,
                group_size=self.group_size,
                dtype=self.target_dtype,
            ).to(device=self.target_device),
            down_proj=dequantize_extra_projection(
                tensors,
                prefix=f"{prefix}.down_proj",
                bits=self.bits,
                group_size=self.group_size,
                dtype=self.target_dtype,
            ).to(device=self.target_device),
        )
