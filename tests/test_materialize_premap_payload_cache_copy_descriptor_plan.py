from __future__ import annotations

import json
from pathlib import Path

from scripts import materialize_premap_payload_cache_copy_descriptor_plan as plan
from scripts import run_premap_payload_cache_issue_stream_executor as executor


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _safe_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {key: False for key in executor.SAFE_FALSE_FLAGS}
    payload.update({key: 0 for key in executor.SAFE_ZERO_FLAGS})
    payload.update(overrides)
    return payload


def _packet(
    *,
    layer_id: int,
    experts: list[int],
    sample_idx: int,
    token_index: int,
    record_id: str = "sample-000",
    include_shifted_context: bool = True,
) -> dict[str, object]:
    first = experts[0] if experts else -1
    last = experts[-1] if experts else -1
    issue_hash = executor._issue_hash(experts)
    export_context = _safe_payload(
        ready=True,
        layer_id=layer_id,
        sample_idx=sample_idx,
        request_id=f"sample_{sample_idx}",
        record_id=record_id,
        sequence_id=0,
        token_index=token_index,
        token_index_source="decode_workload_collector",
        issue_candidate_count=len(experts),
        issue_candidate_first_expert=first,
        issue_candidate_last_expert=last,
        issue_candidate_hash=issue_hash,
    )
    if include_shifted_context:
        export_context.update(
            issue_token_index=max(0, token_index - 1),
            issue_clamped_to_zero=token_index == 0,
        )
    fields: dict[str, object] = {
        "ready": True,
        "layer_id": layer_id,
        "issue_candidate_experts": experts,
        "issue_candidate_count": len(experts),
        "issue_candidate_first_expert": first,
        "issue_candidate_last_expert": last,
        "issue_candidate_hash": issue_hash,
        "issue_source": "previous_token_transition_premap_shadow",
        "previous_experts": experts,
        "transition_topk_count": len(experts),
        "_export_context": export_context,
    }
    fields.update(_safe_payload())
    return fields


def _make_inputs(tmp_path: Path) -> tuple[Path, Path]:
    packet0 = tmp_path / "packets" / "packet0.json"
    packet1 = tmp_path / "packets" / "packet1.json"
    _write_json(
        packet0,
        _packet(
            layer_id=0,
            experts=[1, 2],
            sample_idx=0,
            token_index=1,
            include_shifted_context=False,
        ),
    )
    _write_json(
        packet1,
        _packet(layer_id=0, experts=[2, 3], sample_idx=0, token_index=2),
    )
    online_path = tmp_path / "online.json"
    _write_json(
        online_path,
        _safe_payload(
            ok=True,
            passed=True,
            ready=True,
            failures=[],
            online_packet_export_paths=[str(packet0), str(packet1)],
            online_packet_export_count=2,
            online_configured_export_count=2,
            online_export_source=(
                "runtime_shadow_premap_payload_cache_producer_state_packet_export"
            ),
        ),
    )
    stream_path = tmp_path / "stream.json"
    _write_json(
        stream_path,
        _safe_payload(
            artifact_kind="premap_payload_cache_issue_stream_executor",
            passed=True,
            failures=[],
            online_canary_json=str(online_path),
            packet_count=2,
            nonempty_packet_count=2,
            requested_issue_count=4,
            issued_prefetch_count=3,
            capacity=16,
            service_us_per_issue=0.0,
            service_us_per_batch=0.0,
            queue_batch_size=8,
            queue_deadline_us=200.0,
            event_timing_mode="token_index",
            decode_token_us=10.0,
            issue_lead_tokens=1,
            layer_event_interval_us=1.0,
            issue_arrival_us=0.0,
            demand_gap_us=0.0,
        ),
    )
    return stream_path, online_path


def test_copy_descriptor_plan_materializes_accepted_issue_rows(tmp_path: Path) -> None:
    stream_path, _ = _make_inputs(tmp_path)
    output_path = tmp_path / "plan.json"

    result = plan.build_copy_descriptor_plan(
        issue_stream_executor_json=stream_path,
        output_json=output_path,
        planned_payload_bytes_per_issue=64,
        row_sample_limit=8,
        require_same_source_packet_budget=True,
    )

    assert result["passed"] is True
    assert result["copy_descriptor_plan_ready"] is True
    assert result["packet_count"] == 2
    assert result["requested_issue_count"] == 4
    assert result["issued_prefetch_count"] == 3
    assert result["copy_descriptor_count"] == 3
    assert result["copy_descriptor_shape_checked"] is True
    assert result["planned_payload_bytes"] == 192
    assert result["payload_bytes"] == 0
    assert result["issued_payload_count"] == 0
    assert result["payload_transfer_enabled"] is False
    assert result["ready_credit"] is False
    assert result["passed_to_kernel"] is False
    assert result["copy_descriptor_submitted"] is False
    assert result["copy_descriptor_executed"] is False
    assert len(result["copy_descriptor_row_hash"]) == 64
    rows = result["row_sample"]
    assert [row["expert_id"] for row in rows] == [1, 2, 3]
    assert rows[0]["issue_token_index"] == 0
    assert rows[0]["issue_clamped_to_zero"] is False
    assert rows[0]["planned_payload_bytes"] == 64
    assert output_path.exists()


