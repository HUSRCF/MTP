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
    assert "premap_typed_consumer_load_row_v1" in adapter
    assert "typed_consumer_envelope_kernel" in source
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
