from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import pytest

from scripts import run_premap_payload_cache_producer_state_stream_stub as runner


def test_stream_stub_source_preserves_payloadless_native_producer_contract() -> None:
    source = Path(
        "microbench/premap_kernel_consumer/"
        "premap_payload_cache_producer_state_stream_stub.hip"
    ).read_text(encoding="utf-8")
    assert "producer_transition_stream_kernel" in source
    assert "producer_transition_step_kernel" in source
    assert "hipStreamBeginCapture" in source
    assert "hipGraphLaunch" in source
    assert "persistent_state_on_device" in source
    assert "issue_generation_on_device" in source
    assert "vectorized_copy_used" in source
    assert "reinterpret_cast<const int4*>" in source
    assert "payload_bytes" in source
    assert "kernel_arg_pass" in source
    assert "kernel_arg_pass_allowed" in source
    assert "passed_to_kernel" in source
    assert "changes_kernel_launch_args" in source
    assert "current_wna16_arg_compatible" in source
    assert "uses_current_wna16_args" in source
    assert "passes_current_wna16_args" in source
    assert 'parse_bounded_u32(require_value("--steps"), "--steps", 4096U)' not in source


def test_stream_stub_build_command_targets_dedicated_source(tmp_path: Path) -> None:
    output = tmp_path / "producer_state_stream_stub"
    command = runner.build_command(offload_arch="gfx1100", output=output)
    assert command[:3] == ["hipcc", "-O3", "--std=c++17"]
    assert "--offload-arch=gfx1100" in command
    assert str(runner.SRC) in command
    assert str(output) in command
    assert "premap_payload_cache_producer_state_stream_stub.hip" in str(runner.SRC)


def test_stream_stub_rejects_zero_steps() -> None:
    with pytest.raises(ValueError, match="steps must be positive"):
        runner._validate_count(0, "steps")


def test_stream_stub_allows_zero_topk_as_all_previous() -> None:
    assert runner._validate_count(0, "transition-topk-count", allow_zero=True) == 0


def _args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        device=0,
        steps=4,
        layers=2,
        experts_per_layer=8,
        transition_topk_count=8,
        max_num_experts=256,
        step_shift=1,
        layer_stride=17,
        state_hash_base=0x8A45D2C91FE01237,
        disable_vectorized_copy=False,
        graph_replay=False,
        packet_stream_bin=None,
        offload_arch="gfx1100",
        hip_visible_devices=None,
        force_build=False,
        output_json=tmp_path / "out.json",
    )


def test_stream_stub_run_payload_preserves_no_payload_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runner, "build", lambda *, offload_arch, force: tmp_path / "stub")
    native_payload = {
        "ok": True,
        "passed": True,
        "failures": [],
        "mode": "payload_cache_producer_transition_state_stream_native_canary",
        "payload_bytes": 0,
        "ready_credit": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "persistent_state_on_device": True,
        "issue_generation_on_device": True,
        "vectorized_copy_requested": True,
        "vectorized_copy_used": True,
        "native_graph_replay": False,
        "native_stub_invoked": True,
    }

    def fake_run_cmd(cmd, *, env=None, allow_failure=False):
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps(native_payload),
            stderr="",
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)

    payload = runner.run_stub(_args(tmp_path))

    assert payload["ok"] is True
    assert payload["native_returncode"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["kernel_arg_pass"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["persistent_state_on_device"] is True
    assert payload["issue_generation_on_device"] is True
    assert payload["vectorized_copy_used"] is True
    assert payload["requested_graph_replay"] is False


def test_stream_stub_runner_passes_graph_replay_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runner, "build", lambda *, offload_arch, force: tmp_path / "stub")
    captured: dict[str, object] = {}

    def fake_run_cmd(cmd, *, env=None, allow_failure=False):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "passed": True,
                    "failures": [],
                    "payload_bytes": 0,
                    "ready_credit": False,
                    "kernel_arg_pass": False,
                    "kernel_arg_pass_allowed": False,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                    "uses_current_wna16_args": False,
                    "passes_current_wna16_args": False,
                    "persistent_state_on_device": True,
                    "issue_generation_on_device": True,
                    "vectorized_copy_used": True,
                    "native_graph_replay": True,
                    "native_stub_invoked": True,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    args = _args(tmp_path)
    args.graph_replay = True

    payload = runner.run_stub(args)

    assert "--graph-replay" in captured["cmd"]
    assert payload["requested_graph_replay"] is True
    assert payload["native_graph_replay"] is True


def test_stream_stub_runner_passes_packet_stream_bin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runner, "build", lambda *, offload_arch, force: tmp_path / "stub")
    captured: dict[str, object] = {}

    def fake_run_cmd(cmd, *, env=None, allow_failure=False):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "passed": True,
                    "failures": [],
                    "payload_bytes": 0,
                    "ready_credit": False,
                    "kernel_arg_pass": False,
                    "kernel_arg_pass_allowed": False,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                    "uses_current_wna16_args": False,
                    "passes_current_wna16_args": False,
                    "persistent_state_on_device": True,
                    "issue_generation_on_device": True,
                    "native_graph_replay": True,
                    "native_stub_invoked": True,
                    "packet_stream_input": True,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    args = _args(tmp_path)
    args.graph_replay = True
    args.packet_stream_bin = tmp_path / "packets.bin"

    payload = runner.run_stub(args)

    assert "--packet-stream-bin" in captured["cmd"]
    assert str(args.packet_stream_bin) in captured["cmd"]
    assert payload["requested_packet_stream_bin"] == str(args.packet_stream_bin)


def test_stream_stub_runner_allows_large_packet_stream_step_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runner, "build", lambda *, offload_arch, force: tmp_path / "stub")
    captured: dict[str, object] = {}

    def fake_run_cmd(cmd, *, env=None, allow_failure=False):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "passed": True,
                    "failures": [],
                    "payload_bytes": 0,
                    "ready_credit": False,
                    "kernel_arg_pass": False,
                    "kernel_arg_pass_allowed": False,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                    "uses_current_wna16_args": False,
                    "passes_current_wna16_args": False,
                    "persistent_state_on_device": True,
                    "issue_generation_on_device": True,
                    "native_graph_replay": True,
                    "native_stub_invoked": True,
                    "packet_stream_input": True,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)
    args = _args(tmp_path)
    args.steps = 4097
    args.layers = 1
    args.experts_per_layer = 1
    args.packet_stream_bin = tmp_path / "packets.bin"

    payload = runner.run_stub(args)

    assert payload["requested_steps"] == 4097
    assert "--steps" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--steps") + 1] == "4097"


def test_stream_stub_nonzero_returncode_forces_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runner, "build", lambda *, offload_arch, force: tmp_path / "stub")

    def fake_run_cmd(cmd, *, env=None, allow_failure=False):
        return subprocess.CompletedProcess(
            cmd,
            7,
            stdout=json.dumps({"ok": True, "passed": True, "failures": []}),
            stderr="boom",
        )

    monkeypatch.setattr(runner, "run_cmd", fake_run_cmd)

    payload = runner.run_stub(_args(tmp_path))

    assert payload["ok"] is False
    assert payload["passed"] is False
    assert payload["native_returncode"] == 7
    assert "native_returncode_nonzero" in payload["failures"]
