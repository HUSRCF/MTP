from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_premap_online_native_stub_canary import (
    build_parser,
    exported_input_from_performance,
    exported_inputs_from_performance,
    finalize_report_with_artifact_check,
    run_canary,
    trace_output_dir,
)


def test_trace_output_dir_resolves_repo_relative_path(tmp_path: Path, monkeypatch):
    config = tmp_path / "trace.yaml"
    config.write_text("output_dir: outputs/example\n", encoding="utf-8")

    import scripts.run_premap_online_native_stub_canary as canary

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)

    assert trace_output_dir(config) == tmp_path / "outputs/example"


def test_exported_input_from_performance_requires_current_run_path(tmp_path: Path):
    online_input = tmp_path / "online_input.json"
    online_input.write_text("{}\n", encoding="utf-8")
    perf = tmp_path / "performance_summary.json"
    perf.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_native_typed_consumer_input_export_enabled": True,
                "runtime_shadow_premap_native_typed_consumer_input_export_count": 1,
                "runtime_shadow_premap_native_typed_consumer_input_export_first_path": str(
                    online_input
                ),
                "runtime_shadow_premap_native_typed_consumer_input_export_paths": [
                    str(online_input)
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert exported_input_from_performance(perf) == online_input


def test_exported_input_from_performance_rejects_unlisted_first_path(tmp_path: Path):
    online_input = tmp_path / "online_input.json"
    online_input.write_text("{}\n", encoding="utf-8")
    perf = tmp_path / "performance_summary.json"
    perf.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_native_typed_consumer_input_export_enabled": True,
                "runtime_shadow_premap_native_typed_consumer_input_export_count": 1,
                "runtime_shadow_premap_native_typed_consumer_input_export_first_path": str(
                    online_input
                ),
                "runtime_shadow_premap_native_typed_consumer_input_export_paths": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="first_path is not listed"):
        exported_input_from_performance(perf)


