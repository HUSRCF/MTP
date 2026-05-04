#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation.prefetch_shadow import (  # noqa: E402
    _apply_mtp_token_frequency_table,
    _load_alignment_samples,
    _load_mtp_token_samples,
    _samples_to_dataset,
    _split_positions,
    lead_time_ready_mask,
    mask_metrics,
    novel_mtp_extra_mask,
    queue_aware_ready_mask,
    topk_mask,
)
from mtp_expert_prefetch.training import (  # noqa: E402
    apply_transition_matrix,
    build_token_frequency_table,
    train_frequency_scores,
    train_transition_matrix,
)
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path  # noqa: E402


DEFAULT_CONFIG = Path("configs/eval/prefetch_shadow_256sample_mtp_extra.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep ready-before-demand expert prefetch assumptions."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/ready_sweep.json"),
    )
    parser.add_argument("--max-extra", type=int, action="append", default=None)
    parser.add_argument("--bandwidth-gbps", type=float, action="append", default=None)
    parser.add_argument("--layer-ms", type=float, action="append", default=None)
    parser.add_argument("--mtp-delay-ms", type=float, action="append", default=None)
    parser.add_argument("--sampling-ms", type=float, default=0.0)
    parser.add_argument("--num-layers", type=int, default=40)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument("--device", default="cpu", help="Evaluation device, e.g. cpu or cuda.")
    parser.add_argument(
        "--mode",
        choices=["independent", "queue"],
        default="independent",
        help="independent applies per-source lead limits; queue shares the late window by priority.",
    )
    return parser.parse_args()


