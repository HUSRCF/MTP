#!/usr/bin/env python3
"""Summarize controlled cache-manager prototype smoke artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        type=Path,
        required=True,
        help="Cache-manager prototype smoke JSON. May be passed more than once.",
    )
    parser.add_argument("--policy-suffix", default="_plus_utility_keep50")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--md-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = [
        summarize_case(
            json.loads(path.read_text(encoding="utf-8")),
            source_path=str(path),
            policy_suffix=args.policy_suffix,
        )
        for path in args.input
    ]
    payload = {
        "boundary": (
            "Controlled cache-manager prototype smoke only; not endpoint TPOT "
            "and not a real vLLM cache-manager implementation."
        ),
        "policy_suffix": args.policy_suffix,
        "cases": cases,
    }
    markdown = render_markdown(payload)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.md_output is not None:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(markdown, encoding="utf-8")
    print(markdown)


def summarize_case(
    payload: dict[str, Any], *, source_path: str, policy_suffix: str
) -> dict[str, Any]:
    rows = [row for row in payload.get("rows", []) if isinstance(row, dict)]
    config = payload.get("config") or {}
    transition_policy = _transition_policy_name(config)
    transition = _find_unique_policy(rows, transition_policy)
    candidate_policy = f"{transition_policy}{policy_suffix}"
    candidate = _find_unique_policy(rows, candidate_policy)
    decision = payload.get("cache_lab_gate_decision")
    metadata = payload.get("metadata") or {}
    snapshot = (candidate or {}).get("cache_manager_snapshot") or {}
    return {
        "source_path": source_path,
        "dataset": metadata.get("dataset"),
        "split": metadata.get("split"),
        "run_tag": metadata.get("run_tag"),
        "allow_full_fetch_mtp": _gate_allow(decision),
        "gate_reason": _gate_reason(decision),
        "payload_capacity": _int_or_none(
            _get_decision_or_config(decision, config, "payload_capacity", "cache_capacity")
        ),
        "overlap_factor": _float_or_none(
            _get_decision_or_config(decision, config, "overlap_factor", "overlap_factor")
        ),
        "manager_us_per_issue": _float_or_none(
            _get_decision_or_config(
                decision, config, "manager_us_per_issue", "manager_us_per_issue"
            )
        ),
        "bandwidth_gbps": _float_or_none(
            _get_decision_or_config(decision, config, "bandwidth_gbps", "bandwidth_gbps")
        ),
        "transition_policy": transition_policy,
        "transition_found": transition is not None,
        "candidate_policy": (candidate or {}).get("policy"),
        "candidate_expected_policy": candidate_policy,
        "candidate_found": candidate is not None,
        "candidate_net_saved_us_vs_transition": _float_or_none(
            (candidate or {}).get("net_saved_us_vs_transition")
        ),
        "candidate_stress_shutdown_count": _int_or_none(
            (candidate or {}).get("stress_shutdown_count")
        ),
        "candidate_issued_fetch_count": _int_or_none(
            (candidate or {}).get("issued_fetch_count")
        ),
        "candidate_used_fetch_count": _int_or_none(
            (candidate or {}).get("used_fetch_count")
        ),
        "candidate_unused_fetch_count": _int_or_none(
            (candidate or {}).get("unused_fetch_count")
        ),
        "candidate_evicted_before_use_count": _int_or_none(
            (candidate or {}).get("evicted_before_use_count")
        ),
        "transition_issued_fetch_count": _int_or_none(
            (transition or {}).get("issued_fetch_count")
        ),
        "transition_used_fetch_count": _int_or_none(
            (transition or {}).get("used_fetch_count")
        ),
        "manager_snapshot": snapshot,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Controlled Cache-Manager Prototype Summary",
        "",
        "Boundary:",
        "",
        "```text",
        str(payload["boundary"]),
        "```",
        "",
        f"Policy suffix: `{payload['policy_suffix']}`",
        "",
        "| case | allow | reason | capacity | overlap | manager us/issue | bw GB/s | candidate net us vs transition | issued | used | unused | stress shutdown |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in payload["cases"]:
        label = "/".join(
            str(part)
            for part in (case.get("dataset"), case.get("split"), case.get("run_tag"))
            if part not in (None, "")
        )
        lines.append(
            "| {label} | {allow} | {reason} | {capacity} | {overlap} | {manager} | {bw} | {net} | {issued} | {used} | {unused} | {shutdown} |".format(
                label=label,
                allow=case["allow_full_fetch_mtp"],
                reason=case.get("gate_reason") or "",
                capacity=_fmt(case.get("payload_capacity")),
                overlap=_fmt(case.get("overlap_factor")),
                manager=_fmt(case.get("manager_us_per_issue")),
                bw=_fmt(case.get("bandwidth_gbps")),
                net=_fmt(case.get("candidate_net_saved_us_vs_transition")),
                issued=_fmt(case.get("candidate_issued_fetch_count")),
                used=_fmt(case.get("candidate_used_fetch_count")),
                unused=_fmt(case.get("candidate_unused_fetch_count")),
                shutdown=_fmt(case.get("candidate_stress_shutdown_count")),
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "```text",
            "The controlled manager now owns bounded residency, demand hits/misses,",
            "prefetch issue/use accounting, and unused-prefetch eviction counters.",
            "The gate decides whether MTP full_fetch extras are admitted; when the",
            "gate rejects, gated policies collapse to the transition baseline.",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _find_unique_policy(
    rows: list[dict[str, Any]], policy: str
) -> dict[str, Any] | None:
    matches = [row for row in rows if row.get("policy") == policy]
    if len(matches) > 1:
        raise ValueError(f"Expected one row for policy {policy!r}, found {len(matches)}.")
    return matches[0] if matches else None


def _transition_policy_name(config: dict[str, Any]) -> str:
    value = config.get("transition_topk")
    if value is not None:
        return f"transition_top{int(value)}"
    return "transition_top32"


def _gate_allow(decision: Any) -> bool | None:
    if not isinstance(decision, dict):
        return None
    value = decision.get("allow_full_fetch_mtp")
    return None if value is None else bool(value)


def _gate_reason(decision: Any) -> str:
    if not isinstance(decision, dict):
        return "gate_decision_missing"
    return str(decision.get("reason") or "gate_reason_missing")


def _get_decision_or_config(
    decision: Any, config: dict[str, Any], decision_key: str, config_key: str
) -> Any:
    if isinstance(decision, dict) and decision.get(decision_key) is not None:
        return decision[decision_key]
    return config.get(config_key)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


if __name__ == "__main__":
    main()
