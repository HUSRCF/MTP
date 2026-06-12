#!/usr/bin/env python3
"""Check the ready-time payload-cache gate.

This gate validates the accounting evidence for a future full-payload cache
manager.  It does not claim endpoint latency improvement and it does not
require full_fetch to be enabled.  A valid measured-copy run may deliberately
produce a blocked decision when payloads are not ready before demand.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def check_summary(
    summary: dict[str, Any],
    *,
    root: Path,
    require_measured_copy: bool = True,
    min_demand_hit_rate: float = 0.10,
    max_ready_late_miss_rate: float = 0.20,
    min_manager_rows: int = 1,
    min_demand_count: int = 1,
) -> dict[str, Any]:
    metrics = _normalize_summary(summary)
    failures: list[str] = []

    mode = str(
        metrics.get("runtime_shadow_premap_payload_cache_manager_mode")
        or metrics.get("premap_payload_cache_manager_mode")
        or ""
    )
    if mode != "ready_time":
        failures.append(f"mode_not_ready_time:{mode or '<missing>'}")

    manager_count = _as_int(
        metrics.get("runtime_shadow_aggregate_premap_payload_cache_manager_count")
        or metrics.get("premap_payload_cache_manager_count")
    )
    demand_count = _as_int(
        metrics.get("runtime_shadow_aggregate_premap_payload_cache_demand_count")
        or metrics.get("premap_payload_cache_demand_count")
    )
    demand_hit_count = _as_int(
        metrics.get("runtime_shadow_aggregate_premap_payload_cache_demand_hit_count")
        or metrics.get("premap_payload_cache_demand_hit_count")
    )
    ready_late_miss_count = _as_int(
        metrics.get(
            "runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count"
        )
        or metrics.get("premap_payload_cache_ready_late_miss_count")
    )
    issued_fetch_count = _as_int(
        metrics.get("runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count")
        or metrics.get("premap_payload_cache_issued_fetch_count")
    )
    used_fetch_count = _as_int(
        metrics.get("runtime_shadow_aggregate_premap_payload_cache_used_fetch_count")
        or metrics.get("premap_payload_cache_used_fetch_count")
    )
    queue_batch_size = _as_int(
        metrics.get("runtime_shadow_premap_payload_cache_manager_queue_batch_size")
        or metrics.get("runtime_shadow_aggregate_premap_payload_cache_queue_batch_size_max")
        or metrics.get("premap_payload_cache_queue_batch_size_max")
    )
    queue_deadline_us = _as_float(
        metrics.get("runtime_shadow_premap_payload_cache_manager_queue_deadline_us")
        or metrics.get("runtime_shadow_aggregate_premap_payload_cache_queue_deadline_us_max")
        or metrics.get("premap_payload_cache_queue_deadline_us_max")
    )
    measured_copy_path = metrics.get(
        "runtime_shadow_premap_payload_cache_manager_measured_copy_path"
    )
    measured_copy_effective_gbps = _as_float(
        metrics.get(
            "runtime_shadow_premap_payload_cache_manager_measured_copy_effective_gbps"
        )
    )
    measured_copy_us_per_issue = _as_float(
        metrics.get(
            "runtime_shadow_premap_payload_cache_manager_measured_copy_us_per_issue"
        )
        or metrics.get("runtime_shadow_premap_payload_cache_manager_service_us_per_issue")
    )

    if manager_count < int(min_manager_rows):
        failures.append(f"manager_rows_too_low:{manager_count}")
    if demand_count < int(min_demand_count):
        failures.append(f"demand_count_too_low:{demand_count}")
    if require_measured_copy:
        if not measured_copy_path:
            failures.append("measured_copy_path_missing")
        else:
            path = Path(str(measured_copy_path)).expanduser()
            if not path.is_absolute():
                path = root / path
            if not path.exists():
                failures.append(f"measured_copy_path_missing_on_disk:{path}")
        if measured_copy_us_per_issue <= 0.0:
            failures.append(
                f"measured_copy_us_per_issue_nonpositive:{measured_copy_us_per_issue}"
            )
    if queue_batch_size <= 0:
        failures.append(f"queue_batch_size_nonpositive:{queue_batch_size}")
    if queue_deadline_us <= 0.0:
        failures.append(f"queue_deadline_us_nonpositive:{queue_deadline_us}")

    demand_hit_rate = (
        float(demand_hit_count) / float(demand_count) if demand_count > 0 else 0.0
    )
    ready_late_miss_rate = (
        float(ready_late_miss_count) / float(demand_count)
        if demand_count > 0
        else 0.0
    )
    used_per_issued_fetch = (
        float(used_fetch_count) / float(issued_fetch_count)
        if issued_fetch_count > 0
        else 0.0
    )
    allow_full_fetch = (
        not failures
        and demand_hit_rate >= float(min_demand_hit_rate)
        and ready_late_miss_rate <= float(max_ready_late_miss_rate)
    )
    decision_reason = (
        "allow"
        if allow_full_fetch
        else (
            "invalid_evidence"
            if failures
            else "ready_before_demand_threshold_not_met"
        )
    )

    return {
        "passed": not failures,
        "failures": failures,
        "allow_full_fetch": allow_full_fetch,
        "decision_reason": decision_reason,
        "boundary": (
            "ready-time payload-cache accounting gate only; not endpoint TPOT "
            "and not a real payload-transfer runtime claim"
        ),
        "metrics": {
            "mode": mode,
            "manager_count": manager_count,
            "demand_count": demand_count,
            "demand_hit_count": demand_hit_count,
            "demand_hit_rate": demand_hit_rate,
            "ready_late_miss_count": ready_late_miss_count,
            "ready_late_miss_rate": ready_late_miss_rate,
            "issued_fetch_count": issued_fetch_count,
            "used_fetch_count": used_fetch_count,
            "used_per_issued_fetch": used_per_issued_fetch,
            "queue_batch_size": queue_batch_size,
            "queue_deadline_us": queue_deadline_us,
            "measured_copy_path": measured_copy_path,
            "measured_copy_effective_gbps": measured_copy_effective_gbps,
            "measured_copy_us_per_issue": measured_copy_us_per_issue,
            "min_demand_hit_rate": float(min_demand_hit_rate),
            "max_ready_late_miss_rate": float(max_ready_late_miss_rate),
        },
    }


def _normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    metrics = summary.get("metrics")
    if isinstance(metrics, dict):
        return _with_gate_metric_aliases(metrics)
    return dict(summary)


def _with_gate_metric_aliases(metrics: dict[str, Any]) -> dict[str, Any]:
    """Accept both raw performance summaries and checker-report metrics.

    Checker reports intentionally store normalized metric names such as
    ``demand_count``.  Raw runtime summaries use longer
    ``runtime_shadow_*`` keys.  The checker may be run on either artifact, so
    normalize report-style names back into the raw-key namespace used by the
    validation code above.
    """

    aliases = {
        "mode": "runtime_shadow_premap_payload_cache_manager_mode",
        "manager_count": "runtime_shadow_aggregate_premap_payload_cache_manager_count",
        "demand_count": "runtime_shadow_aggregate_premap_payload_cache_demand_count",
        "demand_hit_count": (
            "runtime_shadow_aggregate_premap_payload_cache_demand_hit_count"
        ),
        "ready_late_miss_count": (
            "runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count"
        ),
        "issued_fetch_count": (
            "runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count"
        ),
        "used_fetch_count": (
            "runtime_shadow_aggregate_premap_payload_cache_used_fetch_count"
        ),
        "queue_batch_size": (
            "runtime_shadow_premap_payload_cache_manager_queue_batch_size"
        ),
        "queue_deadline_us": (
            "runtime_shadow_premap_payload_cache_manager_queue_deadline_us"
        ),
        "measured_copy_path": (
            "runtime_shadow_premap_payload_cache_manager_measured_copy_path"
        ),
        "measured_copy_effective_gbps": (
            "runtime_shadow_premap_payload_cache_manager_measured_copy_effective_gbps"
        ),
        "measured_copy_us_per_issue": (
            "runtime_shadow_premap_payload_cache_manager_measured_copy_us_per_issue"
        ),
    }
    normalized = dict(metrics)
    for short_key, raw_key in aliases.items():
        if raw_key not in normalized and short_key in metrics:
            normalized[raw_key] = metrics[short_key]
    return normalized


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("performance_summary", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-json", type=Path)
    parser.add_argument(
        "--expect",
        choices=("any", "allow", "block"),
        default="any",
        help="Optional decision expectation in addition to evidence validity.",
    )
    parser.add_argument("--min-demand-hit-rate", type=float, default=0.10)
    parser.add_argument("--max-ready-late-miss-rate", type=float, default=0.20)
    parser.add_argument("--min-manager-rows", type=int, default=1)
    parser.add_argument("--min-demand-count", type=int, default=1)
    parser.add_argument("--allow-unmeasured-copy", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = json.loads(args.performance_summary.read_text(encoding="utf-8"))
    result = check_summary(
        summary,
        root=args.root,
        require_measured_copy=not bool(args.allow_unmeasured_copy),
        min_demand_hit_rate=float(args.min_demand_hit_rate),
        max_ready_late_miss_rate=float(args.max_ready_late_miss_rate),
        min_manager_rows=int(args.min_manager_rows),
        min_demand_count=int(args.min_demand_count),
    )
    if args.expect == "allow" and not result["allow_full_fetch"]:
        result["passed"] = False
        result["failures"].append("expected_allow_but_blocked")
    if args.expect == "block" and result["allow_full_fetch"]:
        result["passed"] = False
        result["failures"].append("expected_block_but_allowed")
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
