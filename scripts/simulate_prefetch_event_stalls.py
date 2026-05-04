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
    novel_mtp_extra_mask,
    topk_mask,
)
from mtp_expert_prefetch.runtime.admission import build_mtp_extra_utility_scores  # noqa: E402
from mtp_expert_prefetch.runtime import simulate_stall_proxy, write_stall_proxy_report  # noqa: E402
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
        description="Convert queue-aware ready mass into supplemental fetch/stall proxies."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/event_stall_proxy.json"),
    )
    parser.add_argument(
        "--tensor-cache",
        type=Path,
        default=None,
        help="Load precomputed train/eval score tensors and skip manifest rebuilding.",
    )
    parser.add_argument(
        "--write-tensor-cache",
        type=Path,
        default=None,
        help="Write precomputed train/eval score tensors for faster follow-up sweeps.",
    )
    parser.add_argument("--max-extra", type=int, action="append", default=None)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--num-layers", type=int, default=40)
    parser.add_argument("--layer-ms", type=float, default=1.0)
    parser.add_argument("--sampling-ms", type=float, default=0.0)
    parser.add_argument("--mtp-delay-ms", type=float, default=0.0)
    parser.add_argument("--bandwidth-gbps", type=float, default=16.0)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument(
        "--admission-capacity-per-layer",
        type=int,
        default=None,
        help="Optional sample/layer priority admission capacity before event counters.",
    )
    parser.add_argument(
        "--include-gated-policies",
        action="store_true",
        help="Add MTP-score and utility-score threshold-gated shadow policies.",
    )
    parser.add_argument(
        "--gate-keep-fraction",
        type=float,
        action="append",
        default=None,
        help="Calibration keep fraction for gated policies, e.g. 0.5.",
    )
    parser.add_argument("--gate-max-extra", type=int, default=8)
    parser.add_argument("--utility-rank-alpha", type=float, default=1.0)
    parser.add_argument("--disable-utility-layer-factor", action="store_true")
    parser.add_argument("--disable-utility-ready-factor", action="store_true")
    parser.add_argument(
        "--enable-downgrade-actions",
        action="store_true",
        help=(
            "Downgrade gated MTP extras to metadata/premap instead of treating "
            "every score-passing candidate as full_fetch."
        ),
    )
    parser.add_argument(
        "--downgrade-metadata-threshold-ratio",
        type=float,
        default=0.5,
        help="metadata threshold as a ratio of the calibrated full_fetch threshold.",
    )
    parser.add_argument(
        "--downgrade-premap-threshold-ratio",
        type=float,
        default=0.25,
        help="premap threshold as a ratio of the calibrated full_fetch threshold.",
    )
    parser.add_argument(
        "--downgrade-full-fetch-ready-threshold",
        type=float,
        default=0.75,
        help="Minimum per-layer ready factor required for full_fetch MTP extras.",
    )
    parser.add_argument(
        "--disable-unique-payload-counters",
        action="store_true",
        help="Skip expensive sample/layer/expert unique payload counters.",
    )
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
        msg = "Event stall proxy currently expects future_window=1."
        raise ValueError(msg)
    max_samples = (
        int(args.max_samples)
        if args.max_samples is not None
        else int(config["max_samples"])
        if config.get("max_samples") is not None
        else None
    )
    max_tokens = (
        int(args.max_tokens)
        if args.max_tokens is not None
        else int(config["max_tokens"])
        if config.get("max_tokens") is not None
        else None
    )
    transition_topk = int(config.get("transition_topk", 32))
    mtp_topk = int(config.get("mtp_topk", 64))
    max_extras = sorted({int(item) for item in (args.max_extra or config.get("max_extras", [4, 8]))})

    tensor_cache_path = (
        resolve_path(args.tensor_cache, base_dir=project_root)
        if args.tensor_cache is not None
        else None
    )
    if tensor_cache_path is not None:
        cache = torch.load(tensor_cache_path, map_location="cpu")
        train_transition_scores = cache["train_transition_scores"]
        train_mtp_scores = cache["train_mtp_scores"]
        train_target_mass = cache["train_target_mass"]
        transition_scores = cache["transition_scores"]
        mtp_scores = cache["mtp_scores"]
        target_mass = cache["target_mass"]
        token_sample_indices = cache.get("token_sample_indices")
        eval_split_name = str(cache.get("eval_split", "cached"))
    else:
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
            msg = "Empty train/eval split; cannot simulate event stall proxy."
            raise RuntimeError(msg)

        transition = train_transition_matrix(train.current_feature, train.target_mass)
        transition_scores = apply_transition_matrix(eval_data.current_feature, transition)
        train_transition_scores = apply_transition_matrix(train.current_feature, transition)
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
        train_mtp_scores = _apply_mtp_token_frequency_table(
            target_token_table,
            train.mtp_topm_ids,
            train.mtp_topm_probs,
        )
        train_target_mass = train.target_mass
        target_mass = eval_data.target_mass
        token_sample_indices = eval_data.token_sample_indices
        eval_split_name = "val" if val is not None else "train"

        if args.write_tensor_cache is not None:
            written_cache = resolve_path(args.write_tensor_cache, base_dir=project_root)
            written_cache.parent.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "schema_version": 1,
                    "config": str(resolve_path(args.config, base_dir=project_root)),
                    "merged_manifest": str(merged_manifest),
                    "mtp_token_manifest": str(mtp_token_manifest),
                    "eval_split": eval_split_name,
                    "transition_topk": transition_topk,
                    "mtp_topk": mtp_topk,
                    "max_samples": max_samples,
                    "max_tokens": max_tokens,
                    "train_transition_scores": train_transition_scores.cpu(),
                    "train_mtp_scores": train_mtp_scores.cpu(),
                    "train_target_mass": train_target_mass.cpu(),
                    "transition_scores": transition_scores.cpu(),
                    "mtp_scores": mtp_scores.cpu(),
                    "target_mass": target_mass.cpu(),
                    "token_sample_indices": token_sample_indices.cpu(),
                },
                written_cache,
            )

    device = _resolve_device(args.device)
    gated_score_tensors = None
    gated_score_thresholds = None
    if args.include_gated_policies:
        keep_fractions = sorted(
            {float(value) for value in (args.gate_keep_fraction or [0.125, 0.25, 0.5, 0.75])}
        )
        gated_score_tensors, gated_score_thresholds = _build_gated_shadow_inputs(
            train_transition_scores=train_transition_scores,
            train_mtp_scores=train_mtp_scores,
            train_target_mass=train_target_mass,
            eval_transition_scores=transition_scores,
            eval_mtp_scores=mtp_scores,
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            gate_max_extra=int(args.gate_max_extra),
            keep_fractions=keep_fractions,
            layer_ms=float(args.layer_ms),
            sampling_ms=float(args.sampling_ms),
            mtp_delay_ms=float(args.mtp_delay_ms),
            bandwidth_gbps=float(args.bandwidth_gbps),
            expert_bytes=int(args.expert_bytes),
            utility_rank_alpha=float(args.utility_rank_alpha),
            use_layer_factor=not bool(args.disable_utility_layer_factor),
            use_ready_factor=not bool(args.disable_utility_ready_factor),
            device=device,
        )
    report = simulate_stall_proxy(
        transition_scores.to(device),
        mtp_scores.to(device),
        target_mass.to(device),
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extras=max_extras,
        num_layers=int(args.num_layers),
        layer_ms=float(args.layer_ms),
        sampling_ms=float(args.sampling_ms),
        mtp_delay_ms=float(args.mtp_delay_ms),
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
        token_sample_indices=(
            token_sample_indices.to(device) if token_sample_indices is not None else None
        ),
        admission_capacity_per_layer=(
            int(args.admission_capacity_per_layer)
            if args.admission_capacity_per_layer is not None
            else None
        ),
        gated_score_tensors=gated_score_tensors,
        gated_score_thresholds=gated_score_thresholds,
        gated_max_extra=int(args.gate_max_extra),
        enable_gated_action_downgrade=bool(args.enable_downgrade_actions),
        gated_metadata_threshold_ratio=float(args.downgrade_metadata_threshold_ratio),
        gated_premap_threshold_ratio=float(args.downgrade_premap_threshold_ratio),
        gated_full_fetch_ready_threshold=float(args.downgrade_full_fetch_ready_threshold),
        include_unique_payload_counters=not bool(args.disable_unique_payload_counters),
    )
    written_path = write_stall_proxy_report(report, output)
    payload = report.as_dict()
    payload.update(
        {
            "config": str(resolve_path(args.config, base_dir=project_root)),
            "merged_manifest": str(merged_manifest),
            "mtp_token_manifest": str(mtp_token_manifest),
            "output": str(written_path),
            "eval_split": eval_split_name,
            "num_eval_token_examples": int(target_mass.shape[0]),
            "device": str(device),
            "tensor_cache": str(tensor_cache_path) if tensor_cache_path is not None else None,
            "written_tensor_cache": (
                str(resolve_path(args.write_tensor_cache, base_dir=project_root))
                if args.write_tensor_cache is not None
                else None
            ),
            "admission_capacity_per_layer": (
                int(args.admission_capacity_per_layer)
                if args.admission_capacity_per_layer is not None
                else None
            ),
            "gated_policies": {
                "enabled": bool(args.include_gated_policies),
                "gate_max_extra": int(args.gate_max_extra),
                "keep_fractions": (
                    sorted(
                        {
                            float(value)
                            for value in (
                                args.gate_keep_fraction or [0.125, 0.25, 0.5, 0.75]
                            )
                        }
                    )
                    if args.include_gated_policies
                    else []
                ),
                "utility_rank_alpha": float(args.utility_rank_alpha),
                "utility_layer_factor_enabled": not bool(args.disable_utility_layer_factor),
                "utility_ready_factor_enabled": not bool(args.disable_utility_ready_factor),
                "downgrade_actions_enabled": bool(args.enable_downgrade_actions),
                "downgrade_metadata_threshold_ratio": float(
                    args.downgrade_metadata_threshold_ratio
                ),
                "downgrade_premap_threshold_ratio": float(
                    args.downgrade_premap_threshold_ratio
                ),
                "downgrade_full_fetch_ready_threshold": float(
                    args.downgrade_full_fetch_ready_threshold
                ),
                "unique_payload_counters_enabled": not bool(
                    args.disable_unique_payload_counters
                ),
            },
        }
    )
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def _build_gated_shadow_inputs(
    *,
    train_transition_scores: torch.Tensor,
    train_mtp_scores: torch.Tensor,
    train_target_mass: torch.Tensor,
    eval_transition_scores: torch.Tensor,
    eval_mtp_scores: torch.Tensor,
    transition_topk: int,
    mtp_topk: int,
    gate_max_extra: int,
    keep_fractions: list[float],
    layer_ms: float,
    sampling_ms: float,
    mtp_delay_ms: float,
    bandwidth_gbps: float,
    expert_bytes: int,
    utility_rank_alpha: float,
    use_layer_factor: bool,
    use_ready_factor: bool,
    device: torch.device,
) -> tuple[dict[str, torch.Tensor], dict[str, float]]:
    train_base = topk_mask(train_transition_scores, k=transition_topk)
    eval_base = topk_mask(eval_transition_scores, k=transition_topk)
    layer_factors = (
        _calibrated_layer_factors(
            train_base,
            train_mtp_scores,
            train_target_mass,
            mtp_topk=mtp_topk,
            max_extra=gate_max_extra,
        )
        if use_layer_factor
        else torch.ones(int(train_target_mass.shape[2]), dtype=torch.float32)
    )
    ready_factors = (
        _ready_layer_factors(
            num_layers=int(train_target_mass.shape[2]),
            layer_ms=layer_ms,
            sampling_ms=sampling_ms,
            mtp_delay_ms=mtp_delay_ms,
            bandwidth_gbps=bandwidth_gbps,
            expert_bytes=expert_bytes,
            max_extra=gate_max_extra,
            device=torch.device("cpu"),
        )
        if use_ready_factor
        else torch.ones(int(train_target_mass.shape[2]), dtype=torch.float32)
    )
    train_utility = build_mtp_extra_utility_scores(
        train_base,
        train_mtp_scores,
        mtp_topk=mtp_topk,
        rank_alpha=utility_rank_alpha,
        layer_factors=layer_factors,
        ready_factors=ready_factors,
    )
    eval_utility = build_mtp_extra_utility_scores(
        eval_base,
        eval_mtp_scores,
        mtp_topk=mtp_topk,
        rank_alpha=utility_rank_alpha,
        layer_factors=layer_factors,
        ready_factors=ready_factors,
    )
    score_thresholds = _thresholds_from_calibration(
        train_base,
        train_mtp_scores,
        score_tensor=train_mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=gate_max_extra,
        keep_fractions=keep_fractions,
        prefix="score",
    )
    utility_thresholds = _thresholds_from_calibration(
        train_base,
        train_mtp_scores,
        score_tensor=train_utility,
        mtp_topk=mtp_topk,
        max_extra=gate_max_extra,
        keep_fractions=keep_fractions,
        prefix="utility",
    )
    gated_score_tensors = {
        **{name: eval_mtp_scores.to(device) for name in score_thresholds},
        **{name: eval_utility.to(device) for name in utility_thresholds},
    }
    gated_score_thresholds = {**score_thresholds, **utility_thresholds}
    return gated_score_tensors, gated_score_thresholds


