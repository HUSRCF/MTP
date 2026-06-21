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


def _packet_payload(
    *,
    layer_id: int = 0,
    previous=(3, 5),
    topk: int = 8,
    token_index: int | None = None,
    token_source: str = "decode_workload_collector",
) -> dict:
    issue_candidates = list(dict.fromkeys(int(value) for value in previous if int(value) >= 0))
    limit = len(issue_candidates) if topk == 0 else min(len(issue_candidates), topk)
    issue_candidates = issue_candidates[:limit]
    payload = {
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
    if token_index is not None:
        payload["_export_context"] = {
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
            "token_index": int(token_index),
            "token_index_source": token_source,
            "sample_idx": 0,
            "record_id": "rec-0",
            "sequence_id": 0,
            "issue_candidate_count": len(issue_candidates),
            "issue_candidate_first_expert": (
                issue_candidates[0] if issue_candidates else -1
            ),
            "issue_candidate_last_expert": (
                issue_candidates[-1] if issue_candidates else -1
            ),
            "issue_candidate_hash": _issue_hash(issue_candidates),
        }
    return payload


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


def test_issue_stream_executor_token_index_mode_uses_lead_tokens(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    online = tmp_path / "online.json"
    _write_json(
        packet0,
        _packet_payload(layer_id=0, previous=(3,), topk=1, token_index=3),
    )
    _write_json(
        packet1,
        _packet_payload(layer_id=1, previous=(5,), topk=1, token_index=4),
    )
    _write_json(online, _online_payload([packet0, packet1]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--event-timing-mode",
            "token_index",
            "--decode-token-us",
            "100",
            "--issue-lead-tokens",
            "1",
            "--layer-event-interval-us",
            "1",
            "--service-us-per-issue",
            "0",
            "--queue-batch-size",
            "1",
            "--queue-deadline-us",
            "0",
            "--min-packet-count",
            "2",
            "--min-nonempty-packet-count",
            "2",
        ],
    )

    assert result["passed"] is True
    assert result["event_timing_mode"] == "token_index"
    assert result["token_timing_enabled"] is True
    assert result["token_index_count"] == 2
    assert result["token_source_decode_workload_count"] == 2
    assert result["token_index_min"] == 3
    assert result["token_index_max"] == 4
    assert result["queue_batch_size"] == 1
    assert result["issue_arrival_min_us"] == 200.0
    assert result["issue_arrival_max_us"] == 301.0
    assert result["demand_arrival_min_us"] == 300.0
    assert result["demand_arrival_max_us"] == 401.0
    assert result["demand_hit_rate"] == 1.0
    assert result["shifted_issue_accounting_enabled"] is True
    assert result["shifted_issue_lead_tokens"] == 1
    assert result["shifted_issue_clamped_issue_count"] == 0
    assert result["shifted_issue_duplicate_issue_key_count"] == 0
    assert result["shifted_issue_unique_issue_key_count"] == 2
    assert result["shifted_issue_row_shift_mismatch_count"] == 0
    assert result["shifted_issue_row_clamp_mismatch_count"] == 0


def test_issue_stream_executor_token_index_mode_reports_bootstrap_coalescing(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    online = tmp_path / "online.json"
    _write_json(
        packet0,
        _packet_payload(layer_id=0, previous=(3,), topk=1, token_index=1),
    )
    second_payload = _packet_payload(layer_id=0, previous=(5,), topk=1, token_index=2)
    second_payload["_export_context"].pop("sequence_id")
    _write_json(packet1, second_payload)
    _write_json(online, _online_payload([packet0, packet1]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--event-timing-mode",
            "token_index",
            "--decode-token-us",
            "100",
            "--issue-lead-tokens",
            "4",
            "--service-us-per-issue",
            "0",
            "--queue-batch-size",
            "1",
            "--min-packet-count",
            "2",
            "--min-nonempty-packet-count",
            "2",
        ],
    )

    assert result["passed"] is True
    assert result["shifted_issue_accounting_enabled"] is True
    assert result["shifted_issue_lead_tokens"] == 4
    assert result["shifted_issue_clamped_issue_count"] == 2
    assert result["shifted_issue_duplicate_issue_key_count"] == 1
    assert result["shifted_issue_unique_issue_key_count"] == 1
    assert result["shifted_issue_accounted_packet_count"] == 2
    assert result["shifted_issue_row_shift_mismatch_count"] == 0
    assert result["shifted_issue_row_clamp_mismatch_count"] == 0


def test_issue_stream_executor_token_index_mode_reports_exported_shift_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    payload = _packet_payload(layer_id=0, previous=(3,), topk=1, token_index=2)
    payload["_export_context"]["issue_token_index"] = 2
    payload["_export_context"]["issue_clamped_to_zero"] = False
    _write_json(packet0, payload)
    _write_json(online, _online_payload([packet0]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--event-timing-mode",
            "token_index",
            "--decode-token-us",
            "100",
            "--issue-lead-tokens",
            "4",
            "--service-us-per-issue",
            "0",
            "--min-packet-count",
            "1",
            "--min-nonempty-packet-count",
            "1",
        ],
    )

    assert result["passed"] is False
    assert result["shifted_issue_clamped_issue_count"] == 1
    assert result["shifted_issue_row_shift_mismatch_count"] == 1
    assert result["shifted_issue_row_clamp_mismatch_count"] == 1
    assert "shifted_issue_row_shift_mismatch_count_nonzero" in result["failures"]
    assert "shifted_issue_row_clamp_mismatch_count_nonzero" in result["failures"]


def test_issue_stream_executor_token_index_mode_rejects_malformed_exported_shift(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    payload = _packet_payload(layer_id=0, previous=(3,), topk=1, token_index=2)
    payload["_export_context"]["issue_token_index"] = True
    payload["_export_context"]["issue_clamped_to_zero"] = 0
    _write_json(packet0, payload)
    _write_json(online, _online_payload([packet0]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--event-timing-mode",
            "token_index",
            "--issue-lead-tokens",
            "4",
            "--service-us-per-issue",
            "0",
            "--min-packet-count",
            "1",
            "--min-nonempty-packet-count",
            "1",
        ],
    )

    assert result["passed"] is False
    assert result["shifted_issue_invalid_export_count"] == 2
    assert "packet_0_issue_token_index_invalid" in result["failures"]
    assert "packet_0_issue_clamped_to_zero_invalid" in result["failures"]
    assert "shifted_issue_invalid_export_count_nonzero" in result["failures"]


def test_issue_stream_executor_token_index_mode_rejects_invalid_layer_id(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    _write_json(
        packet0,
        _packet_payload(layer_id=-1, previous=(3,), topk=1, token_index=3),
    )
    _write_json(online, _online_payload([packet0]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        ["--event-timing-mode", "token_index"],
    )

    assert result["passed"] is False
    assert "packet_0_layer_id_invalid" in result["failures"]


def test_issue_stream_executor_token_index_mode_rejects_non_int_layer_ids(
    tmp_path: Path,
):
    module = _load_module()
    packet_paths = []
    invalid_layers = [True, "2", None]
    for idx, layer_id in enumerate(invalid_layers):
        packet = tmp_path / f"packet{idx}.json"
        payload = _packet_payload(layer_id=0, previous=(3 + idx,), topk=1, token_index=idx)
        if layer_id is None:
            payload.pop("layer_id", None)
        else:
            payload["layer_id"] = layer_id
        _write_json(packet, payload)
        packet_paths.append(packet)
    online = tmp_path / "online.json"
    _write_json(online, _online_payload(packet_paths))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        ["--event-timing-mode", "token_index"],
    )

    assert result["passed"] is False
    for idx in range(len(invalid_layers)):
        assert f"packet_{idx}_layer_id_invalid" in result["failures"]


def test_issue_stream_executor_token_index_mode_rejects_config_source(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    _write_json(
        packet0,
        _packet_payload(
            layer_id=0,
            previous=(3,),
            topk=1,
            token_index=3,
            token_source="config",
        ),
    )
    _write_json(online, _online_payload([packet0]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        ["--event-timing-mode", "token_index"],
    )

    assert result["passed"] is False
    assert "packet_0_config_token_source_disallowed" in result["failures"]
    assert "config_token_source_present" in result["failures"]


def test_issue_stream_executor_token_index_mode_allows_empty_config_packet(
    tmp_path: Path,
):
    module = _load_module()
    empty_packet = tmp_path / "empty_packet.json"
    nonempty_packet = tmp_path / "nonempty_packet.json"
    online = tmp_path / "online.json"
    _write_json(
        empty_packet,
        _packet_payload(
            layer_id=0,
            previous=(),
            topk=1,
            token_index=-1,
            token_source="config",
        ),
    )
    _write_json(
        nonempty_packet,
        _packet_payload(layer_id=0, previous=(3,), topk=1, token_index=8),
    )
    _write_json(online, _online_payload([empty_packet, nonempty_packet]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--event-timing-mode",
            "token_index",
            "--allow-empty-config-packets",
            "--service-us-per-issue",
            "0",
            "--min-packet-count",
            "2",
            "--min-nonempty-packet-count",
            "1",
        ],
    )

    assert result["passed"] is True
    assert result["empty_issue_provenance_exempt_count"] == 1
    assert result["required_token_provenance_packet_count"] == 1
    assert result["required_token_index_count"] == 1
    assert result["required_token_source_decode_workload_count"] == 1
    assert result["required_token_source_config_count"] == 0
    assert result["token_source_config_count"] == 1
    assert result["demand_count"] == 1
    assert result["issued_prefetch_count"] == 1


def test_issue_stream_executor_token_index_mode_rejects_nonempty_config_with_empty_exemption(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    _write_json(
        packet0,
        _packet_payload(
            layer_id=0,
            previous=(3,),
            topk=1,
            token_index=8,
            token_source="config",
        ),
    )
    _write_json(online, _online_payload([packet0]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        ["--event-timing-mode", "token_index", "--allow-empty-config-packets"],
    )

    assert result["passed"] is False
    assert "packet_0_config_token_source_disallowed" in result["failures"]
    assert "config_token_source_present" in result["failures"]


def test_issue_stream_executor_token_index_mode_allows_config_source_in_audit_mode(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    _write_json(
        packet0,
        _packet_payload(
            layer_id=0,
            previous=(3,),
            topk=1,
            token_index=3,
            token_source="config",
        ),
    )
    _write_json(online, _online_payload([packet0]))

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--event-timing-mode",
            "token_index",
            "--allow-config-token-source",
            "--service-us-per-issue",
            "0",
        ],
    )

    assert result["passed"] is True
    assert result["allow_config_token_source"] is True
    assert result["token_source_config_count"] == 1


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


def test_issue_stream_executor_rejects_bool_payload_bytes(tmp_path: Path):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    online = tmp_path / "online.json"
    packet = _packet_payload(previous=(3,), topk=1, token_index=1)
    packet["payload_bytes"] = False
    packet["_export_context"]["payload_bytes"] = False
    online_payload = _online_payload([packet0])
    online_payload["payload_bytes"] = False
    _write_json(packet0, packet)
    _write_json(online, online_payload)

    result = _run(
        module,
        online,
        tmp_path / "out.json",
        [
            "--event-timing-mode",
            "token_index",
            "--allow-empty-config-packets",
        ],
    )

    assert result["passed"] is False
    assert "online_payload_bytes_not_zero" in result["failures"]
    assert "packet_0_payload_bytes_not_zero" in result["failures"]
    assert "packet_0_export_context_payload_bytes_not_zero" in result["failures"]
    assert result["payload_bytes"] == 0
    assert result["payload_transfer_enabled"] is False


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