def test_copy_descriptor_plan_rejects_executor_count_mismatch(tmp_path: Path) -> None:
    stream_path, _ = _make_inputs(tmp_path)
    payload = json.loads(stream_path.read_text(encoding="utf-8"))
    payload["issued_prefetch_count"] = 99
    _write_json(stream_path, payload)

    result = plan.build_copy_descriptor_plan(
        issue_stream_executor_json=stream_path,
        output_json=tmp_path / "plan.json",
        planned_payload_bytes_per_issue=64,
    )

    assert result["passed"] is False
    assert "copy_descriptor_count_issued_prefetch_count_mismatch" in result["failures"]
    assert "manager_replay_issued_prefetch_count_mismatch" in result["failures"]


def test_copy_descriptor_plan_can_require_same_source_budget(tmp_path: Path) -> None:
    stream_path, online_path = _make_inputs(tmp_path)
    online = json.loads(online_path.read_text(encoding="utf-8"))
    online["online_configured_export_count"] = 3
    _write_json(online_path, online)

    result = plan.build_copy_descriptor_plan(
        issue_stream_executor_json=stream_path,
        output_json=tmp_path / "plan.json",
        planned_payload_bytes_per_issue=64,
        require_same_source_packet_budget=True,
    )

    assert result["passed"] is False
    assert "same_source_packet_budget_mismatch" in result["failures"]


def test_copy_descriptor_plan_rejects_invalid_event_timing_mode(tmp_path: Path) -> None:
    stream_path, _ = _make_inputs(tmp_path)
    payload = json.loads(stream_path.read_text(encoding="utf-8"))
    payload["event_timing_mode"] = "future"
    _write_json(stream_path, payload)

    result = plan.build_copy_descriptor_plan(
        issue_stream_executor_json=stream_path,
        output_json=tmp_path / "plan.json",
    )

    assert result["passed"] is False
    assert "event_timing_mode_invalid" in result["failures"]


def test_copy_descriptor_plan_rejects_online_source_mismatch(tmp_path: Path) -> None:
    stream_path, online_path = _make_inputs(tmp_path)
    online = json.loads(online_path.read_text(encoding="utf-8"))
    online["online_export_source"] = "wrong"
    _write_json(online_path, online)

    result = plan.build_copy_descriptor_plan(
        issue_stream_executor_json=stream_path,
        output_json=tmp_path / "plan.json",
    )

    assert result["passed"] is False
    assert "online_export_source_mismatch" in result["failures"]


def test_copy_descriptor_plan_rejects_relative_packet_outside_manifest_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    stream_path, online_path = _make_inputs(tmp_path)
    repo_root = tmp_path / "repo"
    repo_packet = repo_root / "repo_only_packets" / "packet0.json"
    _write_json(
        repo_packet,
        _packet(layer_id=0, experts=[1, 2], sample_idx=0, token_index=1),
    )
    online = json.loads(online_path.read_text(encoding="utf-8"))
    online["online_packet_export_paths"] = ["repo_only_packets/packet0.json"]
    online["online_packet_export_count"] = 1
    online["online_configured_export_count"] = 1
    _write_json(online_path, online)
    stream = json.loads(stream_path.read_text(encoding="utf-8"))
    stream["packet_count"] = 1
    stream["nonempty_packet_count"] = 1
    monkeypatch.setattr(plan, "REPO_ROOT", repo_root)
    _write_json(stream_path, stream)

    result = plan.build_copy_descriptor_plan(
        issue_stream_executor_json=stream_path,
        output_json=tmp_path / "plan.json",
    )

    assert result["passed"] is False
    assert any(
        failure.startswith("packet_0_load_or_parse_failed:FileNotFoundError")
        for failure in result["failures"]
    )


def test_copy_descriptor_plan_rejects_invalid_layer_id(tmp_path: Path) -> None:
    stream_path, online_path = _make_inputs(tmp_path)
    online = json.loads(online_path.read_text(encoding="utf-8"))
    first_packet = Path(online["online_packet_export_paths"][0])
    packet = json.loads(first_packet.read_text(encoding="utf-8"))
    packet["layer_id"] = True
    _write_json(first_packet, packet)

    result = plan.build_copy_descriptor_plan(
        issue_stream_executor_json=stream_path,
        output_json=tmp_path / "plan.json",
    )

    assert result["passed"] is False
    assert "packet_0_layer_id_invalid" in result["failures"]


def test_copy_descriptor_plan_rejects_shifted_issue_mismatch(tmp_path: Path) -> None:
    stream_path, online_path = _make_inputs(tmp_path)
    online = json.loads(online_path.read_text(encoding="utf-8"))
    first_packet = Path(online["online_packet_export_paths"][0])
    packet = json.loads(first_packet.read_text(encoding="utf-8"))
    packet["_export_context"]["issue_token_index"] = 99
    packet["_export_context"]["issue_clamped_to_zero"] = True
    _write_json(first_packet, packet)

    result = plan.build_copy_descriptor_plan(
        issue_stream_executor_json=stream_path,
        output_json=tmp_path / "plan.json",
    )

    assert result["passed"] is False
    assert "packet_0_issue_token_index_mismatch" in result["failures"]
    assert "packet_0_issue_clamped_to_zero_mismatch" in result["failures"]


def test_copy_descriptor_plan_rejects_missing_token_source(tmp_path: Path) -> None:
    stream_path, online_path = _make_inputs(tmp_path)
    online = json.loads(online_path.read_text(encoding="utf-8"))
    first_packet = Path(online["online_packet_export_paths"][0])
    packet = json.loads(first_packet.read_text(encoding="utf-8"))
    del packet["_export_context"]["token_index_source"]
    _write_json(first_packet, packet)

    result = plan.build_copy_descriptor_plan(
        issue_stream_executor_json=stream_path,
        output_json=tmp_path / "plan.json",
    )

    assert result["passed"] is False
    assert "packet_0_token_index_source_missing" in result["failures"]
