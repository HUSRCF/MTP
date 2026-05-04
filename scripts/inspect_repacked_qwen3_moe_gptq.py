#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.repack import RepackedMoeExpertStore


DEFAULT_REPACKED_DIR = Path("data/repacked/qwen3_6_moe_experts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect repacked Qwen3 MoE GPTQ expert tensors without loading the full model."
    )
    parser.add_argument(
        "--repacked-dir",
        type=Path,
        default=DEFAULT_REPACKED_DIR,
        help=f"Directory containing summary.json, manifest.jsonl, and layer_XX.safetensors files. "
        f"Default: {DEFAULT_REPACKED_DIR}",
    )
    parser.add_argument(
        "--check-hashes",
        action="store_true",
        help="Read every fused tensor and verify sha256. This is slower and streams the repacked data.",
    )
    parser.add_argument(
        "--sample-layer",
        type=int,
        default=0,
        help="Layer used for printing one sample tensor metadata record.",
    )
    parser.add_argument(
        "--sample-expert",
        type=int,
        default=0,
        help="Expert id used for printing one sample slice shape.",
    )
    parser.add_argument("--sample-projection", default="gate_proj")
    parser.add_argument("--sample-kind", default="qweight")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with RepackedMoeExpertStore(args.repacked_dir) as store:
        result = store.inspect(check_hashes=args.check_hashes)
        info = store.tensor_info(args.sample_layer, args.sample_projection, args.sample_kind)
        sample = store.get_expert_tensor(
            args.sample_layer,
            args.sample_expert,
            args.sample_projection,
            args.sample_kind,
        )
        result["sample"] = {
            "layer": args.sample_layer,
            "expert": args.sample_expert,
            "projection": args.sample_projection,
            "kind": args.sample_kind,
            "fused_key": info.key,
            "fused_shape": list(info.shape),
            "fused_dtype": info.dtype,
            "expert_slice_shape": list(sample.shape),
            "expert_slice_dtype": str(sample.dtype).replace("torch.", ""),
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