def test_exported_inputs_from_performance_selects_multiple_paths(tmp_path: Path):
    inputs = []
    for index in range(3):
        online_input = tmp_path / f"online_input_{index}.json"
        online_input.write_text("{}\n", encoding="utf-8")
        inputs.append(online_input)
    perf = tmp_path / "performance_summary.json"
    perf.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_native_typed_consumer_input_export_enabled": True,
                "runtime_shadow_premap_native_typed_consumer_input_export_count": 3,
                "runtime_shadow_premap_native_typed_consumer_input_export_first_path": str(
                    inputs[0]
                ),
                "runtime_shadow_premap_native_typed_consumer_input_export_paths": [
                    str(path) for path in inputs
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert exported_inputs_from_performance(perf, max_inputs=2) == inputs[:2]
    assert exported_inputs_from_performance(perf, max_inputs=0) == inputs


def test_future_native_dispatch_tail_window_uses_input_row_count(tmp_path: Path):
    import scripts.run_premap_online_native_stub_canary as canary

    input_path = tmp_path / "typed_consumer_input.json"
    input_path.write_text(
        json.dumps({"_meta": {"row_count": 8}, "_export_context": {"row_count": 16}})
        + "\n",
        encoding="utf-8",
    )
    args = build_parser().parse_args(
        [
            "--trace-config",
            str(tmp_path / "trace.yaml"),
            "--future-native-dispatch-row-offset",
            "100",
            "--future-native-dispatch-row-limit",
            "104",
            "--future-native-dispatch-tail-window-size",
            "4",
        ]
    )

    assert canary._typed_consumer_input_row_count(input_path) == 8
    assert canary._future_native_dispatch_extra_args(
        args,
        input_json=input_path,
    ) == [
        "--dispatch-row-offset",
        "4",
        "--dispatch-row-limit",
        "8",
    ]


def test_future_native_dispatch_tail_window_clamps_to_table_head(tmp_path: Path):
    import scripts.run_premap_online_native_stub_canary as canary

    input_path = tmp_path / "typed_consumer_input.json"
    input_path.write_text(
        json.dumps({"_export_context": {"row_count": 3}}) + "\n",
        encoding="utf-8",
    )
    args = build_parser().parse_args(
        [
            "--trace-config",
            str(tmp_path / "trace.yaml"),
            "--future-native-dispatch-tail-window-size",
            "4",
        ]
    )

    assert canary._future_native_dispatch_extra_args(
        args,
        input_json=input_path,
    ) == [
        "--dispatch-row-offset",
        "0",
        "--dispatch-row-limit",
        "3",
    ]


def test_future_native_dispatch_tail_window_supports_dry_run_without_input(
    tmp_path: Path,
):
    import scripts.run_premap_online_native_stub_canary as canary

    args = build_parser().parse_args(
        [
            "--trace-config",
            str(tmp_path / "trace.yaml"),
            "--future-native-dispatch-tail-window-size",
            "4",
            "--dry-run",
        ]
    )

    assert canary._future_native_dispatch_extra_args(
        args,
        input_json=tmp_path / "missing_online_input.json",
    ) == [
        "--dispatch-row-offset",
        "0",
        "--dispatch-row-limit",
        "4",
    ]


def test_run_canary_dry_run_includes_compact_preflight_status(
    tmp_path: Path,
    monkeypatch,
):
    config = tmp_path / "trace.yaml"
    config.write_text("output_dir: outputs/example\n", encoding="utf-8")

    import scripts.run_premap_online_native_stub_canary as canary

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    status_output = tmp_path / "status.json"
    args = build_parser().parse_args(
        [
            "--trace-config",
            str(config),
            "--stub-output-json",
            str(tmp_path / "stub.json"),
            "--per-field-stub-output-json",
            str(tmp_path / "stub_per_field.json"),
            "--envelope-mirror-stub-output-json",
            str(tmp_path / "stub_envelope_mirror.json"),
            "--packed-weight-mirror-stub-output-json",
            str(tmp_path / "stub_packed_weight_mirror.json"),
            "--aux-metadata-mirror-stub-output-json",
            str(tmp_path / "stub_aux_metadata_mirror.json"),
            "--descriptor-ptr-mirror-stub-output-json",
            str(tmp_path / "stub_descriptor_ptr_mirror.json"),
            "--future-kernel-args-stub-output-json",
            str(tmp_path / "stub_future_kernel_args.json"),
            "--future-kernel-native-consumer-stub-output-json",
            str(tmp_path / "stub_future_native_consumer.json"),
            "--future-kernel-native-consumer-launch-stub-output-json",
            str(tmp_path / "stub_future_native_consumer_launch.json"),
            "--future-kernel-native-consumer-dispatch-stub-output-json",
            str(tmp_path / "stub_future_native_consumer_dispatch.json"),
            "--future-kernel-native-consumer-dispatch-descriptor-ptr-stub-output-json",
            str(tmp_path / "stub_future_native_consumer_dispatch_descriptor_ptr.json"),
            "--future-kernel-native-consumer-dispatch-packed-weight-stub-output-json",
            str(tmp_path / "stub_future_native_consumer_dispatch_packed_weight.json"),
            "--future-kernel-native-consumer-dispatch-aux-metadata-stub-output-json",
            str(tmp_path / "stub_future_native_consumer_dispatch_aux_metadata.json"),
            "--preflight-output-json",
            str(tmp_path / "preflight.json"),
            "--preflight-status-output-json",
            str(status_output),
            "--output-json",
            str(tmp_path / "runner.json"),
            "--future-native-dispatch-row-offset",
            "1",
            "--future-native-dispatch-row-limit",
            "5",
            "--dry-run",
        ]
    )

    result = run_canary(args)

    assert result["passed"] is True
    assert result["future_native_dispatch_row_offset"] == 1
    assert result["future_native_dispatch_row_limit"] == 5
    assert "future_native_dispatch_tail_window_size" not in result
    assert "preflight_status" in result["steps"]
    assert "native_stub_per_field" in result["steps"]
    assert "native_stub_kernel_envelope_mirror" in result["steps"]
    assert "native_stub_packed_weight_mirror" in result["steps"]
    assert "native_stub_aux_metadata_mirror" in result["steps"]
    assert "native_stub_descriptor_ptr_mirror" in result["steps"]
    assert "native_stub_future_kernel_consumer_args" in result["steps"]
    assert "native_stub_future_kernel_native_consumer_abi" in result["steps"]
    assert "native_stub_future_kernel_native_consumer_launch_abi" in result["steps"]
    assert (
        "native_stub_future_kernel_native_consumer_launch_descriptor_ptr_mirror"
        in result["steps"]
    )
    assert (
        "native_stub_future_kernel_native_consumer_launch_packed_weight_mirror"
        in result["steps"]
    )
    assert (
        "native_stub_future_kernel_native_consumer_launch_aux_metadata_mirror"
        in result["steps"]
    )
    assert "native_stub_future_kernel_native_consumer_dispatch_abi" in result["steps"]
    assert (
        "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror"
        in result["steps"]
    )
    assert (
        "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror"
        in result["steps"]
    )
    assert (
        "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror"
        in result["steps"]
    )
    assert result["preflight_status_output_json"] == str(status_output)
    per_field_cmd = result["steps"]["native_stub_per_field"]["cmd"]
    assert str(tmp_path / "stub_per_field.json") in per_field_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR" in per_field_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY" not in per_field_cmd
    envelope_cmd = result["steps"]["native_stub_kernel_envelope_mirror"]["cmd"]
    assert str(tmp_path / "stub_envelope_mirror.json") in envelope_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE" in envelope_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD" in envelope_cmd
    packed_cmd = result["steps"]["native_stub_packed_weight_mirror"]["cmd"]
    assert str(tmp_path / "stub_packed_weight_mirror.json") in packed_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD" in packed_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD" not in packed_cmd
    aux_cmd = result["steps"]["native_stub_aux_metadata_mirror"]["cmd"]
    assert str(tmp_path / "stub_aux_metadata_mirror.json") in aux_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD" in aux_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD" not in aux_cmd
    descriptor_cmd = result["steps"]["native_stub_descriptor_ptr_mirror"]["cmd"]
    assert str(tmp_path / "stub_descriptor_ptr_mirror.json") in descriptor_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD" in descriptor_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD" not in descriptor_cmd
    future_args_cmd = result["steps"]["native_stub_future_kernel_consumer_args"]["cmd"]
    assert str(tmp_path / "stub_future_kernel_args.json") in future_args_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS" in future_args_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD" in future_args_cmd
    future_native_cmd = result["steps"]["native_stub_future_kernel_native_consumer_abi"]["cmd"]
    assert str(tmp_path / "stub_future_native_consumer.json") in future_native_cmd
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI"
        in future_native_cmd
    )
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD" in future_native_cmd
    future_native_launch_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_launch_abi"
    ]["cmd"]
    assert str(tmp_path / "stub_future_native_consumer_launch.json") in (
        future_native_launch_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI"
        in future_native_launch_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI"
        in future_native_launch_cmd
    )
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD" in (
        future_native_launch_cmd
    )
    assert "--dispatch-row-offset" not in future_native_launch_cmd
    assert "--dispatch-row-limit" not in future_native_launch_cmd
    future_native_dispatch_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_dispatch_abi"
    ]["cmd"]
    assert str(tmp_path / "stub_future_native_consumer_dispatch.json") in (
        future_native_dispatch_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI"
        in future_native_dispatch_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI"
        in future_native_dispatch_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI"
        in future_native_dispatch_cmd
    )
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD" in (
        future_native_dispatch_cmd
    )
    assert "--dispatch-row-offset" in future_native_dispatch_cmd
    assert "1" in future_native_dispatch_cmd
    assert "--dispatch-row-limit" in future_native_dispatch_cmd
    assert "5" in future_native_dispatch_cmd
    future_native_dispatch_descriptor_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror"
    ]["cmd"]
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI"
        in future_native_dispatch_descriptor_cmd
    )
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD" in (
        future_native_dispatch_descriptor_cmd
    )
    assert "--dispatch-row-offset" in future_native_dispatch_descriptor_cmd
    assert "--dispatch-row-limit" in future_native_dispatch_descriptor_cmd
    future_native_dispatch_packed_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror"
    ]["cmd"]
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI"
        in future_native_dispatch_packed_cmd
    )
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD" in (
        future_native_dispatch_packed_cmd
    )
    assert "--dispatch-row-offset" in future_native_dispatch_packed_cmd
    assert "--dispatch-row-limit" in future_native_dispatch_packed_cmd
    future_native_dispatch_aux_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror"
    ]["cmd"]
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI"
        in future_native_dispatch_aux_cmd
    )
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD" in (
        future_native_dispatch_aux_cmd
    )
    assert "--dispatch-row-offset" in future_native_dispatch_aux_cmd
    assert "--dispatch-row-limit" in future_native_dispatch_aux_cmd
    future_native_launch_descriptor_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_launch_descriptor_ptr_mirror"
    ]["cmd"]
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI" in (
        future_native_launch_descriptor_cmd
    )
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD" in (
        future_native_launch_descriptor_cmd
    )
    assert (
        "--defer-online-prelaunch-runner-evidence"
        in result["steps"]["preflight"]["cmd"]
    )
    assert (
        "--defer-online-prelaunch-artifact-evidence"
        in result["steps"]["preflight"]["cmd"]
    )
    assert "--allow-bootstrap-preflight" in result["steps"]["preflight"]["cmd"]
    assert "--summary-only" in result["steps"]["preflight_status"]["cmd"]
    assert (
        "--defer-online-prelaunch-runner-evidence"
        in result["steps"]["preflight_status"]["cmd"]
    )
    assert (
        "--defer-online-prelaunch-artifact-evidence"
        in result["steps"]["preflight_status"]["cmd"]
    )
    assert (
        "--allow-bootstrap-preflight"
        in result["steps"]["preflight_status"]["cmd"]
    )
    assert "runtime_gate_evidence_deferred_count" in result["preflight_status_summary"]


