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
)
from mtp_expert_prefetch.runtime import simulate_stall_proxy  # noqa: E402
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
        description="Sweep queue-aware event stall proxy assumptions."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/event_stall_sweep.json"),
    )
    parser.add_argument("--max-extra", type=int, action="append", default=None)
    parser.add_argument("--bandwidth-gbps", type=float, action="append", default=None)
    parser.add_argument("--layer-ms", type=float, action="append", default=None)
    parser.add_argument("--mtp-delay-ms", type=float, action="append", default=None)
    parser.add_argument("--sampling-ms", type=float, default=0.0)
    parser.add_argument("--num-layers", type=int, default=40)
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
    if future_window != 1:
        msg = "Event stall sweep currently expects future_window=1."
        raise ValueError(msg)
    max_samples = int(config["max_samples"]) if config.get("max_samples") is not None else None
    max_tokens = int(config["max_tokens"]) if config.get("max_tokens") is not None else None
    transition_topk = int(config.get("transition_topk", 32))
    mtp_topk = int(config.get("mtp_topk", 64))
    max_extras = sorted({int(item) for item in (args.max_extra or [1, 2, 4, 8])})
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
        msg = "Empty train/eval split; cannot sweep event stall proxy."
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

    rows = []
    for bandwidth in bandwidths:
        for layer_ms in layer_times:
            for delay in mtp_delays:
                report = simulate_stall_proxy(
                    transition_scores,
                    mtp_scores,
                    target_mass,
                    transition_topk=transition_topk,
                    mtp_topk=mtp_topk,
                    max_extras=max_extras,
                    num_layers=int(args.num_layers),
                    layer_ms=float(layer_ms),
                    sampling_ms=float(args.sampling_ms),
                    mtp_delay_ms=float(delay),
                    bandwidth_gbps=float(bandwidth),
                    expert_bytes=int(args.expert_bytes),
                )
                base = report.policies["transition_ready"]
                for max_extra in max_extras:
                    name = f"transition_top{transition_topk}_plus_ready_mtp_extra{max_extra}"
                    metrics = report.policies[name]
                    rows.append(
                        {
                            "max_extra": int(max_extra),
                            "bandwidth_gbps": float(bandwidth),
                            "layer_ms": float(layer_ms),
                            "mtp_delay_ms": float(delay),
                            "ready_mass_fraction": metrics["ready_mass_fraction"],
                            "supplemental_fetch_count": metrics["supplemental_fetch_count"],
                            "supplemental_fetch_bytes": metrics["supplemental_fetch_bytes"],
                            "supplemental_stall_ms_sum": metrics["supplemental_stall_ms_sum"],
                            "saved_supplemental_fetch_count_vs_transition": metrics[
                                "saved_supplemental_fetch_count_vs_transition"
                            ],
                            "saved_supplemental_stall_ms_vs_transition": metrics[
                                "saved_supplemental_stall_ms_vs_transition"
                            ],
                            "stall_reduction_ratio_vs_transition": metrics[
                                "stall_reduction_ratio_vs_transition"
                            ],
                            "ready_extra_fraction": metrics["queue_ready_extra_fraction"],
                            "base_supplemental_fetch_count": base["supplemental_fetch_count"],
                            "base_supplemental_stall_ms_sum": base[
                                "supplemental_stall_ms_sum"
                            ],
                        }
                    )

    summary: dict[str, dict[str, float]] = {}
    for max_extra in max_extras:
        selected = [row for row in rows if int(row["max_extra"]) == int(max_extra)]
        positive = [
            row
            for row in selected
            if float(row["saved_supplemental_stall_ms_vs_transition"]) > 0.0
        ]
        strong = [
            row
            for row in selected
            if float(row["stall_reduction_ratio_vs_transition"]) >= 0.05
        ]
        summary[str(max_extra)] = {
            "num_rows": float(len(selected)),
            "positive_saved_stall_rows": float(len(positive)),
            "stall_reduction_ge_5pct_rows": float(len(strong)),
            "mean_stall_reduction_ratio": float(
                sum(float(row["stall_reduction_ratio_vs_transition"]) for row in selected)
                / max(1, len(selected))
            ),
            "best_stall_reduction_ratio": float(
                max(float(row["stall_reduction_ratio_vs_transition"]) for row in selected)
            ),
            "worst_stall_reduction_ratio": float(
                min(float(row["stall_reduction_ratio_vs_transition"]) for row in selected)
            ),
        }

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
        "summary": summary,
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
