#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation.prefetch_shadow import (  # noqa: E402
    _load_alignment_samples,
    _load_mtp_token_samples,
    _samples_to_dataset,
    _split_positions,
)
from mtp_expert_prefetch.runtime.transition_matrix import (  # noqa: E402
    TransitionMatrixMetadata,
    build_transition_matrix_artifact,
    save_transition_matrix_artifact,
)
from mtp_expert_prefetch.training import train_frequency_scores, train_transition_matrix  # noqa: E402
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path  # noqa: E402


DEFAULT_CONFIG = Path("configs/eval/prefetch_shadow_512sample_mtp_extra.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a calibrated previous-token same-layer transition matrix artifact."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/artifacts/transition_matrix_512sample_calibrated.pt"),
    )
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--router-trace-model-id", default=None)
    parser.add_argument("--prefc-fixed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--freq-prior-blend", type=float, default=0.0)
    parser.add_argument("--smoothing", default="none")
    parser.add_argument("--metadata-json", type=Path, default=None)
    return parser.parse_args()


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    config = load_yaml(args.config)
    merged_manifest = resolve_path(config["merged_manifest"], base_dir=project_root)
    mtp_token_manifest = resolve_path(config["mtp_token_manifest"], base_dir=project_root)
    output_path = resolve_path(args.output, base_dir=project_root)
    metadata_json = (
        resolve_path(args.metadata_json, base_dir=project_root)
        if args.metadata_json is not None
        else output_path.with_suffix(".json")
    )

    future_window = int(config.get("future_window", 1))
    if future_window != 1:
        msg = "transition matrix export currently supports future_window=1."
        raise ValueError(msg)
    num_experts = int(config.get("num_experts", 256))
    alignment_samples = _load_alignment_samples(
        merged_manifest,
        future_window=future_window,
        max_samples=_optional_int(config.get("max_samples")),
    )
    mtp_token_samples = _load_mtp_token_samples(mtp_token_manifest)
    train_positions, heldout_positions = _split_positions(
        len(alignment_samples),
        float(config.get("val_fraction", 0.25)),
    )
    train = _samples_to_dataset(
        alignment_samples,
        mtp_token_samples,
        train_positions,
        num_experts=num_experts,
        max_tokens=_optional_int(config.get("max_tokens")),
    )
    if train is None:
        msg = "No train split was produced for transition matrix export."
        raise RuntimeError(msg)

    transition = train_transition_matrix(train.current_feature, train.target_mass)
    frequency_scores = train_frequency_scores(train.target_mass)
    sample_ids = [int(sample_idx) for sample_idx, _payload in alignment_samples]
    metadata = TransitionMatrixMetadata(
        source_manifest=str(merged_manifest),
        train_sample_positions=[int(item) for item in train_positions],
        heldout_sample_positions=[int(item) for item in heldout_positions],
        train_sample_ids=[sample_ids[position] for position in train_positions],
        heldout_sample_ids=[sample_ids[position] for position in heldout_positions],
        num_layers=int(transition.shape[1]),
        num_experts=int(num_experts),
        delta_values=[1],
        smoothing=str(args.smoothing),
        freq_prior_blend=float(args.freq_prior_blend),
        model_id=args.model_id,
        router_trace_model_id=args.router_trace_model_id,
        prefc_fixed=bool(args.prefc_fixed),
        extra={
            "config_path": str(Path(args.config).expanduser().resolve()),
            "mtp_token_manifest": str(mtp_token_manifest),
            "num_train_token_examples": int(train.target_mass.shape[0]),
            "weight_normalization": "runtime_matrix_topk_renormalizes_previous_topk_weights",
        },
    )
    artifact = build_transition_matrix_artifact(
        transition_matrix=transition,
        frequency_scores=frequency_scores,
        metadata=metadata,
    )
    written = save_transition_matrix_artifact(artifact, output_path)
    metadata_json.parent.mkdir(parents=True, exist_ok=True)
    metadata_json.write_text(
        json.dumps(artifact["metadata"], indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output_path": str(written),
                "metadata_path": str(metadata_json),
                "transition_shape": list(transition.shape),
                "frequency_shape": list(frequency_scores.shape),
                "train_sample_count": len(train_positions),
                "heldout_sample_count": len(heldout_positions),
                "num_train_token_examples": int(train.target_mass.shape[0]),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
