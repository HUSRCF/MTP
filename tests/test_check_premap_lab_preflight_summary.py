from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.check_premap_lab_preflight_summary import (
    check_premap_lab_preflight_summary,
)


HEX = "a" * 64


def _summary() -> dict[str, object]:
    return {
        "passed": True,
        "default_contract_passed": True,
        "default_required_evidence_passed": True,
        "default_optional_evidence_passed": True,
        "default_kernel_consumer_schema_passed": True,
        "default_kernel_consumer_schema_row_field_names": [
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ],
        "default_kernel_consumer_schema_row_metadata_names": [
            "layer_id",
            "expert_id",
            "address_key_hash",
            "row_order_hash",
            "ordered_row_hash",
        ],
        "default_kernel_consumer_dispatch_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_dispatch_ptr_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_online_merged_multiprogram_evidence_passed": True,
        "default_kernel_consumer_online_merged_multiprogram_source_count": 32,
        "default_kernel_consumer_online_merged_multiprogram_row_count": 1841,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_offset": 0,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_limit": 1841,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_active_rows": 1841,
        "default_kernel_consumer_online_merged_multiprogram_device": 1,
        "default_kernel_consumer_online_merged_multiprogram_mirror_field": (
            "scale_metadata_handle"
        ),
        "default_kernel_consumer_online_merged_multiprogram_not_single_launch_table": True,
        "default_kernel_consumer_online_merged_multiprogram_hashchain_equal": True,
        "default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked": True,
        "default_kernel_consumer_online_merged_multiprogram_no_payload": True,
        "default_kernel_consumer_online_merged_multiprogram_passed_to_kernel": False,
        "default_kernel_consumer_online_merged_multiprogram_changes_kernel_launch_args": False,
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_all_handle_fields_read": True,
        "default_kernel_consumer_arg_slot_field_read_field_names": [
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ],
        "default_kernel_consumer_arg_slot_field_read_row_ok_counts": {
            "descriptor_ptr": 1841,
            "packed_weight_descriptor": 1841,
            "scale_metadata_handle": 1841,
            "aux_metadata_handle": 1841,
        },
        "default_kernel_consumer_arg_slot_field_read_error_counts": {
            "descriptor_ptr": 0,
            "packed_weight_descriptor": 0,
            "scale_metadata_handle": 0,
            "aux_metadata_handle": 0,
        },
        "default_kernel_consumer_arg_slot_field_read_hashes": {
            "descriptor_ptr": "d35c1",
            "packed_weight_descriptor": "d35c2",
            "scale_metadata_handle": "d35c3",
            "aux_metadata_handle": "d35c4",
        },
        "runtime_gate_evidence_deferred_count": 0,
        "strict_default_gate_evidence_deferred_count": 0,
        "default_kernel_consumer_dispatch_runner_final_runtime_gate_evidence_deferred_count": 0,
        "default_kernel_consumer_dispatch_runner_final_strict_default_gate_evidence_deferred_count": 0,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
        "default_readonly_gate_sha256": HEX,
        "canary_gate_sha256": HEX,
        "default_kernel_consumer_schema_artifact_sha256": HEX,
        "default_kernel_consumer_dispatch_runner_evidence_sha256": HEX,
        "default_kernel_consumer_dispatch_runner_artifact_evidence_sha256": HEX,
        "default_kernel_consumer_online_merged_multiprogram_evidence_sha256": HEX,
        "default_kernel_consumer_dispatch_ptr_standalone_evidence_sha256": HEX,
        "default_kernel_consumer_arg_slot_standalone_evidence_sha256": HEX,
        "required_evidence": {
            "required_count": 18,
            "present_count": 18,
            "passed_count": 18,
            "evidence": {},
        },
        "optional_evidence": {
            "required_count": 19,
            "present_count": 19,
            "passed_count": 19,
            "evidence": {},
        },
    }


def test_check_premap_lab_preflight_summary_accepts_valid_summary() -> None:
    result = check_premap_lab_preflight_summary(_summary())

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["online_merged_source_count"] == 32
    assert result["online_merged_row_count"] == 1841
    assert result["online_merged_device"] == 1
    assert result["online_merged_mirror_field"] == "scale_metadata_handle"


def test_check_premap_lab_preflight_summary_rejects_missing_sha() -> None:
    summary = _summary()
    summary["default_readonly_gate_sha256"] = "not-a-sha"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "default_readonly_gate_sha256_invalid" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_defer_and_kernel_mutation() -> None:
    summary = _summary()
    summary["strict_default_gate_evidence_deferred_count"] = 1
    summary["default_kernel_consumer_online_merged_multiprogram_passed_to_kernel"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "strict_default_gate_evidence_deferred_count_not_zero" in result["failures"]
    assert (
        "default_kernel_consumer_online_merged_multiprogram_passed_to_kernel_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_arg_slot_field_read_gap() -> None:
    summary = _summary()
    summary["default_kernel_consumer_arg_slot_all_handle_fields_read"] = False
    summary["default_kernel_consumer_arg_slot_field_read_row_ok_counts"] = {
        "descriptor_ptr": 1841,
        "packed_weight_descriptor": 1841,
        "scale_metadata_handle": 1840,
        "aux_metadata_handle": 1841,
    }
    summary["default_kernel_consumer_arg_slot_field_read_error_counts"] = {
        "descriptor_ptr": 0,
        "packed_weight_descriptor": 0,
        "scale_metadata_handle": 1,
        "aux_metadata_handle": 0,
    }

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "default_kernel_consumer_arg_slot_all_handle_fields_read_mismatch" in result[
        "failures"
    ]
    assert "arg_slot_scale_metadata_handle_read_row_ok_count_mismatch" in result[
        "failures"
    ]
    assert "arg_slot_scale_metadata_handle_read_error_count_mismatch" in result[
        "failures"
    ]


def test_check_premap_lab_preflight_summary_rejects_arg_slot_runner_boundary() -> None:
    summary = _summary()
    summary["default_kernel_consumer_online_merged_multiprogram_device"] = 0
    summary["default_kernel_consumer_online_merged_multiprogram_mirror_field"] = (
        "packed_weight_descriptor"
    )
    summary[
        "default_kernel_consumer_online_merged_multiprogram_not_single_launch_table"
    ] = False
    summary[
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible"
    ] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "online_merged_device_not_gpu1" in result["failures"]
    assert "online_merged_mirror_field_mismatch" in result["failures"]
    assert (
        "default_kernel_consumer_online_merged_multiprogram_not_single_launch_table_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_cli_writes_output(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    output_path = tmp_path / "check.json"
    summary_path.write_text(json.dumps(_summary()) + "\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "scripts/check_premap_lab_preflight_summary.py",
            str(summary_path),
            "--output-json",
            str(output_path),
        ],
        check=True,
    )

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["source"] == "premap_lab_preflight_summary_check"
