from __future__ import annotations

import json
from pathlib import Path

from scripts.run_premap_online_merged_native_arg_slot_window_sweep import (
    _window_bounds,
    build_parser,
    main,
    run_sweep,
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


def test_window_bounds_cover_head_middle_tail():
    assert _window_bounds(17, 4) == {
        "head": (0, 4),
        "middle": (6, 10),
        "tail": (13, 17),
    }


def test_window_sweep_dry_run_records_expected_windows(tmp_path: Path):
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    output = tmp_path / "sweep.json"
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

    result = run_sweep(args)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["row_count"] == 17
    assert result["windows"]["full"]["dispatch_row_offset"] == 0
    assert result["windows"]["full"]["dispatch_row_limit"] == 17
    assert result["windows"]["head"]["dispatch_row_offset"] == 0
    assert result["windows"]["head"]["dispatch_row_limit"] == 4
    assert result["windows"]["middle"]["dispatch_row_offset"] == 6
    assert result["windows"]["middle"]["dispatch_row_limit"] == 10
    assert result["windows"]["tail"]["dispatch_row_offset"] == 13
    assert result["windows"]["tail"]["dispatch_row_limit"] == 17
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_window_sweep_cli_writes_output(tmp_path: Path):
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    output = tmp_path / "sweep.json"
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
    assert json.loads(output.read_text(encoding="utf-8"))["source"] == (
        "online_merged_future_native_arg_slot_window_sweep_runner"
    )
