#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation.prefetch_shadow import (  # noqa: E402
    _load_alignment_samples,
    _load_mtp_token_samples,
    _samples_to_dataset,
    mask_metrics,
    topk_mask,
)
from mtp_expert_prefetch.runtime import OnlineShadowLogger, RuntimeShadowController  # noqa: E402
from mtp_expert_prefetch.runtime.shadow_log import (  # noqa: E402
    aggregate_shadow_events,
    read_shadow_jsonl,
)
from mtp_expert_prefetch.runtime.transition_matrix import load_transition_matrix_artifact  # noqa: E402
from mtp_expert_prefetch.tracing.router_trace_bridge import load_trace_payload  # noqa: E402
from mtp_expert_prefetch.tracing.vllm_router_trace import VllmRouterRecorder  # noqa: E402
from mtp_expert_prefetch.training import apply_transition_matrix  # noqa: E402
from mtp_expert_prefetch.training.alignment_merge import (  # noqa: E402
    manifest_record_path,
    read_trace_manifest,
)
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path  # noqa: E402


LAYER_RE = re.compile(r"(?:^|\.)layers\.(\d+)\.mlp\.gate$")
DEFAULT_CONFIG = Path("configs/eval/prefetch_shadow_512sample_mtp_extra.yaml")
DEFAULT_ARTIFACT = Path("outputs/artifacts/transition_matrix_512sample_calibrated.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay held-out router traces through the online VllmRouterRecorder "
            "matrix_topk shadow path and compare against offline transition@K."
        )
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument("--transition-artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("outputs/reports/matrix_transition_shadow_replay/heldout_shadow.jsonl"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("outputs/reports/matrix_transition_shadow_replay/summary.json"),
    )
    parser.add_argument("--transition-topk", type=int, default=32)
    parser.add_argument("--request-id", default="matrix_transition_replay")
    parser.add_argument("--max-samples", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    config = load_yaml(args.config)
    merged_manifest = resolve_path(config["merged_manifest"], base_dir=project_root)
    mtp_token_manifest = resolve_path(config["mtp_token_manifest"], base_dir=project_root)
    transition_artifact_path = resolve_path(args.transition_artifact, base_dir=project_root)
    output_jsonl = resolve_path(args.output_jsonl, base_dir=project_root)
    summary_output = resolve_path(args.summary_output, base_dir=project_root)
    artifact = load_transition_matrix_artifact(transition_artifact_path)
    transition = torch.as_tensor(artifact["transition_matrix"], dtype=torch.float32)
    metadata = dict(artifact.get("metadata", {}))
    heldout_positions = [int(item) for item in metadata.get("heldout_sample_positions", [])]
    if args.max_samples is not None:
        heldout_positions = heldout_positions[: int(args.max_samples)]
    if not heldout_positions:
        msg = "Transition artifact has no heldout_sample_positions."
        raise RuntimeError(msg)

    records = read_trace_manifest(merged_manifest)
    selected_records = [records[position] for position in heldout_positions]
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    if output_jsonl.exists():
        output_jsonl.unlink()
    with RuntimeShadowController(
        OnlineShadowLogger(output_jsonl, flush_every=1),
        max_pending=200_000,
    ) as controller:
        for record in selected_records:
            payload = load_trace_payload(manifest_record_path(record))
            recorder = VllmRouterRecorder(
                top_k=_infer_topk(payload),
                shadow_outcome_sink=controller,
                shadow_emit_transition_summary=True,
                shadow_num_experts=int(metadata.get("num_experts", transition.shape[-1])),
                shadow_transition_topk_count=int(args.transition_topk),
                shadow_transition_summary_mode="matrix_topk",
                shadow_transition_matrix=transition,
                request_id=str(args.request_id),
                sequence_id=int(record.get("sample_idx", 0)),
                token_offset=0,
            )
            for layer_id, ids, weights in _iter_layer_topk(payload):
                recorder.record_topk(
                    layer_id=layer_id,
                    topk_ids=ids,
                    topk_weights=weights,
                )
        controller.flush_pending_as_timeouts()

    rows = read_shadow_jsonl(output_jsonl)
    online_all = aggregate_shadow_events(rows)
    online_joined = _joined_metrics(rows)
    offline = _offline_transition_metrics(
        merged_manifest=merged_manifest,
        mtp_token_manifest=mtp_token_manifest,
        heldout_positions=heldout_positions,
        transition=transition,
        num_experts=int(metadata.get("num_experts", transition.shape[-1])),
        transition_topk=int(args.transition_topk),
        config=config,
    )
    checks = _diff_metrics(online_joined, offline)
    summary = {
        "ok": bool(all(item["abs_diff"] <= item["tolerance"] for item in checks)),
        "config": str(Path(args.config).expanduser().resolve()),
        "merged_manifest": str(merged_manifest),
        "transition_artifact": str(transition_artifact_path),
        "output_jsonl": str(output_jsonl),
        "transition_topk": int(args.transition_topk),
        "heldout_positions": heldout_positions,
        "heldout_sample_count": len(heldout_positions),
        "online_all": online_all,
        "online_joined": online_joined,
        "offline_transition": offline,
        "checks": checks,
        "notes": {
            "online_all_includes_token0_outcome_only": True,
            "online_joined_excludes_token0_outcome_only": True,
            "comparison_target": "online_joined vs offline transition@K on same heldout split",
        },
    }
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


def _infer_topk(payload: dict[str, Any]) -> int:
    router_topk = payload.get("router_topk")
    if not isinstance(router_topk, dict) or not router_topk:
        msg = "Trace payload has no router_topk."
        raise KeyError(msg)
    first = torch.as_tensor(next(iter(router_topk.values()))[0])
    return int(first.shape[-1])


def _iter_layer_topk(payload: dict[str, Any]) -> list[tuple[int, torch.Tensor, torch.Tensor]]:
    router_topk = payload.get("router_topk")
    if not isinstance(router_topk, dict) or not router_topk:
        msg = "Trace payload has no router_topk."
        raise KeyError(msg)
    router_weights = payload.get("router_weights")
    result = []
    for module_name in sorted(router_topk, key=_layer_sort_key):
        layer_id = _parse_layer_id(module_name)
        ids = _first_call_2d(router_topk[module_name], dtype=torch.long)
        if isinstance(router_weights, dict) and module_name in router_weights:
            weights = _first_call_2d(router_weights[module_name], dtype=torch.float32)
        else:
            weights = torch.full(ids.shape, 1.0 / max(1, int(ids.shape[-1])), dtype=torch.float32)
        result.append((layer_id, ids, weights))
    return result


def _first_call_2d(calls: Any, *, dtype: torch.dtype) -> torch.Tensor:
    if not isinstance(calls, list) or not calls:
        msg = "Router entry is empty or not a list."
        raise ValueError(msg)
    tensor = torch.as_tensor(calls[0], dtype=dtype)
    if tensor.ndim == 3 and int(tensor.shape[0]) == 1:
        tensor = tensor[0]
    if tensor.ndim != 2:
        msg = f"Expected router call tensor [tokens, topk], got {tuple(tensor.shape)}"
        raise ValueError(msg)
    return tensor.contiguous()


def _layer_sort_key(module_name: str) -> int:
    return _parse_layer_id(module_name)


def _parse_layer_id(module_name: str) -> int:
    match = LAYER_RE.search(module_name)
    if match is None:
        fallback = re.search(r"layers\.(\d+)\.", module_name)
        if fallback is None:
            msg = f"Could not parse layer id from {module_name!r}"
            raise ValueError(msg)
        return int(fallback.group(1))
    return int(match.group(1))


def _joined_metrics(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    joined = [
        row for row in rows if row.get("event_type") == "outcome" and row.get("join_status") == "joined"
    ]
    if not joined:
        msg = "No joined outcome rows found."
        raise RuntimeError(msg)
    count = len(joined)
    return {
        "outcome_count": count,
        "covered_mass_mean": sum(float(row.get("covered_mass", 0.0)) for row in joined) / count,
        "miss_mass_mean": sum(float(row.get("miss_mass", 0.0)) for row in joined) / count,
        "top1_ready_rate": sum(1.0 if row.get("top1_ready") else 0.0 for row in joined) / count,
        "weighted_top1_miss_mean": sum(
            float(row.get("weighted_top1_miss", 0.0)) for row in joined
        )
        / count,
    }


def _offline_transition_metrics(
    *,
    merged_manifest: Path,
    mtp_token_manifest: Path,
    heldout_positions: list[int],
    transition: torch.Tensor,
    num_experts: int,
    transition_topk: int,
    config: dict[str, Any],
) -> dict[str, float | int]:
    alignment_samples = _load_alignment_samples(
        merged_manifest,
        future_window=int(config.get("future_window", 1)),
        max_samples=None,
    )
    mtp_token_samples = _load_mtp_token_samples(mtp_token_manifest)
    dataset = _samples_to_dataset(
        alignment_samples,
        mtp_token_samples,
        heldout_positions,
        num_experts=int(num_experts),
        max_tokens=int(config["max_tokens"]) if config.get("max_tokens") is not None else None,
    )
    if dataset is None:
        msg = "No offline heldout dataset was built."
        raise RuntimeError(msg)
    scores = apply_transition_matrix(dataset.current_feature, transition)
    mask = topk_mask(scores, k=int(transition_topk))
    metrics = mask_metrics(mask, dataset.target_mass)
    return {
        "outcome_count": int(dataset.target_mass.shape[0] * dataset.target_mass.shape[1] * dataset.target_mass.shape[2]),
        "covered_mass_mean": float(metrics["pool_mass_coverage"]),
        "miss_mass_mean": float(1.0 - metrics["pool_mass_coverage"]),
        "top1_ready_rate": float(metrics["top1_hit_rate"]),
        "weighted_top1_miss_mean": float(metrics["weighted_top1_miss"]),
    }


def _diff_metrics(
    online: dict[str, float | int],
    offline: dict[str, float | int],
) -> list[dict[str, float | str | bool]]:
    checks = []
    for key, tolerance in {
        "outcome_count": 0.0,
        "covered_mass_mean": 5e-6,
        "miss_mass_mean": 5e-6,
        "top1_ready_rate": 5e-6,
        "weighted_top1_miss_mean": 5e-6,
    }.items():
        online_value = float(online[key])
        offline_value = float(offline[key])
        diff = abs(online_value - offline_value)
        checks.append(
            {
                "metric": key,
                "online_value": online_value,
                "offline_value": offline_value,
                "abs_diff": diff,
                "tolerance": float(tolerance),
                "passed": bool(diff <= float(tolerance)),
            }
        )
    return checks


if __name__ == "__main__":
    main()
