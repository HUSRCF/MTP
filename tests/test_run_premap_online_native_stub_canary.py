from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_premap_online_native_stub_canary import (
    _apply_pointer_source_observer_gate,
    build_parser,
    exported_input_from_performance,
    exported_inputs_from_performance,
    finalize_report_with_artifact_check,
    finalize_report_with_strict_preflight,
    main,
    _pointer_source_observer_check_summary,
    run_canary,
    trace_output_dir,
)
from scripts.check_premap_prelaunch_pointer_source_observer import (
    HANDOFF_BOOL_PREFIX as PRELAUNCH_POINTER_SOURCE_OBSERVER_HANDOFF_BOOL_PREFIX,
    LIVE_MUTATION_COUNTER_PREFIX as PRELAUNCH_POINTER_SOURCE_OBSERVER_LIVE_MUTATION_COUNTER_PREFIX,
    REQUIRED_BOOL_KEYS as PRELAUNCH_POINTER_SOURCE_OBSERVER_REQUIRED_BOOL_KEYS,
    REQUIRED_INT_KEYS as PRELAUNCH_POINTER_SOURCE_OBSERVER_REQUIRED_INT_KEYS,
    ZERO_INT_KEYS as PRELAUNCH_POINTER_SOURCE_OBSERVER_ZERO_INT_KEYS,
)


def test_trace_output_dir_resolves_repo_relative_path(tmp_path: Path, monkeypatch):
    config = tmp_path / "trace.yaml"
    config.write_text("output_dir: outputs/example\n", encoding="utf-8")

    import scripts.run_premap_online_native_stub_canary as canary

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)

    assert trace_output_dir(config) == tmp_path / "outputs/example"


def _pointer_source_observer_check_payload(**overrides) -> dict[str, object]:
    required_bool_values = {
        key: False for key in PRELAUNCH_POINTER_SOURCE_OBSERVER_REQUIRED_BOOL_KEYS
    }
    required_bool_values[
        "runtime_shadow_premap_live_config_without_router_recorder_enabled"
    ] = True
    required_bool_values[
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled"
    ] = True

    required_int_values = {
        key: 0 for key in PRELAUNCH_POINTER_SOURCE_OBSERVER_REQUIRED_INT_KEYS
    }
    required_int_values["sample_count"] = 16
    required_int_values["requested_output_token_count"] = 1024
    required_int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count"
    ] = 2560
    required_int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count"
    ] = 2560
    required_int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count"
    ] = 2560

    payload: dict[str, object] = {
        "mode": "premap_prelaunch_pointer_source_observer_check",
        "passed": True,
        "failures": [],
        "min_seen": 128,
        "observer_seen": 2560,
        "observer_available": 2560,
        "observer_vllm_device": 2560,
        "observer_unavailable": 0,
        "observer_non_device": 0,
        "min_sample_count": 16,
        "sample_count": 16,
        "min_requested_output_tokens": 1024,
        "requested_output_token_count": 1024,
        "live_handoff_enabled": False,
        "live_consumer_connected": False,
        "kernel_arg_pass_enabled": False,
        "real_kernel_arg_mutation_enabled": False,
        "producer_gpu_assignment_envelope_enabled": False,
        "live_config_without_router_recorder_enabled": True,
        "prelaunch_pointer_source_canary_enabled": True,
        "required_bool_values": required_bool_values,
        "required_int_values": required_int_values,
        "handoff_bool_values": {
            key: value
            for key, value in required_bool_values.items()
            if key.startswith(PRELAUNCH_POINTER_SOURCE_OBSERVER_HANDOFF_BOOL_PREFIX)
        },
        "live_mutation_counter_values": {
            key: value
            for key, value in required_int_values.items()
            if key.startswith(
                PRELAUNCH_POINTER_SOURCE_OBSERVER_LIVE_MUTATION_COUNTER_PREFIX
            )
        },
        "zero_counter_values": {
            key: required_int_values[key]
            for key in PRELAUNCH_POINTER_SOURCE_OBSERVER_ZERO_INT_KEYS
        },
    }
    payload.update(overrides)
    return payload


