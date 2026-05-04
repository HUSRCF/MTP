from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from mtp_expert_prefetch.tracing.router_trace_bridge import load_trace_payload


@dataclass(frozen=True)
class MergeResult:
    payload: dict[str, Any]
    num_tokens: int
    mtp_num_tokens: int
    target_num_tokens: int


def read_trace_manifest(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path).expanduser().resolve()
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            record["_manifest_dir"] = str(path.parent)
            records.append(record)
    return records


def manifest_record_path(record: dict[str, Any]) -> Path:
    manifest_dir = Path(record["_manifest_dir"])
    return (manifest_dir / record["path"]).resolve()


def merge_trace_manifests(
    *,
    mtp_manifest: str | Path,
    target_manifest: str | Path,
    output_dir: str | Path,
    token_policy: str = "prefix",
    max_samples: int | None = None,
) -> Path:
    mtp_records = {
        int(record["sample_idx"]): record
        for record in read_trace_manifest(mtp_manifest)
    }
    target_records = {
        int(record["sample_idx"]): record for record in read_trace_manifest(target_manifest)
    }
    sample_ids = sorted(set(mtp_records) & set(target_records))
    if max_samples is not None:
        sample_ids = sample_ids[:max_samples]
    if not sample_ids:
        msg = "No overlapping sample_idx values between MTP and target manifests."
        raise RuntimeError(msg)

    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_manifest = output_dir / "manifest.jsonl"
    with output_manifest.open("w", encoding="utf-8") as manifest:
        for output_idx, sample_idx in enumerate(sample_ids):
            mtp_path = manifest_record_path(mtp_records[sample_idx])
            target_path = manifest_record_path(target_records[sample_idx])
            result = merge_mtp_source_with_router_targets(
                load_trace_payload(mtp_path),
                load_trace_payload(target_path),
                token_policy=token_policy,
            )
            sample_file = output_dir / f"sample_{output_idx:06d}.pt"
            torch.save(result.payload, sample_file)
            manifest.write(
                json.dumps(
                    {
                        "sample_idx": output_idx,
                        "source_sample_idx": sample_idx,
                        "path": sample_file.name,
                        "num_tokens": result.num_tokens,
                        "mtp_num_tokens": result.mtp_num_tokens,
                        "target_num_tokens": result.target_num_tokens,
                        "num_router_modules": len(result.payload["router_topk"]),
                        "has_native_mtp_router": True,
                        "has_vllm_routed_experts": "vllm_routed_experts" in result.payload,
                        "mtp_source_path": str(mtp_path),
                        "target_source_path": str(target_path),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return output_manifest


def merge_mtp_source_with_router_targets(
    mtp_payload: dict[str, Any],
    target_payload: dict[str, Any],
    *,
    token_policy: str = "prefix",
) -> MergeResult:
    _require_key(mtp_payload, "native_mtp_router_topk")
    _require_key(mtp_payload, "native_mtp_router_weights")
    _require_key(target_payload, "router_topk")

    mtp_input_ids = _as_2d_input_ids(mtp_payload["input_ids"])
    target_input_ids = _as_2d_input_ids(target_payload["input_ids"])
    common_tokens = _validate_and_get_common_token_count(
        mtp_input_ids,
        target_input_ids,
        token_policy=token_policy,
    )

    merged: dict[str, Any] = {
        "backend": "merged_autoround_mtp__vllm_router",
        "record": target_payload.get("record", mtp_payload.get("record", {})),
        "input_ids": target_input_ids[:, :common_tokens].contiguous().to(torch.int32),
        "native_mtp_router_topk": _truncate_token_axis(
            mtp_payload["native_mtp_router_topk"],
            common_tokens,
        ).to(torch.int16),
        "native_mtp_router_weights": _truncate_token_axis(
            mtp_payload["native_mtp_router_weights"],
            common_tokens,
        ).to(torch.float32),
        "router_topk": _truncate_router_dict(target_payload["router_topk"], common_tokens),
        "merge_meta": {
            "token_policy": token_policy,
            "num_tokens": common_tokens,
            "mtp_num_tokens": int(mtp_input_ids.shape[-1]),
            "target_num_tokens": int(target_input_ids.shape[-1]),
            "mtp_backend": mtp_payload.get("backend", "transformers_autoround"),
            "target_backend": target_payload.get("backend", "unknown"),
        },
    }
    if isinstance(target_payload.get("router_weights"), dict):
        merged["router_weights"] = _truncate_router_dict(
            target_payload["router_weights"],
            common_tokens,
        )
    if "router_call_meta" in target_payload:
        merged["router_call_meta"] = target_payload["router_call_meta"]
    if "vllm_routed_experts" in target_payload:
        merged["vllm_routed_experts"] = _truncate_token_axis(
            target_payload["vllm_routed_experts"],
            common_tokens,
        ).to(torch.int16)
        merged["vllm_routed_experts_shape"] = list(merged["vllm_routed_experts"].shape)
    if "native_mtp_router_logits_shape" in mtp_payload:
        merged["native_mtp_router_logits_shape"] = mtp_payload["native_mtp_router_logits_shape"]
    if "native_mtp_moe_inputs_shape" in mtp_payload:
        merged["native_mtp_moe_inputs_shape"] = mtp_payload["native_mtp_moe_inputs_shape"]

    return MergeResult(
        payload=merged,
        num_tokens=common_tokens,
        mtp_num_tokens=int(mtp_input_ids.shape[-1]),
        target_num_tokens=int(target_input_ids.shape[-1]),
    )


def _require_key(payload: dict[str, Any], key: str) -> None:
    if key not in payload:
        msg = f"Trace payload is missing required key `{key}`."
        raise KeyError(msg)


def _as_2d_input_ids(value: Any) -> torch.Tensor:
    tensor = torch.as_tensor(value, dtype=torch.long)
    if tensor.ndim == 1:
        return tensor[None, :]
    if tensor.ndim == 2:
        return tensor
    msg = f"Expected input_ids with 1 or 2 dims, got {tuple(tensor.shape)}"
    raise ValueError(msg)


def _validate_and_get_common_token_count(
    mtp_input_ids: torch.Tensor,
    target_input_ids: torch.Tensor,
    *,
    token_policy: str,
) -> int:
    if int(mtp_input_ids.shape[0]) != int(target_input_ids.shape[0]):
        msg = (
            "MTP and target traces must have the same batch size, got "
            f"{tuple(mtp_input_ids.shape)} and {tuple(target_input_ids.shape)}."
        )
        raise ValueError(msg)

    normalized = token_policy.lower()
    if normalized == "strict":
        if not torch.equal(mtp_input_ids, target_input_ids):
            msg = "MTP and target input_ids are not exactly equal under token_policy='strict'."
            raise ValueError(msg)
        return int(mtp_input_ids.shape[-1])
    if normalized != "prefix":
        msg = f"Unsupported token_policy {token_policy!r}; expected 'prefix' or 'strict'."
        raise ValueError(msg)

    common_tokens = min(int(mtp_input_ids.shape[-1]), int(target_input_ids.shape[-1]))
    if common_tokens <= 0:
        msg = "Cannot merge empty token sequences."
        raise ValueError(msg)
    if not torch.equal(mtp_input_ids[:, :common_tokens], target_input_ids[:, :common_tokens]):
        msg = "MTP and target input_ids do not share a common prefix."
        raise ValueError(msg)
    return common_tokens


def _truncate_token_axis(value: Any, num_tokens: int) -> torch.Tensor:
    tensor = torch.as_tensor(value).detach().cpu()
    if tensor.ndim == 3:
        return tensor[:, :num_tokens, :].contiguous()
    if tensor.ndim == 2:
        return tensor[:num_tokens, :].contiguous()
    if tensor.ndim == 1:
        return tensor[:num_tokens].contiguous()
    msg = f"Expected token tensor with 1-3 dims, got {tuple(tensor.shape)}"
    raise ValueError(msg)


def _truncate_router_dict(router_dict: dict[str, Any], num_tokens: int) -> dict[str, list[Any]]:
    truncated: dict[str, list[Any]] = {}
    for module_name, calls in router_dict.items():
        if not isinstance(calls, list):
            msg = f"Router entry {module_name!r} is not a list."
            raise TypeError(msg)
        truncated[module_name] = [
            _truncate_token_axis(call, num_tokens).tolist()
            for call in calls
        ]
    return truncated
