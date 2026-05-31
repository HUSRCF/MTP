from __future__ import annotations

import json

from scripts.check_vllm_decode_workload_trace import check_trace


def _valid_v2_record() -> dict:
    return {
        "schema_version": 2,
        "trace_type": "vllm_paged_kv_block_table",
        "capture_point": "after_metadata_build_before_attention_launch",
        "record_idx": 0,
        "phase": "decode",
        "decode_step": 1,
        "batch_size": 1,
        "cache_seqlens": [513],
        "q_lens": [1],
        "query_start_loc": [0, 1],
        "seq_start_loc": [0, 1],
        "num_q_heads": 16,
        "num_kv_heads": 2,
        "head_dim": 256,
        "kv_dtype": "bf16",
        "block_size_tokens": 1056,
        "block_tables_shape": [1, 1],
        "sample_idx": 0,
        "record_id": "sample_0",
        "layer_ordinal": 0,
        "q_len": 1,
        "kv_cache_layout": {"available": True},
        "sequences": [
            {
                "row": 0,
                "prompt_len": 512,
                "generated_token_idx": 1,
                "cache_seqlen": 513,
                "valid_block_count": 1,
                "block_ids": [4],
            }
        ],
    }


def _write_jsonl(tmp_path, record: dict):
    path = tmp_path / "trace.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return path


def test_v2_checker_accepts_valid_record(tmp_path):
    summary = check_trace(_write_jsonl(tmp_path, _valid_v2_record()))

    assert summary["error_count"] == 0
    assert summary["row_count"] == 1
    assert summary["block_size_tokens_distribution"] == {"1056": 1}


def test_v2_checker_accepts_strict_decode_provenance_and_layout(tmp_path):
    summary = check_trace(
        _write_jsonl(tmp_path, _valid_v2_record()),
        require_decode_only=True,
        require_provenance=True,
        require_kv_cache_layout_available=True,
    )

    assert summary["error_count"] == 0
    assert summary["strict_requirements"] == {
        "decode_only_q_len_1": True,
        "provenance": True,
        "kv_cache_layout_available": True,
    }


def test_v2_checker_strict_mode_rejects_prefill_and_missing_provenance(tmp_path):
    record = _valid_v2_record()
    record["q_len"] = 512
    record["q_lens"] = [512]
    record.pop("sample_idx")
    record["kv_cache_layout"] = {"available": False}

    summary = check_trace(
        _write_jsonl(tmp_path, record),
        require_decode_only=True,
        require_provenance=True,
        require_kv_cache_layout_available=True,
    )

    assert summary["error_count"] > 0
    assert any("sample_idx is required" in err for err in summary["errors"])
    assert any("kv_cache_layout.available is required" in err for err in summary["errors"])
    assert any("q_len=512 != 1" in err for err in summary["errors"])
    assert any("q_lens must all be 1 for decode-only" in err for err in summary["errors"])


def test_v2_checker_reports_zero_block_size_without_crashing(tmp_path):
    record = _valid_v2_record()
    record["block_size_tokens"] = 0

    summary = check_trace(_write_jsonl(tmp_path, record))

    assert summary["error_count"] > 0
    assert any("block_size_tokens must be positive" in err for err in summary["errors"])


def test_v2_checker_rejects_bool_cache_seqlen(tmp_path):
    record = _valid_v2_record()
    record["cache_seqlens"] = [True]

    summary = check_trace(_write_jsonl(tmp_path, record))

    assert summary["error_count"] > 0
    assert any("cache_seqlens[0] parse failed" in err for err in summary["errors"])


def test_v2_checker_rejects_negative_valid_count(tmp_path):
    record = _valid_v2_record()
    record["sequences"][0]["valid_block_count"] = -1

    summary = check_trace(_write_jsonl(tmp_path, record))

    assert summary["error_count"] > 0
    assert any(
        "sequences[0].valid_block_count must be >= 0" in err
        for err in summary["errors"]
    )


def test_v2_checker_validates_query_start_loc_and_generation_index(tmp_path):
    record = _valid_v2_record()
    record["query_start_loc"] = [0, 2]
    record["sequences"][0]["generated_token_idx"] = 4

    summary = check_trace(_write_jsonl(tmp_path, record))

    assert summary["error_count"] > 0
    assert any("query_start_loc[-1]=2 != sum(q_lens)=1" in err for err in summary["errors"])
    assert any(
        "sequences[0].generated_token_idx=4 != cache_seqlen - prompt_len=1" in err
        for err in summary["errors"]
    )
