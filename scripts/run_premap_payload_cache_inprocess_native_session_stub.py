#!/usr/bin/env python3
"""Run the in-process native producer session canary.

This canary is the next boundary after the whole-stream in-process native
producer.  It creates a persistent native session that owns transition state on
device, then feeds one current-expert row pointer per update.  This is closer to
an online vLLM prelaunch producer boundary than replaying a synthetic stream in
one native call, but it is still not a PyTorch graph-visible op and it does not
move payloads or pass current WNA16 kernel arguments.
"""

from __future__ import annotations

import argparse
import ctypes
import json
from pathlib import Path
import struct
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import run_premap_payload_cache_inprocess_native_producer_stub as base

MAX_NATIVE_STREAM_COUNT = 65536
PACKET_STREAM_MAGIC = 0x5054434D
PACKET_STREAM_VERSION = 2


class InprocessProducerSessionUpdateResult(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_uint32),
        ("ok", ctypes.c_uint32),
        ("passed", ctypes.c_uint32),
        ("native_returncode", ctypes.c_uint32),
        ("session_handle_nonzero", ctypes.c_uint32),
        ("current_expert_ptr_nonzero", ctypes.c_uint32),
        ("layer_id", ctypes.c_uint32),
        ("layers", ctypes.c_uint32),
        ("experts_per_layer", ctypes.c_uint32),
        ("transition_topk_count", ctypes.c_uint32),
        ("previous_count_before", ctypes.c_uint32),
        ("current_count", ctypes.c_uint32),
        ("packet_count", ctypes.c_uint32),
        ("previous_nonempty_packet_count", ctypes.c_uint32),
        ("current_nonempty_packet_count", ctypes.c_uint32),
        ("issue_candidate_count", ctypes.c_uint32),
        ("expected_issue_candidate_count", ctypes.c_uint32),
        ("issue_candidate_hash", ctypes.c_uint64),
        ("first_issue_expert", ctypes.c_int32),
        ("last_issue_expert", ctypes.c_int32),
        ("ready", ctypes.c_uint32),
        ("error_count", ctypes.c_uint32),
        ("gpu_elapsed_ms", ctypes.c_float),
        ("persistent_state_on_device", ctypes.c_uint32),
        ("issue_generation_on_device", ctypes.c_uint32),
        ("prelaunch_callable_native_session", ctypes.c_uint32),
        ("graph_visible", ctypes.c_uint32),
        ("native_stub_invoked", ctypes.c_uint32),
        ("vectorized_copy_requested", ctypes.c_uint32),
        ("vectorized_copy_used", ctypes.c_uint32),
        ("payload_bytes", ctypes.c_uint32),
        ("payload_transfer_enabled", ctypes.c_uint32),
        ("payload_deref_allowed", ctypes.c_uint32),
        ("ready_credit", ctypes.c_uint32),
        ("ready_before_demand_credit", ctypes.c_uint32),
        ("real_ready_credit_granted", ctypes.c_uint32),
        ("passed_to_kernel", ctypes.c_uint32),
        ("changes_kernel_launch_args", ctypes.c_uint32),
        ("kernel_arg_pass", ctypes.c_uint32),
        ("kernel_arg_pass_allowed", ctypes.c_uint32),
        ("current_wna16_arg_compatible", ctypes.c_uint32),
        ("uses_current_wna16_args", ctypes.c_uint32),
        ("passes_current_wna16_args", ctypes.c_uint32),
        ("measures_tpot", ctypes.c_uint32),
        ("measures_vllm_latency", ctypes.c_uint32),
    ]


