#!/usr/bin/env python3
"""Summarize bounded-cache prefetch lab replay reports."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--csv-output", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--md-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, Any]] = []
    for report in args.reports:
        payload = json.loads(report.read_text(encoding="utf-8"))
        rows.extend(extract_rows(report, payload))
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.csv_output is not None:
        args.csv_output.parent.mkdir(parents=True, exist_ok=True)
        write_csv(args.csv_output, rows)
    markdown = render_markdown(rows)
    if args.md_output is not None:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(markdown, encoding="utf-8")
    print(markdown)


def extract_rows(report: Path, payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        return []
    config = payload.get("config", {})
    metadata = payload.get("metadata", {})
    stream_shapes = payload.get("stream_shapes", {})
    queue_coalesce_scope = config.get("queue_coalesce_scope", "token_layer")
    rows = []
    for row in payload.get("rows", []):
        if not _include_policy(str(row.get("policy", ""))):
            continue
        rows.append(
            {
                "report": report.name,
                "campaign": metadata.get("campaign"),
                "dataset": metadata.get("dataset"),
                "split": metadata.get("split"),
                "trace_source": metadata.get("trace_source"),
                "run_tag": metadata.get("run_tag"),
                "max_token_examples": metadata.get("max_token_examples"),
                "policy": row.get("policy"),
                "transition_topk": config.get("transition_topk"),
                "cache_capacity": config.get("cache_capacity"),
                "bandwidth_gbps": config.get("bandwidth_gbps"),
                "overlap_factor": config.get("overlap_factor"),
                "manager_us_per_issue": config.get("manager_us_per_issue"),
                "lookup_us_per_demand": config.get("lookup_us_per_demand"),
                "decision_us_per_token_layer": config.get("decision_us_per_token_layer"),
                "measured_copy_us_per_issue": config.get("measured_copy_us_per_issue"),
                "measured_copy_stat": config.get("measured_copy_stat"),
                "measured_copy_effective_gbps": config.get("measured_copy_effective_gbps"),
                "max_inflight_prefetches": config.get("max_inflight_prefetches"),
                "queue_model": config.get("queue_model", "burst"),
                "queue_batch_size": config.get("queue_batch_size"),
                "queue_coalesce_scope": queue_coalesce_scope,
                "queue_policy": config.get("queue_policy"),
                "queue_admission_policy": config.get(
                    "queue_admission_policy", "prefix"
                ),
                "queue_wait_us_per_overflow": config.get("queue_wait_us_per_overflow"),
                "queue_event_interval_us": config.get("queue_event_interval_us", 0.0),
                "queue_deadline_us": config.get("queue_deadline_us", 0.0),
                "stress_fallback": config.get("stress_fallback"),
                "demand_stream_hash": payload.get("demand_stream_hash"),
                "true_router_stream_hash": payload.get("true_router_stream_hash"),
                "policy_config_hash": payload.get("policy_config_hash"),
                "demand_stream_rows": stream_shapes.get("demand_stream_rows"),
                "true_router_stream_rows": stream_shapes.get("true_router_stream_rows"),
                "demand_hit_rate": row.get("demand_hit_rate"),
                "issued_fetch_count": row.get("issued_fetch_count"),
                "used_per_issued_fetch": row.get(
                    "used_per_issued_fetch",
                    row.get("used_per_extra_byte"),
                ),
                "evicted_before_use_count": row.get("evicted_before_use_count"),
                "demand_stall_ms": float(row.get("demand_stall_us", 0.0)) / 1000.0,
                "prefetch_dma_ms": float(row.get("prefetch_dma_us", 0.0)) / 1000.0,
                "prefetch_queue_wait_ms": float(
                    row.get("prefetch_queue_wait_us", 0.0)
                )
                / 1000.0,
                "prefetch_queue_model": row.get("prefetch_queue_model"),
                "prefetch_queue_backpressure_semantics": row.get(
                    "prefetch_queue_backpressure_semantics",
                    row.get("queue_backpressure_semantics"),
                ),
                "prefetch_queue_policy": row.get("prefetch_queue_policy"),
                "prefetch_queue_admission_policy": row.get(
                    "prefetch_queue_admission_policy",
                    config.get("queue_admission_policy", "prefix"),
                ),
                "prefetch_queue_batch_size": row.get("prefetch_queue_batch_size"),
                "prefetch_queue_coalesce_scope": row.get(
                    "prefetch_queue_coalesce_scope",
                    queue_coalesce_scope,
                ),
                "prefetch_queue_batch_count": row.get("prefetch_queue_batch_count"),
                "prefetch_queue_service_ms": float(
                    row.get("prefetch_queue_service_us", row.get("prefetch_dma_us", 0.0))
                )
                / 1000.0,
                "prefetch_queue_total_span_ms": float(
                    row.get("prefetch_queue_total_span_us", 0.0)
                )
                / 1000.0,
                "prefetch_queue_max_delay_ms": float(
                    row.get("prefetch_queue_max_delay_us", 0.0)
                )
                / 1000.0,
                "prefetch_queue_event_interval_us": row.get(
                    "prefetch_queue_event_interval_us", 0.0
                ),
                "prefetch_queue_deadline_us": row.get(
                    "prefetch_queue_deadline_us", 0.0
                ),
                "prefetch_ready_late_miss_count": row.get(
                    "prefetch_ready_late_miss_count", 0
                ),
                "prefetch_late_completion_unused_count": row.get(
                    "prefetch_late_completion_unused_count", 0
                ),
                "prefetch_backpressure_dropped_count": row.get(
                    "prefetch_backpressure_dropped_count"
                ),
                "prefetch_queue_pressure": row.get("prefetch_queue_pressure"),
                "prefetch_queue_overflow_count": row.get(
                    "prefetch_queue_overflow_count"
                ),
                "prefetch_max_issue_burst": row.get("prefetch_max_issue_burst"),
                "total_cost_ms": float(row.get("total_cost_us", 0.0)) / 1000.0,
                "net_saved_ms_vs_transition": float(
                    row.get("net_saved_us_vs_transition", 0.0)
                )
                / 1000.0,
                "net_saved_ms_vs_no_prefetch": float(
                    row.get("net_saved_us_vs_no_prefetch", 0.0)
                )
                / 1000.0,
                "stress_shutdown_count": row.get("stress_shutdown_count", 0),
            }
        )
    return rows


def _include_policy(policy: str) -> bool:
    return (
        policy == "no_prefetch"
        or policy.startswith("transition_top")
        or policy == "oracle_used"
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "report",
        "campaign",
        "dataset",
        "split",
        "trace_source",
        "run_tag",
        "max_token_examples",
        "policy",
        "transition_topk",
        "cache_capacity",
        "bandwidth_gbps",
        "overlap_factor",
        "manager_us_per_issue",
        "lookup_us_per_demand",
        "decision_us_per_token_layer",
        "measured_copy_us_per_issue",
        "measured_copy_stat",
        "measured_copy_effective_gbps",
        "max_inflight_prefetches",
        "queue_model",
        "queue_batch_size",
        "queue_coalesce_scope",
        "queue_policy",
        "queue_admission_policy",
        "queue_wait_us_per_overflow",
        "queue_event_interval_us",
        "queue_deadline_us",
        "stress_fallback",
        "demand_stream_hash",
        "true_router_stream_hash",
        "policy_config_hash",
        "demand_stream_rows",
        "true_router_stream_rows",
        "demand_hit_rate",
        "issued_fetch_count",
        "used_per_issued_fetch",
        "evicted_before_use_count",
        "demand_stall_ms",
        "prefetch_dma_ms",
        "prefetch_queue_wait_ms",
        "prefetch_queue_model",
        "prefetch_queue_backpressure_semantics",
        "prefetch_queue_policy",
        "prefetch_queue_admission_policy",
        "prefetch_queue_batch_size",
        "prefetch_queue_coalesce_scope",
        "prefetch_queue_batch_count",
        "prefetch_queue_service_ms",
        "prefetch_queue_total_span_ms",
        "prefetch_queue_max_delay_ms",
        "prefetch_queue_event_interval_us",
        "prefetch_queue_deadline_us",
        "prefetch_ready_late_miss_count",
        "prefetch_late_completion_unused_count",
        "prefetch_backpressure_dropped_count",
        "prefetch_queue_pressure",
        "prefetch_queue_overflow_count",
        "prefetch_max_issue_burst",
        "total_cost_ms",
        "net_saved_ms_vs_transition",
        "net_saved_ms_vs_no_prefetch",
        "stress_shutdown_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Prefetch Cache Lab Summary",
        "",
        "Boundary:",
        "",
        "```text",
        "Bounded-cache lab replay only; not endpoint TPOT and not a real vLLM cache manager.",
        "```",
        "",
        "| report | policy | cap | stress | hit | issued | used/issued | late miss | queue wait ms | queue service ms | queue span ms | max delay ms | queue pressure | evicted-unused | total ms | net vs transition ms |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {report} | {policy} | {cap} | {stress} | {hit:.2%} | {issued} | {used:.3f} | {late_miss} | {queue_wait:.3f} | {queue_service:.3f} | {queue_span:.3f} | {queue_max_delay:.3f} | {queue_pressure:.3f} | {evicted} | {total:.3f} | {net:.3f} |".format(
                report=_report_label(row),
                policy=row["policy"],
                cap=row["cache_capacity"],
                stress=row["stress_fallback"],
                hit=float(row["demand_hit_rate"] or 0.0),
                issued=int(row["issued_fetch_count"] or 0),
                used=float(row["used_per_issued_fetch"] or 0.0),
                late_miss=int(row["prefetch_ready_late_miss_count"] or 0),
                queue_wait=float(row["prefetch_queue_wait_ms"] or 0.0),
                queue_service=float(row["prefetch_queue_service_ms"] or 0.0),
                queue_span=float(row["prefetch_queue_total_span_ms"] or 0.0),
                queue_max_delay=float(row["prefetch_queue_max_delay_ms"] or 0.0),
                queue_pressure=float(row["prefetch_queue_pressure"] or 0.0),
                evicted=int(row["evicted_before_use_count"] or 0),
                total=float(row["total_cost_ms"] or 0.0),
                net=float(row["net_saved_ms_vs_transition"] or 0.0),
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "```text",
            "Positive net_saved_ms_vs_transition means the policy beats the",
            "configured transition_topK cache-manager baseline under the same cache capacity,",
            "bandwidth, overlap, and cost model.  It remains a lab replay result,",
            "not endpoint runtime evidence.",
            "",
            "Queue columns are lab-manager approximations. burst uses aggregate",
            "burst-overflow accounting; event uses a small virtual batch queue",
            "with measured-copy service time, logical arrivals, deadline flush,",
            "and drop/wait admission. In event-ready mode, a prefetch counts as",
            "a hit only if its virtual H2D completion is no later than the",
            "token/layer demand deadline. Late in-flight copies are reported as",
            "prefetch_ready_late_miss_count.",
            "The event model currently uses global coalescing.",
            "Neither is a production vLLM DMA scheduler.",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _report_label(row: dict[str, Any]) -> str:
    parts = [
        str(row.get("dataset") or ""),
        str(row.get("split") or ""),
        str(row.get("run_tag") or row.get("report") or ""),
    ]
    label = "/".join(part for part in parts if part)
    return label or str(row.get("report"))


if __name__ == "__main__":
    main()
