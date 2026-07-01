from __future__ import annotations

from scripts import check_premap_payload_cache_stream_producer_ab_bridge as checker


def _payload() -> dict[str, object]:
    return {
        "mode": "payload_cache_stream_producer_production_like_ab_report",
        "passed": True,
        "ok": True,
        "failures": [],
        "baseline_tpot_s": 0.003263,
        "candidate_tpot_s": 0.003265,
        "candidate_overhead_ratio": 0.0007,
        "online_contract_passed": True,
        "measures_tpot": True,
        "benchmark_is_current_wna16_fused_moe": True,
        "native_stream_is_current_wna16_fused_moe": False,
        "native_stream_measures_tpot": False,
        "native_stream_graph_replay_required": True,
        "native_stream_graph_replay": True,
        "native_stream_requested_graph_replay": True,
        "payload_bytes": 0,
        "candidate_payload_bytes": 0,
        "ready_credit": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "candidate_kernel_arg_pass": False,
        "candidate_changes_kernel_launch_args": False,
        "native_stream_packet_count": 2560,
        "native_stream_issue_candidate_count": 20160,
        "online_contract_expected_issue_candidate_count": 20160,
        "native_stream_issue_candidate_hash": "22488eda926276f7",
        "native_stream_persistent_state_on_device": True,
        "native_stream_issue_generation_on_device": True,
    }


def test_ab_bridge_checker_accepts_payloadless_report() -> None:
    result = checker.check_report(_payload(), max_overhead_ratio=0.02)

    assert result["passed"] is True
    assert result["failures"] == []


def test_ab_bridge_checker_accepts_legacy_report_without_packet_count() -> None:
    payload = _payload()
    payload.pop("native_stream_packet_count")

    result = checker.check_report(payload, max_overhead_ratio=0.02)

    assert result["passed"] is True
    assert result["failures"] == []


def test_ab_bridge_checker_accepts_count_ptr_readiness_fields() -> None:
    payload = _payload()
    payload.update(
        {
            "count_ptr_ready_present": True,
            "count_ptr_ready_passed": True,
            "count_ptr_expected_packet_count": 2560,
            "count_ptr_ready_count": 2560,
            "count_ptr_blocked_count": 0,
            "count_ptr_current_count_source_kind": (
                "num_tokens_post_padded_device_tensor"
            ),
            "count_ptr_payload_bytes": 0,
            "count_ptr_kernel_arg_pass": False,
            "count_ptr_passed_to_kernel": False,
            "count_ptr_changes_kernel_launch_args": False,
        }
    )

    result = checker.check_report(payload, max_overhead_ratio=0.02)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["count_ptr_ready_present"] is True
    assert result["count_ptr_ready_count"] == 2560


def test_ab_bridge_checker_rejects_count_ptr_mismatch() -> None:
    payload = _payload()
    payload.update(
        {
            "count_ptr_ready_present": True,
            "count_ptr_ready_passed": True,
            "count_ptr_expected_packet_count": 1,
            "count_ptr_ready_count": 1,
            "count_ptr_blocked_count": 0,
            "count_ptr_current_count_source_kind": (
                "num_tokens_post_padded_device_tensor"
            ),
            "count_ptr_payload_bytes": 0,
            "count_ptr_kernel_arg_pass": False,
            "count_ptr_passed_to_kernel": False,
            "count_ptr_changes_kernel_launch_args": False,
        }
    )

    result = checker.check_report(payload)

    assert result["passed"] is False
    assert "count_ptr_expected_packet_count_mismatch" in result["failures"]
    assert "count_ptr_ready_count_mismatch" in result["failures"]


def test_ab_bridge_checker_requires_packet_count_with_count_ptr() -> None:
    payload = _payload()
    payload.pop("native_stream_packet_count")
    payload.update(
        {
            "count_ptr_ready_present": True,
            "count_ptr_ready_passed": True,
            "count_ptr_expected_packet_count": 2560,
            "count_ptr_ready_count": 2560,
            "count_ptr_blocked_count": 0,
            "count_ptr_current_count_source_kind": (
                "num_tokens_post_padded_device_tensor"
            ),
            "count_ptr_payload_bytes": 0,
            "count_ptr_kernel_arg_pass": False,
            "count_ptr_passed_to_kernel": False,
            "count_ptr_changes_kernel_launch_args": False,
        }
    )

    result = checker.check_report(payload)

    assert result["passed"] is False
    assert "native_stream_packet_count_invalid" in result["failures"]


def test_ab_bridge_checker_rejects_overhead() -> None:
    payload = _payload()
    payload["candidate_overhead_ratio"] = 0.5

    result = checker.check_report(payload, max_overhead_ratio=0.02)

    assert result["passed"] is False
    assert "candidate_overhead_ratio_over_threshold" in result["failures"]


def test_ab_bridge_checker_rejects_payload_or_kernel_arg_use() -> None:
    payload = _payload()
    payload["payload_bytes"] = 1
    payload["candidate_payload_bytes"] = 1
    payload["candidate_kernel_arg_pass"] = True

    result = checker.check_report(payload)

    assert result["passed"] is False
    assert "payload_bytes_mismatch" in result["failures"]
    assert "candidate_payload_bytes_mismatch" in result["failures"]
    assert "candidate_kernel_arg_pass_not_false" in result["failures"]


def test_ab_bridge_checker_rejects_bool_payload_bytes() -> None:
    payload = _payload()
    payload["payload_bytes"] = False
    payload["candidate_payload_bytes"] = False

    result = checker.check_report(payload)

    assert result["passed"] is False
    assert "payload_bytes_invalid" in result["failures"]
    assert "candidate_payload_bytes_invalid" in result["failures"]


def test_ab_bridge_checker_rejects_contract_failure() -> None:
    payload = _payload()
    payload["online_contract_passed"] = False

    result = checker.check_report(payload)

    assert result["passed"] is False
    assert "online_contract_not_passed" in result["failures"]


def test_ab_bridge_checker_rejects_issue_count_mismatch() -> None:
    payload = _payload()
    payload["native_stream_issue_candidate_count"] = 1

    result = checker.check_report(payload)

    assert result["passed"] is False
    assert "native_stream_issue_candidate_count_mismatch" in result["failures"]


def test_ab_bridge_checker_rejects_missing_issue_hash() -> None:
    payload = _payload()
    payload["native_stream_issue_candidate_hash"] = ""

    result = checker.check_report(payload)

    assert result["passed"] is False
    assert "native_stream_issue_candidate_hash_invalid" in result["failures"]


def test_ab_bridge_checker_rejects_non_graph_replay_report() -> None:
    payload = _payload()
    payload["native_stream_graph_replay"] = False
    payload["native_stream_requested_graph_replay"] = False

    result = checker.check_report(payload)

    assert result["passed"] is False
    assert "native_stream_graph_replay_not_true" in result["failures"]
    assert "native_stream_requested_graph_replay_not_true" in result["failures"]


def test_ab_bridge_checker_rejects_bool_issue_count() -> None:
    payload = _payload()
    payload["native_stream_issue_candidate_count"] = True

    result = checker.check_report(payload)

    assert result["passed"] is False
    assert "native_stream_issue_candidate_count_invalid" in result["failures"]