def _validate_count(value: int, name: str, *, allow_zero: bool = False) -> int:
    parsed = int(value)
    if parsed < 0 or (parsed == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {qualifier}")
    if parsed > MAX_NATIVE_STREAM_COUNT:
        raise ValueError(
            f"{name} exceeds native session canary safety bound "
            f"{MAX_NATIVE_STREAM_COUNT}"
        )
    return parsed


def _bool_flag(value: int) -> bool:
    return bool(int(value))


def _load_library(args: argparse.Namespace) -> ctypes.CDLL:
    library = base.build(offload_arch=args.offload_arch, force=args.force_build)
    lib = ctypes.CDLL(str(library))

    create = lib.premap_payload_cache_inprocess_producer_session_create_v1
    create.argtypes = [
        ctypes.c_int,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint64),
    ]
    create.restype = ctypes.c_int

    update = lib.premap_payload_cache_inprocess_producer_session_update_v1
    update.argtypes = [
        ctypes.c_uint64,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(InprocessProducerSessionUpdateResult),
    ]
    update.restype = ctypes.c_int

    update_count_ptr = (
        lib.premap_payload_cache_inprocess_producer_session_update_count_ptr_v1
    )
    update_count_ptr.argtypes = [
        ctypes.c_uint64,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(InprocessProducerSessionUpdateResult),
    ]
    update_count_ptr.restype = ctypes.c_int

    update_generated = (
        lib.premap_payload_cache_inprocess_producer_session_update_generated_v1
    )
    update_generated.argtypes = [
        ctypes.c_uint64,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(InprocessProducerSessionUpdateResult),
    ]
    update_generated.restype = ctypes.c_int

    restore_state = lib.premap_payload_cache_inprocess_producer_session_restore_state_v1
    restore_state.argtypes = [
        ctypes.c_uint64,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    restore_state.restype = ctypes.c_int

    destroy = lib.premap_payload_cache_inprocess_producer_session_destroy_v1
    destroy.argtypes = [ctypes.c_uint64]
    destroy.restype = ctypes.c_int
    return lib


def _make_current_stream(args: argparse.Namespace, *, steps: int, layers: int, experts: int):
    import torch

    device = torch.device(f"cuda:{int(args.device)}")
    expert_ids = torch.arange(experts, device=device, dtype=torch.int32)
    step_ids = torch.arange(steps, device=device, dtype=torch.int32).view(steps, 1, 1)
    layer_ids = torch.arange(layers, device=device, dtype=torch.int32).view(1, layers, 1)
    stream = (
        expert_ids.view(1, 1, experts)
        + step_ids * int(args.step_shift)
        + layer_ids * int(args.layer_stride)
    ) % int(args.max_num_experts)
    return stream.contiguous()


def _load_packet_stream(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    header_size = struct.calcsize("<8I")
    if len(raw) < header_size:
        raise ValueError("packet stream header is truncated")
    (
        magic,
        version,
        packet_count,
        layer_count,
        max_experts_per_packet,
        transition_topk_count,
        max_num_experts,
        reserved,
    ) = struct.unpack_from("<8I", raw, 0)
    if magic != PACKET_STREAM_MAGIC:
        raise ValueError("packet stream magic mismatch")
    if version != PACKET_STREAM_VERSION:
        raise ValueError("packet stream version mismatch")
    if reserved != 0:
        raise ValueError("packet stream reserved header field must be zero")
    packet_count = _validate_count(packet_count, "packet-stream packet-count")
    layer_count = _validate_count(layer_count, "packet-stream layer-count")
    max_experts_per_packet = _validate_count(
        max_experts_per_packet,
        "packet-stream max-experts-per-packet",
    )
    _validate_count(max_num_experts, "packet-stream max-num-experts")
    _validate_count(
        transition_topk_count,
        "packet-stream transition-topk-count",
        allow_zero=True,
    )
    offset = header_size

    def take_u32(count: int, name: str) -> tuple[int, ...]:
        nonlocal offset
        byte_count = struct.calcsize(f"<{count}I")
        if offset + byte_count > len(raw):
            raise ValueError(f"packet stream {name} section is truncated")
        values = struct.unpack_from(f"<{count}I", raw, offset)
        offset += byte_count
        return values

    def take_i32(count: int, name: str) -> tuple[int, ...]:
        nonlocal offset
        byte_count = struct.calcsize(f"<{count}i")
        if offset + byte_count > len(raw):
            raise ValueError(f"packet stream {name} section is truncated")
        values = struct.unpack_from(f"<{count}i", raw, offset)
        offset += byte_count
        return values

    layer_ids = take_u32(packet_count, "layer_ids")
    current_counts = take_u32(packet_count, "current_counts")
    previous_counts = take_u32(packet_count, "previous_counts")
    issue_counts = take_u32(packet_count, "issue_counts")
    state_override_flags = take_u32(packet_count, "state_override_flags")
    flat_count = packet_count * max_experts_per_packet
    current_experts = take_i32(flat_count, "current_experts")
    previous_experts = take_i32(flat_count, "previous_experts")
    issue_experts = take_i32(flat_count, "issue_experts")
    if offset != len(raw):
        raise ValueError("packet stream has trailing bytes")
    for index, layer_id in enumerate(layer_ids):
        if layer_id >= layer_count:
            raise ValueError(f"packet {index} layer id out of range")
    fnv_offset = 0xCBF29CE484222325
    fnv_prime = 0x100000001B3

    def mix(value: int, item: int) -> int:
        value ^= int(item) & 0xFFFFFFFF
        value = (value * fnv_prime) & 0xFFFFFFFFFFFFFFFF
        return value

    layer_hashes = [fnv_offset] * layer_count
    carried_previous_by_layer: list[list[int]] = [[] for _ in range(layer_count)]
    expected_issue_hash = fnv_offset
    for index in range(packet_count):
        current_count = int(current_counts[index])
        previous_count = int(previous_counts[index])
        issue_count = int(issue_counts[index])
        layer_id = int(layer_ids[index])
        state_override = int(state_override_flags[index])
        if current_count > max_experts_per_packet:
            raise ValueError(f"packet {index} current count out of range")
        if previous_count > max_experts_per_packet:
            raise ValueError(f"packet {index} previous count out of range")
        if issue_count > max_experts_per_packet:
            raise ValueError(f"packet {index} issue count out of range")
        if state_override > 1:
            raise ValueError(f"packet {index} state override flag out of range")

        row_start = index * max_experts_per_packet
        current_row = list(current_experts[row_start : row_start + current_count])
        previous_row = list(previous_experts[row_start : row_start + previous_count])
        issue_row = list(issue_experts[row_start : row_start + issue_count])
        for key, row in (
            ("current", current_row),
            ("previous", previous_row),
            ("issue", issue_row),
        ):
            for expert_index, expert in enumerate(row):
                if expert < 0 or expert >= max_num_experts:
                    raise ValueError(
                        f"packet {index} {key} expert {expert_index} out of range"
                    )

        expected_carried_previous = carried_previous_by_layer[layer_id]
        if state_override == 0 and previous_row != expected_carried_previous:
            raise ValueError(f"packet {index} previous experts do not match session state")
        if state_override != 0:
            expected_carried_previous = previous_row

        issue_limit = (
            len(expected_carried_previous)
            if transition_topk_count == 0
            else min(len(expected_carried_previous), transition_topk_count)
        )
        expected_issue_row = expected_carried_previous[:issue_limit]
        if issue_count != issue_limit:
            raise ValueError(f"packet {index} issue count mismatch")
        if issue_row != expected_issue_row:
            raise ValueError(f"packet {index} issue experts do not match previous topk")

        local_issue_hash = fnv_offset
        for expert in expected_issue_row:
            local_issue_hash = mix(local_issue_hash, expert)
        local_issue_hash = mix(local_issue_hash, issue_limit)
        layer_hashes[layer_id] = mix(layer_hashes[layer_id], local_issue_hash)
        expected_issue_hash ^= layer_hashes[layer_id]
        expected_issue_hash = (expected_issue_hash * fnv_prime) & 0xFFFFFFFFFFFFFFFF
        carried_previous_by_layer[layer_id] = current_row
    return {
        "packet_count": packet_count,
        "layer_count": layer_count,
        "max_experts_per_packet": max_experts_per_packet,
        "transition_topk_count": transition_topk_count,
        "max_num_experts": max_num_experts,
        "layer_ids": layer_ids,
        "current_counts": current_counts,
        "previous_counts": previous_counts,
        "issue_counts": issue_counts,
        "state_override_flags": state_override_flags,
        "current_experts": current_experts,
        "previous_experts": previous_experts,
        "issue_experts": issue_experts,
        "state_override_count": sum(
            1 for item in state_override_flags if int(item) != 0
        ),
        "expected_previous_nonempty_packet_count": sum(
            1 for item in previous_counts if int(item) > 0
        ),
        "expected_issue_candidate_count": sum(int(item) for item in issue_counts),
        "expected_issue_candidate_hash": f"{expected_issue_hash:016x}",
    }


def _payload_from_updates(
    *,
    args: argparse.Namespace,
    library: Path,
    create_returncode: int,
    destroy_returncode: int,
    handle: int,
    update_results: list[tuple[int, InprocessProducerSessionUpdateResult]],
    restore_returncodes: list[int] | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    restore_returncodes = [] if restore_returncodes is None else restore_returncodes
    if create_returncode != 0 or handle == 0:
        failures.append("session_create_failed")
    if destroy_returncode != 0:
        failures.append("session_destroy_failed")
    if any(int(code) != 0 for code in restore_returncodes):
        failures.append("session_restore_state_failed")
    if not update_results:
        failures.append("session_update_results_empty")

    packet_count = len(update_results)
    native_packet_count = 0
    native_previous_nonempty_count = 0
    native_issue_candidate_count = 0
    error_count = 0
    ready_count = 0
    vectorized_copy_used = False
    gpu_elapsed_ms = 0.0
    first_issue_expert = -1
    last_issue_expert = -1
    issue_hash = 0xCBF29CE484222325
    native_update_returncode_set: list[int] = []
    expected_layer_ids = tuple(getattr(args, "expected_layer_ids", ()))
    expected_current_counts = tuple(getattr(args, "expected_current_counts", ()))
    expected_previous_counts = tuple(getattr(args, "expected_previous_counts", ()))

    for packet_index, (native_returncode, result) in enumerate(update_results):
        native_update_returncode_set.append(int(native_returncode))
        if native_returncode != 0 or not _bool_flag(result.ok):
            failures.append("session_update_failed")
        expected_issue_delta = min(
            int(result.previous_count_before),
            int(args.transition_topk_count)
            if int(args.transition_topk_count) != 0
            else int(args.experts_per_layer),
        )
        native_packet_count += int(result.packet_count)
        native_previous_nonempty_count += int(result.previous_nonempty_packet_count)
        native_issue_candidate_count += int(result.issue_candidate_count)
        if int(result.layers) != int(args.layers):
            failures.append("native_layers_mismatch")
        if int(result.experts_per_layer) != int(args.experts_per_layer):
            failures.append("native_experts_per_layer_mismatch")
        if int(result.transition_topk_count) != int(args.transition_topk_count):
            failures.append("native_transition_topk_count_mismatch")
        if expected_layer_ids:
            if packet_index >= len(expected_layer_ids):
                failures.append("expected_layer_ids_length_mismatch")
            elif int(result.layer_id) != int(expected_layer_ids[packet_index]):
                failures.append("native_layer_id_mismatch")
        if expected_current_counts:
            if packet_index >= len(expected_current_counts):
                failures.append("expected_current_counts_length_mismatch")
            elif int(result.current_count) != int(expected_current_counts[packet_index]):
                failures.append("native_current_count_mismatch")
        if expected_previous_counts:
            if packet_index >= len(expected_previous_counts):
                failures.append("expected_previous_counts_length_mismatch")
            elif int(result.previous_count_before) != int(
                expected_previous_counts[packet_index]
            ):
                failures.append("native_previous_count_before_mismatch")
        if int(result.packet_count) != 1:
            failures.append("native_packet_delta_mismatch")
        if int(result.previous_nonempty_packet_count) != (
            1 if int(result.previous_count_before) > 0 else 0
        ):
            failures.append("native_previous_nonempty_delta_mismatch")
        if int(result.issue_candidate_count) != expected_issue_delta:
            failures.append("native_issue_delta_mismatch")
        if int(result.expected_issue_candidate_count) != expected_issue_delta:
            failures.append("native_expected_issue_delta_mismatch")
        error_count += int(result.error_count)
        ready_count += 1 if _bool_flag(result.ready) else 0
        vectorized_copy_used = vectorized_copy_used or _bool_flag(
            result.vectorized_copy_used
        )
        gpu_elapsed_ms += float(result.gpu_elapsed_ms)
        if first_issue_expert < 0 and int(result.first_issue_expert) >= 0:
            first_issue_expert = int(result.first_issue_expert)
        if int(result.last_issue_expert) >= 0:
            last_issue_expert = int(result.last_issue_expert)
        issue_hash ^= int(result.issue_candidate_hash)
        issue_hash = (issue_hash * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF

        for key, expected in (
            ("payload_bytes", 0),
            ("payload_transfer_enabled", 0),
            ("payload_deref_allowed", 0),
            ("ready_credit", 0),
            ("ready_before_demand_credit", 0),
            ("real_ready_credit_granted", 0),
            ("passed_to_kernel", 0),
            ("changes_kernel_launch_args", 0),
            ("kernel_arg_pass", 0),
            ("kernel_arg_pass_allowed", 0),
            ("current_wna16_arg_compatible", 0),
            ("uses_current_wna16_args", 0),
            ("passes_current_wna16_args", 0),
            ("measures_tpot", 0),
            ("measures_vllm_latency", 0),
        ):
            if int(getattr(result, key)) != expected:
                failures.append(f"{key}_unexpectedly_enabled")

    expected_previous_nonempty = int(
        getattr(
            args,
            "expected_previous_nonempty_packet_count",
            max(0, int(args.steps) - 1) * int(args.layers),
        )
    )
    issue_per_packet = (
        int(args.experts_per_layer)
        if int(args.transition_topk_count) == 0
        else min(int(args.experts_per_layer), int(args.transition_topk_count))
    )
    expected_issue_candidate_count = int(
        getattr(
            args,
            "expected_issue_candidate_count",
            expected_previous_nonempty * issue_per_packet,
        )
    )
    expected_packet_count = int(
        getattr(args, "expected_packet_count", int(args.steps) * int(args.layers))
    )
    if packet_count != expected_packet_count:
        failures.append("packet_count_mismatch")
    if native_packet_count != packet_count:
        failures.append("native_packet_count_mismatch")
    if native_previous_nonempty_count != expected_previous_nonempty:
        failures.append("previous_nonempty_packet_count_mismatch")
    if native_issue_candidate_count != expected_issue_candidate_count:
        failures.append("issue_candidate_count_mismatch")
    expected_issue_hash = getattr(args, "expected_issue_candidate_hash", None)
    if expected_issue_hash is not None and f"{issue_hash:016x}" != str(
        expected_issue_hash
    ):
        failures.append("issue_candidate_hash_mismatch")
    if error_count != 0:
        failures.append("error_count_nonzero")
    if ready_count != packet_count:
        failures.append("ready_count_mismatch")
    packet_stream_input = bool(getattr(args, "packet_stream_input", False))
    expected_restore_count = int(
        getattr(args, "packet_stream_state_override_count", 0)
    )
    if packet_stream_input and len(restore_returncodes) != expected_restore_count:
        failures.append("packet_stream_state_restore_count_mismatch")
    if (
        not packet_stream_input
        and not bool(args.disable_vectorized_copy)
        and int(args.experts_per_layer) % 4 == 0
        and not vectorized_copy_used
    ):
        failures.append("vectorized_copy_expected_but_not_used")

    ok = not failures
    if packet_stream_input:
        current_expert_ptr_source = "packet_stream_torch_device_tensor"
        current_expert_ptr_source_kind = "online_packet_stream_device_tensor_smoke"
    elif bool(args.native_generated_current):
        current_expert_ptr_source = "native_generated_device_scratch"
        current_expert_ptr_source_kind = "native_scratch_smoke"
    else:
        current_expert_ptr_source = "torch_device_tensor"
        current_expert_ptr_source_kind = "external_torch_device_tensor_smoke"
    external_current_expert_ptr_source = bool(
        not bool(args.native_generated_current)
        and not packet_stream_input
    )
    native_generated_current = bool(args.native_generated_current) and not (
        packet_stream_input
    )
    device_current_count = bool(getattr(args, "device_current_count", False)) and not (
        native_generated_current
    )
    host_scalar_current_count = not native_generated_current and not device_current_count
    if native_generated_current:
        current_count_source_kind = "native_generated_internal_scalar"
    elif device_current_count:
        current_count_source_kind = "device_tensor_int32_bits_as_uint32"
    else:
        current_count_source_kind = "host_scalar_uint32"
    ready_for_external_pointer_smoke = bool(ok and external_current_expert_ptr_source)
    ready_for_vllm_prelaunch_canary = bool(
        ok and current_expert_ptr_source_kind == "vllm_prelaunch_device_tensor"
    )
    return {
        "ok": ok,
        "passed": ok,
        "failures": failures,
        "mode": "payload_cache_producer_state_inprocess_native_session_canary",
        "abi_name": "premap_payload_cache_producer_transition_state_abi_v1",
        "abi_field_count": 9,
        "inprocess_native_op": True,
        "native_runtime": True,
        "native_shared_library": True,
        "native_stub_invoked": True,
        "native_graph_replay": False,
        "prelaunch_callable_native_session": True,
        "packet_stream_input": packet_stream_input,
        "packet_stream_bin": (
            None
            if getattr(args, "packet_stream_bin", None) is None
            else str(args.packet_stream_bin)
        ),
        "packet_stream_state_override_count": int(
            getattr(args, "packet_stream_state_override_count", 0)
        ),
        "packet_stream_state_restore_supported": True,
        "packet_stream_state_restore_count": int(len(restore_returncodes)),
        "packet_stream_state_restore_returncodes": sorted(
            set(int(code) for code in restore_returncodes)
        ),
        "persistent_state_on_device": True,
        "issue_generation_on_device": True,
        "vllm_replay_visible": False,
        "torch_graph_replay_visible": False,
        "graph_visible": False,
        "ready_for_native_session_smoke": ok,
        "ready_for_external_pointer_smoke": ready_for_external_pointer_smoke,
        "ready_for_vllm_prelaunch_canary": ready_for_vllm_prelaunch_canary,
        "create_returncode": int(create_returncode),
        "destroy_returncode": int(destroy_returncode),
        "session_handle_nonzero": bool(handle),
        "native_update_returncodes": sorted(set(native_update_returncode_set)),
        "steps": int(args.steps),
        "layers": int(args.layers),
        "experts_per_layer": int(args.experts_per_layer),
        "transition_topk_count": int(args.transition_topk_count),
        "packet_count": int(packet_count),
        "previous_nonempty_packet_count": int(native_previous_nonempty_count),
        "expected_previous_nonempty_packet_count": int(expected_previous_nonempty),
        "issue_candidate_count": int(native_issue_candidate_count),
        "expected_issue_candidate_count": int(expected_issue_candidate_count),
        "first_issue_expert": int(first_issue_expert),
        "last_issue_expert": int(last_issue_expert),
        "issue_candidate_hash": f"{issue_hash:016x}",
        "expected_issue_candidate_hash": expected_issue_hash,
        "ready_update_count": int(ready_count),
        "error_count": int(error_count),
        "gpu_elapsed_ms": float(gpu_elapsed_ms),
        "vectorized_copy_requested": not bool(args.disable_vectorized_copy),
        "vectorized_copy_used": bool(vectorized_copy_used),
        "current_stream_on_device": True,
        "current_expert_ptr_passed": True,
        "current_expert_ptr_source": current_expert_ptr_source,
        "current_expert_ptr_source_kind": current_expert_ptr_source_kind,
        "current_count_source_kind": current_count_source_kind,
        "current_count_device_ptr_passed": device_current_count,
        "current_count_host_scalar_passed": host_scalar_current_count,
        "external_current_expert_ptr_source": external_current_expert_ptr_source,
        "payload_bytes": 0,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "shared_library": str(library),
        "source": str(base.SRC),
        "abi_header": str(base.ABI_HEADER),
        "offload_arch": str(args.offload_arch),
        "requested_steps": int(args.steps),
        "requested_layers": int(args.layers),
        "requested_experts_per_layer": int(args.experts_per_layer),
        "requested_transition_topk_count": int(args.transition_topk_count),
        "requested_disable_vectorized_copy": bool(args.disable_vectorized_copy),
        "requested_device_current_count": bool(
            getattr(args, "device_current_count", False)
        ),
    }


def run_session_stub(args: argparse.Namespace) -> dict[str, Any]:
    packet_stream = None
    packet_stream_bin = getattr(args, "packet_stream_bin", None)
    if packet_stream_bin is not None:
        packet_stream = _load_packet_stream(Path(packet_stream_bin))
        steps = int(packet_stream["packet_count"])
        layers = int(packet_stream["layer_count"])
        experts_per_layer = int(packet_stream["max_experts_per_packet"])
        transition_topk_count = int(packet_stream["transition_topk_count"])
        max_num_experts = int(packet_stream["max_num_experts"])
        args.steps = steps
        args.layers = layers
        args.experts_per_layer = experts_per_layer
        args.transition_topk_count = transition_topk_count
        args.max_num_experts = max_num_experts
        args.packet_stream_input = True
        args.expected_packet_count = steps
        args.expected_previous_nonempty_packet_count = int(
            packet_stream["expected_previous_nonempty_packet_count"]
        )
        args.expected_issue_candidate_count = int(
            packet_stream["expected_issue_candidate_count"]
        )
        args.packet_stream_state_override_count = int(
            packet_stream["state_override_count"]
        )
        args.expected_issue_candidate_hash = str(
            packet_stream["expected_issue_candidate_hash"]
        )
        args.expected_layer_ids = tuple(packet_stream["layer_ids"])
        args.expected_current_counts = tuple(packet_stream["current_counts"])
        args.expected_previous_counts = tuple(packet_stream["previous_counts"])
    else:
        steps = _validate_count(args.steps, "steps")
        layers = _validate_count(args.layers, "layers")
        experts_per_layer = _validate_count(
            args.experts_per_layer,
            "experts-per-layer",
        )
        transition_topk_count = _validate_count(
            args.transition_topk_count,
            "transition-topk-count",
            allow_zero=True,
        )
        _validate_count(args.max_num_experts, "max-num-experts")
        args.packet_stream_input = False
    _validate_count(args.step_shift, "step-shift", allow_zero=True)
    _validate_count(args.layer_stride, "layer-stride", allow_zero=True)
    library = base.build(offload_arch=args.offload_arch, force=args.force_build)
    lib = _load_library(args)
    create = lib.premap_payload_cache_inprocess_producer_session_create_v1
    update = lib.premap_payload_cache_inprocess_producer_session_update_v1
    update_count_ptr = (
        lib.premap_payload_cache_inprocess_producer_session_update_count_ptr_v1
    )
    update_generated = (
        lib.premap_payload_cache_inprocess_producer_session_update_generated_v1
    )
    restore_state = lib.premap_payload_cache_inprocess_producer_session_restore_state_v1
    destroy = lib.premap_payload_cache_inprocess_producer_session_destroy_v1

    handle = ctypes.c_uint64(0)
    create_returncode = int(
        create(
            int(args.device),
            int(layers),
            int(experts_per_layer),
            int(transition_topk_count),
            ctypes.byref(handle),
        )
    )
    update_results: list[tuple[int, InprocessProducerSessionUpdateResult]] = []
    restore_returncodes: list[int] = []
    if create_returncode == 0 and int(handle.value) != 0:
        current_stream = None
        previous_stream = None
        current_count_stream = None
        if packet_stream is not None:
            import torch

            device = torch.device(f"cuda:{int(args.device)}")
            current_stream = torch.tensor(
                packet_stream["current_experts"],
                device=device,
                dtype=torch.int32,
            ).view(steps, experts_per_layer)
            if bool(args.device_current_count):
                current_count_stream = torch.tensor(
                    packet_stream["current_counts"],
                    device=device,
                    dtype=torch.int32,
                ).view(steps)
            previous_stream = torch.tensor(
                packet_stream["previous_experts"],
                device=device,
                dtype=torch.int32,
            ).view(steps, experts_per_layer)
        elif not args.native_generated_current:
            current_stream = _make_current_stream(
                args,
                steps=steps,
                layers=layers,
                experts=experts_per_layer,
            )
            if bool(args.device_current_count):
                import torch

                device = torch.device(f"cuda:{int(args.device)}")
                current_count_stream = torch.full(
                    (steps, layers),
                    int(experts_per_layer),
                    device=device,
                    dtype=torch.int32,
                )
        for step in range(steps):
            layer_iterable = (
                [int(packet_stream["layer_ids"][step])]
                if packet_stream is not None
                else range(layers)
            )
            for layer in layer_iterable:
                result = InprocessProducerSessionUpdateResult()
                if packet_stream is not None:
                    assert current_stream is not None
                    assert previous_stream is not None
                    if int(packet_stream["state_override_flags"][step]) != 0:
                        previous_row = previous_stream[step]
                        restore_returncode = int(
                            restore_state(
                                int(handle.value),
                                int(layer),
                                ctypes.c_void_p(int(previous_row.data_ptr())),
                                int(packet_stream["previous_counts"][step]),
                            )
                        )
                        restore_returncodes.append(restore_returncode)
                    row = current_stream[step]
                    if bool(args.device_current_count):
                        assert current_count_stream is not None
                        count_value = current_count_stream[step : step + 1]
                        native_returncode = int(
                            update_count_ptr(
                                int(handle.value),
                                int(layer),
                                ctypes.c_void_p(int(row.data_ptr())),
                                ctypes.c_void_p(int(count_value.data_ptr())),
                                0 if args.disable_vectorized_copy else 1,
                                ctypes.byref(result),
                            )
                        )
                    else:
                        native_returncode = int(
                            update(
                                int(handle.value),
                                int(layer),
                                ctypes.c_void_p(int(row.data_ptr())),
                                int(packet_stream["current_counts"][step]),
                                0 if args.disable_vectorized_copy else 1,
                                ctypes.byref(result),
                            )
                        )
                elif args.native_generated_current:
                    native_returncode = int(
                        update_generated(
                            int(handle.value),
                            int(layer),
                            int(step),
                            int(args.step_shift),
                            int(args.layer_stride),
                            int(args.max_num_experts),
                            0 if args.disable_vectorized_copy else 1,
                            ctypes.byref(result),
                        )
                    )
                else:
                    assert current_stream is not None
                    row = current_stream[step, layer]
                    if bool(args.device_current_count):
                        assert current_count_stream is not None
                        count_value = current_count_stream[step, layer : layer + 1]
                        native_returncode = int(
                            update_count_ptr(
                                int(handle.value),
                                int(layer),
                                ctypes.c_void_p(int(row.data_ptr())),
                                ctypes.c_void_p(int(count_value.data_ptr())),
                                0 if args.disable_vectorized_copy else 1,
                                ctypes.byref(result),
                            )
                        )
                    else:
                        native_returncode = int(
                            update(
                                int(handle.value),
                                int(layer),
                                ctypes.c_void_p(int(row.data_ptr())),
                                int(experts_per_layer),
                                0 if args.disable_vectorized_copy else 1,
                                ctypes.byref(result),
                            )
                        )
                update_results.append((native_returncode, result))
    destroy_returncode = 0
    if int(handle.value) != 0:
        destroy_returncode = int(destroy(int(handle.value)))
    return _payload_from_updates(
        args=args,
        library=library,
        create_returncode=create_returncode,
        destroy_returncode=destroy_returncode,
        handle=int(handle.value),
        update_results=update_results,
        restore_returncodes=restore_returncodes,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--layers", type=int, default=40)
    parser.add_argument("--experts-per-layer", type=int, default=8)
    parser.add_argument("--transition-topk-count", type=int, default=8)
    parser.add_argument("--max-num-experts", type=int, default=256)
    parser.add_argument("--step-shift", type=int, default=1)
    parser.add_argument("--layer-stride", type=int, default=17)
    parser.add_argument("--disable-vectorized-copy", action="store_true")
    parser.add_argument(
        "--device-current-count",
        action="store_true",
        help=(
            "Pass current_count as a device uint32 pointer to the native "
            "session update ABI. The runner materializes the count as an int32 "
            "device tensor with identical positive-count bits. This exercises "
            "the future vLLM prelaunch path where the native producer should "
            "not require a host scalar count."
        ),
    )
    parser.add_argument(
        "--packet-stream-bin",
        type=Path,
        help=(
            "Materialized packet-stream binary from the online packet export "
            "manifest. The session bridge consumes its current-expert rows as "
            "device tensors, restores previous-state rows when the stream "
            "marks a state override, and lets native transition state generate "
            "issue candidates."
        ),
    )
    parser.add_argument(
        "--native-generated-current",
        action="store_true",
        help=(
            "Generate the current expert row inside the native library instead "
            "of requiring a torch-visible device tensor pointer. This still "
            "uses the session_update_v1 pointer ABI internally, but it is a "
            "native smoke path rather than a vLLM prelaunch pointer source."
        ),
    )
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT
        / "outputs"
        / "reports"
        / "premap_kernel_consumer"
        / "payload_cache_producer_state_inprocess_native_session_stub.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_session_stub(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
