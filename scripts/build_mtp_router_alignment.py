#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.tracing import load_trace_payload, resolve_trace_sample  # noqa: E402
from mtp_expert_prefetch.training import build_mtp_router_alignment  # noqa: E402


DEFAULT_MANIFEST = Path("data/traces/aya_dataset_smoke_autoround/manifest.jsonl")
DEFAULT_OUTPUT = Path("data/processed/mtp_router_alignment_smoke/sample_000000.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an MTP-router-to-future-backbone-router alignment sample."
    )
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--future-window", type=int, default=4)
    parser.add_argument("--call-index", type=int, default=0)
    parser.add_argument("--batch-index", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sample_path = resolve_trace_sample(sample_path=args.sample, manifest_path=args.manifest)
    payload = load_trace_payload(sample_path)
    alignment = build_mtp_router_alignment(
        payload,
        future_window=args.future_window,
        call_index=args.call_index,
        batch_index=args.batch_index,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(alignment.as_dict(), args.output)
    result = {
        "ok": True,
        "sample": str(sample_path),
        "output": str(args.output),
        "future_window": args.future_window,
        "mtp_expert_ids_shape": list(alignment.mtp_expert_ids.shape),
        "mtp_expert_weights_shape": list(alignment.mtp_expert_weights.shape),
        "target_expert_ids_shape": list(alignment.target_expert_ids.shape),
        "target_layer_ids_shape": list(alignment.target_layer_ids.shape),
        "source_token_indices_shape": list(alignment.source_token_indices.shape),
        "target_token_indices_shape": list(alignment.target_token_indices.shape),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
