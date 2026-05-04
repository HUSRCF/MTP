#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize fixed/gated prefetch event-stall policies as Pareto tables."
    )
    parser.add_argument("report", type=Path)
    parser.add_argument("--csv-output", type=Path, default=None)
    parser.add_argument("--md-output", type=Path, default=None)
    parser.add_argument("--plot-output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(args.report.read_text(encoding="utf-8"))
    rows = _extract_rows(payload)
    if args.csv_output is not None:
        args.csv_output.parent.mkdir(parents=True, exist_ok=True)
        _write_csv(args.csv_output, rows)
    if args.md_output is not None:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(_format_markdown(rows), encoding="utf-8")
    if args.plot_output is not None:
        args.plot_output.parent.mkdir(parents=True, exist_ok=True)
        _write_plot(args.plot_output, rows)
    print(_format_markdown(rows))


def _extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    policies = payload["policies"]
    rows: list[dict[str, Any]] = []
    for name, metrics in policies.items():
        if name == "transition_ready":
            continue
        kind, label, keep_fraction, max_extra = _parse_policy_name(name)
        if kind is None:
            continue
        issued_tb = float(metrics.get("delta_issued_bytes_vs_transition", 0.0)) / 1e12
        stall_reduction_pct = 100.0 * float(
            metrics.get("stall_reduction_ratio_vs_transition", 0.0)
        )
        rows.append(
            {
                "policy": label,
                "kind": kind,
                "keep_fraction": keep_fraction,
                "max_extra": max_extra,
                "extra_issued_tb": issued_tb,
                "stall_reduction_pct": stall_reduction_pct,
                "stall_saved_ms_per_extra_issued_gb": float(
                    metrics.get("stall_saved_ms_per_extra_issued_gb", 0.0)
                ),
                "saved_fetches": int(
                    float(metrics.get("saved_supplemental_fetch_count_vs_transition", 0.0))
                ),
                "used_per_extra_byte": float(
                    metrics.get("delta_used_bytes_per_extra_issued_byte", 0.0)
                ),
                "unused_per_extra_byte": float(
                    metrics.get("delta_unused_bytes_per_extra_issued_byte", 0.0)
                ),
                "weighted_top1_miss": float(
                    metrics.get("weighted_top1_supplemental_miss", 0.0)
                ),
            }
        )
    return sorted(rows, key=lambda r: (r["kind"], r["extra_issued_tb"], r["policy"]))


def _parse_policy_name(name: str) -> tuple[str | None, str, float | None, int | None]:
    fixed_prefix = "transition_top32_plus_ready_mtp_extra"
    score_prefix = "transition_top32_plus_gated_score_keep_top_"
    utility_prefix = "transition_top32_plus_gated_utility_keep_top_"
    if name.startswith(fixed_prefix):
        max_extra = int(name.removeprefix(fixed_prefix))
        return "fixed", f"fixed_extra{max_extra}", None, max_extra
    if name.startswith(score_prefix):
        keep = float(name.removeprefix(score_prefix))
        return "score", f"score_keep_top_{keep:.3f}", keep, None
    if name.startswith(utility_prefix):
        keep = float(name.removeprefix(utility_prefix))
        return "utility", f"utility_keep_top_{keep:.3f}", keep, None
    return None, name, None, None


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "policy",
        "kind",
        "keep_fraction",
        "max_extra",
        "extra_issued_tb",
        "stall_reduction_pct",
        "stall_saved_ms_per_extra_issued_gb",
        "saved_fetches",
        "used_per_extra_byte",
        "unused_per_extra_byte",
        "weighted_top1_miss",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| policy | extra issued TB | stall reduction % | stall saved ms / extra GB | saved fetches | used / extra byte | unused / extra byte |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {policy} | {extra_issued_tb:.3f} | {stall_reduction_pct:.2f} | "
            "{stall_saved_ms_per_extra_issued_gb:.2f} | {saved_fetches:d} | "
            "{used_per_extra_byte:.3f} | {unused_per_extra_byte:.3f} |".format(**row)
        )
    return "\n".join(lines) + "\n"


def _write_plot(path: Path, rows: list[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - optional plotting dependency.
        path.with_suffix(path.suffix + ".error.txt").write_text(str(exc), encoding="utf-8")
        return

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    styles = {
        "fixed": {"marker": "o", "linestyle": "--"},
        "score": {"marker": "s", "linestyle": "-"},
        "utility": {"marker": "^", "linestyle": "-"},
    }
    for kind in ("fixed", "score", "utility"):
        group = [row for row in rows if row["kind"] == kind]
        if not group:
            continue
        group = sorted(group, key=lambda row: row["extra_issued_tb"])
        ax.plot(
            [row["extra_issued_tb"] for row in group],
            [row["stall_reduction_pct"] for row in group],
            label=kind,
            **styles[kind],
        )
    ax.set_xlabel("Extra issued bytes (TB)")
    ax.set_ylabel("Stall reduction vs transition (%)")
    ax.set_title("MTP extra admission Pareto curve")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