def test_pointer_source_observer_check_summary_accepts_valid_artifact(tmp_path: Path):
    artifact = tmp_path / "observer.check.json"
    artifact.write_text(
        json.dumps(_pointer_source_observer_check_payload()) + "\n",
        encoding="utf-8",
    )

    summary = _pointer_source_observer_check_summary(artifact, required=True)

    assert summary["present"] is True
    assert summary["passed"] is True
    assert summary["observer_vllm_device"] == 2560


def test_pointer_source_observer_check_summary_rejects_missing_required_artifact(
    tmp_path: Path,
):
    summary = _pointer_source_observer_check_summary(
        tmp_path / "missing.check.json",
        required=True,
    )

    assert summary["present"] is False
    assert summary["passed"] is False
    assert summary["failures"] == ["pointer_source_observer_check_missing"]


def test_pointer_source_observer_check_summary_optional_missing_is_not_evidence_passed(
    tmp_path: Path,
):
    summary = _pointer_source_observer_check_summary(
        tmp_path / "missing.check.json",
        required=False,
    )

    assert summary["present"] is False
    assert summary["passed"] is False
    assert summary["gate_passed"] is True


def test_pointer_source_observer_check_summary_bad_json_fails_without_crash(
    tmp_path: Path,
):
    artifact = tmp_path / "observer.check.json"
    artifact.write_text("{bad-json", encoding="utf-8")

    summary = _pointer_source_observer_check_summary(artifact, required=False)

    assert summary["present"] is True
    assert summary["passed"] is False
    assert summary["gate_passed"] is False
    assert summary["failures"]


def test_pointer_source_observer_check_summary_bad_utf8_fails_without_crash(
    tmp_path: Path,
):
    artifact = tmp_path / "observer.check.json"
    artifact.write_bytes(b"\xff")

    summary = _pointer_source_observer_check_summary(artifact, required=False)

    assert summary["present"] is True
    assert summary["passed"] is False
    assert summary["gate_passed"] is False
    assert summary["failures"]


def test_pointer_source_observer_check_summary_rejects_bad_artifact(tmp_path: Path):
    artifact = tmp_path / "observer.check.json"
    payload = _pointer_source_observer_check_payload()
    payload["handoff_bool_values"] = {}
    artifact.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    summary = _pointer_source_observer_check_summary(artifact, required=True)

    assert summary["present"] is True
    assert summary["passed"] is False
    assert (
        "prelaunch_pointer_source_observer_handoff_bool_map_truncated"
        in summary["failures"]
    )


