from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "materialize_premap_online_merged_typed_consumer_input.py"
    )
    spec = importlib.util.spec_from_file_location(
        "materialize_premap_online_merged_typed_consumer_input", path
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_input(path: Path, *, start: int, rows: int, export_index: int) -> None:
    payload = {
        "descriptor_ptr": [1000 + start + idx for idx in range(rows)],
        "packed_weight_descriptor": [2000 + start + idx for idx in range(rows)],
        "scale_metadata_handle": [3000 + start + idx for idx in range(rows)],
        "aux_metadata_handle": [4000 + start + idx for idx in range(rows)],
        "expert_id": [(start + idx) % 8 for idx in range(rows)],
        "address_key_hash": [5000 + start + idx for idx in range(rows)],
        "_meta": {
            "schema_hash": "schema",
            "row_count": rows,
            "column_count": 4,
            "table_object_hash": f"table-{export_index}",
            "payload_bytes": 0,
            "ready_credit": False,
            "changes_router": False,
            "changes_descriptor_order": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "_export_context": {
            "export_index": export_index,
            "layer_id": export_index,
            "request_id": f"req-{export_index}",
            "sequence_id": "seq0",
            "token_index": -1,
            "row_count": rows,
        },
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_materialize_merged_input_concatenates_online_tables(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)

    payload = module.materialize_merged_input(
        [first, second],
        min_total_rows=7,
        block_threads=4,
    )

    assert payload["_meta"]["row_count"] == 7
    assert payload["_meta"]["column_count"] == 4
    assert payload["_meta"]["payload_bytes"] == 0
    assert payload["_meta"]["passed_to_kernel"] is False
    assert payload["_merge_context"]["source_count"] == 2
    assert payload["_merge_context"]["expected_program_count"] == 2
    assert payload["_merge_context"]["not_a_single_vllm_launch_table"] is True
    assert payload["descriptor_ptr"] == [1000, 1001, 1002, 1100, 1101, 1102, 1103]
    assert payload["address_key_hash"] == [5000, 5001, 5002, 5100, 5101, 5102, 5103]
    assert payload["_merge_context"]["row_spans"][0]["row_start"] == 0
    assert payload["_merge_context"]["row_spans"][0]["row_end"] == 3
    assert payload["_merge_context"]["row_spans"][1]["row_start"] == 3
    assert payload["_merge_context"]["row_spans"][1]["row_end"] == 7
    assert payload["_merge_context"]["source_contexts"][1]["request_id"] == "req-1"


def test_materialize_merged_input_rejects_single_program(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "input0.json"
    _write_input(first, start=0, rows=4, export_index=0)

    with pytest.raises(ValueError, match="must exceed block_threads"):
        module.materialize_merged_input([first], block_threads=4)


def test_materialize_merged_input_rejects_non_positive_block_threads(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)

    with pytest.raises(ValueError, match="block_threads must be positive"):
        module.materialize_merged_input([first, second], block_threads=0)


def test_materialize_merged_input_rejects_non_positive_max_inputs(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)

    with pytest.raises(ValueError, match="max_inputs must be positive"):
        module.materialize_merged_input([first, second], max_inputs=-1)


def test_input_paths_from_runner_artifact(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    runner.write_text(
        json.dumps({"online_prelaunch_input_jsons": [str(first), str(second)]})
        + "\n",
        encoding="utf-8",
    )

    assert module.input_paths_from_runner_artifact(runner) == [first, second]


def test_materialize_cli_writes_output(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    output = tmp_path / "merged.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)

    exit_code = module.main(
        [
            "--input-json",
            str(first),
            "--input-json",
            str(second),
            "--block-threads",
            "4",
            "--min-total-rows",
            "7",
            "--output-json",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["_meta"]["row_count"] == 7
