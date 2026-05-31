from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _list_get(values: Any, index: int, default: Any = None) -> Any:
    if isinstance(values, list) and 0 <= index < len(values):
        return values[index]
    return default


def _flatten_record(record: dict[str, Any], *, parent_line: int) -> list[dict[str, Any]]:
    sequences = record.get("sequences")
    if not isinstance(sequences, list) or not sequences:
        return []

    q_lens = record.get("q_lens")
    query_lens = record.get("query_lens", q_lens)
    cache_seqlens = record.get("cache_seqlens")
    valid_counts = record.get("block_table_valid_counts")
    sample_indices = record.get("sample_indices")
    record_ids = record.get("record_ids")
    prompt_lens = record.get("prompt_lens")
    chunk_tokens = int(record.get("chunk_tokens") or 32)
    num_kv_heads = int(record.get("num_kv_heads") or 1)
    out: list[dict[str, Any]] = []

    for sequence_index, sequence in enumerate(sequences):
        if not isinstance(sequence, dict):
            continue
        source_row = int(sequence.get("row", sequence_index))
        q_len = int(_list_get(q_lens, source_row, record.get("q_len") or 1) or 1)
        query_len = int(_list_get(query_lens, source_row, q_len) or q_len)
        cache_seqlen = int(
            sequence.get(
                "cache_seqlen",
                _list_get(cache_seqlens, source_row, 0),
            )
            or 0
        )
        block_ids = [int(block_id) for block_id in sequence.get("block_ids", [])]
        valid_block_count = int(
            sequence.get(
                "valid_block_count",
                _list_get(valid_counts, source_row, len(block_ids)),
            )
            or len(block_ids)
        )
        sample_idx = sequence.get("sample_idx", _list_get(sample_indices, source_row))
        record_id = sequence.get("request_id", _list_get(record_ids, source_row))
        prompt_len = sequence.get("prompt_len", _list_get(prompt_lens, source_row))

        flattened = dict(record)
        flattened["parent_record_idx"] = record.get("record_idx")
        flattened["parent_line"] = int(parent_line)
        flattened["parent_row"] = int(source_row)
        flattened["flattened_sequence_index"] = int(sequence_index)
        flattened["batch_size"] = 1
        flattened["q_len"] = q_len
        flattened["q_lens"] = [q_len]
        flattened["query_lens"] = [query_len]
        flattened["query_start_loc"] = [0, q_len]
        flattened["seq_start_loc"] = [0, q_len]
        flattened["cache_seqlens"] = [cache_seqlen]
        flattened["block_table_valid_counts"] = [valid_block_count]
        flattened["block_tables_shape"] = [1, valid_block_count]
        flattened["block_table_shape"] = [1, valid_block_count]
        flattened["scheduler_active_tokens"] = q_len
        flattened["sample_idx"] = sample_idx
        flattened["sample_indices"] = [sample_idx]
        flattened["record_id"] = record_id
        flattened["record_ids"] = [record_id]
        flattened["prompt_len"] = prompt_len
        flattened["prompt_lens"] = [prompt_len]
        flattened["actual_work_size"] = (
            math.ceil(max(0, cache_seqlen) / max(1, chunk_tokens))
            * max(1, num_kv_heads)
            * max(1, q_len)
        )

        flattened_sequence = dict(sequence)
        flattened_sequence["row"] = 0
        flattened_sequence["block_ids"] = block_ids
        flattened_sequence["valid_block_count"] = valid_block_count
        flattened_sequence["cache_seqlen"] = cache_seqlen
        flattened_sequence["sample_idx"] = sample_idx
        flattened_sequence["request_id"] = record_id
        flattened_sequence["seq_id"] = sequence.get("seq_id", record_id)
        flattened_sequence["prompt_len"] = prompt_len
        flattened["sequences"] = [flattened_sequence]
        flattened["trace_id"] = (
            f"{record.get('trace_id', record.get('record_idx', parent_line))}"
            f"_row{source_row}"
        )
        out.append(flattened)
    return out


def flatten_file(input_path: Path, output_path: Path) -> dict[str, int | str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = 0
    flattened_records = 0
    with input_path.open("r", encoding="utf-8") as src, output_path.open(
        "w", encoding="utf-8"
    ) as dst:
        for line_no, line in enumerate(src, start=1):
            if not line.strip():
                continue
            records += 1
            for flattened in _flatten_record(json.loads(line), parent_line=line_no):
                dst.write(json.dumps(flattened, sort_keys=True) + "\n")
                flattened_records += 1
    return {
        "input": str(input_path),
        "output": str(output_path),
        "records": records,
        "flattened_records": flattened_records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Flatten batched vLLM block-table v2 JSONL into one sequence per row."
    )
    parser.add_argument("--input", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = []
    for input_path in args.input:
        output_path = args.output_dir / input_path.name.replace(".jsonl", ".flat.jsonl")
        rows.append(flatten_file(input_path, output_path))
    summary = {
        "schema_version": 1,
        "files": rows,
        "total_records": sum(int(row["records"]) for row in rows),
        "total_flattened_records": sum(int(row["flattened_records"]) for row in rows),
    }
    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

