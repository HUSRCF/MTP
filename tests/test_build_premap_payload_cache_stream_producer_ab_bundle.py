from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import build_premap_payload_cache_stream_producer_ab_bundle as bundle


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _baseline(path: Path) -> None:
    _write_json(
        path,
        {
            "generate_seconds_per_requested_output_token": 0.00326,
            "sample_count": 32,
            "requested_output_token_count": 2048,
        },
    )


def _candidate(path: Path) -> None:
    _write_json(
        path,
        {
            "generate_seconds_per_requested_output_token": 0.003265,
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "runtime_shadow_premap_payload_cache_direct_payload_bytes": 0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": False,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": False,
        },
    )


def _contract(path: Path, *, include_packet_count: bool = True) -> None:
    payload: dict[str, object] = {
        "passed": True,
        "contract_steps": 64,
        "contract_layers": 40,
        "contract_experts_per_layer": 225,
        "contract_expected_issue_candidate_count": 20160,
        "native_stream_issue_candidate_count": 20160,
        "native_stream_first_issue_expert": 0,
        "native_stream_last_issue_expert": 220,
        "native_stream_issue_candidate_hash": "22488eda926276f7",
        "native_stream_previous_nonempty_packet_count": 2520,
        "native_stream_persistent_state_on_device": True,
        "native_stream_issue_generation_on_device": True,
        "native_stream_vectorized_copy_used": False,
        "native_stream_graph_replay_required": True,
        "native_stream_graph_replay": True,
        "native_stream_requested_graph_replay": True,
        "payload_bytes": 0,
        "ready_credit": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "native_stream_is_current_wna16_fused_moe": False,
        "native_stream_measures_tpot": False,
    }
    if include_packet_count:
        payload["native_stream_packet_count"] = 2560
    _write_json(path, payload)


