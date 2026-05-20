#!/usr/bin/env python3
"""Summarize metadata/premap action gates from claim-gate JSON rows."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_entry(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError(
            f"Invalid entry {raw!r}; expected LABEL=PATH."
        )
    label, path = raw.split("=", 1)
    if not label.strip() or not path.strip():
        raise argparse.ArgumentTypeError(
            f"Invalid entry {raw!r}; expected non-empty LABEL=PATH."
        )
    return label.strip(), Path(path.strip())


def collect_rows(entries: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for label, path in entries:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a list of claim-gate rows")
        for row in payload:
            metadata_count = int(row.get("metadata_count", 0) or 0)
            premap_count = int(row.get("premap_count", 0) or 0)
            if metadata_count <= 0 and premap_count <= 0:
                continue
            output.append(
                {
                    "source": label,
                    "report": row.get("report"),
                    "policy": row.get("policy"),
                    "bandwidth_gbps": row.get("bandwidth_gbps"),
                    "overlap_factor": row.get("overlap_factor"),
                    "stall_reduction": row.get("stall_reduction"),
                    "full_fetch_count": row.get("full_fetch_count"),
                    "metadata_count": metadata_count,
                    "premap_count": premap_count,
                    "metadata_later_used_rate": row.get(
                        "metadata_later_used_rate"
                    ),
                    "premap_later_used_rate": row.get("premap_later_used_rate"),
                    "metadata_net_setup_ms": row.get("metadata_net_setup_ms"),
                    "premap_net_setup_ms": row.get("premap_net_setup_ms"),
                    "metadata_positive": float(
                        row.get("metadata_net_setup_ms", 0.0) or 0.0
                    )
                    > 0.0,
                    "premap_positive": float(
                        row.get("premap_net_setup_ms", 0.0) or 0.0
                    )
                    > 0.0,
                }
            )
    return output


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ok": True,
        "boundary": (
            "Metadata/premap setup gate summary only. These actions do not "
            "move full expert payload and are lower-risk than full_fetch, but "
            "they still require positive net setup evidence before default "
            "runtime enablement."
        ),
        "row_count": len(rows),
        "metadata_positive_count": sum(1 for row in rows if row["metadata_positive"]),
        "premap_positive_count": sum(1 for row in rows if row["premap_positive"]),
        "rows": rows,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "source",
        "report",
        "policy",
        "bandwidth_gbps",
        "overlap_factor",
        "stall_reduction",
        "full_fetch_count",
        "metadata_count",
        "premap_count",
        "metadata_later_used_rate",
        "premap_later_used_rate",
        "metadata_net_setup_ms",
        "premap_net_setup_ms",
        "metadata_positive",
        "premap_positive",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Metadata/Premap Setup Gate Summary",
        "",
        payload["boundary"],
        "",
        "## Summary",
        "",
        f"- rows: {payload['row_count']}",
        f"- metadata_positive_count: {payload['metadata_positive_count']}",
        f"- premap_positive_count: {payload['premap_positive_count']}",
        "",
        "## Rows",
        "",
        "| source | report | policy | full_fetch | metadata | premap | "
        "meta used | premap used | meta net ms | premap net ms |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| `{row['source']}` | `{row['report']}` | `{row['policy']}` | "
            f"{row['full_fetch_count']} | {row['metadata_count']} | "
            f"{row['premap_count']} | "
            f"{_fmt(row['metadata_later_used_rate'])} | "
            f"{_fmt(row['premap_later_used_rate'])} | "
            f"{_fmt(row['metadata_net_setup_ms'])} | "
            f"{_fmt(row['premap_net_setup_ms'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Positive metadata/premap counts here mean positive setup proxy under "
            "the existing replay cost model, not endpoint runtime speedup.",
            "- Negative setup proxy means the action should remain shadow/gated, "
            "even though it is lower risk than full payload transfer.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", action="append", type=parse_entry, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    rows = collect_rows(args.entry)
    payload = summarize(rows)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    write_csv(args.output_csv, rows)


if __name__ == "__main__":
    main()
