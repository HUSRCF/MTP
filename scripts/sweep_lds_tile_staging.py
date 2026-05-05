#!/usr/bin/env python3
"""Sweep the speculative LDS tile-staging microbench break-even envelope."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[0]
sys.path.insert(0, str(SCRIPT_DIR))

import run_lds_tile_staging_bench as bench  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, action="append", default=None)
    parser.add_argument("--tile-elems", type=int, action="append", default=None)
    parser.add_argument("--validate-iters", type=int, action="append", default=None)
    parser.add_argument("--metadata-tokens", type=int, action="append", default=None)
    parser.add_argument("--miss-rate", type=float, action="append", default=None)
    parser.add_argument("--block-threads", type=int, action="append", default=None)
    parser.add_argument("--requests", type=int, default=4096)
    parser.add_argument("--experts", type=int, default=256)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=30)
    parser.add_argument("--interference-iters", type=int, action="append", default=None)
    parser.add_argument("--interference-elems", type=int, default=1 << 20)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "lds_tile_staging" / "sweep.json",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "lds_tile_staging" / "sweep.csv",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "lds_tile_staging" / "sweep.md",
    )
    parser.add_argument(
        "--plot-output",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "lds_tile_staging" / "sweep.png",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip optional matplotlib plot generation.",
    )
    return parser.parse_args()


def _values(values: list[Any] | None, default: list[Any]) -> list[Any]:
    if values is None:
        return default
    return sorted(set(values))


def _run_combo(combo: dict[str, Any]) -> dict[str, Any]:
    ns = SimpleNamespace(
        device=combo["device"],
        hip_visible_devices=None,
        requests=combo["requests"],
        experts=combo["experts"],
        tile_elems=combo["tile_elems"],
        block_threads=combo["block_threads"],
        warmup=combo["warmup"],
        iters=combo["iters"],
        validate_iters=combo["validate_iters"],
        metadata_tokens=combo["metadata_tokens"],
        interference_iters=combo["interference_iters"],
        interference_elems=combo["interference_elems"],
        miss_rate=combo["miss_rate"],
        seed=combo["seed"],
    )
    results = [bench.bench_one(ns, mode) for mode in bench.DEFAULT_MODES]
    summary = bench.summarize(results)
    summary["combo"] = combo
    return summary


def _flatten_rows(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for report in reports:
        combo = report["combo"]
        by_mode = {row["mode"]: row for row in report["results"]}
        derived = report["derived"]
        reactive = by_mode["reactive"]
        for mode in bench.DEFAULT_MODES:
            row = by_mode[mode]
            d = derived[mode]
            rows.append(
                {
                    "device": combo["device"],
                    "tile_elems": combo["tile_elems"],
                    "tile_bytes": row["tile_bytes"],
                    "validate_iters": combo["validate_iters"],
                    "metadata_tokens": combo["metadata_tokens"],
                    "miss_rate": combo["miss_rate"],
                    "block_threads": combo["block_threads"],
                    "interference_iters": combo["interference_iters"],
                    "mode": mode,
                    "observed_miss_fraction": row["observed_miss_fraction"],
                    "wall_ms_mean": row["wall_ms_mean"],
                    "first_fma_cycles_p50": row["first_fma_cycles_p50"],
                    "metadata_wait_cycles_p50": row.get("metadata_wait_cycles_p50", 0.0),
                    "stage_cycles_p50": row.get("stage_cycles_p50", 0.0),
                    "overwrite_cycles_p50_miss": row.get("overwrite_cycles_p50_miss", 0.0),
                    "overlap_model_cycles_p50": d["overlap_model_cycles_p50"],
                    "overlap_model_delta_vs_reactive": d["overlap_model_delta_vs_reactive"],
                    "overlap_model_speedup_vs_reactive": d[
                        "overlap_model_speedup_vs_reactive"
                    ],
                    "wall_ms_delta_vs_reactive": d["wall_ms_delta_vs_reactive"],
                    "reactive_overlap_model_cycles_p50": derived["reactive"][
                        "overlap_model_cycles_p50"
                    ],
                    "reactive_first_fma_cycles_p50": reactive["first_fma_cycles_p50"],
                }
            )
    return rows


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for mode in ("oracle", "spec_hit", "spec_miss", "mixed"):
        group = [row for row in rows if row["mode"] == mode]
        positive = [row for row in group if row["overlap_model_delta_vs_reactive"] < 0]
        strong = [row for row in group if row["overlap_model_speedup_vs_reactive"] >= 1.1]
        best = max(group, key=lambda row: row["overlap_model_speedup_vs_reactive"])
        worst = min(group, key=lambda row: row["overlap_model_speedup_vs_reactive"])
        summary[mode] = {
            "num_rows": len(group),
            "positive_rows": len(positive),
            "speedup_ge_1p1_rows": len(strong),
            "mean_speedup": sum(row["overlap_model_speedup_vs_reactive"] for row in group)
            / max(1, len(group)),
            "best": _row_key(best),
            "worst": _row_key(worst),
        }
    return summary


def _row_key(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "device": row["device"],
        "tile_elems": row["tile_elems"],
        "validate_iters": row["validate_iters"],
        "metadata_tokens": row["metadata_tokens"],
        "miss_rate": row["miss_rate"],
        "block_threads": row["block_threads"],
        "speedup": row["overlap_model_speedup_vs_reactive"],
        "delta_cycles": row["overlap_model_delta_vs_reactive"],
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_md(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# LDS Tile-Staging Sweep",
        "",
        "## Summary",
        "",
        "| mode | rows | positive | speedup >= 1.1x | mean speedup | best speedup | worst speedup |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mode, item in summary.items():
        lines.append(
            "| {mode} | {num_rows} | {positive_rows} | {speedup_ge_1p1_rows} | "
            "{mean_speedup:.3f} | {best:.3f} | {worst:.3f} |".format(
                mode=mode,
                num_rows=item["num_rows"],
                positive_rows=item["positive_rows"],
                speedup_ge_1p1_rows=item["speedup_ge_1p1_rows"],
                mean_speedup=item["mean_speedup"],
                best=item["best"]["speedup"],
                worst=item["worst"]["speedup"],
            )
        )
    lines.extend(["", "## Mixed Mode Top 12", ""])
    mixed = sorted(
        [row for row in rows if row["mode"] == "mixed"],
        key=lambda row: row["overlap_model_speedup_vs_reactive"],
        reverse=True,
    )[:12]
    lines.extend(
        [
            "| device | tile | wait iters | metadata tokens | miss | threads | interference | speedup | delta cycles |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in mixed:
        lines.append(
            "| {device} | {tile_elems} | {validate_iters} | {metadata_tokens} | "
            "{miss_rate:.2f} | {block_threads} | {interference_iters} | "
            "{overlap_model_speedup_vs_reactive:.3f} | "
            "{overlap_model_delta_vs_reactive:.1f} |".format(**row)
        )
    return "\n".join(lines) + "\n"


def _write_plot(path: Path, rows: list[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - optional dependency.
        path.with_suffix(path.suffix + ".error.txt").write_text(str(exc), encoding="utf-8")
        return

    mixed = [row for row in rows if row["mode"] == "mixed"]
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in mixed:
        groups.setdefault((int(row["tile_elems"]), int(row["block_threads"])), []).append(row)

    fig, ax = plt.subplots(figsize=(8, 5))
    for (tile, threads), group in sorted(groups.items()):
        group = sorted(group, key=lambda row: (row["validate_iters"], row["miss_rate"]))
        xs = [row["validate_iters"] + row["miss_rate"] * 10.0 for row in group]
        ys = [row["overlap_model_speedup_vs_reactive"] for row in group]
        ax.plot(xs, ys, marker="o", linewidth=1.2, label=f"tile={tile}, thr={threads}")
    ax.axhline(1.0, color="black", linewidth=1.0, alpha=0.4)
    ax.axhline(1.1, color="tab:green", linewidth=1.0, alpha=0.35)
    ax.set_xlabel("validate_iters + miss_rate*10")
    ax.set_ylabel("mixed overlap-model speedup vs reactive")
    ax.set_title("Speculative LDS tile staging break-even sweep")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    devices = _values(args.device, [0])
    tile_elems = _values(args.tile_elems, [256, 512, 1024, 2048])
    validate_iters = _values(args.validate_iters, [0, 64, 256, 1024])
    metadata_tokens = _values(args.metadata_tokens, [0])
    miss_rates = _values(args.miss_rate, [0.0, 0.1, 0.25, 0.5, 1.0])
    block_threads = _values(args.block_threads, [128, 256])
    interference_iters = _values(args.interference_iters, [0])

    bench.build(force=args.force_build)

    combos: list[dict[str, Any]] = []
    index = 0
    for tile in tile_elems:
        for wait in validate_iters:
            for meta_tokens in metadata_tokens:
                for miss in miss_rates:
                    for threads in block_threads:
                        for interference in interference_iters:
                            combos.append(
                                {
                                    "device": devices[index % len(devices)],
                                    "tile_elems": tile,
                                    "validate_iters": wait,
                                    "metadata_tokens": meta_tokens,
                                    "miss_rate": miss,
                                    "block_threads": threads,
                                    "interference_iters": interference,
                                    "interference_elems": args.interference_elems,
                                    "requests": args.requests,
                                    "experts": args.experts,
                                    "warmup": args.warmup,
                                    "iters": args.iters,
                                    "seed": args.seed,
                                }
                            )
                            index += 1

    reports: list[dict[str, Any]] = []
    max_workers = max(1, len(devices))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_combo, combo): combo for combo in combos}
        for future in as_completed(futures):
            combo = futures[future]
            try:
                reports.append(future.result())
            except Exception as exc:
                raise RuntimeError(f"failed combo {combo}") from exc

    rows = _flatten_rows(reports)
    summary = _summarize_rows(rows)
    payload = {
        "ok": True,
        "config": {
            "devices": devices,
            "tile_elems": tile_elems,
            "validate_iters": validate_iters,
            "metadata_tokens": metadata_tokens,
            "miss_rates": miss_rates,
            "block_threads": block_threads,
            "interference_iters": interference_iters,
            "interference_elems": args.interference_elems,
            "requests": args.requests,
            "experts": args.experts,
            "warmup": args.warmup,
            "iters": args.iters,
            "seed": args.seed,
            "num_combos": len(combos),
        },
        "summary": summary,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_csv(args.csv_output, rows)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.write_text(_format_md(summary, rows), encoding="utf-8")
    if not args.no_plot:
        _write_plot(args.plot_output, rows)

    print(json.dumps({"ok": True, "summary": summary, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
