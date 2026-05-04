#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.training.alignment_merge import (  # noqa: E402
    manifest_record_path,
    read_trace_manifest,
)
from mtp_expert_prefetch.utils.config import find_project_root, resolve_path  # noqa: E402

DEFAULT_MERGED_MANIFEST = Path("data/traces/aya_dataset_smoke_merged_mtp_vllm/manifest.jsonl")
DEFAULT_MTP_TOKEN_MANIFEST = Path(
    "data/traces/mtp_token_topm_64sample_prefc_fixed/manifest.jsonl"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace merged native MTP router fields with fixed MTP sidecar outputs."
    )
    parser.add_argument("--merged-manifest", type=Path, default=DEFAULT_MERGED_MANIFEST)
    parser.add_argument("--mtp-token-manifest", type=Path, default=DEFAULT_MTP_TOKEN_MANIFEST)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/traces/aya_dataset_smoke_merged_mtp_vllm_prefc_fixed"),
    )
    parser.add_argument("--max-samples", type=int, default=None)
    return parser.parse_args()


def _as_batched_topk(tensor: torch.Tensor, *, token_limit: int) -> torch.Tensor:
    value = torch.as_tensor(tensor)
    if value.ndim == 2:
        value = value.unsqueeze(0)
    if value.ndim != 3:
        msg = f"Expected top-k tensor with shape [batch, tokens, topk], got {tuple(value.shape)}"
        raise ValueError(msg)
    return value[:, :token_limit].contiguous()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.merged_manifest)
    merged_manifest = resolve_path(args.merged_manifest, base_dir=project_root)
    mtp_token_manifest = resolve_path(args.mtp_token_manifest, base_dir=project_root)
    output_dir = resolve_path(args.output_dir, base_dir=project_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    merged_records = read_trace_manifest(merged_manifest)
    if args.max_samples is not None:
        merged_records = merged_records[: int(args.max_samples)]
    sidecar_records = {
        int(record["sample_idx"]): record for record in read_trace_manifest(mtp_token_manifest)
    }
    output_manifest = output_dir / "manifest.jsonl"
    with output_manifest.open("w", encoding="utf-8") as manifest:
        for index, record in enumerate(merged_records):
            sample_idx = int(record["sample_idx"])
            if sample_idx not in sidecar_records:
                msg = f"Missing fixed MTP sidecar for sample_idx={sample_idx}"
                raise KeyError(msg)
            merged_payload = torch.load(
                manifest_record_path(record),
                map_location="cpu",
                weights_only=False,
            )
            sidecar_payload = torch.load(
                manifest_record_path(sidecar_records[sample_idx]),
                map_location="cpu",
                weights_only=False,
            )
            token_limit = int(merged_payload["input_ids"].shape[-1])
            merged_payload["native_mtp_router_topk"] = _as_batched_topk(
                sidecar_payload["native_mtp_router_topk"],
                token_limit=token_limit,
            )
            merged_payload["native_mtp_router_weights"] = _as_batched_topk(
                sidecar_payload["native_mtp_router_weights"],
                token_limit=token_limit,
            )
            merged_payload["native_mtp_prefc_order_fixed"] = True
            output_path = output_dir / f"sample_{sample_idx:06d}.pt"
            torch.save(merged_payload, output_path)

            output_record = {
                key: value for key, value in record.items() if not str(key).startswith("_")
            }
            output_record["path"] = output_path.name
            output_record["native_mtp_prefc_order_fixed"] = True
            output_record["fixed_mtp_sidecar_path"] = str(
                manifest_record_path(sidecar_records[sample_idx])
            )
            manifest.write(json.dumps(output_record, ensure_ascii=False) + "\n")
            print(f"{index + 1}/{len(merged_records)} sample_{sample_idx:06d}", flush=True)
    print(str(output_manifest))


if __name__ == "__main__":
    main()
