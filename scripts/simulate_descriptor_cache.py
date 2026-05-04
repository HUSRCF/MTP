#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    load_descriptor_jsonl,
    simulate_descriptor_lru_cache,
    simulate_descriptor_priority_cache,
    write_descriptor_cache_report,
)
from mtp_expert_prefetch.utils.config import find_project_root, resolve_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate a per-layer LRU resident expert cache over pre-map descriptors."
    )
    parser.add_argument("descriptors", type=Path)
    parser.add_argument(
        "--policy",
        choices=("lru", "priority_protected"),
        default="lru",
    )
    parser.add_argument("--capacity-per-layer", type=int, default=160)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument(
        "--transfer-budget-mb-per-sample-layer",
        type=float,
        default=None,
        help="Optional per sample/layer transfer budget. Candidates beyond it are skipped.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/cache_lru_report.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.descriptors)
    descriptor_path = resolve_path(args.descriptors, base_dir=project_root)
    output_path = resolve_path(args.output, base_dir=project_root)
    descriptors = load_descriptor_jsonl(descriptor_path)
    simulate = (
        simulate_descriptor_priority_cache
        if args.policy == "priority_protected"
        else simulate_descriptor_lru_cache
    )
    report = simulate(
        descriptors,
        capacity_per_layer=int(args.capacity_per_layer),
        expert_bytes=int(args.expert_bytes),
        transfer_budget_bytes_per_sample_layer=(
            int(float(args.transfer_budget_mb_per_sample_layer) * 1_000_000)
            if args.transfer_budget_mb_per_sample_layer is not None
            else None
        ),
    )
    written_path = write_descriptor_cache_report(report, output_path)
    payload = report.as_dict()
    payload["ok"] = True
    payload["descriptors"] = str(descriptor_path)
    payload["policy"] = str(args.policy)
    payload["output"] = str(written_path)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
