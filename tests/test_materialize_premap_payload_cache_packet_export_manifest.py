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
        / "materialize_premap_payload_cache_packet_export_manifest.py"
    )
    spec = importlib.util.spec_from_file_location(
        "materialize_premap_payload_cache_packet_export_manifest",
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


def _safe_flags() -> dict:
    return {
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
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "payload_bytes": 0,
    }


def _packet_payload(index: int = 0) -> dict:
    experts = [] if index == 0 else [1, 2, 3]
    token_index = -1 if not experts else index * 8
    source = "config" if not experts else "decode_workload_collector"
    count = len(experts)
    first = experts[0] if experts else -1
    last = experts[-1] if experts else -1
    digest = _issue_hash(experts)
    packet = {
        **_safe_flags(),
        "ready": True,
        "layer_id": 0,
        "issue_candidate_experts": experts,
        "issue_candidate_count": count,
        "issue_candidate_first_expert": first,
        "issue_candidate_last_expert": last,
        "issue_candidate_hash": digest,
        "_export_context": {
            **_safe_flags(),
            "ready": True,
            "layer_id": 0,
            "issue_candidate_count": count,
            "issue_candidate_first_expert": first,
            "issue_candidate_last_expert": last,
            "issue_candidate_hash": digest,
            "token_index": token_index,
            "token_index_source": source,
            "sample_idx": None if not experts else 0,
            "record_id": None if not experts else "record-0",
            "sequence_id": 0,
        },
    }
    return packet


def _summary(packet_paths: list[Path], *, enabled: object = True) -> dict:
    prefix = "runtime_shadow_premap_payload_cache_producer_state_packet_export_"
    shifted_prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"
    nonempty_count = max(0, len(packet_paths) - 1)
    first_nonempty_path = str(packet_paths[1]) if nonempty_count else None
    first_nonempty_count = 3 if nonempty_count else 0
    first_nonempty_hash = _issue_hash([1, 2, 3]) if nonempty_count else None
    return {
        f"{prefix}count": len(packet_paths),
        f"{prefix}enabled": True,
        f"{prefix}paths": [str(path) for path in packet_paths],
        f"{prefix}scan_error_count": 0,
        f"{prefix}nonempty_issue_count": nonempty_count,
        f"{prefix}first_nonempty_issue_index": 1 if nonempty_count else -1,
        f"{prefix}first_nonempty_issue_path": first_nonempty_path,
        f"{prefix}first_nonempty_issue_count": first_nonempty_count,
        f"{prefix}first_nonempty_issue_hash": first_nonempty_hash,
        f"{shifted_prefix}enabled": enabled,
        f"{shifted_prefix}runtime_shadow_enabled": enabled,
        f"{shifted_prefix}packet_count": len(packet_paths),
        f"{shifted_prefix}schedulable_packet_count": nonempty_count,
        f"{shifted_prefix}empty_issue_exempt_count": 1 if packet_paths else 0,
        f"{shifted_prefix}safe_packet_count": len(packet_paths),
        f"{shifted_prefix}unsafe_packet_count": 0,
        f"{shifted_prefix}invalid_packet_count": 0,
        f"{shifted_prefix}scan_error_count": 0,
        f"{shifted_prefix}clamped_issue_count": 0,
        f"{shifted_prefix}duplicate_demand_key_count": 0,
        f"{shifted_prefix}duplicate_issue_key_count": 0,
        f"{shifted_prefix}unique_demand_key_count": nonempty_count,
        f"{shifted_prefix}unique_issue_key_count": nonempty_count,
        f"{shifted_prefix}total_issue_candidates": nonempty_count * 3,
        f"{shifted_prefix}issue_hash_count": nonempty_count,
        f"{shifted_prefix}issue_hash_unique_count": 1 if nonempty_count else 0,
        f"{shifted_prefix}issue_lead_tokens": 1,
        f"{shifted_prefix}lead_tokens": 1,
        f"{shifted_prefix}payload_bytes": 0,
        f"{shifted_prefix}ready_credit": False,
        f"{shifted_prefix}ready_before_demand_credit": False,
        f"{shifted_prefix}real_ready_credit_granted": False,
        f"{shifted_prefix}payload_transfer_enabled": False,
        f"{shifted_prefix}payload_deref_allowed": False,
        f"{shifted_prefix}kernel_arg_pass_allowed": False,
        f"{shifted_prefix}passed_to_kernel": False,
        f"{shifted_prefix}changes_kernel_launch_args": False,
        f"{shifted_prefix}uses_current_wna16_args": False,
        f"{shifted_prefix}passes_current_wna16_args": False,
        f"{shifted_prefix}measures_tpot": False,
        f"{shifted_prefix}measures_vllm_latency": False,
    }


def test_packet_export_manifest_materializes_executor_input(tmp_path: Path):
    module = _load_module()
    packets = [tmp_path / "packet0.json", tmp_path / "packet1.json"]
    for index, packet in enumerate(packets):
        _write_json(packet, _packet_payload(index))
    summary = tmp_path / "summary.json"
    output = tmp_path / "manifest.json"
    _write_json(summary, _summary(packets))

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(output),
            "--require-shifted-issue",
            "--min-nonempty-issue-count",
            "1",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is True
    assert result["ok"] is True
    assert result["ready"] is True
    assert result["online_export_source"] == (
        "runtime_shadow_premap_payload_cache_producer_state_packet_export"
    )
    assert result["online_packet_export_count"] == 2
    assert result["online_configured_export_count"] == 2
    assert result["online_packet_export_paths"] == [
        str(path.resolve()) for path in packets
    ]
    assert result["online_nonempty_issue_count"] == 1
    assert result["shifted_issue_enabled"] is True
    assert result["shifted_issue_packet_count"] == 2
    assert result["shifted_issue_schedulable_packet_count"] == 1
    assert result["shifted_issue_safe_packet_count"] == 2
    assert result["payload_bytes"] == 0
    assert result["ready_credit"] is False
    assert result["payload_transfer_enabled"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["measures_tpot"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_packet_export_manifest_rejects_bool_count(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload())
    payload = _summary([packet])
    payload["runtime_shadow_premap_payload_cache_producer_state_packet_export_count"] = True
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "packet_export_count_invalid" in result["failures"]


def test_packet_export_manifest_requires_shifted_issue_when_requested(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload())
    summary = tmp_path / "summary.json"
    _write_json(summary, _summary([packet], enabled=False))

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--require-shifted-issue",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "shifted_issue_runtime_shadow_not_enabled" in result["failures"]


def test_packet_export_manifest_requires_shifted_issue_by_default(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload())
    payload = _summary([packet])
    for key in list(payload):
        if "runtime_shadow_premap_payload_cache_shifted_issue_" in key:
            del payload[key]
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "shifted_issue_runtime_shadow_not_enabled" in result["failures"]


def test_packet_export_manifest_can_opt_out_of_shifted_issue_gate(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload())
    payload = _summary([packet])
    for key in list(payload):
        if "runtime_shadow_premap_payload_cache_shifted_issue_" in key:
            del payload[key]
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
            "--no-require-shifted-issue",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is True
    assert result["shifted_issue_runtime_shadow_required"] is False


def test_packet_export_manifest_rejects_failed_shifted_safety_count(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload())
    payload = _summary([packet])
    payload["runtime_shadow_premap_payload_cache_shifted_issue_unsafe_packet_count"] = 1
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "shifted_issue_unsafe_packet_count_nonzero" in result["failures"]


def test_packet_export_manifest_rejects_negative_shifted_counts(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload())
    payload = _summary([packet])
    payload[
        "runtime_shadow_premap_payload_cache_shifted_issue_schedulable_packet_count"
    ] = -1
    payload[
        "runtime_shadow_premap_payload_cache_shifted_issue_unique_demand_key_count"
    ] = -1
    payload[
        "runtime_shadow_premap_payload_cache_shifted_issue_unique_issue_key_count"
    ] = -1
    payload["runtime_shadow_premap_payload_cache_shifted_issue_issue_hash_count"] = -1
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_payload_cache_shifted_issue_schedulable_packet_count_negative"
        in result["failures"]
    )


def test_packet_export_manifest_requires_shifted_accounting_closure(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    _write_json(packet0, _packet_payload(0))
    _write_json(packet1, _packet_payload(1))
    payload = _summary([packet0, packet1])
    payload[
        "runtime_shadow_premap_payload_cache_shifted_issue_empty_issue_exempt_count"
    ] = 0
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "shifted_issue_packet_count_accounting_mismatch" in result["failures"]


def test_packet_export_manifest_rejects_stale_first_nonempty_summary(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    _write_json(packet0, _packet_payload(0))
    _write_json(packet1, _packet_payload(1))
    payload = _summary([packet0, packet1])
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_count"
    ] = 8
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_hash"
    ] = "0123456789abcdef"
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "packet_export_first_nonempty_issue_count_mismatch" in result["failures"]
    assert "packet_export_first_nonempty_issue_hash_mismatch" in result["failures"]


def test_packet_export_manifest_rejects_stale_first_nonempty_when_no_nonempty_packets(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload(0))
    payload = _summary([packet])
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_index"
    ] = 0
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_path"
    ] = str(packet)
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_count"
    ] = 8
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_hash"
    ] = "0123456789abcdef"
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "packet_export_first_nonempty_issue_index_mismatch" in result["failures"]
    assert "packet_export_first_nonempty_issue_path_mismatch" in result["failures"]
    assert "packet_export_first_nonempty_issue_count_mismatch" in result["failures"]


