#!/usr/bin/env python3
"""Materialize a merged online typed-consumer input for native ABI canaries.

This script concatenates multiple vLLM-exported readonly prelaunch handle
tables into one typed-consumer input JSON accepted by
``scripts/run_premap_typed_consumer_stub.py --input-json``.

The merged table is a diagnostic/native-stub artifact only. It is not a single
vLLM launch table, it does not move payload bytes, and it is not passed to the
current WNA16 fused-MoE kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from mtp_expert_prefetch.runtime.cache_manager import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
    "expert_id",
    "address_key_hash",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _resolve_path(raw: str | Path, *, base: Path = REPO_ROOT) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else base / path


def input_paths_from_runner_artifact(path: Path) -> list[Path]:
    payload = _load_json(path)
    raw_paths = payload.get("online_prelaunch_input_jsons")
    if not isinstance(raw_paths, list) or not raw_paths:
        first = payload.get("online_prelaunch_input_json")
        raw_paths = [first] if isinstance(first, str) and first else []
    paths = [
        _resolve_path(item)
        for item in raw_paths
        if isinstance(item, str) and item.strip()
    ]
    if not paths:
        raise ValueError(f"runner artifact does not list online input JSONs: {path}")
    return paths


def _field_values(payload: dict[str, Any], field: str, *, path: Path) -> list[int]:
    raw = payload.get(field)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"input field must be a non-empty list: {field}: {path}")
    return [int(value) for value in raw]


def _table_row_count(payload: dict[str, Any], *, path: Path) -> int:
    values = _field_values(payload, HANDLE_FIELDS[0], path=path)
    row_count = len(values)
    mismatched = [
        field
        for field in HANDLE_FIELDS[1:]
        if len(_field_values(payload, field, path=path)) != row_count
    ]
    if mismatched:
        raise ValueError(f"input field length mismatch for {path}: {mismatched}")
    meta = payload.get("_meta")
    if isinstance(meta, dict) and meta.get("row_count") != row_count:
        raise ValueError(f"_meta.row_count mismatch for {path}")
    return row_count


def _sha256_hex(obj: Any) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _make_meta(
    arrays: dict[str, list[int]],
    *,
    source_paths: list[Path],
    row_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    row_count = len(arrays["descriptor_ptr"])
    row_order_hash = hashlib.sha256(
        "|".join(str(value) for value in arrays["address_key_hash"]).encode("utf-8")
    ).hexdigest()
    ordered_row_hash = hashlib.sha256(
        "|".join(
            ":".join(
                str(arrays[field][idx])
                for field in (
                    "address_key_hash",
                    "descriptor_ptr",
                    "packed_weight_descriptor",
                    "scale_metadata_handle",
                    "aux_metadata_handle",
                    "expert_id",
                )
            )
            for idx in range(row_count)
        ).encode("utf-8")
    ).hexdigest()
    table_object_hash = _sha256_hex(
        {
            "source": "merged_vllm_prelaunch_typed_consumer_inputs",
            "schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
            "row_count": row_count,
            "source_paths": [str(path) for path in source_paths],
            "row_spans": row_spans,
            "arrays": arrays,
            "payload_bytes": 0,
            "ready_credit": False,
            "changes_router": False,
            "changes_descriptor_order": False,
            "changes_kernel_launch_args": False,
            "passed_to_kernel": False,
        }
    )
    return {
        "schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
        "row_count": row_count,
        "column_count": 4,
        "row_order_hash": row_order_hash,
        "ordered_row_hash": ordered_row_hash,
        "table_object_hash": table_object_hash,
        "payload_bytes": 0,
        "ready_credit": False,
        "changes_router": False,
        "changes_descriptor_order": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }


def materialize_merged_input(
    input_paths: list[Path],
    *,
    max_inputs: int | None = None,
    min_total_rows: int = 0,
    block_threads: int = 256,
) -> dict[str, Any]:
    if not input_paths:
        raise ValueError("at least one input JSON is required")
    if int(block_threads) <= 0:
        raise ValueError("block_threads must be positive")
    if max_inputs is not None and int(max_inputs) <= 0:
        raise ValueError("max_inputs must be positive when provided")
    selected_paths = input_paths[:max_inputs] if max_inputs else list(input_paths)
    arrays: dict[str, list[int]] = {field: [] for field in HANDLE_FIELDS}
    row_spans: list[dict[str, Any]] = []
    source_contexts: list[dict[str, Any]] = []
    cursor = 0
    for index, path in enumerate(selected_paths):
        payload = _load_json(path)
        row_count = _table_row_count(payload, path=path)
        for field in HANDLE_FIELDS:
            arrays[field].extend(_field_values(payload, field, path=path))
        row_spans.append(
            {
                "source_index": index,
                "path": str(path),
                "row_start": cursor,
                "row_count": row_count,
                "row_end": cursor + row_count,
                "source_table_object_hash": (
                    payload.get("_meta", {}).get("table_object_hash")
                    if isinstance(payload.get("_meta"), dict)
                    else None
                ),
                "source_schema_hash": (
                    payload.get("_meta", {}).get("schema_hash")
                    if isinstance(payload.get("_meta"), dict)
                    else None
                ),
            }
        )
        export_context = payload.get("_export_context")
        if isinstance(export_context, dict):
            source_contexts.append(
                {
                    "source_index": index,
                    "export_index": export_context.get("export_index"),
                    "layer_id": export_context.get("layer_id"),
                    "request_id": export_context.get("request_id"),
                    "sequence_id": export_context.get("sequence_id"),
                    "token_index": export_context.get("token_index"),
                    "row_count": export_context.get("row_count"),
                }
            )
        cursor += row_count

    row_count = len(arrays["descriptor_ptr"])
    if min_total_rows and row_count < int(min_total_rows):
        raise ValueError(
            f"merged row_count {row_count} is below required minimum {min_total_rows}"
        )
    if block_threads > 0 and row_count <= int(block_threads):
        raise ValueError(
            f"merged row_count {row_count} must exceed block_threads {block_threads} "
            "for a multi-program canary"
        )
    meta = _make_meta(arrays, source_paths=selected_paths, row_spans=row_spans)
    program_count = (row_count + max(1, int(block_threads)) - 1) // max(
        1, int(block_threads)
    )
    payload: dict[str, Any] = {
        **arrays,
        "_meta": meta,
        "_merge_context": {
            "source": "merged_vllm_prelaunch_typed_consumer_inputs",
            "source_count": len(selected_paths),
            "row_count": row_count,
            "row_spans": row_spans,
            "source_contexts": source_contexts,
            "block_threads": int(block_threads),
            "expected_program_count": program_count,
            "payload_bytes": 0,
            "ready_credit": False,
            "changes_router": False,
            "changes_descriptor_order": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "not_a_single_vllm_launch_table": True,
        },
    }
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner-json", type=Path)
    parser.add_argument("--input-json", type=Path, action="append", default=[])
    parser.add_argument("--max-inputs", type=int)
    parser.add_argument("--min-total-rows", type=int, default=0)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    input_paths = list(args.input_json or [])
    if args.runner_json is not None:
        input_paths.extend(input_paths_from_runner_artifact(args.runner_json))
    input_paths = [_resolve_path(path) for path in input_paths]
    payload = materialize_merged_input(
        input_paths,
        max_inputs=args.max_inputs,
        min_total_rows=int(args.min_total_rows),
        block_threads=int(args.block_threads),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "row_count": payload["_meta"]["row_count"],
                "source_count": payload["_merge_context"]["source_count"],
                "expected_program_count": payload["_merge_context"][
                    "expected_program_count"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
