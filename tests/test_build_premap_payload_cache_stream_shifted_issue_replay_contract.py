from __future__ import annotations

import importlib.util
import json
from pathlib import Path


FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
U64_MASK = 0xFFFFFFFFFFFFFFFF


def _issue_hash(experts: list[int]) -> str:
    value = FNV_OFFSET
    count = 0
    for expert_id in experts:
        value ^= int(expert_id) & 0xFFFFFFFF
        value = (value * FNV_PRIME) & U64_MASK
        count += 1
    value ^= count & 0xFFFFFFFF
    value = (value * FNV_PRIME) & U64_MASK
    return f"{value:016x}"


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_premap_payload_cache_stream_shifted_issue_replay_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_premap_payload_cache_stream_shifted_issue_replay_contract",
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


def _safe_fields() -> dict:
    return {
        "full_fetch_runtime_allowed": False,
        "full_fetch_allowed": False,
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "wna16_benchmark_ready": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def _packet(
    *,
    token_index: int,
    layer_id: int = 0,
    count: int = 2,
    sample_idx: int | None = 0,
    record_id: str | None = "rec-0",
    source: str = "decode_workload_collector",
) -> dict:
    experts = [3, 5][:count]
    first_expert = experts[0] if experts else -1
    last_expert = experts[-1] if experts else -1
    issue_hash = _issue_hash(experts)
    context = {
        **_safe_fields(),
        "token_index": token_index,
        "token_index_source": source,
        "sample_idx": sample_idx,
        "record_id": record_id,
        "sequence_id": 0,
        "layer_id": layer_id,
        "issue_candidate_count": len(experts),
        "issue_candidate_first_expert": first_expert,
        "issue_candidate_last_expert": last_expert,
        "issue_candidate_hash": issue_hash,
    }
    return {
        **_safe_fields(),
        "ready": True,
        "layer_id": layer_id,
        "issue_candidate_count": len(experts),
        "issue_candidate_first_expert": first_expert,
        "issue_candidate_last_expert": last_expert,
        "issue_candidate_hash": issue_hash,
        "issue_candidate_experts": experts,
        "_export_context": context,
    }


def _online(paths: list[Path]) -> dict:
    return {
        **_safe_fields(),
        "ok": True,
        "passed": True,
        "ready": True,
        "failures": [],
        "online_export_source": (
            "runtime_shadow_premap_payload_cache_producer_state_packet_export"
        ),
        "online_packet_export_count": len(paths),
        "online_configured_export_count": len(paths),
        "online_packet_export_paths": [str(path) for path in paths],
    }


def _run(module, online: Path, output: Path, extra_args: list[str] | None = None):
    args_list = [
        "--online-canary-json",
        str(online),
        "--output-json",
        str(output),
    ]
    if extra_args:
        args_list.extend(extra_args)
    args = module.build_parser().parse_args(args_list)
    return module.build_shifted_issue_replay_contract(args)


def test_shifted_issue_replay_contract_builds_lead_schedule(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    online = tmp_path / "online.json"
    _write_json(packet0, _packet(token_index=8, layer_id=0, count=2))
    _write_json(packet1, _packet(token_index=9, layer_id=1, count=1))
    _write_json(online, _online([packet0, packet1]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        ["--issue-lead-tokens", "1", "--min-schedulable-packet-count", "2"],
    )

    assert result["passed"] is True
    assert result["issue_lead_tokens"] == 1
    assert result["schedulable_packet_count"] == 2
    assert result["total_issue_candidates"] == 3
    assert result["rows"][0]["demand_token_index"] == 8
    assert result["rows"][0]["issue_token_index"] == 7
    assert result["rows"][1]["issue_token_index"] == 8
    assert result["payload_transfer_enabled"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["measures_tpot"] is False
    assert json.loads((tmp_path / "out.json").read_text())["passed"] is True


def test_shifted_issue_replay_contract_allows_empty_config_exemption(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    online = tmp_path / "online.json"
    _write_json(
        packet0,
        _packet(token_index=-1, count=0, sample_idx=None, record_id=None, source="config"),
    )
    _write_json(packet1, _packet(token_index=8, count=1))
    _write_json(online, _online([packet0, packet1]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        ["--allow-empty-config-packets"],
    )

    assert result["passed"] is True
    assert result["empty_issue_exempt_count"] == 1
    assert result["schedulable_packet_count"] == 1
    assert len(result["rows"]) == 1


def test_shifted_issue_replay_contract_rejects_bool_payload_bytes(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet(token_index=8)
    packet["payload_bytes"] = False
    packet["_export_context"]["payload_bytes"] = False
    online_payload = _online([packet0])
    online_payload["payload_bytes"] = False
    _write_json(packet0, packet)
    _write_json(online, online_payload)

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "online_payload_bytes_not_zero" in result["failures"]
    assert "packet_0_payload_bytes_not_zero" in result["failures"]
    assert "packet_0_export_context_payload_bytes_not_zero" in result["failures"]
    assert result["payload_bytes"] == 0


def test_shifted_issue_replay_contract_rejects_optional_full_fetch_source_flag(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet(token_index=8)
    packet["full_fetch_allowed"] = True
    packet["_export_context"]["full_fetch_runtime_allowed"] = True
    online_payload = _online([packet0])
    online_payload["full_fetch_allowed"] = True
    _write_json(packet0, packet)
    _write_json(online, online_payload)

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "online_full_fetch_allowed_not_false" in result["failures"]
    assert "packet_0_full_fetch_allowed_not_false" in result["failures"]
    assert (
        "packet_0_export_context_full_fetch_runtime_allowed_not_false"
        in result["failures"]
    )


def test_shifted_issue_replay_contract_rejects_optional_wna16_source_flag(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet(token_index=8)
    packet["current_wna16_arg_compatible"] = True
    packet["_export_context"]["requires_wna16_arg_reinterpretation"] = True
    online_payload = _online([packet0])
    online_payload["wna16_benchmark_ready"] = True
    _write_json(packet0, packet)
    _write_json(online, online_payload)

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "online_wna16_benchmark_ready_not_false" in result["failures"]
    assert "packet_0_current_wna16_arg_compatible_not_false" in result["failures"]
    assert (
        "packet_0_export_context_requires_wna16_arg_reinterpretation_not_false"
        in result["failures"]
    )


def test_shifted_issue_replay_contract_rejects_issue_candidate_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet(token_index=8)
    packet["issue_candidate_count"] = 99
    packet["_export_context"]["issue_candidate_hash"] = "bad"
    _write_json(packet0, packet)
    _write_json(online, _online([packet0]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "packet_0_issue_candidate_count_mismatch" in result["failures"]
    assert "packet_0_export_context_issue_candidate_hash_mismatch" in result[
        "failures"
    ]


def test_shifted_issue_replay_contract_rejects_unknown_token_source_even_when_config_allowed(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    _write_json(packet0, _packet(token_index=8, source="manual"))
    _write_json(online, _online([packet0]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        ["--allow-config-token-source"],
    )

    assert result["passed"] is False
    assert "packet_0_token_index_source_unexpected" in result["failures"]


def test_shifted_issue_replay_contract_rejects_configured_count_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    _write_json(packet0, _packet(token_index=8))
    online_payload = _online([packet0])
    online_payload["online_configured_export_count"] = 2
    _write_json(online, online_payload)

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "online_configured_export_count_mismatch" in result["failures"]


def test_shifted_issue_replay_contract_rejects_context_layer_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet(token_index=8, layer_id=3)
    packet["_export_context"]["layer_id"] = 4
    _write_json(packet0, packet)
    _write_json(online, _online([packet0]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "packet_0_export_context_layer_id_mismatch" in result["failures"]


def test_shifted_issue_replay_contract_rejects_empty_unknown_source_by_default(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    _write_json(
        packet0,
        _packet(
            token_index=-1,
            count=0,
            sample_idx=None,
            record_id=None,
            source="manual",
        ),
    )
    _write_json(online, _online([packet0]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "packet_0_empty_issue_source_not_config" in result["failures"]


def test_shifted_issue_replay_contract_rejects_clamped_issue_by_default(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    _write_json(packet0, _packet(token_index=0))
    _write_json(online, _online([packet0]))

    result = _run(module, online, tmp_path / "out.json", ["--issue-lead-tokens", "1"])

    assert result["passed"] is False
    assert "clamped_issue_tokens_present" in result["failures"]
    assert result["clamped_issue_count"] == 1
    assert result["rows"][0]["issue_token_index"] == 0


def test_shifted_issue_replay_contract_rejects_duplicate_issue_keys_by_default(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    online = tmp_path / "online.json"
    _write_json(packet0, _packet(token_index=8, layer_id=0))
    _write_json(packet1, _packet(token_index=8, layer_id=0))
    _write_json(online, _online([packet0, packet1]))

    result = _run(module, online, tmp_path / "out.json", ["--issue-lead-tokens", "1"])

    assert result["passed"] is False
    assert "duplicate_demand_keys_present" in result["failures"]
    assert "duplicate_issue_keys_present" in result["failures"]
