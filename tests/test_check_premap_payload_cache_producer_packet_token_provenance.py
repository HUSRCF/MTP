from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "check_premap_payload_cache_producer_packet_token_provenance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_premap_payload_cache_producer_packet_token_provenance",
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


def _safe_flags() -> dict:
    return {
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "real_ready_credit_granted": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def _packet(
    *,
    layer_id: int = 0,
    token_index: int = 3,
    token_source: str = "decode_workload_collector",
    issue_count: int = 1,
    sample_idx: int | None = 5,
    record_id: str | None = "rec-5",
) -> dict:
    issue_candidates = list(range(issue_count))
    payload = {
        **_safe_flags(),
        "ready": True,
        "layer_id": layer_id,
        "previous_experts": issue_candidates,
        "current_experts": [7],
        "transition_topk_count": issue_count,
        "issue_candidate_experts": issue_candidates,
        "issue_candidate_count": issue_count,
        "issue_candidate_first_expert": issue_candidates[0] if issue_candidates else -1,
        "issue_candidate_last_expert": issue_candidates[-1] if issue_candidates else -1,
        "issue_candidate_hash": "unused-by-token-provenance-gate",
    }
    payload["_export_context"] = {
        **_safe_flags(),
        "source": "vllm_prelaunch_payload_cache_producer_transition_state_packet",
        "request_id": f"sample_{sample_idx}",
        "sequence_id": 0,
        "token_index": token_index,
        "token_index_source": token_source,
        "sample_idx": sample_idx,
        "record_id": record_id,
        "layer_id": layer_id,
        "export_index": 0,
        "ready": True,
        "issue_candidate_count": issue_count,
        "issue_candidate_first_expert": issue_candidates[0] if issue_candidates else -1,
        "issue_candidate_last_expert": issue_candidates[-1] if issue_candidates else -1,
        "issue_candidate_hash": "unused-by-token-provenance-gate",
    }
    return payload


def _online(packet_paths: list[Path], *, unsafe: bool = False) -> dict:
    payload = {
        **_safe_flags(),
        "ok": True,
        "passed": True,
        "ready": True,
        "failures": [],
        "online_export_source": (
            "runtime_shadow_premap_payload_cache_producer_state_packet_export"
        ),
        "online_packet_export_count": len(packet_paths),
        "online_packet_export_paths": [str(path) for path in packet_paths],
        "online_configured_export_count": len(packet_paths),
    }
    if unsafe:
        payload["payload_transfer_enabled"] = True
    return payload


def _run(
    module,
    online_path: Path,
    output_path: Path,
    extra_args: list[str] | None = None,
) -> dict:
    argv = [
        "--online-canary-json",
        str(online_path),
        "--output-json",
        str(output_path),
    ]
    if extra_args:
        argv.extend(extra_args)
    args = module.build_parser().parse_args(argv)
    return module.check_packet_token_provenance(args)


def test_packet_token_provenance_gate_accepts_decode_source_packets(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    online = tmp_path / "online.json"
    _write_json(packet0, _packet(layer_id=0, token_index=3, issue_count=2))
    _write_json(packet1, _packet(layer_id=1, token_index=4, issue_count=1))
    _write_json(online, _online([packet0, packet1]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--min-packet-count",
            "2",
            "--min-valid-token-count",
            "2",
        ],
    )

    assert result["passed"] is True
    assert result["packet_count"] == 2
    assert result["valid_token_count"] == 2
    assert result["decode_workload_source_count"] == 2
    assert result["token_index_min"] == 3
    assert result["token_index_max"] == 4
    assert result["token_span"] == 2
    assert result["layer_count"] == 2
    assert result["payload_transfer_enabled"] is False
    assert result["passed_to_kernel"] is False
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))[
        "passed"
    ] is True


def test_packet_token_provenance_gate_rejects_config_source_by_default(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    online = tmp_path / "online.json"
    _write_json(packet, _packet(token_source="config"))
    _write_json(online, _online([packet]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
    )

    assert result["passed"] is False
    assert "decode_workload_source_count_mismatch" in result["failures"]
    assert "config_token_source_present" in result["failures"]


def test_packet_token_provenance_gate_allows_config_source_only_in_audit_mode(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    online = tmp_path / "online.json"
    _write_json(packet, _packet(token_source="config"))
    _write_json(online, _online([packet]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        ["--allow-config-token-source"],
    )

    assert result["passed"] is True
    assert result["allow_config_token_source"] is True
    assert result["require_decode_workload_source"] is False


def test_packet_token_provenance_gate_rejects_unsafe_packet_context(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    online = tmp_path / "online.json"
    payload = _packet()
    payload["_export_context"]["passed_to_kernel"] = True
    _write_json(packet, payload)
    _write_json(online, _online([packet]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "packet_0_export_context_passed_to_kernel_not_false" in result["failures"]


def test_packet_token_provenance_gate_rejects_duplicate_token_layer(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    online = tmp_path / "online.json"
    _write_json(packet0, _packet(layer_id=0, token_index=3))
    _write_json(packet1, _packet(layer_id=0, token_index=3))
    _write_json(online, _online([packet0, packet1]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "duplicate_token_layer_keys_present" in result["failures"]
    assert result["duplicate_token_layer_count"] == 1


def test_packet_token_provenance_gate_allows_same_token_layer_across_samples(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    online = tmp_path / "online.json"
    _write_json(
        packet0,
        _packet(layer_id=0, token_index=3, sample_idx=5, record_id="rec-5"),
    )
    _write_json(
        packet1,
        _packet(layer_id=0, token_index=3, sample_idx=6, record_id="rec-6"),
    )
    _write_json(online, _online([packet0, packet1]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["duplicate_token_layer_count"] == 0
    assert result["sample_count"] == 2
    assert result["record_count"] == 2


def test_packet_token_provenance_gate_rejects_missing_sample_record_by_default(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    online = tmp_path / "online.json"
    _write_json(packet, _packet(sample_idx=None, record_id=None))
    _write_json(online, _online([packet]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "packet_0_sample_idx_invalid" in result["failures"]
    assert "packet_0_record_id_invalid" in result["failures"]
