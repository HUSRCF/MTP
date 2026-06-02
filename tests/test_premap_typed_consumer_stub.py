from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_premap_typed_consumer_stub.py"
    )
    spec = importlib.util.spec_from_file_location("run_premap_typed_consumer_stub", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_typed_consumer_stub_build_command_enables_schema_guard(tmp_path: Path):
    module = _load_module()
    output = tmp_path / "stub"

    cmd = module.build_command(
        macros=[
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
        ],
        offload_arch="gfx1100",
        output=output,
    )

    assert "-DMTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1=1" in cmd
    assert any(
        item.startswith("-DMTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI=0x")
        for item in cmd
    )
    assert any(
        item.startswith("-DMTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO=0x")
        for item in cmd
    )
    assert "-DMTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA=1" in cmd
    assert "-DMTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE=1" in cmd
    assert str(output) in cmd


def test_typed_consumer_stub_uses_kernel_side_abi_header():
    module = _load_module()
    source = Path(module.SRC).read_text(encoding="utf-8")
    header = Path(module.ABI_HEADER).read_text(encoding="utf-8")
    adapter = Path(module.ADAPTER_HEADER).read_text(encoding="utf-8")

    assert '#include "premap_typed_consumer_abi_v1.h"' in source
    assert '#include "premap_typed_consumer_adapter_v1.h"' in source
    assert "PremapKernelSideTypedConsumerAbiV1 table" in source
    assert "struct PremapKernelSideTypedConsumerAbiV1" in header
    assert "struct PremapKernelSideTypedConsumerRowV1" in adapter
    assert "struct PremapKernelSideTypedConsumerLaunchEnvelopeV1" in adapter
    assert "struct PremapKernelSideTypedConsumerPathResultV1" in adapter
    assert "struct PremapKernelSideCompatibleConsumerResultV1" in adapter
    assert "struct PremapFutureKernelSideConsumerArgsV1" in adapter
    assert "struct PremapFutureKernelSideConsumerResultV1" in adapter
    assert "struct PremapFutureKernelNativeConsumerParamsV1" in adapter
    assert "struct PremapFutureKernelNativeConsumerResultV1" in adapter
    assert "struct PremapFutureKernelNativeConsumerLaunchV1" in adapter
    assert "struct PremapFutureKernelNativeConsumerLaunchResultV1" in adapter
    assert "struct PremapFutureKernelNativeConsumerDispatchV1" in adapter
    assert "struct PremapFutureKernelNativeConsumerDispatchResultV1" in adapter
    assert "struct PremapFutureKernelNativeConsumerArgSlotV1" in adapter
    assert "PremapFutureKernelNativeConsumerArgSlotResultV1" in adapter
    assert "kPremapKernelSideCompatibleConsumerAbiV1Name" in adapter
    assert "kPremapFutureKernelSideConsumerArgsV1Name" in adapter
    assert "kPremapFutureKernelNativeConsumerAbiV1Name" in adapter
    assert "premap_typed_consumer_load_row_v1" in adapter
    assert "premap_typed_consumer_kernel_side_consume_row_v1" in adapter
    assert (
        "premap_typed_consumer_kernel_side_compatible_consume_row_v1"
        in adapter
    )
    assert "premap_typed_consumer_future_kernel_consume_row_v1" in adapter
    assert "premap_typed_consumer_future_native_consume_row_v1" in adapter
    assert "premap_typed_consumer_future_native_launch_consume_row_v1" in adapter
    assert "premap_typed_consumer_future_native_dispatch_consume_row_v1" in adapter
    assert (
        "premap_typed_consumer_future_native_arg_slot_consume_program_lane_v1"
        in adapter
    )
    assert "typed_consumer_envelope_kernel" in source
    assert "typed_consumer_future_kernel_args_kernel" in source
    assert "typed_consumer_future_native_kernel" in source
    assert "typed_consumer_future_native_launch_kernel" in source
    assert "typed_consumer_future_native_dispatch_kernel" in source
    assert "typed_consumer_future_native_arg_slot_kernel" in source
    assert "kernel_side_compatible_consumer_checked" in source
    assert "future_kernel_consumer_args_checked" in source
    assert "future_kernel_consumer_args_struct_size" in source
    assert "future_kernel_consumer_args_offset_field_mask" in source
    assert "future_kernel_consumer_args_offset_single_field_mirror_kind" in source
    assert "future_kernel_native_consumer_checked" in source
    assert "future_kernel_native_launch_consumer_checked" in source
    assert "future_kernel_native_dispatch_consumer_checked" in source
    assert "future_kernel_native_dispatch_consumer_active_rows" in source
    assert "future_kernel_native_dispatch_consumer_launch_threads" in source
    assert "future_kernel_native_dispatch_consumer_launch_geometry_checked" in source
    assert "future_kernel_native_dispatch_consumer_launch_covers_active_rows" in source
    assert "future_kernel_native_dispatch_consumer_launch_minimal_cover" in source
    assert (
        "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_ok_count"
        in source
    )
    assert (
        "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_ok_count"
        in source
    )
    assert (
        "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_ok_count"
        in source
    )
    assert (
        "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_ok_count"
        in source
    )
    assert "future_kernel_native_arg_slot_consumer_checked" in source
    assert "future_kernel_native_arg_slot_consumer_slot_struct_size" in source
    assert "future_kernel_native_consumer_params_struct_align" in source
    assert "future_kernel_native_dispatch_consumer_dispatch_struct_size" in source
    assert "future_kernel_native_dispatch_consumer_offset_row_offset" in source
    assert "launch_geometry_valid" in adapter
    assert "previous_grid_threads < static_cast<uint64_t>(active_rows)" in adapter
    for field in (
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ):
        assert field in header


def test_typed_consumer_stub_rejects_forbidden_macro():
    module = _load_module()

    with pytest.raises(ValueError, match="forbidden typed consumer macros"):
        module.validate_macros(["MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS"])


def test_typed_consumer_stub_rejects_multiple_mirror_macros():
    module = _load_module()

    with pytest.raises(ValueError, match="single-field mirror"):
        module.validate_macros(
            [
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
            ]
        )


def test_typed_consumer_stub_dry_run_writes_command(tmp_path: Path):
    module = _load_module()
    output = tmp_path / "dry_run.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
            "--output-json",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = output.read_text(encoding="utf-8")
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION" in payload
    assert "expected_schema_hash" in payload
    parsed = json.loads(payload)
    assert parsed["abi_header"].endswith("premap_typed_consumer_abi_v1.h")
    assert parsed["adapter_header"].endswith("premap_typed_consumer_adapter_v1.h")


def test_typed_consumer_stub_dry_run_accepts_per_field_macros(tmp_path: Path):
    module = _load_module()
    output = tmp_path / "dry_run_fields.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
            "--output-json",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    ]


