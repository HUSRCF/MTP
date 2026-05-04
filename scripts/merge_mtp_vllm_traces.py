#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.training.alignment_merge import merge_trace_manifests


DEFAULT_MTP_MANIFEST = Path("data/traces/aya_dataset_smoke_autoround/manifest.jsonl")
DEFAULT_TARGET_MANIFEST = Path("data/traces/aya_dataset_smoke_awq_vllm/manifest.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/traces/aya_dataset_smoke_merged_mtp_vllm")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge AutoRound native MTP router features with vLLM router targets."
    )
    parser.add_argument("--mtp-manifest", type=Path, default=DEFAULT_MTP_MANIFEST)
    parser.add_argument("--target-manifest", type=Path, default=DEFAULT_TARGET_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--token-policy", choices=["prefix", "strict"], default="prefix")
    parser.add_argument("--max-samples", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = merge_trace_manifests(
        mtp_manifest=args.mtp_manifest,
        target_manifest=args.target_manifest,
        output_dir=args.output_dir,
        token_policy=args.token_policy,
        max_samples=args.max_samples,
    )
    print(json.dumps({"ok": True, "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()
