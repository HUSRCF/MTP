from __future__ import annotations

import importlib.util
import argparse
from pathlib import Path
import subprocess

import pytest

from mtp_expert_prefetch.runtime import (
    PremapPayloadCacheProducerTransitionStatePacket,
)


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_premap_payload_cache_producer_state_stub.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_premap_payload_cache_producer_state_stub",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_payload_cache_producer_state_stub_build_command(tmp_path: Path):
    module = _load_module()
    output = tmp_path / "producer_state_stub"

    cmd = module.build_command(offload_arch="gfx1100", output=output)

    assert cmd[:3] == ["hipcc", "-O3", "--std=c++17"]
    assert "--offload-arch=gfx1100" in cmd
    assert str(module.SRC) in cmd
    assert str(output) in cmd


def test_payload_cache_producer_state_stub_preserves_readonly_contract():
    module = _load_module()
    source = Path(module.SRC).read_text(encoding="utf-8")

    assert "PremapPayloadCacheProducerTransitionStateAbiV1 packet" in source
    assert "producer_transition_state_kernel" in source
    assert "kPremapPayloadCacheProducerTransitionStateAbiV1FieldCount == 9" in source
    assert "kPremapPayloadCacheProducerTransitionStateAbiV1PayloadBytesAllowed" in source
    assert "kPremapPayloadCacheProducerTransitionStateAbiV1KernelArgPassAllowed" in source
    assert "kPremapPayloadCacheProducerTransitionStateAbiV1CurrentWna16ArgCompatible" in source
    assert "parse_bounded_u32" in source
    assert "parse_u64" in source
    assert "issue_hash_mix" in source
    assert "kMaxCount = 65536UL" in source
    assert "kMaxCsvCount = 65536UL" in source
    assert "--layer-id" in source
    assert "--state-hash" in source
    assert '\\"layer_id\\":' in source
    assert '\\"issue_candidate_first_expert\\":' in source
    assert '\\"issue_candidate_last_expert\\":' in source
    assert '\\"issue_candidate_hash\\":' in source
    assert '\\"payload_bytes\\":0' in source
    assert '\\"ready_credit\\":false' in source
    assert '\\"passed_to_kernel\\":false' in source
    assert '\\"changes_kernel_launch_args\\":false' in source
    assert '\\"current_wna16_arg_compatible\\":false' in source
    assert '\\"native_stub_invoked\\":true' in source


def test_payload_cache_producer_state_stub_rejects_invalid_counts():
    module = _load_module()

    with pytest.raises(ValueError, match="non-negative"):
        module._validate_count(-1, "previous-count")
    with pytest.raises(ValueError, match="safety bound"):
        module._validate_count(module.MAX_NATIVE_CANARY_COUNT + 1, "previous-count")


def test_payload_cache_producer_state_issue_candidate_hash_topk_semantics():
    module = _load_module()

    assert module._issue_candidate_hash((2, 7, 9), 0) == 0x733CF4903B9B8F3A
    assert module._issue_candidate_hash((2, 7, 9), 2) == 0xEA95D41875D6802C
    assert module._issue_candidate_hash((2, 7, 9), 3) == 0x733CF4903B9B8F3A
    assert module._issue_candidate_bounds((2, 7, 9), 0) == (3, 2, 9)
    assert module._issue_candidate_bounds((2, 7, 9), 2) == (2, 2, 7)
    assert module._issue_candidate_bounds((), 8) == (0, -1, -1)


def test_payload_cache_producer_state_stub_returns_structured_failure(monkeypatch, tmp_path: Path):
    module = _load_module()

    monkeypatch.setattr(module, "build", lambda **_: tmp_path / "stub")

    def fake_run_cmd(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["stub"],
            returncode=7,
            stdout="not-json",
            stderr="boom",
        )

    monkeypatch.setattr(module, "run_cmd", fake_run_cmd)
    payload = module.run_stub(
        argparse.Namespace(
            device=0,
            previous_count=1,
            current_count=1,
            transition_topk_count=1,
            current_offset=0,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices=None,
        )
    )

    assert payload["ok"] is False
    assert payload["passed"] is False
    assert payload["native_returncode"] == 7
    assert payload["failures"] == ["native_json_parse_error"]
    assert payload["stderr"] == "boom"