def test_packet_export_manifest_rejects_bool_context_layer_id_even_without_shifted_gate(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    payload_packet = _packet_payload(1)
    payload_packet["layer_id"] = 1
    payload_packet["_export_context"]["layer_id"] = True
    _write_json(packet, payload_packet)
    payload = _summary([packet])
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_nonempty_issue_count"
    ] = 1
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_index"
    ] = 0
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_path"
    ] = str(packet)
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_count"
    ] = 3
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_first_nonempty_issue_hash"
    ] = _issue_hash([1, 2, 3])
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--no-require-shifted-issue",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "packet_0_export_context_layer_id_mismatch" in result["failures"]


def test_packet_export_manifest_allows_config_token_source_when_enabled(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    _write_json(packet0, _packet_payload(0))
    payload1 = _packet_payload(1)
    payload1["_export_context"]["token_index_source"] = "config"
    _write_json(packet1, payload1)
    payload = _summary([packet0, packet1])
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--allow-config-token-source",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is True
    assert result["allow_config_token_source"] is True


def test_packet_export_manifest_rejects_packet_recomputed_clamp_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    _write_json(packet0, _packet_payload(0))
    payload1 = _packet_payload(1)
    payload1["_export_context"]["token_index"] = 0
    _write_json(packet1, payload1)
    payload = _summary([packet0, packet1])
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert (
        "shifted_issue_clamped_issue_count_packet_mismatch" in result["failures"]
    )


def test_packet_export_manifest_rejects_packet_recomputed_duplicate_key_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    packet0 = tmp_path / "packet0.json"
    packet1 = tmp_path / "packet1.json"
    packet2 = tmp_path / "packet2.json"
    _write_json(packet0, _packet_payload(0))
    _write_json(packet1, _packet_payload(1))
    payload2 = _packet_payload(2)
    payload2["_export_context"]["token_index"] = 8
    _write_json(packet2, payload2)
    payload = _summary([packet0, packet1, packet2])
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert (
        "shifted_issue_duplicate_demand_key_count_packet_mismatch"
        in result["failures"]
    )
    assert (
        "shifted_issue_duplicate_issue_key_count_packet_mismatch"
        in result["failures"]
    )


def test_packet_export_manifest_rejects_missing_packet_path(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "missing.json"
    payload = _summary([packet])
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "packet_export_path_0_missing" in result["failures"]


def test_packet_export_manifest_rejects_directory_packet_path(tmp_path: Path):
    module = _load_module()
    packet_dir = tmp_path / "packet_dir"
    packet_dir.mkdir()
    payload = _summary([packet_dir])
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "packet_export_path_0_missing" in result["failures"]


def test_packet_export_manifest_rejects_unsafe_packet_flags(tmp_path: Path):
    module = _load_module()
    packet = tmp_path / "packet.json"
    payload = _packet_payload()
    payload["payload_transfer_enabled"] = True
    _write_json(packet, payload)
    summary = tmp_path / "summary.json"
    _write_json(summary, _summary([packet]))

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "packet_0_payload_transfer_enabled_not_false" in result["failures"]


def test_packet_export_manifest_rejects_invalid_canonical_issue_lead_tokens(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload())
    payload = _summary([packet])
    payload["runtime_shadow_premap_payload_cache_shifted_issue_issue_lead_tokens"] = True
    payload["runtime_shadow_premap_payload_cache_shifted_issue_lead_tokens"] = 1
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "shifted_issue_lead_tokens_invalid" in result["failures"]


def test_packet_export_manifest_rejects_negative_nonempty_issue_count(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload())
    payload = _summary([packet])
    payload[
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_nonempty_issue_count"
    ] = -1
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "-2",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "min_nonempty_issue_count_negative" in result["failures"]
    assert "packet_export_nonempty_issue_count_negative" in result["failures"]


def test_packet_export_manifest_reports_bad_count_without_crashing(
    tmp_path: Path,
):
    module = _load_module()
    packet = tmp_path / "packet.json"
    _write_json(packet, _packet_payload())
    payload = _summary([packet])
    payload["runtime_shadow_premap_payload_cache_producer_state_packet_export_count"] = (
        "abc"
    )
    summary = tmp_path / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is False
    assert "packet_export_count_invalid" in result["failures"]
    assert "packet_export_configured_count_invalid" in result["failures"]


def test_packet_export_manifest_resolves_relative_paths_from_summary_dir(
    tmp_path: Path,
):
    module = _load_module()
    trace_dir = tmp_path / "trace"
    packet = trace_dir / "packets" / "packet.json"
    _write_json(packet, _packet_payload())
    payload = _summary([Path("packets/packet.json")])
    summary = trace_dir / "summary.json"
    _write_json(summary, payload)

    args = module.build_parser().parse_args(
        [
            "--performance-summary",
            str(summary),
            "--output-json",
            str(tmp_path / "manifest.json"),
            "--min-nonempty-issue-count",
            "0",
        ]
    )
    result = module._packet_export_manifest(args)

    assert result["passed"] is True
    assert result["online_packet_export_paths"] == [str(packet.resolve())]
