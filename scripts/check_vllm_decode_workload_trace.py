from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "schema_version",
    "trace_id",
    "phase",
    "capture_point",
    "batch_size",
    "q_len",
    "num_q_heads",
    "num_kv_heads",
    "head_dim",
    "dtype",
    "kv_dtype",
    "page_block_size",
    "cache_seqlens",
    "block_table_valid_counts",
    "block_table_shape",
    "sliding_window",
    "scheduler_active_tokens",
)
V2_REQUIRED_FIELDS = (
    "schema_version",
    "trace_type",
    "capture_point",
    "record_idx",
    "phase",
    "decode_step",
    "batch_size",
    "cache_seqlens",
    "q_lens",
    "query_start_loc",
    "seq_start_loc",
    "num_q_heads",
    "num_kv_heads",
    "head_dim",
    "kv_dtype",
    "block_size_tokens",
    "block_tables_shape",
    "sequences",
)


def _percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(math.ceil(q * len(ordered)) - 1)))
    return int(ordered[index])


def _as_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{field} must be an integer, got bool")
    return int(value)


def _parse_int(
    value: Any,
    field: str,
    *,
    line_no: int,
    errors: list[str],
    minimum: int | None = None,
    positive: bool = False,
) -> int | None:
    try:
        parsed = _as_int(value, field)
    except Exception as exc:
        errors.append(f"line {line_no}: {field} parse failed: {exc}")
        return None
    if positive and parsed <= 0:
        errors.append(f"line {line_no}: {field} must be positive")
    if minimum is not None and parsed < minimum:
        errors.append(f"line {line_no}: {field} must be >= {minimum}")
    return parsed


def _parse_int_list(
    value: Any,
    field: str,
    *,
    line_no: int,
    errors: list[str],
    expected_len: int | None = None,
    minimum: int | None = None,
    positive: bool = False,
) -> list[int] | None:
    if not isinstance(value, list):
        errors.append(f"line {line_no}: {field} must be a list")
        return None
    if expected_len is not None and len(value) != expected_len:
        errors.append(f"line {line_no}: len({field}) != {expected_len}")
    parsed: list[int] = []
    for index, item in enumerate(value):
        parsed_item = _parse_int(
            item,
            f"{field}[{index}]",
            line_no=line_no,
            errors=errors,
            minimum=minimum,
            positive=positive,
        )
        if parsed_item is not None:
            parsed.append(parsed_item)
    return parsed if len(parsed) == len(value) else None


def _is_monotonic_non_decreasing(values: list[int]) -> bool:
    return all(right >= left for left, right in zip(values, values[1:]))


def _summary_int(value: Any) -> int | None:
    try:
        return _as_int(value, "summary")
    except Exception:
        return None


