from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_premap_payload_cache_issue_plan_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_premap_payload_cache_issue_plan_gate",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _issue_hash(module, experts: tuple[int, ...]) -> str:
    return module._issue_hash(experts)  # noqa: SLF001


def _packet_payload(*, previous=(3, 5), topk=1) -> dict:
    return {
        "ready": True,
        "layer_id": 7,
        "previous_experts": list(previous),
        "current_experts": [11],
        "transition_topk_count": topk,
    }


def _online_payload(module, packet_path: Path, *, issue_hash: str | None = None) -> dict:
    expected_hash = issue_hash or _issue_hash(module, (3,))
    return {
        "ok": True,
        "passed": True,
        "ready": True,
        "failures": [],
        "native_returncode": 0,
        "native_stub_invoked": True,
        "input_source": "semantic_packet_json",
        "online_export_source": (
            "runtime_shadow_premap_payload_cache_producer_state_packet_export"
        ),
        "selected_packet_selection_mode": "first_nonempty_issue",
        "selected_packet_index": 0,
        "selected_packet_json": str(packet_path),
        "online_packet_export_count": 2,
        "online_packet_export_paths": [str(packet_path)],
        "online_configured_export_count": 2,
        "layer_id": 7,
        "state_hash": "abc",
        "packet_state_hash": "abc" * 21 + "a",
        "issue_candidate_count": 1,
        "issue_candidate_first_expert": 3,
        "issue_candidate_last_expert": 3,
        "issue_candidate_hash": expected_hash,
        "expected_issue_candidate_hash": expected_hash,
        "payload_bytes": 0,
        "ready_credit": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
    }


def _run(module, online_path: Path, output_path: Path) -> dict:
    args = module.build_parser().parse_args(
        [
            "--online-canary-json",
            str(online_path),
            "--output-json",
            str(output_path),
        ]
    )
    return module.build_issue_plan_gate(args)


def test_issue_plan_gate_accepts_native_packet_match(tmp_path: Path):
    module = _load_module()
    packet_path = tmp_path / "packet.json"
    online_path = tmp_path / "online.json"
    _write_json(packet_path, _packet_payload())
    _write_json(online_path, _online_payload(module, packet_path))

    result = _run(module, online_path, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["issue_plan_ready"] is True
    assert result["payload_cache_issue_plan_candidate"] is True
    assert result["native_issue_plan_valid"] is True
    assert result["issue_candidate_count"] == 1
    assert result["issue_candidate_first_expert"] == 3
    assert result["issue_candidate_last_expert"] == 3
    assert result["issue_candidate_hash"] == _issue_hash(module, (3,))
    assert result["issue_candidate_experts"] == [3]
    assert result["payload_bytes"] == 0
    assert result["ready_credit"] is False
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["measures_tpot"] is False
    assert result["next_runtime_stage"] == "implement_payload_cache_manager_issue_executor"
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))[
        "passed"
    ] is True


def test_issue_plan_gate_rejects_native_hash_mismatch(tmp_path: Path):
    module = _load_module()
    packet_path = tmp_path / "packet.json"
    online_path = tmp_path / "online.json"
    _write_json(packet_path, _packet_payload())
    online = _online_payload(module, packet_path)
    online["issue_candidate_hash"] = "0000000000000000"
    _write_json(online_path, online)

    result = _run(module, online_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "native_issue_candidate_hash_packet_mismatch" in result["failures"]
    assert result["issue_plan_ready"] is False


def test_issue_plan_gate_rejects_payload_or_kernel_mutation(tmp_path: Path):
    module = _load_module()
    packet_path = tmp_path / "packet.json"
    online_path = tmp_path / "online.json"
    _write_json(packet_path, _packet_payload())
    online = _online_payload(module, packet_path)
    online["payload_bytes"] = 16
    online["passed_to_kernel"] = True
    _write_json(online_path, online)

    result = _run(module, online_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "payload_bytes_not_zero" in result["failures"]
    assert "passed_to_kernel_not_false" in result["failures"]


def test_issue_plan_gate_rejects_unsafe_packet_boundary(tmp_path: Path):
    module = _load_module()
    packet_path = tmp_path / "packet.json"
    online_path = tmp_path / "online.json"
    packet = _packet_payload()
    packet["payload_bytes"] = 16
    packet["changes_kernel_launch_args"] = True
    _write_json(packet_path, packet)
    _write_json(online_path, _online_payload(module, packet_path))

    result = _run(module, online_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "packet_payload_bytes_not_zero" in result["failures"]
    assert "packet_changes_kernel_launch_args_not_false" in result["failures"]


def test_issue_plan_gate_requires_native_first_last(tmp_path: Path):
    module = _load_module()
    packet_path = tmp_path / "packet.json"
    online_path = tmp_path / "online.json"
    _write_json(packet_path, _packet_payload())
    online = _online_payload(module, packet_path)
    online.pop("issue_candidate_first_expert")
    online.pop("issue_candidate_last_expert")
    _write_json(online_path, online)

    result = _run(module, online_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "native_issue_candidate_first_expert_missing" in result["failures"]
    assert "native_issue_candidate_last_expert_missing" in result["failures"]


def test_issue_plan_gate_rejects_selected_packet_provenance_mismatch(tmp_path: Path):
    module = _load_module()
    packet_path = tmp_path / "packet.json"
    other_path = tmp_path / "other.json"
    online_path = tmp_path / "online.json"
    _write_json(packet_path, _packet_payload())
    _write_json(other_path, _packet_payload(previous=(9,), topk=1))
    online = _online_payload(module, packet_path)
    online["online_packet_export_paths"] = [str(other_path)]
    _write_json(online_path, online)

    result = _run(module, online_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "selected_packet_not_in_online_export_paths" in result["failures"]
    assert "selected_packet_index_path_mismatch" in result["failures"]


def test_issue_plan_gate_rejects_empty_issue_by_default(tmp_path: Path):
    module = _load_module()
    packet_path = tmp_path / "packet.json"
    online_path = tmp_path / "online.json"
    _write_json(packet_path, _packet_payload(previous=(), topk=8))
    online = _online_payload(module, packet_path, issue_hash=_issue_hash(module, ()))
    online["issue_candidate_count"] = 0
    online["issue_candidate_first_expert"] = -1
    online["issue_candidate_last_expert"] = -1
    _write_json(online_path, online)

    result = _run(module, online_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "issue_candidate_count_not_positive" in result["failures"]


def test_issue_plan_gate_rejects_unknown_selection_mode(tmp_path: Path):
    module = _load_module()
    packet_path = tmp_path / "packet.json"
    online_path = tmp_path / "online.json"
    _write_json(packet_path, _packet_payload())
    online = _online_payload(module, packet_path)
    online["selected_packet_selection_mode"] = "packet_index"
    _write_json(online_path, online)

    result = _run(module, online_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "selected_packet_selection_mode_not_nonempty" in result["failures"]
