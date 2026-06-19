from __future__ import annotations

import importlib.util
import json
from pathlib import Path

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
U64_MASK = 0xFFFFFFFFFFFFFFFF


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_premap_payload_cache_issue_stream_executor.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_premap_payload_cache_issue_stream_executor",
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


def _packet_payload(*, layer_id: int = 0, previous=(3, 5), topk: int = 8) -> dict:
    issue_candidates = list(dict.fromkeys(int(value) for value in previous if int(value) >= 0))
    limit = len(issue_candidates) if topk == 0 else min(len(issue_candidates), topk)
    issue_candidates = issue_candidates[:limit]
    return {
        "ready": True,
        "layer_id": layer_id,
        "previous_experts": list(previous),
        "current_experts": [11],
        "transition_topk_count": topk,
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
        "issue_candidate_experts": issue_candidates,
        "issue_candidate_count": len(issue_candidates),
        "issue_candidate_first_expert": issue_candidates[0] if issue_candidates else -1,
        "issue_candidate_last_expert": issue_candidates[-1] if issue_candidates else -1,
        "issue_candidate_hash": _issue_hash(issue_candidates),
    }


def _online_payload(packet_paths: list[Path], *, unsafe: bool = False) -> dict:
    payload = {
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
    if unsafe:
        payload["payload_transfer_enabled"] = True
    return payload


def _run(
    module,
    online_path: Path,
    output_path: Path,
    extra_args: list[str] | None = None,
):
    args_list = [
        "--online-canary-json",
        str(online_path),
        "--output-json",
        str(output_path),
    ]
    if extra_args:
        args_list.extend(extra_args)
    args = module.build_parser().parse_args(args_list)
    return module.run_issue_stream_executor(args)


def test_issue_stream_executor_accepts_multi_packet_ready_time_hits(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    online = tmp_path / "online.json"
    _write_json(packet0, _packet_payload(previous=(3, 5), topk=8))
    _write_json(packet1, _packet_payload(previous=(5, 7), topk=8))
    _write_json(online, _online_payload([packet0, packet1]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--queue-batch-size",
            "2",
            "--service-us-per-issue",
            "0",
            "--event-interval-us",
            "10",
            "--min-packet-count",
            "2",
            "--min-nonempty-packet-count",
            "2",
        ],
    )

    assert result["passed"] is True
    assert result["stream_executor_ready"] is True
    assert result["packet_count"] == 2
    assert result["nonempty_packet_count"] == 2
    assert result["requested_issue_count"] == 4
    assert result["issued_prefetch_count"] == 3
    assert result["dedup_issue_drop_count"] == 1
    assert result["demand_count"] == 4
    assert result["demand_hit_count"] == 4
    assert result["demand_hit_rate"] == 1.0
    assert result["used_per_issued_fetch"] == 1.0
    assert result["real_payload_ready_hit_count"] == 0
    assert result["payload_transfer_enabled"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))[
        "passed"
    ] is True


def test_issue_stream_executor_prefers_exported_issue_candidates(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet_payload(previous=(3, 5), topk=2)
    packet["issue_candidate_experts"] = [7]
    packet["issue_candidate_count"] = 1
    packet["issue_candidate_first_expert"] = 7
    packet["issue_candidate_last_expert"] = 7
    packet["issue_candidate_hash"] = _issue_hash([7])
    _write_json(packet0, packet)
    _write_json(online, _online_payload([packet0]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        ["--service-us-per-issue", "0"],
    )

    assert result["passed"] is True
    assert result["requested_issue_count"] == 1
    assert result["issued_prefetch_count"] == 1
    assert result["demand_count"] == 1


def test_issue_stream_executor_rejects_issue_provenance_mismatch(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet_payload(previous=(3, 5), topk=2)
    packet["issue_candidate_hash"] = "0000000000000000"
    _write_json(packet0, packet)
    _write_json(online, _online_payload([packet0]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "packet_0_issue_candidate_hash_mismatch" in result["failures"]


def test_issue_stream_executor_rejects_measured_copy_deadline_miss(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    measured_copy = tmp_path / "measured_copy.json"
    _write_json(packet0, _packet_payload(previous=tuple(range(8)), topk=8))
    _write_json(online, _online_payload([packet0]))
    _write_json(
        measured_copy,
        {
            "rows": [
                {
                    "direction": "h2d",
                    "pinned": True,
                    "experts": 8,
                    "p95_ms": 16.0,
                    "p95_gbps": 0.8,
                }
            ]
        },
    )

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--measured-copy-json",
            str(measured_copy),
            "--measured-copy-stat",
            "p95",
            "--measured-copy-experts",
            "8",
            "--measured-copy-pinned",
            "true",
            "--queue-deadline-us",
            "200",
        ],
    )

    assert result["passed"] is False
    assert result["measured_copy_model_enabled"] is True
    assert result["measured_copy_us_per_batch"] == 16000.0
    assert result["measured_copy_us_per_issue"] == 2000.0
    assert result["full_fetch_allowed"] is False
    assert result["full_fetch_block_reason"] == "measured_copy_stream_deadline_miss"
    assert "demand_hit_rate_below_threshold" in result["failures"]
    assert "ready_late_miss_rate_above_threshold" in result["failures"]


def test_issue_stream_executor_rejects_payload_or_kernel_mutation(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet_payload(previous=(3,), topk=1)
    packet["passed_to_kernel"] = True
    _write_json(packet0, packet)
    _write_json(online, _online_payload([packet0], unsafe=True))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "online_payload_transfer_enabled_not_false" in result["failures"]
    assert "packet_0_passed_to_kernel_not_false" in result["failures"]
    assert result["payload_bytes"] == 0
    assert result["changes_kernel_launch_args"] is False


def test_issue_stream_executor_rejects_real_ready_credit_granted(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet_payload(previous=(3,), topk=1)
    packet["real_ready_credit_granted"] = True
    _write_json(packet0, packet)
    _write_json(online, _online_payload([packet0]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "packet_0_real_ready_credit_granted_not_false" in result["failures"]
    assert result["real_payload_ready_hit_count"] == 0
    assert result["real_ready_credit_granted"] is False


def test_issue_stream_executor_rejects_export_context_issue_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet_payload(previous=(3,), topk=1)
    packet["_export_context"] = {
        key: packet[key]
        for key in (
            "payload_bytes",
            "ready_credit",
            "ready_before_demand_credit",
            "payload_transfer_enabled",
            "payload_deref_allowed",
            "kernel_arg_pass_allowed",
            "real_ready_credit_granted",
            "passed_to_kernel",
            "changes_kernel_launch_args",
            "uses_current_wna16_args",
            "passes_current_wna16_args",
            "measures_tpot",
            "measures_vllm_latency",
            "issue_candidate_count",
            "issue_candidate_first_expert",
            "issue_candidate_last_expert",
            "issue_candidate_hash",
        )
    }
    packet["_export_context"]["issue_candidate_count"] = 2
    _write_json(packet0, packet)
    _write_json(online, _online_payload([packet0]))

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert (
        "packet_0_export_context_issue_candidate_count_mismatch"
        in result["failures"]
    )


def test_issue_stream_executor_rejects_missing_noop_contract_fields(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet_payload(previous=(3,), topk=1)
    packet.pop("payload_transfer_enabled")
    online_payload = _online_payload([packet0])
    online_payload.pop("kernel_arg_pass_allowed")
    _write_json(packet0, packet)
    _write_json(online, online_payload)

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "online_kernel_arg_pass_allowed_missing" in result["failures"]
    assert "packet_0_payload_transfer_enabled_missing" in result["failures"]


def test_issue_stream_executor_rejects_packet_export_count_mismatch(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    _write_json(packet0, _packet_payload(previous=(3,), topk=1))
    online_payload = _online_payload([packet0])
    online_payload["online_packet_export_count"] = 2
    _write_json(online, online_payload)

    result = _run(module, online, tmp_path / "out.json")

    assert result["passed"] is False
    assert "online_packet_export_paths_count_mismatch" in result["failures"]
    assert "online_configured_export_count_mismatch" in result["failures"]
    assert "packet_count_online_export_count_mismatch" in result["failures"]


def test_issue_stream_executor_rejects_measured_copy_issue_width_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    measured_copy = tmp_path / "measured_copy.json"
    _write_json(packet0, _packet_payload(previous=tuple(range(8)), topk=8))
    _write_json(online, _online_payload([packet0]))
    _write_json(
        measured_copy,
        {
            "rows": [
                {
                    "direction": "h2d",
                    "pinned": True,
                    "experts": 4,
                    "p95_ms": 8.0,
                }
            ]
        },
    )

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--measured-copy-json",
            str(measured_copy),
            "--measured-copy-stat",
            "p95",
            "--measured-copy-experts",
            "4",
            "--measured-copy-pinned",
            "true",
        ],
    )

    assert result["passed"] is False
    assert "measured_copy_experts_below_max_packet_issue_width" in result["failures"]
    assert result["full_fetch_block_reason"] == "measured_copy_issue_width_mismatch"
