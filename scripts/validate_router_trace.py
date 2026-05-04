#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation import (  # noqa: E402
    analyze_router_trace_sanity,
    write_router_trace_sanity_report,
)
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path  # noqa: E402


DEFAULT_CONFIG = Path("configs/eval/router_trace_sanity_awq_vllm.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate router trace ids/weights semantics.")
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    config = load_yaml(resolve_path(args.config, base_dir=project_root))
    report = analyze_router_trace_sanity(
        resolve_path(config["manifest_path"], base_dir=project_root),
        expected_trace_source=config.get("expected_trace_source"),
        expected_layers=int(config["expected_layers"]) if config.get("expected_layers") else None,
        num_experts=int(config.get("num_experts", 256)),
        max_samples=int(config["max_samples"]) if config.get("max_samples") else None,
    )
    output_path = resolve_path(config["output_path"], base_dir=project_root)
    write_router_trace_sanity_report(report, output_path)
    print(
        json.dumps(
            report.as_dict() | {"output_path": str(output_path)},
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
