from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

from scripts import run_premap_payload_cache_packet_stream_native_canary as canary


def _packet(
    *,
    layer_id: int,
    current_experts: list[int],
    previous_experts: list[int],
) -> dict:
    payload = {
        "layer_id": layer_id,
        "current_expert_count": len(current_experts),
        "current_experts": current_experts,
        "previous_expert_count": len(previous_experts),
        "previous_experts": previous_experts,
        "issue_candidate_count": len(previous_experts),
        "issue_candidate_experts": previous_experts,
        "transition_topk_count": 2,
        "max_num_experts": 256,
        "state_owner": "producer",
        "payload_bytes": 0,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "uses_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "changes_kernel_launch_args": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }
    payload["_export_context"] = {
        "payload_bytes": 0,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "uses_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "changes_kernel_launch_args": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }
    return payload


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _manifest(tmp_path: Path, packet_paths: list[Path]) -> Path:
    path = tmp_path / "manifest.json"
    _write_json(
        path,
        {
            "ok": True,
            "passed": True,
            "payload_bytes": 0,
            "kernel_arg_pass": False,
            "kernel_arg_pass_allowed": False,
            "passed_to_kernel": False,
            "passes_current_wna16_args": False,
            "uses_current_wna16_args": False,
            "current_wna16_arg_compatible": False,
            "changes_kernel_launch_args": False,
            "payload_transfer_enabled": False,
            "payload_deref_allowed": False,
            "ready_credit": False,
            "ready_before_demand_credit": False,
            "real_ready_credit_granted": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
            "online_packet_export_paths": [str(packet_path) for packet_path in packet_paths],
            "checked_packet_count": len(packet_paths),
            "checked_nonempty_packet_count": 1,
            "shifted_issue_total_issue_candidates": 2,
        },
    )
    return path


def test_packet_stream_materialization_writes_v2_rows_and_state_overrides(
    tmp_path: Path,
) -> None:
    first = tmp_path / "packet0.json"
    second = tmp_path / "packet1.json"
    _write_json(first, _packet(layer_id=0, current_experts=[5, 7, 9], previous_experts=[]))
    _write_json(second, _packet(layer_id=0, current_experts=[11, 13], previous_experts=[5, 7]))
    manifest = _manifest(tmp_path, [first, second])
    output_bin = tmp_path / "stream.bin"

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=output_bin,
    )

    assert result["passed"] is True
    assert result["packet_count"] == 2
    assert result["max_experts_per_packet"] == 3
    assert result["state_override_count"] == 1
    assert result["expected_issue_candidate_hash"] == canary._expected_native_packet_issue_hash(
        [[], [5, 7]]
    )
    raw = output_bin.read_bytes()
    header = struct.unpack_from("<8I", raw, 0)
    assert header[:7] == (
        canary.PACKET_STREAM_MAGIC,
        canary.PACKET_STREAM_VERSION,
        2,
        1,
        3,
        2,
        256,
    )
    offset = struct.calcsize("<8I")
    layer_ids = struct.unpack_from("<2I", raw, offset)
    offset += struct.calcsize("<2I")
    current_counts = struct.unpack_from("<2I", raw, offset)
    offset += struct.calcsize("<2I")
    previous_counts = struct.unpack_from("<2I", raw, offset)
    offset += struct.calcsize("<2I")
    issue_counts = struct.unpack_from("<2I", raw, offset)
    offset += struct.calcsize("<2I")
    state_override_flags = struct.unpack_from("<2I", raw, offset)
    offset += struct.calcsize("<2I")
    current_experts = struct.unpack_from("<6i", raw, offset)
    offset += struct.calcsize("<6i")
    previous_experts = struct.unpack_from("<6i", raw, offset)
    offset += struct.calcsize("<6i")
    issue_experts = struct.unpack_from("<6i", raw, offset)
    assert layer_ids == (0, 0)
    assert current_counts == (3, 2)
    assert previous_counts == (0, 2)
    assert issue_counts == (0, 2)
    assert state_override_flags == (0, 1)
    assert current_experts == (5, 7, 9, 11, 13, -1)
    assert previous_experts == (-1, -1, -1, 5, 7, -1)
    assert issue_experts == (-1, -1, -1, 5, 7, -1)


def test_packet_stream_native_canary_compares_manifest_counts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    first = tmp_path / "packet0.json"
    second = tmp_path / "packet1.json"
    _write_json(first, _packet(layer_id=0, current_experts=[5, 7], previous_experts=[]))
    _write_json(second, _packet(layer_id=0, current_experts=[11, 13], previous_experts=[5, 7]))
    manifest = _manifest(tmp_path, [first, second])
    captured: dict[str, object] = {}

    def fake_run_stub(args: argparse.Namespace) -> dict:
        captured["args"] = args
        assert args.packet_stream_bin.exists()
        assert args.graph_replay is True
        issue_hash = canary._expected_native_packet_issue_hash([[], [5, 7]])
        return {
            "ok": True,
            "passed": True,
            "native_returncode": 0,
            "packet_stream_input": True,
            "native_graph_replay": True,
            "persistent_state_on_device": True,
            "issue_generation_on_device": True,
            "packet_count": 2,
            "previous_nonempty_packet_count": 1,
            "issue_candidate_count": 2,
            "issue_candidate_hash": issue_hash,
            "expected_issue_candidate_count": 2,
            "state_override_count": 0,
            "state_mismatch_count": 0,
            "issue_expert_mismatch_count": 0,
            "payload_bytes": 0,
            "kernel_arg_pass": False,
            "kernel_arg_pass_allowed": False,
            "payload_transfer_enabled": False,
            "payload_deref_allowed": False,
            "ready_credit": False,
            "ready_before_demand_credit": False,
            "real_ready_credit_granted": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
        }

    monkeypatch.setattr(canary.stream_stub, "run_stub", fake_run_stub)
    args = argparse.Namespace(
        manifest_json=manifest,
        packet_stream_bin=tmp_path / "stream.bin",
        native_output_json=tmp_path / "native.json",
        output_json=tmp_path / "out.json",
        device=0,
        hip_visible_devices=None,
        offload_arch="gfx1100",
        state_hash_base=0x8A45D2C91FE01237,
        disable_vectorized_copy=False,
        no_graph_replay=False,
        force_build=False,
    )

    payload = canary.run_canary(args)

    assert payload["passed"] is True
    assert payload["native"]["failures"] == []
    assert payload["comparisons"] == {
        "packet_count_match": True,
        "previous_nonempty_packet_count_match": True,
        "issue_candidate_count_match": True,
        "issue_candidate_hash_match": True,
        "expected_issue_candidate_count_match": True,
        "state_override_count_match": True,
        "state_mismatch_count_zero": True,
        "issue_expert_mismatch_count_zero": True,
    }
    assert captured["args"].packet_stream_bin == args.packet_stream_bin
    assert json.loads(args.native_output_json.read_text())["failures"] == []


def test_packet_stream_native_canary_rejects_bool_zero_native_fields(
    monkeypatch,
    tmp_path: Path,
) -> None:
    first = tmp_path / "packet0.json"
    second = tmp_path / "packet1.json"
    _write_json(first, _packet(layer_id=0, current_experts=[5, 7], previous_experts=[]))
    _write_json(second, _packet(layer_id=0, current_experts=[11, 13], previous_experts=[5, 7]))
    manifest = _manifest(tmp_path, [first, second])

    def fake_run_stub(args: argparse.Namespace) -> dict:
        issue_hash = canary._expected_native_packet_issue_hash([[], [5, 7]])
        return {
            "ok": True,
            "passed": True,
            "native_returncode": False,
            "packet_stream_input": True,
            "native_graph_replay": True,
            "persistent_state_on_device": True,
            "issue_generation_on_device": True,
            "packet_count": 2,
            "previous_nonempty_packet_count": 1,
            "issue_candidate_count": 2,
            "issue_candidate_hash": issue_hash,
            "expected_issue_candidate_count": 2,
            "state_override_count": 1,
            "state_mismatch_count": False,
            "issue_expert_mismatch_count": False,
            "payload_bytes": False,
            "kernel_arg_pass": False,
            "kernel_arg_pass_allowed": False,
            "payload_transfer_enabled": False,
            "payload_deref_allowed": False,
            "ready_credit": False,
            "ready_before_demand_credit": False,
            "real_ready_credit_granted": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
        }

    monkeypatch.setattr(canary.stream_stub, "run_stub", fake_run_stub)
    args = argparse.Namespace(
        manifest_json=manifest,
        packet_stream_bin=tmp_path / "stream.bin",
        native_output_json=tmp_path / "native.json",
        output_json=tmp_path / "out.json",
        device=0,
        hip_visible_devices=None,
        offload_arch="gfx1100",
        state_hash_base=0x8A45D2C91FE01237,
        disable_vectorized_copy=False,
        no_graph_replay=False,
        force_build=False,
    )

    payload = canary.run_canary(args)

    assert payload["passed"] is False
    assert "native_returncode_nonzero" in payload["failures"]
    assert "native_payload_bytes_nonzero" in payload["failures"]
    assert "state_mismatch_count_zero" in payload["failures"]
    assert "issue_expert_mismatch_count_zero" in payload["failures"]


def test_packet_stream_native_canary_marks_hip_device_failure_runtime_blocked(
    monkeypatch,
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet(layer_id=0, current_experts=[5], previous_experts=[]))
    manifest = _manifest(tmp_path, [packet])

    def fake_run_stub(args: argparse.Namespace) -> dict:
        return {
            "ok": False,
            "passed": False,
            "native_returncode": 1,
            "failures": ["native_json_parse_error", "native_returncode_nonzero"],
            "stderr": "hipSetDevice: no ROCm-capable device is detected\n",
        }

    monkeypatch.setattr(canary.stream_stub, "run_stub", fake_run_stub)
    args = argparse.Namespace(
        manifest_json=manifest,
        packet_stream_bin=tmp_path / "stream.bin",
        native_output_json=tmp_path / "native.json",
        output_json=tmp_path / "out.json",
        device=0,
        hip_visible_devices=None,
        offload_arch="gfx1100",
        state_hash_base=0x8A45D2C91FE01237,
        disable_vectorized_copy=False,
        no_graph_replay=False,
        force_build=False,
    )

    payload = canary.run_canary(args)

    assert payload["passed"] is False
    assert payload["native_runtime_blocked"] is True
    assert payload["failures"] == ["native_runtime_blocked"]
    assert payload["comparisons"]["packet_count_match"] is None


def test_packet_stream_native_canary_rejects_payload_packet(tmp_path: Path) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload["payload_bytes"] = 1
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_payload_bytes_nonzero" in result["failures"]


def test_packet_stream_native_canary_rejects_ready_credit_packet(tmp_path: Path) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload["ready_credit"] = True
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_ready_credit_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_kernel_arg_pass_packet(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload["kernel_arg_pass"] = True
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_kernel_arg_pass_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_kernel_arg_pass_allowed_packet(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload["kernel_arg_pass_allowed"] = True
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_kernel_arg_pass_allowed_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_current_wna_packet(tmp_path: Path) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload["current_wna16_arg_compatible"] = True
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_current_wna16_arg_compatible_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_out_of_range_expert(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[300], previous_experts=[])
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_current_experts_0_oob" in result["failures"]


def test_packet_stream_native_canary_rejects_zero_max_num_experts(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload["max_num_experts"] = 0
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_max_num_experts_zero" in result["failures"]


def test_packet_stream_native_canary_rejects_issue_not_previous_topk(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[3], previous_experts=[1, 2])
    payload["issue_candidate_experts"] = [1]
    payload["issue_candidate_count"] = 1
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_issue_experts_not_previous_topk" in result["failures"]


def test_packet_stream_native_canary_rejects_manifest_ready_credit(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet(layer_id=0, current_experts=[1], previous_experts=[]))
    manifest = _manifest(tmp_path, [packet])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["ready_credit"] = True
    _write_json(manifest, payload)

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "manifest_ready_credit_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_manifest_kernel_arg_pass(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet(layer_id=0, current_experts=[1], previous_experts=[]))
    manifest = _manifest(tmp_path, [packet])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["kernel_arg_pass"] = True
    _write_json(manifest, payload)

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "manifest_kernel_arg_pass_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_manifest_kernel_arg_pass_allowed(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet(layer_id=0, current_experts=[1], previous_experts=[]))
    manifest = _manifest(tmp_path, [packet])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["kernel_arg_pass_allowed"] = True
    _write_json(manifest, payload)

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "manifest_kernel_arg_pass_allowed_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_checked_packet_count_mismatch(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet(layer_id=0, current_experts=[1], previous_experts=[]))
    manifest = _manifest(tmp_path, [packet])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["checked_packet_count"] = 2
    _write_json(manifest, payload)

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "checked_packet_count_mismatch" in result["failures"]


def test_packet_stream_native_canary_rejects_context_ready_credit(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload["_export_context"]["ready_credit"] = True
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_ready_credit_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_context_kernel_arg_pass(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload["_export_context"]["kernel_arg_pass"] = True
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_kernel_arg_pass_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_context_kernel_arg_pass_allowed(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload["_export_context"]["kernel_arg_pass_allowed"] = True
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_kernel_arg_pass_allowed_not_false" in result["failures"]


def test_packet_stream_native_canary_rejects_missing_export_context(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet.json"
    payload = _packet(layer_id=0, current_experts=[1], previous_experts=[])
    payload.pop("_export_context")
    _write_json(packet, payload)
    manifest = _manifest(tmp_path, [packet])

    result = canary._materialize_packet_stream(
        manifest_path=manifest,
        output_bin=tmp_path / "stream.bin",
    )

    assert result["passed"] is False
    assert "packet_0_export_context_missing" in result["failures"]
