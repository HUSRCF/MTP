#!/usr/bin/env python3
"""Evaluate p_min-gated LDS staging eligibility from a microbench sweep CSV."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_TIERS = {
    "transition_top16": 0.90,
    "transition_top17_32": 0.65,
    "mtp_extra1_4": 0.45,
    "mtp_extra5_8": 0.30,
    "random_control": 0.125,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("outputs/reports/lds_tile_staging/sweep_grouped_consumer_rows_2gpu.csv"),
    )
    parser.add_argument("--mode", default="mixed")
    parser.add_argument("--safety-margin", type=float, default=0.05)
    parser.add_argument("--min-occupancy-blocks", type=int, default=2)
    parser.add_argument(
        "--tier",
        action="append",
        default=None,
        help="Override/add tier as name=expected_hit_rate, e.g. mtp_extra1_4=0.42.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/lds_tile_staging/lds_stage_policy_eval.json"),
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("outputs/reports/lds_tile_staging/lds_stage_policy_eval.md"),
    )
    return parser.parse_args()


def _tiers(overrides: list[str] | None) -> dict[str, float]:
    tiers = dict(DEFAULT_TIERS)
    for item in overrides or []:
        if "=" not in item:
            msg = f"--tier must be name=value, got {item!r}."
            raise ValueError(msg)
        name, value = item.split("=", 1)
        tiers[name.strip()] = float(value)
    return tiers


def _read_rows(path: Path, mode: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("mode") == mode]
    if not rows:
        msg = f"No rows found for mode={mode!r} in {path}."
        raise RuntimeError(msg)
    return rows


def _float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value in (None, ""):
        return default
    return float(value)


def _int(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key)
    if value in (None, ""):
        return default
    return int(float(value))


def evaluate(
    rows: list[dict[str, str]],
    tiers: dict[str, float],
    *,
    safety_margin: float,
    min_occupancy_blocks: int,
) -> dict[str, Any]:
    tier_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for tier_name, expected_hit in tiers.items():
        enabled = 0
        occupancy_blocked = 0
        below_pmin = 0
        missing_pmin = 0
        thresholds: list[float] = []
        speedups: list[float] = []
        for row in rows:
            occupancy = _int(row, "occupancy_blocks_per_cu", 0)
            p_min = row.get("p_min_hit_rate_clamped")
            if p_min in (None, ""):
                missing_pmin += 1
                gate = False
                required = None
            else:
                required = float(p_min) + float(safety_margin)
                if occupancy < int(min_occupancy_blocks):
                    occupancy_blocked += 1
                    gate = False
                elif float(expected_hit) >= required:
                    enabled += 1
                    gate = True
                    thresholds.append(required)
                    speedups.append(_float(row, "overlap_model_speedup_vs_reactive", 0.0))
                else:
                    below_pmin += 1
                    gate = False
            tier_rows.append(
                {
                    "tier": tier_name,
                    "expected_hit_rate": expected_hit,
                    "gate_enabled": gate,
                    "required_hit_rate": required,
                    "p_min_hit_rate_clamped": None if p_min in (None, "") else float(p_min),
                    "occupancy_blocks_per_cu": occupancy,
                    "tile_elems": _int(row, "tile_elems", 0),
                    "metadata_tokens": _int(row, "metadata_tokens", 0),
                    "compute_iters": _int(row, "compute_iters", 0),
                    "consumer_rows": _int(row, "consumer_rows", 0),
                    "miss_rate": _float(row, "miss_rate", 0.0),
                    "tile_stride": _int(row, "tile_stride", 0),
                    "cache_flush_elems": _int(row, "cache_flush_elems", 0),
                    "overlap_model_speedup_vs_reactive": _float(
                        row,
                        "overlap_model_speedup_vs_reactive",
                        0.0,
                    ),
                }
            )
        total = len(rows)
        summary[tier_name] = {
            "expected_hit_rate": expected_hit,
            "enabled_rows": enabled,
            "total_rows": total,
            "enabled_fraction": enabled / max(1, total),
            "below_pmin_rows": below_pmin,
            "occupancy_blocked_rows": occupancy_blocked,
            "missing_pmin_rows": missing_pmin,
            "mean_required_hit_rate_when_enabled": (
                sum(thresholds) / len(thresholds) if thresholds else None
            ),
            "mean_speedup_when_enabled": (
                sum(speedups) / len(speedups) if speedups else None
            ),
        }
    return {
        "summary": summary,
        "rows": tier_rows,
        "num_microbench_rows": len(rows),
        "safety_margin": safety_margin,
        "min_occupancy_blocks": min_occupancy_blocks,
    }


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LDS Stage Policy Evaluation",
        "",
        "| tier | expected hit | enabled | total | enabled fraction | mean required hit | mean speedup | blocked low occupancy | below p_min |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for tier, item in payload["summary"].items():
        mean_required = item["mean_required_hit_rate_when_enabled"]
        mean_speedup = item["mean_speedup_when_enabled"]
        lines.append(
            "| {tier} | {expected:.3f} | {enabled} | {total} | {frac:.3f} | "
            "{required} | {speedup} | {occ} | {below} |".format(
                tier=tier,
                expected=float(item["expected_hit_rate"]),
                enabled=int(item["enabled_rows"]),
                total=int(item["total_rows"]),
                frac=float(item["enabled_fraction"]),
                required="-" if mean_required is None else f"{float(mean_required):.3f}",
                speedup="-" if mean_speedup is None else f"{float(mean_speedup):.3f}",
                occ=int(item["occupancy_blocked_rows"]),
                below=int(item["below_pmin_rows"]),
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    rows = _read_rows(args.csv, args.mode)
    payload = evaluate(
        rows,
        _tiers(args.tier),
        safety_margin=args.safety_margin,
        min_occupancy_blocks=args.min_occupancy_blocks,
    )
    payload["config"] = {
        "csv": str(args.csv),
        "mode": args.mode,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(args.md_output, payload)
    print(json.dumps({"ok": True, "summary": payload["summary"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
