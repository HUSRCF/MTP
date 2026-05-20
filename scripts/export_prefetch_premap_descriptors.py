#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation.prefetch_shadow import (  # noqa: E402
    _apply_mtp_token_frequency_table,
    _load_alignment_samples,
    _load_mtp_token_samples,
    _samples_to_dataset,
    _split_positions,
)
from mtp_expert_prefetch.runtime import (  # noqa: E402
    ExpertPrefetchDescriptor,
    OnlineShadowLogger,
    ShadowEventId,
    build_premap_descriptors,
    descriptor_summary,
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
        description="Export offline pre-map expert descriptors from a shadow policy config."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/descriptors.jsonl"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/descriptors_summary.json"),
    )
    parser.add_argument("--max-extra", type=int, default=None)
    parser.add_argument("--score-reduce", choices=["max", "mean", "sum"], default="max")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--shadow-jsonl",
        type=Path,
        default=None,
        help=(
            "Optional output path for premap_summary shadow rows. Rows are "
            "grouped by sample/layer and audit descriptor/address prep only."
        ),
    )
    parser.add_argument(
        "--shadow-summary-output",
        type=Path,
        default=None,
        help="Optional JSON aggregate for --shadow-jsonl.",
    )
    parser.add_argument(
        "--premap-descriptor-bytes",
        type=int,
        default=4_096,
        help=(
            "Bytes charged to one premap descriptor/address record in shadow "
            "audit. This is not full expert payload bytes."
        ),
    )
    parser.add_argument(
        "--expert-bytes",
        type=int,
        default=1_650_000,
        help=(
            "Approximate bytes for one routed expert's quantized weights. "
            "Default is a rough Qwen3.6 A3B int4 expert payload including metadata."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    config = load_yaml(args.config)
    merged_manifest = resolve_path(config["merged_manifest"], base_dir=project_root)
    mtp_token_manifest = resolve_path(config["mtp_token_manifest"], base_dir=project_root)
    output_jsonl = resolve_path(args.output_jsonl, base_dir=project_root)
    summary_output = resolve_path(args.summary_output, base_dir=project_root)
    shadow_jsonl = (
        resolve_path(args.shadow_jsonl, base_dir=project_root)
        if args.shadow_jsonl is not None
        else None
    )
    shadow_summary_output = (
        resolve_path(args.shadow_summary_output, base_dir=project_root)
        if args.shadow_summary_output is not None
        else None
    )

    future_window = int(config.get("future_window", 1))
    max_samples = int(config["max_samples"]) if config.get("max_samples") is not None else None
    max_tokens = int(config["max_tokens"]) if config.get("max_tokens") is not None else None
    transition_topk = int(config.get("transition_topk", 32))
    mtp_topk = int(config.get("mtp_topk", 64))
    max_extra = int(
        args.max_extra
        if args.max_extra is not None
        else config.get("high_budget_max_extra", 8)
    )

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
        msg = "Empty train/eval split; cannot export descriptors."
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

    descriptors = build_premap_descriptors(
        transition_scores,
        mtp_scores,
        eval_data.token_sample_indices,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
        reduce=args.score_reduce,
    )
    if args.limit is not None:
        descriptors_to_write = descriptors[: int(args.limit)]
    else:
        descriptors_to_write = descriptors

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for descriptor in descriptors_to_write:
            handle.write(json.dumps(descriptor.as_dict(), ensure_ascii=False) + "\n")

    summary = descriptor_summary(descriptors, expert_bytes=int(args.expert_bytes))
    summary.update(
        {
            "ok": True,
            "config": str(resolve_path(args.config, base_dir=project_root)),
            "merged_manifest": str(merged_manifest),
            "mtp_token_manifest": str(mtp_token_manifest),
            "output_jsonl": str(output_jsonl),
            "summary_output": str(summary_output),
            "written_descriptors": len(descriptors_to_write),
            "max_extra": max_extra,
            "transition_topk": transition_topk,
            "mtp_topk": mtp_topk,
            "score_reduce": args.score_reduce,
            "eval_split": "val" if val is not None else "train",
            "num_eval_token_examples": int(eval_data.target_mass.shape[0]),
        }
    )
    shadow_aggregate = None
    if shadow_jsonl is not None:
        shadow_aggregate = _write_premap_shadow_jsonl(
            descriptors=descriptors_to_write,
            output=shadow_jsonl,
            descriptor_bytes=int(args.premap_descriptor_bytes),
            premap_policy="premap_only",
            premap_source="export_prefetch_premap_descriptors",
        )
        summary["premap_shadow_jsonl"] = str(shadow_jsonl)
        summary["premap_shadow_summary"] = shadow_aggregate
        if shadow_summary_output is not None:
            shadow_summary_output.parent.mkdir(parents=True, exist_ok=True)
            shadow_summary_output.write_text(
                json.dumps(shadow_aggregate, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            summary["premap_shadow_summary_output"] = str(shadow_summary_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


def _write_premap_shadow_jsonl(
    *,
    descriptors: list[ExpertPrefetchDescriptor],
    output: Path,
    descriptor_bytes: int,
    premap_policy: str,
    premap_source: str,
) -> dict[str, object]:
    grouped: dict[tuple[int, int], list[ExpertPrefetchDescriptor]] = {}
    for descriptor in descriptors:
        sample_idx = int(getattr(descriptor, "sample_idx"))
        layer_idx = int(getattr(descriptor, "layer_idx"))
        grouped.setdefault((sample_idx, layer_idx), []).append(descriptor)
    with OnlineShadowLogger(output, flush_every=256, writer_mode="jsonl_batched") as logger:
        for (sample_idx, layer_idx), group in sorted(grouped.items()):
            logger.write_premap_summary_from_descriptors(
                event_id=ShadowEventId(
                    "premap_export",
                    sequence_id=int(sample_idx),
                    token_index=-1,
                    layer=int(layer_idx),
                ),
                descriptors=group,
                premap_policy=premap_policy,
                premap_source=premap_source,
                descriptor_bytes=descriptor_bytes,
            )
        return logger.aggregate()


if __name__ == "__main__":
    main()