def _check_record(record: dict[str, Any], *, line_no: int) -> list[str]:
    schema_version_raw = record.get("schema_version")
    try:
        schema_version = _as_int(schema_version_raw, "schema_version")
    except Exception:
        schema_version = 1
    if schema_version == 2:
        return _check_record_v2(record, line_no=line_no)

    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"line {line_no}: missing required field {field}")
    if errors:
        return errors

    try:
        schema_version = _as_int(record["schema_version"], "schema_version")
        if schema_version != 1:
            errors.append(f"line {line_no}: schema_version must be 1")
        batch_size = _as_int(record["batch_size"], "batch_size")
        q_len = _as_int(record["q_len"], "q_len")
        num_q_heads = _as_int(record["num_q_heads"], "num_q_heads")
        num_kv_heads = _as_int(record["num_kv_heads"], "num_kv_heads")
        head_dim = _as_int(record["head_dim"], "head_dim")
        page_block_size = _as_int(record["page_block_size"], "page_block_size")
        scheduler_active_tokens = _as_int(
            record["scheduler_active_tokens"], "scheduler_active_tokens"
        )
    except Exception as exc:
        return [f"line {line_no}: integer field parse failed: {exc}"]

    if batch_size <= 0:
        errors.append(f"line {line_no}: batch_size must be positive")
    if q_len <= 0:
        errors.append(f"line {line_no}: q_len must be positive")
    if num_q_heads <= 0 or num_kv_heads <= 0:
        errors.append(f"line {line_no}: head counts must be positive")
    if head_dim <= 0:
        errors.append(f"line {line_no}: head_dim must be positive")
    if page_block_size <= 0:
        errors.append(f"line {line_no}: page_block_size must be positive")
    if scheduler_active_tokens <= 0:
        errors.append(f"line {line_no}: scheduler_active_tokens must be positive")

    cache_seqlens = record["cache_seqlens"]
    valid_counts = record["block_table_valid_counts"]
    block_shape = record["block_table_shape"]
    if not isinstance(cache_seqlens, list):
        errors.append(f"line {line_no}: cache_seqlens must be a list")
    if not isinstance(valid_counts, list):
        errors.append(f"line {line_no}: block_table_valid_counts must be a list")
    if not isinstance(block_shape, list) or len(block_shape) != 2:
        errors.append(f"line {line_no}: block_table_shape must be [rows, cols]")
    if isinstance(cache_seqlens, list) and len(cache_seqlens) != batch_size:
        errors.append(
            f"line {line_no}: len(cache_seqlens)={len(cache_seqlens)} "
            f"!= batch_size={batch_size}"
        )
    if isinstance(valid_counts, list) and len(valid_counts) != batch_size:
        errors.append(
            f"line {line_no}: len(block_table_valid_counts)={len(valid_counts)} "
            f"!= batch_size={batch_size}"
        )
    if isinstance(block_shape, list) and len(block_shape) == 2:
        try:
            rows = int(block_shape[0])
            cols = int(block_shape[1])
            if rows < batch_size:
                errors.append(
                    f"line {line_no}: block_table_shape[0]={rows} < batch_size={batch_size}"
                )
            if cols <= 0:
                errors.append(f"line {line_no}: block_table_shape[1] must be positive")
        except Exception as exc:
            errors.append(f"line {line_no}: block_table_shape parse failed: {exc}")

    if isinstance(cache_seqlens, list) and isinstance(valid_counts, list):
        for index, (seq_len, count) in enumerate(zip(cache_seqlens, valid_counts)):
            seq_len_int = int(seq_len)
            count_int = int(count)
            if seq_len_int < 0:
                errors.append(f"line {line_no}: cache_seqlens[{index}] is negative")
            expected_min = (seq_len_int + page_block_size - 1) // page_block_size
            if count_int < expected_min:
                errors.append(
                    f"line {line_no}: block_table_valid_counts[{index}]={count_int} "
                    f"< ceil(cache_seqlens/page_block_size)={expected_min}"
                )

    if "actual_work_size" in record and int(record["actual_work_size"]) < 0:
        errors.append(f"line {line_no}: actual_work_size must be non-negative")
    if "actual_work_size" in record and "work_item_formula" not in record:
        errors.append(
            f"line {line_no}: work_item_formula is required with actual_work_size"
        )
    return errors


