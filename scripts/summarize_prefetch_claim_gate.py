#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize production-like prefetch action replay evidence."
    )
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--csv-output", type=Path, default=None)
    parser.add_argument("--md-output", type=Path, default=None)
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if included policies are missing required replay fields.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, Any]] = []
    for report in args.reports:
        payload = json.loads(report.read_text(encoding="utf-8"))
        rows.extend(_extract_rows(report, payload, strict=args.strict))

    if args.csv_output is not None:
        args.csv_output.parent.mkdir(parents=True, exist_ok=True)
        _write_csv(args.csv_output, rows)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    markdown = _format_markdown(rows)
    if args.md_output is not None:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(markdown, encoding="utf-8")
    print(markdown)


def _extract_rows(
    report: Path, payload: dict[str, Any], *, strict: bool = False
) -> list[dict[str, Any]]:
    policies = payload.get("policies", {})
    rows = []
    for name, metrics in policies.items():
        if not _include_policy(name):
            continue
        if strict:
            _validate_required_metrics(report, name, metrics)
        row = _base_row(report, payload, name, metrics)
        for action in ("full_fetch", "metadata", "premap", "skip"):
            row[f"{action}_count"] = _action_count(metrics, action)
        for action in ("full_fetch", "metadata", "premap"):
            row[f"{action}_later_used_rate"] = _action_later_used_rate(metrics, action)
        row["metadata_net_setup_ms"] = _action_net_setup_ms(metrics, "metadata")
        row["premap_net_setup_ms"] = _action_net_setup_ms(metrics, "premap")
        rows.append(row)
    return rows


def _validate_required_metrics(
    report: Path, policy: str, metrics: dict[str, Any]
) -> None:
    required = [
        ("ready mass", ("ready_mass_fraction", "ready_pool_mass_coverage")),
        ("ready_top1_hit_rate", ("ready_top1_hit_rate",)),
        ("weighted_top1_supplemental_miss", ("weighted_top1_supplemental_miss",)),
    ]
    if policy != "transition_ready":
        required.extend(
            [
                ("stall_reduction_ratio_vs_transition", ("stall_reduction_ratio_vs_transition",)),
                ("delta_issued_bytes_vs_transition", ("delta_issued_bytes_vs_transition",)),
                (
                    "saved_supplemental_fetch_count_vs_transition",
                    ("saved_supplemental_fetch_count_vs_transition",),
                ),
                (
                    "delta_used_bytes_per_extra_issued_byte",
                    ("delta_used_bytes_per_extra_issued_byte",),
                ),
                (
                    "delta_unused_bytes_per_extra_issued_byte",
                    ("delta_unused_bytes_per_extra_issued_byte",),
                ),
            ]
        )
    missing = [label for label, keys in required if not any(key in metrics for key in keys)]
    if missing:
        raise KeyError(f"{report}: policy {policy!r} missing required fields: {missing}")

    if "gated_" in policy:
        counters = metrics.get("admission_action_counters") or metrics.get(
            "admission_action_counts"
        )
        outcomes = metrics.get("admission_action_outcomes")
        if not isinstance(counters, dict):
            raise KeyError(f"{report}: policy {policy!r} missing action counters")
        if not isinstance(outcomes, dict):
            raise KeyError(f"{report}: policy {policy!r} missing action outcomes")


def _include_policy(name: str) -> bool:
    return (
        name == "transition_ready"
        or "ready_mtp_extra" in name
        or "gated_score" in name
        or "gated_utility" in name
    )


