#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mtp_expert_prefetch.runtime import simulate_stall_proxy  # noqa: E402
from mtp_expert_prefetch.utils.config import find_project_root, resolve_path  # noqa: E402
from simulate_prefetch_event_stalls import (  # noqa: E402
    DEFAULT_CONFIG,
    _build_gated_shadow_inputs,
    _resolve_device,
)


DEFAULT_CACHE = Path(
    "outputs/reports/prefetch_shadow_256sample_mtp_extra/"
    "event_stall_tensor_cache_256sample.pt"
)
DEFAULT_OUTPUT = Path(
    "outputs/reports/prefetch_shadow_256sample_mtp_extra/"
    "metadata_action_gate_sweep.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep metadata-only high-tail action gates under different overlap assumptions."
        )
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument("--tensor-cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--transition-topk", type=int, default=32)
    parser.add_argument("--mtp-topk", type=int, default=64)
    parser.add_argument("--gate-max-extra", type=int, default=4)
    parser.add_argument("--gate-keep-fraction", type=float, default=0.5)
    parser.add_argument("--metadata-ratio", type=float, action="append", default=None)
    parser.add_argument("--overlap-factor", type=float, action="append", default=None)
    parser.add_argument(
        "--num-shards",
        type=int,
        default=1,
        help="Split the ratio/overlap sweep into this many shards.",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=0,
        help="Run only this zero-based sweep shard.",
    )
    parser.add_argument("--admission-capacity-per-layer", type=int, default=160)
    parser.add_argument("--bandwidth-gbps", type=float, default=6.589)
    parser.add_argument("--layer-ms", type=float, default=1.0)
    parser.add_argument("--sampling-ms", type=float, default=0.0)
    parser.add_argument("--mtp-delay-ms", type=float, default=2.0)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument("--metadata-bytes", type=int, default=65_536)
    parser.add_argument("--metadata-supplemental-saved-us", type=float, default=20.0)
    parser.add_argument("--full-fetch-ready-threshold", type=float, default=0.99)
    parser.add_argument(
        "--include-full-reports",
        action="store_true",
        help="Store the full event-simulator report for every sweep point.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    tensor_cache = resolve_path(args.tensor_cache, base_dir=project_root)
    output = resolve_path(args.output, base_dir=project_root)
    device = _resolve_device(args.device)
    cache = torch.load(tensor_cache, map_location="cpu")
    train_transition_scores = cache["train_transition_scores"]
    train_mtp_scores = cache["train_mtp_scores"]
    train_target_mass = cache["train_target_mass"]
    transition_scores = cache["transition_scores"]
    mtp_scores = cache["mtp_scores"]
    target_mass = cache["target_mass"]
    token_sample_indices = cache.get("token_sample_indices")

    gated_score_tensors, gated_score_thresholds = _build_gated_shadow_inputs(
        train_transition_scores=train_transition_scores,
        train_mtp_scores=train_mtp_scores,
        train_target_mass=train_target_mass,
        eval_transition_scores=transition_scores,
        eval_mtp_scores=mtp_scores,
        transition_topk=int(args.transition_topk),
        mtp_topk=int(args.mtp_topk),
        gate_max_extra=int(args.gate_max_extra),
        keep_fractions=[float(args.gate_keep_fraction)],
        layer_ms=float(args.layer_ms),
        sampling_ms=float(args.sampling_ms),
        mtp_delay_ms=float(args.mtp_delay_ms),
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
        utility_rank_alpha=1.0,
        use_layer_factor=True,
        use_ready_factor=True,
        device=device,
    )
    metadata_ratios = args.metadata_ratio or [0.5, 0.75, 0.9, 0.95, 0.99]
    overlap_factors = args.overlap_factor or [0.0, 0.5, 0.8, 0.9, 0.95]
    if args.num_shards < 1:
        raise ValueError("--num-shards must be >= 1")
    if args.shard_index < 0 or args.shard_index >= args.num_shards:
        raise ValueError("--shard-index must satisfy 0 <= index < num_shards")
    sweep_pairs = [
        (float(metadata_ratio), float(overlap_factor))
        for metadata_ratio in metadata_ratios
        for overlap_factor in overlap_factors
    ]
    sweep_pairs = [
        pair
        for index, pair in enumerate(sweep_pairs)
        if index % int(args.num_shards) == int(args.shard_index)
    ]
    rows = []
    reports = {}
    transition_scores_device = transition_scores.to(device)
    mtp_scores_device = mtp_scores.to(device)
    target_mass_device = target_mass.to(device)
    token_sample_indices_device = (
        token_sample_indices.to(device) if token_sample_indices is not None else None
    )
    for pair_index, (metadata_ratio, overlap_factor) in enumerate(sweep_pairs, start=1):
        print(
            json.dumps(
                {
                    "progress": f"{pair_index}/{len(sweep_pairs)}",
                    "metadata_ratio": metadata_ratio,
                    "overlap_factor": overlap_factor,
                    "device": str(device),
                }
            ),
            flush=True,
        )
        report = simulate_stall_proxy(
            transition_scores_device,
            mtp_scores_device,
            target_mass_device,
            transition_topk=int(args.transition_topk),
            mtp_topk=int(args.mtp_topk),
            max_extras=[int(args.gate_max_extra)],
            num_layers=int(target_mass.shape[2]),
            layer_ms=float(args.layer_ms),
            sampling_ms=float(args.sampling_ms),
            mtp_delay_ms=float(args.mtp_delay_ms),
            bandwidth_gbps=float(args.bandwidth_gbps),
            expert_bytes=int(args.expert_bytes),
            token_sample_indices=token_sample_indices_device,
            admission_capacity_per_layer=int(args.admission_capacity_per_layer),
            gated_score_tensors=gated_score_tensors,
            gated_score_thresholds=gated_score_thresholds,
            gated_max_extra=int(args.gate_max_extra),
            enable_gated_action_downgrade=True,
            gated_metadata_threshold_ratio=float(metadata_ratio),
            gated_premap_downgrade_enabled=False,
            gated_full_fetch_ready_threshold=float(args.full_fetch_ready_threshold),
            metadata_bytes=int(args.metadata_bytes),
            metadata_supplemental_saved_us=float(args.metadata_supplemental_saved_us),
            action_cost_overlap_factor=float(overlap_factor),
            include_unique_payload_counters=False,
        )
        if args.include_full_reports:
            reports[
                f"metadata_ratio_{metadata_ratio:.3f}_overlap_{overlap_factor:.3f}"
            ] = report.as_dict()
        for policy_name, metrics in report.policies.items():
            if "_gated_" not in policy_name:
                continue
            metadata = metrics["admission_action_outcomes"]["metadata"]
            rows.append(
                {
                    "metadata_ratio": float(metadata_ratio),
                    "overlap_factor": float(overlap_factor),
                    "policy": policy_name,
                    "metadata_count": metadata["count"],
                    "metadata_later_used_count": metadata["later_used_count"],
                    "metadata_later_used_rate": metadata["later_used_rate"],
                    "metadata_actual_bytes": metadata["actual_bytes"],
                    "metadata_net_setup_benefit_ms": metadata["net_setup_benefit_ms"],
                    "metadata_overlap_adjusted_net_setup_benefit_ms": metadata[
                        "overlap_adjusted_net_setup_benefit_ms"
                    ],
                    "metadata_setup_saved_ms": metadata["later_used_setup_saved_ms"],
                    "stall_reduction_ratio_vs_transition": metrics[
                        "stall_reduction_ratio_vs_transition"
                    ],
                    "overlap_adjusted_net_benefit_ms_vs_transition": metrics[
                        "overlap_adjusted_net_benefit_ms_vs_transition"
                    ],
                }
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    csv_output = output.with_suffix(".csv")
    if rows:
        with csv_output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    payload = {
        "ok": True,
        "tensor_cache": str(tensor_cache),
        "output": str(output),
        "csv_output": str(csv_output),
        "device": str(device),
        "metadata_ratios": [float(value) for value in metadata_ratios],
        "overlap_factors": [float(value) for value in overlap_factors],
        "num_shards": int(args.num_shards),
        "shard_index": int(args.shard_index),
        "sweep_points": [
            {"metadata_ratio": ratio, "overlap_factor": overlap}
            for ratio, overlap in sweep_pairs
        ],
        "rows": rows,
        "reports": reports,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "reports"}, indent=2))


if __name__ == "__main__":
    main()