def test_run_canary_requires_pointer_source_observer_check_in_dry_run(tmp_path: Path):
    trace_config = tmp_path / "trace.yaml"
    trace_config.write_text("output_dir: outputs/example\n", encoding="utf-8")
    args = build_parser().parse_args(
        [
            "--dry-run",
            "--require-pointer-source-observer-check",
            "--pointer-source-observer-check-json",
            str(tmp_path / "missing.check.json"),
            "--trace-config",
            str(trace_config),
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )

    result = run_canary(args)

    assert result["passed"] is False
    assert result["failures"] == ["pointer_source_observer_check_not_passed"]
    assert result["pointer_source_observer_check_required"] is True
    assert result["pointer_source_observer_check"]["present"] is False


def test_pointer_source_observer_gate_rejects_existing_payload_when_required_missing(
    tmp_path: Path,
):
    args = build_parser().parse_args(
        [
            "--dry-run",
            "--require-pointer-source-observer-check",
            "--pointer-source-observer-check-json",
            str(tmp_path / "missing.check.json"),
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )
    payload = {"passed": True, "failures": []}

    result = _apply_pointer_source_observer_gate(payload, args)

    assert result["passed"] is False
    assert result["failures"] == ["pointer_source_observer_check_not_passed"]
    assert result["pointer_source_observer_check_required"] is True
    assert result["pointer_source_observer_gate_passed"] is False


def test_pointer_source_observer_gate_preserves_existing_payload_when_valid(
    tmp_path: Path,
):
    artifact = tmp_path / "observer.check.json"
    artifact.write_text(
        json.dumps(_pointer_source_observer_check_payload()) + "\n",
        encoding="utf-8",
    )
    args = build_parser().parse_args(
        [
            "--dry-run",
            "--require-pointer-source-observer-check",
            "--pointer-source-observer-check-json",
            str(artifact),
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )
    payload = {"passed": True, "failures": []}

    result = _apply_pointer_source_observer_gate(payload, args)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["pointer_source_observer_check_passed"] is True
    assert result["pointer_source_observer_gate_passed"] is True


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


def test_run_canary_rejects_too_few_exported_inputs_before_stub(
    tmp_path: Path,
    monkeypatch,
):
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    config = tmp_path / "trace.yaml"
    config.write_text(f"output_dir: {trace_dir}\n", encoding="utf-8")
    online_input = trace_dir / "input0.json"
    online_input.write_text("{}\n", encoding="utf-8")
    (trace_dir / "performance_summary.json").write_text(
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

    import scripts.run_premap_online_native_stub_canary as canary

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return {"cmd": cmd, "returncode": 0}

    monkeypatch.setattr(canary, "_run", fake_run)
    args = build_parser().parse_args(
        [
            "--trace-config",
            str(config),
            "--skip-trace",
            "--min-artifact-online-inputs",
            "2",
            "--max-online-inputs",
            "2",
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )

    with pytest.raises(ValueError, match="not enough exported online typed-consumer"):
        run_canary(args)
    assert calls == []


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


def test_future_native_projection_hashchain_includes_consumer_view():
    import scripts.run_premap_online_native_stub_canary as canary

    payload = {
        "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator": "abc",
    }

    assert canary._future_native_handle_projection_hashchain_equal(payload) is True

    payload[
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator"
    ] = "abd"
    assert canary._future_native_handle_projection_hashchain_equal(payload) is False

    payload[
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator"
    ] = "not_hex"
    assert canary._future_native_handle_projection_hashchain_equal(payload) is False


def test_existing_stub_reuse_requires_matching_dispatch_window(tmp_path: Path):
    import scripts.run_premap_online_native_stub_canary as canary

    output = tmp_path / "stub.json"
    input_json = tmp_path / "input.json"
    input_json.write_text("{}\n", encoding="utf-8")
    macros = [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
        "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
    ]
    output.write_text(
        json.dumps(
            {
                "passed": True,
                "requested_macros": macros,
                "offload_arch": "gfx1100",
                "input_json": str(input_json),
                "requested_dispatch_row_offset": 1,
                "requested_dispatch_row_limit": 5,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    matching_cmd = [
        "python",
        "scripts/run_premap_typed_consumer_stub.py",
        "--input-json",
        str(input_json),
        "--offload-arch",
        "gfx1100",
        "--output-json",
        str(output),
        "--macro",
        macros[0],
        "--macro",
        macros[1],
        "--dispatch-row-offset",
        "1",
        "--dispatch-row-limit",
        "5",
    ]
    mismatched_cmd = [
        "python",
        "scripts/run_premap_typed_consumer_stub.py",
        "--input-json",
        str(input_json),
        "--offload-arch",
        "gfx1100",
        "--output-json",
        str(output),
        "--macro",
        macros[0],
        "--macro",
        macros[1],
        "--dispatch-row-offset",
        "0",
        "--dispatch-row-limit",
        "5",
    ]
    full_table_cmd = [
        "python",
        "scripts/run_premap_typed_consumer_stub.py",
        "--input-json",
        str(input_json),
        "--offload-arch",
        "gfx1100",
        "--output-json",
        str(output),
        "--macro",
        macros[0],
        "--macro",
        macros[1],
    ]
    mismatched_macro_cmd = matching_cmd + [
        "--macro",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI",
    ]

    assert canary._can_reuse_existing_stub_output(matching_cmd, output) is True
    assert canary._can_reuse_existing_stub_output(mismatched_cmd, output) is False
    assert canary._can_reuse_existing_stub_output(full_table_cmd, output) is False
    assert canary._can_reuse_existing_stub_output(mismatched_macro_cmd, output) is False


def test_existing_stub_reuse_accepts_matching_full_table_output(tmp_path: Path):
    import scripts.run_premap_online_native_stub_canary as canary

    output = tmp_path / "stub.json"
    input_json = tmp_path / "input.json"
    input_json.write_text("{}\n", encoding="utf-8")
    macros = ["MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA"]
    output.write_text(
        json.dumps(
            {
                "passed": True,
                "requested_macros": macros,
                "offload_arch": "gfx1100",
                "input_json": str(input_json),
                "requested_dispatch_row_offset": 0,
                "requested_dispatch_row_limit": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cmd = [
        "python",
        "scripts/run_premap_typed_consumer_stub.py",
        "--input-json",
        str(input_json),
        "--offload-arch",
        "gfx1100",
        "--output-json",
        str(output),
        "--macro",
        macros[0],
    ]

    assert canary._can_reuse_existing_stub_output(cmd, output) is True


def test_existing_stub_reuse_rejects_legacy_output_without_window(tmp_path: Path):
    import scripts.run_premap_online_native_stub_canary as canary

    output = tmp_path / "stub.json"
    output.write_text(json.dumps({"passed": True}) + "\n", encoding="utf-8")
    cmd = [
        "python",
        "scripts/run_premap_typed_consumer_stub.py",
        "--output-json",
        str(output),
    ]

    assert canary._can_reuse_existing_stub_output(cmd, output) is False


def test_run_canary_dry_run_includes_compact_preflight_status(
    tmp_path: Path,
    monkeypatch,
):
    config = tmp_path / "trace.yaml"
    config.write_text("output_dir: outputs/example\n", encoding="utf-8")

    import scripts.run_premap_online_native_stub_canary as canary

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    status_output = tmp_path / "status.json"
    status_check_output = tmp_path / "status.check.json"
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
            "--future-kernel-native-consumer-request-ptr-stub-output-json",
            str(tmp_path / "stub_future_native_consumer_request_ptr.json"),
            "--future-kernel-native-consumer-request-launch-stub-output-json",
            str(tmp_path / "stub_future_native_consumer_request_launch.json"),
            "--future-kernel-native-consumer-request-launch-ptr-stub-output-json",
            str(tmp_path / "stub_future_native_consumer_request_launch_ptr.json"),
            "--preflight-output-json",
            str(tmp_path / "preflight.json"),
            "--preflight-status-output-json",
            str(status_output),
            "--preflight-status-check-output-json",
            str(status_check_output),
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
    assert "native_stub_future_kernel_native_consumer_request_ptr_abi" in result["steps"]
    assert "native_stub_future_kernel_native_consumer_request_launch_abi" in result["steps"]
    assert (
        "native_stub_future_kernel_native_consumer_request_launch_ptr_abi"
        in result["steps"]
    )
    assert "future_kernel_native_consumer_dispatch_arg_slot_stub_summary" in result
    assert (
        "future_kernel_native_arg_slot_consumer_row_count"
        in result["future_kernel_native_consumer_dispatch_arg_slot_stub_summary"]
    )
    assert "future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_summary" in result
    assert (
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count"
        in result[
            "future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_summary"
        ]
    )
    assert result["preflight_status_output_json"] == str(status_output)
    assert result["preflight_status_check_output_json"] == str(status_check_output)
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
    future_native_request_ptr_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_request_ptr_abi"
    ]["cmd"]
    assert str(tmp_path / "stub_future_native_consumer_request_ptr.json") in (
        future_native_request_ptr_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI"
        in future_native_request_ptr_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI"
        in future_native_request_ptr_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI"
        not in future_native_request_ptr_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI"
        not in future_native_request_ptr_cmd
    )
    future_native_request_launch_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_request_launch_abi"
    ]["cmd"]
    assert str(tmp_path / "stub_future_native_consumer_request_launch.json") in (
        future_native_request_launch_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI"
        in future_native_request_launch_cmd
    )
    future_native_request_launch_ptr_cmd = result["steps"][
        "native_stub_future_kernel_native_consumer_request_launch_ptr_abi"
    ]["cmd"]
    assert str(tmp_path / "stub_future_native_consumer_request_launch_ptr.json") in (
        future_native_request_launch_ptr_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI"
        in future_native_request_launch_ptr_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI"
        not in future_native_request_launch_ptr_cmd
    )
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI"
        not in future_native_request_launch_ptr_cmd
    )
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


def test_run_canary_rejects_request_launch_ptr_hash_mismatch(
    tmp_path: Path,
    monkeypatch,
):
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    config = tmp_path / "trace.yaml"
    config.write_text(f"output_dir: {trace_dir}\n", encoding="utf-8")
    input_json = trace_dir / "online_input.json"
    input_json.write_text(json.dumps({"row_count": 2}) + "\n", encoding="utf-8")
    (trace_dir / "performance_summary.json").write_text(
        json.dumps(
            {
                "runtime_shadow_premap_native_typed_consumer_input_export_enabled": True,
                "runtime_shadow_premap_native_typed_consumer_input_export_count": 1,
                "runtime_shadow_premap_native_typed_consumer_input_export_first_path": str(
                    input_json
                ),
                "runtime_shadow_premap_native_typed_consumer_input_export_paths": [
                    str(input_json)
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    import scripts.run_premap_online_native_stub_canary as canary

    row_hash = "1234567890abcdef"
    bad_row_hash = "fedcba0987654321"
    field_read_hash = "0fedcba987654321"
    row_metadata_hash = "55aa55aa55aa55aa"

    def add_summary(payload: dict[str, object], prefix: str, *, hash_value: str):
        payload.update(
            {
                f"{prefix}_row_count": 2,
                f"{prefix}_row_ok_count": 2,
                f"{prefix}_error_count": 0,
                f"{prefix}_field_mask": 15,
                f"{prefix}_descriptor_ptr_read_row_ok_count": 2,
                f"{prefix}_packed_weight_descriptor_read_row_ok_count": 2,
                f"{prefix}_scale_metadata_handle_read_row_ok_count": 2,
                f"{prefix}_aux_metadata_handle_read_row_ok_count": 2,
                f"{prefix}_expert_id_read_row_ok_count": 2,
                f"{prefix}_address_key_hash_read_row_ok_count": 2,
                f"{prefix}_row_metadata_read_row_ok_count": 2,
                f"{prefix}_row_hash_accumulator": hash_value,
                f"{prefix}_field_read_hash_accumulator": field_read_hash,
                f"{prefix}_row_metadata_hash_accumulator": row_metadata_hash,
            }
        )

    request_launch_ptr_payload: dict[str, object] = {
        "passed": True,
        "ok": True,
        "row_count": 2,
        "row_ok_count": 2,
        "error_count": 0,
        "input_json": str(input_json),
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "future_kernel_native_consumer_request_launch_ptr_abi_name": (
            "premap_future_kernel_native_consumer_request_launch_ptr_abi_v1"
        ),
        "future_kernel_native_consumer_request_launch_ptr_mode": (
            "readonly_future_kernel_native_consumer_request_launch_ptr_abi"
        ),
        "future_kernel_native_consumer_request_launch_ptr_source": (
            "premap_future_kernel_native_consumer_request_launch_abi_v1"
        ),
        "future_kernel_native_consumer_request_launch_ptr_field_read_path": (
            "request_launch_ptr_to_request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        "future_kernel_native_consumer_request_launch_ptr_checked": True,
        "future_kernel_native_consumer_request_launch_ptr_version": 1,
        "future_kernel_native_consumer_request_launch_ptr_packet_chain_depth": 6,
        "future_kernel_native_consumer_request_launch_ptr_pointer_size": 8,
        "future_kernel_native_consumer_request_launch_ptr_request_id": 1,
        "future_kernel_native_consumer_request_launch_ptr_payload_bytes": 0,
        "future_kernel_native_consumer_request_launch_ptr_payload_deref_allowed": False,
        "future_kernel_native_consumer_request_launch_ptr_passed_to_kernel": False,
        "future_kernel_native_consumer_request_launch_ptr_kernel_arg_pass_allowed": False,
        "future_kernel_native_consumer_request_launch_ptr_changes_kernel_launch_args": False,
        "future_kernel_native_consumer_request_launch_ptr_current_wna16_arg_compatible": False,
        "future_kernel_native_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation": False,
    }
    add_summary(
        request_launch_ptr_payload,
        "future_kernel_native_consumer_request_launch_ptr_summary",
        hash_value=bad_row_hash,
    )
    for prefix in (
        "future_kernel_native_consumer_request_launch_summary",
        "future_kernel_native_consumer_request_ptr_summary",
        "future_kernel_native_consumer_kernel_entry_summary",
    ):
        add_summary(request_launch_ptr_payload, prefix, hash_value=row_hash)

    def fake_run(cmd, *, env, dry_run, allow_failure=False):
        return {"cmd": cmd, "returncode": 0}

    def fake_load(path: Path):
        path_str = str(path)
        if path_str.endswith("request_launch_ptr.json"):
            return request_launch_ptr_payload
        if path_str.endswith("stub.json"):
            return {"passed": True, "input_json": str(input_json)}
        if path_str.endswith("preflight.json") or path_str.endswith("status.json"):
            return {"passed": True}
        return {}

    monkeypatch.setattr(canary, "_run", fake_run)
    monkeypatch.setattr(canary, "_load_json_if_exists", fake_load)
    args = build_parser().parse_args(
        [
            "--trace-config",
            str(config),
            "--skip-trace",
            "--stub-output-json",
            str(tmp_path / "stub.json"),
            "--future-kernel-native-consumer-request-launch-ptr-stub-output-json",
            str(tmp_path / "request_launch_ptr.json"),
            "--preflight-output-json",
            str(tmp_path / "preflight.json"),
            "--preflight-status-output-json",
            str(tmp_path / "status.json"),
            "--output-json",
            str(tmp_path / "runner.json"),
            "--skip-per-field-stub",
            "--skip-envelope-mirror-stub",
            "--skip-packed-weight-mirror-stub",
            "--skip-aux-metadata-mirror-stub",
            "--skip-descriptor-ptr-mirror-stub",
            "--skip-kernel-side-compatible-stub",
            "--skip-future-kernel-args-stub",
            "--skip-future-kernel-args-extra-field-stubs",
            "--skip-future-kernel-args-compatible-path-stub",
            "--skip-future-kernel-native-consumer-stub",
            "--skip-future-kernel-native-consumer-extra-field-stubs",
            "--skip-future-kernel-native-consumer-request-ptr-stub",
            "--skip-future-kernel-native-consumer-request-launch-stub",
            "--skip-artifact-check",
        ]
    )

    result = run_canary(args)

    assert result["passed"] is False
    assert (
        "native_stub_future_native_request_launch_ptr_row_hash_mismatch"
        in result["failures"]
    )


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
                    "runner_online_prelaunch_input_row_counts": [4],
                    "runner_online_prelaunch_input_row_count_min": 4,
                    "runner_online_prelaunch_input_row_count_max": 4,
                    "runner_online_prelaunch_input_row_count_sum": 4,
                    "runner_online_prelaunch_input_row_count_diverse": False,
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
                    "runner_future_kernel_native_consumer_request_ptr_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_request_ptr_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_request_launch_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_request_launch_stub_row_ok_count": 4,
                    "runner_future_kernel_native_consumer_request_launch_ptr_stub_row_count": 4,
                    "runner_future_kernel_native_consumer_request_launch_ptr_stub_row_ok_count": 4,
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
        "runner_online_prelaunch_input_row_counts": [4],
        "runner_online_prelaunch_input_row_count_min": 4,
        "runner_online_prelaunch_input_row_count_max": 4,
        "runner_online_prelaunch_input_row_count_sum": 4,
        "runner_online_prelaunch_input_row_count_diverse": False,
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
            "runner_future_kernel_native_consumer_request_ptr_stub_row_count": 4,
            "runner_future_kernel_native_consumer_request_ptr_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_request_launch_stub_row_count": 4,
            "runner_future_kernel_native_consumer_request_launch_stub_row_ok_count": 4,
            "runner_future_kernel_native_consumer_request_launch_ptr_stub_row_count": 4,
            "runner_future_kernel_native_consumer_request_launch_ptr_stub_row_ok_count": 4,
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


def test_finalize_report_with_artifact_check_mirrors_bootstrap_to_canonical_path(
    tmp_path: Path,
    monkeypatch,
):
    import scripts.run_premap_online_native_stub_canary as canary

    artifact_output = tmp_path / "artifact_check.json"
    bootstrap_output = tmp_path / "artifact_check_bootstrap.json"

    def fake_run(cmd, *, env, dry_run, allow_failure=False):
        assert allow_failure is True
        assert "--allow-bootstrap-preflight" in cmd
        output = Path(cmd[cmd.index("--output-json") + 1])
        assert output == bootstrap_output
        output.write_text(
            json.dumps(
                {
                    "passed": False,
                    "failures": ["runner_not_passed"],
                    "bootstrap_preflight_allowed": True,
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
        allow_bootstrap_preflight=True,
    )

    assert result["artifact_check_bootstrap_output_json"] == str(bootstrap_output)
    assert result["artifact_check_bootstrap_summary"]["bootstrap_preflight_allowed"]
    assert bootstrap_output.exists()
    assert artifact_output.exists()
    assert json.loads(artifact_output.read_text(encoding="utf-8"))[
        "bootstrap_preflight_allowed"
    ] is True
    assert result["steps"]["artifact_check_bootstrap"]["returncode"] == 1


def test_finalize_report_with_strict_preflight_runs_status_checker(
    tmp_path: Path,
    monkeypatch,
):
    import scripts.run_premap_online_native_stub_canary as canary

    def fake_run(cmd, *, env, dry_run, allow_failure=False):
        output = Path(cmd[cmd.index("--output-json") + 1])
        if cmd[1] == "scripts/check_premap_lab_preflight_summary.py":
            output.write_text(
                json.dumps(
                    {
                        "passed": True,
                        "failures": [],
                        "source": "premap_lab_preflight_summary_check",
                        "online_merged_source_count": 32,
                        "online_merged_row_count": 1841,
                        "online_merged_dispatch_active_rows": 1841,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        elif "--summary-only" in cmd:
            output.write_text(
                json.dumps(
                    {
                        "passed": True,
                        "runtime_gate_evidence_deferred_count": 0,
                        "strict_default_gate_evidence_deferred_count": 0,
                        "required_evidence": {
                            "passed": True,
                            "present_count": 18,
                            "passed_count": 18,
                            "required_count": 18,
                        },
                        "optional_evidence": {
                            "passed": True,
                            "present_count": 19,
                            "passed_count": 19,
                            "required_count": 19,
                        },
                        "native_typed_consumer_bridge_required": True,
                        "native_stub_online_invocation_canary_required": True,
                        "payload_bytes_required": 0,
                        "passed_to_kernel_required": False,
                        "changes_kernel_launch_args_required": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        else:
            output.write_text(
                json.dumps({"passed": True, "failures": []}) + "\n",
                encoding="utf-8",
            )
        return {"cmd": cmd, "returncode": 0}

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(canary, "_run", fake_run)
    status_check_output = tmp_path / "status.check.json"
    args = build_parser().parse_args(
        [
            "--preflight-output-json",
            str(tmp_path / "preflight.json"),
            "--preflight-status-output-json",
            str(tmp_path / "status.json"),
            "--preflight-status-check-output-json",
            str(status_check_output),
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )
    payload = {"passed": True, "failures": [], "steps": {}}

    result = finalize_report_with_strict_preflight(args=args, payload=payload)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["final_preflight_status_check_output_json"] == str(
        status_check_output
    )
    assert result["final_preflight_status_check_summary"] == {
        "passed": True,
        "failures": [],
        "source": "premap_lab_preflight_summary_check",
        "online_merged_source_count": 32,
        "online_merged_row_count": 1841,
        "online_merged_dispatch_active_rows": 1841,
    }
    assert "final_preflight_status_check" in result["steps"]


def test_finalize_report_with_strict_preflight_fails_on_status_checker_failure(
    tmp_path: Path,
    monkeypatch,
):
    import scripts.run_premap_online_native_stub_canary as canary

    def fake_run(cmd, *, env, dry_run, allow_failure=False):
        output = Path(cmd[cmd.index("--output-json") + 1])
        if cmd[1] == "scripts/check_premap_lab_preflight_summary.py":
            output.write_text(
                json.dumps(
                    {
                        "passed": False,
                        "failures": ["payload_bytes_required_mismatch"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        elif "--summary-only" in cmd:
            output.write_text(json.dumps({"passed": True}) + "\n", encoding="utf-8")
        else:
            output.write_text(
                json.dumps({"passed": True, "failures": []}) + "\n",
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
            "--preflight-status-check-output-json",
            str(tmp_path / "status.check.json"),
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )
    payload = {"passed": True, "failures": [], "steps": {}}

    result = finalize_report_with_strict_preflight(args=args, payload=payload)

    assert result["passed"] is False
    assert "final_preflight_status_check_not_passed" in result["failures"]
    assert result["final_preflight_status_check_summary"]["failures"] == [
        "payload_bytes_required_mismatch"
    ]


def test_main_finalize_existing_applies_required_pointer_source_gate(
    tmp_path: Path,
    monkeypatch,
):
    import scripts.run_premap_online_native_stub_canary as canary

    def passthrough_finalize(**kwargs):
        return kwargs["payload"]

    monkeypatch.setattr(canary, "finalize_report_with_artifact_check", passthrough_finalize)
    monkeypatch.setattr(canary, "finalize_report_with_strict_preflight", passthrough_finalize)
    runner = tmp_path / "runner.json"
    runner.write_text(json.dumps({"passed": True, "failures": []}) + "\n", encoding="utf-8")

    exit_code = main(
        [
            "--finalize-existing",
            "--require-pointer-source-observer-check",
            "--pointer-source-observer-check-json",
            str(tmp_path / "missing.check.json"),
            "--output-json",
            str(runner),
            "--stdout-mode",
            "none",
        ]
    )
    payload = json.loads(runner.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert payload["passed"] is False
    assert payload["failures"] == ["pointer_source_observer_check_not_passed"]
    assert payload["pointer_source_observer_gate_passed"] is False


def test_main_finalize_existing_preserves_pass_with_valid_pointer_source_gate(
    tmp_path: Path,
    monkeypatch,
):
    import scripts.run_premap_online_native_stub_canary as canary

    def passthrough_finalize(**kwargs):
        return kwargs["payload"]

    monkeypatch.setattr(canary, "finalize_report_with_artifact_check", passthrough_finalize)
    monkeypatch.setattr(canary, "finalize_report_with_strict_preflight", passthrough_finalize)
    artifact = tmp_path / "observer.check.json"
    artifact.write_text(
        json.dumps(_pointer_source_observer_check_payload()) + "\n",
        encoding="utf-8",
    )
    runner = tmp_path / "runner.json"
    runner.write_text(json.dumps({"passed": True, "failures": []}) + "\n", encoding="utf-8")

    exit_code = main(
        [
            "--finalize-existing",
            "--require-pointer-source-observer-check",
            "--pointer-source-observer-check-json",
            str(artifact),
            "--output-json",
            str(runner),
            "--stdout-mode",
            "none",
        ]
    )
    payload = json.loads(runner.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["passed"] is True
    assert payload["failures"] == []
    assert payload["pointer_source_observer_gate_passed"] is True