def _base_row(
    report: Path, payload: dict[str, Any], policy: str, metrics: dict[str, Any]
) -> dict[str, Any]:
    return {
        "report": report.name,
        "policy": policy,
        "bandwidth_gbps": payload.get("bandwidth_gbps"),
        "layer_ms": payload.get("layer_ms"),
        "mtp_delay_ms": payload.get("mtp_delay_ms"),
        "overlap_factor": payload.get("action_cost_overlap_factor")
        if "action_cost_overlap_factor" in payload
        else payload.get("gated_policies", {}).get("action_cost_overlap_factor"),
        "ready_mass": _float_first(metrics, "ready_mass_fraction", "ready_pool_mass_coverage"),
        "top1_hit": float(metrics.get("ready_top1_hit_rate", 0.0)),
        "weighted_top1_miss": float(
            metrics.get("weighted_top1_supplemental_miss", 0.0)
        ),
        "stall_reduction": float(
            metrics.get("stall_reduction_ratio_vs_transition", 0.0)
        ),
        "saved_fetches": int(
            float(metrics.get("saved_supplemental_fetch_count_vs_transition", 0.0))
        ),
        "delta_issued_tb": float(
            metrics.get("delta_issued_bytes_vs_transition", 0.0)
        )
        / 1e12,
        "used_per_extra_byte": float(
            metrics.get("delta_used_bytes_per_extra_issued_byte", 0.0)
        ),
        "unused_per_extra_byte": float(
            metrics.get("delta_unused_bytes_per_extra_issued_byte", 0.0)
        ),
        "ready_extra_fraction": float(metrics.get("queue_ready_extra_fraction", 0.0)),
        "setup_saved_ms": float(metrics.get("metadata_premap_setup_saved_ms", 0.0)),
    }


def _float_first(metrics: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if key in metrics:
            return float(metrics[key])
    return 0.0


def _action_count(metrics: dict[str, Any], action: str) -> int:
    counters = metrics.get("admission_action_counters", {})
    if action in counters:
        return _count_from_value(counters[action])
    counts = metrics.get("admission_action_counts", {})
    if action in counts:
        return _count_from_value(counts[action])
    outcome = metrics.get("admission_action_outcomes", {}).get(action, {})
    for key in ("issued_count", "count", "total_count"):
        if key in outcome:
            return int(outcome[key])
    return 0


def _count_from_value(value: Any) -> int:
    if isinstance(value, dict):
        for key in ("count", "issued_count", "total_count", "n"):
            if key in value:
                return int(value[key])
        return 0
    return int(value)


def _action_later_used_rate(metrics: dict[str, Any], action: str) -> float:
    outcome = metrics.get("admission_action_outcomes", {}).get(action, {})
    if "later_used_rate" in outcome:
        return float(outcome["later_used_rate"])
    count = _action_count(metrics, action)
    later_used = int(outcome.get("later_used_count", 0))
    return float(later_used / count) if count else 0.0


def _action_net_setup_ms(metrics: dict[str, Any], action: str) -> float:
    outcome = metrics.get("admission_action_outcomes", {}).get(action, {})
    return float(outcome.get("overlap_adjusted_net_setup_benefit_ms", 0.0))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "report",
        "policy",
        "bandwidth_gbps",
        "layer_ms",
        "mtp_delay_ms",
        "overlap_factor",
        "ready_mass",
        "top1_hit",
        "weighted_top1_miss",
        "stall_reduction",
        "saved_fetches",
        "delta_issued_tb",
        "used_per_extra_byte",
        "unused_per_extra_byte",
        "ready_extra_fraction",
        "setup_saved_ms",
        "full_fetch_count",
        "metadata_count",
        "premap_count",
        "skip_count",
        "full_fetch_later_used_rate",
        "metadata_later_used_rate",
        "premap_later_used_rate",
        "metadata_net_setup_ms",
        "premap_net_setup_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| report | policy | bw | overlap | ready | top1 | miss | stall red. | issued TB | saved fetches | used/extra | full_fetch | metadata | premap | skip | meta used | premap used | meta net ms | premap net ms |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {report} | {policy} | {bandwidth_gbps} | {overlap_factor} | "
            "{ready_mass:.4f} | {top1_hit:.4f} | {weighted_top1_miss:.4f} | "
            "{stall_reduction:.4f} | {delta_issued_tb:.3f} | {saved_fetches:d} | "
            "{used_per_extra_byte:.3f} | {full_fetch_count:d} | {metadata_count:d} | "
            "{premap_count:d} | {skip_count:d} | {metadata_later_used_rate:.3f} | "
            "{premap_later_used_rate:.3f} | {metadata_net_setup_ms:.2f} | "
            "{premap_net_setup_ms:.2f} |".format(**row)
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