def test_typed_consumer_stub_dry_run_accepts_kernel_consumer_envelope_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_envelope.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE"
    ]


def test_typed_consumer_stub_dry_run_accepts_kernel_side_consumer_path_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_kernel_side_path.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH"
    ]


def test_typed_consumer_stub_dry_run_accepts_kernel_side_compatible_abi_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_kernel_side_compatible_abi.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI"
    ]


def test_typed_consumer_stub_dry_run_accepts_future_kernel_args_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_future_kernel_args.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    ]


def test_typed_consumer_stub_dry_run_accepts_packed_weight_mirror_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_packed_mirror.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD"
    ]


def test_typed_consumer_stub_dry_run_accepts_future_native_consumer_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_future_native_consumer.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    ]


def test_typed_consumer_stub_dry_run_accepts_future_native_launch_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_future_native_launch_consumer.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    ]


def test_typed_consumer_stub_rejects_future_native_launch_without_native_abi():
    module = _load_module()

    with pytest.raises(ValueError, match="future native consumer launch ABI requires"):
        module.validate_macros(
            [
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI"
            ]
        )


def test_typed_consumer_stub_dry_run_accepts_future_native_dispatch_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_future_native_dispatch_consumer.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    ]


def test_typed_consumer_stub_dry_run_accepts_dispatch_row_window(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_future_native_dispatch_row_window.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--dispatch-row-offset",
            "1",
            "--dispatch-row-limit",
            "5",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_dispatch_row_offset"] == 1
    assert payload["requested_dispatch_row_limit"] == 5


def test_typed_consumer_stub_rejects_future_native_dispatch_without_launch_abi():
    module = _load_module()

    with pytest.raises(ValueError, match="future native consumer dispatch ABI requires"):
        module.validate_macros(
            [
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
            ]
        )


def test_typed_consumer_stub_dry_run_accepts_future_native_arg_slot_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_future_native_arg_slot_consumer.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    ]


def test_typed_consumer_stub_rejects_future_native_arg_slot_without_dispatch_ptr():
    module = _load_module()

    with pytest.raises(ValueError, match="future native consumer arg-slot ABI requires"):
        module.validate_macros(
            [
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
            ]
        )


def test_typed_consumer_stub_dry_run_accepts_aux_metadata_mirror_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_aux_mirror.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD"
    ]


def test_typed_consumer_stub_dry_run_accepts_descriptor_ptr_mirror_macro(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output = tmp_path / "dry_run_descriptor_mirror.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["requested_macros"] == [
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD"
    ]


def test_typed_consumer_stub_writes_binary_input_prefix(tmp_path: Path):
    module = _load_module()
    input_json = tmp_path / "input.json"
    input_json.write_text(
        json.dumps(
            {
                "descriptor_ptr": [1, 2],
                "packed_weight_descriptor": [3, 4],
                "scale_metadata_handle": [5, 6],
                "aux_metadata_handle": [7, 8],
                "expert_id": [9, 10],
                "address_key_hash": [11, 12],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    prefix, row_count = module._input_prefix_from_json(input_json)

    assert row_count == 2
    assert prefix.with_suffix(".descriptor_ptr.u64").exists()
    assert prefix.with_suffix(".aux_metadata_handle.u64").exists()
    assert prefix.with_suffix(".expert_id.i32").exists()


def test_typed_consumer_stub_allows_missing_optional_aux_input(tmp_path: Path):
    module = _load_module()
    input_json = tmp_path / "input.json"
    input_json.write_text(
        json.dumps(
            {
                "descriptor_ptr": [1, 2],
                "packed_weight_descriptor": [3, 4],
                "scale_metadata_handle": [5, 6],
                "expert_id": [9, 10],
                "address_key_hash": [11, 12],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    prefix, row_count = module._input_prefix_from_json(input_json)

    assert row_count == 2
    assert prefix.with_suffix(".aux_metadata_handle.u64").exists()


def test_typed_consumer_stub_dry_run_accepts_omit_aux_pointer(tmp_path: Path):
    module = _load_module()
    output = tmp_path / "dry_run.json"

    exit_code = module.main(
        [
            "--dry-run",
            "--omit-aux-pointer",
            "--macro",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
            "--output-json",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = output.read_text(encoding="utf-8")
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA" in payload
