from __future__ import annotations

import json
from pathlib import Path

from scripts import check_premap_payload_cache_packet_stream_native_canary as checker


def _safe() -> dict:
    return {
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def _passed_canary() -> dict:
    native = {
        **_safe(),
        "ok": True,
        "passed": True,
        "failures": [],
        "native_returncode": 0,
        "native_graph_replay": True,
        "packet_stream_input": True,
        "persistent_state_on_device": True,
        "issue_generation_on_device": True,
        "native_stub_invoked": True,
        "packet_count": 32,
        "previous_nonempty_packet_count": 28,
        "issue_candidate_count": 224,
        "issue_candidate_hash": "83a1a8065edf2ddd",
        "expected_issue_candidate_count": 224,
        "state_override_count": 31,
        "state_mismatch_count": 0,
        "issue_expert_mismatch_count": 0,
    }
    return {
        **_safe(),
        "ok": True,
        "passed": True,
        "failures": [],
        "mode": "payload_cache_producer_state_packet_stream_native_canary",
        "materialized": {
            "passed": True,
            "failures": [],
            "packet_count": 32,
            "state_override_count": 31,
            "expected_issue_candidate_count": 224,
            "expected_issue_candidate_hash": "83a1a8065edf2ddd",
            "expected_previous_nonempty_packet_count": 28,
        },
        "native": native,
        "comparisons": {
            "packet_count_match": True,
            "previous_nonempty_packet_count_match": True,
            "issue_candidate_count_match": True,
            "issue_candidate_hash_match": True,
            "expected_issue_candidate_count_match": True,
            "state_override_count_match": True,
            "state_mismatch_count_zero": True,
            "issue_expert_mismatch_count_zero": True,
        },
    }


def test_packet_stream_native_canary_checker_accepts_passed_artifact() -> None:
    result = checker.check_packet_stream_native_canary(_passed_canary())

    assert result["passed"] is True
    assert result["packet_count"] == 32
    assert result["issue_candidate_count"] == 224
    assert result["issue_candidate_hash"] == "83a1a8065edf2ddd"
    assert result["expected_issue_candidate_hash"] == "83a1a8065edf2ddd"
    assert result["previous_nonempty_packet_count"] == 28
    assert result["materialized_expected_previous_nonempty_packet_count"] == 28
    assert result["state_override_count"] == 31


def test_packet_stream_native_canary_checker_rejects_runtime_blocked() -> None:
    payload = _passed_canary()
    payload["passed"] = False
    payload["ok"] = False
    payload["failures"] = ["native_runtime_blocked"]
    payload["native_runtime_blocked"] = True

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert result["failures"] == [
        "report_not_passed",
        "report_failures_not_empty",
        "native_runtime_blocked",
    ]


def test_packet_stream_native_canary_checker_rejects_payload_mutation() -> None:
    payload = _passed_canary()
    payload["native"]["payload_transfer_enabled"] = True

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "native_payload_transfer_enabled_not_false" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_bool_payload_bytes() -> None:
    payload = _passed_canary()
    payload["payload_bytes"] = False

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "payload_bytes_mismatch" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_missing_top_level_safety() -> None:
    payload = _passed_canary()
    del payload["payload_transfer_enabled"]

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "payload_transfer_enabled_not_false" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_kernel_arg_pass_allowed() -> None:
    payload = _passed_canary()
    payload["kernel_arg_pass_allowed"] = True

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "kernel_arg_pass_allowed_not_false" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_native_kernel_arg_pass_allowed() -> None:
    payload = _passed_canary()
    payload["native"]["kernel_arg_pass_allowed"] = True

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "native_kernel_arg_pass_allowed_not_false" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_missing_report_failures_field() -> None:
    payload = _passed_canary()
    del payload["failures"]

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "report_failures_not_empty" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_missing_child_failures_fields() -> None:
    payload = _passed_canary()
    del payload["materialized"]["failures"]
    del payload["native"]["failures"]

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "materialized_failures_not_empty" in result["failures"]
    assert "native_failures_not_empty" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_issue_mismatch() -> None:
    payload = _passed_canary()
    payload["comparisons"]["issue_expert_mismatch_count_zero"] = False
    payload["native"]["issue_expert_mismatch_count"] = 1

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "issue_expert_mismatch_count_zero_not_true" in result["failures"]
    assert "issue_expert_mismatch_count_nonzero" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_forged_comparison_counts() -> None:
    payload = _passed_canary()
    payload["native"]["state_override_count"] = 7
    payload["comparisons"]["state_override_count_match"] = True

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "native_materialized_state_override_count_mismatch" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_forged_hash_comparison() -> None:
    payload = _passed_canary()
    payload["native"]["issue_candidate_hash"] = "0000000000000001"
    payload["comparisons"]["issue_candidate_hash_match"] = True

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "native_materialized_issue_candidate_hash_mismatch" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_wrong_hash_kind() -> None:
    payload = _passed_canary()
    sha_like = "f" * 64
    payload["native"]["issue_candidate_hash"] = sha_like
    payload["materialized"]["expected_issue_candidate_hash"] = sha_like
    payload["comparisons"]["issue_candidate_hash_match"] = True

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "issue_candidate_hash_invalid" in result["failures"]
    assert "materialized_expected_issue_candidate_hash_invalid" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_missing_materialized_counts() -> None:
    payload = _passed_canary()
    del payload["materialized"]["packet_count"]
    del payload["materialized"]["expected_issue_candidate_count"]
    del payload["materialized"]["expected_issue_candidate_hash"]
    del payload["materialized"]["state_override_count"]

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "materialized_counts_invalid" in result["failures"]
    assert "materialized_expected_issue_candidate_hash_invalid" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_missing_native_state_override_count() -> None:
    payload = _passed_canary()
    del payload["native"]["state_override_count"]
    payload["comparisons"]["state_override_count_match"] = True

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "state_override_count_invalid" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_bool_native_returncode() -> None:
    payload = _passed_canary()
    payload["native"]["native_returncode"] = False

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "native_returncode_nonzero" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_bool_zero_mismatch_counts() -> None:
    payload = _passed_canary()
    payload["native"]["state_mismatch_count"] = False
    payload["native"]["issue_expert_mismatch_count"] = False

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "state_mismatch_count_nonzero" in result["failures"]
    assert "issue_expert_mismatch_count_nonzero" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_missing_previous_nonempty_materialized_count() -> None:
    payload = _passed_canary()
    del payload["materialized"]["expected_previous_nonempty_packet_count"]

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "previous_nonempty_packet_count_invalid" in result["failures"]


def test_packet_stream_native_canary_checker_rejects_forged_previous_nonempty_comparison() -> None:
    payload = _passed_canary()
    payload["native"]["previous_nonempty_packet_count"] = 7
    payload["comparisons"]["previous_nonempty_packet_count_match"] = True

    result = checker.check_packet_stream_native_canary(payload)

    assert result["passed"] is False
    assert "native_materialized_previous_nonempty_count_mismatch" in result["failures"]


def test_packet_stream_native_canary_checker_cli_writes_output(tmp_path: Path) -> None:
    canary_path = tmp_path / "canary.json"
    output_path = tmp_path / "check.json"
    canary_path.write_text(
        json.dumps(_passed_canary(), sort_keys=True) + "\n",
        encoding="utf-8",
    )

    rc = checker.main(
        [
            "--canary-json",
            str(canary_path),
            "--output-json",
            str(output_path),
        ]
    )

    assert rc == 0
    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True
