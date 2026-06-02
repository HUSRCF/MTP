from __future__ import annotations

import json
from pathlib import Path

from scripts.run_premap_online_merged_native_arg_slot_all_field_window_sweep import (
    MIRROR_FIELDS,
    build_parser,
    main,
    run_all_field_sweep,
)


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


def _write_runner(path: Path, inputs: list[Path]) -> None:
    path.write_text(
        json.dumps({"online_prelaunch_input_jsons": [str(item) for item in inputs]})
        + "\n",
        encoding="utf-8",
    )


def test_all_field_window_sweep_dry_run_records_all_fields(tmp_path: Path):
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    output = tmp_path / "all_fields.json"
    _write_input(first, start=0, rows=8, export_index=0)
    _write_input(second, start=100, rows=9, export_index=1)
    _write_runner(runner, [first, second])

    args = build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--output-json",
            str(output),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "17",
            "--block-threads",
            "4",
            "--window-size",
            "4",
            "--dry-run",
        ]
    )

    result = run_all_field_sweep(args)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["payload_bytes"] == 0
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert result["mirror_fields"] == list(MIRROR_FIELDS)
    assert set(result["field_reports"]) == set(MIRROR_FIELDS)
    assert set(result["row_counts"].values()) == {17}
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_all_field_window_sweep_cli_writes_output(tmp_path: Path):
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    output = tmp_path / "all_fields.json"
    _write_input(first, start=0, rows=8, export_index=0)
    _write_input(second, start=100, rows=9, export_index=1)
    _write_runner(runner, [first, second])

    exit_code = main(
        [
            "--runner-json",
            str(runner),
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--output-json",
            str(output),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "17",
            "--block-threads",
            "4",
            "--window-size",
            "4",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source"] == (
        "online_merged_future_native_arg_slot_all_field_window_sweep_runner"
    )
    assert payload["passed"] is True
