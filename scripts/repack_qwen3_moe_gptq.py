from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from huggingface_hub import snapshot_download

from mtp_expert_prefetch.repack.qwen3_moe_gptq import repack_qwen3_moe_gptq


DEFAULT_MODEL_ID = "palmfuture/Qwen3.6-35B-A3B-GPTQ-Int4"
DEFAULT_OUTPUT_DIR = Path("data/repacked/qwen3_6_moe_experts")


def resolve_snapshot_path(model_id: str, snapshot: Path | None, local_files_only: bool) -> Path:
    if snapshot is not None:
        return snapshot
    return Path(snapshot_download(model_id, local_files_only=local_files_only))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repack Qwen3.6 MoE GPTQ expert tensors into per-layer fused safetensors."
    )
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="HF model id used to resolve cache.")
    parser.add_argument("--snapshot", type=Path, default=None, help="Local snapshot directory.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    parser.add_argument(
        "--layers",
        default=None,
        help="Optional layer selection, e.g. '0', '0,3,7', or '0-3'. Default: all layers.",
    )
    parser.add_argument("--num-experts", type=int, default=256, help="Expected experts per layer.")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Check every stacked slice equals the original expert tensor before saving.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing manifest.")
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
    manifest_path = repack_qwen3_moe_gptq(
        snapshot_path,
        args.output_dir,
        layers=args.layers,
        num_experts=args.num_experts,
        verify=args.verify,
        overwrite=args.overwrite,
    )
    print(manifest_path)


if __name__ == "__main__":
    main()