def _thresholds_from_calibration(
    base: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    score_tensor: torch.Tensor,
    mtp_topk: int,
    max_extra: int,
    keep_fractions: list[float],
    prefix: str,
) -> dict[str, float]:
    extra = novel_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    scores = score_tensor[extra].float()
    scores = scores[torch.isfinite(scores)]
    thresholds = {}
    for keep_fraction in keep_fractions:
        keep_fraction = min(max(float(keep_fraction), 0.0), 1.0)
        name = f"{prefix}_keep_top_{keep_fraction:.3f}"
        if keep_fraction <= 0.0 or scores.numel() == 0:
            thresholds[name] = float("inf")
        elif keep_fraction >= 1.0:
            thresholds[name] = float(scores.min().item())
        else:
            thresholds[name] = float(torch.quantile(scores, 1.0 - keep_fraction).item())
    return thresholds


def _calibrated_layer_factors(
    base: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
) -> torch.Tensor:
    extra = novel_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    count_by_layer = extra.float().sum(dim=(0, 1, 3)).clamp_min(1.0)
    gain_by_layer = (extra.float() * target_mass).sum(dim=(0, 1, 3)) / count_by_layer
    positive = gain_by_layer[gain_by_layer.gt(0.0)]
    if positive.numel() == 0:
        return torch.ones_like(gain_by_layer)
    return (gain_by_layer / positive.mean().clamp_min(1e-12)).clamp(0.5, 1.5)


def _ready_layer_factors(
    *,
    num_layers: int,
    layer_ms: float,
    sampling_ms: float,
    mtp_delay_ms: float,
    bandwidth_gbps: float,
    expert_bytes: int,
    max_extra: int,
    device: torch.device,
) -> torch.Tensor:
    if max_extra <= 0:
        return torch.ones(num_layers, device=device)
    bytes_per_ms = float(bandwidth_gbps) * 1_000_000_000.0 / 1000.0
    factors = []
    for layer_idx in range(int(num_layers)):
        lead_ms = max(
            0.0,
            float(layer_idx) * float(layer_ms) + float(sampling_ms) - float(mtp_delay_ms),
        )
        fetch_capacity = lead_ms * bytes_per_ms / max(1.0, float(expert_bytes))
        factors.append(min(1.0, fetch_capacity / float(max_extra)))
    return torch.tensor(factors, dtype=torch.float32, device=device)


if __name__ == "__main__":
    main()
