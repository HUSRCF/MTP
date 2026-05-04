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
        description="Evaluate token-level ready-before-demand prefetch mass under lead-time limits."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/ready_before_demand.json"),
    )
    parser.add_argument("--max-extra", type=int, action="append", default=None)
    parser.add_argument("--num-layers", type=int, default=40)
    parser.add_argument("--layer-ms", type=float, default=1.0)
    parser.add_argument("--sampling-ms", type=float, default=0.0)
    parser.add_argument("--mtp-delay-ms", type=float, default=0.0)
    parser.add_argument("--bandwidth-gbps", type=float, default=16.0)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument("--device", default="cpu", help="Evaluation device, e.g. cpu or cuda.")
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
    max_extras = sorted({int(item) for item in (args.max_extra or config.get("max_extras", [4, 8]))})

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
        msg = "Empty train/eval split; cannot evaluate ready-before-demand policy."
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
    policies = {"transition_ready": base_metrics}
    lead_stats = {}
    offline_policies = {}
    for max_extra in max_extras:
        offline_mask = base_mask | novel_mtp_extra_mask(
            base_mask,
            mtp_scores,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
        )
        offline_metrics = mask_metrics(offline_mask, target_mass, base_mask=base_mask)
        offline_metrics["delta_pool_mass_coverage"] = (
            offline_metrics["pool_mass_coverage"] - base_metrics["pool_mass_coverage"]
        )
        offline_metrics["delta_weighted_top1_miss"] = (
            offline_metrics["weighted_top1_miss"] - base_metrics["weighted_top1_miss"]
        )
        offline_name = f"transition_top{transition_topk}_plus_offline_mtp_extra{max_extra}"
        offline_policies[offline_name] = offline_metrics

        ready_mask, stats = lead_time_ready_mask(
            transition_scores,
            mtp_scores,
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
            num_layers=int(args.num_layers),
            layer_ms=float(args.layer_ms),
            sampling_ms=float(args.sampling_ms),
            mtp_delay_ms=float(args.mtp_delay_ms),
            bandwidth_gbps=float(args.bandwidth_gbps),
            expert_bytes=int(args.expert_bytes),
        )
        metrics = mask_metrics(ready_mask, target_mass, base_mask=base_mask)
        metrics["delta_pool_mass_coverage"] = (
            metrics["pool_mass_coverage"] - base_metrics["pool_mass_coverage"]
        )
        metrics["delta_weighted_top1_miss"] = (
            metrics["weighted_top1_miss"] - base_metrics["weighted_top1_miss"]
        )
        offline_gain = max(0.0, float(offline_metrics["delta_pool_mass_coverage"]))
        metrics["offline_delta_pool_mass_coverage"] = float(
            offline_metrics["delta_pool_mass_coverage"]
        )
        metrics["realized_gain_ratio"] = (
            float(metrics["delta_pool_mass_coverage"]) / offline_gain
            if offline_gain > 0.0
            else 0.0
        )
        offline_risk_drop = max(
            0.0,
            -float(offline_metrics["delta_weighted_top1_miss"]),
        )
        metrics["offline_delta_weighted_top1_miss"] = float(
            offline_metrics["delta_weighted_top1_miss"]
        )
        metrics["realized_risk_reduction_ratio"] = (
            -float(metrics["delta_weighted_top1_miss"]) / offline_risk_drop
            if offline_risk_drop > 0.0
            else 0.0
        )
        name = f"transition_top{transition_topk}_plus_ready_mtp_extra{max_extra}"
        policies[name] = metrics
        lead_stats[name] = stats

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
        "num_layers": int(args.num_layers),
        "layer_ms": float(args.layer_ms),
        "sampling_ms": float(args.sampling_ms),
        "mtp_delay_ms": float(args.mtp_delay_ms),
        "bandwidth_gbps": float(args.bandwidth_gbps),
        "expert_bytes": int(args.expert_bytes),
        "device": str(device),
        "policies": policies,
        "offline_policies": offline_policies,
        "lead_stats": lead_stats,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
