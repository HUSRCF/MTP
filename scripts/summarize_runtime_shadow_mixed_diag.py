#!/usr/bin/env python3
"""Summarize mixed runtime-shadow diagnostics.

This is intentionally separate from summarize_premap_shadow_contract.py:
mixed diagnostics may include outcome aggregates, descriptor-order summaries,
decoder timing, and premap summaries in the same JSONL file.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

from mtp_expert_prefetch.runtime import aggregate_shadow_events, read_shadow_jsonl


CORE_EVENT_TYPES = {
    "decoder_layer_timing",
    "descriptor_summary_min",
    "outcome_aggregate",
    "premap_summary",
}

DEFAULT_ALLOWED_EVENT_TYPES = CORE_EVENT_TYPES | {"descriptor_layer_timing"}


class StrictValidationError(ValueError):
    """Raised when a mixed-shadow diagnostic violates its expected contract."""


def _numeric_stats(values: Iterable[Any]) -> dict[str, float | int] | None:
    nums: list[float] = []
    for value in values:
        if value is None:
            continue
        try:
            nums.append(float(value))
        except (TypeError, ValueError):
            continue
    if not nums:
        return None
    nums.sort()

    def percentile(q: float) -> float:
        idx = int(round((len(nums) - 1) * q))
        idx = max(0, min(len(nums) - 1, idx))
        return nums[idx]

    return {
        "count": len(nums),
        "sum": sum(nums),
        "mean": mean(nums),
        "p50": median(nums),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "max": nums[-1],
    }


def _collect_event_stats(
    rows: list[dict[str, Any]], event_type: str, fields: list[str]
) -> dict[str, dict[str, float | int]]:
    event_rows = [row for row in rows if row.get("event_type") == event_type]
    stats: dict[str, dict[str, float | int]] = {}
    for field in fields:
        field_stats = _numeric_stats(row.get(field) for row in event_rows)
        if field_stats is not None:
            stats[field] = field_stats
    return stats


def validate_mixed_diagnostic(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    *,
    allowed_event_types: set[str] | None = None,
    require_decode_phase: bool = False,
) -> None:
    """Validate the mixed diagnostic contract.

    The contract is intentionally about event boundaries and premap safety, not
    endpoint performance: premap remains descriptor/address-only, descriptor
    order remains minimal/count-only, and outcome rows are aggregate rows.
    """

    allowed = allowed_event_types or DEFAULT_ALLOWED_EVENT_TYPES
    event_counts = summary["event_counts"]
    errors: list[str] = []

    unknown = sorted(set(event_counts) - allowed)
    if unknown:
        errors.append(f"unexpected event types: {unknown}")

    missing = sorted(event for event in CORE_EVENT_TYPES if event_counts.get(event, 0) <= 0)
    if missing:
        errors.append(f"missing required event types: {missing}")

    core_counts = {event: event_counts.get(event, 0) for event in CORE_EVENT_TYPES}
    positive_core_counts = {count for count in core_counts.values() if count > 0}
    if len(positive_core_counts) > 1:
        errors.append(f"core event counts differ: {core_counts}")

    descriptor_layer_count = event_counts.get("descriptor_layer_timing", 0)
    decoder_count = event_counts.get("decoder_layer_timing", 0)
    if descriptor_layer_count and descriptor_layer_count != decoder_count:
        errors.append(
            "descriptor_layer_timing count must match decoder_layer_timing "
            f"when present: {descriptor_layer_count} != {decoder_count}"
        )

    aggregate = summary["aggregate"]
    if int(aggregate.get("premap_summary_payload_bytes", 0) or 0) != 0:
        errors.append("premap_summary_payload_bytes must remain zero")

    premap_rows = [row for row in rows if row.get("event_type") == "premap_summary"]
    for idx, row in enumerate(premap_rows):
        if int(row.get("premap_payload_bytes", 0) or 0) != 0:
            errors.append(f"premap row {idx} has non-zero payload bytes")
            break
        if bool(row.get("premap_changes_router", False)):
            errors.append(f"premap row {idx} changes router")
            break
        if bool(row.get("premap_changes_descriptor_order", False)):
            errors.append(f"premap row {idx} changes descriptor order")
            break
        if bool(row.get("premap_ready_credit", False)):
            errors.append(f"premap row {idx} grants ready credit")
            break

    descriptor_rows = [
        row for row in rows if row.get("event_type") == "descriptor_summary_min"
    ]
    bad_descriptor_modes = sorted(
        {
            str(row.get("descriptor_order_metrics_mode"))
            for row in descriptor_rows
            if str(row.get("descriptor_order_metrics_mode")) not in {"count_only", "none"}
        }
    )
    if bad_descriptor_modes:
        errors.append(f"unexpected descriptor_order_metrics_mode: {bad_descriptor_modes}")

    non_minimal_descriptor_rows = [
        row
        for row in descriptor_rows
        if row.get("descriptor_order_lru_at_8") is not None
        or row.get("descriptor_order_hit_rate") is not None
    ]
    if non_minimal_descriptor_rows:
        errors.append("descriptor_summary_min rows must not contain compact LRU/order-hit metrics")

    outcome_modes = {
        str(row.get("outcome_logging_mode"))
        for row in rows
        if row.get("event_type") == "outcome_aggregate"
    }
    if outcome_modes - {"aggregate"}:
        errors.append(f"unexpected outcome logging modes: {sorted(outcome_modes)}")

    if require_decode_phase and "decode" not in summary["decoder_by_phase"]:
        errors.append("decode phase was required but is absent")

    if errors:
        raise StrictValidationError("; ".join(errors))


def summarize(path: Path) -> dict[str, Any]:
    rows = read_shadow_jsonl(path)
    aggregate = aggregate_shadow_events(rows)
    event_counts = Counter(str(row.get("event_type")) for row in rows)

    decoder_by_phase: dict[str, Any] = {}
    slow_decoder_rows: list[tuple[float, dict[str, Any]]] = []
    phase_values: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        if row.get("event_type") != "decoder_layer_timing":
            continue
        elapsed = row.get("decoder_layer_elapsed_us")
        phase = str(row.get("decoder_layer_phase"))
        phase_values[phase].append(elapsed)
        try:
            slow_decoder_rows.append((float(elapsed), row))
        except (TypeError, ValueError):
            pass
    for phase, values in sorted(phase_values.items()):
        phase_stats = _numeric_stats(values)
        if phase_stats is not None:
            decoder_by_phase[phase] = phase_stats

    slow_decoder_rows.sort(key=lambda item: item[0], reverse=True)
    slowest = [
        {
            "decoder_layer_elapsed_us": elapsed,
            "request_id": row.get("request_id"),
            "layer": row.get("layer"),
            "token_index": row.get("token_index"),
            "phase": row.get("decoder_layer_phase"),
        }
        for elapsed, row in slow_decoder_rows[:5]
    ]

    categorical: dict[str, dict[str, int]] = {}
    for event_type, field in [
        ("descriptor_summary_min", "descriptor_order_policy"),
        ("descriptor_summary_min", "descriptor_order_execution_mode"),
        ("descriptor_summary_min", "descriptor_order_metrics_mode"),
        ("outcome_aggregate", "outcome_logging_mode"),
    ]:
        counter = Counter(
            str(row.get(field))
            for row in rows
            if row.get("event_type") == event_type
        )
        if counter:
            categorical[f"{event_type}.{field}"] = dict(sorted(counter.items()))

    selected_aggregate_keys = [
        "outcome_aggregate_count",
        "descriptor_order_summary_count",
        "decoder_layer_timing_count",
        "premap_summary_count",
        "premap_summary_descriptor_count",
        "premap_summary_actual_bytes",
        "premap_summary_payload_bytes",
        "premap_address_manager_count",
        "premap_address_new_count",
        "premap_address_reused_count",
        "premap_address_evicted_count",
        "premap_address_resident_count_max",
        "premap_address_resident_descriptor_bytes_max",
        "premap_address_prepared_descriptor_actual_bytes_max",
        "premap_address_reuse_rate_mean",
        "premap_address_eviction_pressure_mean",
        "premap_consumer_mapping_count",
        "premap_consumer_address_hit_rate",
        "premap_consumer_descriptor_handle_hit_rate",
        "premap_consumer_lookup_after_prepare_rate",
        "premap_consumer_real_descriptor_handle_hit_count",
        "premap_consumer_real_descriptor_handle_miss_count",
        "premap_consumer_real_descriptor_handle_hit_rate",
        "premap_consumer_real_descriptor_handle_available_rate",
        "premap_consumer_real_descriptor_handle_packed_weight_hit_count",
        "premap_consumer_real_descriptor_handle_packed_weight_miss_count",
        "premap_consumer_real_descriptor_handle_scale_metadata_hit_count",
        "premap_consumer_real_descriptor_handle_scale_metadata_miss_count",
        "premap_consumer_real_descriptor_handle_aux_metadata_hit_count",
        "premap_consumer_real_descriptor_handle_aux_metadata_miss_count",
        "premap_consumer_real_descriptor_handle_resolver_disabled_count",
        "premap_consumer_real_descriptor_handle_consumer_layer_missing_count",
        "premap_consumer_real_descriptor_handle_expert_map_miss_count",
        "premap_consumer_real_descriptor_handle_no_handle_parts_count",
        "premap_consumer_real_descriptor_handle_binding_mismatch_count",
        "premap_consumer_real_descriptor_handle_for_address_miss_count",
        "premap_consumer_readonly_lookup_count",
        "premap_consumer_readonly_handle_hit_count",
        "premap_consumer_readonly_handle_miss_count",
        "premap_consumer_readonly_handle_hit_rate",
        "premap_consumer_readonly_evicted_before_consume_count",
        "premap_consumer_readonly_evicted_before_consume_rate",
        "premap_consumer_readonly_stale_handle_count",
        "premap_consumer_readonly_stale_handle_rate",
        "premap_consumer_readonly_handle_parity_ok_rate",
        "premap_consumer_error_count",
        "descriptor_order_gate_allow_count",
        "descriptor_order_gate_evidence_found_count",
    ]

    return {
        "path": str(path),
        "row_count": len(rows),
        "event_counts": dict(sorted(event_counts.items())),
        "aggregate": {
            key: aggregate[key] for key in selected_aggregate_keys if key in aggregate
        },
        "decoder_by_phase": decoder_by_phase,
        "decoder_slowest_rows": slowest,
        "outcome_aggregate_stats": _collect_event_stats(
            rows,
            "outcome_aggregate",
            [
                "token_count",
                "topk_entry_count",
                "routed_expert_count",
                "top_k",
                "topk_weight_mass_sum",
                "top1_weight_sum",
                "top1_weight_mean",
            ],
        ),
        "descriptor_order_stats": _collect_event_stats(
            rows,
            "descriptor_summary_min",
            [
                "descriptor_order_build_us",
                "descriptor_tile_request_count",
                "descriptor_unique_b_tiles",
                "descriptor_window_count",
                "descriptor_order_gate_allow",
            ],
        ),
        "premap_stats": _collect_event_stats(
            rows,
            "premap_summary",
            [
                "premap_build_us",
                "counter_update_us",
                "premap_descriptor_count",
                "premap_address_reuse_rate",
                "premap_address_resident_descriptor_bytes",
            ],
        ),
        "categorical": categorical,
    }


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# Mixed Runtime Shadow Diagnostic Summary")
    lines.append("")
    lines.append(f"- path: `{summary['path']}`")
    lines.append(f"- rows: `{summary['row_count']}`")
    lines.append("")
    lines.append("## Event Counts")
    lines.append("")
    lines.append("| event_type | count |")
    lines.append("| --- | ---: |")
    for event_type, count in summary["event_counts"].items():
        lines.append(f"| `{event_type}` | {count} |")
    lines.append("")

    if summary["aggregate"]:
        lines.append("## Selected Aggregate Fields")
        lines.append("")
        lines.append("| field | value |")
        lines.append("| --- | ---: |")
        for key, value in summary["aggregate"].items():
            lines.append(f"| `{key}` | {_fmt(value)} |")
        lines.append("")

    for section, payload in [
        ("Decoder By Phase", summary["decoder_by_phase"]),
        ("Outcome Aggregate Stats", summary["outcome_aggregate_stats"]),
        ("Descriptor-Order Stats", summary["descriptor_order_stats"]),
        ("Premap Stats", summary["premap_stats"]),
    ]:
        if not payload:
            continue
        lines.append(f"## {section}")
        lines.append("")
        lines.append("| key | count | mean | p50 | p95 | p99 | max |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for key, stats in payload.items():
            lines.append(
                "| "
                + f"`{key}` | {stats.get('count', '')} | "
                + f"{_fmt(stats.get('mean', ''))} | {_fmt(stats.get('p50', ''))} | "
                + f"{_fmt(stats.get('p95', ''))} | {_fmt(stats.get('p99', ''))} | "
                + f"{_fmt(stats.get('max', ''))} |"
            )
        lines.append("")

    if summary["categorical"]:
        lines.append("## Categorical Counts")
        lines.append("")
        for key, counts in summary["categorical"].items():
            lines.append(f"- `{key}`: `{json.dumps(counts, sort_keys=True)}`")
        lines.append("")

    if summary["decoder_slowest_rows"]:
        lines.append("## Slowest Decoder Rows")
        lines.append("")
        lines.append("| elapsed_us | request_id | layer | token_index | phase |")
        lines.append("| ---: | --- | ---: | ---: | --- |")
        for row in summary["decoder_slowest_rows"]:
            lines.append(
                f"| {_fmt(row['decoder_layer_elapsed_us'])} | "
                f"`{row['request_id']}` | {row['layer']} | "
                f"{row['token_index']} | `{row['phase']}` |"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_shadow_jsonl", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Validate the expected mixed diagnostic event and safety contract.",
    )
    parser.add_argument(
        "--require-decode-phase",
        action="store_true",
        help="With --strict, require at least one decoder_layer_timing row tagged decode.",
    )
    parser.add_argument(
        "--allow-event",
        action="append",
        default=[],
        help=(
            "Additional allowed event_type for --strict. Core mixed events are "
            "always required; descriptor_layer_timing is allowed by default."
        ),
    )
    args = parser.parse_args()

    rows = read_shadow_jsonl(args.runtime_shadow_jsonl)
    summary = summarize(args.runtime_shadow_jsonl)
    if args.strict:
        validate_mixed_diagnostic(
            rows,
            summary,
            allowed_event_types=DEFAULT_ALLOWED_EVENT_TYPES | set(args.allow_event),
            require_decode_phase=args.require_decode_phase,
        )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(summary, args.output_md)
    if args.output_json is None and args.output_md is None:
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
