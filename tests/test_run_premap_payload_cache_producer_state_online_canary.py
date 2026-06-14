from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_premap_payload_cache_producer_state_online_canary.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_premap_payload_cache_producer_state_online_canary",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeStubRunner:
    def __init__(self) -> None:
        self.args = None

    def run_stub(self, args):
        self.args = args
        return {
            "ok": True,
            "passed": True,
            "packet_json": str(args.packet_json),
            "input_source": "semantic_packet_json",
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "native_stub_invoked": True,
        }


def test_online_canary_selects_packet_from_performance_summary(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    packets_dir = tmp_path / "packets"
    packets_dir.mkdir()
    packet0 = packets_dir / "packet0.json"
    packet1 = packets_dir / "packet1.json"
    packet0.write_text('{"ready": true}\n', encoding="utf-8")
    packet1.write_text('{"ready": true}\n', encoding="utf-8")
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": True,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 2,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths": [
                    str(packet0.relative_to(tmp_path)),
                    str(packet1.relative_to(tmp_path)),
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    fake = _FakeStubRunner()
    monkeypatch.setattr(module, "_load_stub_runner", lambda: fake)

    payload = module.run_online_canary(
        argparse.Namespace(
            performance_summary=performance_summary,
            packet_json=None,
            packet_index=1,
            device=1,
            current_offset=0,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices="1",
        )
    )

    assert payload["ok"] is True
    assert payload["selected_packet_json"] == str(packet1)
    assert payload["online_packet_export_count"] == 2
    assert payload["online_configured_export_enabled"] is True
    assert payload["online_configured_export_count"] == 2
    assert fake.args.device == 1
    assert fake.args.hip_visible_devices == "1"
    assert fake.args.packet_json == packet1


def test_online_canary_prefers_nonempty_issue_packet(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    packets_dir = tmp_path / "packets"
    packets_dir.mkdir()
    packet0 = packets_dir / "packet0.json"
    packet1 = packets_dir / "packet1.json"
    packet0.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [],
                "transition_topk_count": 8,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    packet1.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [3, 5],
                "transition_topk_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": True,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 2,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths": [
                    str(packet0.relative_to(tmp_path)),
                    str(packet1.relative_to(tmp_path)),
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    fake = _FakeStubRunner()
    monkeypatch.setattr(module, "_load_stub_runner", lambda: fake)

    payload = module.run_online_canary(
        argparse.Namespace(
            performance_summary=performance_summary,
            packet_json=None,
            packet_index=0,
            prefer_nonempty_issue=True,
            require_nonempty_issue=True,
            device=0,
            current_offset=0,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices=None,
        )
    )

    assert payload["ok"] is True
    assert payload["selected_packet_index"] == 1
    assert payload["selected_packet_json"] == str(packet1)
    assert payload["selected_packet_selection_mode"] == "first_nonempty_issue"
    assert fake.args.packet_json == packet1


def test_online_canary_prefers_summary_nonempty_issue_packet(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    packets_dir = tmp_path / "packets"
    packets_dir.mkdir()
    packet0 = packets_dir / "packet0.json"
    packet1 = packets_dir / "packet1.json"
    packet0.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [],
                "transition_topk_count": 8,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    packet1.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [3, 5],
                "transition_topk_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": True,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 2,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths": [
                    str(packet0.relative_to(tmp_path)),
                    str(packet1.relative_to(tmp_path)),
                ],
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_nonempty_issue_count": 1,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_index": 1,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_path": str(
                    packet1.relative_to(tmp_path)
                ),
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_count": 1,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_hash": "083a5007b4f20f1b",
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_scan_error_count": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    fake = _FakeStubRunner()
    monkeypatch.setattr(module, "_load_stub_runner", lambda: fake)

    payload = module.run_online_canary(
        argparse.Namespace(
            performance_summary=performance_summary,
            packet_json=None,
            packet_index=0,
            prefer_nonempty_issue=True,
            require_nonempty_issue=True,
            device=0,
            current_offset=0,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices=None,
        )
    )

    assert payload["ok"] is True
    assert payload["selected_packet_index"] == 1
    assert payload["selected_packet_json"] == str(packet1)
    assert payload["selected_packet_selection_mode"] == "summary_first_nonempty_issue"
    assert fake.args.packet_json == packet1


def test_online_canary_require_nonempty_honors_summary_zero(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    packet.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [3],
                "transition_topk_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": True,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 1,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths": [
                    str(packet.relative_to(tmp_path)),
                ],
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_nonempty_issue_count": 0,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_index": -1,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_path": None,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_count": 0,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_hash": None,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_scan_error_count": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        module.run_online_canary(
            argparse.Namespace(
                performance_summary=performance_summary,
                packet_json=None,
                packet_index=0,
                prefer_nonempty_issue=True,
                require_nonempty_issue=True,
                device=0,
                current_offset=0,
                offload_arch="gfx1100",
                force_build=False,
                hip_visible_devices=None,
            )
        )
    except ValueError as exc:
        assert "does not contain a nonempty producer-state issue packet" in str(exc)
    else:
        raise AssertionError("expected summary-zero nonempty issue to raise ValueError")


def test_online_canary_rejects_nonempty_summary_with_scan_errors(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    packet.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [3],
                "transition_topk_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": True,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 1,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths": [
                    str(packet.relative_to(tmp_path)),
                ],
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_nonempty_issue_count": 0,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_index": -1,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_path": None,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_count": 0,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_hash": None,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_scan_error_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        module.run_online_canary(
            argparse.Namespace(
                performance_summary=performance_summary,
                packet_json=None,
                packet_index=0,
                prefer_nonempty_issue=True,
                require_nonempty_issue=True,
                device=0,
                current_offset=0,
                offload_arch="gfx1100",
                force_build=False,
                hip_visible_devices=None,
            )
        )
    except ValueError as exc:
        assert "scan had errors" in str(exc)
    else:
        raise AssertionError("expected scan-error nonempty summary to raise ValueError")


def test_online_canary_requires_nonempty_issue_packet(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    packet.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [],
                "transition_topk_count": 8,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": True,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 1,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths": [
                    str(packet.relative_to(tmp_path)),
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        module.run_online_canary(
            argparse.Namespace(
                performance_summary=performance_summary,
                packet_json=None,
                packet_index=0,
                prefer_nonempty_issue=False,
                require_nonempty_issue=True,
                device=0,
                current_offset=0,
                offload_arch="gfx1100",
                force_build=False,
                hip_visible_devices=None,
            )
        )
    except ValueError as exc:
        assert "does not contain a nonempty producer-state issue packet" in str(exc)
    else:
        raise AssertionError("expected missing nonempty issue packet to raise ValueError")


def test_online_canary_nonempty_selection_rejects_missing_packet_path(tmp_path: Path):
    module = _load_module()
    missing = tmp_path / "missing.json"
    packet = tmp_path / "packet.json"
    packet.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [3],
                "transition_topk_count": 8,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": True,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 2,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths": [
                    str(missing.relative_to(tmp_path)),
                    str(packet.relative_to(tmp_path)),
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        module.run_online_canary(
            argparse.Namespace(
                performance_summary=performance_summary,
                packet_json=None,
                packet_index=0,
                prefer_nonempty_issue=True,
                require_nonempty_issue=True,
                device=0,
                current_offset=0,
                offload_arch="gfx1100",
                force_build=False,
                hip_visible_devices=None,
            )
        )
    except ValueError as exc:
        assert "producer-state packet export path missing" in str(exc)
    else:
        raise AssertionError("expected missing packet path to raise ValueError")


def test_online_canary_accepts_explicit_packet_json(monkeypatch, tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    packet.write_text('{"ready": true}\n', encoding="utf-8")
    fake = _FakeStubRunner()
    monkeypatch.setattr(module, "_load_stub_runner", lambda: fake)

    payload = module.run_online_canary(
        argparse.Namespace(
            performance_summary=None,
            packet_json=packet,
            packet_index=0,
            device=0,
            current_offset=0,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices=None,
        )
    )

    assert payload["ok"] is True
    assert payload["selected_packet_json"] == str(packet)
    assert payload["online_performance_summary"] is None
    assert payload["online_packet_export_paths"] == [str(packet)]
    assert fake.args.packet_json == packet


def test_online_canary_accepts_explicit_nonempty_issue_packet_json(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    packet.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [1, 7],
                "transition_topk_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    fake = _FakeStubRunner()
    monkeypatch.setattr(module, "_load_stub_runner", lambda: fake)

    payload = module.run_online_canary(
        argparse.Namespace(
            performance_summary=None,
            packet_json=packet,
            packet_index=0,
            prefer_nonempty_issue=False,
            require_nonempty_issue=True,
            device=0,
            current_offset=0,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices=None,
        )
    )

    assert payload["ok"] is True
    assert payload["selected_packet_json"] == str(packet)
    assert payload["selected_packet_selection_mode"] == (
        "explicit_packet_json_nonempty_issue"
    )
    assert fake.args.packet_json == packet


def test_online_canary_rejects_explicit_empty_issue_packet_json(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    packet.write_text(
        json.dumps(
            {
                "ready": True,
                "previous_experts": [],
                "transition_topk_count": 8,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        module.run_online_canary(
            argparse.Namespace(
                performance_summary=None,
                packet_json=packet,
                packet_index=0,
                prefer_nonempty_issue=False,
                require_nonempty_issue=True,
                device=0,
                current_offset=0,
                offload_arch="gfx1100",
                force_build=False,
                hip_visible_devices=None,
            )
        )
    except ValueError as exc:
        assert "does not contain a nonempty issue prefix" in str(exc)
    else:
        raise AssertionError("expected empty explicit issue packet to raise ValueError")


def test_online_canary_reports_missing_packet(tmp_path: Path):
    module = _load_module()
    missing = tmp_path / "missing.json"

    payload = module.run_online_canary(
        argparse.Namespace(
            performance_summary=None,
            packet_json=missing,
            packet_index=0,
            device=0,
            current_offset=0,
            offload_arch="gfx1100",
            force_build=False,
            hip_visible_devices=None,
        )
    )

    assert payload["ok"] is False
    assert payload["passed"] is False
    assert payload["failures"] == ["packet_json_missing"]
    assert payload["packet_json"] == str(missing)


def test_online_canary_rejects_summary_without_packet_paths(tmp_path: Path):
    module = _load_module()
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": True,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        module.run_online_canary(
            argparse.Namespace(
                performance_summary=performance_summary,
                packet_json=None,
                packet_index=0,
                device=0,
                current_offset=0,
                offload_arch="gfx1100",
                force_build=False,
                hip_visible_devices=None,
            )
        )
    except ValueError as exc:
        assert "does not contain producer-state packet export paths" in str(exc)
    else:
        raise AssertionError("expected missing packet paths to raise ValueError")


def test_online_canary_rejects_summary_with_disabled_export(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    packet.write_text('{"ready": true}\n', encoding="utf-8")
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": False,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 1,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths": [
                    str(packet)
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        module.run_online_canary(
            argparse.Namespace(
                performance_summary=performance_summary,
                packet_json=None,
                packet_index=0,
                device=0,
                current_offset=0,
                offload_arch="gfx1100",
                force_build=False,
                hip_visible_devices=None,
            )
        )
    except ValueError as exc:
        assert "producer-state packet export is not enabled" in str(exc)
    else:
        raise AssertionError("expected disabled export summary to raise ValueError")


def test_online_canary_rejects_summary_with_zero_export_count(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    packet.write_text('{"ready": true}\n', encoding="utf-8")
    performance_summary = tmp_path / "performance_summary.json"
    performance_summary.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": True,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_count": 0,
                "runtime_shadow_premap_payload_cache_producer_state_packet_export_paths": [
                    str(packet)
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        module.run_online_canary(
            argparse.Namespace(
                performance_summary=performance_summary,
                packet_json=None,
                packet_index=0,
                device=0,
                current_offset=0,
                offload_arch="gfx1100",
                force_build=False,
                hip_visible_devices=None,
            )
        )
    except ValueError as exc:
        assert "producer-state packet export count is zero" in str(exc)
    else:
        raise AssertionError("expected zero export count summary to raise ValueError")
