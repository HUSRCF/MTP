from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from huggingface_hub import snapshot_download

from mtp_expert_prefetch.repack.qwen3_moe_gptq import verify_random_repacked_slices


DEFAULT_MODEL_ID = "palmfuture/Qwen3.6-35B-A3B-GPTQ-Int4"
DEFAULT_REPACKED_DIR = Path("data/repacked/qwen3_6_moe_experts")


def resolve_snapshot_path(model_id: str, snapshot: Path | None, local_files_only: bool) -> Path:
    if snapshot is not None:
        return snapshot
    return Path(snapshot_download(model_id, local_files_only=local_files_only))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Randomly verify fused Qwen3.6 MoE GPTQ expert slices against the original checkpoint."
    )
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="HF model id used to resolve cache.")
    parser.add_argument("--snapshot", type=Path, default=None, help="Local snapshot directory.")
    parser.add_argument("--repacked-dir", type=Path, default=DEFAULT_REPACKED_DIR)
    parser.add_argument("--samples", type=int, default=128, help="Number of random slices to check.")
    parser.add_argument("--seed", type=int, default=0, help="Random seed.")
    parser.add_argument(
        "--layers",
        default=None,
        help="Optional layer selection, e.g. '0', '0,3,7', or '0-3'. Default: all repacked layers.",
    )
    parser.add_argument("--num-experts", type=int, default=None, help="Override expected experts.")
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Continue checking after the first mismatch.",
    )
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Allow Hugging Face to download missing files. Default uses local cache only.",
    )
    args = parser.parse_args()

    snapshot_path = resolve_snapshot_path(
        args.model_id,
        args.snapshot,
        local_files_only=not args.allow_download,
    )
    result = verify_random_repacked_slices(
        snapshot_path,
        args.repacked_dir,
        samples=args.samples,
        seed=args.seed,
        layers=args.layers,
        num_experts=args.num_experts,
        fail_fast=not args.no_fail_fast,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
