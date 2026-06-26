from __future__ import annotations

import argparse
import ctypes
from pathlib import Path
import struct

import pytest

from scripts import run_premap_payload_cache_inprocess_native_producer_stub as runner
from scripts import run_premap_payload_cache_inprocess_native_session_stub as session_runner


def test_inprocess_native_stub_source_preserves_payloadless_contract() -> None:
    source = Path(
        "microbench/premap_kernel_consumer/"
        "premap_payload_cache_inprocess_native_producer_stub.hip"
    ).read_text(encoding="utf-8")
    assert "extern \"C\" int premap_payload_cache_inprocess_producer_run_v1" in source
    assert "hipStreamBeginCapture" in source
    assert "hipGraphLaunch" in source
    assert "persistent_state_on_device" in source
    assert "issue_generation_on_device" in source
    assert "passed_to_kernel = 0" in source
    assert "kernel_arg_pass = 0" in source
    assert "kernel_arg_pass_allowed = 0" in source
    assert (
        "extern \"C\" int "
        "premap_payload_cache_inprocess_producer_session_restore_state_v1"
    ) in source
    assert (
        "extern \"C\" int "
        "premap_payload_cache_inprocess_producer_session_update_count_ptr_v1"
    ) in source
    assert "current_wna16_arg_compatible = 0" in source
    assert "uses_current_wna16_args = 0" in source
    assert "passes_current_wna16_args = 0" in source


def test_inprocess_native_stub_builds_shared_library_command(tmp_path: Path) -> None:
    output = tmp_path / "producer.so"
    command = runner.build_command(offload_arch="gfx1100", output=output)

    assert command[:5] == ["hipcc", "-O3", "--std=c++17", "-shared", "-fPIC"]
    assert "--offload-arch=gfx1100" in command
    assert str(runner.SRC) in command
    assert str(output) in command


def test_inprocess_native_result_ctypes_layout_is_pinned() -> None:
    expected_offsets = {
        "abi_version": 0,
        "ok": 4,
        "passed": 8,
        "native_returncode": 12,
        "steps": 16,
        "layers": 20,
        "experts_per_layer": 24,
        "transition_topk_count": 28,
        "packet_count": 32,
        "previous_nonempty_packet_count": 40,
        "current_nonempty_packet_count": 48,
        "issue_candidate_count": 56,
        "expected_issue_candidate_count": 64,
        "issue_candidate_hash": 72,
        "first_issue_expert": 80,
        "last_issue_expert": 84,
        "ready_layer_count": 88,
        "error_count": 92,
        "gpu_elapsed_ms": 96,
        "persistent_state_on_device": 100,
        "issue_generation_on_device": 104,
        "native_graph_replay": 108,
        "native_stub_invoked": 112,
        "vectorized_copy_requested": 116,
        "vectorized_copy_used": 120,
        "payload_bytes": 124,
        "payload_transfer_enabled": 128,
        "payload_deref_allowed": 132,
        "ready_credit": 136,
        "ready_before_demand_credit": 140,
        "real_ready_credit_granted": 144,
        "passed_to_kernel": 148,
        "changes_kernel_launch_args": 152,
        "kernel_arg_pass": 156,
        "kernel_arg_pass_allowed": 160,
        "current_wna16_arg_compatible": 164,
        "uses_current_wna16_args": 168,
        "passes_current_wna16_args": 172,
        "measures_tpot": 176,
        "measures_vllm_latency": 180,
    }

    assert ctypes.sizeof(runner.InprocessProducerResult) == 184
    assert {
        name: getattr(runner.InprocessProducerResult, name).offset
        for name, _ctype in runner.InprocessProducerResult._fields_
    } == expected_offsets


