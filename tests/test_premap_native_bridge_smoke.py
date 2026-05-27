from __future__ import annotations

import json
from pathlib import Path

from scripts.run_premap_native_bridge_smoke import build_bridge_payload, main


def test_premap_native_bridge_payload_is_noop_and_native_shape() -> None:
    native_input, summary = build_bridge_payload()

    assert summary["bridge_ok"] is True
    assert summary["row_count"] == 2
    assert summary["payload_bytes"] == 0
    assert summary["passed_to_kernel"] is False
    assert summary["changes_kernel_launch_args"] is False
    assert len(native_input["descriptor_ptr"]) == 2
    assert len(native_input["packed_weight_descriptor"]) == 2
    assert len(native_input["scale_metadata_handle"]) == 2
    assert native_input["aux_metadata_handle"] == [0, 0]
    assert native_input["expert_id"] == [3, 7]


def test_premap_native_bridge_cli_writes_input_and_summary(tmp_path: Path) -> None:
    output_json = tmp_path / "bridge.json"
    input_json = tmp_path / "bridge_input.json"

    exit_code = main(
        [
            "--output-json",
            str(output_json),
            "--input-json-output",
            str(input_json),
        ]
    )

    summary = json.loads(output_json.read_text(encoding="utf-8"))
    native_input = json.loads(input_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert summary["passed"] is True
    assert summary["native_stub"] is None
    assert summary["payload_bytes"] == 0
    assert summary["passed_to_kernel"] is False
    assert summary["changes_kernel_launch_args"] is False
    assert native_input["expert_id"] == [3, 7]
