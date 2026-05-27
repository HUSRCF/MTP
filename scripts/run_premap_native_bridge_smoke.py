#!/usr/bin/env python3
"""Build a premap prepared-table native-input bridge artifact.

The smoke builds a small `ControlledPremapAddressManager` table object, exports
it through `PremapKernelArgShadowTableObject.to_native_typed_consumer_input_dict`,
and optionally feeds that JSON into the readonly HIP native consumer stub.
"""

from __future__ import annotations

import argparse
import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from mtp_expert_prefetch.runtime import (
    ControlledPremapAddressManager,
    ExpertPrefetchDescriptor,
    PremapRealDescriptorHandle,
    prepare_premap_address_plan,
)
from scripts.run_premap_typed_consumer_stub import run_stub, validate_macros


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]


def build_bridge_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    plan = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    real_handles = {
        key: PremapRealDescriptorHandle(
            expert_id=record.expert_id,
            local_expert_id=record.expert_id,
            handle_hash=f"real-hash-{record.expert_id}",
            address_key=key,
            packed_weight_descriptor=f"0x{0x2000 + record.expert_id:x}",
            scale_metadata_handle=f"0x{0x3000 + record.expert_id:x}",
            aux_metadata_handle=None,
            payload_bytes=0,
        )
        for key, record in zip(keys, plan.records, strict=True)
    }
    prep_result = manager.execute_descriptor_prep_readonly(
        keys,
        real_descriptor_handles_by_address_key=real_handles,
    )
    read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key=prep_result.consumer_object_hash_by_address_key,
        real_descriptor_handles_by_address_key=real_handles,
    )
    table_result, table_object = manager.build_kernel_arg_shadow_table_object_readonly(
        keys,
        read_result=read_result,
        expected_object_hash_by_address_key=prep_result.consumer_object_hash_by_address_key,
        real_descriptor_handles_by_address_key=real_handles,
    )
    native_input = table_object.to_native_typed_consumer_input_dict()
    bridge_ok = (
        bool(prep_result.execution_ok)
        and bool(read_result.read_ok)
        and bool(table_result.table_ok)
        and bool(table_object.lifecycle_ok)
        and int(native_input["_meta"]["payload_bytes"]) == 0
        and not bool(native_input["_meta"]["passed_to_kernel"])
        and not bool(native_input["_meta"]["changes_kernel_launch_args"])
    )
    bridge_summary = {
        "bridge_ok": bridge_ok,
        "row_count": table_object.row_count,
        "column_count": table_object.column_count,
        "table_object_hash": table_object.object_hash,
        "row_order_hash": table_object.row_order_hash,
        "ordered_row_hash": table_object.ordered_row_hash,
        "prep_execution_ok": prep_result.execution_ok,
        "read_ok": read_result.read_ok,
        "table_ok": table_result.table_ok,
        "lifecycle_ok": table_object.lifecycle_ok,
        "payload_bytes": table_object.payload_bytes,
        "passed_to_kernel": table_object.passed_to_kernel,
        "changes_kernel_launch_args": table_object.changes_kernel_launch_args,
    }
    return native_input, bridge_summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--macro", action="append", default=None)
    parser.add_argument("--run-native-stub", action="store_true")
    parser.add_argument("--omit-aux-pointer", action="store_true")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--hip-visible-devices")
    parser.add_argument(
        "--input-json-output",
        type=Path,
        default=REPO_ROOT
        / "outputs"
        / "reports"
        / "premap_kernel_consumer"
        / "native_bridge_input.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT
        / "outputs"
        / "reports"
        / "premap_kernel_consumer"
        / "native_bridge_smoke.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    macros = validate_macros(DEFAULT_MACROS if args.macro is None else args.macro)
    native_input, bridge_summary = build_bridge_payload()
    args.input_json_output.parent.mkdir(parents=True, exist_ok=True)
    args.input_json_output.write_text(
        json.dumps(native_input, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    native_stub_payload = None
    if args.run_native_stub:
        native_stub_payload = run_stub(
            Namespace(
                device=args.device,
                rows=int(bridge_summary["row_count"]),
                block_threads=args.block_threads,
                input_json=args.input_json_output,
                macro=macros,
                offload_arch=args.offload_arch,
                hip_visible_devices=args.hip_visible_devices,
                force_build=args.force_build,
                omit_aux_pointer=args.omit_aux_pointer,
            )
        )
    passed = bool(bridge_summary["bridge_ok"]) and (
        native_stub_payload is None or bool(native_stub_payload.get("ok"))
    )
    payload: dict[str, Any] = {
        "passed": passed,
        "failures": [] if passed else ["native_bridge_smoke_failed"],
        "native_input_json": str(args.input_json_output),
        "bridge_summary": bridge_summary,
        "native_stub": native_stub_payload,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