def test_inprocess_native_session_update_result_ctypes_layout_is_pinned() -> None:
    expected_offsets = {
        "abi_version": 0,
        "ok": 4,
        "passed": 8,
        "native_returncode": 12,
        "session_handle_nonzero": 16,
        "current_expert_ptr_nonzero": 20,
        "layer_id": 24,
        "layers": 28,
        "experts_per_layer": 32,
        "transition_topk_count": 36,
        "previous_count_before": 40,
        "current_count": 44,
        "packet_count": 48,
        "previous_nonempty_packet_count": 52,
        "current_nonempty_packet_count": 56,
        "issue_candidate_count": 60,
        "expected_issue_candidate_count": 64,
        "issue_candidate_hash": 72,
        "first_issue_expert": 80,
        "last_issue_expert": 84,
        "ready": 88,
        "error_count": 92,
        "gpu_elapsed_ms": 96,
        "persistent_state_on_device": 100,
        "issue_generation_on_device": 104,
        "prelaunch_callable_native_session": 108,
        "graph_visible": 112,
        "native_stub_invoked": 116,
        "vectorized_copy_requested": 120,
        "vectorized_copy_used": 124,
        "payload_bytes": 128,
        "payload_transfer_enabled": 132,
        "payload_deref_allowed": 136,
        "ready_credit": 140,
        "ready_before_demand_credit": 144,
        "real_ready_credit_granted": 148,
        "passed_to_kernel": 152,
        "changes_kernel_launch_args": 156,
        "kernel_arg_pass": 160,
        "kernel_arg_pass_allowed": 164,
        "current_wna16_arg_compatible": 168,
        "uses_current_wna16_args": 172,
        "passes_current_wna16_args": 176,
        "measures_tpot": 180,
        "measures_vllm_latency": 184,
    }

    assert ctypes.sizeof(session_runner.InprocessProducerSessionUpdateResult) == 192
    assert {
        name: getattr(session_runner.InprocessProducerSessionUpdateResult, name).offset
        for name, _ctype in session_runner.InprocessProducerSessionUpdateResult._fields_
    } == expected_offsets


def _args() -> argparse.Namespace:
    return argparse.Namespace(
        steps=4,
        layers=2,
        experts_per_layer=8,
        transition_topk_count=8,
        graph_replay=True,
        disable_vectorized_copy=False,
        offload_arch="gfx1100",
    )


def _valid_result() -> runner.InprocessProducerResult:
    result = runner.InprocessProducerResult()
    result.abi_version = 1
    result.ok = 1
    result.passed = 1
    result.native_returncode = 0
    result.steps = 4
    result.layers = 2
    result.experts_per_layer = 8
    result.transition_topk_count = 8
    result.packet_count = 8
    result.previous_nonempty_packet_count = 6
    result.current_nonempty_packet_count = 8
    result.issue_candidate_count = 48
    result.expected_issue_candidate_count = 48
    result.issue_candidate_hash = 0x1234
    result.first_issue_expert = 0
    result.last_issue_expert = 7
    result.ready_layer_count = 2
    result.error_count = 0
    result.gpu_elapsed_ms = 0.125
    result.persistent_state_on_device = 1
    result.issue_generation_on_device = 1
    result.native_graph_replay = 1
    result.native_stub_invoked = 1
    result.vectorized_copy_requested = 1
    result.vectorized_copy_used = 1
    return result


