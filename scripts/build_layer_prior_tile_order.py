#!/usr/bin/env python3
"""Build calibrated per-layer B-tile group-order priors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    build_layer_tile_prior,
    load_tile_requests_jsonl,
    write_layer_tile_prior,
)


SCORES = [
    "frequency",
    "utility",
    "weighted_utility",
    "weighted_frequency",
    "transition",
    "mtp",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--score", choices=SCORES, default="utility")
    parser.add_argument("--split-name", default="calibration")
    parser.add_argument("--source-manifest", default=None)
    parser.add_argument("--experiment-id", default=None)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, default=None)
    return parser.parse_args()


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def render_markdown(payload: dict[str, Any]) -> str:
    metadata = payload["metadata"]
    lines = [
        "# Layer-Prior Tile Group Order",
        "",
        "This artifact is a calibrated per-layer group-order prior. It is not an",
        "exact descriptor permutation cache; runtime still preserves the current",
        "descriptor multiset and only ranks the tile groups that are present.",
        "",
        f"- Score: `{payload['score_name']}`",
        f"- Requests: `{metadata['request_count']}`",
        f"- Layers: `{metadata['layer_count']}`",
        f"- Tiles: `{metadata['tile_count']}`",
        f"- Split: `{metadata.get('split_name')}`",
        "",
        "## Layer Preview",
        "",
        "| layer | top tiles |",
        "|---:|---|",
    ]
    for layer, order in list(sorted(payload["layer_orders"].items(), key=lambda row: int(row[0])))[:10]:
        lines.append(f"| {layer} | `{', '.join(str(tile) for tile in order[:16])}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    requests = load_tile_requests_jsonl(args.input_jsonl)
    split_values = sorted({request.split for request in requests if request.split is not None})
    metadata = {
        "input_jsonl": str(args.input_jsonl),
        "split_name": args.split_name,
        "observed_splits": split_values,
        "source_manifest": args.source_manifest,
        "experiment_id": args.experiment_id,
        "policy_semantics": "rank_present_tile_groups_only_preserve_current_multiset",
    }
    prior = build_layer_tile_prior(requests, score_name=args.score, metadata=metadata)
    write_layer_tile_prior(prior, args.output_json)
    payload = prior.as_dict()
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(render_markdown(payload))


if __name__ == "__main__":
    main()
