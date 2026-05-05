#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime import aggregate_shadow_events, read_shadow_jsonl  # noqa: E402


DEFAULT_METRIC_MAP = {
    "ready_mass_fraction": ("aggregate.covered_mass_mean", "policies.{policy}.ready_mass_fraction"),
    "top1_ready_rate": ("aggregate.top1_ready_rate", "policies.{policy}.ready_top1_hit_rate"),
    "weighted_top1_miss": (
        "aggregate.weighted_top1_miss_mean",
        "policies.{policy}.ready_weighted_top1_miss",
    ),
    "full_fetch_count": (
        "aggregate.full_fetch_count",
        "policies.{policy}.admission_action_counters.full_fetch.count",
    ),
    "metadata_count": (
        "aggregate.metadata_count",
        "policies.{policy}.admission_action_counters.metadata.count",
    ),
    "premap_count": (
        "aggregate.premap_count",
        "policies.{policy}.admission_action_counters.premap.count",
    ),
    "full_fetch_used_count": (
        "aggregate.full_fetch_used_count",
        "policies.{policy}.admission_action_outcomes.full_fetch.later_used_count",
    ),
    "metadata_later_used_count": (
        "aggregate.metadata_later_used_count",
        "policies.{policy}.admission_action_outcomes.metadata.later_used_count",
    ),
    "premap_later_used_count": (
        "aggregate.premap_later_used_count",
        "policies.{policy}.admission_action_outcomes.premap.later_used_count",
    ),
}
READY_METRICS = {"ready_mass_fraction", "top1_ready_rate", "weighted_top1_miss"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare runtime shadow replay aggregates with event-sim policy metrics."
    )
    parser.add_argument("--shadow-summary", type=Path, default=None)
    parser.add_argument("--shadow-jsonl", type=Path, default=None)
    parser.add_argument("--event-report", type=Path, required=True)
    parser.add_argument(
        "--policy",
        default="transition_top32_plus_gated_utility_keep_top_0.500",
    )
    parser.add_argument("--rtol", type=float, default=1e-3)
    parser.add_argument("--atol", type=float, default=1e-6)
    parser.add_argument(
        "--metric-group",
        choices=["all", "ready", "actions"],
        default="all",
        help=(
            "Use ready for fallback/stress comparisons where runtime policy may "
            "suppress actions that the event sim still requested."
        ),
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.shadow_summary is None and args.shadow_jsonl is None:
        msg = "Provide --shadow-summary or --shadow-jsonl."
        raise ValueError(msg)
    shadow = _load_shadow(args)
    event = json.loads(Path(args.event_report).read_text(encoding="utf-8"))
    checks = []
    ok = True
    metric_map = _select_metric_map(args.metric_group)
    for name, (shadow_path, event_path_template) in metric_map.items():
        event_path = event_path_template.format(policy=args.policy)
        shadow_value = _get_path(shadow, shadow_path)
        event_value = _get_path(event, event_path)
        passed = _close(float(shadow_value), float(event_value), rtol=args.rtol, atol=args.atol)
        ok = ok and passed
        checks.append(
            {
                "metric": name,
                "shadow_path": shadow_path,
                "event_path": event_path,
                "shadow_value": float(shadow_value),
                "event_value": float(event_value),
                "abs_diff": abs(float(shadow_value) - float(event_value)),
                "passed": passed,
            }
        )
    payload = {
        "ok": ok,
        "shadow_summary": str(args.shadow_summary) if args.shadow_summary else None,
        "shadow_jsonl": str(args.shadow_jsonl) if args.shadow_jsonl else None,
        "event_report": str(args.event_report),
        "policy": args.policy,
        "rtol": float(args.rtol),
        "atol": float(args.atol),
        "metric_group": str(args.metric_group),
        "checks": checks,
    }
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    if not ok:
        raise SystemExit(1)


def _load_shadow(args: argparse.Namespace) -> dict[str, Any]:
    if args.shadow_summary is not None:
        return json.loads(Path(args.shadow_summary).read_text(encoding="utf-8"))
    rows = read_shadow_jsonl(args.shadow_jsonl)
    return {"aggregate": aggregate_shadow_events(rows)}


def _select_metric_map(metric_group: str) -> dict[str, tuple[str, str]]:
    if metric_group == "all":
        return DEFAULT_METRIC_MAP
    if metric_group == "ready":
        return {key: value for key, value in DEFAULT_METRIC_MAP.items() if key in READY_METRICS}
    if metric_group == "actions":
        return {
            key: value for key, value in DEFAULT_METRIC_MAP.items() if key not in READY_METRICS
        }
    msg = f"Unknown metric_group={metric_group!r}."
    raise ValueError(msg)


def _get_path(payload: dict[str, Any], path: str) -> Any:
    if path.startswith("policies."):
        prefix = "policies."
        remainder = path[len(prefix) :]
        policies = payload["policies"]
        for policy_name in sorted(policies, key=len, reverse=True):
            marker = policy_name + "."
            if remainder.startswith(marker):
                return _get_path(policies[policy_name], remainder[len(marker) :])
    current: Any = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            msg = f"Missing path {path!r} at {part!r}."
            raise KeyError(msg)
    return current


def _close(left: float, right: float, *, rtol: float, atol: float) -> bool:
    return abs(left - right) <= float(atol) + float(rtol) * max(abs(left), abs(right))


if __name__ == "__main__":
    main()
