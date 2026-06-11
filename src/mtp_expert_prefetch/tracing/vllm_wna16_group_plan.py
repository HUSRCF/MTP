from __future__ import annotations

from typing import Any

import torch

from vllm.triton_utils import tl, triton


@triton.jit
def _write_zeros_to_output(
    c_ptr,
    stride_cm,
    stride_cn,
    pid_n,
    N,
    offs_token,
    token_mask,
    BLOCK_SIZE_M,
    BLOCK_SIZE_N,
    compute_type,
):
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=compute_type)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_token[:, None] + stride_cn * offs_cn[None, :]
    c_mask = token_mask[:, None] & (offs_cn[None, :] < N)
    tl.store(c_ptrs, accumulator, mask=c_mask)


@triton.jit
def reorder_prepared_expert_assignment_group_plan_kernel(
    sorted_token_ids_ptr,
    expert_ids_ptr,
    out_sorted_token_ids_ptr,
    out_expert_ids_ptr,
    group_order_ptr,
    group_offsets_ptr,
    group_source_starts_ptr,
    num_groups,
    max_group_blocks,
    block_size: tl.constexpr,
):
    group_idx = tl.program_id(axis=0)
    local_block = tl.program_id(axis=1)
    if group_idx >= num_groups:
        return

    group_start = tl.load(group_offsets_ptr + group_idx).to(tl.int64)
    group_end = tl.load(group_offsets_ptr + group_idx + 1).to(tl.int64)
    group_blocks = group_end - group_start
    if local_block >= group_blocks:
        return

    src_start = tl.load(group_source_starts_ptr + group_idx).to(tl.int64)
    src_block = src_start + local_block
    dst_block = group_start + local_block
    expert = tl.load(group_order_ptr + group_idx)
    tl.store(out_expert_ids_ptr + dst_block, expert)

    offsets = tl.arange(0, block_size).to(tl.int64)
    src_offsets = src_block * block_size + offsets
    dst_offsets = dst_block * block_size + offsets
    token_ids = tl.load(sorted_token_ids_ptr + src_offsets)
    tl.store(out_sorted_token_ids_ptr + dst_offsets, token_ids)


@triton.jit
def prepare_decode_expert_assignment_layer_prior_kernel(
    topk_ids_ptr,
    expert_map_ptr,
    prior_rank_ptr,
    out_sorted_token_ids_ptr,
    out_expert_ids_ptr,
    num_tokens_post_padded_ptr,
    routed_count: tl.constexpr,
    routed_count_p2: tl.constexpr,
    expert_count: tl.constexpr,
    block_size: tl.constexpr,
    HAS_EXPERT_MAP: tl.constexpr,
    IGNORE_INVALID_EXPERTS: tl.constexpr,
):
    candidates = tl.arange(0, routed_count_p2)
    in_range = candidates < routed_count
    experts = tl.load(topk_ids_ptr + candidates, mask=in_range, other=-1).to(tl.int32)
    valid_expert_id = in_range & (experts >= 0) & (experts < expert_count)
    mapped_experts = experts
    if HAS_EXPERT_MAP:
        mapped_experts = tl.load(
            expert_map_ptr + experts,
            mask=valid_expert_id,
            other=-1,
        ).to(tl.int32)
    valid = valid_expert_id
    if HAS_EXPERT_MAP and IGNORE_INVALID_EXPERTS:
        valid = valid & (mapped_experts >= 0)
    valid_count = tl.sum(valid.to(tl.int32), axis=0)
    ranks = tl.load(prior_rank_ptr + experts, mask=valid, other=2147483647)
    scores = tl.where(valid, ranks * routed_count + candidates, 2147483647)
    selected = tl.full((routed_count_p2,), False, tl.int1)

    for dst in tl.static_range(0, routed_count_p2):
        available_scores = tl.where(selected, 2147483647, scores)
        best_score = tl.min(available_scores, axis=0)
        chosen = tl.min(
            tl.where(available_scores == best_score, candidates, routed_count),
            axis=0,
        )
        do_store = dst < valid_count
        chosen_in_range = chosen < routed_count
        chosen_expert = tl.load(
            topk_ids_ptr + chosen,
            mask=do_store & chosen_in_range,
            other=-1,
        ).to(tl.int32)
        chosen_valid_expert = (chosen_expert >= 0) & (chosen_expert < expert_count)
        if HAS_EXPERT_MAP:
            output_expert = tl.load(
                expert_map_ptr + chosen_expert,
                mask=do_store & chosen_valid_expert,
                other=-1,
            ).to(tl.int32)
        else:
            output_expert = chosen_expert
        tl.store(out_expert_ids_ptr + dst, output_expert, mask=do_store)

        offsets = tl.arange(0, block_size).to(tl.int64)
        token_ids = tl.where(offsets == 0, chosen, routed_count)
        dst_offsets = dst * block_size + offsets
        tl.store(out_sorted_token_ids_ptr + dst_offsets, token_ids, mask=do_store)
        selected = selected | (candidates == chosen)

    tl.store(num_tokens_post_padded_ptr, valid_count * block_size)