def _check_record_v2(record: dict[str, Any], *, line_no: int) -> list[str]:
    errors: list[str] = []
    for field in V2_REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"line {line_no}: missing required v2 field {field}")
    if errors:
        return errors
    try:
        if _as_int(record["schema_version"], "schema_version") != 2:
            errors.append(f"line {line_no}: schema_version must be 2")
        batch_size = _as_int(record["batch_size"], "batch_size")
        num_q_heads = _as_int(record["num_q_heads"], "num_q_heads")
        num_kv_heads = _as_int(record["num_kv_heads"], "num_kv_heads")
        head_dim = _as_int(record["head_dim"], "head_dim")
        block_size_tokens = _as_int(record["block_size_tokens"], "block_size_tokens")
    except Exception as exc:
        return [f"line {line_no}: integer field parse failed: {exc}"]
    if record.get("trace_type") != "vllm_paged_kv_block_table":
        errors.append(f"line {line_no}: trace_type must be vllm_paged_kv_block_table")
    if batch_size <= 0:
        errors.append(f"line {line_no}: batch_size must be positive")
    if num_q_heads <= 0 or num_kv_heads <= 0:
        errors.append(f"line {line_no}: head counts must be positive")
    if head_dim <= 0:
        errors.append(f"line {line_no}: head_dim must be positive")
    if block_size_tokens <= 0:
        errors.append(f"line {line_no}: block_size_tokens must be positive")
    # Hybrid/Mamba-backed vLLM models may intentionally raise the attention
    # block size to match a larger state page.  Keep validating the field, but
    # report the distribution instead of rejecting nonstandard real values.
    cache_seqlens = record.get("cache_seqlens")
    q_lens = record.get("q_lens")
    query_start_loc = record.get("query_start_loc")
    seq_start_loc = record.get("seq_start_loc")
    block_tables_shape = record.get("block_tables_shape")
    sequences = record.get("sequences")
    cache_values = _parse_int_list(
        cache_seqlens,
        "cache_seqlens",
        line_no=line_no,
        errors=errors,
        expected_len=batch_size,
        minimum=0,
    )
    q_values = _parse_int_list(
        q_lens,
        "q_lens",
        line_no=line_no,
        errors=errors,
        expected_len=batch_size,
        positive=True,
    )
    query_start_values = _parse_int_list(
        query_start_loc,
        "query_start_loc",
        line_no=line_no,
        errors=errors,
        expected_len=batch_size + 1,
        minimum=0,
    )
    seq_start_values = _parse_int_list(
        seq_start_loc,
        "seq_start_loc",
        line_no=line_no,
        errors=errors,
        expected_len=batch_size + 1,
        minimum=0,
    )
    if not isinstance(sequences, list):
        errors.append(f"line {line_no}: sequences must be a list")
    if query_start_values is not None:
        if not _is_monotonic_non_decreasing(query_start_values):
            errors.append(f"line {line_no}: query_start_loc must be monotonic")
        if query_start_values and query_start_values[0] != 0:
            errors.append(f"line {line_no}: query_start_loc must start at 0")
        if q_values is not None and query_start_values:
            expected_tail = sum(q_values)
            if query_start_values[-1] != expected_tail:
                errors.append(
                    f"line {line_no}: query_start_loc[-1]={query_start_values[-1]} "
                    f"!= sum(q_lens)={expected_tail}"
                )
            if len(query_start_values) == len(q_values) + 1:
                for index, q_len_value in enumerate(q_values):
                    span = query_start_values[index + 1] - query_start_values[index]
                    if span != q_len_value:
                        errors.append(
                            f"line {line_no}: query_start_loc span {index}={span} "
                            f"!= q_lens[{index}]={q_len_value}"
                        )
                        break
    if seq_start_values is not None:
        if not _is_monotonic_non_decreasing(seq_start_values):
            errors.append(f"line {line_no}: seq_start_loc must be monotonic")
        if seq_start_values and seq_start_values[0] != 0:
            errors.append(f"line {line_no}: seq_start_loc must start at 0")
    if not isinstance(block_tables_shape, list) or len(block_tables_shape) != 2:
        errors.append(f"line {line_no}: block_tables_shape must be [rows, cols]")
        table_rows = None
        table_cols = None
    else:
        table_rows = _parse_int(
            block_tables_shape[0],
            "block_tables_shape[0]",
            line_no=line_no,
            errors=errors,
            minimum=0,
        )
        table_cols = _parse_int(
            block_tables_shape[1],
            "block_tables_shape[1]",
            line_no=line_no,
            errors=errors,
            minimum=0,
        )
        if table_rows is not None and table_rows < batch_size:
            errors.append(
                f"line {line_no}: block_tables_shape[0]={table_rows} "
                f"< batch_size={batch_size}"
            )
    if isinstance(sequences, list) and len(sequences) != batch_size:
        errors.append(f"line {line_no}: len(sequences) != batch_size")
    if not (
        cache_values is not None
        and isinstance(sequences, list)
        and table_cols is not None
        and block_size_tokens > 0
    ):
        return errors
    for row, sequence in enumerate(sequences):
        if not isinstance(sequence, dict):
            errors.append(f"line {line_no}: sequences[{row}] must be object")
            continue
        sequence_row = _parse_int(
            sequence.get("row", row),
            f"sequences[{row}].row",
            line_no=line_no,
            errors=errors,
            minimum=0,
        )
        if sequence_row is not None and sequence_row != row:
            errors.append(f"line {line_no}: sequences[{row}].row mismatch")
        cache_len = cache_values[row]
        sequence_cache_len = sequence.get("cache_seqlen")
        if sequence_cache_len is not None:
            parsed_sequence_cache_len = _parse_int(
                sequence_cache_len,
                f"sequences[{row}].cache_seqlen",
                line_no=line_no,
                errors=errors,
                minimum=0,
            )
            if (
                parsed_sequence_cache_len is not None
                and parsed_sequence_cache_len != cache_len
            ):
                errors.append(
                    f"line {line_no}: sequences[{row}].cache_seqlen="
                    f"{parsed_sequence_cache_len} != cache_seqlens[{row}]={cache_len}"
                )
        expected_blocks = (cache_len + block_size_tokens - 1) // block_size_tokens
        valid_count = _parse_int(
            sequence.get("valid_block_count", -1),
            f"sequences[{row}].valid_block_count",
            line_no=line_no,
            errors=errors,
            minimum=0,
        )
        if valid_count is None:
            continue
        if valid_count != expected_blocks:
            errors.append(
                f"line {line_no}: sequences[{row}].valid_block_count={valid_count} "
                f"!= ceil(cache_seqlen/block_size_tokens)={expected_blocks}"
            )
        if valid_count > table_cols:
            errors.append(f"line {line_no}: valid_block_count exceeds table columns")
        block_ids = sequence.get("block_ids")
        if not isinstance(block_ids, list):
            errors.append(f"line {line_no}: sequences[{row}].block_ids must be list")
            continue
        if len(block_ids) != valid_count:
            errors.append(
                f"line {line_no}: len(sequences[{row}].block_ids)={len(block_ids)} "
                f"!= valid_block_count={valid_count}"
            )
        for block_index, block_id in enumerate(block_ids):
            parsed_block_id = _parse_int(
                block_id,
                f"sequences[{row}].block_ids[{block_index}]",
                line_no=line_no,
                errors=errors,
                minimum=0,
            )
            if parsed_block_id is None:
                break
        prompt_len = sequence.get("prompt_len")
        generated_token_idx = sequence.get("generated_token_idx")
        if prompt_len is not None:
            parsed_prompt_len = _parse_int(
                prompt_len,
                f"sequences[{row}].prompt_len",
                line_no=line_no,
                errors=errors,
                minimum=0,
            )
        else:
            parsed_prompt_len = None
        if generated_token_idx is not None:
            parsed_generated_token_idx = _parse_int(
                generated_token_idx,
                f"sequences[{row}].generated_token_idx",
                line_no=line_no,
                errors=errors,
                minimum=0,
            )
        else:
            parsed_generated_token_idx = None
        if (
            parsed_prompt_len is not None
            and parsed_generated_token_idx is not None
            and cache_len >= parsed_prompt_len
        ):
            expected_generated_token_idx = cache_len - parsed_prompt_len
            if parsed_generated_token_idx != expected_generated_token_idx:
                errors.append(
                    f"line {line_no}: sequences[{row}].generated_token_idx="
                    f"{parsed_generated_token_idx} != cache_seqlen - prompt_len="
                    f"{expected_generated_token_idx}"
                )
    return errors