def _resolve_device(name: str) -> torch.device:
    if name.startswith("cuda") and not torch.cuda.is_available():
        msg = f"Requested {name}, but torch.cuda.is_available() is false."
        raise RuntimeError(msg)
    return torch.device(name)


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    config = load_yaml(args.config)
    merged_manifest = resolve_path(config["merged_manifest"], base_dir=project_root)
    mtp_token_manifest = resolve_path(config["mtp_token_manifest"], base_dir=project_root)
    output = resolve_path(args.output, base_dir=project_root)

    future_window = int(config.get("future_window", 1))
    max_samples = int(config["max_samples"]) if config.get("max_samples") is not None else None
    max_tokens = int(config["max_tokens"]) if config.get("max_tokens") is not None else None
    transition_topk = int(config.get("transition_topk", 32))
    mtp_topk = int(config.get("mtp_topk", 64))
    max_extras = sorted({int(item) for item in (args.max_extra or [4, 8])})
    bandwidths = sorted({float(item) for item in (args.bandwidth_gbps or [2, 4, 8, 16, 32])})
    layer_times = sorted({float(item) for item in (args.layer_ms or [0.25, 0.5, 1.0, 2.0])})
    mtp_delays = sorted({float(item) for item in (args.mtp_delay_ms or [0, 1, 2, 4, 8])})

    alignment_samples = _load_alignment_samples(
        merged_manifest,
        future_window=future_window,
        max_samples=max_samples,
    )
    token_samples = _load_mtp_token_samples(mtp_token_manifest)
    train_positions, val_positions = _split_positions(
        len(alignment_samples),
        float(config.get("val_fraction", 0.25)),
    )
    train = _samples_to_dataset(
        alignment_samples,
        token_samples,
        train_positions,
        num_experts=int(config.get("num_experts", 256)),
        max_tokens=max_tokens,
    )
    val = _samples_to_dataset(
        alignment_samples,
        token_samples,
        val_positions,
        num_experts=int(config.get("num_experts", 256)),
        max_tokens=max_tokens,
    )
    eval_data = val if val is not None else train
    if train is None or eval_data is None:
        msg = "Empty train/eval split; cannot sweep ready-before-demand policies."
        raise RuntimeError(msg)

    transition = train_transition_matrix(train.current_feature, train.target_mass)
    transition_scores = apply_transition_matrix(eval_data.current_feature, transition)
    frequency_scores = train_frequency_scores(train.target_mass)
    target_token_table = build_token_frequency_table(
        train.target_token_ids,
        train.target_mass,
        fallback=frequency_scores,
    )
    mtp_scores = _apply_mtp_token_frequency_table(
        target_token_table,
        eval_data.mtp_topm_ids,
        eval_data.mtp_topm_probs,
    )
    device = _resolve_device(args.device)
    target_mass = eval_data.target_mass.to(device)
    transition_scores = transition_scores.to(device)
    mtp_scores = mtp_scores.to(device)

    base_mask = topk_mask(transition_scores, k=transition_topk)
    base_metrics = mask_metrics(base_mask, target_mass)
    offline_by_extra = {}
    for max_extra in max_extras:
        offline_mask = base_mask | novel_mtp_extra_mask(
            base_mask,
            mtp_scores,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
        )
        offline = mask_metrics(offline_mask, target_mass, base_mask=base_mask)
        offline["delta_pool_mass_coverage"] = (
            offline["pool_mass_coverage"] - base_metrics["pool_mass_coverage"]
        )
        offline["delta_weighted_top1_miss"] = (
            offline["weighted_top1_miss"] - base_metrics["weighted_top1_miss"]
        )
        offline_by_extra[str(max_extra)] = offline

    rows = []
    for max_extra in max_extras:
        offline = offline_by_extra[str(max_extra)]
        offline_gain = max(0.0, float(offline["delta_pool_mass_coverage"]))
        offline_risk_drop = max(0.0, -float(offline["delta_weighted_top1_miss"]))
        for bandwidth in bandwidths:
            for layer_ms in layer_times:
                for delay in mtp_delays:
                    ready_mask, lead_stats = lead_time_ready_mask(
                        transition_scores,
                        mtp_scores,
                        transition_topk=transition_topk,
                        mtp_topk=mtp_topk,
                        max_extra=max_extra,
                        num_layers=int(args.num_layers),
                        layer_ms=layer_ms,
                        sampling_ms=float(args.sampling_ms),
                        mtp_delay_ms=delay,
                        bandwidth_gbps=bandwidth,
                        expert_bytes=int(args.expert_bytes),
                    ) if args.mode == "independent" else queue_aware_ready_mask(
                        transition_scores,
                        mtp_scores,
                        transition_topk=transition_topk,
                        mtp_topk=mtp_topk,
                        max_extra=max_extra,
                        num_layers=int(args.num_layers),
                        layer_ms=layer_ms,
                        sampling_ms=float(args.sampling_ms),
                        mtp_delay_ms=delay,
                        bandwidth_gbps=bandwidth,
                        expert_bytes=int(args.expert_bytes),
                    )
                    ready = mask_metrics(ready_mask, target_mass, base_mask=base_mask)
                    delta_mass = ready["pool_mass_coverage"] - base_metrics["pool_mass_coverage"]
                    risk_delta = ready["weighted_top1_miss"] - base_metrics["weighted_top1_miss"]
                    rows.append(
                        {
                            "max_extra": int(max_extra),
                            "bandwidth_gbps": float(bandwidth),
                            "layer_ms": float(layer_ms),
                            "mtp_delay_ms": float(delay),
                            "pool_mass_coverage": ready["pool_mass_coverage"],
                            "delta_pool_mass_coverage": delta_mass,
                            "offline_delta_pool_mass_coverage": offline[
                                "delta_pool_mass_coverage"
                            ],
                            "realized_gain_ratio": (
                                delta_mass / offline_gain if offline_gain > 0.0 else 0.0
                            ),
                            "weighted_top1_miss": ready["weighted_top1_miss"],
                            "delta_weighted_top1_miss": risk_delta,
                            "offline_delta_weighted_top1_miss": offline[
                                "delta_weighted_top1_miss"
                            ],
                            "realized_risk_reduction_ratio": (
                                -risk_delta / offline_risk_drop
                                if offline_risk_drop > 0.0
                                else 0.0
                            ),
                            "avg_extra_count": ready["avg_extra_count"],
                            "ready_extra_fraction": lead_stats["ready_extra_fraction"],
                            "mtp_cap_mean": lead_stats["mtp_cap_mean"],
                            "mtp_cap_p50": lead_stats["mtp_cap_p50"],
                        }
                    )

    payload = {
        "ok": True,
        "config": str(resolve_path(args.config, base_dir=project_root)),
        "merged_manifest": str(merged_manifest),
        "mtp_token_manifest": str(mtp_token_manifest),
        "output": str(output),
        "eval_split": "val" if val is not None else "train",
        "num_eval_token_examples": int(eval_data.target_mass.shape[0]),
        "transition_topk": transition_topk,
        "mtp_topk": mtp_topk,
        "max_extras": max_extras,
        "bandwidths_gbps": bandwidths,
        "layer_times_ms": layer_times,
        "mtp_delays_ms": mtp_delays,
        "expert_bytes": int(args.expert_bytes),
        "device": str(device),
        "mode": args.mode,
        "base_metrics": base_metrics,
        "offline_by_extra": offline_by_extra,
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
