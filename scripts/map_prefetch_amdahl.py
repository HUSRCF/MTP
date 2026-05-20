#!/usr/bin/env python3
"""Map prefetch replay local stall reduction to endpoint Amdahl upper bounds."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_shares(
    bottleneck: dict[str, Any] | None,
    *,
    moe_apply_share_pct: float | None,
    mlp_moe_share_pct: float | None,
) -> dict[str, float]:
    shares: dict[str, float] = {}
    if bottleneck:
        coarse = bottleneck.get("low_intrusion_coarse")
        if isinstance(coarse, dict):
            attention = coarse.get("attention_total_only")
            if isinstance(attention, dict):
                if mlp_moe_share_pct is None:
                    mlp_moe_share_pct = _float_or_none(
                        attention.get("mlp_moe_share_pct")
                    )
                if moe_apply_share_pct is None:
                    moe_apply_share_pct = _float_or_none(
                        attention.get("moe_apply_share_pct")
                    )
            shared = coarse.get("shared_body_total_only")
            if isinstance(shared, dict) and moe_apply_share_pct is None:
                moe_apply_share_pct = _float_or_none(
                    shared.get("moe_apply_share_pct")
                )
        diagnostic = bottleneck.get("diagnostic_light_shares_pct")
        if isinstance(diagnostic, dict):
            if mlp_moe_share_pct is None:
                mlp_moe_share_pct = _float_or_none(diagnostic.get("mlp_moe"))
            if moe_apply_share_pct is None:
                moe_apply_share_pct = _float_or_none(diagnostic.get("moe_apply"))

    if moe_apply_share_pct is not None:
        shares["moe_apply"] = moe_apply_share_pct
    if mlp_moe_share_pct is not None:
        shares["mlp_moe"] = mlp_moe_share_pct
    if not shares:
        raise ValueError(
            "No endpoint shares available. Provide --bottleneck-json or "
            "--moe-apply-share-pct/--mlp-moe-share-pct."
        )
    return shares


def _normalize_stall_reduction(value: Any) -> tuple[float, str]:
    """Return stall reduction as a fraction.

    Claim-gate rows currently store ``stall_reduction`` as a fraction
    (for example, 0.072).  This guard also accepts percent-style inputs
    from ad hoc tables (for example, 7.2) so future report plumbing cannot
    accidentally inflate the Amdahl upper bound by 100x.
    """

    local = float(value or 0.0)
    if abs(local) <= 1.0:
        return local, "fraction"
    if abs(local) <= 100.0:
        return local / 100.0, "percent"
    raise ValueError(
        f"Unreasonable stall_reduction={local!r}; expected fraction or percent."
    )


def _amdahl_speedup_pct(local_reduction: float, component_share_pct: float) -> tuple[float, float]:
    saved_share = max(0.0, local_reduction) * component_share_pct
    if saved_share >= 100.0:
        return saved_share, float("inf")
    speedup = 1.0 / (1.0 - saved_share / 100.0)
    return saved_share, (speedup - 1.0) * 100.0


def build_rows(
    claim_rows: list[dict[str, Any]],
    shares: dict[str, float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in claim_rows:
        local, local_unit = _normalize_stall_reduction(row.get("stall_reduction"))
        mapped: dict[str, Any] = {
            "report": row.get("report"),
            "policy": row.get("policy"),
            "bandwidth_gbps": row.get("bandwidth_gbps"),
            "overlap_factor": row.get("overlap_factor"),
            "local_stall_reduction_pct": local * 100.0,
            "local_stall_reduction_input_unit": local_unit,
            "ready_mass": row.get("ready_mass"),
            "top1_hit": row.get("top1_hit"),
            "weighted_top1_miss": row.get("weighted_top1_miss"),
            "delta_issued_tb": row.get("delta_issued_tb"),
            "saved_fetches": row.get("saved_fetches"),
            "used_per_extra_byte": row.get("used_per_extra_byte"),
            "full_fetch_count": row.get("full_fetch_count"),
            "metadata_count": row.get("metadata_count"),
            "premap_count": row.get("premap_count"),
            "metadata_net_setup_ms": row.get("metadata_net_setup_ms"),
            "premap_net_setup_ms": row.get("premap_net_setup_ms"),
        }
        for name, share_pct in shares.items():
            saved_share, speedup_pct = _amdahl_speedup_pct(local, share_pct)
            mapped[f"{name}_share_pct"] = share_pct
            mapped[f"{name}_endpoint_saved_share_pct"] = saved_share
            mapped[f"{name}_endpoint_speedup_upper_pct"] = speedup_pct
        rows.append(mapped)
    return rows


def render_markdown(rows: list[dict[str, Any]], shares: dict[str, float]) -> str:
    share_desc = ", ".join(f"{name}={value:.2f}%" for name, value in shares.items())
    lines = [
        "# Prefetch Amdahl Upper-Bound Mapping",
        "",
        "Boundary:",
        "",
        "```text",
        "This maps action-replay local stall-proxy reductions to endpoint upper",
        "bounds using measured decoder component shares.  It is not endpoint TPOT",
        "evidence and does not assume a real DMA/cache-manager implementation.",
        "```",
        "",
        f"Endpoint component shares: `{share_desc}`",
        "",
        "| report | policy | local stall red. | MoE apply saved | MoE apply speedup | MLP/MoE saved | MLP/MoE speedup | issued TB | used/extra | full_fetch |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        moe_saved = row.get("moe_apply_endpoint_saved_share_pct")
        moe_speed = row.get("moe_apply_endpoint_speedup_upper_pct")
        mlp_saved = row.get("mlp_moe_endpoint_saved_share_pct")
        mlp_speed = row.get("mlp_moe_endpoint_speedup_upper_pct")
        lines.append(
            "| {report} | {policy} | {local:.2f}% | {moe_saved} | {moe_speed} | "
            "{mlp_saved} | {mlp_speed} | {issued:.3f} | {used:.3f} | {full_fetch} |".format(
                report=row.get("report"),
                policy=row.get("policy"),
                local=float(row.get("local_stall_reduction_pct") or 0.0),
                moe_saved=("" if moe_saved is None else f"{float(moe_saved):.2f}%"),
                moe_speed=("" if moe_speed is None else f"{float(moe_speed):.2f}%"),
                mlp_saved=("" if mlp_saved is None else f"{float(mlp_saved):.2f}%"),
                mlp_speed=("" if mlp_speed is None else f"{float(mlp_speed):.2f}%"),
                issued=float(row.get("delta_issued_tb") or 0.0),
                used=float(row.get("used_per_extra_byte") or 0.0),
                full_fetch=int(row.get("full_fetch_count") or 0),
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "```text",
            "Use the MoE-apply mapping as the conservative endpoint upper bound for",
            "expert-fetch related work.  The broader MLP/MoE mapping is an optimistic",
            "ceiling and should not be used as a direct runtime claim.",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claim_gate_json", type=Path)
    parser.add_argument("--bottleneck-json", type=Path)
    parser.add_argument("--moe-apply-share-pct", type=float)
    parser.add_argument("--mlp-moe-share-pct", type=float)
    parser.add_argument("--csv-output", type=Path)
    parser.add_argument("--md-output", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    claim_rows = _load_json(args.claim_gate_json)
    if not isinstance(claim_rows, list):
        raise TypeError("claim_gate_json must contain a list of policy rows.")
    bottleneck = (
        _load_json(args.bottleneck_json)
        if args.bottleneck_json is not None
        else None
    )
    if bottleneck is not None and not isinstance(bottleneck, dict):
        raise TypeError("bottleneck_json must contain an object.")
    shares = _extract_shares(
        bottleneck,
        moe_apply_share_pct=args.moe_apply_share_pct,
        mlp_moe_share_pct=args.mlp_moe_share_pct,
    )
    rows = build_rows(claim_rows, shares)

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps({"component_shares": shares, "rows": rows}, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    if args.csv_output:
        args.csv_output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = sorted({key for row in rows for key in row})
        with args.csv_output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    markdown = render_markdown(rows, shares)
    if args.md_output:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)


if __name__ == "__main__":
    main()