def check_trace(path: Path) -> dict[str, Any]:
    rows = 0
    errors: list[str] = []
    phase_counts: dict[str, int] = {}
    max_cache_len = 0
    schema_counts: dict[str, int] = {}
    block_size_counts: dict[str, int] = {}
    nonstandard_block_sizes: dict[str, int] = {}
    cache_lengths: list[int] = []
    valid_block_counts: list[int] = []
    unique_blocks: set[int] = set()
    total_block_refs = 0
    consecutive_run_lengths: list[int] = []
    first_row_prefixes: list[tuple[int, ...]] = []
    kv_cache_layout_available = 0
    kv_cache_layout_unavailable = 0
    sequence_prompt_len_null = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            rows += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_no}: invalid JSON: {exc}")
                continue
            if not isinstance(record, dict):
                errors.append(f"line {line_no}: row must be a JSON object")
                continue
            errors.extend(_check_record(record, line_no=line_no))
            schema = str(record.get("schema_version"))
            schema_counts[schema] = schema_counts.get(schema, 0) + 1
            phase = str(record.get("phase"))
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            cache_seqlens = record.get("cache_seqlens")
            if isinstance(cache_seqlens, list) and cache_seqlens:
                cache_values = [
                    parsed
                    for parsed in (_summary_int(value) for value in cache_seqlens)
                    if parsed is not None and parsed >= 0
                ]
            else:
                cache_values = []
            if cache_values:
                max_cache_len = max(max_cache_len, max(cache_values))
                cache_lengths.extend(cache_values)
            schema_version = _summary_int(record.get("schema_version", 1))
            if schema_version == 2:
                kv_layout = record.get("kv_cache_layout")
                if isinstance(kv_layout, dict) and bool(kv_layout.get("available")):
                    kv_cache_layout_available += 1
                else:
                    kv_cache_layout_unavailable += 1
                block_size = record.get("block_size_tokens")
                block_size_int = _summary_int(block_size)
                if block_size_int is not None:
                    key = str(block_size_int)
                    block_size_counts[key] = block_size_counts.get(key, 0) + 1
                    if block_size_int not in {8, 16, 32, 64}:
                        nonstandard_block_sizes[key] = (
                            nonstandard_block_sizes.get(key, 0) + 1
                        )
                sequences = record.get("sequences")
                if isinstance(sequences, list):
                    for sequence in sequences:
                        if not isinstance(sequence, dict):
                            continue
                        if sequence.get("prompt_len") is None:
                            sequence_prompt_len_null += 1
                        valid_count = sequence.get("valid_block_count")
                        valid_count_int = _summary_int(valid_count)
                        if valid_count_int is not None and valid_count_int >= 0:
                            valid_block_counts.append(valid_count_int)
                        block_ids = sequence.get("block_ids")
                        if not isinstance(block_ids, list):
                            continue
                        block_values = [
                            parsed
                            for parsed in (_summary_int(item) for item in block_ids)
                            if parsed is not None and parsed >= 0
                        ]
                        if len(block_values) != len(block_ids):
                            continue
                        unique_blocks.update(block_values)
                        total_block_refs += len(block_values)
                        if block_values:
                            first_row_prefixes.append(
                                tuple(block_values[: min(8, len(block_values))])
                            )
                        current_run = 1
                        for left, right in zip(block_values, block_values[1:]):
                            if int(right) == int(left) + 1:
                                current_run += 1
                            else:
                                consecutive_run_lengths.append(current_run)
                                current_run = 1
                        if block_values:
                            consecutive_run_lengths.append(current_run)
    prefix_counts: dict[tuple[int, ...], int] = {}
    for prefix in first_row_prefixes:
        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
    shared_prefix_counts = [count for count in prefix_counts.values() if count > 1]
    return {
        "path": str(path),
        "row_count": rows,
        "error_count": len(errors),
        "errors": errors[:50],
        "phase_counts": phase_counts,
        "schema_version_counts": schema_counts,
        "max_cache_seqlen": max_cache_len,
        "block_size_tokens_distribution": block_size_counts,
        "nonstandard_block_size_tokens_distribution": nonstandard_block_sizes,
        "nonstandard_block_size_note": (
            "nonstandard values are allowed when vLLM changes attention page "
            "size for hybrid/Mamba page alignment; inspect vLLM logs/config"
            if nonstandard_block_sizes
            else None
        ),
        "cache_seqlen": {
            "min": min(cache_lengths) if cache_lengths else None,
            "p50": _percentile(cache_lengths, 0.50),
            "p90": _percentile(cache_lengths, 0.90),
            "max": max(cache_lengths) if cache_lengths else None,
        },
        "valid_block_count": {
            "min": min(valid_block_counts) if valid_block_counts else None,
            "p50": _percentile(valid_block_counts, 0.50),
            "p90": _percentile(valid_block_counts, 0.90),
            "max": max(valid_block_counts) if valid_block_counts else None,
        },
        "unique_physical_block_ids": len(unique_blocks),
        "total_block_references": int(total_block_refs),
        "kv_cache_layout_available_count": int(kv_cache_layout_available),
        "kv_cache_layout_unavailable_count": int(kv_cache_layout_unavailable),
        "sequence_prompt_len_null_count": int(sequence_prompt_len_null),
        "block_reuse_ratio": (
            float(1.0 - (len(unique_blocks) / total_block_refs))
            if total_block_refs > 0
            else None
        ),
        "prefix_shared_block_count_distribution": {
            "shared_prefixes": len(shared_prefix_counts),
            "max_reuse": max(shared_prefix_counts) if shared_prefix_counts else 0,
        },
        "consecutive_block_id_run_length": {
            "min": min(consecutive_run_lengths) if consecutive_run_lengths else None,
            "p50": _percentile(consecutive_run_lengths, 0.50),
            "p90": _percentile(consecutive_run_lengths, 0.90),
            "max": max(consecutive_run_lengths) if consecutive_run_lengths else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--require-rows", type=int, default=1)
    args = parser.parse_args()

    summary = check_trace(args.trace)
    if summary["row_count"] < int(args.require_rows):
        summary["error_count"] += 1
        summary["errors"].append(
            f"row_count={summary['row_count']} < required {args.require_rows}"
        )
    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if int(summary["error_count"]) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
