from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch
import yaml


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _extract_text(record: dict[str, Any]) -> str:
    for key in ("text", "prompt", "inputs", "targets"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    fields = []
    for key in ("instruction", "context", "response"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            fields.append(value.strip())
    if fields:
        return "\n\n".join(fields)
    raise KeyError(f"record has no usable text field: {sorted(record)}")


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"expected mapping in {path}")
    return payload


def _dump_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _make_exact_length_ids(
    *,
    tokenizer: Any,
    base_text: str,
    prompt_length: int,
    length: int,
    sample_idx: int,
) -> tuple[list[int], str]:
    header = (
        f"Trace sample {sample_idx}; target prompt tokens {prompt_length}; "
        f"length bucket {length}.\n\n"
    )
    filler = (
        "\n\nContinue with detailed reasoning, constraints, examples, and "
        "edge cases so the prompt has enough context for decode metadata tracing."
    )
    text = header + base_text
    # Tokenize a few times at most.  The generated data is for trace-only
    # workload geometry, so repeated source text is acceptable and keeps each
    # bucket prompt-diverse while guaranteeing the requested token length.
    for _ in range(8):
        encoded = tokenizer(
            text,
            return_tensors=None,
            truncation=True,
            max_length=prompt_length,
        )
        input_ids = [int(token) for token in encoded["input_ids"]]
        if len(input_ids) >= prompt_length:
            return input_ids[:prompt_length], text
        text = text + filler + "\n\n" + base_text
    encoded = tokenizer(
        text,
        return_tensors=None,
        truncation=True,
        max_length=prompt_length,
    )
    input_ids = [int(token) for token in encoded["input_ids"]]
    if not input_ids:
        raise ValueError("tokenizer returned no input ids")
    while len(input_ids) < prompt_length:
        input_ids.append(int(input_ids[-1]))
    return input_ids[:prompt_length], text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-trace-config",
        type=Path,
        default=Path(
            "configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_base.yaml"
        ),
    )
    parser.add_argument(
        "--base-model-config",
        type=Path,
        default=Path("configs/model/qwen3_6_35b_a3b_awq_4bit.yaml"),
    )
    parser.add_argument(
        "--source-jsonl",
        type=Path,
        default=Path("data/raw/external_prompt_gate_dolly_128.jsonl"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("traceData/vllm_decode_block_table_v2"),
    )
    parser.add_argument("--lengths", nargs="+", type=int, default=[64, 128, 256, 512, 1024, 2048])
    parser.add_argument("--samples-per-length", type=int, default=32)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--gpu", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.50)
    parser.add_argument("--max-num-seqs", type=int, default=1)
    parser.add_argument("--engine-chunk-size", type=int, default=1)
    parser.add_argument("--chunk-tokens", type=int, default=32)
    parser.add_argument("--max-trace-rows", type=int, default=10000)
    parser.add_argument("--schema-version", type=int, default=2)
    parser.add_argument("--include-block-ids", action="store_true", default=True)
    parser.add_argument("--no-include-block-ids", dest="include_block_ids", action="store_false")
    parser.add_argument("--include-kv-cache-layout", action="store_true", default=True)
    parser.add_argument(
        "--no-include-kv-cache-layout",
        dest="include_kv_cache_layout",
        action="store_false",
    )
    parser.add_argument("--capture-metadata-builder", action="store_true", default=True)
    parser.add_argument(
        "--no-capture-metadata-builder",
        dest="capture_metadata_builder",
        action="store_false",
    )
    parser.add_argument("--capture-attention-forward", action="store_true", default=True)
    parser.add_argument(
        "--no-capture-attention-forward",
        dest="capture_attention_forward",
        action="store_false",
    )
    parser.add_argument("--capture-chunked-prefill-paged-decode", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    base_trace = _load_yaml(root / args.base_trace_config)
    base_model = _load_yaml(root / args.base_model_config)
    source_records = _load_jsonl(root / args.source_jsonl)
    if not source_records:
        raise RuntimeError(f"no source records: {args.source_jsonl}")

    from transformers import AutoTokenizer

    model_id = root / str(base_model["model_id"])
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_id),
        trust_remote_code=bool(base_model.get("trust_remote_code", True)),
        local_files_only=bool(base_model.get("local_files_only", True)),
    )

    output_root = root / args.output_root
    data_dir = output_root / "data"
    config_dir = output_root / "configs"
    token_dir = output_root / "token_sources"
    trace_dir = output_root / "jsonl"
    run_dir = output_root / "runs"
    manifest_rows: list[dict[str, Any]] = []

    for length in args.lengths:
        prompt_length = int(length)
        run_id = f"dolly_plen{prompt_length}_gen{int(args.max_tokens)}_gpu{int(args.gpu)}"
        data_jsonl = data_dir / f"{run_id}.jsonl"
        data_yaml = config_dir / f"data_{run_id}.yaml"
        model_yaml = config_dir / f"model_{run_id}.yaml"
        trace_yaml = config_dir / f"trace_{run_id}.yaml"
        token_manifest = token_dir / run_id / "manifest.jsonl"
        trace_jsonl = trace_dir / f"{run_id}.jsonl"
        run_output_dir = run_dir / run_id

        token_manifest.parent.mkdir(parents=True, exist_ok=True)
        data_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with data_jsonl.open("w", encoding="utf-8") as data_handle, token_manifest.open(
            "w",
            encoding="utf-8",
        ) as token_handle:
            for sample_idx in range(int(args.samples_per_length)):
                source_index = (sample_idx * 17 + prompt_length) % len(source_records)
                source = source_records[source_index]
                base_text = _extract_text(source)
                input_ids, expanded_text = _make_exact_length_ids(
                    tokenizer=tokenizer,
                    base_text=base_text,
                    prompt_length=prompt_length,
                    length=prompt_length,
                    sample_idx=sample_idx,
                )
                sample_path = token_manifest.parent / f"sample_{sample_idx:06d}.pt"
                torch.save({"input_ids": torch.tensor(input_ids, dtype=torch.long)}, sample_path)
                data_handle.write(
                    json.dumps(
                        {
                            "id": f"{run_id}_{sample_idx:06d}",
                            "text": expanded_text[:4096],
                            "source_index": int(source_index),
                            "target_prompt_tokens": int(prompt_length),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
                token_handle.write(
                    json.dumps(
                        {
                            "sample_idx": int(sample_idx),
                            "path": sample_path.name,
                            "target_prompt_tokens": int(prompt_length),
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )

        data_payload = {
            "name": f"vllm_decode_workload_{run_id}",
            "source": "materialized_jsonl",
            "material_path": str(data_jsonl.relative_to(root)),
            "max_samples": int(args.samples_per_length),
        }
        _dump_yaml(data_yaml, data_payload)

        model_payload = dict(base_model)
        model_payload["vllm"] = dict(base_model.get("vllm", {}))
        model_payload["vllm"]["max_model_len"] = int(prompt_length + int(args.max_tokens))
        model_payload["vllm"]["max_tokens"] = int(args.max_tokens)
        model_payload["vllm"]["max_num_seqs"] = int(args.max_num_seqs)
        model_payload["vllm"]["engine_chunk_size"] = int(args.engine_chunk_size)
        model_payload["vllm"]["gpu_memory_utilization"] = float(
            args.gpu_memory_utilization
        )
        model_payload["vllm"]["enable_return_routed_experts"] = True
        model_payload["vllm"]["disable_v1_multiprocessing_for_recorder"] = True
        _dump_yaml(model_yaml, model_payload)

        trace_payload = dict(base_trace)
        trace_payload["model"] = str(model_yaml.relative_to(root))
        trace_payload["data"] = str(data_yaml.relative_to(root))
        trace_payload["output_dir"] = str(run_output_dir.relative_to(root))
        trace_options = dict(base_trace.get("trace", {}))
        trace_options.update(
            {
                "capture_router_topk": False,
                "capture_router_scores": False,
                "use_router_logits_recorder": False,
                "split_id": run_id,
                "expected_sample_start": 0,
                "expected_sample_end": int(args.samples_per_length) - 1,
                "start_sample": 0,
                "max_samples": int(args.samples_per_length),
                "max_length": int(prompt_length + int(args.max_tokens)),
                "max_tokens": int(args.max_tokens),
                "token_source_manifest": str(token_manifest.relative_to(root)),
                "decode_workload_trace": {
                    "enabled": True,
                    "output_path": str(trace_jsonl.relative_to(root)),
                    "overwrite": True,
                    "run_id": run_id,
                    "schema_version": int(args.schema_version),
                    "phase": "decode",
                    "chunk_tokens": int(args.chunk_tokens),
                    "head_mapping": "kv",
                    "max_rows": int(args.max_trace_rows),
                    "sample_period": 1,
                    "flush_every": 256,
                    "include_block_ids": bool(args.include_block_ids),
                    "include_kv_cache_layout": bool(args.include_kv_cache_layout),
                    "capture_metadata_builder": bool(args.capture_metadata_builder),
                    "capture_attention_forward": bool(args.capture_attention_forward),
                    "capture_chunked_prefill_paged_decode": bool(
                        args.capture_chunked_prefill_paged_decode
                    ),
                },
                "runtime_shadow": {"enabled": False},
            }
        )
        trace_payload["trace"] = trace_options
        _dump_yaml(trace_yaml, trace_payload)

        manifest_rows.append(
            {
                "run_id": run_id,
                "prompt_length": int(prompt_length),
                "samples": int(args.samples_per_length),
                "max_tokens": int(args.max_tokens),
                "config": str(trace_yaml.relative_to(root)),
                "decode_trace": str(trace_jsonl.relative_to(root)),
                "output_dir": str(run_output_dir.relative_to(root)),
                "token_source_manifest": str(token_manifest.relative_to(root)),
            }
        )

    manifest_path = output_root / "length_sweep_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "coverage": "vllm_decode_attention_workload_metadata",
                "lengths": [int(length) for length in args.lengths],
                "samples_per_length": int(args.samples_per_length),
                "runs": manifest_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