def _count_ptr(
    path: Path,
    *,
    expected_packet_count: int = 2560,
    ready_count: int = 2560,
) -> None:
    _write_json(
        path,
        {
            "passed": True,
            "expected_packet_count": expected_packet_count,
            "prelaunch_native_session_update_count_ptr_v1_abi_ready_count": ready_count,
            "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count": 0,
            "prelaunch_last_current_count_source_kind": (
                "num_tokens_post_padded_device_tensor"
            ),
            "payload_bytes": 0,
            "kernel_arg_pass": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
    )


def _args(tmp_path: Path, *, count_ptr: Path | None) -> argparse.Namespace:
    return argparse.Namespace(
        baseline_summary=tmp_path / "baseline.json",
        candidate_summary=tmp_path / "candidate.json",
        online_contract=tmp_path / "contract.json",
        count_ptr_readiness=count_ptr,
        report_json=tmp_path / "report.json",
        check_json=tmp_path / "check.json",
        summary_json=tmp_path / "summary.json",
        max_overhead_ratio=0.02,
        min_issue_candidate_count=1,
    )


def test_ab_bundle_accepts_same_source_count_ptr(tmp_path: Path) -> None:
    _baseline(tmp_path / "baseline.json")
    _candidate(tmp_path / "candidate.json")
    _contract(tmp_path / "contract.json")
    _count_ptr(tmp_path / "count_ptr.json")

    summary = bundle.build_bundle(_args(tmp_path, count_ptr=tmp_path / "count_ptr.json"))

    assert summary["passed"] is True
    assert summary["ok"] is True
    assert summary["report_passed"] is True
    assert summary["check_passed"] is True
    assert summary["report_json"] == str(tmp_path / "report.json")
    assert summary["check_json"] == str(tmp_path / "check.json")
    assert summary["count_ptr_readiness_json"] == str(tmp_path / "count_ptr.json")
    assert summary["count_ptr_ready_present"] is True
    assert summary["count_ptr_ready_passed"] is True
    assert summary["native_stream_packet_count"] == 2560
    report = json.loads((tmp_path / "report.json").read_text())
    check = json.loads((tmp_path / "check.json").read_text())
    assert report["count_ptr_ready_count"] == 2560
    assert check["count_ptr_ready_present"] is True


def test_ab_bundle_keeps_legacy_bridge_compatible(tmp_path: Path) -> None:
    _baseline(tmp_path / "baseline.json")
    _candidate(tmp_path / "candidate.json")
    _contract(tmp_path / "contract.json", include_packet_count=False)

    summary = bundle.build_bundle(_args(tmp_path, count_ptr=None))

    assert summary["passed"] is True
    assert summary["ok"] is True
    assert summary["count_ptr_ready_present"] is False
    assert summary["count_ptr_readiness_json"] is None
    assert summary["native_stream_packet_count"] == 0


def test_ab_bundle_rejects_count_ptr_packet_mismatch(tmp_path: Path) -> None:
    _baseline(tmp_path / "baseline.json")
    _candidate(tmp_path / "candidate.json")
    _contract(tmp_path / "contract.json")
    _count_ptr(tmp_path / "count_ptr.json", expected_packet_count=1, ready_count=1)

    summary = bundle.build_bundle(_args(tmp_path, count_ptr=tmp_path / "count_ptr.json"))

    assert summary["passed"] is False
    assert "report:count_ptr_readiness_failed" in summary["failures"]
    assert "report:count_ptr_expected_packet_count_mismatch" in summary["failures"]
    assert "report:count_ptr_ready_count_mismatch" in summary["failures"]
    assert "check:count_ptr_expected_packet_count_mismatch" in summary["failures"]
    assert "check:count_ptr_ready_count_mismatch" in summary["failures"]
    assert all(
        failure.startswith(("report:", "check:")) for failure in summary["failures"]
    )


def test_ab_bundle_rejects_count_ptr_ready_count_mismatch_only(tmp_path: Path) -> None:
    _baseline(tmp_path / "baseline.json")
    _candidate(tmp_path / "candidate.json")
    _contract(tmp_path / "contract.json")
    _count_ptr(tmp_path / "count_ptr.json", expected_packet_count=2560, ready_count=1)

    summary = bundle.build_bundle(_args(tmp_path, count_ptr=tmp_path / "count_ptr.json"))

    assert summary["passed"] is False
    assert "report:count_ptr_ready_count_mismatch" in summary["failures"]
    assert "check:count_ptr_ready_count_mismatch" in summary["failures"]
    assert "report:count_ptr_expected_packet_count_mismatch" not in summary["failures"]
    assert "check:count_ptr_expected_packet_count_mismatch" not in summary["failures"]
    assert all(
        failure.startswith(("report:", "check:")) for failure in summary["failures"]
    )


def test_ab_bundle_rejects_count_ptr_expected_packet_mismatch_only(
    tmp_path: Path,
) -> None:
    _baseline(tmp_path / "baseline.json")
    _candidate(tmp_path / "candidate.json")
    _contract(tmp_path / "contract.json")
    _count_ptr(tmp_path / "count_ptr.json", expected_packet_count=1, ready_count=2560)

    summary = bundle.build_bundle(_args(tmp_path, count_ptr=tmp_path / "count_ptr.json"))

    assert summary["passed"] is False
    assert "report:count_ptr_expected_packet_count_mismatch" in summary["failures"]
    assert "check:count_ptr_expected_packet_count_mismatch" in summary["failures"]
    assert "report:count_ptr_ready_count_mismatch" not in summary["failures"]
    assert "check:count_ptr_ready_count_mismatch" not in summary["failures"]
    assert all(
        failure.startswith(("report:", "check:")) for failure in summary["failures"]
    )


def test_ab_bundle_converts_report_exception_to_failed_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def raise_report(_args: argparse.Namespace) -> dict[str, object]:
        raise ValueError("bad report input")

    monkeypatch.setattr(bundle.report_builder, "build_report", raise_report)
    _write_json(tmp_path / "report.json", {"passed": True, "stale": True})
    _write_json(tmp_path / "check.json", {"passed": True, "stale": True})

    summary = bundle.build_bundle(_args(tmp_path, count_ptr=None))

    assert summary["passed"] is False
    assert summary["ok"] is False
    assert summary["report_passed"] is False
    assert summary["check_passed"] is False
    assert summary["failures"] == [
        "report:report_exception:ValueError: bad report input"
    ]
    assert summary["candidate_overhead_ratio"] is None
    assert summary["native_stream_packet_count"] is None
    assert summary["native_stream_issue_candidate_count"] is None
    assert summary["payload_bytes"] is None
    assert summary["passed_to_kernel"] is None
    assert summary["changes_kernel_launch_args"] is None
    assert json.loads((tmp_path / "report.json").read_text()) == {
        "failures": ["report:report_exception:ValueError: bad report input"],
        "mode": "payload_cache_stream_producer_production_like_ab_report",
        "passed": False,
    }
    assert json.loads((tmp_path / "check.json").read_text()) == {
        "failures": ["report:report_exception:ValueError: bad report input"],
        "mode": "premap_payload_cache_stream_producer_ab_bridge_check",
        "passed": False,
    }


def test_ab_bundle_converts_check_exception_to_failed_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _baseline(tmp_path / "baseline.json")
    _candidate(tmp_path / "candidate.json")
    _contract(tmp_path / "contract.json")

    def raise_check(*_args, **_kwargs) -> dict[str, object]:
        raise RuntimeError("bad check input")

    monkeypatch.setattr(bundle.checker, "check_report", raise_check)
    _write_json(tmp_path / "check.json", {"passed": True, "stale": True})

    summary = bundle.build_bundle(_args(tmp_path, count_ptr=None))

    assert summary["passed"] is False
    assert summary["ok"] is False
    assert summary["report_passed"] is True
    assert summary["check_passed"] is False
    assert summary["failures"] == [
        "check:check_exception:RuntimeError: bad check input"
    ]
    assert summary["candidate_overhead_ratio"] is not None
    assert summary["payload_bytes"] == 0
    assert summary["passed_to_kernel"] is False
    assert summary["changes_kernel_launch_args"] is False
    assert json.loads((tmp_path / "report.json").read_text())["passed"] is True
    assert json.loads((tmp_path / "check.json").read_text()) == {
        "failures": ["check:check_exception:RuntimeError: bad check input"],
        "mode": "premap_payload_cache_stream_producer_ab_bridge_check",
        "passed": False,
    }


def test_ab_bundle_preserves_report_failures_when_check_raises(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _baseline(tmp_path / "baseline.json")
    _candidate(tmp_path / "candidate.json")
    _contract(tmp_path / "contract.json")
    _count_ptr(tmp_path / "count_ptr.json", expected_packet_count=1, ready_count=2560)

    def raise_check(*_args, **_kwargs) -> dict[str, object]:
        raise RuntimeError("bad check input")

    monkeypatch.setattr(bundle.checker, "check_report", raise_check)

    summary = bundle.build_bundle(_args(tmp_path, count_ptr=tmp_path / "count_ptr.json"))

    assert summary["passed"] is False
    assert "report:count_ptr_readiness_failed" in summary["failures"]
    assert "report:count_ptr_expected_packet_count_mismatch" in summary["failures"]
    assert "check:check_exception:RuntimeError: bad check input" in summary["failures"]
    assert all(
        failure.startswith(("report:", "check:")) for failure in summary["failures"]
    )
