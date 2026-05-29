from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_online_native_stub_canary_artifacts import (
    check_online_native_stub_canary_artifacts,
    main,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _extra_input_summary(row_count: int = 4) -> dict:
    def stub_summary() -> dict:
        return {
            "passed": True,
            "ok": True,
            "row_count": row_count,
            "row_ok_count": row_count,
            "error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        }

    def mirror_summary(field_name: str, *, envelope: bool = False) -> dict:
        payload = {
            **stub_summary(),
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": field_name,
            "single_field_mirror_row_count": row_count,
            "single_field_mirror_row_ok_count": row_count,
            "single_field_mirror_error_count": 0,
        }
        if envelope:
            payload.update(
                {
                    "kernel_consumer_envelope_checked": True,
                    "kernel_consumer_envelope_payload_bytes": 0,
                    "kernel_consumer_envelope_passed_to_kernel": False,
                }
            )
        return payload

    return {
        "input_index": 1,
        "input_json": "input1.json",
        "passed": True,
        "failures": [],
        "outputs": {
            "native_stub": {"summary": stub_summary()},
            "native_stub_per_field": {"summary": stub_summary()},
            "native_stub_kernel_envelope_mirror": {
                "summary": mirror_summary("scale_metadata_handle", envelope=True)
            },
            "native_stub_packed_weight_mirror": {
                "summary": mirror_summary("packed_weight_descriptor")
            },
            "native_stub_aux_metadata_mirror": {
                "summary": mirror_summary("aux_metadata_handle")
            },
            "native_stub_descriptor_ptr_mirror": {
                "summary": mirror_summary("descriptor_ptr")
            },
        },
    }


def _payloads(root: Path) -> tuple[Path, Path, Path]:
    runner_path = root / "runner.json"
    preflight_path = root / "preflight.json"
    status_path = root / "status.json"
    stage1 = {
        "passed": True,
        "required_evidence_present_count": 9,
        "required_evidence_passed_count": 9,
        "required_evidence_required_count": 10,
        "optional_evidence_present_count": 1,
        "optional_evidence_passed_count": 1,
        "optional_evidence_required_count": 1,
        "optional_evidence_passed": True,
        "runtime_gate_evidence_deferred_count": 1,
        "strict_default_gate_evidence_deferred_count": 1,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    final = {
        "passed": True,
        "required_evidence_present_count": 10,
        "required_evidence_passed_count": 10,
        "required_evidence_required_count": 10,
        "optional_evidence_present_count": 1,
        "optional_evidence_passed_count": 1,
        "optional_evidence_required_count": 1,
        "optional_evidence_passed": True,
        "runtime_gate_evidence_deferred_count": 0,
        "strict_default_gate_evidence_deferred_count": 0,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    runner = {
        "passed": True,
        "failures": [],
        "preflight_output_json": str(preflight_path),
        "preflight_status_output_json": str(status_path),
        "online_prelaunch_input_check_count": 1,
        "online_prelaunch_input_extra_check_count": 0,
        "online_prelaunch_input_extra_check_passed_count": 0,
        "preflight_status_summary": stage1,
        "final_preflight_status_summary": final,
        "stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "per_field_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "kernel_envelope_mirror_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "kernel_consumer_envelope_checked": True,
            "kernel_consumer_envelope_payload_bytes": 0,
            "kernel_consumer_envelope_passed_to_kernel": False,
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": "scale_metadata_handle",
            "single_field_mirror_row_count": 4,
            "single_field_mirror_row_ok_count": 4,
            "single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "packed_weight_mirror_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": "packed_weight_descriptor",
            "single_field_mirror_row_count": 4,
            "single_field_mirror_row_ok_count": 4,
            "single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "aux_metadata_mirror_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": "aux_metadata_handle",
            "single_field_mirror_row_count": 4,
            "single_field_mirror_row_ok_count": 4,
            "single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "descriptor_ptr_mirror_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": "descriptor_ptr",
            "single_field_mirror_row_count": 4,
            "single_field_mirror_row_ok_count": 4,
            "single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
    }
    _write_json(runner_path, runner)
    _write_json(preflight_path, {"passed": True, "failures": []})
    _write_json(
        status_path,
        {
            "passed": True,
            "runtime_gate_evidence_deferred_count": 0,
            "strict_default_gate_evidence_deferred_count": 0,
            "payload_bytes_required": 0,
            "passed_to_kernel_required": False,
            "changes_kernel_launch_args_required": False,
            "required_evidence": {
                "passed": True,
                "present_count": 10,
                "passed_count": 10,
                "required_count": 10,
            },
            "optional_evidence": {
                "passed": True,
                "present_count": 1,
                "passed_count": 1,
                "required_count": 1,
            },
        },
    )
    return runner_path, preflight_path, status_path


def test_check_online_native_stub_canary_artifacts_accepts_consistent_payloads(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["stage1_deferred_count"] == 1
    assert result["final_deferred_count"] == 0
    assert result["status_deferred_count"] == 0
    assert result["require_all_field_mirror_stubs"] is False
    assert result["min_online_inputs"] == 1
    assert result["runner_online_prelaunch_input_check_count"] == 1


def test_check_online_native_stub_canary_artifacts_requires_all_field_mirrors(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner.pop("aux_metadata_mirror_stub_summary")
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        require_all_field_mirror_stubs=True,
    )

    assert result["passed"] is False
    assert result["require_all_field_mirror_stubs"] is True
    assert "runner_aux_metadata_mirror_stub_summary_required" in result["failures"]


def test_check_online_native_stub_canary_artifacts_requires_min_online_inputs(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["online_prelaunch_input_check_count"] = 2
    runner["online_prelaunch_input_extra_check_count"] = 1
    runner["online_prelaunch_input_extra_check_passed_count"] = 1
    runner["extra_online_input_check_summaries"] = [_extra_input_summary()]
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )

    assert result["passed"] is True
    assert result["min_online_inputs"] == 2
    assert result["runner_online_prelaunch_input_check_count"] == 2

    runner["online_prelaunch_input_extra_check_passed_count"] = 0
    _write_json(runner_path, runner)
    failed = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )
    assert failed["passed"] is False
    assert (
        "runner_online_prelaunch_input_extra_check_passed_count_mismatch"
        in failed["failures"]
    )

    runner["online_prelaunch_input_extra_check_passed_count"] = 1
    runner["extra_online_input_check_summaries"] = [
        {**_extra_input_summary(), "passed": False}
    ]
    _write_json(runner_path, runner)
    failed_summary = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )
    assert failed_summary["passed"] is False
    assert "runner_extra_input_0001_not_passed" in failed_summary["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_stale_status_path(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["preflight_status_output_json"] = str(tmp_path / "old_status.json")
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert "runner_preflight_status_output_json_mismatch" in result["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_final_defer(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["runtime_gate_evidence_deferred_count"] = 1
    _write_json(status_path, status)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert "status_runtime_gate_evidence_deferred_count_mismatch" in result["failures"]


def test_check_online_native_stub_canary_artifacts_cli_writes_json(tmp_path: Path):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    output = tmp_path / "check.json"

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--runner-json",
            str(runner_path),
            "--preflight-json",
            str(preflight_path),
            "--status-json",
            str(status_path),
            "--output-json",
            str(output),
            "--require-all-field-mirror-stubs",
            "--min-online-inputs",
            "1",
        ]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["runner_stub_row_count"] == 4
    assert result["runner_per_field_stub_row_count"] == 4
    assert result["runner_kernel_envelope_mirror_stub_row_count"] == 4
    assert result["runner_packed_weight_mirror_stub_row_count"] == 4
    assert result["runner_aux_metadata_mirror_stub_row_count"] == 4
    assert result["runner_descriptor_ptr_mirror_stub_row_count"] == 4
    assert result["require_all_field_mirror_stubs"] is True
    assert result["min_online_inputs"] == 1
    assert result["runner_online_prelaunch_input_check_count"] == 1


def test_check_online_native_stub_canary_artifacts_rejects_per_field_stub_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["per_field_stub_summary"]["row_ok_count"] = 3
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert "runner_per_field_stub_row_ok_count_mismatch" in result["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_packed_mirror_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["packed_weight_mirror_stub_summary"][
        "single_field_mirror_field_name"
    ] = "scale_metadata_handle"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_packed_weight_mirror_stub_single_field_mirror_field_name_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_aux_mirror_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["aux_metadata_mirror_stub_summary"][
        "single_field_mirror_field_name"
    ] = "packed_weight_descriptor"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_aux_metadata_mirror_stub_single_field_mirror_field_name_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_descriptor_mirror_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["descriptor_ptr_mirror_stub_summary"][
        "single_field_mirror_field_name"
    ] = "aux_metadata_handle"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_descriptor_ptr_mirror_stub_single_field_mirror_field_name_mismatch"
        in result["failures"]
    )
