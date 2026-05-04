#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation import (  # noqa: E402
    analyze_prefill_working_set,
    write_prefill_working_set_report,
)
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path  # noqa: E402


DEFAULT_CONFIG = Path("configs/eval/prefill_working_set_merged_vllm.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze MoE expert working-set pressure during prefill traces."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    return parser.parse_args()


def _parse_budgets(value: object) -> list[int]:
    if isinstance(value, int):
        budgets = [int(value)]
    elif isinstance(value, list):
        budgets = [int(item) for item in value]
    elif isinstance(value, str):
        budgets = [int(part.strip()) for part in value.split(",") if part.strip()]
    else:
        msg = "`budgets` must be an int, list[int], or comma-separated string."
        raise TypeError(msg)
    budgets = sorted({budget for budget in budgets if budget > 0})
    if not budgets:
        msg = "At least one positive expert cache budget is required."
        raise ValueError(msg)
    return budgets


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    config = load_yaml(args.config)
    manifest_path = resolve_path(config["manifest_path"], base_dir=project_root)
    output_path = resolve_path(config["output_path"], base_dir=project_root)
    budgets = _parse_budgets(config.get("budgets", [8, 16, 32, 64, 128, 256]))
    max_samples = config.get("max_samples")

    report = analyze_prefill_working_set(
        manifest_path,
        budgets=budgets,
        max_samples=int(max_samples) if max_samples is not None else None,
    )
    written_path = write_prefill_working_set_report(report, output_path)
    print(
        json.dumps(
            {
                "ok": True,
                "output_path": str(written_path),
                "num_samples": report.num_samples,
                "total_tokens": report.total_tokens,
                "layer_unique_summary": report.layer_unique_summary,
                "sample_unique_summary": report.sample_unique_summary,
                "hot_cache": report.hot_cache,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
