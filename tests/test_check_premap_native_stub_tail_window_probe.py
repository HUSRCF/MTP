from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_native_stub_tail_window_probe import (
    check_tail_window_probe,
    main,
)


def _dispatch_summary(
    *,
    field_name: str,
    row_count: int = 16,
    tail_window_size: int = 4,
) -> dict:
    offset = row_count - tail_window_size
    return {
        "passed": True,
        "ok": True,
        "row_count": row_count,
        "row_ok_count": row_count,
        "error_count": 0,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "future_kernel_native_dispatch_consumer_checked": True,
        "future_kernel_native_dispatch_consumer_payload_bytes": 0,
        "future_kernel_native_dispatch_consumer_passed_to_kernel": False,
        "future_kernel_native_dispatch_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_dispatch_consumer_row_count": tail_window_size,
        "future_kernel_native_dispatch_consumer_row_ok_count": tail_window_size,
        "future_kernel_native_dispatch_consumer_row_offset": offset,
        "future_kernel_native_dispatch_consumer_row_limit": row_count,
        "future_kernel_native_dispatch_consumer_active_rows": tail_window_size,
        "future_kernel_native_dispatch_ptr_consumer_checked": True,
        "future_kernel_native_dispatch_ptr_consumer_payload_bytes": 0,
        "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel": False,
        "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_dispatch_ptr_consumer_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_dispatch_ptr_consumer_row_count": tail_window_size,
        "future_kernel_native_dispatch_ptr_consumer_row_ok_count": tail_window_size,
        "future_kernel_native_arg_slot_consumer_checked": True,
        "future_kernel_native_arg_slot_consumer_payload_bytes": 0,
        "future_kernel_native_arg_slot_consumer_passed_to_kernel": False,
        "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_arg_slot_consumer_row_count": tail_window_size,
        "future_kernel_native_arg_slot_consumer_row_ok_count": tail_window_size,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_checked": True,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name": field_name,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": tail_window_size,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": tail_window_size,
    }