def test_payload_cache_producer_state_stub_returns_structured_root_type_failure(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()

    monkeypatch.setattr(module, "build", lambda **_: tmp_path / "stub")

    def fake_run_cmd(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["stub"],
            returncode=0,
            stdout="[1, 2, 3]",
            stderr="",
        )

    monkeypatch.setattr(module, "run_cmd", fake_run_cmd)
    payload = module.run_stub(
        argparse.Namespace(
            device=0,
            previous_count=1,
            current_count=1,
            transition_topk_count=1,
            current_offset=0,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices=None,
        )
    )

    assert payload["ok"] is False
    assert payload["passed"] is False
    assert payload["native_returncode"] == 0
    assert payload["failures"] == ["native_json_root_type_error"]
    assert payload["native_json_root_type"] == "list"
    assert payload["native_stdout"] == "[1, 2, 3]"


def test_payload_cache_producer_state_stub_accepts_semantic_packet_json(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=1,
        previous_experts=(7, 2, 7),
        current_experts=(4, 2),
        state_owner="producer",
        transition_topk_count=4,
        max_num_experts=8,
    )
    packet_json = tmp_path / "packet.json"
    packet_json.write_text(module.json.dumps(packet.as_dict()), encoding="utf-8")

    monkeypatch.setattr(module, "build", lambda **_: tmp_path / "stub")
    captured: dict[str, list[str]] = {}

    def fake_run_cmd(cmd, **_kwargs):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout='{"ok":true,"passed":true}',
            stderr="",
        )

    monkeypatch.setattr(module, "run_cmd", fake_run_cmd)
    payload = module.run_stub(
        argparse.Namespace(
            device=0,
            previous_count=1,
            current_count=1,
            transition_topk_count=1,
            current_offset=0,
            packet_json=packet_json,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices=None,
        )
    )

    assert payload["input_source"] == "semantic_packet_json"
    assert payload["packet_ready"] is True
    assert payload["requested_previous_count"] == 2
    assert payload["requested_current_count"] == 2
    assert payload["requested_layer_id"] == 1
    assert payload["requested_state_hash"] == packet.state_hash[:16]
    assert payload["packet_state_hash_u64"] == packet.state_hash[:16]
    assert payload["expected_issue_candidate_count"] == 2
    assert payload["expected_issue_candidate_first_expert"] == 2
    assert payload["expected_issue_candidate_last_expert"] == 7
    assert payload["expected_issue_candidate_hash"] == (
        f"{module._issue_candidate_hash((2, 7), 4):016x}"
    )
    assert "--layer-id" in captured["cmd"]
    assert "1" in captured["cmd"]
    assert "--state-hash" in captured["cmd"]
    assert str(int(packet.state_hash[:16], 16)) in captured["cmd"]
    assert "--previous-experts" in captured["cmd"]
    assert "2,7" in captured["cmd"]
    assert "--current-experts" in captured["cmd"]
    assert "2,4" in captured["cmd"]


def test_payload_cache_producer_state_stub_returns_structured_packet_json_failure(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    packet_json = tmp_path / "bad_packet.json"
    packet_json.write_text('{"ready": false}', encoding="utf-8")

    monkeypatch.setattr(module, "build", lambda **_: tmp_path / "stub")
    payload = module.run_stub(
        argparse.Namespace(
            device=0,
            previous_count=1,
            current_count=1,
            transition_topk_count=1,
            current_offset=0,
            packet_json=packet_json,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices=None,
        )
    )

    assert payload["ok"] is False
    assert payload["passed"] is False
    assert payload["native_returncode"] is None
    assert payload["failures"] == ["packet_json_error"]
    assert payload["packet_json"] == str(packet_json)