def test_inprocess_native_stub_payload_preserves_no_payload_contract(
    tmp_path: Path,
) -> None:
    payload = runner._payload_from_result(
        _valid_result(),
        native_returncode=0,
        library=tmp_path / "producer.so",
        args=_args(),
    )

    assert payload["ok"] is True
    assert payload["passed"] is True
    assert payload["inprocess_native_op"] is True
    assert payload["native_runtime"] is True
    assert payload["native_shared_library"] is True
    assert payload["native_graph_replay"] is True
    assert payload["vllm_replay_visible"] is False
    assert payload["torch_graph_replay_visible"] is False
    assert payload["ready_for_vllm_prelaunch_canary"] is True
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["kernel_arg_pass"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["current_wna16_arg_compatible"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def test_inprocess_native_stub_payload_rejects_missing_graph_replay(
    tmp_path: Path,
) -> None:
    result = _valid_result()
    result.native_graph_replay = 0
    args = _args()
    args.graph_replay = False

    payload = runner._payload_from_result(
        result,
        native_returncode=0,
        library=tmp_path / "producer.so",
        args=args,
    )

    assert payload["ok"] is False
    assert payload["passed"] is False
    assert "native_graph_replay_not_enabled" in payload["failures"]


def test_inprocess_native_stub_payload_rejects_kernel_arg_pass_allowed(
    tmp_path: Path,
) -> None:
    result = _valid_result()
    result.kernel_arg_pass_allowed = 1

    payload = runner._payload_from_result(
        result,
        native_returncode=0,
        library=tmp_path / "producer.so",
        args=_args(),
    )

    assert payload["ok"] is False
    assert payload["passed"] is False
    assert "kernel_arg_pass_allowed_unexpectedly_enabled" in payload["failures"]


def _session_args() -> argparse.Namespace:
    return argparse.Namespace(
        steps=4,
        layers=2,
        experts_per_layer=8,
        transition_topk_count=8,
        max_num_experts=256,
        step_shift=1,
        layer_stride=17,
        disable_vectorized_copy=False,
        device_current_count=False,
        native_generated_current=False,
        offload_arch="gfx1100",
        force_build=False,
        packet_stream_bin=None,
    )


def _write_packet_stream(
    path: Path,
    *,
    layer_ids: list[int],
    current_counts: list[int],
    previous_counts: list[int],
    issue_counts: list[int],
    state_override_flags: list[int] | None = None,
    current_rows: list[list[int]] | None = None,
    previous_rows: list[list[int]] | None = None,
    issue_rows: list[list[int]] | None = None,
    max_experts_per_packet: int = 4,
    transition_topk_count: int = 2,
    max_num_experts: int = 64,
) -> None:
    packet_count = len(layer_ids)
    assert len(current_counts) == packet_count
    assert len(previous_counts) == packet_count
    assert len(issue_counts) == packet_count
    if state_override_flags is None:
        state_override_flags = [0] * packet_count
    assert len(state_override_flags) == packet_count
    layer_count = max(layer_ids) + 1

    def padded(rows: list[list[int]]) -> list[int]:
        flat: list[int] = []
        for row in rows:
            flat.extend(row + [-1] * (max_experts_per_packet - len(row)))
        return flat

    if current_rows is None:
        current_rows = [
            list(range(index, index + count))
            for index, count in enumerate(current_counts)
        ]
    if previous_rows is None:
        previous_rows = [
            list(range(10 + index, 10 + index + count))
            for index, count in enumerate(previous_counts)
        ]
    if issue_rows is None:
        issue_rows = [
            list(range(20 + index, 20 + index + count))
            for index, count in enumerate(issue_counts)
        ]
    assert [len(row) for row in current_rows] == current_counts
    assert [len(row) for row in previous_rows] == previous_counts
    assert [len(row) for row in issue_rows] == issue_counts
    with path.open("wb") as handle:
        handle.write(
            struct.pack(
                "<8I",
                session_runner.PACKET_STREAM_MAGIC,
                session_runner.PACKET_STREAM_VERSION,
                packet_count,
                layer_count,
                max_experts_per_packet,
                transition_topk_count,
                max_num_experts,
                0,
            )
        )
        for values in (
            layer_ids,
            current_counts,
            previous_counts,
            issue_counts,
            state_override_flags,
        ):
            handle.write(struct.pack(f"<{packet_count}I", *values))
        for values in (
            padded(current_rows),
            padded(previous_rows),
            padded(issue_rows),
        ):
            handle.write(struct.pack(f"<{len(values)}i", *values))


def _valid_session_update_result(
    *,
    previous_count_before: int,
    first_issue_expert: int = -1,
    last_issue_expert: int = -1,
) -> session_runner.InprocessProducerSessionUpdateResult:
    result = session_runner.InprocessProducerSessionUpdateResult()
    result.abi_version = 1
    result.ok = 1
    result.passed = 1
    result.native_returncode = 0
    result.session_handle_nonzero = 1
    result.current_expert_ptr_nonzero = 1
    result.layers = 2
    result.experts_per_layer = 8
    result.transition_topk_count = 8
    result.previous_count_before = previous_count_before
    result.current_count = 8
    result.packet_count = 1
    result.previous_nonempty_packet_count = 1 if previous_count_before > 0 else 0
    result.current_nonempty_packet_count = 1
    result.issue_candidate_count = previous_count_before
    result.expected_issue_candidate_count = previous_count_before
    result.issue_candidate_hash = 0x1234 + previous_count_before
    result.first_issue_expert = first_issue_expert
    result.last_issue_expert = last_issue_expert
    result.ready = 1
    result.error_count = 0
    result.gpu_elapsed_ms = 0.01
    result.persistent_state_on_device = 1
    result.issue_generation_on_device = 1
    result.prelaunch_callable_native_session = 1
    result.graph_visible = 0
    result.native_stub_invoked = 1
    result.vectorized_copy_requested = 1
    result.vectorized_copy_used = 1
    return result


def test_inprocess_native_session_payload_preserves_no_payload_contract(
    tmp_path: Path,
) -> None:
    update_results = []
    for step in range(4):
        for layer in range(2):
            update_results.append(
                (
                    0,
                    _valid_session_update_result(
                        previous_count_before=0 if step == 0 else 8,
                        first_issue_expert=-1 if step == 0 else 0,
                        last_issue_expert=-1 if step == 0 else 7,
                    ),
                )
            )

    payload = session_runner._payload_from_updates(
        args=_session_args(),
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=update_results,
    )

    assert payload["ok"] is True
    assert payload["passed"] is True
    assert payload["mode"] == "payload_cache_producer_state_inprocess_native_session_canary"
    assert payload["prelaunch_callable_native_session"] is True
    assert payload["ready_for_native_session_smoke"] is True
    assert payload["ready_for_external_pointer_smoke"] is True
    assert payload["ready_for_vllm_prelaunch_canary"] is False
    assert payload["native_graph_replay"] is False
    assert payload["current_expert_ptr_source"] == "torch_device_tensor"
    assert payload["current_expert_ptr_source_kind"] == (
        "external_torch_device_tensor_smoke"
    )
    assert payload["current_count_source_kind"] == "host_scalar_uint32"
    assert payload["current_count_device_ptr_passed"] is False
    assert payload["current_count_host_scalar_passed"] is True
    assert payload["external_current_expert_ptr_source"] is True
    assert payload["vllm_replay_visible"] is False
    assert payload["torch_graph_replay_visible"] is False
    assert payload["graph_visible"] is False
    assert payload["packet_count"] == 8
    assert payload["previous_nonempty_packet_count"] == 6
    assert payload["issue_candidate_count"] == 48
    assert payload["expected_issue_candidate_count"] == 48
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["kernel_arg_pass"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False


def test_inprocess_native_session_payload_marks_device_current_count(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(**{**vars(_session_args()), "device_current_count": True})
    update_results = [
        (0, _valid_session_update_result(previous_count_before=0)),
        (0, _valid_session_update_result(previous_count_before=0)),
    ]

    payload = session_runner._payload_from_updates(
        args=argparse.Namespace(**{**vars(args), "steps": 1}),
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=update_results,
    )

    assert payload["ok"] is True
    assert payload["current_count_source_kind"] == "device_tensor_int32_bits_as_uint32"
    assert payload["current_count_device_ptr_passed"] is True
    assert payload["current_count_host_scalar_passed"] is False
    assert payload["payload_bytes"] == 0
    assert payload["kernel_arg_pass"] is False


def test_inprocess_native_session_payload_disambiguates_native_generated_current(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(**{**vars(_session_args()), "native_generated_current": True})
    update_results = []
    for step in range(4):
        for _layer in range(2):
            update_results.append(
                (
                    0,
                    _valid_session_update_result(
                        previous_count_before=0 if step == 0 else 8,
                        first_issue_expert=-1 if step == 0 else 0,
                        last_issue_expert=-1 if step == 0 else 7,
                    ),
                )
            )

    payload = session_runner._payload_from_updates(
        args=args,
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=update_results,
    )

    assert payload["ok"] is True
    assert payload["ready_for_native_session_smoke"] is True
    assert payload["ready_for_external_pointer_smoke"] is False
    assert payload["ready_for_vllm_prelaunch_canary"] is False
    assert payload["current_expert_ptr_source"] == "native_generated_device_scratch"
    assert payload["current_expert_ptr_source_kind"] == "native_scratch_smoke"
    assert payload["external_current_expert_ptr_source"] is False


def test_inprocess_native_session_payload_rejects_kernel_arg_pass(
    tmp_path: Path,
) -> None:
    update = _valid_session_update_result(previous_count_before=0)
    update.passed_to_kernel = 1

    payload = session_runner._payload_from_updates(
        args=argparse.Namespace(**{**vars(_session_args()), "steps": 1}),
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=[
            (0, update),
            (0, _valid_session_update_result(previous_count_before=0)),
        ],
    )

    assert payload["ok"] is False
    assert payload["passed"] is False
    assert "passed_to_kernel_unexpectedly_enabled" in payload["failures"]


def test_inprocess_native_session_loads_packet_stream_metadata(
    tmp_path: Path,
) -> None:
    stream = tmp_path / "packets.bin"
    _write_packet_stream(
        stream,
        layer_ids=[0, 0, 0],
        current_counts=[4, 4, 4],
        previous_counts=[0, 4, 4],
        issue_counts=[0, 2, 2],
        state_override_flags=[0, 0, 1],
        current_rows=[[1, 2, 3, 4], [4, 5, 6, 7], [6, 7, 8, 9]],
        previous_rows=[[], [1, 2, 3, 4], [11, 12, 13, 14]],
        issue_rows=[[], [1, 2], [11, 12]],
        max_experts_per_packet=4,
        transition_topk_count=2,
        max_num_experts=64,
    )

    payload = session_runner._load_packet_stream(stream)

    assert payload["packet_count"] == 3
    assert payload["layer_count"] == 1
    assert payload["max_experts_per_packet"] == 4
    assert payload["transition_topk_count"] == 2
    assert payload["max_num_experts"] == 64
    assert payload["layer_ids"] == (0, 0, 0)
    assert payload["current_counts"] == (4, 4, 4)
    assert payload["expected_previous_nonempty_packet_count"] == 2
    assert payload["expected_issue_candidate_count"] == 4
    assert payload["state_override_count"] == 1
    assert len(payload["current_experts"]) == 12


def test_inprocess_native_session_payload_accepts_packet_stream_source(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        **{
            **vars(_session_args()),
            "steps": 2,
            "layers": 1,
            "experts_per_layer": 3,
            "transition_topk_count": 2,
            "packet_stream_input": True,
            "packet_stream_bin": tmp_path / "packets.bin",
        "packet_stream_state_override_count": 0,
        "packet_stream_state_restore_count": 0,
        "expected_packet_count": 2,
        "expected_previous_nonempty_packet_count": 1,
        "expected_issue_candidate_count": 2,
        "expected_previous_counts": (0, 2),
    }
    )
    update_results = [
        (
            0,
            _valid_session_update_result(
                previous_count_before=0,
                first_issue_expert=-1,
                last_issue_expert=-1,
            ),
        ),
        (
            0,
            _valid_session_update_result(
                previous_count_before=2,
                first_issue_expert=3,
                last_issue_expert=4,
            ),
        ),
    ]
    for _native_returncode, result in update_results:
        result.layer_id = 0
        result.layers = 1
        result.experts_per_layer = 3
        result.transition_topk_count = 2
        result.current_count = 3
    update_results[1][1].issue_candidate_count = 2
    update_results[1][1].expected_issue_candidate_count = 2

    payload = session_runner._payload_from_updates(
        args=args,
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=update_results,
    )

    assert payload["ok"] is True
    assert payload["passed"] is True
    assert payload["packet_stream_input"] is True
    assert payload["packet_stream_bin"] == str(args.packet_stream_bin)
    assert payload["packet_stream_state_override_count"] == 0
    assert payload["packet_stream_state_restore_supported"] is True
    assert payload["packet_stream_state_restore_count"] == 0
    assert payload["packet_stream_state_restore_returncodes"] == []
    assert payload["packet_count"] == 2
    assert payload["previous_nonempty_packet_count"] == 1
    assert payload["expected_previous_nonempty_packet_count"] == 1
    assert payload["issue_candidate_count"] == 2
    assert payload["expected_issue_candidate_count"] == 2
    assert payload["current_expert_ptr_source"] == "packet_stream_torch_device_tensor"
    assert payload["current_expert_ptr_source_kind"] == (
        "online_packet_stream_device_tensor_smoke"
    )
    assert payload["external_current_expert_ptr_source"] is False
    assert payload["ready_for_external_pointer_smoke"] is False
    assert payload["ready_for_vllm_prelaunch_canary"] is False
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["kernel_arg_pass"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False


def test_inprocess_native_session_payload_rejects_packet_layer_mismatch(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        **{
            **vars(_session_args()),
            "steps": 1,
            "layers": 2,
            "experts_per_layer": 3,
            "transition_topk_count": 2,
            "packet_stream_input": True,
            "packet_stream_bin": tmp_path / "packets.bin",
            "expected_packet_count": 1,
            "expected_previous_nonempty_packet_count": 0,
            "expected_issue_candidate_count": 0,
            "expected_layer_ids": (1,),
            "expected_current_counts": (3,),
        }
    )
    update = _valid_session_update_result(previous_count_before=0)
    update.layer_id = 0
    update.layers = 2
    update.experts_per_layer = 3
    update.transition_topk_count = 2
    update.current_count = 3

    payload = session_runner._payload_from_updates(
        args=args,
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=[(0, update)],
    )

    assert payload["ok"] is False
    assert "native_layer_id_mismatch" in payload["failures"]


def test_inprocess_native_session_payload_rejects_packet_previous_count_mismatch(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        **{
            **vars(_session_args()),
            "steps": 1,
            "layers": 1,
            "experts_per_layer": 3,
            "transition_topk_count": 2,
            "packet_stream_input": True,
            "packet_stream_bin": tmp_path / "packets.bin",
            "expected_packet_count": 1,
            "expected_previous_nonempty_packet_count": 1,
            "expected_issue_candidate_count": 2,
            "expected_previous_counts": (2,),
        }
    )
    update = _valid_session_update_result(previous_count_before=1)
    update.layer_id = 0
    update.layers = 1
    update.experts_per_layer = 3
    update.transition_topk_count = 2
    update.current_count = 3
    update.previous_nonempty_packet_count = 1
    update.issue_candidate_count = 1
    update.expected_issue_candidate_count = 1

    payload = session_runner._payload_from_updates(
        args=args,
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=[(0, update)],
    )

    assert payload["ok"] is False
    assert "native_previous_count_before_mismatch" in payload["failures"]


def test_inprocess_native_session_payload_rejects_packet_previous_count_length_mismatch(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        **{
            **vars(_session_args()),
            "steps": 1,
            "layers": 1,
            "experts_per_layer": 3,
            "transition_topk_count": 2,
            "packet_stream_input": True,
            "packet_stream_bin": tmp_path / "packets.bin",
            "expected_packet_count": 1,
            "expected_previous_nonempty_packet_count": 0,
            "expected_issue_candidate_count": 0,
            "expected_previous_counts": (),
            "expected_layer_ids": (),
            "expected_current_counts": (),
        }
    )
    args.expected_previous_counts = (0,)
    update = _valid_session_update_result(previous_count_before=0)
    update.layer_id = 0
    update.layers = 1
    update.experts_per_layer = 3
    update.transition_topk_count = 2
    update.current_count = 3

    payload = session_runner._payload_from_updates(
        args=args,
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=[(0, update), (0, update)],
    )

    assert payload["ok"] is False
    assert "expected_previous_counts_length_mismatch" in payload["failures"]


def test_inprocess_native_session_payload_rejects_restore_failure(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        **{
            **vars(_session_args()),
            "steps": 1,
            "layers": 1,
            "experts_per_layer": 3,
            "transition_topk_count": 2,
            "packet_stream_input": True,
            "packet_stream_bin": tmp_path / "packets.bin",
            "packet_stream_state_override_count": 1,
            "expected_packet_count": 1,
            "expected_previous_nonempty_packet_count": 0,
            "expected_issue_candidate_count": 0,
            "expected_previous_counts": (0,),
        }
    )
    update = _valid_session_update_result(previous_count_before=0)
    update.layer_id = 0
    update.layers = 1
    update.experts_per_layer = 3
    update.transition_topk_count = 2
    update.current_count = 3

    payload = session_runner._payload_from_updates(
        args=args,
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=[(0, update)],
        restore_returncodes=[262],
    )

    assert payload["ok"] is False
    assert payload["packet_stream_state_restore_count"] == 1
    assert payload["packet_stream_state_restore_returncodes"] == [262]
    assert "session_restore_state_failed" in payload["failures"]


def test_inprocess_native_session_payload_rejects_missing_restore_for_override(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        **{
            **vars(_session_args()),
            "steps": 1,
            "layers": 1,
            "experts_per_layer": 3,
            "transition_topk_count": 2,
            "packet_stream_input": True,
            "packet_stream_bin": tmp_path / "packets.bin",
            "packet_stream_state_override_count": 1,
            "expected_packet_count": 1,
            "expected_previous_nonempty_packet_count": 0,
            "expected_issue_candidate_count": 0,
            "expected_previous_counts": (0,),
        }
    )
    update = _valid_session_update_result(previous_count_before=0)
    update.layer_id = 0
    update.layers = 1
    update.experts_per_layer = 3
    update.transition_topk_count = 2
    update.current_count = 3

    payload = session_runner._payload_from_updates(
        args=args,
        library=tmp_path / "producer.so",
        create_returncode=0,
        destroy_returncode=0,
        handle=1234,
        update_results=[(0, update)],
        restore_returncodes=[],
    )

    assert payload["ok"] is False
    assert payload["packet_stream_state_restore_count"] == 0
    assert "packet_stream_state_restore_count_mismatch" in payload["failures"]


def test_inprocess_native_session_parser_rejects_issue_content_mismatch(
    tmp_path: Path,
) -> None:
    stream = tmp_path / "packets.bin"
    _write_packet_stream(
        stream,
        layer_ids=[0, 0],
        current_counts=[2, 2],
        previous_counts=[0, 2],
        issue_counts=[0, 1],
        current_rows=[[4, 5], [6, 7]],
        previous_rows=[[], [4, 5]],
        issue_rows=[[], [5]],
        max_experts_per_packet=2,
        transition_topk_count=1,
    )

    with pytest.raises(ValueError, match="issue experts do not match previous topk"):
        session_runner._load_packet_stream(stream)


def test_inprocess_native_session_parser_rejects_current_count_out_of_range(
    tmp_path: Path,
) -> None:
    stream = tmp_path / "packets.bin"
    _write_packet_stream(
        stream,
        layer_ids=[0],
        current_counts=[2],
        previous_counts=[0],
        issue_counts=[0],
        current_rows=[[4, 5]],
        previous_rows=[[]],
        issue_rows=[[]],
        max_experts_per_packet=2,
        transition_topk_count=1,
    )
    raw = bytearray(stream.read_bytes())
    header_size = struct.calcsize("<8I")
    current_counts_offset = header_size + struct.calcsize("<1I")
    raw[current_counts_offset : current_counts_offset + 4] = struct.pack("<I", 3)
    stream.write_bytes(bytes(raw))

    with pytest.raises(ValueError, match="current count out of range"):
        session_runner._load_packet_stream(stream)


def test_inprocess_native_session_parser_rejects_reserved_header(
    tmp_path: Path,
) -> None:
    stream = tmp_path / "packets.bin"
    _write_packet_stream(
        stream,
        layer_ids=[0],
        current_counts=[2],
        previous_counts=[0],
        issue_counts=[0],
        current_rows=[[4, 5]],
        previous_rows=[[]],
        issue_rows=[[]],
        max_experts_per_packet=2,
        transition_topk_count=1,
    )
    raw = bytearray(stream.read_bytes())
    raw[28:32] = struct.pack("<I", 1)
    stream.write_bytes(bytes(raw))

    with pytest.raises(ValueError, match="reserved header"):
        session_runner._load_packet_stream(stream)