def _runner_payload(*, row_count: int = 16, tail_window_size: int = 4) -> dict:
    def extra_suite(extra_row_count: int) -> dict:
        return {
            "passed": True,
            "failures": [],
            "outputs": {
                "native_stub_future_kernel_native_consumer_dispatch_abi": {
                    "summary": _dispatch_summary(
                        field_name="scale_metadata_handle",
                        row_count=extra_row_count,
                        tail_window_size=tail_window_size,
                    )
                },
                "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror": {
                    "summary": _dispatch_summary(
                        field_name="descriptor_ptr",
                        row_count=extra_row_count,
                        tail_window_size=tail_window_size,
                    )
                },
                "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror": {
                    "summary": _dispatch_summary(
                        field_name="packed_weight_descriptor",
                        row_count=extra_row_count,
                        tail_window_size=tail_window_size,
                    )
                },
                "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror": {
                    "summary": _dispatch_summary(
                        field_name="aux_metadata_handle",
                        row_count=extra_row_count,
                        tail_window_size=tail_window_size,
                    )
                },
            },
        }

    return {
        "passed": True,
        "failures": [],
        "future_native_dispatch_tail_window_size": tail_window_size,
        "online_prelaunch_input_check_count": 2,
        "online_prelaunch_input_row_counts": [row_count, row_count + 8],
        "online_prelaunch_input_row_count_min": row_count,
        "online_prelaunch_input_row_count_max": row_count + 8,
        "online_prelaunch_input_row_count_sum": row_count * 2 + 8,
        "online_prelaunch_input_row_count_diverse": True,
        "future_kernel_native_consumer_dispatch_stub_summary": _dispatch_summary(
            field_name="scale_metadata_handle",
            row_count=row_count,
            tail_window_size=tail_window_size,
        ),
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary": _dispatch_summary(
            field_name="descriptor_ptr",
            row_count=row_count,
            tail_window_size=tail_window_size,
        ),
        "future_kernel_native_consumer_dispatch_packed_weight_stub_summary": _dispatch_summary(
            field_name="packed_weight_descriptor",
            row_count=row_count,
            tail_window_size=tail_window_size,
        ),
        "future_kernel_native_consumer_dispatch_aux_metadata_stub_summary": _dispatch_summary(
            field_name="aux_metadata_handle",
            row_count=row_count,
            tail_window_size=tail_window_size,
        ),
        "extra_online_input_check_summaries": [extra_suite(row_count + 8)],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_check_tail_window_probe_accepts_tail_window_runner(tmp_path: Path):
    runner = tmp_path / "runner.json"
    _write_json(runner, _runner_payload())

    result = check_tail_window_probe(
        runner_json=runner,
        expected_tail_window_size=4,
        min_online_inputs=2,
        min_tail_windowed_inputs=2,
        require_diverse_row_counts=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["dispatch_window_rows"][
        "future_kernel_native_consumer_dispatch_stub_summary"
    ] == 4


def test_check_tail_window_probe_rejects_full_table_runner(tmp_path: Path):
    runner = tmp_path / "runner.json"
    payload = _runner_payload(row_count=16, tail_window_size=4)
    payload["future_kernel_native_consumer_dispatch_stub_summary"][
        "future_kernel_native_dispatch_consumer_row_offset"
    ] = 0
    payload["future_kernel_native_consumer_dispatch_stub_summary"][
        "future_kernel_native_dispatch_consumer_row_count"
    ] = 16
    _write_json(runner, payload)

    result = check_tail_window_probe(
        runner_json=runner,
        expected_tail_window_size=4,
        min_online_inputs=2,
        min_tail_windowed_inputs=1,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "dispatch_offset_not_tail"
    ) in result["failures"]


def test_check_tail_window_probe_rejects_summary_row_count_input_mismatch(
    tmp_path: Path,
):
    runner = tmp_path / "runner.json"
    payload = _runner_payload(row_count=16, tail_window_size=4)
    summary = payload["future_kernel_native_consumer_dispatch_stub_summary"]
    summary["row_count"] = 12
    summary["row_ok_count"] = 12
    summary["future_kernel_native_dispatch_consumer_row_offset"] = 8
    summary["future_kernel_native_dispatch_consumer_row_limit"] = 12
    _write_json(runner, payload)

    result = check_tail_window_probe(
        runner_json=runner,
        expected_tail_window_size=4,
        min_online_inputs=2,
        min_tail_windowed_inputs=1,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "row_count_input_mismatch"
    ) in result["failures"]


def test_check_tail_window_probe_rejects_cross_field_window_mismatch(
    tmp_path: Path,
):
    runner = tmp_path / "runner.json"
    payload = _runner_payload(row_count=16, tail_window_size=4)
    summary = payload[
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary"
    ]
    summary["future_kernel_native_dispatch_consumer_row_offset"] = 11
    summary["future_kernel_native_dispatch_consumer_row_limit"] = 15
    _write_json(runner, payload)

    result = check_tail_window_probe(
        runner_json=runner,
        expected_tail_window_size=4,
        min_online_inputs=2,
        min_tail_windowed_inputs=1,
    )

    assert result["passed"] is False
    assert "dispatch_summary_offsets_not_consistent" in result["failures"]
    assert "dispatch_summary_limits_not_consistent" in result["failures"]


def test_check_tail_window_probe_rejects_wna16_reinterpretation_flag(
    tmp_path: Path,
):
    runner = tmp_path / "runner.json"
    payload = _runner_payload(row_count=16, tail_window_size=4)
    payload["future_kernel_native_consumer_dispatch_stub_summary"][
        "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation"
    ] = True
    _write_json(runner, payload)

    result = check_tail_window_probe(
        runner_json=runner,
        expected_tail_window_size=4,
        min_online_inputs=2,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation_mismatch"
    ) in result["failures"]


def test_check_tail_window_probe_accepts_exact_tail_window_input(tmp_path: Path):
    runner = tmp_path / "runner.json"
    payload = _runner_payload(row_count=16, tail_window_size=4)
    payload["online_prelaunch_input_row_counts"] = [16, 4]
    payload["online_prelaunch_input_row_count_min"] = 4
    payload["online_prelaunch_input_row_count_max"] = 16
    payload["online_prelaunch_input_row_count_sum"] = 20
    payload["extra_online_input_check_summaries"] = [
        {
            "passed": True,
            "failures": [],
            "outputs": {
                "native_stub_future_kernel_native_consumer_dispatch_abi": {
                    "summary": _dispatch_summary(
                        field_name="scale_metadata_handle",
                        row_count=4,
                        tail_window_size=4,
                    )
                },
                "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror": {
                    "summary": _dispatch_summary(
                        field_name="descriptor_ptr",
                        row_count=4,
                        tail_window_size=4,
                    )
                },
                "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror": {
                    "summary": _dispatch_summary(
                        field_name="packed_weight_descriptor",
                        row_count=4,
                        tail_window_size=4,
                    )
                },
                "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror": {
                    "summary": _dispatch_summary(
                        field_name="aux_metadata_handle",
                        row_count=4,
                        tail_window_size=4,
                    )
                },
            },
        }
    ]
    _write_json(runner, payload)

    result = check_tail_window_probe(
        runner_json=runner,
        expected_tail_window_size=4,
        min_online_inputs=2,
        min_tail_windowed_inputs=1,
    )

    assert result["passed"] is True
    assert result["runner_tail_windowed_input_count"] == 1


def test_check_tail_window_probe_rejects_no_tail_windowed_input(tmp_path: Path):
    runner = tmp_path / "runner.json"
    payload = _runner_payload(row_count=4, tail_window_size=4)
    payload["online_prelaunch_input_row_counts"] = [4, 4]
    payload["online_prelaunch_input_row_count_min"] = 4
    payload["online_prelaunch_input_row_count_max"] = 4
    payload["online_prelaunch_input_row_count_sum"] = 8
    payload["online_prelaunch_input_row_count_diverse"] = False
    payload["extra_online_input_check_summaries"][0]["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_abi"
    ]["summary"] = _dispatch_summary(
        field_name="scale_metadata_handle",
        row_count=4,
        tail_window_size=4,
    )
    payload["extra_online_input_check_summaries"][0]["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror"
    ]["summary"] = _dispatch_summary(
        field_name="descriptor_ptr",
        row_count=4,
        tail_window_size=4,
    )
    payload["extra_online_input_check_summaries"][0]["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror"
    ]["summary"] = _dispatch_summary(
        field_name="packed_weight_descriptor",
        row_count=4,
        tail_window_size=4,
    )
    payload["extra_online_input_check_summaries"][0]["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror"
    ]["summary"] = _dispatch_summary(
        field_name="aux_metadata_handle",
        row_count=4,
        tail_window_size=4,
    )
    _write_json(runner, payload)

    result = check_tail_window_probe(
        runner_json=runner,
        expected_tail_window_size=4,
        min_online_inputs=2,
    )

    assert result["passed"] is False
    assert "runner_tail_windowed_input_count_below_min" in result["failures"]


def test_check_tail_window_probe_rejects_non_positive_thresholds(tmp_path: Path):
    runner = tmp_path / "runner.json"
    _write_json(runner, _runner_payload())

    result = check_tail_window_probe(
        runner_json=runner,
        expected_tail_window_size=0,
        min_online_inputs=0,
        min_tail_windowed_inputs=0,
        require_diverse_row_counts=True,
    )

    assert result["passed"] is False
    assert "expected_tail_window_size_not_positive" in result["failures"]
    assert "min_online_inputs_not_positive" in result["failures"]
    assert "min_tail_windowed_inputs_not_positive" in result["failures"]


def test_check_tail_window_probe_rejects_extra_summary_row_count_mismatch(
    tmp_path: Path,
):
    runner = tmp_path / "runner.json"
    payload = _runner_payload(row_count=16, tail_window_size=4)
    extra_summary = payload["extra_online_input_check_summaries"][0]["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_abi"
    ]["summary"]
    extra_summary["row_count"] = 16
    extra_summary["row_ok_count"] = 16
    extra_summary["future_kernel_native_dispatch_consumer_row_offset"] = 12
    extra_summary["future_kernel_native_dispatch_consumer_row_limit"] = 16
    _write_json(runner, payload)

    result = check_tail_window_probe(
        runner_json=runner,
        expected_tail_window_size=4,
        min_online_inputs=2,
    )

    assert result["passed"] is False
    assert (
        "runner_extra_input_0001_"
        "native_stub_future_kernel_native_consumer_dispatch_abi_"
        "row_count_input_mismatch"
    ) in result["failures"]


def test_check_tail_window_probe_cli_writes_output(tmp_path: Path):
    runner = tmp_path / "runner.json"
    output = tmp_path / "check.json"
    _write_json(runner, _runner_payload())

    assert (
        main(
            [
                "--runner-json",
                str(runner),
                "--expected-tail-window-size",
                "4",
                "--min-online-inputs",
                "2",
                "--min-tail-windowed-inputs",
                "2",
                "--require-diverse-row-counts",
                "--output-json",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_check_tail_window_probe_cli_allows_uniform_row_counts(tmp_path: Path):
    runner = tmp_path / "runner.json"
    output = tmp_path / "check.json"
    payload = _runner_payload(row_count=16, tail_window_size=4)
    payload["online_prelaunch_input_row_counts"] = [16, 16]
    payload["online_prelaunch_input_row_count_min"] = 16
    payload["online_prelaunch_input_row_count_max"] = 16
    payload["online_prelaunch_input_row_count_sum"] = 32
    payload["online_prelaunch_input_row_count_diverse"] = False
    for entry in payload["extra_online_input_check_summaries"][0][
        "outputs"
    ].values():
        entry["summary"] = _dispatch_summary(
            field_name=entry["summary"][
                "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
            ],
            row_count=16,
            tail_window_size=4,
        )
    _write_json(runner, payload)

    assert (
        main(
            [
                "--runner-json",
                str(runner),
                "--expected-tail-window-size",
                "4",
                "--min-online-inputs",
                "2",
                "--min-tail-windowed-inputs",
                "2",
                "--allow-uniform-row-counts",
                "--output-json",
                str(output),
            ]
        )
        == 0
    )
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["runner_online_prelaunch_input_row_count_diverse"] is False


def test_check_tail_window_probe_cli_rejects_uniform_row_counts_by_default(
    tmp_path: Path,
):
    runner = tmp_path / "runner.json"
    output = tmp_path / "check.json"
    payload = _runner_payload(row_count=16, tail_window_size=4)
    payload["online_prelaunch_input_row_counts"] = [16, 16]
    payload["online_prelaunch_input_row_count_min"] = 16
    payload["online_prelaunch_input_row_count_max"] = 16
    payload["online_prelaunch_input_row_count_sum"] = 32
    payload["online_prelaunch_input_row_count_diverse"] = False
    for entry in payload["extra_online_input_check_summaries"][0][
        "outputs"
    ].values():
        entry["summary"] = _dispatch_summary(
            field_name=entry["summary"][
                "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
            ],
            row_count=16,
            tail_window_size=4,
        )
    _write_json(runner, payload)

    assert (
        main(
            [
                "--runner-json",
                str(runner),
                "--expected-tail-window-size",
                "4",
                "--min-online-inputs",
                "2",
                "--min-tail-windowed-inputs",
                "2",
                "--output-json",
                str(output),
            ]
        )
        == 1
    )
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["passed"] is False
    assert "runner_online_input_row_counts_not_diverse" in result["failures"]
