#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation import (  # noqa: E402
    simulate_prefetch_shadow,
    write_prefetch_shadow_report,
)
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path  # noqa: E402


DEFAULT_CONFIG = Path("configs/eval/prefetch_shadow_256sample_mtp_extra.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run offline shadow-mode expert prefetch policy simulation."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    return parser.parse_args()


def _parse_int_list(value: object, *, default: list[int]) -> list[int]:
    if value is None:
        return default
    if isinstance(value, int):
        parsed = [int(value)]
    elif isinstance(value, list):
        parsed = [int(item) for item in value]
    elif isinstance(value, str):
        parsed = [int(part.strip()) for part in value.split(",") if part.strip()]
    else:
        msg = "Expected an int, list[int], comma-separated string, or null."
        raise TypeError(msg)
    parsed = sorted({item for item in parsed if item >= 0})
    if not parsed:
        msg = "At least one non-negative integer is required."
        raise ValueError(msg)
    return parsed


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    config = load_yaml(args.config)
    merged_manifest = resolve_path(config["merged_manifest"], base_dir=project_root)
    mtp_token_manifest = resolve_path(config["mtp_token_manifest"], base_dir=project_root)
    output_path = resolve_path(config["output_path"], base_dir=project_root)

    report = simulate_prefetch_shadow(
        merged_manifest,
        mtp_token_manifest,
        future_window=int(config.get("future_window", 1)),
        num_experts=int(config.get("num_experts", 256)),
        val_fraction=float(config.get("val_fraction", 0.25)),
        max_samples=(
            int(config["max_samples"]) if config.get("max_samples") is not None else None
        ),
        max_tokens=int(config["max_tokens"]) if config.get("max_tokens") is not None else None,
        transition_topk=int(config.get("transition_topk", 32)),
        mtp_topk=int(config.get("mtp_topk", 64)),
        max_extras=_parse_int_list(config.get("max_extras"), default=[1, 2, 4, 8]),
        default_max_extra=int(config.get("default_max_extra", 4)),
        high_budget_max_extra=int(config.get("high_budget_max_extra", 8)),
        cache_capacities=_parse_int_list(
            config.get("cache_capacities"),
            default=[96, 128, 160, 192, 224, 256],
        ),
        action_keep_fraction=float(config.get("action_keep_fraction", 0.5)),
        metadata_score_ratio=float(config.get("metadata_score_ratio", 0.95)),
        metadata_max_extra=int(config.get("metadata_max_extra", 1)),
        premap_max_extra=int(config.get("premap_max_extra", 1)),
    )
    written_path = write_prefetch_shadow_report(report, output_path)
    print(
        json.dumps(
            {
                "ok": True,
                "output_path": str(written_path),
                "capacity_guarded_policies": report.capacity_guarded_policies,
                "eval_split": report.eval_split,
                "num_eval_token_examples": report.num_eval_token_examples,
                "policies": report.policies,
                "priority_tiers": report.priority_tiers,
                "action_shadow_policies": report.action_shadow_policies,
                "policy_working_sets": report.policy_working_sets,
                "priority_admission_policies": report.priority_admission_policies,
                "recommendation": report.recommendation,
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
