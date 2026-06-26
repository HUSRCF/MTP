#!/usr/bin/env python3
"""Summarize the payload-cache native producer evidence ladder.

The payload-cache producer path has several intentionally different evidence
levels.  This checker keeps them separated so a passed standalone/native replay
artifact cannot be mistaken for a live vLLM replay-visible producer op.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


NEXT_REQUIRED_BOUNDARY = "inprocess_vllm_replay_visible_native_producer_op"


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _false_or_missing(value: Any) -> bool:
    return value in (None, False, 0)


_RUNTIME_DISABLED_FIELDS = (
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "kernel_arg_pass",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)


def _clean_passed(payload: dict[str, Any] | None) -> bool:
    return bool(
        payload is not None
        and payload.get("passed") is True
        and payload.get("ok") is True
        and payload.get("failures") == []
    )


def _require_payload_zero(
    payload: dict[str, Any],
    *,
    prefix: str,
    failures: list[str],
    allow_missing: bool = False,
) -> None:
    value = payload.get("payload_bytes")
    if allow_missing:
        ok = value in (None, 0)
    else:
        ok = value == 0
    if not ok:
        failures.append(f"{prefix}_payload_bytes_nonzero")


def _require_false_fields(
    payload: dict[str, Any],
    keys: tuple[str, ...],
    *,
    prefix: str,
    failures: list[str],
    allow_missing: bool = False,
) -> None:
    for key in keys:
        value = payload.get(key)
        if allow_missing:
            ok = value in (None, False)
        else:
            ok = value is False
        if not ok:
            failures.append(f"{prefix}_{key}_not_false")


def _int_metric(payload: dict[str, Any] | None, key: str) -> int | None:
    if payload is None:
        return None
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def check_ladder(
    *,
    boundary_gap_json: Path,
    native_graph_replay_json: Path | None = None,
    packet_stream_native_canary_json: Path | None = None,
    session_online_contract_json: Path | None = None,
) -> dict[str, Any]:
    boundary = _load_json(boundary_gap_json)
    native = _load_json(native_graph_replay_json)
    packet_stream = _load_json(packet_stream_native_canary_json)
    session = _load_json(session_online_contract_json)
    assert boundary is not None

    failures: list[str] = []
    if boundary.get("passed") is not True or boundary.get("ok") is not True:
        failures.append("boundary_gap_not_acknowledged")
    if boundary.get("failures") not in ([], None):
        failures.append("boundary_gap_failures_not_empty")
    if boundary.get("mode") != "payload_cache_online_native_producer_boundary_gap_report":
        failures.append("boundary_gap_mode_mismatch")
    if boundary.get("online_tensor_producer_passed") is not False:
        failures.append("boundary_gap_online_tensor_producer_passed_not_false")
    if boundary.get("online_capture_once_per_layer_suspected") is not True:
        failures.append("boundary_gap_capture_once_not_reported")
    if (
        boundary.get("online_replay_update_status")
        != "capture_once_per_layer_no_replay_updates"
    ):
        failures.append("boundary_gap_replay_status_mismatch")
    if boundary.get("ready_for_lab_runtime_gate") is not False:
        failures.append("boundary_gap_ready_for_lab_runtime_gate_not_false")
    if boundary.get("runtime_passed") is not False:
        failures.append("boundary_gap_runtime_passed_not_false")
    if boundary.get("lab_gate_passed") is not False:
        failures.append("boundary_gap_lab_gate_passed_not_false")
    if boundary.get("next_required_boundary") != NEXT_REQUIRED_BOUNDARY:
        failures.append("boundary_gap_next_required_boundary_mismatch")
    if boundary.get("payload_bytes") != 0:
        failures.append("boundary_gap_payload_bytes_nonzero")
    _require_false_fields(
        boundary,
        _RUNTIME_DISABLED_FIELDS + ("current_wna16_arg_compatible",),
        prefix="boundary_gap",
        failures=failures,
    )

    boundary_native_issue = _int_metric(boundary, "native_issue_candidate_count")
    boundary_online_issue = _int_metric(
        boundary,
        "online_graph_expected_issue_candidate_count",
    )
    boundary_native_expected_issue = _int_metric(
        boundary,
        "native_expected_issue_candidate_count",
    )
    boundary_native_packets = _int_metric(boundary, "native_packet_count")
    boundary_online_packets = _int_metric(boundary, "online_graph_expected_packet_count")
    for label, value in (
        ("boundary_native_issue_candidate_count", boundary_native_issue),
        ("boundary_online_graph_expected_issue_candidate_count", boundary_online_issue),
        ("boundary_native_packet_count", boundary_native_packets),
        ("boundary_online_graph_expected_packet_count", boundary_online_packets),
    ):
        if value is None or value <= 0:
            failures.append(f"{label}_invalid")
    if (
        boundary_native_issue is not None
        and boundary_online_issue is not None
        and boundary_native_issue != boundary_online_issue
    ):
        failures.append("boundary_native_online_issue_count_mismatch")
    if (
        boundary_native_expected_issue is not None
        and boundary_online_issue is not None
        and boundary_native_expected_issue != boundary_online_issue
    ):
        failures.append("boundary_native_expected_online_issue_count_mismatch")
    if (
        boundary_native_packets is not None
        and boundary_online_packets is not None
        and boundary_native_packets != boundary_online_packets
    ):
        failures.append("boundary_native_online_packet_count_mismatch")

    native_graph_replay_passed = bool(
        _clean_passed(native)
        and native is not None
        and native.get("native_graph_replay") is True
        and native.get("inprocess_native_op") in (None, True)
    )
    native_issue = _int_metric(native, "issue_candidate_count")
    native_packets = _int_metric(native, "packet_count")
    if native is not None:
        if not native_graph_replay_passed:
            failures.append("native_graph_replay_not_passed")
        _require_payload_zero(
            native,
            prefix="native_graph_replay",
            failures=failures,
        )
        if native_issue != boundary_native_issue:
            failures.append("native_graph_replay_issue_count_mismatch")
        if native_packets != boundary_native_packets:
            failures.append("native_graph_replay_packet_count_mismatch")
        _require_false_fields(
            native,
            _RUNTIME_DISABLED_FIELDS,
            prefix="native_graph_replay",
            failures=failures,
        )

    packet_stream_native = (
        packet_stream.get("native") if isinstance(packet_stream, dict) else None
    )
    packet_stream_wrapper = bool(
        packet_stream is not None
        and packet_stream.get("mode")
        == "payload_cache_producer_state_packet_stream_native_canary"
    )
    packet_stream_passed = bool(
        packet_stream is not None
        and _clean_passed(packet_stream)
        and (
            (
                not packet_stream_wrapper
                and packet_stream.get("packet_stream_input") is True
            )
            or (
                packet_stream_wrapper
                and isinstance(packet_stream_native, dict)
                and _clean_passed(packet_stream_native)
            )
        )
    )
    if packet_stream is not None:
        if not packet_stream_passed:
            failures.append("packet_stream_native_canary_not_passed")
        if packet_stream_wrapper:
            if packet_stream.get("payload_bytes") != 0:
                failures.append("packet_stream_payload_bytes_nonzero")
            _require_false_fields(
                packet_stream,
                _RUNTIME_DISABLED_FIELDS,
                prefix="packet_stream",
                failures=failures,
                allow_missing=True,
            )
            if isinstance(packet_stream_native, dict):
                _require_payload_zero(
                    packet_stream_native,
                    prefix="packet_stream_native",
                    failures=failures,
                    allow_missing=True,
                )
                _require_false_fields(
                    packet_stream_native,
                    _RUNTIME_DISABLED_FIELDS,
                    prefix="packet_stream_native",
                    failures=failures,
                    allow_missing=True,
                )
            else:
                failures.append("packet_stream_native_payload_missing")
        else:
            if packet_stream.get("current_expert_ptr_source") != (
                "packet_stream_torch_device_tensor"
            ):
                failures.append("packet_stream_source_mismatch")
            if packet_stream.get("ready_for_vllm_prelaunch_canary") is not False:
                failures.append(
                    "packet_stream_ready_for_vllm_prelaunch_canary_not_false"
                )
            _require_payload_zero(
                packet_stream,
                prefix="packet_stream",
                failures=failures,
                allow_missing=True,
            )
            _require_false_fields(
                packet_stream,
                _RUNTIME_DISABLED_FIELDS,
                prefix="packet_stream",
                failures=failures,
                allow_missing=True,
            )

    session_contract_passed = bool(
        _clean_passed(session)
        and session is not None
        and session.get("mode")
        == "payload_cache_producer_state_inprocess_native_session_online_contract"
        and session.get("source_is_online_stream_contract") is True
        and session.get("source_is_raw_vllm_performance_summary") is False
        and session.get("source_kind")
        == "derived_payload_cache_producer_state_stream_online_contract"
        and session.get("source_stream_online_contract_passed") is True
        and session.get("source_stream_online_contract_failures") == []
        and session.get("inprocess_native_op") is True
    )
    if session is not None:
        if not session_contract_passed:
            failures.append("session_online_contract_not_passed")
        source = session.get("current_expert_ptr_source")
        source_kind = session.get("current_expert_ptr_source_kind")
        external_source = session.get("external_current_expert_ptr_source")
        if source == "native_generated_device_scratch":
            if source_kind != "native_scratch_smoke":
                failures.append("session_online_contract_source_kind_mismatch")
            if external_source is not False:
                failures.append("session_online_contract_external_source_not_false")
        elif source == "packet_stream_torch_device_tensor":
            if source_kind != "online_packet_stream_device_tensor_smoke":
                failures.append("session_online_contract_source_kind_mismatch")
            if external_source is not False:
                failures.append("session_online_contract_external_source_not_false")
        else:
            failures.append("session_online_contract_source_unexpected")
        if session.get("ready_for_vllm_prelaunch_canary") is not False:
            failures.append("session_online_contract_vllm_prelaunch_not_false")
        _require_payload_zero(
            session,
            prefix="session_online_contract",
            failures=failures,
        )
        _require_false_fields(
            session,
            _RUNTIME_DISABLED_FIELDS,
            prefix="session_online_contract",
            failures=failures,
        )
        native_session = session.get("native")
        if isinstance(native_session, dict):
            if not _clean_passed(native_session):
                failures.append("session_online_contract_native_not_passed")
            _require_payload_zero(
                native_session,
                prefix="session_online_contract_native",
                failures=failures,
            )
            _require_false_fields(
                native_session,
                _RUNTIME_DISABLED_FIELDS,
                prefix="session_online_contract_native",
                failures=failures,
            )

    native_graph_replay_passed = bool(
        native_graph_replay_passed
        and not any(item.startswith("native_graph_replay_") for item in failures)
    )
    packet_stream_passed = bool(
        packet_stream_passed
        and not any(item.startswith("packet_stream_") for item in failures)
    )
    session_contract_passed = bool(
        session_contract_passed
        and not any(item.startswith("session_online_contract_") for item in failures)
    )

    runtime_ready = False
    lab_gate_passed = False
    return {
        "passed": not failures,
        "ok": not failures,
        "failures": failures,
        "mode": "payload_cache_native_producer_evidence_ladder",
        "boundary_gap_json": str(boundary_gap_json),
        "native_graph_replay_json": (
            None if native_graph_replay_json is None else str(native_graph_replay_json)
        ),
        "packet_stream_native_canary_json": (
            None
            if packet_stream_native_canary_json is None
            else str(packet_stream_native_canary_json)
        ),
        "session_online_contract_json": (
            None
            if session_online_contract_json is None
            else str(session_online_contract_json)
        ),
        "native_graph_replay_passed": native_graph_replay_passed,
        "packet_stream_native_canary_passed": packet_stream_passed,
        "session_online_contract_passed": session_contract_passed,
        "native_issue_candidate_count": int(boundary_native_issue or 0),
        "online_expected_issue_candidate_count": int(boundary_online_issue or 0),
        "native_packet_count": int(boundary_native_packets or 0),
        "online_expected_packet_count": int(boundary_online_packets or 0),
        "online_capture_once_gap_acknowledged": boundary.get("passed") is True,
        "runtime_ready": runtime_ready,
        "lab_gate_passed": lab_gate_passed,
        "ready_for_inprocess_native_op_work": bool(
            boundary.get("ready_for_inprocess_native_op_work") is True
        ),
        "next_required_boundary": NEXT_REQUIRED_BOUNDARY,
        "next_boundary_is_vllm_replay_visible": True,
        "payload_bytes": 0,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "evidence_levels": {
            "native_graph_replay": (
                "passed" if native_graph_replay_passed else "missing_or_failed"
            ),
            "packet_stream_native_canary": (
                "passed" if packet_stream_passed else "missing_or_failed"
            ),
            "session_online_contract": (
                "passed" if session_contract_passed else "missing_or_failed"
            ),
            "online_vllm_tensor_producer": "capture_once_gap_acknowledged",
            "required_runtime_boundary": NEXT_REQUIRED_BOUNDARY,
        },
        "runtime_safety_fields_all_disabled": all(
            _false_or_missing(boundary.get(key))
            for key in (
                "payload_transfer_enabled",
                "payload_deref_allowed",
                "ready_credit",
                "kernel_arg_pass",
                "kernel_arg_pass_allowed",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "uses_current_wna16_args",
                "passes_current_wna16_args",
            )
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundary-gap-json", type=Path, required=True)
    parser.add_argument("--native-graph-replay-json", type=Path)
    parser.add_argument("--packet-stream-native-canary-json", type=Path)
    parser.add_argument("--session-online-contract-json", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    payload = check_ladder(
        boundary_gap_json=args.boundary_gap_json,
        native_graph_replay_json=args.native_graph_replay_json,
        packet_stream_native_canary_json=args.packet_stream_native_canary_json,
        session_online_contract_json=args.session_online_contract_json,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
