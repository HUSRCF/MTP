#!/usr/bin/env python3
"""Build and check the payload-cache stream producer A/B bundle.

This is a thin orchestration wrapper around
``build_premap_payload_cache_stream_producer_production_ab_report.py`` and
``check_premap_payload_cache_stream_producer_ab_bridge.py``.  It is intended for
same-source production-like runs where the optional count-pointer readiness
artifact should travel with the A/B report.

The script does not run vLLM, move payload bytes, grant readiness, or pass kernel
arguments.  It only materializes report/check JSON from already-produced
artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import (
    build_premap_payload_cache_stream_producer_production_ab_report as report_builder,
)
from scripts import check_premap_payload_cache_stream_producer_ab_bridge as checker


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _artifact_paths(args: argparse.Namespace) -> dict[str, object]:
    return {
        "report_json": str(args.report_json),
        "check_json": str(args.check_json),
        "count_ptr_readiness_json": (
            str(args.count_ptr_readiness)
            if args.count_ptr_readiness is not None
            else None
        ),
    }


def _base_summary(args: argparse.Namespace) -> dict[str, object]:
    return {
        "mode": "payload_cache_stream_producer_ab_bundle",
        **_artifact_paths(args),
        "candidate_overhead_ratio": None,
        "native_stream_packet_count": None,
        "native_stream_issue_candidate_count": None,
        "count_ptr_ready_present": None,
        "count_ptr_ready_passed": None,
        "payload_bytes": None,
        "passed_to_kernel": None,
        "changes_kernel_launch_args": None,
    }


def build_bundle(args: argparse.Namespace) -> dict[str, object]:
    report_args = argparse.Namespace(
        baseline_summary=args.baseline_summary,
        candidate_summary=args.candidate_summary,
        online_contract=args.online_contract,
        count_ptr_readiness=args.count_ptr_readiness,
        output_json=args.report_json,
        max_overhead_ratio=args.max_overhead_ratio,
    )
    try:
        report = report_builder.build_report(report_args)
    except Exception as exc:  # pragma: no cover - exact failures are input-dependent.
        failure = f"report:report_exception:{type(exc).__name__}: {exc}"
        report = {
            "passed": False,
            "failures": [failure],
            "mode": "payload_cache_stream_producer_production_like_ab_report",
        }
        check = {
            "passed": False,
            "failures": [failure],
            "mode": "premap_payload_cache_stream_producer_ab_bridge_check",
        }
        _write_json(args.report_json, report)
        _write_json(args.check_json, check)
        return {
            **_base_summary(args),
            "passed": False,
            "ok": False,
            "failures": [failure],
            "report_passed": False,
            "check_passed": False,
        }
    _write_json(args.report_json, report)
    try:
        check = checker.check_report(
            report,
            max_overhead_ratio=args.max_overhead_ratio,
            min_issue_candidate_count=args.min_issue_candidate_count,
        )
    except Exception as exc:  # pragma: no cover - exact failures are input-dependent.
        failure = f"check:check_exception:{type(exc).__name__}: {exc}"
        check = {
            "passed": False,
            "failures": [failure],
            "mode": "premap_payload_cache_stream_producer_ab_bridge_check",
        }
        _write_json(args.check_json, check)
        return {
            **_base_summary(args),
            "passed": False,
            "ok": False,
            "failures": [
                *(
                    f"report:{report_failure}"
                    for report_failure in report.get("failures", [])
                ),
                failure,
            ],
            "report_passed": bool(report.get("passed")),
            "check_passed": False,
            "candidate_overhead_ratio": report.get("candidate_overhead_ratio"),
            "native_stream_packet_count": report.get("native_stream_packet_count"),
            "native_stream_issue_candidate_count": report.get(
                "native_stream_issue_candidate_count"
            ),
            "count_ptr_ready_present": report.get("count_ptr_ready_present"),
            "count_ptr_ready_passed": report.get("count_ptr_ready_passed"),
            "payload_bytes": report.get("payload_bytes"),
            "passed_to_kernel": report.get("passed_to_kernel"),
            "changes_kernel_launch_args": report.get("changes_kernel_launch_args"),
        }
    _write_json(args.check_json, check)
    return {
        **_base_summary(args),
        "passed": bool(report.get("passed") is True and check.get("passed") is True),
        "ok": bool(report.get("passed") is True and check.get("passed") is True),
        "failures": [
            *(f"report:{failure}" for failure in report.get("failures", [])),
            *(f"check:{failure}" for failure in check.get("failures", [])),
        ],
        "report_passed": bool(report.get("passed")),
        "check_passed": bool(check.get("passed")),
        "candidate_overhead_ratio": report.get("candidate_overhead_ratio"),
        "native_stream_packet_count": report.get("native_stream_packet_count"),
        "native_stream_issue_candidate_count": report.get(
            "native_stream_issue_candidate_count"
        ),
        "count_ptr_ready_present": report.get("count_ptr_ready_present"),
        "count_ptr_ready_passed": report.get("count_ptr_ready_passed"),
        "payload_bytes": report.get("payload_bytes"),
        "passed_to_kernel": report.get("passed_to_kernel"),
        "changes_kernel_launch_args": report.get("changes_kernel_launch_args"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-summary", type=Path, required=True)
    parser.add_argument("--candidate-summary", type=Path, required=True)
    parser.add_argument("--online-contract", type=Path, required=True)
    parser.add_argument("--count-ptr-readiness", type=Path)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--check-json", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--max-overhead-ratio", type=float, default=0.02)
    parser.add_argument("--min-issue-candidate-count", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_bundle(args)
    if args.summary_json is not None:
        _write_json(args.summary_json, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