def test_run_canary_dry_run_includes_explicit_tail_window_size(
    tmp_path: Path,
    monkeypatch,
):
    config = tmp_path / "trace.yaml"
    config.write_text("output_dir: outputs/example\n", encoding="utf-8")

    import scripts.run_premap_online_native_stub_canary as canary

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    args = build_parser().parse_args(
        [
            "--trace-config",
            str(config),
            "--future-native-dispatch-tail-window-size",
            "4",
            "--dry-run",
        ]
    )

    result = run_canary(args)

    assert result["passed"] is True
    assert result["future_native_dispatch_tail_window_size"] == 4
    dispatch_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_dispatch_abi"
    ]["cmd"]
    assert "--dispatch-row-offset" in dispatch_cmd
    assert "0" in dispatch_cmd
    assert "--dispatch-row-limit" in dispatch_cmd
    assert "4" in dispatch_cmd
    assert (
        "strict_default_gate_evidence_deferred_count"
        in result["preflight_status_summary"]
    )
    assert "optional_evidence_present_count" in result["preflight_status_summary"]


def test_finalize_report_with_artifact_check_records_summary(
    tmp_path: Path,
    monkeypatch,
):
    import scripts.run_premap_online_native_stub_canary as canary

    artifact_output = tmp_path / "artifact_check.json"

    def fake_run(cmd, *, env, dry_run, allow_failure=False):
        assert "scripts/check_premap_online_native_stub_canary_artifacts.py" in cmd
        assert dry_run is False
        assert allow_failure is True
        assert env["PYTHONPATH"].startswith(str(tmp_path))
        output_index = cmd.index("--output-json") + 1
        assert Path(cmd[output_index]) == artifact_output
        assert "--require-all-field-mirror-stubs" in cmd
        min_index = cmd.index("--min-online-inputs") + 1
        assert cmd[min_index] == "1"
        artifact_output.write_text(
            json.dumps(
                {
                    "passed": True,
                    "failures": [],
                    "runner_stub_row_count": 4,
                    "runner_stub_row_ok_count": 4,
                    "require_all_field_mirror_stubs": True,
                    "min_online_inputs": 1,
                    "runner_online_prelaunch_input_check_count": 1,
                    "runner_online_prelaunch_input_extra_check_count": 0,
                    "runner_online_prelaunch_input_extra_check_passed_count": 0,
                    "runner_descriptor_ptr_mirror_stub_row_count": 4,
                    "runner_descriptor_ptr_mirror_stub_row_ok_count": 4,
                    "runner_packed_weight_mirror_stub_row_count": 4,
                    "runner_packed_weight_mirror_stub_row_ok_count": 4,
                    "runner_kernel_envelope_mirror_stub_row_count": 4,
                    "runner_kernel_envelope_mirror_stub_row_ok_count": 4,
                    "runner_aux_metadata_mirror_stub_row_count": 4,
                    "runner_aux_metadata_mirror_stub_row_ok_count": 4,
                    "runner_kernel_side_compatible_stub_row_count": 4,
                    "runner_kernel_side_compatible_stub_row_ok_count": 4,
                    "runner_future_kernel_args_stub_row_count": 4,
                    "runner_future_kernel_args_stub_row_ok_count": 4,
                    "runner_future_kernel_args_descriptor_ptr_stub_row_count": 4,
                    "runner_future_kernel_args_descriptor_ptr_stub_row_ok_count": 4,
                    "runner_future_kernel_args_packed_weight_stub_row_count": 4,
                    "runner_future_kernel_args_packed_weight_stub_row_ok_count": 4,
                    "runner_future_kernel_args_aux_metadata_stub_row_count": 4,
                    "runner_future_kernel_args_aux_metadata_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_packed_weight_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_packed_weight_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_aux_metadata_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_aux_metadata_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_launch_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_launch_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_row_ok_count": 4,
                    "stage1_deferred_count": 0,
                    "final_deferred_count": 0,
                    "status_deferred_count": 0,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {"cmd": cmd, "returncode": 0}

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(canary, "_run", fake_run)
    args = build_parser().parse_args(
        [
            "--preflight-output-json",
            str(tmp_path / "preflight.json"),
            "--preflight-status-output-json",
            str(tmp_path / "status.json"),
            "--artifact-check-output-json",
            str(artifact_output),
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )
    payload = {"passed": True, "failures": [], "steps": {}}

    result = finalize_report_with_artifact_check(
        args=args,
        payload=payload,
        runner_json=tmp_path / "runner.json",
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["artifact_check_output_json"] == str(artifact_output)
    assert result["artifact_check_summary"] == {
        "passed": True,
        "failures": [],
        "bootstrap_preflight_allowed": False,
        "runner_stub_row_count": 4,
        "runner_stub_row_ok_count": 4,
        "require_all_field_mirror_stubs": True,
        "min_online_inputs": 1,
        "runner_online_prelaunch_input_check_count": 1,
        "runner_online_prelaunch_input_extra_check_count": 0,
        "runner_online_prelaunch_input_extra_check_passed_count": 0,
        "runner_descriptor_ptr_mirror_stub_row_count": 4,
        "runner_descriptor_ptr_mirror_stub_row_ok_count": 4,
        "runner_packed_weight_mirror_stub_row_count": 4,
        "runner_packed_weight_mirror_stub_row_ok_count": 4,
        "runner_kernel_envelope_mirror_stub_row_count": 4,
        "runner_kernel_envelope_mirror_stub_row_ok_count": 4,
        "runner_aux_metadata_mirror_stub_row_count": 4,
        "runner_aux_metadata_mirror_stub_row_ok_count": 4,
        "runner_kernel_side_compatible_stub_row_count": 4,
        "runner_kernel_side_compatible_stub_row_ok_count": 4,
            "runner_future_kernel_args_stub_row_count": 4,
            "runner_future_kernel_args_stub_row_ok_count": 4,
            "runner_future_kernel_args_descriptor_ptr_stub_row_count": 4,
            "runner_future_kernel_args_descriptor_ptr_stub_row_ok_count": 4,
            "runner_future_kernel_args_packed_weight_stub_row_count": 4,
            "runner_future_kernel_args_packed_weight_stub_row_ok_count": 4,
            "runner_future_kernel_args_aux_metadata_stub_row_count": 4,
            "runner_future_kernel_args_aux_metadata_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_stub_row_count": 4,
            "runner_future_kernel_native_consumer_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_count": 4,
            "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_packed_weight_stub_row_count": 4,
            "runner_future_kernel_native_consumer_packed_weight_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_aux_metadata_stub_row_count": 4,
            "runner_future_kernel_native_consumer_aux_metadata_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_launch_stub_row_count": 4,
            "runner_future_kernel_native_consumer_launch_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_count": 4,
            "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_count": 4,
            "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_count": 4,
            "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_dispatch_stub_row_count": 4,
            "runner_future_kernel_native_consumer_dispatch_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_count": 4,
            "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_count": 4,
            "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_count": 4,
            "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_count": 4,
            "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_row_count": 4,
            "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_row_ok_count": 4,
            "stage1_deferred_count": 0,
            "final_deferred_count": 0,
            "status_deferred_count": 0,
    }
    assert "artifact_check_final" in result["steps"]
    assert "artifact_check_bootstrap" not in result["steps"]


def test_finalize_report_with_artifact_check_records_failure_without_raising(
    tmp_path: Path,
    monkeypatch,
):
    import scripts.run_premap_online_native_stub_canary as canary

    artifact_output = tmp_path / "artifact_check.json"

    def fake_run(cmd, *, env, dry_run, allow_failure=False):
        assert allow_failure is True
        artifact_output.write_text(
            json.dumps(
                {
                    "passed": False,
                    "failures": ["runner_not_passed"],
                    "runner_stub_row_count": 4,
                    "runner_stub_row_ok_count": 4,
                    "stage1_deferred_count": 0,
                    "final_deferred_count": 0,
                    "status_deferred_count": 0,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {"cmd": cmd, "returncode": 1}

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(canary, "_run", fake_run)
    args = build_parser().parse_args(
        [
            "--artifact-check-output-json",
            str(artifact_output),
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )
    payload = {"passed": True, "failures": [], "steps": {}}

    result = finalize_report_with_artifact_check(
        args=args,
        payload=payload,
        runner_json=tmp_path / "runner.json",
    )

    assert result["passed"] is False
    assert result["failures"] == ["artifact_consistency_check_failed"]
    assert result["artifact_check_summary"]["passed"] is False
    assert result["artifact_check_summary"]["failures"] == ["runner_not_passed"]
    assert result["steps"]["artifact_check_final"]["returncode"] == 1