def prepare_decode_expert_assignment_layer_prior(
    *,
    topk_ids: torch.Tensor,
    expert_map: torch.Tensor | None = None,
    prior_rank: torch.Tensor,
    block_size: int,
    ignore_invalid_experts: bool = False,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    routed_count = int(topk_ids.numel())
    block_size = int(block_size)
    if routed_count <= 0:
        raise ValueError("decode layer-prior producer requires routed_count > 0")
    if block_size <= 0:
        raise ValueError("decode layer-prior producer requires block_size > 0")
    if topk_ids.ndim != 2 or int(topk_ids.shape[0]) != 1:
        raise ValueError("decode layer-prior producer only supports one token")
    if prior_rank.ndim != 1:
        raise ValueError("decode layer-prior producer requires a 1D prior rank tensor")
    expert_count = int(prior_rank.numel())
    if expert_count <= 0:
        raise ValueError("decode layer-prior producer requires a non-empty prior rank")
    routed_count_p2 = 1 << (routed_count - 1).bit_length()

    out_sorted_token_ids = torch.empty(
        (routed_count * block_size,),
        dtype=torch.int32,
        device=topk_ids.device,
    )
    out_expert_ids = torch.empty((routed_count,), dtype=torch.int32, device=topk_ids.device)
    num_tokens_post_padded = torch.empty((1,), dtype=torch.int32, device=topk_ids.device)
    prepare_decode_expert_assignment_layer_prior_kernel[(1,)](
        topk_ids,
        expert_map if expert_map is not None else prior_rank,
        prior_rank,
        out_sorted_token_ids,
        out_expert_ids,
        num_tokens_post_padded,
        routed_count=routed_count,
        routed_count_p2=routed_count_p2,
        expert_count=expert_count,
        block_size=block_size,
        HAS_EXPERT_MAP=expert_map is not None,
        IGNORE_INVALID_EXPERTS=bool(ignore_invalid_experts),
    )
    return out_sorted_token_ids, out_expert_ids, num_tokens_post_padded


def reorder_prepared_expert_assignment_group_plan(
    *,
    sorted_token_ids: torch.Tensor,
    expert_ids: torch.Tensor,
    group_order: torch.Tensor,
    group_offsets: torch.Tensor,
    group_source_starts: torch.Tensor,
    max_group_blocks: int,
    block_size: int,
    active_block_count: int | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    num_groups = int(group_order.numel()) if group_order is not None else 0
    if num_groups <= 0:
        raise ValueError("producer group-plan reorder requires non-empty group_order")
    if group_offsets is None or int(group_offsets.numel()) != num_groups + 1:
        raise ValueError("producer group-plan reorder requires group_offsets")
    if group_source_starts is None or int(group_source_starts.numel()) != num_groups:
        raise ValueError("producer group-plan reorder requires group_source_starts")
    max_group_blocks = int(max_group_blocks)
    if max_group_blocks <= 0:
        raise ValueError("producer group-plan reorder requires max_group_blocks > 0")
    block_size = int(block_size)
    if block_size <= 0:
        raise ValueError("producer group-plan reorder requires block_size > 0")
    if active_block_count is None:
        # Outside the validated router path, preserve tails conservatively.
        active_block_count = int(expert_ids.numel())
    active_block_count = int(active_block_count)
    if active_block_count < 0 or active_block_count > int(expert_ids.numel()):
        raise ValueError("active_block_count is outside expert_ids bounds")
    active_token_count = active_block_count * block_size
    if active_token_count > int(sorted_token_ids.numel()):
        raise ValueError("active_block_count exceeds sorted_token_ids bounds")

    has_tail = (
        active_token_count < int(sorted_token_ids.numel())
        or active_block_count < int(expert_ids.numel())
    )
    out_sorted_token_ids = (
        sorted_token_ids.clone() if has_tail else torch.empty_like(sorted_token_ids)
    )
    out_expert_ids = expert_ids.clone() if has_tail else torch.empty_like(expert_ids)
    reorder_prepared_expert_assignment_group_plan_kernel[
        (num_groups, max_group_blocks)
    ](
        sorted_token_ids,
        expert_ids,
        out_sorted_token_ids,
        out_expert_ids,
        group_order,
        group_offsets,
        group_source_starts,
        num_groups,
        max_group_blocks,
        block_size=block_size,
    )
    return out_sorted_token_ids, out_expert_ids


@triton.jit
def fused_moe_kernel_gptq_awq_indirect(
    a_ptr,
    b_ptr,
    c_ptr,
    b_scale_ptr,
    b_zp_ptr,
    topk_weights_ptr,
    sorted_token_ids_ptr,
    expert_ids_ptr,
    num_tokens_post_padded_ptr,
    source_block_ids_ptr,
    group_order_ptr,
    group_offsets_ptr,
    group_source_starts_ptr,
    typed_slot_descriptor_ptr,
    typed_slot_packed_weight_descriptor_ptr,
    typed_slot_scale_metadata_handle_ptr,
    typed_slot_aux_metadata_handle_ptr,
    N: tl.constexpr,
    K: tl.constexpr,
    EM,
    num_valid_tokens,
    num_groups,
    source_block_count,
    typed_slot_row_count,
    stride_am,
    stride_ak,
    stride_be,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    stride_bse,
    stride_bsk,
    stride_bsn,
    stride_bze,
    stride_bzk,
    stride_bzn,
    block_k_diviable: tl.constexpr,
    group_size: tl.constexpr,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
    SPLIT_K: tl.constexpr,
    MUL_ROUTED_WEIGHT: tl.constexpr,
    top_k: tl.constexpr,
    compute_type: tl.constexpr,
    has_zp: tl.constexpr,
    use_int4_w4a16: tl.constexpr,
    use_int8_w8a16: tl.constexpr,
    INDIRECT_MODE: tl.constexpr,
    SOURCE_BLOCK_IDS_PACKED: tl.constexpr,
    MAX_GROUPS: tl.constexpr,
    TYPED_SLOT_MODE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(EM, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    logical_pid_m = first_pid_m + ((pid % num_pid_in_group) % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    num_tokens_post_padded = tl.load(num_tokens_post_padded_ptr)
    if logical_pid_m * BLOCK_SIZE_M >= num_tokens_post_padded:
        return

    if TYPED_SLOT_MODE:
        if typed_slot_row_count <= 0:
            return
        if pid_n == 0:
            typed_row = logical_pid_m % typed_slot_row_count
            descriptor_handle = tl.load(typed_slot_descriptor_ptr + typed_row).to(
                tl.int64
            )
            packed_weight_handle = tl.load(
                typed_slot_packed_weight_descriptor_ptr + typed_row
            ).to(tl.int64)
            scale_metadata_handle = tl.load(
                typed_slot_scale_metadata_handle_ptr + typed_row
            ).to(tl.int64)
            aux_metadata_handle = tl.load(
                typed_slot_aux_metadata_handle_ptr + typed_row
            ).to(tl.int64)
            # The first typed-slot WNA16 variant consumes the independent ABI
            # slot once per M-block.  It does not reinterpret current WNA16
            # B/B_scale/B_zp arguments. A zero handle marks an invalid slot.
            invalid_slot = (
                (descriptor_handle == 0)
                | (packed_weight_handle == 0)
                | (scale_metadata_handle == 0)
            )
            if invalid_slot:
                return

    if INDIRECT_MODE == 1:
        if logical_pid_m >= source_block_count:
            return
        encoded_source = tl.load(source_block_ids_ptr + logical_pid_m).to(tl.int64)
        if SOURCE_BLOCK_IDS_PACKED:
            source_pid_m = encoded_source >> 10
            packed_expert = encoded_source & 1023
            off_experts = tl.where(packed_expert == 1023, -1, packed_expert)
        else:
            source_pid_m = encoded_source
            off_experts = tl.load(expert_ids_ptr + source_pid_m).to(tl.int64)
    elif INDIRECT_MODE == 2:
        selected_group = tl.full((), 0, tl.int64)
        for group_idx in tl.static_range(0, MAX_GROUPS):
            if group_idx < num_groups:
                start = tl.load(group_offsets_ptr + group_idx)
                end = tl.load(group_offsets_ptr + group_idx + 1)
                in_group = (logical_pid_m >= start) & (logical_pid_m < end)
                selected_group = tl.where(in_group, group_idx, selected_group)
        group_start = tl.load(group_offsets_ptr + selected_group).to(tl.int64)
        source_start = tl.load(group_source_starts_ptr + selected_group).to(tl.int64)
        source_pid_m = source_start + (logical_pid_m - group_start)
        off_experts = tl.load(group_order_ptr + selected_group).to(tl.int64)
    else:
        source_pid_m = logical_pid_m
        off_experts = tl.load(expert_ids_ptr + source_pid_m).to(tl.int64)

    offs_token_id = source_pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M).to(
        tl.int64
    )
    offs_token = tl.load(sorted_token_ids_ptr + offs_token_id).to(tl.int64)
    token_mask = offs_token < num_valid_tokens

    if off_experts == -1:
        _write_zeros_to_output(
            c_ptr,
            stride_cm,
            stride_cn,
            pid_n,
            N,
            offs_token,
            token_mask,
            BLOCK_SIZE_M,
            BLOCK_SIZE_N,
            compute_type,
        )
        return

    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N).to(tl.int64)) % N
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    a_ptrs = a_ptr + (
        offs_token[:, None] // top_k * stride_am + offs_k[None, :] * stride_ak
    )

    if use_int4_w4a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + (offs_k[:, None] // 2) * stride_bk
            + offs_bn[None, :] * stride_bn
        )
        b_shifter = (offs_k[:, None] % 2) * 4
    elif use_int8_w8a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + offs_k[:, None] * stride_bk
            + offs_bn[None, :] * stride_bn
        )

    if not has_zp and use_int4_w4a16:
        b_zp_num = 8
    if not has_zp and use_int8_w8a16:
        b_zp_num = 128
    elif has_zp and use_int4_w4a16:
        b_zp_shifter = (offs_bn[None, :] % 2) * 4

    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        if not block_k_diviable:
            k_mask = offs_k[:, None] < K - k * BLOCK_SIZE_K
            k_other = 0.0
        else:
            k_mask = None
            k_other = None

        a = tl.load(
            a_ptrs,
            mask=token_mask[:, None] & (offs_k[None, :] < K - k * BLOCK_SIZE_K),
            other=0.0,
        )
        b = tl.load(b_ptrs)
        if use_int4_w4a16:
            b = (b >> b_shifter) & 0xF

        b_scale_ptrs = (
            b_scale_ptr
            + off_experts * stride_bse
            + offs_bn[None, :] * stride_bsn
            + ((offs_k[:, None] + BLOCK_SIZE_K * k) // group_size) * stride_bsk
        )
        b_scale = tl.load(b_scale_ptrs, mask=k_mask, other=k_other)
        b_scale = b_scale.to(tl.float32)

        if has_zp and use_int4_w4a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + (offs_bn[None, :] // 2) * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = (b_zp >> b_zp_shifter) & 0xF
            b_zp = b_zp.to(tl.float32)
        elif has_zp and use_int8_w8a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + offs_bn[None, :] * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = b_zp.to(tl.float32)

        if has_zp:
            b = ((b.to(tl.float32) - b_zp) * b_scale).to(compute_type)
        else:
            b = ((b.to(tl.float32) - b_zp_num) * b_scale).to(compute_type)
        accumulator = tl.dot(a, b, acc=accumulator)

        a_ptrs += BLOCK_SIZE_K * stride_ak
        if use_int4_w4a16:
            b_ptrs += (BLOCK_SIZE_K // 2) * stride_bk
        else:
            b_ptrs += BLOCK_SIZE_K * stride_bk

    if MUL_ROUTED_WEIGHT:
        moe_weight = tl.load(topk_weights_ptr + offs_token, mask=token_mask, other=0)
        accumulator = accumulator * moe_weight[:, None]

    accumulator = accumulator.to(compute_type)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_token[:, None] + stride_cn * offs_cn[None, :]
    c_mask = token_mask[:, None] & (offs_cn[None, :] < N)
    tl.store(c_ptrs, accumulator, mask=c_mask)


@triton.jit
def fused_moe_kernel_gptq_awq_source_block_ids(
    a_ptr,
    b_ptr,
    c_ptr,
    b_scale_ptr,
    b_zp_ptr,
    topk_weights_ptr,
    sorted_token_ids_ptr,
    expert_ids_ptr,
    num_tokens_post_padded_ptr,
    source_block_ids_ptr,
    N: tl.constexpr,
    K: tl.constexpr,
    EM,
    num_valid_tokens,
    source_block_count,
    stride_am,
    stride_ak,
    stride_be,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    stride_bse,
    stride_bsk,
    stride_bsn,
    stride_bze,
    stride_bzk,
    stride_bzn,
    block_k_diviable: tl.constexpr,
    group_size: tl.constexpr,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
    SPLIT_K: tl.constexpr,
    MUL_ROUTED_WEIGHT: tl.constexpr,
    top_k: tl.constexpr,
    compute_type: tl.constexpr,
    has_zp: tl.constexpr,
    use_int4_w4a16: tl.constexpr,
    use_int8_w8a16: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(EM, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    logical_pid_m = first_pid_m + ((pid % num_pid_in_group) % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    num_tokens_post_padded = tl.load(num_tokens_post_padded_ptr)
    if logical_pid_m * BLOCK_SIZE_M >= num_tokens_post_padded:
        return
    if logical_pid_m >= source_block_count:
        return

    source_pid_m = tl.load(source_block_ids_ptr + logical_pid_m).to(tl.int64)
    off_experts = tl.load(expert_ids_ptr + source_pid_m).to(tl.int64)

    offs_token_id = source_pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M).to(
        tl.int64
    )
    offs_token = tl.load(sorted_token_ids_ptr + offs_token_id).to(tl.int64)
    token_mask = offs_token < num_valid_tokens

    if off_experts == -1:
        _write_zeros_to_output(
            c_ptr,
            stride_cm,
            stride_cn,
            pid_n,
            N,
            offs_token,
            token_mask,
            BLOCK_SIZE_M,
            BLOCK_SIZE_N,
            compute_type,
        )
        return

    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N).to(tl.int64)) % N
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    a_ptrs = a_ptr + (
        offs_token[:, None] // top_k * stride_am + offs_k[None, :] * stride_ak
    )

    if use_int4_w4a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + (offs_k[:, None] // 2) * stride_bk
            + offs_bn[None, :] * stride_bn
        )
        b_shifter = (offs_k[:, None] % 2) * 4
    elif use_int8_w8a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + offs_k[:, None] * stride_bk
            + offs_bn[None, :] * stride_bn
        )

    if not has_zp and use_int4_w4a16:
        b_zp_num = 8
    if not has_zp and use_int8_w8a16:
        b_zp_num = 128
    elif has_zp and use_int4_w4a16:
        b_zp_shifter = (offs_bn[None, :] % 2) * 4

    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        if not block_k_diviable:
            k_mask = offs_k[:, None] < K - k * BLOCK_SIZE_K
            k_other = 0.0
        else:
            k_mask = None
            k_other = None

        a = tl.load(
            a_ptrs,
            mask=token_mask[:, None] & (offs_k[None, :] < K - k * BLOCK_SIZE_K),
            other=0.0,
        )
        b = tl.load(b_ptrs)
        if use_int4_w4a16:
            b = (b >> b_shifter) & 0xF

        b_scale_ptrs = (
            b_scale_ptr
            + off_experts * stride_bse
            + offs_bn[None, :] * stride_bsn
            + ((offs_k[:, None] + BLOCK_SIZE_K * k) // group_size) * stride_bsk
        )
        b_scale = tl.load(b_scale_ptrs, mask=k_mask, other=k_other)
        b_scale = b_scale.to(tl.float32)

        if has_zp and use_int4_w4a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + (offs_bn[None, :] // 2) * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = (b_zp >> b_zp_shifter) & 0xF
            b_zp = b_zp.to(tl.float32)
        elif has_zp and use_int8_w8a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + offs_bn[None, :] * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = b_zp.to(tl.float32)

        if has_zp:
            b = ((b.to(tl.float32) - b_zp) * b_scale).to(compute_type)
        else:
            b = ((b.to(tl.float32) - b_zp_num) * b_scale).to(compute_type)
        accumulator = tl.dot(a, b, acc=accumulator)

        a_ptrs += BLOCK_SIZE_K * stride_ak
        if use_int4_w4a16:
            b_ptrs += (BLOCK_SIZE_K // 2) * stride_bk
        else:
            b_ptrs += BLOCK_SIZE_K * stride_bk

    if MUL_ROUTED_WEIGHT:
        moe_weight = tl.load(topk_weights_ptr + offs_token, mask=token_mask, other=0)
        accumulator = accumulator * moe_weight[:, None]

    accumulator = accumulator.to(compute_type)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_token[:, None] + stride_cn * offs_cn[None, :]
    c_mask = token_mask[:, None] & (offs_cn[None, :] < N)
    tl.store(c_ptrs, accumulator, mask=c_mask)


@triton.jit
def fused_moe_kernel_gptq_awq_group_plan_direct(
    a_ptr,
    b_ptr,
    c_ptr,
    b_scale_ptr,
    b_zp_ptr,
    topk_weights_ptr,
    sorted_token_ids_ptr,
    num_tokens_post_padded_ptr,
    group_order_ptr,
    group_offsets_ptr,
    group_source_starts_ptr,
    N: tl.constexpr,
    K: tl.constexpr,
    num_valid_tokens,
    num_groups,
    max_group_blocks,
    stride_am,
    stride_ak,
    stride_be,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    stride_bse,
    stride_bsk,
    stride_bsn,
    stride_bze,
    stride_bzk,
    stride_bzn,
    block_k_diviable: tl.constexpr,
    group_size: tl.constexpr,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
    SPLIT_K: tl.constexpr,
    MUL_ROUTED_WEIGHT: tl.constexpr,
    top_k: tl.constexpr,
    compute_type: tl.constexpr,
    has_zp: tl.constexpr,
    use_int4_w4a16: tl.constexpr,
    use_int8_w8a16: tl.constexpr,
):
    group_idx = tl.program_id(axis=0)
    pid_group_n = tl.program_id(axis=1)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    local_pid_m = pid_group_n % max_group_blocks
    pid_n = pid_group_n // max_group_blocks

    if group_idx >= num_groups:
        return
    if pid_n >= num_pid_n:
        return

    group_start = tl.load(group_offsets_ptr + group_idx).to(tl.int64)
    group_end = tl.load(group_offsets_ptr + group_idx + 1).to(tl.int64)
    group_blocks = group_end - group_start
    if local_pid_m >= group_blocks:
        return

    source_start = tl.load(group_source_starts_ptr + group_idx).to(tl.int64)
    source_pid_m = source_start + local_pid_m
    off_experts = tl.load(group_order_ptr + group_idx).to(tl.int64)

    num_tokens_post_padded = tl.load(num_tokens_post_padded_ptr)
    if source_pid_m * BLOCK_SIZE_M >= num_tokens_post_padded:
        return

    offs_token_id = source_pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M).to(
        tl.int64
    )
    offs_token = tl.load(sorted_token_ids_ptr + offs_token_id).to(tl.int64)
    token_mask = offs_token < num_valid_tokens

    if off_experts == -1:
        _write_zeros_to_output(
            c_ptr,
            stride_cm,
            stride_cn,
            pid_n,
            N,
            offs_token,
            token_mask,
            BLOCK_SIZE_M,
            BLOCK_SIZE_N,
            compute_type,
        )
        return

    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N).to(tl.int64)) % N
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    a_ptrs = a_ptr + (
        offs_token[:, None] // top_k * stride_am + offs_k[None, :] * stride_ak
    )

    if use_int4_w4a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + (offs_k[:, None] // 2) * stride_bk
            + offs_bn[None, :] * stride_bn
        )
        b_shifter = (offs_k[:, None] % 2) * 4
    elif use_int8_w8a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + offs_k[:, None] * stride_bk
            + offs_bn[None, :] * stride_bn
        )

    if not has_zp and use_int4_w4a16:
        b_zp_num = 8
    if not has_zp and use_int8_w8a16:
        b_zp_num = 128
    elif has_zp and use_int4_w4a16:
        b_zp_shifter = (offs_bn[None, :] % 2) * 4

    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        if not block_k_diviable:
            k_mask = offs_k[:, None] < K - k * BLOCK_SIZE_K
            k_other = 0.0
        else:
            k_mask = None
            k_other = None

        a = tl.load(
            a_ptrs,
            mask=token_mask[:, None] & (offs_k[None, :] < K - k * BLOCK_SIZE_K),
            other=0.0,
        )
        b = tl.load(b_ptrs)
        if use_int4_w4a16:
            b = (b >> b_shifter) & 0xF

        b_scale_ptrs = (
            b_scale_ptr
            + off_experts * stride_bse
            + offs_bn[None, :] * stride_bsn
            + ((offs_k[:, None] + BLOCK_SIZE_K * k) // group_size) * stride_bsk
        )
        b_scale = tl.load(b_scale_ptrs, mask=k_mask, other=k_other)
        b_scale = b_scale.to(tl.float32)

        if has_zp and use_int4_w4a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + (offs_bn[None, :] // 2) * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = (b_zp >> b_zp_shifter) & 0xF
            b_zp = b_zp.to(tl.float32)
        elif has_zp and use_int8_w8a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + offs_bn[None, :] * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = b_zp.to(tl.float32)

        if has_zp:
            b = ((b.to(tl.float32) - b_zp) * b_scale).to(compute_type)
        else:
            b = ((b.to(tl.float32) - b_zp_num) * b_scale).to(compute_type)
        accumulator = tl.dot(a, b, acc=accumulator)

        a_ptrs += BLOCK_SIZE_K * stride_ak
        if use_int4_w4a16:
            b_ptrs += (BLOCK_SIZE_K // 2) * stride_bk
        else:
            b_ptrs += BLOCK_SIZE_K * stride_bk

    if MUL_ROUTED_WEIGHT:
        moe_weight = tl.load(topk_weights_ptr + offs_token, mask=token_mask, other=0)
        accumulator = accumulator * moe_weight[:, None]

    accumulator = accumulator.to(compute_type)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_token[:, None] + stride_cn * offs_cn[None, :]
    c_mask = token_mask[:, None] & (offs_cn[None, :] < N)
    tl.store(c_ptrs, accumulator, mask=c_mask)


def invoke_fused_moe_wna16_triton_kernel_source_block_ids(
    *,
    fused_moe_impl: Any,
    source_block_ids: torch.Tensor,
    A: torch.Tensor,
    B: torch.Tensor,
    C: torch.Tensor,
    B_scale: torch.Tensor | None,
    B_zp: torch.Tensor | None,
    topk_weights: torch.Tensor | None,
    sorted_token_ids: torch.Tensor,
    expert_ids: torch.Tensor,
    num_tokens_post_padded: torch.Tensor,
    mul_routed_weight: bool,
    top_k: int,
    config: dict[str, Any],
    compute_type: tl.dtype,
    use_int8_w8a16: bool,
    use_int4_w4a16: bool,
    block_shape: list[int] | None,
) -> None:
    assert B_scale is not None and B_scale.ndim == 3
    assert B_zp is None or B_zp.ndim == 3
    assert block_shape is not None and block_shape[0] == 0
    if source_block_ids is None or int(source_block_ids.numel()) <= 0:
        raise ValueError("source_block_ids kernel requires a non-empty mapping")

    M = A.size(0)
    num_tokens = M * top_k
    EM = sorted_token_ids.size(0)
    if A.size(0) < config["BLOCK_SIZE_M"]:
        EM = min(sorted_token_ids.size(0), A.size(0) * top_k * config["BLOCK_SIZE_M"])
    grid = lambda META: (
        triton.cdiv(EM, META["BLOCK_SIZE_M"])
        * triton.cdiv(B.size(1), META["BLOCK_SIZE_N"]),
    )
    launch_config = config.copy()
    launch_config.update(
        fused_moe_impl.get_moe_wna16_block_config(
            config=launch_config,
            use_moe_wna16_cuda=False,
            num_valid_tokens=num_tokens,
            size_k=A.size(1),
            size_n=B.size(1),
            num_experts=B.size(1),
            group_size=block_shape[1],
            real_top_k=top_k,
            block_size_m=launch_config["BLOCK_SIZE_M"],
        )
    )

    fused_moe_kernel_gptq_awq_source_block_ids[grid](
        A,
        B,
        C,
        B_scale,
        B_zp,
        topk_weights,
        sorted_token_ids,
        expert_ids,
        num_tokens_post_padded,
        source_block_ids,
        B.size(1),
        A.size(1),
        EM,
        num_tokens,
        int(source_block_ids.numel()),
        A.stride(0),
        A.stride(1),
        B.stride(0),
        B.stride(2),
        B.stride(1),
        C.stride(1),
        C.stride(2),
        B_scale.stride(0),
        B_scale.stride(2),
        B_scale.stride(1),
        B_zp.stride(0) if B_zp is not None else 0,
        B_zp.stride(2) if B_zp is not None else 0,
        B_zp.stride(1) if B_zp is not None else 0,
        block_k_diviable=A.size(1) % launch_config["BLOCK_SIZE_K"] == 0,
        group_size=block_shape[1],
        MUL_ROUTED_WEIGHT=mul_routed_weight,
        top_k=top_k,
        compute_type=compute_type,
        has_zp=B_zp is not None,
        use_int4_w4a16=use_int4_w4a16,
        use_int8_w8a16=use_int8_w8a16,
        **launch_config,
    )


def invoke_fused_moe_wna16_triton_kernel_group_plan_direct(
    *,
    fused_moe_impl: Any,
    group_order: torch.Tensor,
    group_offsets: torch.Tensor,
    group_source_starts: torch.Tensor,
    max_group_blocks: int,
    A: torch.Tensor,
    B: torch.Tensor,
    C: torch.Tensor,
    B_scale: torch.Tensor | None,
    B_zp: torch.Tensor | None,
    topk_weights: torch.Tensor | None,
    sorted_token_ids: torch.Tensor,
    num_tokens_post_padded: torch.Tensor,
    mul_routed_weight: bool,
    top_k: int,
    config: dict[str, Any],
    compute_type: tl.dtype,
    use_int8_w8a16: bool,
    use_int4_w4a16: bool,
    block_shape: list[int] | None,
) -> None:
    assert B_scale is not None and B_scale.ndim == 3
    assert B_zp is None or B_zp.ndim == 3
    assert block_shape is not None and block_shape[0] == 0
    num_groups = int(group_order.numel()) if group_order is not None else 0
    if num_groups <= 0:
        raise ValueError("group_plan_direct requires non-empty group_order")
    if group_offsets is None or int(group_offsets.numel()) != num_groups + 1:
        raise ValueError("group_plan_direct requires group_offsets length group_count + 1")
    if group_source_starts is None or int(group_source_starts.numel()) != num_groups:
        raise ValueError("group_plan_direct requires group_source_starts per group")
    max_group_blocks = int(max_group_blocks)
    if max_group_blocks <= 0:
        raise ValueError("group_plan_direct requires max_group_blocks > 0")

    M = A.size(0)
    num_tokens = M * top_k
    launch_config = config.copy()
    launch_config.update(
        fused_moe_impl.get_moe_wna16_block_config(
            config=launch_config,
            use_moe_wna16_cuda=False,
            num_valid_tokens=num_tokens,
            size_k=A.size(1),
            size_n=B.size(1),
            num_experts=B.size(1),
            group_size=block_shape[1],
            real_top_k=top_k,
            block_size_m=launch_config["BLOCK_SIZE_M"],
        )
    )
    grid = lambda META: (
        num_groups,
        max_group_blocks * triton.cdiv(B.size(1), META["BLOCK_SIZE_N"]),
    )

    fused_moe_kernel_gptq_awq_group_plan_direct[grid](
        A,
        B,
        C,
        B_scale,
        B_zp,
        topk_weights,
        sorted_token_ids,
        num_tokens_post_padded,
        group_order,
        group_offsets,
        group_source_starts,
        B.size(1),
        A.size(1),
        num_tokens,
        num_groups,
        max_group_blocks,
        A.stride(0),
        A.stride(1),
        B.stride(0),
        B.stride(2),
        B.stride(1),
        C.stride(1),
        C.stride(2),
        B_scale.stride(0),
        B_scale.stride(2),
        B_scale.stride(1),
        B_zp.stride(0) if B_zp is not None else 0,
        B_zp.stride(2) if B_zp is not None else 0,
        B_zp.stride(1) if B_zp is not None else 0,
        block_k_diviable=A.size(1) % launch_config["BLOCK_SIZE_K"] == 0,
        group_size=block_shape[1],
        MUL_ROUTED_WEIGHT=mul_routed_weight,
        top_k=top_k,
        compute_type=compute_type,
        has_zp=B_zp is not None,
        use_int4_w4a16=use_int4_w4a16,
        use_int8_w8a16=use_int8_w8a16,
        **launch_config,
    )


@triton.jit
def fused_moe_kernel_gptq_awq_direct_topk_layer_prior(
    a_ptr,
    b_ptr,
    c_ptr,
    b_scale_ptr,
    b_zp_ptr,
    topk_weights_ptr,
    topk_ids_ptr,
    expert_map_ptr,
    prior_rank_ptr,
    N: tl.constexpr,
    K: tl.constexpr,
    expert_count: tl.constexpr,
    route_count: tl.constexpr,
    stride_am,
    stride_ak,
    stride_be,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    stride_bse,
    stride_bsk,
    stride_bsn,
    stride_bze,
    stride_bzk,
    stride_bzn,
    block_k_diviable: tl.constexpr,
    group_size: tl.constexpr,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
    SPLIT_K: tl.constexpr,
    MUL_ROUTED_WEIGHT: tl.constexpr,
    dispatch_top_k: tl.constexpr,
    route_count_p2: tl.constexpr,
    compute_type: tl.constexpr,
    has_zp: tl.constexpr,
    use_int4_w4a16: tl.constexpr,
    use_int8_w8a16: tl.constexpr,
    HAS_EXPERT_MAP: tl.constexpr,
    IGNORE_INVALID_EXPERTS: tl.constexpr,
    IDENTITY_ORDER: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    logical_pid_m = pid % route_count
    pid_n = pid // route_count
    if pid_n >= num_pid_n:
        return

    candidates = tl.arange(0, route_count_p2)
    in_range = candidates < route_count
    experts = tl.load(topk_ids_ptr + candidates, mask=in_range, other=-1).to(tl.int32)
    valid_expert_id = in_range & (experts >= 0) & (experts < expert_count)
    mapped_experts = experts
    if HAS_EXPERT_MAP:
        mapped_experts = tl.load(
            expert_map_ptr + experts,
            mask=valid_expert_id,
            other=-1,
        ).to(tl.int32)
    valid = valid_expert_id
    if HAS_EXPERT_MAP and IGNORE_INVALID_EXPERTS:
        valid = valid & (mapped_experts >= 0)
    valid_count = tl.sum(valid.to(tl.int32), axis=0)
    if (not IDENTITY_ORDER) and logical_pid_m >= valid_count:
        return

    if IDENTITY_ORDER:
        chosen = logical_pid_m
    else:
        ranks = tl.load(prior_rank_ptr + experts, mask=valid, other=2147483647)
        scores = tl.where(valid, ranks * route_count + candidates, 2147483647)
        selected = tl.full((route_count_p2,), False, tl.int1)
        chosen = tl.full((), route_count, tl.int32)
        for dst in tl.static_range(0, route_count_p2):
            available_scores = tl.where(selected, 2147483647, scores)
            best_score = tl.min(available_scores, axis=0)
            current = tl.min(
                tl.where(available_scores == best_score, candidates, route_count),
                axis=0,
            )
            chosen = tl.where(logical_pid_m == dst, current, chosen)
            selected = selected | (candidates == current)

    chosen_in_range = chosen < route_count
    chosen_expert = tl.load(
        topk_ids_ptr + chosen,
        mask=chosen_in_range,
        other=-1,
    ).to(tl.int32)
    chosen_valid_expert = (chosen_expert >= 0) & (chosen_expert < expert_count)
    if HAS_EXPERT_MAP:
        off_experts = tl.load(
            expert_map_ptr + chosen_expert,
            mask=chosen_valid_expert,
            other=-1,
        ).to(tl.int64)
    else:
        off_experts = chosen_expert.to(tl.int64)

    offsets = tl.arange(0, BLOCK_SIZE_M).to(tl.int64)
    offs_token = tl.where(offsets == 0, chosen.to(tl.int64), route_count)
    token_mask = offs_token < route_count

    if off_experts == -1:
        _write_zeros_to_output(
            c_ptr,
            stride_cm,
            stride_cn,
            pid_n,
            N,
            offs_token,
            token_mask,
            BLOCK_SIZE_M,
            BLOCK_SIZE_N,
            compute_type,
        )
        return

    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N).to(tl.int64)) % N
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    a_ptrs = a_ptr + (
        offs_token[:, None] // dispatch_top_k * stride_am + offs_k[None, :] * stride_ak
    )

    if use_int4_w4a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + (offs_k[:, None] // 2) * stride_bk
            + offs_bn[None, :] * stride_bn
        )
        b_shifter = (offs_k[:, None] % 2) * 4
    elif use_int8_w8a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + offs_k[:, None] * stride_bk
            + offs_bn[None, :] * stride_bn
        )

    if not has_zp and use_int4_w4a16:
        b_zp_num = 8
    if not has_zp and use_int8_w8a16:
        b_zp_num = 128
    elif has_zp and use_int4_w4a16:
        b_zp_shifter = (offs_bn[None, :] % 2) * 4

    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        if not block_k_diviable:
            k_mask = offs_k[:, None] < K - k * BLOCK_SIZE_K
            k_other = 0.0
        else:
            k_mask = None
            k_other = None

        a = tl.load(
            a_ptrs,
            mask=token_mask[:, None] & (offs_k[None, :] < K - k * BLOCK_SIZE_K),
            other=0.0,
        )
        b = tl.load(b_ptrs)
        if use_int4_w4a16:
            b = (b >> b_shifter) & 0xF

        b_scale_ptrs = (
            b_scale_ptr
            + off_experts * stride_bse
            + offs_bn[None, :] * stride_bsn
            + ((offs_k[:, None] + BLOCK_SIZE_K * k) // group_size) * stride_bsk
        )
        b_scale = tl.load(b_scale_ptrs, mask=k_mask, other=k_other)
        b_scale = b_scale.to(tl.float32)

        if has_zp and use_int4_w4a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + (offs_bn[None, :] // 2) * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = (b_zp >> b_zp_shifter) & 0xF
            b_zp = b_zp.to(tl.float32)
        elif has_zp and use_int8_w8a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + offs_bn[None, :] * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = b_zp.to(tl.float32)

        if has_zp:
            b = ((b.to(tl.float32) - b_zp) * b_scale).to(compute_type)
        else:
            b = ((b.to(tl.float32) - b_zp_num) * b_scale).to(compute_type)
        accumulator = tl.dot(a, b, acc=accumulator)

        a_ptrs += BLOCK_SIZE_K * stride_ak
        if use_int4_w4a16:
            b_ptrs += (BLOCK_SIZE_K // 2) * stride_bk
        else:
            b_ptrs += BLOCK_SIZE_K * stride_bk

    if MUL_ROUTED_WEIGHT:
        moe_weight = tl.load(topk_weights_ptr + offs_token, mask=token_mask, other=0)
        accumulator = accumulator * moe_weight[:, None]

    accumulator = accumulator.to(compute_type)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_token[:, None] + stride_cn * offs_cn[None, :]
    c_mask = token_mask[:, None] & (offs_cn[None, :] < N)
    tl.store(c_ptrs, accumulator, mask=c_mask)


@triton.jit
def fused_moe_kernel_gptq_awq_direct_topk8_layer_prior(
    a_ptr,
    b_ptr,
    c_ptr,
    b_scale_ptr,
    b_zp_ptr,
    topk_weights_ptr,
    topk_ids_ptr,
    expert_map_ptr,
    prior_rank_ptr,
    N: tl.constexpr,
    K: tl.constexpr,
    expert_count: tl.constexpr,
    stride_am,
    stride_ak,
    stride_be,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    stride_bse,
    stride_bsk,
    stride_bsn,
    stride_bze,
    stride_bzk,
    stride_bzn,
    block_k_diviable: tl.constexpr,
    group_size: tl.constexpr,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
    SPLIT_K: tl.constexpr,
    MUL_ROUTED_WEIGHT: tl.constexpr,
    compute_type: tl.constexpr,
    has_zp: tl.constexpr,
    use_int4_w4a16: tl.constexpr,
    use_int8_w8a16: tl.constexpr,
    HAS_EXPERT_MAP: tl.constexpr,
    IGNORE_INVALID_EXPERTS: tl.constexpr,
    IDENTITY_ORDER: tl.constexpr,
):
    logical_pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    expert0 = tl.load(topk_ids_ptr + 0).to(tl.int32)
    expert1 = tl.load(topk_ids_ptr + 1).to(tl.int32)
    expert2 = tl.load(topk_ids_ptr + 2).to(tl.int32)
    expert3 = tl.load(topk_ids_ptr + 3).to(tl.int32)
    expert4 = tl.load(topk_ids_ptr + 4).to(tl.int32)
    expert5 = tl.load(topk_ids_ptr + 5).to(tl.int32)
    expert6 = tl.load(topk_ids_ptr + 6).to(tl.int32)
    expert7 = tl.load(topk_ids_ptr + 7).to(tl.int32)

    valid0 = (expert0 >= 0) & (expert0 < expert_count)
    valid1 = (expert1 >= 0) & (expert1 < expert_count)
    valid2 = (expert2 >= 0) & (expert2 < expert_count)
    valid3 = (expert3 >= 0) & (expert3 < expert_count)
    valid4 = (expert4 >= 0) & (expert4 < expert_count)
    valid5 = (expert5 >= 0) & (expert5 < expert_count)
    valid6 = (expert6 >= 0) & (expert6 < expert_count)
    valid7 = (expert7 >= 0) & (expert7 < expert_count)

    mapped0 = expert0
    mapped1 = expert1
    mapped2 = expert2
    mapped3 = expert3
    mapped4 = expert4
    mapped5 = expert5
    mapped6 = expert6
    mapped7 = expert7
    if HAS_EXPERT_MAP:
        mapped0 = tl.load(expert_map_ptr + expert0, mask=valid0, other=-1).to(tl.int32)
        mapped1 = tl.load(expert_map_ptr + expert1, mask=valid1, other=-1).to(tl.int32)
        mapped2 = tl.load(expert_map_ptr + expert2, mask=valid2, other=-1).to(tl.int32)
        mapped3 = tl.load(expert_map_ptr + expert3, mask=valid3, other=-1).to(tl.int32)
        mapped4 = tl.load(expert_map_ptr + expert4, mask=valid4, other=-1).to(tl.int32)
        mapped5 = tl.load(expert_map_ptr + expert5, mask=valid5, other=-1).to(tl.int32)
        mapped6 = tl.load(expert_map_ptr + expert6, mask=valid6, other=-1).to(tl.int32)
        mapped7 = tl.load(expert_map_ptr + expert7, mask=valid7, other=-1).to(tl.int32)
    if HAS_EXPERT_MAP and IGNORE_INVALID_EXPERTS:
        valid0 = valid0 & (mapped0 >= 0)
        valid1 = valid1 & (mapped1 >= 0)
        valid2 = valid2 & (mapped2 >= 0)
        valid3 = valid3 & (mapped3 >= 0)
        valid4 = valid4 & (mapped4 >= 0)
        valid5 = valid5 & (mapped5 >= 0)
        valid6 = valid6 & (mapped6 >= 0)
        valid7 = valid7 & (mapped7 >= 0)

    valid_count = (
        valid0.to(tl.int32)
        + valid1.to(tl.int32)
        + valid2.to(tl.int32)
        + valid3.to(tl.int32)
        + valid4.to(tl.int32)
        + valid5.to(tl.int32)
        + valid6.to(tl.int32)
        + valid7.to(tl.int32)
    )
    if (not IDENTITY_ORDER) and logical_pid_m >= valid_count:
        return

    if IDENTITY_ORDER:
        pos0 = 0
        pos1 = 1
        pos2 = 2
        pos3 = 3
        pos4 = 4
        pos5 = 5
        pos6 = 6
        pos7 = 7
    else:
        rank0 = tl.load(prior_rank_ptr + expert0, mask=valid0, other=2147483647)
        rank1 = tl.load(prior_rank_ptr + expert1, mask=valid1, other=2147483647)
        rank2 = tl.load(prior_rank_ptr + expert2, mask=valid2, other=2147483647)
        rank3 = tl.load(prior_rank_ptr + expert3, mask=valid3, other=2147483647)
        rank4 = tl.load(prior_rank_ptr + expert4, mask=valid4, other=2147483647)
        rank5 = tl.load(prior_rank_ptr + expert5, mask=valid5, other=2147483647)
        rank6 = tl.load(prior_rank_ptr + expert6, mask=valid6, other=2147483647)
        rank7 = tl.load(prior_rank_ptr + expert7, mask=valid7, other=2147483647)
        score0 = tl.where(valid0, rank0 * 8 + 0, 2147483647)
        score1 = tl.where(valid1, rank1 * 8 + 1, 2147483647)
        score2 = tl.where(valid2, rank2 * 8 + 2, 2147483647)
        score3 = tl.where(valid3, rank3 * 8 + 3, 2147483647)
        score4 = tl.where(valid4, rank4 * 8 + 4, 2147483647)
        score5 = tl.where(valid5, rank5 * 8 + 5, 2147483647)
        score6 = tl.where(valid6, rank6 * 8 + 6, 2147483647)
        score7 = tl.where(valid7, rank7 * 8 + 7, 2147483647)

        pos0 = (
            (score1 < score0).to(tl.int32)
            + (score2 < score0).to(tl.int32)
            + (score3 < score0).to(tl.int32)
            + (score4 < score0).to(tl.int32)
            + (score5 < score0).to(tl.int32)
            + (score6 < score0).to(tl.int32)
            + (score7 < score0).to(tl.int32)
        )
        pos1 = (
            (score0 < score1).to(tl.int32)
            + (score2 < score1).to(tl.int32)
            + (score3 < score1).to(tl.int32)
            + (score4 < score1).to(tl.int32)
            + (score5 < score1).to(tl.int32)
            + (score6 < score1).to(tl.int32)
            + (score7 < score1).to(tl.int32)
        )
        pos2 = (
            (score0 < score2).to(tl.int32)
            + (score1 < score2).to(tl.int32)
            + (score3 < score2).to(tl.int32)
            + (score4 < score2).to(tl.int32)
            + (score5 < score2).to(tl.int32)
            + (score6 < score2).to(tl.int32)
            + (score7 < score2).to(tl.int32)
        )
        pos3 = (
            (score0 < score3).to(tl.int32)
            + (score1 < score3).to(tl.int32)
            + (score2 < score3).to(tl.int32)
            + (score4 < score3).to(tl.int32)
            + (score5 < score3).to(tl.int32)
            + (score6 < score3).to(tl.int32)
            + (score7 < score3).to(tl.int32)
        )
        pos4 = (
            (score0 < score4).to(tl.int32)
            + (score1 < score4).to(tl.int32)
            + (score2 < score4).to(tl.int32)
            + (score3 < score4).to(tl.int32)
            + (score5 < score4).to(tl.int32)
            + (score6 < score4).to(tl.int32)
            + (score7 < score4).to(tl.int32)
        )
        pos5 = (
            (score0 < score5).to(tl.int32)
            + (score1 < score5).to(tl.int32)
            + (score2 < score5).to(tl.int32)
            + (score3 < score5).to(tl.int32)
            + (score4 < score5).to(tl.int32)
            + (score6 < score5).to(tl.int32)
            + (score7 < score5).to(tl.int32)
        )
        pos6 = (
            (score0 < score6).to(tl.int32)
            + (score1 < score6).to(tl.int32)
            + (score2 < score6).to(tl.int32)
            + (score3 < score6).to(tl.int32)
            + (score4 < score6).to(tl.int32)
            + (score5 < score6).to(tl.int32)
            + (score7 < score6).to(tl.int32)
        )
        pos7 = (
            (score0 < score7).to(tl.int32)
            + (score1 < score7).to(tl.int32)
            + (score2 < score7).to(tl.int32)
            + (score3 < score7).to(tl.int32)
            + (score4 < score7).to(tl.int32)
            + (score5 < score7).to(tl.int32)
            + (score6 < score7).to(tl.int32)
        )

    if IDENTITY_ORDER:
        chosen = logical_pid_m
    else:
        chosen = tl.full((), 8, tl.int32)
        chosen = tl.where(valid0 & (pos0 == logical_pid_m), 0, chosen)
        chosen = tl.where(valid1 & (pos1 == logical_pid_m), 1, chosen)
        chosen = tl.where(valid2 & (pos2 == logical_pid_m), 2, chosen)
        chosen = tl.where(valid3 & (pos3 == logical_pid_m), 3, chosen)
        chosen = tl.where(valid4 & (pos4 == logical_pid_m), 4, chosen)
        chosen = tl.where(valid5 & (pos5 == logical_pid_m), 5, chosen)
        chosen = tl.where(valid6 & (pos6 == logical_pid_m), 6, chosen)
        chosen = tl.where(valid7 & (pos7 == logical_pid_m), 7, chosen)
    chosen_expert = tl.load(topk_ids_ptr + chosen, mask=chosen < 8, other=-1).to(tl.int32)
    chosen_valid_expert = (chosen_expert >= 0) & (chosen_expert < expert_count)
    if HAS_EXPERT_MAP:
        off_experts = tl.load(
            expert_map_ptr + chosen_expert,
            mask=chosen_valid_expert,
            other=-1,
        ).to(tl.int64)
    else:
        off_experts = chosen_expert.to(tl.int64)

    offsets = tl.arange(0, BLOCK_SIZE_M).to(tl.int64)
    offs_token = tl.where(offsets == 0, chosen.to(tl.int64), 8)
    token_mask = offs_token < 8

    if off_experts == -1:
        _write_zeros_to_output(
            c_ptr,
            stride_cm,
            stride_cn,
            pid_n,
            N,
            offs_token,
            token_mask,
            BLOCK_SIZE_M,
            BLOCK_SIZE_N,
            compute_type,
        )
        return

    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N).to(tl.int64)) % N
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    a_ptrs = a_ptr + (
        offs_token[:, None] // 8 * stride_am + offs_k[None, :] * stride_ak
    )

    if use_int4_w4a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + (offs_k[:, None] // 2) * stride_bk
            + offs_bn[None, :] * stride_bn
        )
        b_shifter = (offs_k[:, None] % 2) * 4
    elif use_int8_w8a16:
        b_ptrs = (
            b_ptr
            + off_experts * stride_be
            + offs_k[:, None] * stride_bk
            + offs_bn[None, :] * stride_bn
        )

    if not has_zp and use_int4_w4a16:
        b_zp_num = 8
    if not has_zp and use_int8_w8a16:
        b_zp_num = 128
    elif has_zp and use_int4_w4a16:
        b_zp_shifter = (offs_bn[None, :] % 2) * 4

    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        if not block_k_diviable:
            k_mask = offs_k[:, None] < K - k * BLOCK_SIZE_K
            k_other = 0.0
        else:
            k_mask = None
            k_other = None

        a = tl.load(
            a_ptrs,
            mask=token_mask[:, None] & (offs_k[None, :] < K - k * BLOCK_SIZE_K),
            other=0.0,
        )
        b = tl.load(b_ptrs)
        if use_int4_w4a16:
            b = (b >> b_shifter) & 0xF

        b_scale_ptrs = (
            b_scale_ptr
            + off_experts * stride_bse
            + offs_bn[None, :] * stride_bsn
            + ((offs_k[:, None] + BLOCK_SIZE_K * k) // group_size) * stride_bsk
        )
        b_scale = tl.load(b_scale_ptrs, mask=k_mask, other=k_other)
        b_scale = b_scale.to(tl.float32)

        if has_zp and use_int4_w4a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + (offs_bn[None, :] // 2) * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = (b_zp >> b_zp_shifter) & 0xF
            b_zp = b_zp.to(tl.float32)
        elif has_zp and use_int8_w8a16:
            offs_k_true = (offs_k[:, None] + BLOCK_SIZE_K * k) // group_size
            b_zp_ptrs = (
                b_zp_ptr
                + off_experts * stride_bze
                + offs_bn[None, :] * stride_bzn
                + offs_k_true * stride_bzk
            )
            b_zp = tl.load(b_zp_ptrs, mask=k_mask, other=k_other)
            b_zp = b_zp.to(tl.float32)

        if has_zp:
            b = ((b.to(tl.float32) - b_zp) * b_scale).to(compute_type)
        else:
            b = ((b.to(tl.float32) - b_zp_num) * b_scale).to(compute_type)
        accumulator = tl.dot(a, b, acc=accumulator)

        a_ptrs += BLOCK_SIZE_K * stride_ak
        if use_int4_w4a16:
            b_ptrs += (BLOCK_SIZE_K // 2) * stride_bk
        else:
            b_ptrs += BLOCK_SIZE_K * stride_bk

    if MUL_ROUTED_WEIGHT:
        moe_weight = tl.load(topk_weights_ptr + offs_token, mask=token_mask, other=0)
        accumulator = accumulator * moe_weight[:, None]

    accumulator = accumulator.to(compute_type)
    offs_cn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    c_ptrs = c_ptr + stride_cm * offs_token[:, None] + stride_cn * offs_cn[None, :]
    c_mask = token_mask[:, None] & (offs_cn[None, :] < N)
    tl.store(c_ptrs, accumulator, mask=c_mask)


def invoke_fused_moe_wna16_triton_kernel_direct_topk_layer_prior(
    *,
    fused_moe_impl: Any,
    topk_ids: torch.Tensor,
    expert_map: torch.Tensor | None,
    prior_rank: torch.Tensor,
    ignore_invalid_experts: bool,
    A: torch.Tensor,
    B: torch.Tensor,
    C: torch.Tensor,
    B_scale: torch.Tensor | None,
    B_zp: torch.Tensor | None,
    topk_weights: torch.Tensor | None,
    mul_routed_weight: bool,
    top_k: int,
    config: dict[str, Any],
    compute_type: tl.dtype,
    use_int8_w8a16: bool,
    use_int4_w4a16: bool,
    block_shape: list[int] | None,
) -> None:
    assert B_scale is not None and B_scale.ndim == 3
    assert B_zp is None or B_zp.ndim == 3
    assert block_shape is not None and block_shape[0] == 0
    if topk_ids.ndim != 2 or int(topk_ids.shape[0]) != 1:
        raise ValueError("direct_topk_layer_prior requires topk_ids shape [1, top_k]")
    route_count = int(topk_ids.numel())
    if int(A.size(0)) * int(top_k) != route_count:
        raise ValueError(
            "direct_topk_layer_prior requires A.size(0) * dispatch top_k "
            f"to match route_count, got {int(A.size(0))} * {int(top_k)} "
            f"!= {route_count}"
        )
    if prior_rank.ndim != 1 or int(prior_rank.numel()) <= 0:
        raise ValueError("direct_topk_layer_prior requires non-empty prior_rank")

    launch_config = config.copy()
    launch_config.update(
        fused_moe_impl.get_moe_wna16_block_config(
            config=launch_config,
            use_moe_wna16_cuda=False,
            num_valid_tokens=route_count,
            size_k=A.size(1),
            size_n=B.size(1),
            num_experts=B.size(1),
            group_size=block_shape[1],
            real_top_k=top_k,
            block_size_m=launch_config["BLOCK_SIZE_M"],
        )
    )
    if route_count == 8 and int(top_k) == 8:
        grid = lambda META: (
            8,
            triton.cdiv(B.size(1), META["BLOCK_SIZE_N"]),
        )
        fused_moe_kernel_gptq_awq_direct_topk8_layer_prior[grid](
            A,
            B,
            C,
            B_scale,
            B_zp,
            topk_weights,
            topk_ids,
            expert_map if expert_map is not None else prior_rank,
            prior_rank,
            B.size(1),
            A.size(1),
            int(prior_rank.numel()),
            A.stride(0),
            A.stride(1),
            B.stride(0),
            B.stride(2),
            B.stride(1),
            C.stride(1),
            C.stride(2),
            B_scale.stride(0),
            B_scale.stride(2),
            B_scale.stride(1),
            B_zp.stride(0) if B_zp is not None else 0,
            B_zp.stride(2) if B_zp is not None else 0,
            B_zp.stride(1) if B_zp is not None else 0,
            block_k_diviable=A.size(1) % launch_config["BLOCK_SIZE_K"] == 0,
            group_size=block_shape[1],
            MUL_ROUTED_WEIGHT=mul_routed_weight,
            compute_type=compute_type,
            has_zp=B_zp is not None,
            use_int4_w4a16=use_int4_w4a16,
            use_int8_w8a16=use_int8_w8a16,
            HAS_EXPERT_MAP=expert_map is not None,
            IGNORE_INVALID_EXPERTS=bool(ignore_invalid_experts),
            IDENTITY_ORDER=False,
            **launch_config,
        )
        return

    route_count_p2 = 1 << (route_count - 1).bit_length()
    grid = lambda META: (
        route_count * triton.cdiv(B.size(1), META["BLOCK_SIZE_N"]),
    )
    fused_moe_kernel_gptq_awq_direct_topk_layer_prior[grid](
        A,
        B,
        C,
        B_scale,
        B_zp,
        topk_weights,
        topk_ids,
        expert_map if expert_map is not None else prior_rank,
        prior_rank,
        B.size(1),
        A.size(1),
        int(prior_rank.numel()),
        route_count,
        A.stride(0),
        A.stride(1),
        B.stride(0),
        B.stride(2),
        B.stride(1),
        C.stride(1),
        C.stride(2),
        B_scale.stride(0),
        B_scale.stride(2),
        B_scale.stride(1),
        B_zp.stride(0) if B_zp is not None else 0,
        B_zp.stride(2) if B_zp is not None else 0,
        B_zp.stride(1) if B_zp is not None else 0,
        block_k_diviable=A.size(1) % launch_config["BLOCK_SIZE_K"] == 0,
        group_size=block_shape[1],
        MUL_ROUTED_WEIGHT=mul_routed_weight,
        dispatch_top_k=top_k,
        route_count_p2=route_count_p2,
        compute_type=compute_type,
        has_zp=B_zp is not None,
        use_int4_w4a16=use_int4_w4a16,
        use_int8_w8a16=use_int8_w8a16,
        HAS_EXPERT_MAP=expert_map is not None,
        IGNORE_INVALID_EXPERTS=bool(ignore_invalid_experts),
        IDENTITY_ORDER=False,
        **launch_config,
    )


def invoke_fused_moe_wna16_triton_kernel_direct_topk_identity(
    *,
    fused_moe_impl: Any,
    topk_ids: torch.Tensor,
    expert_map: torch.Tensor | None,
    expert_count: int,
    ignore_invalid_experts: bool,
    A: torch.Tensor,
    B: torch.Tensor,
    C: torch.Tensor,
    B_scale: torch.Tensor | None,
    B_zp: torch.Tensor | None,
    topk_weights: torch.Tensor | None,
    mul_routed_weight: bool,
    top_k: int,
    config: dict[str, Any],
    compute_type: tl.dtype,
    use_int8_w8a16: bool,
    use_int4_w4a16: bool,
    block_shape: list[int] | None,
) -> None:
    assert B_scale is not None and B_scale.ndim == 3
    assert B_zp is None or B_zp.ndim == 3
    assert block_shape is not None and block_shape[0] == 0
    if topk_ids.ndim != 2 or int(topk_ids.shape[0]) != 1:
        raise ValueError("direct_topk_identity requires topk_ids shape [1, top_k]")
    route_count = int(topk_ids.numel())
    if route_count != 8 or int(top_k) not in {1, 8}:
        raise ValueError(
            "direct_topk_identity currently requires route_count=8 and top_k in {1, 8}, "
            f"got route_count={route_count}, top_k={int(top_k)}"
        )
    if int(A.size(0)) * int(top_k) != route_count:
        raise ValueError(
            "direct_topk_identity requires A.size(0) * dispatch top_k "
            f"to match route_count, got {int(A.size(0))} * {int(top_k)} "
            f"!= {route_count}"
        )
    if int(expert_count) <= 0:
        raise ValueError("direct_topk_identity requires positive expert_count")

    launch_config = config.copy()
    launch_config.update(
        fused_moe_impl.get_moe_wna16_block_config(
            config=launch_config,
            use_moe_wna16_cuda=False,
            num_valid_tokens=route_count,
            size_k=A.size(1),
            size_n=B.size(1),
            num_experts=B.size(1),
            group_size=block_shape[1],
            real_top_k=top_k,
            block_size_m=launch_config["BLOCK_SIZE_M"],
        )
    )
    if int(top_k) == 8:
        grid = lambda META: (
            8,
            triton.cdiv(B.size(1), META["BLOCK_SIZE_N"]),
        )
        fused_moe_kernel_gptq_awq_direct_topk8_layer_prior[grid](
            A,
            B,
            C,
            B_scale,
            B_zp,
            topk_weights,
            topk_ids,
            expert_map if expert_map is not None else topk_ids,
            topk_ids,
            B.size(1),
            A.size(1),
            int(expert_count),
            A.stride(0),
            A.stride(1),
            B.stride(0),
            B.stride(2),
            B.stride(1),
            C.stride(1),
            C.stride(2),
            B_scale.stride(0),
            B_scale.stride(2),
            B_scale.stride(1),
            B_zp.stride(0) if B_zp is not None else 0,
            B_zp.stride(2) if B_zp is not None else 0,
            B_zp.stride(1) if B_zp is not None else 0,
            block_k_diviable=A.size(1) % launch_config["BLOCK_SIZE_K"] == 0,
            group_size=block_shape[1],
            MUL_ROUTED_WEIGHT=mul_routed_weight,
            compute_type=compute_type,
            has_zp=B_zp is not None,
            use_int4_w4a16=use_int4_w4a16,
            use_int8_w8a16=use_int8_w8a16,
            HAS_EXPERT_MAP=expert_map is not None,
            IGNORE_INVALID_EXPERTS=bool(ignore_invalid_experts),
            IDENTITY_ORDER=True,
            **launch_config,
        )
        return

    route_count_p2 = 1 << (route_count - 1).bit_length()
    grid = lambda META: (
        route_count * triton.cdiv(B.size(1), META["BLOCK_SIZE_N"]),
    )
    fused_moe_kernel_gptq_awq_direct_topk_layer_prior[grid](
        A,
        B,
        C,
        B_scale,
        B_zp,
        topk_weights,
        topk_ids,
        expert_map if expert_map is not None else topk_ids,
        topk_ids,
        B.size(1),
        A.size(1),
        int(expert_count),
        route_count,
        A.stride(0),
        A.stride(1),
        B.stride(0),
        B.stride(2),
        B.stride(1),
        C.stride(1),
        C.stride(2),
        B_scale.stride(0),
        B_scale.stride(2),
        B_scale.stride(1),
        B_zp.stride(0) if B_zp is not None else 0,
        B_zp.stride(2) if B_zp is not None else 0,
        B_zp.stride(1) if B_zp is not None else 0,
        block_k_diviable=A.size(1) % launch_config["BLOCK_SIZE_K"] == 0,
        group_size=block_shape[1],
        MUL_ROUTED_WEIGHT=mul_routed_weight,
        dispatch_top_k=top_k,
        route_count_p2=route_count_p2,
        compute_type=compute_type,
        has_zp=B_zp is not None,
        use_int4_w4a16=use_int4_w4a16,
        use_int8_w8a16=use_int8_w8a16,
        HAS_EXPERT_MAP=expert_map is not None,
        IGNORE_INVALID_EXPERTS=bool(ignore_invalid_experts),
        IDENTITY_ORDER=True,
        **launch_config,
    )


def invoke_fused_moe_wna16_triton_kernel_indirect(
    *,
    fused_moe_impl: Any,
    indirect_mode: str,
    source_block_ids: torch.Tensor | None,
    group_order: torch.Tensor | None,
    group_offsets: torch.Tensor | None,
    group_source_starts: torch.Tensor | None,
    max_groups: int,
    source_block_ids_packed: bool = False,
    A: torch.Tensor,
    B: torch.Tensor,
    C: torch.Tensor,
    B_scale: torch.Tensor | None,
    B_zp: torch.Tensor | None,
    topk_weights: torch.Tensor | None,
    sorted_token_ids: torch.Tensor,
    expert_ids: torch.Tensor,
    num_tokens_post_padded: torch.Tensor,
    mul_routed_weight: bool,
    top_k: int,
    config: dict[str, Any],
    compute_type: tl.dtype,
    use_int8_w8a16: bool,
    use_int4_w4a16: bool,
    block_shape: list[int] | None,
) -> None:
    assert B_scale is not None and B_scale.ndim == 3
    assert B_zp is None or B_zp.ndim == 3
    assert block_shape is not None and block_shape[0] == 0
    normalized_mode = str(indirect_mode).strip().lower()
    if normalized_mode == "source_block_ids":
        if source_block_ids is None:
            raise ValueError("source_block_ids mode requires source_block_ids")
        group_order = source_block_ids
        group_offsets = source_block_ids
        group_source_starts = source_block_ids
        indirect_flag = 1
        num_groups = 0
    elif normalized_mode in {"identity", "gpu_assignment_identity"}:
        source_block_ids = expert_ids
        group_order = expert_ids
        group_offsets = expert_ids
        group_source_starts = expert_ids
        indirect_flag = 0
        num_groups = 0
    elif normalized_mode == "group_plan":
        if group_order is None or group_offsets is None or group_source_starts is None:
            raise ValueError("group_plan mode requires group_order/offsets/starts")
        source_block_ids = group_order
        indirect_flag = 2
        num_groups = int(group_order.numel())
    else:
        raise ValueError(f"unsupported indirect WNA16 mode: {indirect_mode}")

    M = A.size(0)
    num_tokens = M * top_k
    EM = sorted_token_ids.size(0)
    if A.size(0) < config["BLOCK_SIZE_M"]:
        EM = min(sorted_token_ids.size(0), A.size(0) * top_k * config["BLOCK_SIZE_M"])
    # source_block_ids is generated for active padded blocks. The launch EM can
    # include an extra tail block, but the kernel returns before indirect lookup
    # when logical_pid_m * BLOCK_SIZE_M >= num_tokens_post_padded.
    if indirect_flag == 1 and int(source_block_ids.numel()) <= 0:
        raise ValueError("source_block_ids mode requires a non-empty mapping")
    if indirect_flag == 2:
        if int(max_groups) < int(num_groups):
            raise ValueError("MAX_GROUPS must be >= group_order length")
        if int(group_offsets.numel()) != int(num_groups) + 1:
            raise ValueError("group_offsets length must be group_count + 1")
        if int(group_source_starts.numel()) != int(num_groups):
            raise ValueError("group_source_starts length must match group_count")
    grid = lambda META: (
        triton.cdiv(EM, META["BLOCK_SIZE_M"])
        * triton.cdiv(B.size(1), META["BLOCK_SIZE_N"]),
    )
    launch_config = config.copy()
    launch_config.update(
        fused_moe_impl.get_moe_wna16_block_config(
            config=launch_config,
            use_moe_wna16_cuda=False,
            num_valid_tokens=num_tokens,
            size_k=A.size(1),
            size_n=B.size(1),
            num_experts=B.size(1),
            group_size=block_shape[1],
            real_top_k=top_k,
            block_size_m=launch_config["BLOCK_SIZE_M"],
        )
    )

    fused_moe_kernel_gptq_awq_indirect[grid](
        A,
        B,
        C,
        B_scale,
        B_zp,
        topk_weights,
        sorted_token_ids,
        expert_ids,
        num_tokens_post_padded,
        source_block_ids,
        group_order,
        group_offsets,
        group_source_starts,
        source_block_ids,
        source_block_ids,
        source_block_ids,
        source_block_ids,
        B.size(1),
        A.size(1),
        EM,
        num_tokens,
        num_groups,
        int(source_block_ids.numel()) if indirect_flag == 1 else 0,
        0,
        A.stride(0),
        A.stride(1),
        B.stride(0),
        B.stride(2),
        B.stride(1),
        C.stride(1),
        C.stride(2),
        B_scale.stride(0),
        B_scale.stride(2),
        B_scale.stride(1),
        B_zp.stride(0) if B_zp is not None else 0,
        B_zp.stride(2) if B_zp is not None else 0,
        B_zp.stride(1) if B_zp is not None else 0,
        block_k_diviable=A.size(1) % launch_config["BLOCK_SIZE_K"] == 0,
        group_size=block_shape[1],
        MUL_ROUTED_WEIGHT=mul_routed_weight,
        top_k=top_k,
        compute_type=compute_type,
        has_zp=B_zp is not None,
        use_int4_w4a16=use_int4_w4a16,
        use_int8_w8a16=use_int8_w8a16,
        INDIRECT_MODE=indirect_flag,
        SOURCE_BLOCK_IDS_PACKED=bool(source_block_ids_packed),
        MAX_GROUPS=max(1, int(max_groups)),
        TYPED_SLOT_MODE=False,
        **launch_config,
    )


def invoke_fused_moe_wna16_triton_kernel_gpu_assignment_identity(
    *,
    fused_moe_impl: Any,
    A: torch.Tensor,
    B: torch.Tensor,
    C: torch.Tensor,
    B_scale: torch.Tensor | None,
    B_zp: torch.Tensor | None,
    topk_weights: torch.Tensor | None,
    sorted_token_ids: torch.Tensor,
    expert_ids: torch.Tensor,
    num_tokens_post_padded: torch.Tensor,
    mul_routed_weight: bool,
    top_k: int,
    config: dict[str, Any],
    compute_type: tl.dtype,
    use_int8_w8a16: bool,
    use_int4_w4a16: bool,
    block_shape: list[int] | None,
) -> None:
    """Run the future WNA16 path by consuming GPU-side assignment tensors.

    This canary does not require descriptor/address prepared-table columns.
    It launches the independent WNA16/Triton consumer with identity block order,
    so the kernel reads ``num_tokens_post_padded`` and ``expert_ids`` directly
    from the same GPU tensors used by the current vLLM launch.
    """

    invoke_fused_moe_wna16_triton_kernel_indirect(
        fused_moe_impl=fused_moe_impl,
        indirect_mode="gpu_assignment_identity",
        source_block_ids=None,
        group_order=None,
        group_offsets=None,
        group_source_starts=None,
        max_groups=1,
        source_block_ids_packed=False,
        A=A,
        B=B,
        C=C,
        B_scale=B_scale,
        B_zp=B_zp,
        topk_weights=topk_weights,
        sorted_token_ids=sorted_token_ids,
        expert_ids=expert_ids,
        num_tokens_post_padded=num_tokens_post_padded,
        mul_routed_weight=mul_routed_weight,
        top_k=top_k,
        config=config,
        compute_type=compute_type,
        use_int8_w8a16=use_int8_w8a16,
        use_int4_w4a16=use_int4_w4a16,
        block_shape=block_shape,
    )


def invoke_fused_moe_wna16_triton_kernel_future_typed_slot_identity(
    *,
    fused_moe_impl: Any,
    typed_slot_descriptor_ptr: torch.Tensor,
    typed_slot_packed_weight_descriptor: torch.Tensor,
    typed_slot_scale_metadata_handle: torch.Tensor,
    typed_slot_aux_metadata_handle: torch.Tensor,
    A: torch.Tensor,
    B: torch.Tensor,
    C: torch.Tensor,
    B_scale: torch.Tensor | None,
    B_zp: torch.Tensor | None,
    topk_weights: torch.Tensor | None,
    sorted_token_ids: torch.Tensor,
    expert_ids: torch.Tensor,
    num_tokens_post_padded: torch.Tensor,
    mul_routed_weight: bool,
    top_k: int,
    config: dict[str, Any],
    compute_type: tl.dtype,
    use_int8_w8a16: bool,
    use_int4_w4a16: bool,
    block_shape: list[int] | None,
) -> None:
    """Run the WNA16 compute kernel with an independent typed-slot ABI.

    The typed-slot table is consumed as a separate future-kernel argument slot.
    It is deliberately not reinterpreted as the current WNA16 B/B_scale/B_zp
    launch arguments; those stay on the original path for this canary variant.
    """

    assert B_scale is not None and B_scale.ndim == 3
    assert B_zp is None or B_zp.ndim == 3
    assert block_shape is not None and block_shape[0] == 0
    typed_tensors = (
        typed_slot_descriptor_ptr,
        typed_slot_packed_weight_descriptor,
        typed_slot_scale_metadata_handle,
        typed_slot_aux_metadata_handle,
    )
    typed_slot_row_count = int(typed_slot_descriptor_ptr.numel())
    if typed_slot_row_count <= 0:
        raise ValueError("future typed-slot WNA16 variant requires non-empty typed slots")
    for tensor in typed_tensors:
        if tensor is None or not tensor.is_cuda:
            raise ValueError("future typed-slot WNA16 variant requires CUDA/HIP tensors")
        if int(tensor.numel()) != typed_slot_row_count:
            raise ValueError("future typed-slot WNA16 variant requires equal column lengths")
        if tensor.dtype not in {torch.int64, torch.uint64}:
            raise ValueError("future typed-slot WNA16 variant requires int64/uint64 columns")

    M = A.size(0)
    num_tokens = M * top_k
    EM = sorted_token_ids.size(0)
    if A.size(0) < config["BLOCK_SIZE_M"]:
        EM = min(sorted_token_ids.size(0), A.size(0) * top_k * config["BLOCK_SIZE_M"])
    grid = lambda META: (
        triton.cdiv(EM, META["BLOCK_SIZE_M"])
        * triton.cdiv(B.size(1), META["BLOCK_SIZE_N"]),
    )
    launch_config = config.copy()
    launch_config.update(
        fused_moe_impl.get_moe_wna16_block_config(
            config=launch_config,
            use_moe_wna16_cuda=False,
            num_valid_tokens=num_tokens,
            size_k=A.size(1),
            size_n=B.size(1),
            num_experts=B.size(1),
            group_size=block_shape[1],
            real_top_k=top_k,
            block_size_m=launch_config["BLOCK_SIZE_M"],
        )
    )

    fused_moe_kernel_gptq_awq_indirect[grid](
        A,
        B,
        C,
        B_scale,
        B_zp,
        topk_weights,
        sorted_token_ids,
        expert_ids,
        num_tokens_post_padded,
        typed_slot_descriptor_ptr,
        typed_slot_descriptor_ptr,
        typed_slot_descriptor_ptr,
        typed_slot_descriptor_ptr,
        typed_slot_descriptor_ptr,
        typed_slot_packed_weight_descriptor,
        typed_slot_scale_metadata_handle,
        typed_slot_aux_metadata_handle,
        B.size(1),
        A.size(1),
        EM,
        num_tokens,
        0,
        0,
        typed_slot_row_count,
        A.stride(0),
        A.stride(1),
        B.stride(0),
        B.stride(2),
        B.stride(1),
        C.stride(1),
        C.stride(2),
        B_scale.stride(0),
        B_scale.stride(2),
        B_scale.stride(1),
        B_zp.stride(0) if B_zp is not None else 0,
        B_zp.stride(2) if B_zp is not None else 0,
        B_zp.stride(1) if B_zp is not None else 0,
        block_k_diviable=A.size(1) % launch_config["BLOCK_SIZE_K"] == 0,
        group_size=block_shape[1],
        MUL_ROUTED_WEIGHT=mul_routed_weight,
        top_k=top_k,
        compute_type=compute_type,
        has_zp=B_zp is not None,
        use_int4_w4a16=use_int4_w4a16,
        use_int8_w8a16=use_int8_w8a16,
        INDIRECT_MODE=0,
        SOURCE_BLOCK_IDS_PACKED=False,
        MAX_GROUPS=1,
        TYPED_SLOT_MODE=True,
        **launch_config,
    )
