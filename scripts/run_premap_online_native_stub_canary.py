#!/usr/bin/env python3
"""Run the online prelaunch typed-consumer canary end to end.

The canary is intentionally a no-op runtime bridge:

1. Run a small vLLM/AWQ trace that exports one prepared prelaunch handle table.
2. Feed that exported table to the native HIP typed-consumer stub.
3. Run the lab preflight gate, which verifies both the stub evidence and the
   trace performance summary point at the same online-exported input.

It never enables payload dereference, ready credit, descriptor-order mutation,
or WNA16 kernel-argument pass.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_premap_lab_preflight import (
    _validate_prelaunch_pointer_source_observer_check_evidence,
)

DEFAULT_TRACE_CONFIG = (
    REPO_ROOT
    / "configs"
    / "trace"
    / "router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary.yaml"
)
DEFAULT_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_canary.json"
)
DEFAULT_PER_FIELD_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_per_field_canary.json"
)
DEFAULT_ENVELOPE_MIRROR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_kernel_envelope_mirror_canary.json"
)
DEFAULT_PACKED_WEIGHT_MIRROR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_packed_weight_mirror_canary.json"
)
DEFAULT_AUX_METADATA_MIRROR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_aux_metadata_mirror_canary.json"
)
DEFAULT_DESCRIPTOR_PTR_MIRROR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_descriptor_ptr_mirror_canary.json"
)
DEFAULT_KERNEL_SIDE_COMPATIBLE_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_kernel_side_compatible_consumer_abi_canary.json"
)
DEFAULT_FUTURE_KERNEL_ARGS_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_future_kernel_args_scale_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_ARGS_DESCRIPTOR_PTR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_kernel_args_descriptor_ptr_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_ARGS_PACKED_WEIGHT_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_kernel_args_packed_weight_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_ARGS_AUX_METADATA_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_kernel_args_aux_metadata_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_ARGS_COMPATIBLE_PATH_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_kernel_args_compatible_path_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_consumer_scale_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DESCRIPTOR_PTR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_consumer_descriptor_ptr_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_PACKED_WEIGHT_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_consumer_packed_weight_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_AUX_METADATA_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_consumer_aux_metadata_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_launch_consumer_scale_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_DESCRIPTOR_PTR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_launch_consumer_descriptor_ptr_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_PACKED_WEIGHT_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_launch_consumer_packed_weight_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_AUX_METADATA_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_launch_consumer_aux_metadata_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_dispatch_consumer_scale_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_DESCRIPTOR_PTR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_dispatch_consumer_descriptor_ptr_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PACKED_WEIGHT_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_dispatch_consumer_packed_weight_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_AUX_METADATA_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_dispatch_consumer_aux_metadata_mirror_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_request_ptr_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_request_launch_canary.json"
)
DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_native_request_launch_ptr_canary.json"
)
DEFAULT_PREFLIGHT_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_online_prelaunch_native_stub_canary.json"
)
DEFAULT_PREFLIGHT_STATUS_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_status_online_prelaunch_native_stub_canary.json"
)
DEFAULT_PREFLIGHT_STATUS_CHECK_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_status_online_prelaunch_native_stub_canary.check.json"
)
DEFAULT_REPORT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_prelaunch_native_stub_canary_runner.json"
)
DEFAULT_ARTIFACT_CHECK_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_prelaunch_native_stub_canary_artifact_check.json"
)
DEFAULT_POINTER_SOURCE_OBSERVER_CHECK = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "prelaunch_pointer_source_observer_16sample_20260626"
    / "production_batch_premap_prelaunch_pointer_source_observer_detailed"
    / "repeat_00"
    / "prelaunch_pointer_source_observer.check.json"
)
TYPED_HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
REQUEST_LEVEL_SINGLE_FIELD_HANDOFF_FIELD = "scale_metadata_handle"
REQUEST_LEVEL_HANDOFF_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
PER_FIELD_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
ENVELOPE_MIRROR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
PACKED_WEIGHT_MIRROR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
AUX_METADATA_MIRROR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
DESCRIPTOR_PTR_MIRROR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
KERNEL_SIDE_COMPATIBLE_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_ARGS_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_ARGS_DESCRIPTOR_PTR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_ARGS_PACKED_WEIGHT_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_ARGS_AUX_METADATA_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_ARGS_COMPATIBLE_PATH_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_ARGS_LAYOUT_SUMMARY_KEYS = (
    "future_kernel_consumer_args_struct_size",
    "future_kernel_consumer_args_struct_align",
    "future_kernel_consumer_args_result_struct_size",
    "future_kernel_consumer_args_result_struct_align",
    "future_kernel_consumer_args_offset_envelope",
    "future_kernel_consumer_args_offset_field_mask",
    "future_kernel_consumer_args_offset_single_field_mirror_kind",
    "future_kernel_consumer_args_offset_payload_bytes",
    "future_kernel_consumer_args_offset_flags",
)
FUTURE_KERNEL_NATIVE_CONSUMER_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_DESCRIPTOR_PTR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_PACKED_WEIGHT_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_AUX_METADATA_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_DESCRIPTOR_PTR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_PACKED_WEIGHT_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_AUX_METADATA_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_DESCRIPTOR_PTR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PACKED_WEIGHT_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_AUX_METADATA_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_STUB_MACROS = [
    *FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_STUB_MACROS[:-1],
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_STUB_MACROS = [
    *FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_STUB_MACROS[:-1],
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]

FUTURE_KERNEL_NATIVE_CONSUMER_SUMMARY_KEYS = (
    "passed",
    "ok",
    "row_count",
    "row_ok_count",
    "error_count",
    "future_kernel_native_consumer_abi_name",
    "future_kernel_native_consumer_checked",
    "future_kernel_native_consumer_mode",
    "future_kernel_native_consumer_source",
    "future_kernel_native_consumer_params_struct_size",
    "future_kernel_native_consumer_params_struct_align",
    "future_kernel_native_consumer_result_struct_size",
    "future_kernel_native_consumer_result_struct_align",
    "future_kernel_native_consumer_params_offset_descriptor_ptr",
    "future_kernel_native_consumer_params_offset_packed_weight_descriptor",
    "future_kernel_native_consumer_params_offset_scale_metadata_handle",
    "future_kernel_native_consumer_params_offset_aux_metadata_handle",
    "future_kernel_native_consumer_params_offset_expert_id",
    "future_kernel_native_consumer_params_offset_address_key_hash",
    "future_kernel_native_consumer_params_offset_row_count",
    "future_kernel_native_consumer_params_offset_field_mask",
    "future_kernel_native_consumer_params_offset_payload_bytes",
    "future_kernel_native_consumer_params_offset_flags",
    "future_kernel_native_consumer_row_count",
    "future_kernel_native_consumer_row_ok_count",
    "future_kernel_native_consumer_error_count",
    "future_kernel_native_consumer_payload_bytes",
    "future_kernel_native_consumer_passed_to_kernel",
    "future_kernel_native_consumer_changes_kernel_launch_args",
    "future_kernel_native_consumer_current_wna16_arg_compatible",
    "future_kernel_native_consumer_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_field_mask",
    "future_kernel_native_consumer_required_field_mask",
    "future_kernel_native_consumer_single_field_mirror_checked",
    "future_kernel_native_consumer_single_field_mirror_field_name",
    "future_kernel_native_consumer_single_field_mirror_row_count",
    "future_kernel_native_consumer_single_field_mirror_row_ok_count",
    "future_kernel_native_consumer_single_field_mirror_error_count",
    "payload_bytes",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "input_json",
)
FUTURE_KERNEL_NATIVE_LAUNCH_CONSUMER_SUMMARY_KEYS = (
    "passed",
    "ok",
    "row_count",
    "row_ok_count",
    "error_count",
    "future_kernel_native_consumer_checked",
    "future_kernel_native_consumer_row_count",
    "future_kernel_native_consumer_row_ok_count",
    "future_kernel_native_consumer_error_count",
    "future_kernel_native_consumer_params_struct_size",
    "future_kernel_native_consumer_params_struct_align",
    "future_kernel_native_consumer_result_struct_size",
    "future_kernel_native_consumer_result_struct_align",
    "future_kernel_native_consumer_params_offset_descriptor_ptr",
    "future_kernel_native_consumer_params_offset_packed_weight_descriptor",
    "future_kernel_native_consumer_params_offset_scale_metadata_handle",
    "future_kernel_native_consumer_params_offset_aux_metadata_handle",
    "future_kernel_native_consumer_params_offset_expert_id",
    "future_kernel_native_consumer_params_offset_address_key_hash",
    "future_kernel_native_consumer_params_offset_row_count",
    "future_kernel_native_consumer_params_offset_field_mask",
    "future_kernel_native_consumer_params_offset_payload_bytes",
    "future_kernel_native_consumer_params_offset_flags",
    "future_kernel_native_launch_consumer_abi_name",
    "future_kernel_native_launch_consumer_checked",
    "future_kernel_native_launch_consumer_mode",
    "future_kernel_native_launch_consumer_source",
    "future_kernel_native_launch_consumer_version",
    "future_kernel_native_launch_consumer_launch_struct_size",
    "future_kernel_native_launch_consumer_launch_struct_align",
    "future_kernel_native_launch_consumer_params_struct_size",
    "future_kernel_native_launch_consumer_params_struct_align",
    "future_kernel_native_launch_consumer_result_struct_size",
    "future_kernel_native_launch_consumer_result_struct_align",
    "future_kernel_native_launch_consumer_offset_params",
    "future_kernel_native_launch_consumer_offset_abi_version",
    "future_kernel_native_launch_consumer_offset_params_struct_size",
    "future_kernel_native_launch_consumer_offset_result_struct_size",
    "future_kernel_native_launch_consumer_offset_row_stride",
    "future_kernel_native_launch_consumer_offset_payload_bytes",
    "future_kernel_native_launch_consumer_offset_flags",
    "future_kernel_native_launch_consumer_row_stride",
    "future_kernel_native_launch_consumer_row_count",
    "future_kernel_native_launch_consumer_row_ok_count",
    "future_kernel_native_launch_consumer_error_count",
    "future_kernel_native_launch_consumer_payload_bytes",
    "future_kernel_native_launch_consumer_passed_to_kernel",
    "future_kernel_native_launch_consumer_changes_kernel_launch_args",
    "future_kernel_native_launch_consumer_current_wna16_arg_compatible",
    "future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation",
    "future_kernel_native_launch_consumer_field_mask",
    "future_kernel_native_launch_consumer_required_field_mask",
    "future_kernel_native_launch_consumer_single_field_mirror_checked",
    "future_kernel_native_launch_consumer_single_field_mirror_field_name",
    "future_kernel_native_launch_consumer_single_field_mirror_row_count",
    "future_kernel_native_launch_consumer_single_field_mirror_row_ok_count",
    "future_kernel_native_launch_consumer_single_field_mirror_error_count",
    "payload_bytes",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "input_json",
)
FUTURE_KERNEL_NATIVE_DISPATCH_CONSUMER_SUMMARY_KEYS = (
    "passed",
    "ok",
    "row_count",
    "row_ok_count",
    "error_count",
    "future_kernel_native_consumer_checked",
    "future_kernel_native_consumer_row_count",
    "future_kernel_native_consumer_row_ok_count",
    "future_kernel_native_consumer_error_count",
    "future_kernel_native_consumer_params_struct_size",
    "future_kernel_native_consumer_params_struct_align",
    "future_kernel_native_consumer_result_struct_size",
    "future_kernel_native_consumer_result_struct_align",
    "future_kernel_native_consumer_params_offset_descriptor_ptr",
    "future_kernel_native_consumer_params_offset_packed_weight_descriptor",
    "future_kernel_native_consumer_params_offset_scale_metadata_handle",
    "future_kernel_native_consumer_params_offset_aux_metadata_handle",
    "future_kernel_native_consumer_params_offset_expert_id",
    "future_kernel_native_consumer_params_offset_address_key_hash",
    "future_kernel_native_consumer_params_offset_row_count",
    "future_kernel_native_consumer_params_offset_field_mask",
    "future_kernel_native_consumer_params_offset_payload_bytes",
    "future_kernel_native_consumer_params_offset_flags",
    "future_kernel_native_launch_consumer_checked",
    "future_kernel_native_launch_consumer_row_count",
    "future_kernel_native_launch_consumer_row_ok_count",
    "future_kernel_native_launch_consumer_error_count",
    "future_kernel_native_launch_consumer_launch_struct_size",
    "future_kernel_native_launch_consumer_launch_struct_align",
    "future_kernel_native_launch_consumer_params_struct_size",
    "future_kernel_native_launch_consumer_params_struct_align",
    "future_kernel_native_launch_consumer_result_struct_size",
    "future_kernel_native_launch_consumer_result_struct_align",
    "future_kernel_native_launch_consumer_offset_params",
    "future_kernel_native_launch_consumer_offset_abi_version",
    "future_kernel_native_launch_consumer_offset_params_struct_size",
    "future_kernel_native_launch_consumer_offset_result_struct_size",
    "future_kernel_native_launch_consumer_offset_row_stride",
    "future_kernel_native_launch_consumer_offset_payload_bytes",
    "future_kernel_native_launch_consumer_offset_flags",
    "future_kernel_native_dispatch_consumer_abi_name",
    "future_kernel_native_dispatch_consumer_checked",
    "future_kernel_native_dispatch_consumer_mode",
    "future_kernel_native_dispatch_consumer_source",
    "future_kernel_native_dispatch_consumer_version",
    "future_kernel_native_dispatch_consumer_dispatch_struct_size",
    "future_kernel_native_dispatch_consumer_dispatch_struct_align",
    "future_kernel_native_dispatch_consumer_result_struct_size",
    "future_kernel_native_dispatch_consumer_result_struct_align",
    "future_kernel_native_dispatch_consumer_offset_launch",
    "future_kernel_native_dispatch_consumer_offset_dispatch_version",
    "future_kernel_native_dispatch_consumer_offset_grid_x",
    "future_kernel_native_dispatch_consumer_offset_block_x",
    "future_kernel_native_dispatch_consumer_offset_shared_mem_bytes",
    "future_kernel_native_dispatch_consumer_offset_row_offset",
    "future_kernel_native_dispatch_consumer_offset_row_limit",
    "future_kernel_native_dispatch_consumer_offset_rows_per_program",
    "future_kernel_native_dispatch_consumer_offset_payload_bytes",
    "future_kernel_native_dispatch_consumer_offset_flags",
    "future_kernel_native_dispatch_consumer_grid_x",
    "future_kernel_native_dispatch_consumer_block_x",
    "future_kernel_native_dispatch_consumer_shared_mem_bytes",
    "future_kernel_native_dispatch_consumer_row_offset",
    "future_kernel_native_dispatch_consumer_row_limit",
    "future_kernel_native_dispatch_consumer_rows_per_program",
    "future_kernel_native_dispatch_consumer_active_rows",
    "future_kernel_native_dispatch_consumer_launch_threads",
    "future_kernel_native_dispatch_consumer_program_iteration_checked",
    "future_kernel_native_dispatch_consumer_row_assignment_formula",
    "future_kernel_native_dispatch_consumer_program_count",
    "future_kernel_native_dispatch_consumer_full_program_count",
    "future_kernel_native_dispatch_consumer_last_program_active_rows",
    "future_kernel_native_dispatch_consumer_inactive_lane_count",
    "future_kernel_native_dispatch_consumer_first_program_row_offset",
    "future_kernel_native_dispatch_consumer_last_program_row_offset",
    "future_kernel_native_dispatch_consumer_program_iteration_hash",
    "future_kernel_native_dispatch_consumer_launch_geometry_checked",
    "future_kernel_native_dispatch_consumer_launch_covers_active_rows",
    "future_kernel_native_dispatch_consumer_launch_minimal_cover",
    "future_kernel_native_dispatch_consumer_row_count",
    "future_kernel_native_dispatch_consumer_row_ok_count",
    "future_kernel_native_dispatch_consumer_error_count",
    "future_kernel_native_dispatch_consumer_hash_accumulator",
    "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator",
    "future_kernel_native_dispatch_consumer_payload_bytes",
    "future_kernel_native_dispatch_consumer_passed_to_kernel",
    "future_kernel_native_dispatch_consumer_changes_kernel_launch_args",
    "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible",
    "future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation",
    "future_kernel_native_dispatch_consumer_field_mask",
    "future_kernel_native_dispatch_consumer_required_field_mask",
    "future_kernel_native_dispatch_consumer_single_field_mirror_checked",
    "future_kernel_native_dispatch_consumer_single_field_mirror_field_name",
    "future_kernel_native_dispatch_consumer_single_field_mirror_row_count",
    "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count",
    "future_kernel_native_dispatch_consumer_single_field_mirror_error_count",
    "future_kernel_native_dispatch_consumer_single_field_mirror_hash_accumulator",
    "future_kernel_native_dispatch_ptr_consumer_abi_name",
    "future_kernel_native_dispatch_ptr_consumer_checked",
    "future_kernel_native_dispatch_ptr_consumer_mode",
    "future_kernel_native_dispatch_ptr_consumer_source",
    "future_kernel_native_dispatch_ptr_consumer_version",
    "future_kernel_native_dispatch_ptr_consumer_packet_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_packet_struct_align",
    "future_kernel_native_dispatch_ptr_consumer_dispatch_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_result_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_offset_dispatch",
    "future_kernel_native_dispatch_ptr_consumer_offset_abi_version",
    "future_kernel_native_dispatch_ptr_consumer_offset_dispatch_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_offset_result_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_offset_payload_bytes",
    "future_kernel_native_dispatch_ptr_consumer_offset_flags",
    "future_kernel_native_dispatch_ptr_consumer_packet_visible",
    "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible",
    "future_kernel_native_dispatch_ptr_consumer_packet_chain_depth",
    "future_kernel_native_dispatch_ptr_consumer_row_count",
    "future_kernel_native_dispatch_ptr_consumer_row_ok_count",
    "future_kernel_native_dispatch_ptr_consumer_error_count",
    "future_kernel_native_dispatch_ptr_consumer_hash_accumulator",
    "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator",
    "future_kernel_native_dispatch_ptr_consumer_payload_bytes",
    "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel",
    "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args",
    "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible",
    "future_kernel_native_dispatch_ptr_consumer_requires_wna16_arg_reinterpretation",
    "future_kernel_native_dispatch_ptr_consumer_field_mask",
    "future_kernel_native_dispatch_ptr_consumer_required_field_mask",
    "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_checked",
    "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_field_name",
    "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count",
    "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count",
    "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_error_count",
    "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_abi_name",
    "future_kernel_native_arg_slot_consumer_checked",
    "future_kernel_native_arg_slot_consumer_mode",
    "future_kernel_native_arg_slot_consumer_source",
    "future_kernel_native_arg_slot_consumer_version",
    "future_kernel_native_arg_slot_consumer_slot_struct_size",
    "future_kernel_native_arg_slot_consumer_slot_struct_align",
    "future_kernel_native_arg_slot_consumer_dispatch_ptr_struct_size",
    "future_kernel_native_arg_slot_consumer_result_struct_size",
    "future_kernel_native_arg_slot_consumer_offset_dispatch_ptr",
    "future_kernel_native_arg_slot_consumer_offset_abi_version",
    "future_kernel_native_arg_slot_consumer_offset_dispatch_ptr_struct_size",
    "future_kernel_native_arg_slot_consumer_offset_result_struct_size",
    "future_kernel_native_arg_slot_consumer_offset_payload_bytes",
    "future_kernel_native_arg_slot_consumer_offset_flags",
    "future_kernel_native_arg_slot_consumer_slot_visible",
    "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible",
    "future_kernel_native_arg_slot_consumer_dispatch_packet_visible",
    "future_kernel_native_arg_slot_consumer_packet_chain_depth",
    "future_kernel_native_arg_slot_consumer_row_count",
    "future_kernel_native_arg_slot_consumer_row_ok_count",
    "future_kernel_native_arg_slot_consumer_error_count",
    "future_kernel_native_arg_slot_consumer_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_count",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_error_count",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_count",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_error_count",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_count",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_error_count",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_count",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_error_count",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_payload_bytes",
    "future_kernel_native_arg_slot_consumer_passed_to_kernel",
    "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args",
    "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible",
    "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation",
    "future_kernel_native_arg_slot_consumer_field_mask",
    "future_kernel_native_arg_slot_consumer_required_field_mask",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_checked",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator",
    "future_kernel_native_consumer_view_abi_name",
    "future_kernel_native_consumer_view_checked",
    "future_kernel_native_consumer_view_mode",
    "future_kernel_native_consumer_view_source",
    "future_kernel_native_consumer_view_version",
    "future_kernel_native_consumer_view_struct_size",
    "future_kernel_native_consumer_view_struct_align",
    "future_kernel_native_consumer_view_params_struct_size",
    "future_kernel_native_consumer_view_params_struct_align",
    "future_kernel_native_consumer_view_result_struct_size",
    "future_kernel_native_consumer_view_result_struct_align",
    "future_kernel_native_consumer_view_row_struct_size",
    "future_kernel_native_consumer_view_row_struct_align",
    "future_kernel_native_consumer_view_row_offset_descriptor_ptr",
    "future_kernel_native_consumer_view_row_offset_packed_weight_descriptor",
    "future_kernel_native_consumer_view_row_offset_scale_metadata_handle",
    "future_kernel_native_consumer_view_row_offset_aux_metadata_handle",
    "future_kernel_native_consumer_view_row_offset_expert_id",
    "future_kernel_native_consumer_view_row_offset_address_key_hash",
    "future_kernel_native_consumer_view_row_offset_row_index",
    "future_kernel_native_consumer_view_offset_params",
    "future_kernel_native_consumer_view_offset_abi_version",
    "future_kernel_native_consumer_view_offset_source_packet_chain_depth",
    "future_kernel_native_consumer_view_offset_row_offset",
    "future_kernel_native_consumer_view_offset_row_limit",
    "future_kernel_native_consumer_view_offset_rows_per_program",
    "future_kernel_native_consumer_view_offset_payload_bytes",
    "future_kernel_native_consumer_view_offset_flags",
    "future_kernel_native_consumer_view_source_packet_chain_depth",
    "future_kernel_native_consumer_view_row_count",
    "future_kernel_native_consumer_view_row_ok_count",
    "future_kernel_native_consumer_view_error_count",
    "future_kernel_native_consumer_view_hash_accumulator",
    "future_kernel_native_consumer_view_handle_projection_hash_accumulator",
    "future_kernel_native_consumer_view_descriptor_ptr_read_row_count",
    "future_kernel_native_consumer_view_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_view_descriptor_ptr_read_error_count",
    "future_kernel_native_consumer_view_descriptor_ptr_read_hash_accumulator",
    "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_count",
    "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_view_packed_weight_descriptor_read_error_count",
    "future_kernel_native_consumer_view_packed_weight_descriptor_read_hash_accumulator",
    "future_kernel_native_consumer_view_scale_metadata_handle_read_row_count",
    "future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_view_scale_metadata_handle_read_error_count",
    "future_kernel_native_consumer_view_scale_metadata_handle_read_hash_accumulator",
    "future_kernel_native_consumer_view_aux_metadata_handle_read_row_count",
    "future_kernel_native_consumer_view_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_view_aux_metadata_handle_read_error_count",
    "future_kernel_native_consumer_view_aux_metadata_handle_read_hash_accumulator",
    "future_kernel_native_consumer_view_payload_bytes",
    "future_kernel_native_consumer_view_passed_to_kernel",
    "future_kernel_native_consumer_view_changes_kernel_launch_args",
    "future_kernel_native_consumer_view_current_wna16_arg_compatible",
    "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_view_field_mask",
    "future_kernel_native_consumer_view_required_field_mask",
    "future_kernel_native_consumer_view_single_field_mirror_checked",
    "future_kernel_native_consumer_view_single_field_mirror_field_name",
    "future_kernel_native_consumer_view_single_field_mirror_row_count",
    "future_kernel_native_consumer_view_single_field_mirror_row_ok_count",
    "future_kernel_native_consumer_view_single_field_mirror_error_count",
    "future_kernel_native_consumer_view_single_field_mirror_hash_accumulator",
    "payload_bytes",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "input_json",
)
FUTURE_KERNEL_NATIVE_REQUEST_PTR_CONSUMER_SUMMARY_KEYS = (
    "passed",
    "ok",
    "row_count",
    "row_ok_count",
    "error_count",
    "future_kernel_native_consumer_request_ptr_abi_name",
    "future_kernel_native_consumer_request_ptr_mode",
    "future_kernel_native_consumer_request_ptr_source",
    "future_kernel_native_consumer_request_ptr_field_read_path",
    "future_kernel_native_consumer_request_ptr_checked",
    "future_kernel_native_consumer_request_ptr_version",
    "future_kernel_native_consumer_request_ptr_packet_chain_depth",
    "future_kernel_native_consumer_request_ptr_pointer_size",
    "future_kernel_native_consumer_request_ptr_request_id",
    "future_kernel_native_consumer_request_ptr_payload_bytes",
    "future_kernel_native_consumer_request_ptr_payload_deref_allowed",
    "future_kernel_native_consumer_request_ptr_passed_to_kernel",
    "future_kernel_native_consumer_request_ptr_kernel_arg_pass_allowed",
    "future_kernel_native_consumer_request_ptr_changes_kernel_launch_args",
    "future_kernel_native_consumer_request_ptr_current_wna16_arg_compatible",
    "future_kernel_native_consumer_request_ptr_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_request_ptr_summary_row_count",
    "future_kernel_native_consumer_request_ptr_summary_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_error_count",
    "future_kernel_native_consumer_request_ptr_summary_field_mask",
    "future_kernel_native_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_expert_id_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_address_key_hash_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_row_metadata_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator",
    "future_kernel_native_consumer_request_ptr_summary_field_read_hash_accumulator",
    "future_kernel_native_consumer_request_ptr_summary_row_metadata_hash_accumulator",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_checked",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_field_name",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_source",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_row_count",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_row_ok_count",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_error_count",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_hash_accumulator",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_payload_bytes",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_passed_to_kernel",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_changes_kernel_launch_args",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_current_wna16_arg_compatible",
    "future_kernel_native_consumer_request_ptr_single_field_handoff_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_checked",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_field_names",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_source",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_row_count",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_row_ok_count",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_error_count",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_hash_accumulator",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_descriptor_ptr_row_ok_count",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_packed_weight_descriptor_row_ok_count",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_scale_metadata_handle_row_ok_count",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_aux_metadata_handle_row_ok_count",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_payload_bytes",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_passed_to_kernel",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_changes_kernel_launch_args",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_current_wna16_arg_compatible",
    "future_kernel_native_consumer_request_ptr_all_field_handoff_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_kernel_entry_summary_row_count",
    "future_kernel_native_consumer_kernel_entry_summary_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_error_count",
    "future_kernel_native_consumer_kernel_entry_summary_field_mask",
    "future_kernel_native_consumer_kernel_entry_summary_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_expert_id_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_address_key_hash_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_summary_field_read_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_summary_row_metadata_hash_accumulator",
    "payload_bytes",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "input_json",
)
FUTURE_KERNEL_NATIVE_REQUEST_LAUNCH_CONSUMER_SUMMARY_KEYS = (
    "passed",
    "ok",
    "row_count",
    "row_ok_count",
    "error_count",
    "future_kernel_native_consumer_request_launch_abi_name",
    "future_kernel_native_consumer_request_launch_mode",
    "future_kernel_native_consumer_request_launch_source",
    "future_kernel_native_consumer_request_launch_field_read_path",
    "future_kernel_native_consumer_request_launch_checked",
    "future_kernel_native_consumer_request_launch_version",
    "future_kernel_native_consumer_request_launch_packet_chain_depth",
    "future_kernel_native_consumer_request_launch_pointer_size",
    "future_kernel_native_consumer_request_launch_request_id",
    "future_kernel_native_consumer_request_launch_device_ordinal",
    "future_kernel_native_consumer_request_launch_stream_domain",
    "future_kernel_native_consumer_request_launch_grid_x",
    "future_kernel_native_consumer_request_launch_block_x",
    "future_kernel_native_consumer_request_launch_row_offset",
    "future_kernel_native_consumer_request_launch_row_limit",
    "future_kernel_native_consumer_request_launch_rows_per_program",
    "future_kernel_native_consumer_request_launch_row_count",
    "future_kernel_native_consumer_request_launch_payload_bytes",
    "future_kernel_native_consumer_request_launch_payload_deref_allowed",
    "future_kernel_native_consumer_request_launch_passed_to_kernel",
    "future_kernel_native_consumer_request_launch_kernel_arg_pass_allowed",
    "future_kernel_native_consumer_request_launch_changes_kernel_launch_args",
    "future_kernel_native_consumer_request_launch_current_wna16_arg_compatible",
    "future_kernel_native_consumer_request_launch_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_request_launch_summary_row_count",
    "future_kernel_native_consumer_request_launch_summary_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_error_count",
    "future_kernel_native_consumer_request_launch_summary_field_mask",
    "future_kernel_native_consumer_request_launch_summary_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_expert_id_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_address_key_hash_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_row_metadata_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_row_hash_accumulator",
    "future_kernel_native_consumer_request_launch_summary_field_read_hash_accumulator",
    "future_kernel_native_consumer_request_launch_summary_row_metadata_hash_accumulator",
    "future_kernel_native_consumer_request_launch_single_field_handoff_checked",
    "future_kernel_native_consumer_request_launch_single_field_handoff_field_name",
    "future_kernel_native_consumer_request_launch_single_field_handoff_source",
    "future_kernel_native_consumer_request_launch_single_field_handoff_row_count",
    "future_kernel_native_consumer_request_launch_single_field_handoff_row_ok_count",
    "future_kernel_native_consumer_request_launch_single_field_handoff_error_count",
    "future_kernel_native_consumer_request_launch_single_field_handoff_hash_accumulator",
    "future_kernel_native_consumer_request_launch_single_field_handoff_payload_bytes",
    "future_kernel_native_consumer_request_launch_single_field_handoff_passed_to_kernel",
    "future_kernel_native_consumer_request_launch_single_field_handoff_changes_kernel_launch_args",
    "future_kernel_native_consumer_request_launch_single_field_handoff_current_wna16_arg_compatible",
    "future_kernel_native_consumer_request_launch_single_field_handoff_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_request_launch_all_field_handoff_checked",
    "future_kernel_native_consumer_request_launch_all_field_handoff_field_names",
    "future_kernel_native_consumer_request_launch_all_field_handoff_source",
    "future_kernel_native_consumer_request_launch_all_field_handoff_row_count",
    "future_kernel_native_consumer_request_launch_all_field_handoff_row_ok_count",
    "future_kernel_native_consumer_request_launch_all_field_handoff_error_count",
    "future_kernel_native_consumer_request_launch_all_field_handoff_hash_accumulator",
    "future_kernel_native_consumer_request_launch_all_field_handoff_descriptor_ptr_row_ok_count",
    "future_kernel_native_consumer_request_launch_all_field_handoff_packed_weight_descriptor_row_ok_count",
    "future_kernel_native_consumer_request_launch_all_field_handoff_scale_metadata_handle_row_ok_count",
    "future_kernel_native_consumer_request_launch_all_field_handoff_aux_metadata_handle_row_ok_count",
    "future_kernel_native_consumer_request_launch_all_field_handoff_payload_bytes",
    "future_kernel_native_consumer_request_launch_all_field_handoff_passed_to_kernel",
    "future_kernel_native_consumer_request_launch_all_field_handoff_changes_kernel_launch_args",
    "future_kernel_native_consumer_request_launch_all_field_handoff_current_wna16_arg_compatible",
    "future_kernel_native_consumer_request_launch_all_field_handoff_requires_wna16_arg_reinterpretation",
    "payload_bytes",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "input_json",
)
FUTURE_KERNEL_NATIVE_REQUEST_LAUNCH_PTR_CONSUMER_SUMMARY_KEYS = (
    "passed",
    "ok",
    "row_count",
    "row_ok_count",
    "error_count",
    "future_kernel_native_consumer_request_launch_ptr_abi_name",
    "future_kernel_native_consumer_request_launch_ptr_mode",
    "future_kernel_native_consumer_request_launch_ptr_source",
    "future_kernel_native_consumer_request_launch_ptr_field_read_path",
    "future_kernel_native_consumer_request_launch_ptr_checked",
    "future_kernel_native_consumer_request_launch_ptr_version",
    "future_kernel_native_consumer_request_launch_ptr_packet_chain_depth",
    "future_kernel_native_consumer_request_launch_ptr_pointer_size",
    "future_kernel_native_consumer_request_launch_ptr_request_id",
    "future_kernel_native_consumer_request_launch_ptr_payload_bytes",
    "future_kernel_native_consumer_request_launch_ptr_payload_deref_allowed",
    "future_kernel_native_consumer_request_launch_ptr_passed_to_kernel",
    "future_kernel_native_consumer_request_launch_ptr_kernel_arg_pass_allowed",
    "future_kernel_native_consumer_request_launch_ptr_changes_kernel_launch_args",
    "future_kernel_native_consumer_request_launch_ptr_current_wna16_arg_compatible",
    "future_kernel_native_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_request_launch_ptr_summary_row_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_error_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_field_mask",
    "future_kernel_native_consumer_request_launch_ptr_summary_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_expert_id_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_address_key_hash_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_row_metadata_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_summary_row_hash_accumulator",
    "future_kernel_native_consumer_request_launch_ptr_summary_field_read_hash_accumulator",
    "future_kernel_native_consumer_request_launch_ptr_summary_row_metadata_hash_accumulator",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_checked",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_field_name",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_source",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_row_count",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_error_count",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_hash_accumulator",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_payload_bytes",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_passed_to_kernel",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_changes_kernel_launch_args",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_current_wna16_arg_compatible",
    "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_checked",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_field_names",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_source",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_row_count",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_error_count",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_hash_accumulator",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_descriptor_ptr_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_packed_weight_descriptor_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_scale_metadata_handle_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_aux_metadata_handle_row_ok_count",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_payload_bytes",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_passed_to_kernel",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_changes_kernel_launch_args",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_current_wna16_arg_compatible",
    "future_kernel_native_consumer_request_launch_ptr_all_field_handoff_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_request_launch_summary_row_count",
    "future_kernel_native_consumer_request_launch_summary_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_error_count",
    "future_kernel_native_consumer_request_launch_summary_field_mask",
    "future_kernel_native_consumer_request_launch_summary_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_expert_id_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_address_key_hash_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_row_metadata_read_row_ok_count",
    "future_kernel_native_consumer_request_launch_summary_row_hash_accumulator",
    "future_kernel_native_consumer_request_launch_summary_field_read_hash_accumulator",
    "future_kernel_native_consumer_request_launch_summary_row_metadata_hash_accumulator",
    "future_kernel_native_consumer_request_ptr_summary_row_count",
    "future_kernel_native_consumer_request_ptr_summary_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_error_count",
    "future_kernel_native_consumer_request_ptr_summary_field_mask",
    "future_kernel_native_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_expert_id_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_address_key_hash_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_row_metadata_read_row_ok_count",
    "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator",
    "future_kernel_native_consumer_request_ptr_summary_field_read_hash_accumulator",
    "future_kernel_native_consumer_request_ptr_summary_row_metadata_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_summary_row_count",
    "future_kernel_native_consumer_kernel_entry_summary_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_error_count",
    "future_kernel_native_consumer_kernel_entry_summary_field_mask",
    "future_kernel_native_consumer_kernel_entry_summary_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_expert_id_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_address_key_hash_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_summary_field_read_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_summary_row_metadata_hash_accumulator",
    "payload_bytes",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "input_json",
)
FUTURE_KERNEL_NATIVE_ARG_SLOT_CONSUMER_SUMMARY_KEYS = (
    "passed",
    "ok",
    "row_count",
    "row_ok_count",
    "error_count",
    "future_kernel_native_arg_slot_consumer_abi_name",
    "future_kernel_native_arg_slot_consumer_checked",
    "future_kernel_native_arg_slot_consumer_mode",
    "future_kernel_native_arg_slot_consumer_source",
    "future_kernel_native_arg_slot_consumer_version",
    "future_kernel_native_arg_slot_consumer_slot_struct_size",
    "future_kernel_native_arg_slot_consumer_slot_struct_align",
    "future_kernel_native_arg_slot_consumer_dispatch_ptr_struct_size",
    "future_kernel_native_arg_slot_consumer_result_struct_size",
    "future_kernel_native_arg_slot_consumer_offset_dispatch_ptr",
    "future_kernel_native_arg_slot_consumer_offset_abi_version",
    "future_kernel_native_arg_slot_consumer_offset_dispatch_ptr_struct_size",
    "future_kernel_native_arg_slot_consumer_offset_result_struct_size",
    "future_kernel_native_arg_slot_consumer_offset_payload_bytes",
    "future_kernel_native_arg_slot_consumer_offset_flags",
    "future_kernel_native_arg_slot_consumer_slot_visible",
    "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible",
    "future_kernel_native_arg_slot_consumer_dispatch_packet_visible",
    "future_kernel_native_arg_slot_consumer_packet_chain_depth",
    "future_kernel_native_arg_slot_consumer_row_count",
    "future_kernel_native_arg_slot_consumer_row_ok_count",
    "future_kernel_native_arg_slot_consumer_error_count",
    "future_kernel_native_arg_slot_consumer_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_count",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_error_count",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_count",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_error_count",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_count",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_error_count",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_count",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_error_count",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_payload_bytes",
    "future_kernel_native_arg_slot_consumer_passed_to_kernel",
    "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args",
    "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible",
    "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation",
    "future_kernel_native_arg_slot_consumer_field_mask",
    "future_kernel_native_arg_slot_consumer_required_field_mask",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_checked",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator",
    "payload_bytes",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "input_json",
)

_FUTURE_KERNEL_REQUIRED_FIELD_MASK = 0x7
_FUTURE_KERNEL_ALL_FIELD_MASK = 0xF
_FUTURE_KERNEL_AUX_FIELD_MASK = 0x8
_UINT64_MASK = (1 << 64) - 1


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _resolve_repo_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else REPO_ROOT / path


def _future_field_mask_ok(
    payload: dict[str, Any],
    *,
    prefix: str,
    expected_field: str,
) -> bool:
    field_mask = payload.get(f"{prefix}_field_mask")
    required_mask = payload.get(f"{prefix}_required_field_mask")
    if not isinstance(field_mask, int) or isinstance(field_mask, bool):
        return False
    if not isinstance(required_mask, int) or isinstance(required_mask, bool):
        return False
    if required_mask != _FUTURE_KERNEL_REQUIRED_FIELD_MASK:
        return False
    if field_mask & _FUTURE_KERNEL_REQUIRED_FIELD_MASK != _FUTURE_KERNEL_REQUIRED_FIELD_MASK:
        return False
    if field_mask & ~_FUTURE_KERNEL_ALL_FIELD_MASK:
        return False
    if expected_field == "aux_metadata_handle" and not (
        field_mask & _FUTURE_KERNEL_AUX_FIELD_MASK
    ):
        return False
    return True


def _future_handle_field_reads_ok(
    payload: dict[str, Any],
    *,
    prefix: str,
    expected_rows: int,
) -> bool:
    for field in TYPED_HANDLE_FIELDS:
        read_prefix = f"{prefix}_{field}_read"
        if payload.get(f"{read_prefix}_row_count") != expected_rows:
            return False
        if payload.get(f"{read_prefix}_row_ok_count") != expected_rows:
            return False
        if payload.get(f"{read_prefix}_error_count") != 0:
            return False
        hash_value = payload.get(f"{read_prefix}_hash_accumulator")
        if not isinstance(hash_value, str) or not hash_value:
            return False
    return True


def _parse_hex64(value: Any) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = int(value, 16)
    except ValueError:
        return None
    if parsed < 0 or parsed > _UINT64_MASK:
        return None
    return parsed


def _strict_int_equals(value: Any, expected: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == expected


def _annotate_request_level_single_field_handoff(
    payload: dict[str, Any],
    *,
    consumer_prefix: str,
    summary_prefix: str,
    field_name: str = REQUEST_LEVEL_SINGLE_FIELD_HANDOFF_FIELD,
) -> None:
    """Expose a request-level one-field handoff canary alias.

    The native request/launch structs already read all handle fields through the
    future kernel-side ABI.  This alias makes the safest first field
    (`scale_metadata_handle`) explicit at the higher-level request boundary
    without changing the native ABI layout or passing WNA16 kernel args.
    """

    row_count = payload.get(f"{summary_prefix}_row_count")
    row_ok_count = payload.get(f"{summary_prefix}_{field_name}_read_row_ok_count")
    summary_error_count = payload.get(f"{summary_prefix}_error_count")
    error_count = (
        0
        if (
            isinstance(row_count, int)
            and not isinstance(row_count, bool)
            and row_count > 0
            and row_ok_count == row_count
            and summary_error_count == 0
        )
        else 1
    )
    payload[f"{consumer_prefix}_single_field_handoff_checked"] = True
    payload[f"{consumer_prefix}_single_field_handoff_field_name"] = field_name
    payload[f"{consumer_prefix}_single_field_handoff_source"] = (
        "native_request_summary_field_read_counts"
    )
    payload[f"{consumer_prefix}_single_field_handoff_row_count"] = row_count
    payload[f"{consumer_prefix}_single_field_handoff_row_ok_count"] = row_ok_count
    payload[f"{consumer_prefix}_single_field_handoff_error_count"] = error_count
    payload[f"{consumer_prefix}_single_field_handoff_hash_accumulator"] = payload.get(
        f"{summary_prefix}_field_read_hash_accumulator"
    )
    payload[f"{consumer_prefix}_single_field_handoff_payload_bytes"] = 0
    payload[f"{consumer_prefix}_single_field_handoff_passed_to_kernel"] = False
    payload[f"{consumer_prefix}_single_field_handoff_changes_kernel_launch_args"] = False
    payload[f"{consumer_prefix}_single_field_handoff_current_wna16_arg_compatible"] = False
    payload[
        f"{consumer_prefix}_single_field_handoff_requires_wna16_arg_reinterpretation"
    ] = False

    all_field_row_ok = [
        payload.get(f"{summary_prefix}_{item}_read_row_ok_count")
        for item in REQUEST_LEVEL_HANDOFF_FIELDS
    ]
    all_field_error_count = (
        0
        if (
            isinstance(row_count, int)
            and not isinstance(row_count, bool)
            and row_count > 0
            and summary_error_count == 0
            and all(value == row_count for value in all_field_row_ok)
        )
        else 1
    )
    payload[f"{consumer_prefix}_all_field_handoff_checked"] = True
    payload[f"{consumer_prefix}_all_field_handoff_field_names"] = list(
        REQUEST_LEVEL_HANDOFF_FIELDS
    )
    payload[f"{consumer_prefix}_all_field_handoff_source"] = (
        "native_request_summary_field_read_counts"
    )
    payload[f"{consumer_prefix}_all_field_handoff_row_count"] = row_count
    payload[f"{consumer_prefix}_all_field_handoff_row_ok_count"] = (
        row_count if all_field_error_count == 0 else None
    )
    payload[f"{consumer_prefix}_all_field_handoff_error_count"] = (
        all_field_error_count
    )
    payload[f"{consumer_prefix}_all_field_handoff_hash_accumulator"] = payload.get(
        f"{summary_prefix}_field_read_hash_accumulator"
    )
    payload[f"{consumer_prefix}_all_field_handoff_payload_bytes"] = 0
    payload[f"{consumer_prefix}_all_field_handoff_passed_to_kernel"] = False
    payload[f"{consumer_prefix}_all_field_handoff_changes_kernel_launch_args"] = False
    payload[f"{consumer_prefix}_all_field_handoff_current_wna16_arg_compatible"] = False
    payload[
        f"{consumer_prefix}_all_field_handoff_requires_wna16_arg_reinterpretation"
    ] = False
    for field_name_item, row_ok_count_item in zip(
        REQUEST_LEVEL_HANDOFF_FIELDS,
        all_field_row_ok,
        strict=True,
    ):
        payload[
            f"{consumer_prefix}_all_field_handoff_{field_name_item}_row_ok_count"
        ] = row_ok_count_item


def _request_level_single_field_handoff_passed(
    payload: dict[str, Any],
    *,
    consumer_prefix: str,
    expected_rows: int,
    field_name: str = REQUEST_LEVEL_SINGLE_FIELD_HANDOFF_FIELD,
) -> bool:
    return bool(
        payload.get(f"{consumer_prefix}_single_field_handoff_checked") is True
        and payload.get(f"{consumer_prefix}_single_field_handoff_field_name")
        == field_name
        and payload.get(f"{consumer_prefix}_single_field_handoff_source")
        == "native_request_summary_field_read_counts"
        and _strict_int_equals(
            payload.get(f"{consumer_prefix}_single_field_handoff_row_count"),
            expected_rows,
        )
        and _strict_int_equals(
            payload.get(f"{consumer_prefix}_single_field_handoff_row_ok_count"),
            expected_rows,
        )
        and _strict_int_equals(
            payload.get(f"{consumer_prefix}_single_field_handoff_error_count"),
            0,
        )
        and _parse_hex64(
            payload.get(f"{consumer_prefix}_single_field_handoff_hash_accumulator")
        )
        is not None
        and _strict_int_equals(
            payload.get(f"{consumer_prefix}_single_field_handoff_payload_bytes"),
            0,
        )
        and payload.get(f"{consumer_prefix}_single_field_handoff_passed_to_kernel")
        is False
        and payload.get(
            f"{consumer_prefix}_single_field_handoff_changes_kernel_launch_args"
        )
        is False
        and payload.get(
            f"{consumer_prefix}_single_field_handoff_current_wna16_arg_compatible"
        )
        is False
        and payload.get(
            f"{consumer_prefix}_single_field_handoff_requires_wna16_arg_reinterpretation"
        )
        is False
        and payload.get(f"{consumer_prefix}_all_field_handoff_checked") is True
        and payload.get(f"{consumer_prefix}_all_field_handoff_field_names")
        == list(REQUEST_LEVEL_HANDOFF_FIELDS)
        and payload.get(f"{consumer_prefix}_all_field_handoff_source")
        == "native_request_summary_field_read_counts"
        and _strict_int_equals(
            payload.get(f"{consumer_prefix}_all_field_handoff_row_count"),
            expected_rows,
        )
        and _strict_int_equals(
            payload.get(f"{consumer_prefix}_all_field_handoff_row_ok_count"),
            expected_rows,
        )
        and _strict_int_equals(
            payload.get(f"{consumer_prefix}_all_field_handoff_error_count"),
            0,
        )
        and _parse_hex64(
            payload.get(f"{consumer_prefix}_all_field_handoff_hash_accumulator")
        )
        is not None
        and all(
            _strict_int_equals(
                payload.get(
                    f"{consumer_prefix}_all_field_handoff_{item}_row_ok_count"
                ),
                expected_rows,
            )
            for item in REQUEST_LEVEL_HANDOFF_FIELDS
        )
        and _strict_int_equals(
            payload.get(f"{consumer_prefix}_all_field_handoff_payload_bytes"),
            0,
        )
        and payload.get(f"{consumer_prefix}_all_field_handoff_passed_to_kernel")
        is False
        and payload.get(
            f"{consumer_prefix}_all_field_handoff_changes_kernel_launch_args"
        )
        is False
        and payload.get(
            f"{consumer_prefix}_all_field_handoff_current_wna16_arg_compatible"
        )
        is False
        and payload.get(
            f"{consumer_prefix}_all_field_handoff_requires_wna16_arg_reinterpretation"
        )
        is False
    )


_FUTURE_NATIVE_HANDLE_PROJECTION_HASH_PREFIXES = (
    "future_kernel_native_dispatch_consumer",
    "future_kernel_native_dispatch_ptr_consumer",
    "future_kernel_native_arg_slot_consumer",
    "future_kernel_native_consumer_view",
)


def _future_native_handle_projection_hashchain_equal(
    payload: dict[str, Any],
) -> bool:
    values = tuple(
        _parse_hex64(payload.get(f"{prefix}_handle_projection_hash_accumulator"))
        for prefix in _FUTURE_NATIVE_HANDLE_PROJECTION_HASH_PREFIXES
    )
    return all(value is not None for value in values) and len(set(values)) == 1


def trace_output_dir(config_path: Path) -> Path:
    config = _load_yaml(config_path)
    if not isinstance(config, dict):
        raise ValueError(f"trace config must be a mapping: {config_path}")
    raw_output = config.get("output_dir")
    if not isinstance(raw_output, str) or not raw_output:
        raise ValueError(f"trace config missing output_dir: {config_path}")
    return _resolve_repo_path(raw_output)


def exported_inputs_from_performance(
    performance_path: Path,
    *,
    max_inputs: int | None = 1,
) -> list[Path]:
    payload = json.loads(performance_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"performance summary must be an object: {performance_path}")
    if payload.get("runtime_shadow_premap_native_typed_consumer_input_export_enabled") is not True:
        raise ValueError("online typed-consumer input export was not enabled")
    count = payload.get("runtime_shadow_premap_native_typed_consumer_input_export_count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise ValueError(f"invalid online typed-consumer input export count: {count!r}")
    first = payload.get(
        "runtime_shadow_premap_native_typed_consumer_input_export_first_path"
    )
    if not isinstance(first, str) or not first:
        raise ValueError("missing online typed-consumer export first_path")
    paths = payload.get("runtime_shadow_premap_native_typed_consumer_input_export_paths")
    if not isinstance(paths, list) or first not in paths:
        raise ValueError("online typed-consumer export first_path is not listed")
    if max_inputs is not None and max_inputs < 0:
        raise ValueError(f"max_inputs must be non-negative or None: {max_inputs}")
    selected_raw = paths if max_inputs in (None, 0) else paths[:max_inputs]
    input_paths: list[Path] = []
    for raw_path in selected_raw:
        if not isinstance(raw_path, str) or not raw_path:
            continue
        input_path = _resolve_repo_path(raw_path)
        if not input_path.exists():
            raise FileNotFoundError(input_path)
        input_paths.append(input_path)
    if not input_paths:
        raise ValueError("no exported online typed-consumer inputs selected")
    first_path = _resolve_repo_path(first)
    if input_paths[0] != first_path:
        raise ValueError("selected online typed-consumer inputs must start with first_path")
    return input_paths


def exported_input_from_performance(performance_path: Path) -> Path:
    return exported_inputs_from_performance(performance_path, max_inputs=1)[0]


def _require_min_online_inputs(
    input_paths: list[Path],
    *,
    min_online_inputs: int,
    performance_path: Path,
) -> None:
    if min_online_inputs < 0:
        raise ValueError(
            f"min_artifact_online_inputs must be non-negative: {min_online_inputs}"
        )
    if min_online_inputs > 0 and len(input_paths) < min_online_inputs:
        raise ValueError(
            "not enough exported online typed-consumer inputs selected: "
            f"selected={len(input_paths)} min_required={min_online_inputs} "
            f"performance_summary={performance_path}"
        )


def _base_env(*, gpu_index: int | None) -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = f"{REPO_ROOT}:{REPO_ROOT / 'src'}"
    env["PYTHONPATH"] = (
        f"{pythonpath}:{env['PYTHONPATH']}" if env.get("PYTHONPATH") else pythonpath
    )
    if gpu_index is not None:
        env["HIP_VISIBLE_DEVICES"] = str(gpu_index)
        env["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
    return env


def _int_arg(cmd: list[str], name: str, default: int | None) -> int | None:
    if name not in cmd:
        return default
    index = cmd.index(name) + 1
    if index >= len(cmd):
        raise ValueError(f"missing value for {name}")
    return int(cmd[index])


def _str_arg(cmd: list[str], name: str, default: str | None = None) -> str | None:
    if name not in cmd:
        return default
    index = cmd.index(name) + 1
    if index >= len(cmd):
        raise ValueError(f"missing value for {name}")
    return str(cmd[index])


def _multi_arg(cmd: list[str], name: str) -> list[str]:
    values: list[str] = []
    for index, item in enumerate(cmd[:-1]):
        if item == name:
            values.append(str(cmd[index + 1]))
    return values


def _expected_stub_dispatch_window(cmd: list[str]) -> tuple[int, int | None]:
    return (
        int(_int_arg(cmd, "--dispatch-row-offset", 0) or 0),
        _int_arg(cmd, "--dispatch-row-limit", None),
    )


def _can_reuse_existing_stub_output(cmd: list[str], output_path: Path) -> bool:
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not bool(payload.get("passed", payload.get("ok", False))):
        return False
    expected_macros = sorted(_multi_arg(cmd, "--macro"))
    observed_macros = payload.get("requested_macros")
    if not isinstance(observed_macros, list):
        return False
    if sorted(str(item) for item in observed_macros) != expected_macros:
        return False
    expected_offload_arch = _str_arg(cmd, "--offload-arch")
    if expected_offload_arch is None or payload.get("offload_arch") != expected_offload_arch:
        return False
    expected_input_json = _str_arg(cmd, "--input-json")
    if expected_input_json is not None:
        observed_input_json = payload.get("input_json")
        if not isinstance(observed_input_json, str) or not observed_input_json:
            return False
        if _resolve_repo_path(observed_input_json) != _resolve_repo_path(
            expected_input_json
        ):
            return False
    expected_offset, expected_limit = _expected_stub_dispatch_window(cmd)
    if "requested_dispatch_row_offset" not in payload:
        return False
    if int(payload["requested_dispatch_row_offset"]) != expected_offset:
        return False
    if "requested_dispatch_row_limit" not in payload:
        return False
    actual_limit = payload["requested_dispatch_row_limit"]
    if actual_limit is None:
        return expected_limit is None
    return expected_limit is not None and int(actual_limit) == expected_limit


def _run(
    cmd: list[str],
    *,
    env: dict[str, str],
    dry_run: bool,
    allow_failure: bool = False,
) -> dict[str, object]:
    if dry_run:
        return {"cmd": cmd, "returncode": 0, "dry_run": True}
    if (
        env.get("MTP_PREMAP_REUSE_EXISTING_STUB_OUTPUTS") == "1"
        and len(cmd) >= 2
        and cmd[1] == "scripts/run_premap_typed_consumer_stub.py"
        and "--output-json" in cmd
    ):
        output_index = cmd.index("--output-json") + 1
        if output_index < len(cmd):
            output_path = Path(cmd[output_index])
            output_path = output_path if output_path.is_absolute() else REPO_ROOT / output_path
            if output_path.exists() and _can_reuse_existing_stub_output(
                cmd,
                output_path,
            ):
                return {
                    "cmd": cmd,
                    "returncode": 0,
                    "reused_existing_output": True,
                    "reuse_dispatch_window_checked": True,
                    "output_json": str(output_path),
                }
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    row: dict[str, object] = {
        "cmd": cmd,
        "returncode": int(result.returncode),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(
            f"command failed with code {result.returncode}: {' '.join(cmd)}\n"
            f"stdout tail:\n{result.stdout[-4000:]}\n"
            f"stderr tail:\n{result.stderr[-4000:]}"
        )
    return row


def _stub_command(
    *,
    input_json: Path,
    output_json: Path,
    device: int,
    offload_arch: str,
    macros: list[str] | tuple[str, ...] = STUB_MACROS,
    extra_args: list[str] | tuple[str, ...] = (),
) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/run_premap_typed_consumer_stub.py",
        "--device",
        str(device),
        "--input-json",
        str(input_json),
        "--offload-arch",
        offload_arch,
        "--output-json",
        str(output_json),
    ]
    for macro in macros:
        cmd.extend(["--macro", macro])
    cmd.extend(str(arg) for arg in extra_args)
    return cmd


def _future_native_dispatch_extra_args(
    args: argparse.Namespace,
    *,
    input_json: Path | None = None,
) -> list[str]:
    if args.future_native_dispatch_tail_window_size is not None:
        if input_json is None:
            raise ValueError(
                "--future-native-dispatch-tail-window-size requires an input JSON"
            )
        window_size = int(args.future_native_dispatch_tail_window_size)
        if bool(getattr(args, "dry_run", False)) and not input_json.exists():
            row_count = window_size
        else:
            row_count = _typed_consumer_input_row_count(input_json)
        return [
            "--dispatch-row-offset",
            str(max(0, row_count - window_size)),
            "--dispatch-row-limit",
            str(row_count),
        ]
    extra_args = [
        "--dispatch-row-offset",
        str(int(args.future_native_dispatch_row_offset)),
    ]
    if args.future_native_dispatch_row_limit is not None:
        extra_args.extend(
            [
                "--dispatch-row-limit",
                str(int(args.future_native_dispatch_row_limit)),
            ]
        )
    return extra_args


def _indexed_output_path(path: Path, input_index: int) -> Path:
    if input_index == 0:
        return path
    return path.with_name(f"{path.stem}_input{input_index:04d}{path.suffix}")


def _stub_summary(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys}


def _preflight_command(
    *,
    output_json: Path,
    summary_only: bool,
    defer_runner: bool,
    defer_artifact: bool = False,
    allow_bootstrap_preflight: bool = False,
    allow_runner_self_finalization: bool = False,
) -> list[str]:
    cmd = [sys.executable, "scripts/run_premap_lab_preflight.py"]
    if summary_only:
        cmd.append("--summary-only")
    if defer_runner:
        cmd.append("--defer-online-prelaunch-runner-evidence")
    if defer_artifact:
        cmd.append("--defer-online-prelaunch-artifact-evidence")
    if allow_bootstrap_preflight:
        cmd.append("--allow-bootstrap-preflight")
    if allow_runner_self_finalization:
        cmd.append("--allow-online-runner-self-finalization")
    cmd.extend(["--output-json", str(output_json)])
    return cmd


def _artifact_check_command(
    *,
    runner_json: Path,
    preflight_json: Path,
    status_json: Path,
    output_json: Path,
    min_online_inputs: int = 1,
    allow_bootstrap_preflight: bool = False,
) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/check_premap_online_native_stub_canary_artifacts.py",
        "--runner-json",
        str(runner_json),
        "--preflight-json",
        str(preflight_json),
        "--status-json",
        str(status_json),
        "--output-json",
        str(output_json),
        "--require-all-field-mirror-stubs",
        "--min-online-inputs",
        str(int(min_online_inputs)),
    ]
    if allow_bootstrap_preflight:
        cmd.append("--allow-bootstrap-preflight")
    return cmd


def _preflight_status_check_command(
    *,
    summary_json: Path,
    output_json: Path,
) -> list[str]:
    return [
        sys.executable,
        "scripts/check_premap_lab_preflight_summary.py",
        str(summary_json),
        "--output-json",
        str(output_json),
    ]


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    return {}


def _pointer_source_observer_check_summary(
    path: Path,
    *,
    required: bool,
) -> dict[str, object]:
    resolved = _resolve_repo_path(path)
    if not resolved.exists():
        return {
            "required": bool(required),
            "present": False,
            "path": str(resolved),
            "passed": False,
            "gate_passed": not bool(required),
            "failures": ["pointer_source_observer_check_missing"]
            if required
            else [],
        }
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "required": bool(required),
            "present": True,
            "path": str(resolved),
            "passed": False,
            "gate_passed": False,
            "failures": [f"pointer_source_observer_check_read_error:{type(exc).__name__}"],
        }
    if not isinstance(payload, dict):
        return {
            "required": bool(required),
            "present": True,
            "path": str(resolved),
            "passed": False,
            "gate_passed": False,
            "failures": ["pointer_source_observer_check_not_object"],
        }
    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)
    evidence_passed = not failures
    return {
        "required": bool(required),
        "present": True,
        "path": str(resolved),
        "passed": evidence_passed,
        "gate_passed": evidence_passed,
        "failures": failures,
        "mode": payload.get("mode"),
        "observer_seen": payload.get("observer_seen"),
        "observer_available": payload.get("observer_available"),
        "observer_vllm_device": payload.get("observer_vllm_device"),
        "sample_count": payload.get("sample_count"),
        "requested_output_token_count": payload.get("requested_output_token_count"),
    }


def _apply_pointer_source_observer_gate(
    payload: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    pointer_source_observer_check = _pointer_source_observer_check_summary(
        args.pointer_source_observer_check_json,
        required=bool(args.require_pointer_source_observer_check),
    )
    pointer_source_observer_gate_passed = (
        pointer_source_observer_check.get("gate_passed") is True
    )
    payload["pointer_source_observer_check"] = pointer_source_observer_check
    payload["pointer_source_observer_check_json"] = str(
        _resolve_repo_path(args.pointer_source_observer_check_json)
    )
    payload["pointer_source_observer_check_required"] = bool(
        args.require_pointer_source_observer_check
    )
    payload["pointer_source_observer_check_passed"] = (
        pointer_source_observer_check.get("passed") is True
    )
    payload["pointer_source_observer_gate_passed"] = (
        pointer_source_observer_gate_passed
    )
    if not pointer_source_observer_gate_passed:
        failures = payload.get("failures")
        failure_list = list(failures) if isinstance(failures, list) else []
        if "pointer_source_observer_check_not_passed" not in failure_list:
            failure_list.append("pointer_source_observer_check_not_passed")
        payload["failures"] = failure_list
        payload["passed"] = False
    return payload


def _typed_consumer_input_row_count(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"typed consumer input is not a JSON object: {path}")
    for container_name in ("_meta", "_export_context"):
        container = payload.get(container_name)
        if not isinstance(container, dict):
            continue
        value = container.get("row_count")
        if value is None:
            continue
        if isinstance(value, bool):
            raise ValueError(f"{container_name}.row_count must be an integer in {path}")
        row_count = int(value)
        if row_count <= 0:
            raise ValueError(f"{container_name}.row_count must be positive in {path}")
        return row_count
    value = payload.get("row_count")
    if value is not None:
        if isinstance(value, bool):
            raise ValueError(f"row_count must be an integer in {path}")
        row_count = int(value)
        if row_count <= 0:
            raise ValueError(f"row_count must be positive in {path}")
        return row_count
    raise ValueError(
        "typed consumer input does not expose row_count in _meta, "
        f"_export_context, or top level: {path}"
    )


def write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_canary(args: argparse.Namespace) -> dict[str, object]:
    if args.future_native_dispatch_tail_window_size is not None:
        if int(args.future_native_dispatch_tail_window_size) <= 0:
            raise ValueError("--future-native-dispatch-tail-window-size must be > 0")
    else:
        if int(args.future_native_dispatch_row_offset) < 0:
            raise ValueError("--future-native-dispatch-row-offset must be >= 0")
        if (
            args.future_native_dispatch_row_limit is not None
            and int(args.future_native_dispatch_row_limit)
            <= int(args.future_native_dispatch_row_offset)
        ):
            raise ValueError(
                "--future-native-dispatch-row-limit must be greater than "
                "--future-native-dispatch-row-offset"
            )
    trace_config = _resolve_repo_path(args.trace_config)
    output_dir = trace_output_dir(trace_config)
    performance_path = output_dir / "performance_summary.json"
    env = _base_env(gpu_index=args.gpu_index)
    steps: dict[str, object] = {}
    pointer_source_observer_check = _pointer_source_observer_check_summary(
        args.pointer_source_observer_check_json,
        required=bool(args.require_pointer_source_observer_check),
    )
    pointer_source_observer_gate_passed = (
        pointer_source_observer_check.get("gate_passed") is True
    )

    if not args.skip_trace:
        steps["trace"] = _run(
            [sys.executable, "scripts/trace_router_mtp_vllm.py", str(trace_config)],
            env=env,
            dry_run=bool(args.dry_run),
        )
    max_online_inputs = int(args.max_online_inputs)
    if args.dry_run:
        input_paths = [Path("<dry-run-online-input>")]
    else:
        input_paths = exported_inputs_from_performance(
            performance_path,
            max_inputs=None if max_online_inputs == 0 else max_online_inputs,
        )
        _require_min_online_inputs(
            input_paths,
            min_online_inputs=int(args.min_artifact_online_inputs),
            performance_path=performance_path,
        )
    input_path = input_paths[0]
    input_row_counts = (
        []
        if args.dry_run
        else [_typed_consumer_input_row_count(path) for path in input_paths]
    )

    stub_output = _resolve_repo_path(args.stub_output_json)
    if not args.skip_stub:
        steps["native_stub"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    per_field_stub_output = _resolve_repo_path(args.per_field_stub_output_json)
    if not args.skip_stub and not args.skip_per_field_stub:
        steps["native_stub_per_field"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=per_field_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=PER_FIELD_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    envelope_mirror_stub_output = _resolve_repo_path(
        args.envelope_mirror_stub_output_json
    )
    if not args.skip_stub and not args.skip_envelope_mirror_stub:
        steps["native_stub_kernel_envelope_mirror"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=envelope_mirror_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=ENVELOPE_MIRROR_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    packed_weight_mirror_stub_output = _resolve_repo_path(
        args.packed_weight_mirror_stub_output_json
    )
    if not args.skip_stub and not args.skip_packed_weight_mirror_stub:
        steps["native_stub_packed_weight_mirror"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=packed_weight_mirror_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=PACKED_WEIGHT_MIRROR_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    aux_metadata_mirror_stub_output = _resolve_repo_path(
        args.aux_metadata_mirror_stub_output_json
    )
    if not args.skip_stub and not args.skip_aux_metadata_mirror_stub:
        steps["native_stub_aux_metadata_mirror"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=aux_metadata_mirror_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=AUX_METADATA_MIRROR_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    descriptor_ptr_mirror_stub_output = _resolve_repo_path(
        args.descriptor_ptr_mirror_stub_output_json
    )
    if not args.skip_stub and not args.skip_descriptor_ptr_mirror_stub:
        steps["native_stub_descriptor_ptr_mirror"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=descriptor_ptr_mirror_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=DESCRIPTOR_PTR_MIRROR_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    kernel_side_compatible_stub_output = _resolve_repo_path(
        args.kernel_side_compatible_stub_output_json
    )
    if not args.skip_stub and not args.skip_kernel_side_compatible_stub:
        steps["native_stub_kernel_side_compatible_consumer_abi"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=kernel_side_compatible_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=KERNEL_SIDE_COMPATIBLE_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    future_kernel_args_stub_output = _resolve_repo_path(
        args.future_kernel_args_stub_output_json
    )
    if not args.skip_stub and not args.skip_future_kernel_args_stub:
        steps["native_stub_future_kernel_consumer_args"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=future_kernel_args_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=FUTURE_KERNEL_ARGS_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    future_kernel_args_descriptor_ptr_stub_output = _resolve_repo_path(
        args.future_kernel_args_descriptor_ptr_stub_output_json
    )
    future_kernel_args_packed_weight_stub_output = _resolve_repo_path(
        args.future_kernel_args_packed_weight_stub_output_json
    )
    future_kernel_args_aux_metadata_stub_output = _resolve_repo_path(
        args.future_kernel_args_aux_metadata_stub_output_json
    )
    future_kernel_args_compatible_path_stub_output = _resolve_repo_path(
        args.future_kernel_args_compatible_path_stub_output_json
    )
    future_kernel_native_consumer_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_stub_output_json
    )
    future_kernel_native_consumer_descriptor_ptr_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_descriptor_ptr_stub_output_json
    )
    future_kernel_native_consumer_packed_weight_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_packed_weight_stub_output_json
    )
    future_kernel_native_consumer_aux_metadata_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_aux_metadata_stub_output_json
    )
    future_kernel_native_consumer_launch_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_launch_stub_output_json
    )
    future_kernel_native_consumer_launch_descriptor_ptr_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_launch_descriptor_ptr_stub_output_json
    )
    future_kernel_native_consumer_launch_packed_weight_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_launch_packed_weight_stub_output_json
    )
    future_kernel_native_consumer_launch_aux_metadata_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_launch_aux_metadata_stub_output_json
    )
    future_kernel_native_consumer_dispatch_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_dispatch_stub_output_json
    )
    future_kernel_native_consumer_dispatch_descriptor_ptr_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_dispatch_descriptor_ptr_stub_output_json
    )
    future_kernel_native_consumer_dispatch_packed_weight_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_dispatch_packed_weight_stub_output_json
    )
    future_kernel_native_consumer_dispatch_aux_metadata_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_dispatch_aux_metadata_stub_output_json
    )
    future_kernel_native_consumer_request_ptr_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_request_ptr_stub_output_json
    )
    future_kernel_native_consumer_request_launch_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_request_launch_stub_output_json
    )
    future_kernel_native_consumer_request_launch_ptr_stub_output = _resolve_repo_path(
        args.future_kernel_native_consumer_request_launch_ptr_stub_output_json
    )
    future_args_extra_stubs = (
        (
            "native_stub_future_kernel_args_descriptor_ptr_mirror",
            future_kernel_args_descriptor_ptr_stub_output,
            FUTURE_KERNEL_ARGS_DESCRIPTOR_PTR_STUB_MACROS,
        ),
        (
            "native_stub_future_kernel_args_packed_weight_mirror",
            future_kernel_args_packed_weight_stub_output,
            FUTURE_KERNEL_ARGS_PACKED_WEIGHT_STUB_MACROS,
        ),
        (
            "native_stub_future_kernel_args_aux_metadata_mirror",
            future_kernel_args_aux_metadata_stub_output,
            FUTURE_KERNEL_ARGS_AUX_METADATA_STUB_MACROS,
        ),
    )
    if (
        not args.skip_stub
        and not args.skip_future_kernel_args_stub
        and not args.skip_future_kernel_args_extra_field_stubs
    ):
        for step_label, output_path, macros in future_args_extra_stubs:
            steps[step_label] = _run(
                _stub_command(
                    input_json=input_path,
                    output_json=output_path,
                    device=int(args.stub_device),
                    offload_arch=str(args.offload_arch),
                    macros=macros,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    if not args.skip_stub and not args.skip_future_kernel_args_compatible_path_stub:
        steps["native_stub_future_kernel_args_compatible_consumer_path"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=future_kernel_args_compatible_path_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=FUTURE_KERNEL_ARGS_COMPATIBLE_PATH_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    if not args.skip_stub and not args.skip_future_kernel_native_consumer_stub:
        steps["native_stub_future_kernel_native_consumer_abi"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=future_kernel_native_consumer_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=FUTURE_KERNEL_NATIVE_CONSUMER_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    future_native_extra_stubs = (
        (
            "native_stub_future_kernel_native_consumer_descriptor_ptr_mirror",
            future_kernel_native_consumer_descriptor_ptr_stub_output,
            FUTURE_KERNEL_NATIVE_CONSUMER_DESCRIPTOR_PTR_STUB_MACROS,
        ),
        (
            "native_stub_future_kernel_native_consumer_packed_weight_mirror",
            future_kernel_native_consumer_packed_weight_stub_output,
            FUTURE_KERNEL_NATIVE_CONSUMER_PACKED_WEIGHT_STUB_MACROS,
        ),
        (
            "native_stub_future_kernel_native_consumer_aux_metadata_mirror",
            future_kernel_native_consumer_aux_metadata_stub_output,
            FUTURE_KERNEL_NATIVE_CONSUMER_AUX_METADATA_STUB_MACROS,
        ),
    )
    if (
        not args.skip_stub
        and not args.skip_future_kernel_native_consumer_stub
        and not args.skip_future_kernel_native_consumer_extra_field_stubs
    ):
        for step_label, output_path, macros in future_native_extra_stubs:
            steps[step_label] = _run(
                _stub_command(
                    input_json=input_path,
                    output_json=output_path,
                    device=int(args.stub_device),
                    offload_arch=str(args.offload_arch),
                    macros=macros,
                ),
                env=env,
                dry_run=bool(args.dry_run),
            )
    if not args.skip_stub and not args.skip_future_kernel_native_consumer_request_ptr_stub:
        steps["native_stub_future_kernel_native_consumer_request_ptr_abi"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=future_kernel_native_consumer_request_ptr_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    if not args.skip_stub and not args.skip_future_kernel_native_consumer_request_launch_stub:
        steps["native_stub_future_kernel_native_consumer_request_launch_abi"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=future_kernel_native_consumer_request_launch_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    if (
        not args.skip_stub
        and not args.skip_future_kernel_native_consumer_request_launch_ptr_stub
    ):
        steps["native_stub_future_kernel_native_consumer_request_launch_ptr_abi"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=future_kernel_native_consumer_request_launch_ptr_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    if not args.skip_stub and not args.skip_future_kernel_native_consumer_stub:
        steps["native_stub_future_kernel_native_consumer_dispatch_abi"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=future_kernel_native_consumer_dispatch_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_STUB_MACROS,
                extra_args=_future_native_dispatch_extra_args(
                    args,
                    input_json=input_path,
                ),
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    future_native_dispatch_extra_stubs = (
        (
            "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror",
            future_kernel_native_consumer_dispatch_descriptor_ptr_stub_output,
            FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_DESCRIPTOR_PTR_STUB_MACROS,
        ),
        (
            "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror",
            future_kernel_native_consumer_dispatch_packed_weight_stub_output,
            FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PACKED_WEIGHT_STUB_MACROS,
        ),
        (
            "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror",
            future_kernel_native_consumer_dispatch_aux_metadata_stub_output,
            FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_AUX_METADATA_STUB_MACROS,
        ),
    )
    if (
        not args.skip_stub
        and not args.skip_future_kernel_native_consumer_stub
        and not args.skip_future_kernel_native_consumer_extra_field_stubs
    ):
        for step_label, output_path, macros in future_native_dispatch_extra_stubs:
            steps[step_label] = _run(
                _stub_command(
                    input_json=input_path,
                    output_json=output_path,
                    device=int(args.stub_device),
                    offload_arch=str(args.offload_arch),
                    macros=macros,
                    extra_args=_future_native_dispatch_extra_args(
                        args,
                        input_json=input_path,
                    ),
                ),
                env=env,
                dry_run=bool(args.dry_run),
            )
    if not args.skip_stub and not args.skip_future_kernel_native_consumer_stub:
        steps["native_stub_future_kernel_native_consumer_launch_abi"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=future_kernel_native_consumer_launch_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    future_native_launch_extra_stubs = (
        (
            "native_stub_future_kernel_native_consumer_launch_descriptor_ptr_mirror",
            future_kernel_native_consumer_launch_descriptor_ptr_stub_output,
            FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_DESCRIPTOR_PTR_STUB_MACROS,
        ),
        (
            "native_stub_future_kernel_native_consumer_launch_packed_weight_mirror",
            future_kernel_native_consumer_launch_packed_weight_stub_output,
            FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_PACKED_WEIGHT_STUB_MACROS,
        ),
        (
            "native_stub_future_kernel_native_consumer_launch_aux_metadata_mirror",
            future_kernel_native_consumer_launch_aux_metadata_stub_output,
            FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_AUX_METADATA_STUB_MACROS,
        ),
    )
    if (
        not args.skip_stub
        and not args.skip_future_kernel_native_consumer_stub
        and not args.skip_future_kernel_native_consumer_extra_field_stubs
    ):
        for step_label, output_path, macros in future_native_launch_extra_stubs:
            steps[step_label] = _run(
                _stub_command(
                    input_json=input_path,
                    output_json=output_path,
                    device=int(args.stub_device),
                    offload_arch=str(args.offload_arch),
                    macros=macros,
                ),
                env=env,
                dry_run=bool(args.dry_run),
            )

    extra_input_check_summaries: list[dict[str, Any]] = []
    for input_index, extra_input_path in enumerate(input_paths[1:], start=1):
        suite: dict[str, Any] = {
            "input_index": input_index,
            "input_json": str(extra_input_path),
            "passed": True,
            "failures": [],
            "outputs": {},
        }
        for label, skip_label, macros, base_output in (
            ("native_stub", "skip_stub", STUB_MACROS, stub_output),
            (
                "native_stub_per_field",
                "skip_per_field_stub",
                PER_FIELD_STUB_MACROS,
                per_field_stub_output,
            ),
            (
                "native_stub_kernel_envelope_mirror",
                "skip_envelope_mirror_stub",
                ENVELOPE_MIRROR_STUB_MACROS,
                envelope_mirror_stub_output,
            ),
            (
                "native_stub_packed_weight_mirror",
                "skip_packed_weight_mirror_stub",
                PACKED_WEIGHT_MIRROR_STUB_MACROS,
                packed_weight_mirror_stub_output,
            ),
            (
                "native_stub_aux_metadata_mirror",
                "skip_aux_metadata_mirror_stub",
                AUX_METADATA_MIRROR_STUB_MACROS,
                aux_metadata_mirror_stub_output,
            ),
            (
                "native_stub_descriptor_ptr_mirror",
                "skip_descriptor_ptr_mirror_stub",
                DESCRIPTOR_PTR_MIRROR_STUB_MACROS,
                descriptor_ptr_mirror_stub_output,
            ),
            (
                "native_stub_kernel_side_compatible_consumer_abi",
                "skip_kernel_side_compatible_stub",
                KERNEL_SIDE_COMPATIBLE_STUB_MACROS,
                kernel_side_compatible_stub_output,
            ),
            (
                "native_stub_future_kernel_consumer_args",
                "skip_future_kernel_args_stub",
                FUTURE_KERNEL_ARGS_STUB_MACROS,
                future_kernel_args_stub_output,
            ),
            (
                "native_stub_future_kernel_args_descriptor_ptr_mirror",
                "skip_future_kernel_args_extra_field_stubs",
                FUTURE_KERNEL_ARGS_DESCRIPTOR_PTR_STUB_MACROS,
                future_kernel_args_descriptor_ptr_stub_output,
            ),
            (
                "native_stub_future_kernel_args_packed_weight_mirror",
                "skip_future_kernel_args_extra_field_stubs",
                FUTURE_KERNEL_ARGS_PACKED_WEIGHT_STUB_MACROS,
                future_kernel_args_packed_weight_stub_output,
            ),
            (
                "native_stub_future_kernel_args_aux_metadata_mirror",
                "skip_future_kernel_args_extra_field_stubs",
                FUTURE_KERNEL_ARGS_AUX_METADATA_STUB_MACROS,
                future_kernel_args_aux_metadata_stub_output,
            ),
            (
                "native_stub_future_kernel_args_compatible_consumer_path",
                "skip_future_kernel_args_compatible_path_stub",
                FUTURE_KERNEL_ARGS_COMPATIBLE_PATH_STUB_MACROS,
                future_kernel_args_compatible_path_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_abi",
                "skip_future_kernel_native_consumer_stub",
                FUTURE_KERNEL_NATIVE_CONSUMER_STUB_MACROS,
                future_kernel_native_consumer_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_descriptor_ptr_mirror",
                "skip_future_kernel_native_consumer_extra_field_stubs",
                FUTURE_KERNEL_NATIVE_CONSUMER_DESCRIPTOR_PTR_STUB_MACROS,
                future_kernel_native_consumer_descriptor_ptr_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_packed_weight_mirror",
                "skip_future_kernel_native_consumer_extra_field_stubs",
                FUTURE_KERNEL_NATIVE_CONSUMER_PACKED_WEIGHT_STUB_MACROS,
                future_kernel_native_consumer_packed_weight_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_aux_metadata_mirror",
                "skip_future_kernel_native_consumer_extra_field_stubs",
                FUTURE_KERNEL_NATIVE_CONSUMER_AUX_METADATA_STUB_MACROS,
                future_kernel_native_consumer_aux_metadata_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_launch_abi",
                "skip_future_kernel_native_consumer_stub",
                FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_STUB_MACROS,
                future_kernel_native_consumer_launch_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_launch_descriptor_ptr_mirror",
                "skip_future_kernel_native_consumer_extra_field_stubs",
                FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_DESCRIPTOR_PTR_STUB_MACROS,
                future_kernel_native_consumer_launch_descriptor_ptr_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_launch_packed_weight_mirror",
                "skip_future_kernel_native_consumer_extra_field_stubs",
                FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_PACKED_WEIGHT_STUB_MACROS,
                future_kernel_native_consumer_launch_packed_weight_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_launch_aux_metadata_mirror",
                "skip_future_kernel_native_consumer_extra_field_stubs",
                FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_AUX_METADATA_STUB_MACROS,
                future_kernel_native_consumer_launch_aux_metadata_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_dispatch_abi",
                "skip_future_kernel_native_consumer_stub",
                FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_STUB_MACROS,
                future_kernel_native_consumer_dispatch_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror",
                "skip_future_kernel_native_consumer_extra_field_stubs",
                FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_DESCRIPTOR_PTR_STUB_MACROS,
                future_kernel_native_consumer_dispatch_descriptor_ptr_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror",
                "skip_future_kernel_native_consumer_extra_field_stubs",
                FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PACKED_WEIGHT_STUB_MACROS,
                future_kernel_native_consumer_dispatch_packed_weight_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror",
                "skip_future_kernel_native_consumer_extra_field_stubs",
                FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_AUX_METADATA_STUB_MACROS,
                future_kernel_native_consumer_dispatch_aux_metadata_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_request_ptr_abi",
                "skip_future_kernel_native_consumer_request_ptr_stub",
                FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_STUB_MACROS,
                future_kernel_native_consumer_request_ptr_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_request_launch_abi",
                "skip_future_kernel_native_consumer_request_launch_stub",
                FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_STUB_MACROS,
                future_kernel_native_consumer_request_launch_stub_output,
            ),
            (
                "native_stub_future_kernel_native_consumer_request_launch_ptr_abi",
                "skip_future_kernel_native_consumer_request_launch_ptr_stub",
                FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_STUB_MACROS,
                future_kernel_native_consumer_request_launch_ptr_stub_output,
            ),
        ):
            if bool(args.skip_stub) or bool(getattr(args, skip_label, False)):
                continue
            if (
                label.startswith("native_stub_future_kernel_args_")
                and bool(args.skip_future_kernel_args_stub)
            ):
                continue
            if (
                label.startswith("native_stub_future_kernel_native_consumer_")
                and bool(args.skip_future_kernel_native_consumer_stub)
            ):
                continue
            output_path = _indexed_output_path(base_output, input_index)
            step_key = f"{label}_input{input_index:04d}"
            stub_extra_args = (
                _future_native_dispatch_extra_args(
                    args,
                    input_json=extra_input_path,
                )
                if label.startswith(
                    "native_stub_future_kernel_native_consumer_dispatch_"
                )
                else []
            )
            steps[step_key] = _run(
                _stub_command(
                    input_json=extra_input_path,
                    output_json=output_path,
                    device=int(args.stub_device),
                    offload_arch=str(args.offload_arch),
                    macros=macros,
                    extra_args=stub_extra_args,
                ),
                env=env,
                dry_run=bool(args.dry_run),
            )
            stub_result = {} if args.dry_run else _load_json_if_exists(output_path)
            output_summary = _stub_summary(
                stub_result,
                (
                    "passed",
                    "ok",
                    "row_count",
                    "row_ok_count",
                    "error_count",
                    "payload_bytes",
                    "passed_to_kernel",
                    "changes_kernel_launch_args",
                    "kernel_consumer_envelope_checked",
                    "kernel_consumer_envelope_payload_bytes",
                    "kernel_consumer_envelope_passed_to_kernel",
                    "kernel_side_consumer_path_checked",
                    "kernel_side_consumer_path_name",
                    "kernel_side_consumer_path_row_count",
                    "kernel_side_consumer_path_row_ok_count",
                    "kernel_side_consumer_path_error_count",
                    "kernel_side_consumer_path_payload_bytes",
                    "kernel_side_consumer_path_passed_to_kernel",
                    "kernel_side_consumer_path_changes_kernel_launch_args",
                    "kernel_side_consumer_path_current_wna16_arg_compatible",
                    "kernel_side_compatible_consumer_checked",
                    "kernel_side_compatible_consumer_name",
                    "kernel_side_compatible_consumer_mode",
                    "kernel_side_compatible_consumer_source",
                    "kernel_side_compatible_consumer_row_count",
                    "kernel_side_compatible_consumer_row_ok_count",
                    "kernel_side_compatible_consumer_error_count",
                    "kernel_side_compatible_consumer_payload_bytes",
                    "kernel_side_compatible_consumer_passed_to_kernel",
                    "kernel_side_compatible_consumer_changes_kernel_launch_args",
                    "kernel_side_compatible_consumer_current_wna16_arg_compatible",
                    "future_kernel_consumer_args_checked",
                    "future_kernel_consumer_args_name",
                    "future_kernel_consumer_args_mode",
                    "future_kernel_consumer_args_source",
                    "future_kernel_consumer_args_row_count",
                    "future_kernel_consumer_args_row_ok_count",
                    "future_kernel_consumer_args_error_count",
                    "future_kernel_consumer_args_payload_bytes",
                    "future_kernel_consumer_args_passed_to_kernel",
                    "future_kernel_consumer_args_changes_kernel_launch_args",
                    "future_kernel_consumer_args_current_wna16_arg_compatible",
                    "future_kernel_consumer_args_requires_wna16_arg_reinterpretation",
                    "future_kernel_consumer_args_field_mask",
                    "future_kernel_consumer_args_required_field_mask",
                    "future_kernel_consumer_args_single_field_mirror_checked",
                    "future_kernel_consumer_args_single_field_mirror_field_name",
                    "future_kernel_consumer_args_single_field_mirror_row_count",
                    "future_kernel_consumer_args_single_field_mirror_row_ok_count",
                    "future_kernel_consumer_args_single_field_mirror_error_count",
                    *FUTURE_KERNEL_ARGS_LAYOUT_SUMMARY_KEYS,
                    "future_kernel_args_compatible_consumer_path_checked",
                    "future_kernel_args_compatible_consumer_path_name",
                    "future_kernel_args_compatible_consumer_path_mode",
                    "future_kernel_args_compatible_consumer_path_source",
                    "future_kernel_args_compatible_consumer_path_row_count",
                    "future_kernel_args_compatible_consumer_path_row_ok_count",
                    "future_kernel_args_compatible_consumer_path_error_count",
                    "future_kernel_args_compatible_consumer_path_payload_bytes",
                    "future_kernel_args_compatible_consumer_path_passed_to_kernel",
                    "future_kernel_args_compatible_consumer_path_changes_kernel_launch_args",
                    "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible",
                    "future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation",
                    "future_kernel_native_consumer_abi_name",
                    "future_kernel_native_consumer_checked",
                    "future_kernel_native_consumer_mode",
                    "future_kernel_native_consumer_source",
                    "future_kernel_native_consumer_params_struct_size",
                    "future_kernel_native_consumer_params_struct_align",
                    "future_kernel_native_consumer_result_struct_size",
                    "future_kernel_native_consumer_result_struct_align",
                    "future_kernel_native_consumer_params_offset_descriptor_ptr",
                    "future_kernel_native_consumer_params_offset_packed_weight_descriptor",
                    "future_kernel_native_consumer_params_offset_scale_metadata_handle",
                    "future_kernel_native_consumer_params_offset_aux_metadata_handle",
                    "future_kernel_native_consumer_params_offset_expert_id",
                    "future_kernel_native_consumer_params_offset_address_key_hash",
                    "future_kernel_native_consumer_params_offset_row_count",
                    "future_kernel_native_consumer_params_offset_field_mask",
                    "future_kernel_native_consumer_params_offset_payload_bytes",
                    "future_kernel_native_consumer_params_offset_flags",
                    "future_kernel_native_consumer_row_count",
                    "future_kernel_native_consumer_row_ok_count",
                    "future_kernel_native_consumer_error_count",
                    "future_kernel_native_consumer_payload_bytes",
                    "future_kernel_native_consumer_passed_to_kernel",
                    "future_kernel_native_consumer_changes_kernel_launch_args",
                    "future_kernel_native_consumer_current_wna16_arg_compatible",
                    "future_kernel_native_consumer_requires_wna16_arg_reinterpretation",
                    "future_kernel_native_consumer_field_mask",
                    "future_kernel_native_consumer_required_field_mask",
                    "future_kernel_native_consumer_single_field_mirror_checked",
                    "future_kernel_native_consumer_single_field_mirror_field_name",
                    "future_kernel_native_consumer_single_field_mirror_row_count",
                    "future_kernel_native_consumer_single_field_mirror_row_ok_count",
                    "future_kernel_native_consumer_single_field_mirror_error_count",
                    "future_kernel_native_launch_consumer_abi_name",
                    "future_kernel_native_launch_consumer_checked",
                    "future_kernel_native_launch_consumer_mode",
                    "future_kernel_native_launch_consumer_source",
                    "future_kernel_native_launch_consumer_version",
                    "future_kernel_native_launch_consumer_launch_struct_size",
                    "future_kernel_native_launch_consumer_launch_struct_align",
                    "future_kernel_native_launch_consumer_params_struct_size",
                    "future_kernel_native_launch_consumer_params_struct_align",
                    "future_kernel_native_launch_consumer_result_struct_size",
                    "future_kernel_native_launch_consumer_result_struct_align",
                    "future_kernel_native_launch_consumer_offset_params",
                    "future_kernel_native_launch_consumer_offset_abi_version",
                    "future_kernel_native_launch_consumer_offset_params_struct_size",
                    "future_kernel_native_launch_consumer_offset_result_struct_size",
                    "future_kernel_native_launch_consumer_offset_row_stride",
                    "future_kernel_native_launch_consumer_offset_payload_bytes",
                    "future_kernel_native_launch_consumer_offset_flags",
                    "future_kernel_native_launch_consumer_row_stride",
                    "future_kernel_native_launch_consumer_row_count",
                    "future_kernel_native_launch_consumer_row_ok_count",
                    "future_kernel_native_launch_consumer_error_count",
                    "future_kernel_native_launch_consumer_payload_bytes",
                    "future_kernel_native_launch_consumer_passed_to_kernel",
                    "future_kernel_native_launch_consumer_changes_kernel_launch_args",
                    "future_kernel_native_launch_consumer_current_wna16_arg_compatible",
                    "future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation",
                    "future_kernel_native_launch_consumer_field_mask",
                    "future_kernel_native_launch_consumer_required_field_mask",
                    "future_kernel_native_launch_consumer_single_field_mirror_checked",
                    "future_kernel_native_launch_consumer_single_field_mirror_field_name",
                    "future_kernel_native_launch_consumer_single_field_mirror_row_count",
                    "future_kernel_native_launch_consumer_single_field_mirror_row_ok_count",
                    "future_kernel_native_launch_consumer_single_field_mirror_error_count",
                    "future_kernel_native_dispatch_consumer_abi_name",
                    "future_kernel_native_dispatch_consumer_checked",
                    "future_kernel_native_dispatch_consumer_mode",
                    "future_kernel_native_dispatch_consumer_source",
                    "future_kernel_native_dispatch_consumer_version",
                    "future_kernel_native_dispatch_consumer_dispatch_struct_size",
                    "future_kernel_native_dispatch_consumer_dispatch_struct_align",
                    "future_kernel_native_dispatch_consumer_result_struct_size",
                    "future_kernel_native_dispatch_consumer_result_struct_align",
                    "future_kernel_native_dispatch_consumer_offset_launch",
                    "future_kernel_native_dispatch_consumer_offset_dispatch_version",
                    "future_kernel_native_dispatch_consumer_offset_grid_x",
                    "future_kernel_native_dispatch_consumer_offset_block_x",
                    "future_kernel_native_dispatch_consumer_offset_shared_mem_bytes",
                    "future_kernel_native_dispatch_consumer_offset_row_offset",
                    "future_kernel_native_dispatch_consumer_offset_row_limit",
                    "future_kernel_native_dispatch_consumer_offset_rows_per_program",
                    "future_kernel_native_dispatch_consumer_offset_payload_bytes",
                    "future_kernel_native_dispatch_consumer_offset_flags",
                    "future_kernel_native_dispatch_consumer_grid_x",
                    "future_kernel_native_dispatch_consumer_block_x",
                    "future_kernel_native_dispatch_consumer_shared_mem_bytes",
                    "future_kernel_native_dispatch_consumer_row_offset",
                    "future_kernel_native_dispatch_consumer_row_limit",
                    "future_kernel_native_dispatch_consumer_rows_per_program",
                    "future_kernel_native_dispatch_consumer_active_rows",
                    "future_kernel_native_dispatch_consumer_launch_threads",
                    "future_kernel_native_dispatch_consumer_program_iteration_checked",
                    "future_kernel_native_dispatch_consumer_row_assignment_formula",
                    "future_kernel_native_dispatch_consumer_program_count",
                    "future_kernel_native_dispatch_consumer_full_program_count",
                    "future_kernel_native_dispatch_consumer_last_program_active_rows",
                    "future_kernel_native_dispatch_consumer_inactive_lane_count",
                    "future_kernel_native_dispatch_consumer_first_program_row_offset",
                    "future_kernel_native_dispatch_consumer_last_program_row_offset",
                    "future_kernel_native_dispatch_consumer_program_iteration_hash",
                    "future_kernel_native_dispatch_consumer_launch_geometry_checked",
                    "future_kernel_native_dispatch_consumer_launch_covers_active_rows",
                    "future_kernel_native_dispatch_consumer_launch_minimal_cover",
                    "future_kernel_native_dispatch_consumer_row_count",
                    "future_kernel_native_dispatch_consumer_row_ok_count",
                    "future_kernel_native_dispatch_consumer_error_count",
                    "future_kernel_native_dispatch_consumer_payload_bytes",
                    "future_kernel_native_dispatch_consumer_passed_to_kernel",
                    "future_kernel_native_dispatch_consumer_changes_kernel_launch_args",
                    "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible",
                    "future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation",
                    "future_kernel_native_dispatch_consumer_field_mask",
                    "future_kernel_native_dispatch_consumer_required_field_mask",
                    "future_kernel_native_dispatch_consumer_single_field_mirror_checked",
                    "future_kernel_native_dispatch_consumer_single_field_mirror_field_name",
                    "future_kernel_native_dispatch_consumer_single_field_mirror_row_count",
                    "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count",
                    "future_kernel_native_dispatch_consumer_single_field_mirror_error_count",
                    *FUTURE_KERNEL_NATIVE_DISPATCH_CONSUMER_SUMMARY_KEYS,
                    *FUTURE_KERNEL_NATIVE_REQUEST_PTR_CONSUMER_SUMMARY_KEYS,
                    *FUTURE_KERNEL_NATIVE_REQUEST_LAUNCH_CONSUMER_SUMMARY_KEYS,
                    *FUTURE_KERNEL_NATIVE_REQUEST_LAUNCH_PTR_CONSUMER_SUMMARY_KEYS,
                    "single_field_mirror_checked",
                    "single_field_mirror_field_name",
                    "single_field_mirror_row_count",
                    "single_field_mirror_row_ok_count",
                    "single_field_mirror_error_count",
                    "input_json",
                ),
            )
            output_entry = {
                "output_json": str(output_path),
                "summary": output_summary,
            }
            suite_outputs = suite["outputs"]
            if isinstance(suite_outputs, dict):
                suite_outputs[label] = output_entry
            if not args.dry_run:
                if stub_result.get("passed") is not True:
                    suite["passed"] = False
                    suite["failures"].append(f"{label}_not_passed")
                if stub_result.get("input_json") is None:
                    suite["passed"] = False
                    suite["failures"].append(f"{label}_input_json_missing")
                elif _resolve_repo_path(str(stub_result.get("input_json"))) != extra_input_path:
                    suite["passed"] = False
                    suite["failures"].append(f"{label}_input_json_mismatch")
        extra_input_check_summaries.append(suite)
    preflight_output = _resolve_repo_path(args.preflight_output_json)
    preflight_status_output = _resolve_repo_path(args.preflight_status_output_json)
    preflight_status_check_output = _resolve_repo_path(
        args.preflight_status_check_output_json
    )
    if not args.skip_preflight:
        # Stage-1 preflight runs before this runner JSON and its artifact
        # consistency report exist, so it explicitly defers those two
        # self-referential evidence rows. The final preflight below is strict
        # no-defer and is the only result accepted as a lab gate.
        steps["preflight"] = _run(
            _preflight_command(
                output_json=preflight_output,
                summary_only=False,
                defer_runner=True,
                defer_artifact=True,
                allow_bootstrap_preflight=True,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
        steps["preflight_status"] = _run(
            _preflight_command(
                output_json=preflight_status_output,
                summary_only=True,
                defer_runner=True,
                defer_artifact=True,
                allow_bootstrap_preflight=True,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )

    stub_payload = {} if args.dry_run else _load_json_if_exists(stub_output)
    per_field_stub_payload = (
        {} if args.dry_run else _load_json_if_exists(per_field_stub_output)
    )
    envelope_mirror_stub_payload = (
        {} if args.dry_run else _load_json_if_exists(envelope_mirror_stub_output)
    )
    packed_weight_mirror_stub_payload = (
        {} if args.dry_run else _load_json_if_exists(packed_weight_mirror_stub_output)
    )
    aux_metadata_mirror_stub_payload = (
        {} if args.dry_run else _load_json_if_exists(aux_metadata_mirror_stub_output)
    )
    descriptor_ptr_mirror_stub_payload = (
        {} if args.dry_run else _load_json_if_exists(descriptor_ptr_mirror_stub_output)
    )
    kernel_side_compatible_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(kernel_side_compatible_stub_output)
    )
    future_kernel_args_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_args_stub_output)
    )
    future_kernel_args_descriptor_ptr_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_args_descriptor_ptr_stub_output)
    )
    future_kernel_args_packed_weight_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_args_packed_weight_stub_output)
    )
    future_kernel_args_aux_metadata_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_args_aux_metadata_stub_output)
    )
    future_kernel_args_compatible_path_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_args_compatible_path_stub_output)
    )
    future_kernel_native_consumer_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_native_consumer_stub_output)
    )
    future_kernel_native_consumer_descriptor_ptr_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_native_consumer_descriptor_ptr_stub_output)
    )
    future_kernel_native_consumer_packed_weight_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_native_consumer_packed_weight_stub_output)
    )
    future_kernel_native_consumer_aux_metadata_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_native_consumer_aux_metadata_stub_output)
    )
    future_kernel_native_consumer_launch_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_native_consumer_launch_stub_output)
    )
    future_kernel_native_consumer_launch_descriptor_ptr_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(
            future_kernel_native_consumer_launch_descriptor_ptr_stub_output
        )
    )
    future_kernel_native_consumer_launch_packed_weight_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(
            future_kernel_native_consumer_launch_packed_weight_stub_output
        )
    )
    future_kernel_native_consumer_launch_aux_metadata_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(
            future_kernel_native_consumer_launch_aux_metadata_stub_output
        )
    )
    future_kernel_native_consumer_dispatch_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_native_consumer_dispatch_stub_output)
    )
    future_kernel_native_consumer_dispatch_descriptor_ptr_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(
            future_kernel_native_consumer_dispatch_descriptor_ptr_stub_output
        )
    )
    future_kernel_native_consumer_dispatch_packed_weight_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(
            future_kernel_native_consumer_dispatch_packed_weight_stub_output
        )
    )
    future_kernel_native_consumer_dispatch_aux_metadata_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(
            future_kernel_native_consumer_dispatch_aux_metadata_stub_output
        )
    )
    future_kernel_native_consumer_request_ptr_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(future_kernel_native_consumer_request_ptr_stub_output)
    )
    future_kernel_native_consumer_request_launch_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(
            future_kernel_native_consumer_request_launch_stub_output
        )
    )
    future_kernel_native_consumer_request_launch_ptr_stub_payload = (
        {}
        if args.dry_run
        else _load_json_if_exists(
            future_kernel_native_consumer_request_launch_ptr_stub_output
        )
    )
    if not args.dry_run:
        _annotate_request_level_single_field_handoff(
            future_kernel_native_consumer_request_ptr_stub_payload,
            consumer_prefix="future_kernel_native_consumer_request_ptr",
            summary_prefix="future_kernel_native_consumer_request_ptr_summary",
        )
        _annotate_request_level_single_field_handoff(
            future_kernel_native_consumer_request_launch_stub_payload,
            consumer_prefix="future_kernel_native_consumer_request_launch",
            summary_prefix="future_kernel_native_consumer_request_launch_summary",
        )
        _annotate_request_level_single_field_handoff(
            future_kernel_native_consumer_request_launch_ptr_stub_payload,
            consumer_prefix="future_kernel_native_consumer_request_launch_ptr",
            summary_prefix="future_kernel_native_consumer_request_launch_ptr_summary",
        )
    preflight_payload = (
        {} if args.dry_run else _load_json_if_exists(preflight_output)
    )
    preflight_status_payload = (
        {} if args.dry_run else _load_json_if_exists(preflight_status_output)
    )

    per_field_required = not bool(args.skip_stub or args.skip_per_field_stub)
    per_field_passed = bool(
        args.dry_run
        or not per_field_required
        or (
            per_field_stub_payload.get("passed") is True
            and per_field_stub_payload.get("input_json") is not None
            and _resolve_repo_path(str(per_field_stub_payload.get("input_json")))
            == input_path
        )
    )
    envelope_mirror_required = not bool(
        args.skip_stub or args.skip_envelope_mirror_stub
    )
    envelope_mirror_passed = bool(
        args.dry_run
        or not envelope_mirror_required
        or (
            envelope_mirror_stub_payload.get("passed") is True
            and envelope_mirror_stub_payload.get("input_json") is not None
            and _resolve_repo_path(str(envelope_mirror_stub_payload.get("input_json")))
            == input_path
            and envelope_mirror_stub_payload.get("kernel_consumer_envelope_checked")
            is True
            and envelope_mirror_stub_payload.get("single_field_mirror_checked")
            is True
        )
    )
    packed_weight_mirror_required = not bool(
        args.skip_stub or args.skip_packed_weight_mirror_stub
    )
    packed_weight_mirror_passed = bool(
        args.dry_run
        or not packed_weight_mirror_required
        or (
            packed_weight_mirror_stub_payload.get("passed") is True
            and packed_weight_mirror_stub_payload.get("input_json") is not None
            and _resolve_repo_path(
                str(packed_weight_mirror_stub_payload.get("input_json"))
            )
            == input_path
            and packed_weight_mirror_stub_payload.get("single_field_mirror_checked")
            is True
            and packed_weight_mirror_stub_payload.get("single_field_mirror_field_name")
            == "packed_weight_descriptor"
        )
    )
    aux_metadata_mirror_required = not bool(
        args.skip_stub or args.skip_aux_metadata_mirror_stub
    )
    aux_metadata_mirror_passed = bool(
        args.dry_run
        or not aux_metadata_mirror_required
        or (
            aux_metadata_mirror_stub_payload.get("passed") is True
            and aux_metadata_mirror_stub_payload.get("input_json") is not None
            and _resolve_repo_path(str(aux_metadata_mirror_stub_payload.get("input_json")))
            == input_path
            and aux_metadata_mirror_stub_payload.get("single_field_mirror_checked")
            is True
            and aux_metadata_mirror_stub_payload.get("single_field_mirror_field_name")
            == "aux_metadata_handle"
        )
    )
    descriptor_ptr_mirror_required = not bool(
        args.skip_stub or args.skip_descriptor_ptr_mirror_stub
    )
    descriptor_ptr_mirror_passed = bool(
        args.dry_run
        or not descriptor_ptr_mirror_required
        or (
            descriptor_ptr_mirror_stub_payload.get("passed") is True
            and descriptor_ptr_mirror_stub_payload.get("input_json") is not None
            and _resolve_repo_path(str(descriptor_ptr_mirror_stub_payload.get("input_json")))
            == input_path
            and descriptor_ptr_mirror_stub_payload.get("single_field_mirror_checked")
            is True
            and descriptor_ptr_mirror_stub_payload.get("single_field_mirror_field_name")
            == "descriptor_ptr"
        )
    )
    kernel_side_compatible_required = not bool(
        args.skip_stub or args.skip_kernel_side_compatible_stub
    )
    kernel_side_compatible_passed = bool(
        args.dry_run
        or not kernel_side_compatible_required
        or (
            kernel_side_compatible_stub_payload.get("passed") is True
            and kernel_side_compatible_stub_payload.get("input_json") is not None
            and _resolve_repo_path(
                str(kernel_side_compatible_stub_payload.get("input_json"))
            )
            == input_path
            and kernel_side_compatible_stub_payload.get(
                "kernel_side_compatible_consumer_checked"
            )
            is True
            and kernel_side_compatible_stub_payload.get(
                "kernel_side_compatible_consumer_error_count"
            )
            == 0
            and kernel_side_compatible_stub_payload.get(
                "kernel_side_compatible_consumer_passed_to_kernel"
            )
            is False
            and kernel_side_compatible_stub_payload.get(
                "kernel_side_compatible_consumer_current_wna16_arg_compatible"
            )
            is False
        )
    )
    future_kernel_args_required = not bool(
        args.skip_stub or args.skip_future_kernel_args_stub
    )
    future_kernel_args_passed = bool(
        args.dry_run
        or not future_kernel_args_required
        or (
            future_kernel_args_stub_payload.get("passed") is True
            and future_kernel_args_stub_payload.get("input_json") is not None
            and _resolve_repo_path(str(future_kernel_args_stub_payload.get("input_json")))
            == input_path
            and future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_checked"
            )
            is True
            and future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_error_count"
            )
            == 0
            and future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_passed_to_kernel"
            )
            is False
            and future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_current_wna16_arg_compatible"
            )
            is False
            and future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation"
            )
            is False
            and _future_field_mask_ok(
                future_kernel_args_stub_payload,
                prefix="future_kernel_consumer_args",
                expected_field="scale_metadata_handle",
            )
            and future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_single_field_mirror_checked"
            )
            is True
            and future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_single_field_mirror_field_name"
            )
            == "scale_metadata_handle"
            and future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_single_field_mirror_error_count"
            )
            == 0
        )
    )

    def _future_kernel_args_field_passed(
        payload: dict[str, Any],
        *,
        expected_field: str,
    ) -> bool:
        return bool(
            payload.get("passed") is True
            and payload.get("input_json") is not None
            and _resolve_repo_path(str(payload.get("input_json"))) == input_path
            and payload.get("future_kernel_consumer_args_checked") is True
            and payload.get("future_kernel_consumer_args_error_count") == 0
            and payload.get("future_kernel_consumer_args_passed_to_kernel") is False
            and payload.get("future_kernel_consumer_args_current_wna16_arg_compatible")
            is False
            and payload.get(
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation"
            )
            is False
            and _future_field_mask_ok(
                payload,
                prefix="future_kernel_consumer_args",
                expected_field=expected_field,
            )
            and payload.get("future_kernel_consumer_args_single_field_mirror_checked")
            is True
            and payload.get("future_kernel_consumer_args_single_field_mirror_field_name")
            == expected_field
            and payload.get("future_kernel_consumer_args_single_field_mirror_error_count")
            == 0
        )

    future_kernel_args_extra_required = not bool(
        args.skip_stub
        or args.skip_future_kernel_args_stub
        or args.skip_future_kernel_args_extra_field_stubs
    )
    future_kernel_args_extra_passed = bool(
        args.dry_run
        or not future_kernel_args_extra_required
        or (
            _future_kernel_args_field_passed(
                future_kernel_args_descriptor_ptr_stub_payload,
                expected_field="descriptor_ptr",
            )
            and _future_kernel_args_field_passed(
                future_kernel_args_packed_weight_stub_payload,
                expected_field="packed_weight_descriptor",
            )
            and _future_kernel_args_field_passed(
                future_kernel_args_aux_metadata_stub_payload,
                expected_field="aux_metadata_handle",
            )
        )
    )
    future_kernel_args_compatible_path_required = not bool(
        args.skip_stub or args.skip_future_kernel_args_compatible_path_stub
    )
    future_kernel_args_compatible_path_passed = bool(
        args.dry_run
        or not future_kernel_args_compatible_path_required
        or (
            future_kernel_args_compatible_path_stub_payload.get("passed") is True
            and future_kernel_args_compatible_path_stub_payload.get("input_json")
            is not None
            and _resolve_repo_path(
                str(future_kernel_args_compatible_path_stub_payload.get("input_json"))
            )
            == input_path
            and future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_consumer_args_checked"
            )
            is True
            and future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_consumer_args_error_count"
            )
            == 0
            and future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_args_compatible_consumer_path_checked"
            )
            is True
            and future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_args_compatible_consumer_path_error_count"
            )
            == 0
            and future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_args_compatible_consumer_path_passed_to_kernel"
            )
            is False
            and future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible"
            )
            is False
            and future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation"
            )
            is False
            and future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation"
            )
            is False
        )
    )

    def _future_native_consumer_field_passed(
        payload: dict[str, Any],
        *,
        expected_field: str,
    ) -> bool:
        return bool(
            payload.get("passed") is True
            and payload.get("input_json") is not None
            and _resolve_repo_path(str(payload.get("input_json"))) == input_path
            and payload.get("future_kernel_native_consumer_checked") is True
            and payload.get("future_kernel_native_consumer_abi_name")
            == "premap_future_kernel_native_consumer_abi_v1"
            and payload.get("future_kernel_native_consumer_mode")
            == "readonly_future_kernel_native_consumer_abi"
            and payload.get("future_kernel_native_consumer_source")
            == "premap_typed_handle_table_soa_fields"
            and payload.get("future_kernel_native_consumer_error_count") == 0
            and payload.get("future_kernel_native_consumer_payload_bytes") == 0
            and payload.get("future_kernel_native_consumer_passed_to_kernel") is False
            and payload.get("future_kernel_native_consumer_changes_kernel_launch_args")
            is False
            and payload.get("future_kernel_native_consumer_current_wna16_arg_compatible")
            is False
            and payload.get(
                "future_kernel_native_consumer_requires_wna16_arg_reinterpretation"
            )
            is False
            and _future_field_mask_ok(
                payload,
                prefix="future_kernel_native_consumer",
                expected_field=expected_field,
            )
            and payload.get("future_kernel_native_consumer_single_field_mirror_checked")
            is True
            and payload.get("future_kernel_native_consumer_single_field_mirror_field_name")
            == expected_field
            and payload.get("future_kernel_native_consumer_single_field_mirror_error_count")
            == 0
        )

    def _future_native_launch_consumer_field_passed(
        payload: dict[str, Any],
        *,
        expected_field: str,
    ) -> bool:
        return bool(
            payload.get("passed") is True
            and payload.get("input_json") is not None
            and _resolve_repo_path(str(payload.get("input_json"))) == input_path
            and payload.get("future_kernel_native_consumer_checked") is True
            and payload.get("future_kernel_native_consumer_error_count") == 0
            and payload.get("future_kernel_native_launch_consumer_checked") is True
            and payload.get("future_kernel_native_launch_consumer_abi_name")
            == "premap_future_kernel_native_consumer_launch_abi_v1"
            and payload.get("future_kernel_native_launch_consumer_mode")
            == "readonly_future_kernel_native_consumer_launch_abi"
            and payload.get("future_kernel_native_launch_consumer_source")
            == "premap_future_kernel_native_consumer_abi_v1"
            and payload.get("future_kernel_native_launch_consumer_error_count") == 0
            and payload.get("future_kernel_native_launch_consumer_payload_bytes") == 0
            and payload.get("future_kernel_native_launch_consumer_passed_to_kernel")
            is False
            and payload.get(
                "future_kernel_native_launch_consumer_changes_kernel_launch_args"
            )
            is False
            and payload.get(
                "future_kernel_native_launch_consumer_current_wna16_arg_compatible"
            )
            is False
            and payload.get(
                "future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation"
            )
            is False
            and _future_field_mask_ok(
                payload,
                prefix="future_kernel_native_launch_consumer",
                expected_field=expected_field,
            )
            and payload.get(
                "future_kernel_native_launch_consumer_single_field_mirror_checked"
            )
            is True
            and payload.get(
                "future_kernel_native_launch_consumer_single_field_mirror_field_name"
            )
            == expected_field
            and payload.get(
                "future_kernel_native_launch_consumer_single_field_mirror_error_count"
            )
            == 0
        )

    def _future_native_dispatch_consumer_field_passed(
        payload: dict[str, Any],
        *,
        expected_field: str,
    ) -> bool:
        grid_x = payload.get("future_kernel_native_dispatch_consumer_grid_x")
        block_x = payload.get("future_kernel_native_dispatch_consumer_block_x")
        row_offset = payload.get("future_kernel_native_dispatch_consumer_row_offset")
        row_limit = payload.get("future_kernel_native_dispatch_consumer_row_limit")
        row_count = payload.get("row_count")
        rows_per_program = payload.get(
            "future_kernel_native_dispatch_consumer_rows_per_program"
        )
        active_rows = payload.get(
            "future_kernel_native_dispatch_consumer_active_rows"
        )
        launch_threads = payload.get(
            "future_kernel_native_dispatch_consumer_launch_threads"
        )
        dispatch_row_count = payload.get(
            "future_kernel_native_dispatch_consumer_row_count"
        )
        dispatch_row_ok_count = payload.get(
            "future_kernel_native_dispatch_consumer_row_ok_count"
        )
        mirror_row_count = payload.get(
            "future_kernel_native_dispatch_consumer_single_field_mirror_row_count"
        )
        mirror_row_ok_count = payload.get(
            "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count"
        )
        ptr_dispatch_row_count = payload.get(
            "future_kernel_native_dispatch_ptr_consumer_row_count"
        )
        ptr_dispatch_row_ok_count = payload.get(
            "future_kernel_native_dispatch_ptr_consumer_row_ok_count"
        )
        ptr_mirror_row_count = payload.get(
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count"
        )
        ptr_mirror_row_ok_count = payload.get(
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count"
        )
        arg_slot_row_count = payload.get(
            "future_kernel_native_arg_slot_consumer_row_count"
        )
        arg_slot_row_ok_count = payload.get(
            "future_kernel_native_arg_slot_consumer_row_ok_count"
        )
        arg_slot_mirror_row_count = payload.get(
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count"
        )
        arg_slot_mirror_row_ok_count = payload.get(
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count"
        )
        consumer_view_row_count = payload.get(
            "future_kernel_native_consumer_view_row_count"
        )
        consumer_view_row_ok_count = payload.get(
            "future_kernel_native_consumer_view_row_ok_count"
        )
        dispatch_ints = (
            grid_x,
            block_x,
            row_offset,
            row_limit,
            row_count,
            rows_per_program,
            active_rows,
            launch_threads,
            dispatch_row_count,
            dispatch_row_ok_count,
            mirror_row_count,
            mirror_row_ok_count,
            ptr_dispatch_row_count,
            ptr_dispatch_row_ok_count,
            ptr_mirror_row_count,
            ptr_mirror_row_ok_count,
            arg_slot_row_count,
            arg_slot_row_ok_count,
            arg_slot_mirror_row_count,
            arg_slot_mirror_row_ok_count,
            consumer_view_row_count,
            consumer_view_row_ok_count,
        )
        dispatch_ints_valid = all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in dispatch_ints
        )
        if dispatch_ints_valid:
            launched_threads = grid_x * block_x
            previous_grid_threads = (grid_x - 1) * block_x
            active_rows_expected = row_limit - row_offset
            dispatch_geometry_ok = (
                grid_x > 0
                and block_x > 0
                and row_offset >= 0
                and row_limit <= row_count
                and row_limit > row_offset
                and rows_per_program == block_x
                and active_rows == active_rows_expected
                and active_rows > 0
                and launch_threads == launched_threads
                and launched_threads >= active_rows
                and previous_grid_threads < active_rows
                and dispatch_row_count == active_rows
                and dispatch_row_ok_count == active_rows
                and mirror_row_count == active_rows
                and mirror_row_ok_count == active_rows
                and ptr_dispatch_row_count == active_rows
                and ptr_dispatch_row_ok_count == active_rows
                and ptr_mirror_row_count == active_rows
                and ptr_mirror_row_ok_count == active_rows
                and arg_slot_row_count == active_rows
                and arg_slot_row_ok_count == active_rows
                and arg_slot_mirror_row_count == active_rows
                and arg_slot_mirror_row_ok_count == active_rows
                and consumer_view_row_count == active_rows
                and consumer_view_row_ok_count == active_rows
            )
        else:
            dispatch_geometry_ok = False
        def _hash_chain_prefixes() -> tuple[str, ...]:
            return (
                "future_kernel_native_dispatch_consumer",
                "future_kernel_native_dispatch_ptr_consumer",
                "future_kernel_native_arg_slot_consumer",
            )

        def _hash_chain_equal(suffix: str) -> bool:
            values = tuple(
                _parse_hex64(payload.get(f"{prefix}_{suffix}"))
                for prefix in _hash_chain_prefixes()
            )
            return all(value is not None for value in values) and len(set(values)) == 1
        def _hash_chain_valid(suffix: str) -> bool:
            return all(
                _parse_hex64(payload.get(f"{prefix}_{suffix}")) is not None
                for prefix in _hash_chain_prefixes()
            )

        return bool(
            payload.get("passed") is True
            and payload.get("input_json") is not None
            and _resolve_repo_path(str(payload.get("input_json"))) == input_path
            and payload.get("future_kernel_native_consumer_checked") is True
            and payload.get("future_kernel_native_consumer_error_count") == 0
            and payload.get("future_kernel_native_launch_consumer_checked") is True
            and payload.get("future_kernel_native_launch_consumer_error_count") == 0
            and payload.get("future_kernel_native_dispatch_consumer_checked") is True
            and payload.get("future_kernel_native_dispatch_consumer_abi_name")
            == "premap_future_kernel_native_consumer_dispatch_abi_v1"
            and payload.get("future_kernel_native_dispatch_consumer_mode")
            == "readonly_future_kernel_native_consumer_dispatch_abi"
            and payload.get("future_kernel_native_dispatch_consumer_source")
            == "premap_future_kernel_native_consumer_launch_abi_v1"
            and payload.get("future_kernel_native_dispatch_consumer_error_count") == 0
            and payload.get("future_kernel_native_dispatch_consumer_payload_bytes") == 0
            and payload.get("future_kernel_native_dispatch_consumer_passed_to_kernel")
            is False
            and payload.get(
                "future_kernel_native_dispatch_consumer_changes_kernel_launch_args"
            )
            is False
            and payload.get(
                "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible"
            )
            is False
            and payload.get(
                "future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation"
            )
            is False
            and _future_field_mask_ok(
                payload,
                prefix="future_kernel_native_dispatch_consumer",
                expected_field=expected_field,
            )
            and payload.get(
                "future_kernel_native_dispatch_consumer_single_field_mirror_checked"
            )
            is True
            and payload.get(
                "future_kernel_native_dispatch_consumer_single_field_mirror_field_name"
            )
            == expected_field
            and payload.get(
                "future_kernel_native_dispatch_consumer_single_field_mirror_error_count"
            )
            == 0
            and payload.get(
                "future_kernel_native_dispatch_consumer_launch_geometry_checked"
            )
            is True
            and payload.get(
                "future_kernel_native_dispatch_consumer_launch_covers_active_rows"
            )
            is True
            and payload.get(
                "future_kernel_native_dispatch_consumer_launch_minimal_cover"
            )
            is True
            and payload.get("future_kernel_native_dispatch_ptr_consumer_checked")
            is True
            and payload.get("future_kernel_native_dispatch_ptr_consumer_abi_name")
            == "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
            and payload.get("future_kernel_native_dispatch_ptr_consumer_mode")
            == "readonly_future_kernel_native_consumer_dispatch_ptr_abi"
            and payload.get("future_kernel_native_dispatch_ptr_consumer_source")
            == "premap_future_kernel_native_consumer_dispatch_abi_v1"
            and payload.get("future_kernel_native_dispatch_ptr_consumer_error_count") == 0
            and payload.get("future_kernel_native_dispatch_ptr_consumer_payload_bytes") == 0
            and payload.get("future_kernel_native_dispatch_ptr_consumer_passed_to_kernel")
            is False
            and payload.get(
                "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args"
            )
            is False
            and payload.get(
                "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible"
            )
            is False
            and payload.get(
                "future_kernel_native_dispatch_ptr_consumer_requires_wna16_arg_reinterpretation"
            )
            is False
            and _future_field_mask_ok(
                payload,
                prefix="future_kernel_native_dispatch_ptr_consumer",
                expected_field=expected_field,
            )
            and payload.get(
                "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_checked"
            )
            is True
            and payload.get(
                "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_field_name"
            )
            == expected_field
            and payload.get(
                "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_error_count"
            )
            == 0
            and payload.get("future_kernel_native_arg_slot_consumer_checked")
            is True
            and payload.get("future_kernel_native_arg_slot_consumer_abi_name")
            == "premap_future_kernel_native_consumer_arg_slot_abi_v1"
            and payload.get("future_kernel_native_arg_slot_consumer_mode")
            == "readonly_future_kernel_native_consumer_arg_slot_abi"
            and payload.get("future_kernel_native_arg_slot_consumer_source")
            == "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
            and payload.get("future_kernel_native_arg_slot_consumer_error_count") == 0
            and payload.get("future_kernel_native_arg_slot_consumer_payload_bytes") == 0
            and payload.get("future_kernel_native_arg_slot_consumer_passed_to_kernel")
            is False
            and payload.get(
                "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args"
            )
            is False
            and payload.get(
                "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible"
            )
            is False
            and payload.get(
                "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation"
            )
            is False
            and _future_field_mask_ok(
                payload,
                prefix="future_kernel_native_arg_slot_consumer",
                expected_field=expected_field,
            )
            and payload.get(
                "future_kernel_native_arg_slot_consumer_single_field_mirror_checked"
            )
            is True
            and payload.get(
                "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
            )
            == expected_field
            and payload.get(
                "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count"
            )
            == 0
            and _future_handle_field_reads_ok(
                payload,
                prefix="future_kernel_native_arg_slot_consumer",
                expected_rows=active_rows,
            )
            and payload.get("future_kernel_native_consumer_view_checked") is True
            and payload.get("future_kernel_native_consumer_view_abi_name")
            == "premap_future_kernel_native_consumer_view_abi_v1"
            and payload.get("future_kernel_native_consumer_view_mode")
            == "readonly_future_kernel_native_consumer_view_abi"
            and payload.get("future_kernel_native_consumer_view_source")
            == "premap_future_kernel_native_consumer_arg_slot_abi_v1"
            and payload.get("future_kernel_native_consumer_view_source_packet_chain_depth")
            == 3
            and payload.get("future_kernel_native_consumer_view_error_count") == 0
            and payload.get("future_kernel_native_consumer_view_payload_bytes") == 0
            and payload.get("future_kernel_native_consumer_view_passed_to_kernel")
            is False
            and payload.get(
                "future_kernel_native_consumer_view_changes_kernel_launch_args"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_view_current_wna16_arg_compatible"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation"
            )
            is False
            and _future_field_mask_ok(
                payload,
                prefix="future_kernel_native_consumer_view",
                expected_field=expected_field,
            )
            and _future_handle_field_reads_ok(
                payload,
                prefix="future_kernel_native_consumer_view",
                expected_rows=active_rows,
            )
            and dispatch_geometry_ok
            and _hash_chain_valid("hash_accumulator")
            and _future_native_handle_projection_hashchain_equal(payload)
            and _hash_chain_equal("single_field_mirror_hash_accumulator")
        )

    future_native_consumer_required = not bool(
        args.skip_stub or args.skip_future_kernel_native_consumer_stub
    )
    future_native_consumer_passed = bool(
        args.dry_run
        or not future_native_consumer_required
        or _future_native_consumer_field_passed(
            future_kernel_native_consumer_stub_payload,
            expected_field="scale_metadata_handle",
        )
    )
    future_native_consumer_extra_required = not bool(
        args.skip_stub
        or args.skip_future_kernel_native_consumer_stub
        or args.skip_future_kernel_native_consumer_extra_field_stubs
    )
    future_native_consumer_extra_passed = bool(
        args.dry_run
        or not future_native_consumer_extra_required
        or (
            _future_native_consumer_field_passed(
                future_kernel_native_consumer_descriptor_ptr_stub_payload,
                expected_field="descriptor_ptr",
            )
            and _future_native_consumer_field_passed(
                future_kernel_native_consumer_packed_weight_stub_payload,
                expected_field="packed_weight_descriptor",
            )
            and _future_native_consumer_field_passed(
                future_kernel_native_consumer_aux_metadata_stub_payload,
                expected_field="aux_metadata_handle",
            )
        )
    )
    future_native_launch_consumer_required = not bool(
        args.skip_stub or args.skip_future_kernel_native_consumer_stub
    )
    future_native_launch_consumer_passed = bool(
        args.dry_run
        or not future_native_launch_consumer_required
        or _future_native_launch_consumer_field_passed(
            future_kernel_native_consumer_launch_stub_payload,
            expected_field="scale_metadata_handle",
        )
    )
    future_native_launch_consumer_extra_required = not bool(
        args.skip_stub
        or args.skip_future_kernel_native_consumer_stub
        or args.skip_future_kernel_native_consumer_extra_field_stubs
    )
    future_native_launch_consumer_extra_passed = bool(
        args.dry_run
        or not future_native_launch_consumer_extra_required
        or (
            _future_native_launch_consumer_field_passed(
                future_kernel_native_consumer_launch_descriptor_ptr_stub_payload,
                expected_field="descriptor_ptr",
            )
            and _future_native_launch_consumer_field_passed(
                future_kernel_native_consumer_launch_packed_weight_stub_payload,
                expected_field="packed_weight_descriptor",
            )
            and _future_native_launch_consumer_field_passed(
                future_kernel_native_consumer_launch_aux_metadata_stub_payload,
                expected_field="aux_metadata_handle",
            )
        )
    )
    future_native_dispatch_consumer_required = not bool(
        args.skip_stub or args.skip_future_kernel_native_consumer_stub
    )
    future_native_dispatch_consumer_passed = bool(
        args.dry_run
        or not future_native_dispatch_consumer_required
        or _future_native_dispatch_consumer_field_passed(
            future_kernel_native_consumer_dispatch_stub_payload,
            expected_field="scale_metadata_handle",
        )
    )
    future_native_dispatch_consumer_extra_required = not bool(
        args.skip_stub
        or args.skip_future_kernel_native_consumer_stub
        or args.skip_future_kernel_native_consumer_extra_field_stubs
    )
    future_native_dispatch_consumer_extra_passed = bool(
        args.dry_run
        or not future_native_dispatch_consumer_extra_required
        or (
            _future_native_dispatch_consumer_field_passed(
                future_kernel_native_consumer_dispatch_descriptor_ptr_stub_payload,
                expected_field="descriptor_ptr",
            )
            and _future_native_dispatch_consumer_field_passed(
                future_kernel_native_consumer_dispatch_packed_weight_stub_payload,
                expected_field="packed_weight_descriptor",
            )
            and _future_native_dispatch_consumer_field_passed(
                future_kernel_native_consumer_dispatch_aux_metadata_stub_payload,
                expected_field="aux_metadata_handle",
            )
        )
    )
    future_native_request_ptr_required = not bool(
        args.skip_stub or args.skip_future_kernel_native_consumer_request_ptr_stub
    )

    def _future_native_request_ptr_passed(payload: dict[str, Any]) -> bool:
        row_count = payload.get("row_count")
        if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count <= 0:
            return False
        hash_suffixes = (
            "row_hash_accumulator",
            "field_read_hash_accumulator",
            "row_metadata_hash_accumulator",
        )
        read_count_expectations = {
            "descriptor_ptr_read_row_ok_count": row_count,
            "packed_weight_descriptor_read_row_ok_count": row_count,
            "scale_metadata_handle_read_row_ok_count": row_count,
            "aux_metadata_handle_read_row_ok_count": row_count,
            "expert_id_read_row_ok_count": row_count,
            "address_key_hash_read_row_ok_count": row_count,
            "row_metadata_read_row_ok_count": row_count,
        }
        for summary_prefix in (
            "future_kernel_native_consumer_request_ptr_summary",
            "future_kernel_native_consumer_kernel_entry_summary",
        ):
            if payload.get(f"{summary_prefix}_row_count") != row_count:
                return False
            if payload.get(f"{summary_prefix}_row_ok_count") != row_count:
                return False
            if payload.get(f"{summary_prefix}_error_count") != 0:
                return False
            if payload.get(f"{summary_prefix}_field_mask") != _FUTURE_KERNEL_ALL_FIELD_MASK:
                return False
            for suffix, expected_value in read_count_expectations.items():
                if payload.get(f"{summary_prefix}_{suffix}") != expected_value:
                    return False
            for suffix in hash_suffixes:
                if _parse_hex64(payload.get(f"{summary_prefix}_{suffix}")) is None:
                    return False
        for suffix in hash_suffixes:
            request_hash = _parse_hex64(
                payload.get(
                    f"future_kernel_native_consumer_request_ptr_summary_{suffix}"
                )
            )
            kernel_entry_hash = _parse_hex64(
                payload.get(
                    f"future_kernel_native_consumer_kernel_entry_summary_{suffix}"
                )
            )
            if (
                request_hash is None
                or kernel_entry_hash is None
                or request_hash != kernel_entry_hash
            ):
                return False
        return bool(
            payload.get("passed") is True
            and payload.get("input_json") is not None
            and _resolve_repo_path(str(payload.get("input_json"))) == input_path
            and payload.get("future_kernel_native_consumer_request_ptr_checked") is True
            and payload.get("future_kernel_native_consumer_request_ptr_abi_name")
            == "premap_future_kernel_native_consumer_request_ptr_abi_v1"
            and payload.get("future_kernel_native_consumer_request_ptr_mode")
            == "readonly_future_kernel_native_consumer_request_ptr_abi"
            and payload.get("future_kernel_native_consumer_request_ptr_source")
            == "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1"
            and payload.get("future_kernel_native_consumer_request_ptr_field_read_path")
            == "request_ptr_to_kernel_arg_packet_to_program_view_rows"
            and payload.get("future_kernel_native_consumer_request_ptr_packet_chain_depth")
            == 4
            and payload.get("future_kernel_native_consumer_request_ptr_pointer_size")
            == 8
            and payload.get("future_kernel_native_consumer_request_ptr_payload_bytes")
            == 0
            and payload.get("future_kernel_native_consumer_request_ptr_payload_deref_allowed")
            is False
            and payload.get("future_kernel_native_consumer_request_ptr_passed_to_kernel")
            is False
            and payload.get("future_kernel_native_consumer_request_ptr_kernel_arg_pass_allowed")
            is False
            and payload.get(
                "future_kernel_native_consumer_request_ptr_changes_kernel_launch_args"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_ptr_current_wna16_arg_compatible"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_ptr_requires_wna16_arg_reinterpretation"
            )
            is False
            and _request_level_single_field_handoff_passed(
                payload,
                consumer_prefix="future_kernel_native_consumer_request_ptr",
                expected_rows=row_count,
            )
        )

    future_native_request_ptr_passed = bool(
        args.dry_run
        or not future_native_request_ptr_required
        or _future_native_request_ptr_passed(
            future_kernel_native_consumer_request_ptr_stub_payload
        )
    )
    future_native_request_launch_required = not bool(
        args.skip_stub or args.skip_future_kernel_native_consumer_request_launch_stub
    )

    def _future_native_request_launch_passed(payload: dict[str, Any]) -> bool:
        row_count = payload.get("row_count")
        if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count <= 0:
            return False
        device_ordinal = payload.get(
            "future_kernel_native_consumer_request_launch_device_ordinal"
        )
        if device_ordinal != int(args.stub_device):
            return False
        block_x = payload.get("future_kernel_native_consumer_request_launch_block_x")
        grid_x = payload.get("future_kernel_native_consumer_request_launch_grid_x")
        rows_per_program = payload.get(
            "future_kernel_native_consumer_request_launch_rows_per_program"
        )
        if (
            not isinstance(block_x, int)
            or isinstance(block_x, bool)
            or block_x <= 0
            or not isinstance(grid_x, int)
            or isinstance(grid_x, bool)
            or grid_x <= 0
        ):
            return False
        if rows_per_program != block_x:
            return False
        if grid_x != (row_count + block_x - 1) // block_x:
            return False
        hash_suffixes = (
            "row_hash_accumulator",
            "field_read_hash_accumulator",
            "row_metadata_hash_accumulator",
        )
        read_count_expectations = {
            "descriptor_ptr_read_row_ok_count": row_count,
            "packed_weight_descriptor_read_row_ok_count": row_count,
            "scale_metadata_handle_read_row_ok_count": row_count,
            "aux_metadata_handle_read_row_ok_count": row_count,
            "expert_id_read_row_ok_count": row_count,
            "address_key_hash_read_row_ok_count": row_count,
            "row_metadata_read_row_ok_count": row_count,
        }
        for summary_prefix in (
            "future_kernel_native_consumer_request_launch_summary",
            "future_kernel_native_consumer_request_ptr_summary",
            "future_kernel_native_consumer_kernel_entry_summary",
        ):
            if payload.get(f"{summary_prefix}_row_count") != row_count:
                return False
            if payload.get(f"{summary_prefix}_row_ok_count") != row_count:
                return False
            if payload.get(f"{summary_prefix}_error_count") != 0:
                return False
            if payload.get(f"{summary_prefix}_field_mask") != _FUTURE_KERNEL_ALL_FIELD_MASK:
                return False
            for suffix, expected_value in read_count_expectations.items():
                if payload.get(f"{summary_prefix}_{suffix}") != expected_value:
                    return False
            for suffix in hash_suffixes:
                if _parse_hex64(payload.get(f"{summary_prefix}_{suffix}")) is None:
                    return False
        for suffix in hash_suffixes:
            values = [
                _parse_hex64(
                    payload.get(f"{prefix}_{suffix}")
                )
                for prefix in (
                    "future_kernel_native_consumer_request_launch_summary",
                    "future_kernel_native_consumer_request_ptr_summary",
                    "future_kernel_native_consumer_kernel_entry_summary",
                )
            ]
            if any(value is None for value in values) or len(set(values)) != 1:
                return False
        return bool(
            payload.get("passed") is True
            and payload.get("input_json") is not None
            and _resolve_repo_path(str(payload.get("input_json"))) == input_path
            and payload.get("future_kernel_native_consumer_request_launch_checked")
            is True
            and payload.get("future_kernel_native_consumer_request_launch_abi_name")
            == "premap_future_kernel_native_consumer_request_launch_abi_v1"
            and payload.get("future_kernel_native_consumer_request_launch_mode")
            == "readonly_future_kernel_native_consumer_request_launch_abi"
            and payload.get("future_kernel_native_consumer_request_launch_source")
            == "premap_future_kernel_native_consumer_request_ptr_abi_v1"
            and payload.get("future_kernel_native_consumer_request_launch_field_read_path")
            == "request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
            and payload.get(
                "future_kernel_native_consumer_request_launch_packet_chain_depth"
            )
            == 5
            and payload.get("future_kernel_native_consumer_request_launch_pointer_size")
            == 8
            and payload.get("future_kernel_native_consumer_request_launch_stream_domain")
            == 0
            and payload.get("future_kernel_native_consumer_request_launch_row_offset")
            == 0
            and payload.get("future_kernel_native_consumer_request_launch_row_limit")
            == row_count
            and payload.get("future_kernel_native_consumer_request_launch_row_count")
            == row_count
            and payload.get("future_kernel_native_consumer_request_launch_payload_bytes")
            == 0
            and payload.get(
                "future_kernel_native_consumer_request_launch_payload_deref_allowed"
            )
            is False
            and payload.get("future_kernel_native_consumer_request_launch_passed_to_kernel")
            is False
            and payload.get(
                "future_kernel_native_consumer_request_launch_kernel_arg_pass_allowed"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_launch_changes_kernel_launch_args"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_launch_current_wna16_arg_compatible"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_launch_requires_wna16_arg_reinterpretation"
            )
            is False
            and _request_level_single_field_handoff_passed(
                payload,
                consumer_prefix="future_kernel_native_consumer_request_launch",
                expected_rows=row_count,
            )
        )

    future_native_request_launch_passed = bool(
        args.dry_run
        or not future_native_request_launch_required
        or _future_native_request_launch_passed(
            future_kernel_native_consumer_request_launch_stub_payload
        )
    )
    future_native_request_launch_ptr_required = not bool(
        args.skip_stub
        or args.skip_future_kernel_native_consumer_request_launch_ptr_stub
    )

    def _future_native_request_launch_ptr_passed(payload: dict[str, Any]) -> bool:
        row_count = payload.get("row_count")
        if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count <= 0:
            return False
        hash_suffixes = (
            "row_hash_accumulator",
            "field_read_hash_accumulator",
            "row_metadata_hash_accumulator",
        )
        read_count_expectations = {
            "descriptor_ptr_read_row_ok_count": row_count,
            "packed_weight_descriptor_read_row_ok_count": row_count,
            "scale_metadata_handle_read_row_ok_count": row_count,
            "aux_metadata_handle_read_row_ok_count": row_count,
            "expert_id_read_row_ok_count": row_count,
            "address_key_hash_read_row_ok_count": row_count,
            "row_metadata_read_row_ok_count": row_count,
        }
        for summary_prefix in (
            "future_kernel_native_consumer_request_launch_ptr_summary",
            "future_kernel_native_consumer_request_launch_summary",
            "future_kernel_native_consumer_request_ptr_summary",
            "future_kernel_native_consumer_kernel_entry_summary",
        ):
            if payload.get(f"{summary_prefix}_row_count") != row_count:
                return False
            if payload.get(f"{summary_prefix}_row_ok_count") != row_count:
                return False
            if payload.get(f"{summary_prefix}_error_count") != 0:
                return False
            if payload.get(f"{summary_prefix}_field_mask") != _FUTURE_KERNEL_ALL_FIELD_MASK:
                return False
            for suffix, expected_value in read_count_expectations.items():
                if payload.get(f"{summary_prefix}_{suffix}") != expected_value:
                    return False
            for suffix in hash_suffixes:
                if _parse_hex64(payload.get(f"{summary_prefix}_{suffix}")) is None:
                    return False
        for suffix in hash_suffixes:
            values = [
                _parse_hex64(payload.get(f"{prefix}_{suffix}"))
                for prefix in (
                    "future_kernel_native_consumer_request_launch_ptr_summary",
                    "future_kernel_native_consumer_request_launch_summary",
                    "future_kernel_native_consumer_request_ptr_summary",
                    "future_kernel_native_consumer_kernel_entry_summary",
                )
            ]
            if any(value is None for value in values) or len(set(values)) != 1:
                return False
        return bool(
            payload.get("passed") is True
            and payload.get("input_json") is not None
            and _resolve_repo_path(str(payload.get("input_json"))) == input_path
            and payload.get("future_kernel_native_consumer_request_launch_ptr_checked")
            is True
            and payload.get("future_kernel_native_consumer_request_launch_ptr_abi_name")
            == "premap_future_kernel_native_consumer_request_launch_ptr_abi_v1"
            and payload.get("future_kernel_native_consumer_request_launch_ptr_mode")
            == "readonly_future_kernel_native_consumer_request_launch_ptr_abi"
            and payload.get("future_kernel_native_consumer_request_launch_ptr_source")
            == "premap_future_kernel_native_consumer_request_launch_abi_v1"
            and payload.get(
                "future_kernel_native_consumer_request_launch_ptr_field_read_path"
            )
            == "request_launch_ptr_to_request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
            and payload.get(
                "future_kernel_native_consumer_request_launch_ptr_packet_chain_depth"
            )
            == 6
            and payload.get("future_kernel_native_consumer_request_launch_ptr_pointer_size")
            == 8
            and payload.get("future_kernel_native_consumer_request_launch_ptr_payload_bytes")
            == 0
            and payload.get(
                "future_kernel_native_consumer_request_launch_ptr_payload_deref_allowed"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_launch_ptr_passed_to_kernel"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_launch_ptr_kernel_arg_pass_allowed"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_launch_ptr_changes_kernel_launch_args"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_launch_ptr_current_wna16_arg_compatible"
            )
            is False
            and payload.get(
                "future_kernel_native_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation"
            )
            is False
            and _request_level_single_field_handoff_passed(
                payload,
                consumer_prefix="future_kernel_native_consumer_request_launch_ptr",
                expected_rows=row_count,
            )
        )

    future_native_request_launch_ptr_passed = bool(
        args.dry_run
        or not future_native_request_launch_ptr_required
        or _future_native_request_launch_ptr_passed(
            future_kernel_native_consumer_request_launch_ptr_stub_payload
        )
    )
    extra_input_checks_passed = bool(
        args.dry_run
        or all(item.get("passed") is True for item in extra_input_check_summaries)
    )
    passed = bool(
        (
            args.dry_run
            or (
                stub_payload.get("passed") is True
                and stub_payload.get("input_json") is not None
                and _resolve_repo_path(str(stub_payload.get("input_json")))
                == input_path
                and per_field_passed
                and envelope_mirror_passed
                and packed_weight_mirror_passed
                and aux_metadata_mirror_passed
                and descriptor_ptr_mirror_passed
                and kernel_side_compatible_passed
                and future_kernel_args_passed
                and future_kernel_args_extra_passed
                and future_kernel_args_compatible_path_passed
                and future_native_consumer_passed
                and future_native_consumer_extra_passed
                and future_native_launch_consumer_passed
                and future_native_launch_consumer_extra_passed
                and future_native_dispatch_consumer_passed
                and future_native_dispatch_consumer_extra_passed
                and future_native_request_ptr_passed
                and future_native_request_launch_passed
                and future_native_request_launch_ptr_passed
                and extra_input_checks_passed
                and preflight_payload.get("passed") is True
                and preflight_status_payload.get("passed") is True
            )
        )
        and pointer_source_observer_gate_passed
    )
    failures: list[str] = []
    if not passed:
        if not pointer_source_observer_gate_passed:
            failures.append("pointer_source_observer_check_not_passed")
        suppress_native_dry_run_failures = bool(
            args.dry_run and not pointer_source_observer_gate_passed
        )
        if not suppress_native_dry_run_failures:
            if stub_payload.get("passed") is not True:
                failures.append("native_stub_not_passed")
            if stub_payload.get("input_json") is None:
                failures.append("native_stub_input_json_missing")
            elif (
                not args.dry_run
                and _resolve_repo_path(str(stub_payload.get("input_json")))
                != input_path
            ):
                failures.append("native_stub_input_json_mismatch")
            if preflight_payload.get("passed") is not True:
                failures.append("preflight_not_passed")
            if preflight_status_payload.get("passed") is not True:
                failures.append("preflight_status_not_passed")
    if not per_field_passed:
        if per_field_stub_payload.get("passed") is not True:
            failures.append("native_stub_per_field_not_passed")
        if per_field_stub_payload.get("input_json") is None:
            failures.append("native_stub_per_field_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(str(per_field_stub_payload.get("input_json")))
            != input_path
        ):
            failures.append("native_stub_per_field_input_json_mismatch")
    if not envelope_mirror_passed:
        if envelope_mirror_stub_payload.get("passed") is not True:
            failures.append("native_stub_kernel_envelope_mirror_not_passed")
        if envelope_mirror_stub_payload.get("input_json") is None:
            failures.append("native_stub_kernel_envelope_mirror_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(str(envelope_mirror_stub_payload.get("input_json")))
            != input_path
        ):
            failures.append("native_stub_kernel_envelope_mirror_input_json_mismatch")
        if (
            envelope_mirror_stub_payload.get("kernel_consumer_envelope_checked")
            is not True
        ):
            failures.append("native_stub_kernel_envelope_not_checked")
        if envelope_mirror_stub_payload.get("single_field_mirror_checked") is not True:
            failures.append("native_stub_kernel_envelope_mirror_field_not_checked")
    if not packed_weight_mirror_passed:
        if packed_weight_mirror_stub_payload.get("passed") is not True:
            failures.append("native_stub_packed_weight_mirror_not_passed")
        if packed_weight_mirror_stub_payload.get("input_json") is None:
            failures.append("native_stub_packed_weight_mirror_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(packed_weight_mirror_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append("native_stub_packed_weight_mirror_input_json_mismatch")
        if packed_weight_mirror_stub_payload.get("single_field_mirror_checked") is not True:
            failures.append("native_stub_packed_weight_mirror_field_not_checked")
        if (
            packed_weight_mirror_stub_payload.get("single_field_mirror_field_name")
            != "packed_weight_descriptor"
        ):
            failures.append("native_stub_packed_weight_mirror_field_name_mismatch")
    if not aux_metadata_mirror_passed:
        if aux_metadata_mirror_stub_payload.get("passed") is not True:
            failures.append("native_stub_aux_metadata_mirror_not_passed")
        if aux_metadata_mirror_stub_payload.get("input_json") is None:
            failures.append("native_stub_aux_metadata_mirror_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(str(aux_metadata_mirror_stub_payload.get("input_json")))
            != input_path
        ):
            failures.append("native_stub_aux_metadata_mirror_input_json_mismatch")
        if aux_metadata_mirror_stub_payload.get("single_field_mirror_checked") is not True:
            failures.append("native_stub_aux_metadata_mirror_field_not_checked")
        if (
            aux_metadata_mirror_stub_payload.get("single_field_mirror_field_name")
            != "aux_metadata_handle"
        ):
            failures.append("native_stub_aux_metadata_mirror_field_name_mismatch")
    if not descriptor_ptr_mirror_passed:
        if descriptor_ptr_mirror_stub_payload.get("passed") is not True:
            failures.append("native_stub_descriptor_ptr_mirror_not_passed")
        if descriptor_ptr_mirror_stub_payload.get("input_json") is None:
            failures.append("native_stub_descriptor_ptr_mirror_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(descriptor_ptr_mirror_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append("native_stub_descriptor_ptr_mirror_input_json_mismatch")
        if descriptor_ptr_mirror_stub_payload.get("single_field_mirror_checked") is not True:
            failures.append("native_stub_descriptor_ptr_mirror_field_not_checked")
        if (
            descriptor_ptr_mirror_stub_payload.get("single_field_mirror_field_name")
            != "descriptor_ptr"
        ):
            failures.append("native_stub_descriptor_ptr_mirror_field_name_mismatch")
    if not kernel_side_compatible_passed:
        if kernel_side_compatible_stub_payload.get("passed") is not True:
            failures.append("native_stub_kernel_side_compatible_not_passed")
        if kernel_side_compatible_stub_payload.get("input_json") is None:
            failures.append("native_stub_kernel_side_compatible_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(kernel_side_compatible_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append("native_stub_kernel_side_compatible_input_json_mismatch")
        if (
            kernel_side_compatible_stub_payload.get(
                "kernel_side_compatible_consumer_checked"
            )
            is not True
        ):
            failures.append("native_stub_kernel_side_compatible_not_checked")
        if (
            kernel_side_compatible_stub_payload.get(
                "kernel_side_compatible_consumer_error_count"
            )
            != 0
        ):
            failures.append("native_stub_kernel_side_compatible_error_count_mismatch")
        if (
            kernel_side_compatible_stub_payload.get(
                "kernel_side_compatible_consumer_passed_to_kernel"
            )
            is not False
        ):
            failures.append("native_stub_kernel_side_compatible_passed_to_kernel")
        if (
            kernel_side_compatible_stub_payload.get(
                "kernel_side_compatible_consumer_current_wna16_arg_compatible"
            )
            is not False
        ):
            failures.append("native_stub_kernel_side_compatible_wna16_arg_compatible")
    if not future_kernel_args_passed:
        if future_kernel_args_stub_payload.get("passed") is not True:
            failures.append("native_stub_future_kernel_args_not_passed")
        if future_kernel_args_stub_payload.get("input_json") is None:
            failures.append("native_stub_future_kernel_args_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(future_kernel_args_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append("native_stub_future_kernel_args_input_json_mismatch")
        if (
            future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_checked"
            )
            is not True
        ):
            failures.append("native_stub_future_kernel_args_not_checked")
        if (
            future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_error_count"
            )
            != 0
        ):
            failures.append("native_stub_future_kernel_args_error_count_mismatch")
        if (
            future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_passed_to_kernel"
            )
            is not False
        ):
            failures.append("native_stub_future_kernel_args_passed_to_kernel")
        if (
            future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_current_wna16_arg_compatible"
            )
            is not False
        ):
            failures.append("native_stub_future_kernel_args_wna16_arg_compatible")
        if (
            future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_single_field_mirror_checked"
            )
            is not True
        ):
            failures.append("native_stub_future_kernel_args_mirror_not_checked")
        if (
            future_kernel_args_stub_payload.get(
                "future_kernel_consumer_args_single_field_mirror_field_name"
            )
            != "scale_metadata_handle"
        ):
            failures.append(
                "native_stub_future_kernel_args_mirror_field_name_mismatch"
            )
    if not future_kernel_args_extra_passed:
        for label, payload, expected_field in (
            (
                "descriptor_ptr",
                future_kernel_args_descriptor_ptr_stub_payload,
                "descriptor_ptr",
            ),
            (
                "packed_weight",
                future_kernel_args_packed_weight_stub_payload,
                "packed_weight_descriptor",
            ),
            (
                "aux_metadata",
                future_kernel_args_aux_metadata_stub_payload,
                "aux_metadata_handle",
            ),
        ):
            if not _future_kernel_args_field_passed(
                payload,
                expected_field=expected_field,
            ):
                failures.append(f"native_stub_future_kernel_args_{label}_not_passed")
    if not future_kernel_args_compatible_path_passed:
        if future_kernel_args_compatible_path_stub_payload.get("passed") is not True:
            failures.append("native_stub_future_kernel_args_compatible_path_not_passed")
        if future_kernel_args_compatible_path_stub_payload.get("input_json") is None:
            failures.append(
                "native_stub_future_kernel_args_compatible_path_input_json_missing"
            )
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(future_kernel_args_compatible_path_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append(
                "native_stub_future_kernel_args_compatible_path_input_json_mismatch"
            )
        if (
            future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_args_compatible_consumer_path_checked"
            )
            is not True
        ):
            failures.append(
                "native_stub_future_kernel_args_compatible_path_not_checked"
            )
        if (
            future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_args_compatible_consumer_path_error_count"
            )
            != 0
        ):
            failures.append(
                "native_stub_future_kernel_args_compatible_path_error_count_mismatch"
            )
        if (
            future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_args_compatible_consumer_path_passed_to_kernel"
            )
            is not False
        ):
            failures.append(
                "native_stub_future_kernel_args_compatible_path_passed_to_kernel"
            )
        if (
            future_kernel_args_compatible_path_stub_payload.get(
                "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible"
            )
            is not False
        ):
            failures.append(
                "native_stub_future_kernel_args_compatible_path_wna16_arg_compatible"
            )
    if not future_native_consumer_passed:
        if future_kernel_native_consumer_stub_payload.get("passed") is not True:
            failures.append("native_stub_future_native_consumer_not_passed")
        if future_kernel_native_consumer_stub_payload.get("input_json") is None:
            failures.append("native_stub_future_native_consumer_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(future_kernel_native_consumer_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append("native_stub_future_native_consumer_input_json_mismatch")
        if (
            future_kernel_native_consumer_stub_payload.get(
                "future_kernel_native_consumer_checked"
            )
            is not True
        ):
            failures.append("native_stub_future_native_consumer_not_checked")
        if (
            future_kernel_native_consumer_stub_payload.get(
                "future_kernel_native_consumer_error_count"
            )
            != 0
        ):
            failures.append("native_stub_future_native_consumer_error_count_mismatch")
        if (
            future_kernel_native_consumer_stub_payload.get(
                "future_kernel_native_consumer_passed_to_kernel"
            )
            is not False
        ):
            failures.append("native_stub_future_native_consumer_passed_to_kernel")
        if (
            future_kernel_native_consumer_stub_payload.get(
                "future_kernel_native_consumer_current_wna16_arg_compatible"
            )
            is not False
        ):
            failures.append("native_stub_future_native_consumer_wna16_arg_compatible")
        if (
            future_kernel_native_consumer_stub_payload.get(
                "future_kernel_native_consumer_single_field_mirror_checked"
            )
            is not True
        ):
            failures.append("native_stub_future_native_consumer_mirror_not_checked")
        if (
            future_kernel_native_consumer_stub_payload.get(
                "future_kernel_native_consumer_single_field_mirror_field_name"
            )
            != "scale_metadata_handle"
        ):
            failures.append(
                "native_stub_future_native_consumer_mirror_field_name_mismatch"
            )
    if not future_native_consumer_extra_passed:
        for label, payload, expected_field in (
            (
                "descriptor_ptr",
                future_kernel_native_consumer_descriptor_ptr_stub_payload,
                "descriptor_ptr",
            ),
            (
                "packed_weight",
                future_kernel_native_consumer_packed_weight_stub_payload,
                "packed_weight_descriptor",
            ),
            (
                "aux_metadata",
                future_kernel_native_consumer_aux_metadata_stub_payload,
                "aux_metadata_handle",
            ),
        ):
            if not _future_native_consumer_field_passed(
                payload,
                expected_field=expected_field,
            ):
                failures.append(f"native_stub_future_native_consumer_{label}_not_passed")
    if not future_native_launch_consumer_passed:
        if future_kernel_native_consumer_launch_stub_payload.get("passed") is not True:
            failures.append("native_stub_future_native_launch_consumer_not_passed")
        if future_kernel_native_consumer_launch_stub_payload.get("input_json") is None:
            failures.append(
                "native_stub_future_native_launch_consumer_input_json_missing"
            )
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(future_kernel_native_consumer_launch_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append(
                "native_stub_future_native_launch_consumer_input_json_mismatch"
            )
        if (
            future_kernel_native_consumer_launch_stub_payload.get(
                "future_kernel_native_launch_consumer_checked"
            )
            is not True
        ):
            failures.append("native_stub_future_native_launch_consumer_not_checked")
        if (
            future_kernel_native_consumer_launch_stub_payload.get(
                "future_kernel_native_launch_consumer_error_count"
            )
            != 0
        ):
            failures.append(
                "native_stub_future_native_launch_consumer_error_count_mismatch"
            )
        if (
            future_kernel_native_consumer_launch_stub_payload.get(
                "future_kernel_native_launch_consumer_passed_to_kernel"
            )
            is not False
        ):
            failures.append("native_stub_future_native_launch_consumer_passed_to_kernel")
        if (
            future_kernel_native_consumer_launch_stub_payload.get(
                "future_kernel_native_launch_consumer_current_wna16_arg_compatible"
            )
            is not False
        ):
            failures.append(
                "native_stub_future_native_launch_consumer_wna16_arg_compatible"
            )
        if (
            future_kernel_native_consumer_launch_stub_payload.get(
                "future_kernel_native_launch_consumer_single_field_mirror_checked"
            )
            is not True
        ):
            failures.append(
                "native_stub_future_native_launch_consumer_mirror_not_checked"
            )
        if (
            future_kernel_native_consumer_launch_stub_payload.get(
                "future_kernel_native_launch_consumer_single_field_mirror_field_name"
            )
            != "scale_metadata_handle"
        ):
            failures.append(
                "native_stub_future_native_launch_consumer_mirror_field_name_mismatch"
            )
    if not future_native_launch_consumer_extra_passed:
        for label, payload, expected_field in (
            (
                "descriptor_ptr",
                future_kernel_native_consumer_launch_descriptor_ptr_stub_payload,
                "descriptor_ptr",
            ),
            (
                "packed_weight",
                future_kernel_native_consumer_launch_packed_weight_stub_payload,
                "packed_weight_descriptor",
            ),
            (
                "aux_metadata",
                future_kernel_native_consumer_launch_aux_metadata_stub_payload,
                "aux_metadata_handle",
            ),
        ):
            if not _future_native_launch_consumer_field_passed(
                payload,
                expected_field=expected_field,
            ):
                failures.append(
                    f"native_stub_future_native_launch_consumer_{label}_not_passed"
                )
    if not future_native_dispatch_consumer_passed:
        if future_kernel_native_consumer_dispatch_stub_payload.get("passed") is not True:
            failures.append("native_stub_future_native_dispatch_consumer_not_passed")
        if future_kernel_native_consumer_dispatch_stub_payload.get("input_json") is None:
            failures.append(
                "native_stub_future_native_dispatch_consumer_input_json_missing"
            )
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(future_kernel_native_consumer_dispatch_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append(
                "native_stub_future_native_dispatch_consumer_input_json_mismatch"
            )
        if (
            future_kernel_native_consumer_dispatch_stub_payload.get(
                "future_kernel_native_dispatch_consumer_checked"
            )
            is not True
        ):
            failures.append("native_stub_future_native_dispatch_consumer_not_checked")
        if (
            future_kernel_native_consumer_dispatch_stub_payload.get(
                "future_kernel_native_dispatch_consumer_error_count"
            )
            != 0
        ):
            failures.append(
                "native_stub_future_native_dispatch_consumer_error_count_mismatch"
            )
        if (
            future_kernel_native_consumer_dispatch_stub_payload.get(
                "future_kernel_native_dispatch_consumer_passed_to_kernel"
            )
            is not False
        ):
            failures.append(
                "native_stub_future_native_dispatch_consumer_passed_to_kernel"
            )
        if (
            future_kernel_native_consumer_dispatch_stub_payload.get(
                "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible"
            )
            is not False
        ):
            failures.append(
                "native_stub_future_native_dispatch_consumer_wna16_arg_compatible"
            )
    if not future_native_dispatch_consumer_extra_passed:
        for label, payload, expected_field in (
            (
                "descriptor_ptr",
                future_kernel_native_consumer_dispatch_descriptor_ptr_stub_payload,
                "descriptor_ptr",
            ),
            (
                "packed_weight",
                future_kernel_native_consumer_dispatch_packed_weight_stub_payload,
                "packed_weight_descriptor",
            ),
            (
                "aux_metadata",
                future_kernel_native_consumer_dispatch_aux_metadata_stub_payload,
                "aux_metadata_handle",
            ),
        ):
            if not _future_native_dispatch_consumer_field_passed(
                payload,
                expected_field=expected_field,
            ):
                failures.append(
                    f"native_stub_future_native_dispatch_consumer_{label}_not_passed"
                )
    if not future_native_request_ptr_passed:
        if future_kernel_native_consumer_request_ptr_stub_payload.get("passed") is not True:
            failures.append("native_stub_future_native_request_ptr_not_passed")
        if future_kernel_native_consumer_request_ptr_stub_payload.get("input_json") is None:
            failures.append("native_stub_future_native_request_ptr_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(future_kernel_native_consumer_request_ptr_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append("native_stub_future_native_request_ptr_input_json_mismatch")
        if (
            future_kernel_native_consumer_request_ptr_stub_payload.get(
                "future_kernel_native_consumer_request_ptr_checked"
            )
            is not True
        ):
            failures.append("native_stub_future_native_request_ptr_not_checked")
        if (
            future_kernel_native_consumer_request_ptr_stub_payload.get(
                "future_kernel_native_consumer_request_ptr_summary_error_count"
            )
            != 0
        ):
            failures.append(
                "native_stub_future_native_request_ptr_summary_error_count_mismatch"
            )
        if (
            future_kernel_native_consumer_request_ptr_stub_payload.get(
                "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator"
            )
            != future_kernel_native_consumer_request_ptr_stub_payload.get(
                "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator"
            )
        ):
            failures.append("native_stub_future_native_request_ptr_row_hash_mismatch")
    if not future_native_request_launch_passed:
        if (
            future_kernel_native_consumer_request_launch_stub_payload.get("passed")
            is not True
        ):
            failures.append("native_stub_future_native_request_launch_not_passed")
        if (
            future_kernel_native_consumer_request_launch_stub_payload.get("input_json")
            is None
        ):
            failures.append(
                "native_stub_future_native_request_launch_input_json_missing"
            )
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(
                    future_kernel_native_consumer_request_launch_stub_payload.get(
                        "input_json"
                    )
                )
            )
            != input_path
        ):
            failures.append(
                "native_stub_future_native_request_launch_input_json_mismatch"
            )
        if (
            future_kernel_native_consumer_request_launch_stub_payload.get(
                "future_kernel_native_consumer_request_launch_checked"
            )
            is not True
        ):
            failures.append("native_stub_future_native_request_launch_not_checked")
        if (
            future_kernel_native_consumer_request_launch_stub_payload.get(
                "future_kernel_native_consumer_request_launch_summary_error_count"
            )
            != 0
        ):
            failures.append(
                "native_stub_future_native_request_launch_summary_error_count_mismatch"
            )
        if (
            future_kernel_native_consumer_request_launch_stub_payload.get(
                "future_kernel_native_consumer_request_launch_summary_row_hash_accumulator"
            )
            != future_kernel_native_consumer_request_launch_stub_payload.get(
                "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator"
            )
        ):
            failures.append("native_stub_future_native_request_launch_row_hash_mismatch")
    if not future_native_request_launch_ptr_passed:
        if (
            future_kernel_native_consumer_request_launch_ptr_stub_payload.get("passed")
            is not True
        ):
            failures.append("native_stub_future_native_request_launch_ptr_not_passed")
        if (
            future_kernel_native_consumer_request_launch_ptr_stub_payload.get(
                "input_json"
            )
            is None
        ):
            failures.append(
                "native_stub_future_native_request_launch_ptr_input_json_missing"
            )
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(
                    future_kernel_native_consumer_request_launch_ptr_stub_payload.get(
                        "input_json"
                    )
                )
            )
            != input_path
        ):
            failures.append(
                "native_stub_future_native_request_launch_ptr_input_json_mismatch"
            )
        if (
            future_kernel_native_consumer_request_launch_ptr_stub_payload.get(
                "future_kernel_native_consumer_request_launch_ptr_checked"
            )
            is not True
        ):
            failures.append("native_stub_future_native_request_launch_ptr_not_checked")
        if (
            future_kernel_native_consumer_request_launch_ptr_stub_payload.get(
                "future_kernel_native_consumer_request_launch_ptr_summary_error_count"
            )
            != 0
        ):
            failures.append(
                "native_stub_future_native_request_launch_ptr_summary_error_count_mismatch"
            )
        if (
            future_kernel_native_consumer_request_launch_ptr_stub_payload.get(
                "future_kernel_native_consumer_request_launch_ptr_summary_row_hash_accumulator"
            )
            != future_kernel_native_consumer_request_launch_ptr_stub_payload.get(
                "future_kernel_native_consumer_request_launch_summary_row_hash_accumulator"
            )
        ):
            failures.append(
                "native_stub_future_native_request_launch_ptr_row_hash_mismatch"
            )
    if not extra_input_checks_passed:
        failures.append("extra_online_input_stub_check_not_passed")

    required_evidence = preflight_status_payload.get("required_evidence")
    if not isinstance(required_evidence, dict):
        required_evidence = {}
    optional_evidence = preflight_status_payload.get("optional_evidence")
    if not isinstance(optional_evidence, dict):
        optional_evidence = {}

    return {
        "passed": passed,
        "failures": failures,
        "trace_config": str(trace_config),
        "trace_output_dir": str(output_dir),
        "performance_summary": str(performance_path),
        "online_prelaunch_input_json": str(input_path),
        "online_prelaunch_input_jsons": [str(path) for path in input_paths],
        "online_prelaunch_input_check_count": len(input_paths),
        "online_prelaunch_input_row_counts": input_row_counts,
        "online_prelaunch_input_row_count_min": (
            min(input_row_counts) if input_row_counts else None
        ),
        "online_prelaunch_input_row_count_max": (
            max(input_row_counts) if input_row_counts else None
        ),
        "online_prelaunch_input_row_count_sum": (
            sum(input_row_counts) if input_row_counts else None
        ),
        "online_prelaunch_input_row_count_diverse": (
            (min(input_row_counts) < max(input_row_counts))
            if input_row_counts
            else None
        ),
        "online_prelaunch_input_extra_check_count": len(extra_input_check_summaries),
        "online_prelaunch_input_extra_check_passed_count": sum(
            1 for item in extra_input_check_summaries if item.get("passed") is True
        ),
        "extra_online_input_check_summaries": extra_input_check_summaries,
        "native_stub_output_json": str(stub_output),
        "per_field_native_stub_output_json": str(per_field_stub_output),
        "kernel_envelope_mirror_native_stub_output_json": str(
            envelope_mirror_stub_output
        ),
        "packed_weight_mirror_native_stub_output_json": str(
            packed_weight_mirror_stub_output
        ),
        "aux_metadata_mirror_native_stub_output_json": str(
            aux_metadata_mirror_stub_output
        ),
        "descriptor_ptr_mirror_native_stub_output_json": str(
            descriptor_ptr_mirror_stub_output
        ),
        "kernel_side_compatible_native_stub_output_json": str(
            kernel_side_compatible_stub_output
        ),
        "future_kernel_args_native_stub_output_json": str(
            future_kernel_args_stub_output
        ),
        "future_kernel_args_descriptor_ptr_native_stub_output_json": str(
            future_kernel_args_descriptor_ptr_stub_output
        ),
        "future_kernel_args_packed_weight_native_stub_output_json": str(
            future_kernel_args_packed_weight_stub_output
        ),
        "future_kernel_args_aux_metadata_native_stub_output_json": str(
            future_kernel_args_aux_metadata_stub_output
        ),
        "future_kernel_args_compatible_path_native_stub_output_json": str(
            future_kernel_args_compatible_path_stub_output
        ),
        "future_kernel_native_consumer_native_stub_output_json": str(
            future_kernel_native_consumer_stub_output
        ),
        "future_kernel_native_consumer_descriptor_ptr_native_stub_output_json": str(
            future_kernel_native_consumer_descriptor_ptr_stub_output
        ),
        "future_kernel_native_consumer_packed_weight_native_stub_output_json": str(
            future_kernel_native_consumer_packed_weight_stub_output
        ),
        "future_kernel_native_consumer_aux_metadata_native_stub_output_json": str(
            future_kernel_native_consumer_aux_metadata_stub_output
        ),
        "future_kernel_native_consumer_launch_native_stub_output_json": str(
            future_kernel_native_consumer_launch_stub_output
        ),
        "future_kernel_native_consumer_launch_descriptor_ptr_native_stub_output_json": str(
            future_kernel_native_consumer_launch_descriptor_ptr_stub_output
        ),
        "future_kernel_native_consumer_launch_packed_weight_native_stub_output_json": str(
            future_kernel_native_consumer_launch_packed_weight_stub_output
        ),
        "future_kernel_native_consumer_launch_aux_metadata_native_stub_output_json": str(
            future_kernel_native_consumer_launch_aux_metadata_stub_output
        ),
        "future_kernel_native_consumer_dispatch_native_stub_output_json": str(
            future_kernel_native_consumer_dispatch_stub_output
        ),
        "future_kernel_native_consumer_dispatch_descriptor_ptr_native_stub_output_json": str(
            future_kernel_native_consumer_dispatch_descriptor_ptr_stub_output
        ),
        "future_kernel_native_consumer_dispatch_packed_weight_native_stub_output_json": str(
            future_kernel_native_consumer_dispatch_packed_weight_stub_output
        ),
        "future_kernel_native_consumer_dispatch_aux_metadata_native_stub_output_json": str(
            future_kernel_native_consumer_dispatch_aux_metadata_stub_output
        ),
        "future_kernel_native_consumer_request_ptr_native_stub_output_json": str(
            future_kernel_native_consumer_request_ptr_stub_output
        ),
        "future_kernel_native_consumer_request_launch_native_stub_output_json": str(
            future_kernel_native_consumer_request_launch_stub_output
        ),
        "future_kernel_native_consumer_request_launch_ptr_native_stub_output_json": str(
            future_kernel_native_consumer_request_launch_ptr_stub_output
        ),
        "preflight_output_json": str(preflight_output),
        "preflight_status_output_json": str(preflight_status_output),
        "preflight_status_check_output_json": str(preflight_status_check_output),
        "pointer_source_observer_check": pointer_source_observer_check,
        "pointer_source_observer_check_json": str(
            _resolve_repo_path(args.pointer_source_observer_check_json)
        ),
        "pointer_source_observer_check_required": bool(
            args.require_pointer_source_observer_check
        ),
        "pointer_source_observer_check_passed": (
            pointer_source_observer_check.get("passed") is True
        ),
        "pointer_source_observer_gate_passed": pointer_source_observer_gate_passed,
        "gpu_index": args.gpu_index,
        "stub_device": int(args.stub_device),
        "future_native_dispatch_row_offset": int(
            args.future_native_dispatch_row_offset
        ),
        "future_native_dispatch_row_limit": (
            None
            if args.future_native_dispatch_row_limit is None
            else int(args.future_native_dispatch_row_limit)
        ),
        **(
            {
                "future_native_dispatch_tail_window_size": int(
                    args.future_native_dispatch_tail_window_size
                )
            }
            if args.future_native_dispatch_tail_window_size is not None
            else {}
        ),
        "steps": steps,
        "stub_summary": {
            key: stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "kernel_side_consumer_path_checked",
                "kernel_side_consumer_path_name",
                "kernel_side_consumer_path_row_count",
                "kernel_side_consumer_path_row_ok_count",
                "kernel_side_consumer_path_error_count",
                "kernel_side_consumer_path_payload_bytes",
                "kernel_side_consumer_path_passed_to_kernel",
                "kernel_side_consumer_path_changes_kernel_launch_args",
                "kernel_side_consumer_path_current_wna16_arg_compatible",
                "input_json",
            )
        },
        "per_field_stub_summary": {
            key: per_field_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "kernel_envelope_mirror_stub_summary": {
            key: envelope_mirror_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "kernel_consumer_envelope_checked",
                "kernel_consumer_envelope_payload_bytes",
                "kernel_consumer_envelope_passed_to_kernel",
                "single_field_mirror_checked",
                "single_field_mirror_field_name",
                "single_field_mirror_row_count",
                "single_field_mirror_row_ok_count",
                "single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "packed_weight_mirror_stub_summary": {
            key: packed_weight_mirror_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "single_field_mirror_checked",
                "single_field_mirror_field_name",
                "single_field_mirror_row_count",
                "single_field_mirror_row_ok_count",
                "single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "aux_metadata_mirror_stub_summary": {
            key: aux_metadata_mirror_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "single_field_mirror_checked",
                "single_field_mirror_field_name",
                "single_field_mirror_row_count",
                "single_field_mirror_row_ok_count",
                "single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "descriptor_ptr_mirror_stub_summary": {
            key: descriptor_ptr_mirror_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "single_field_mirror_checked",
                "single_field_mirror_field_name",
                "single_field_mirror_row_count",
                "single_field_mirror_row_ok_count",
                "single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "kernel_side_compatible_stub_summary": {
            key: kernel_side_compatible_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "kernel_side_compatible_consumer_checked",
                "kernel_side_compatible_consumer_name",
                "kernel_side_compatible_consumer_mode",
                "kernel_side_compatible_consumer_source",
                "kernel_side_compatible_consumer_row_count",
                "kernel_side_compatible_consumer_row_ok_count",
                "kernel_side_compatible_consumer_error_count",
                "kernel_side_compatible_consumer_payload_bytes",
                "kernel_side_compatible_consumer_passed_to_kernel",
                "kernel_side_compatible_consumer_changes_kernel_launch_args",
                "kernel_side_compatible_consumer_current_wna16_arg_compatible",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "future_kernel_args_stub_summary": {
            key: future_kernel_args_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "future_kernel_consumer_args_checked",
                "future_kernel_consumer_args_name",
                "future_kernel_consumer_args_mode",
                "future_kernel_consumer_args_source",
                *FUTURE_KERNEL_ARGS_LAYOUT_SUMMARY_KEYS,
                "future_kernel_consumer_args_row_count",
                "future_kernel_consumer_args_row_ok_count",
                "future_kernel_consumer_args_error_count",
                "future_kernel_consumer_args_payload_bytes",
                "future_kernel_consumer_args_passed_to_kernel",
                "future_kernel_consumer_args_changes_kernel_launch_args",
                "future_kernel_consumer_args_current_wna16_arg_compatible",
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation",
                "future_kernel_consumer_args_field_mask",
                "future_kernel_consumer_args_required_field_mask",
                "future_kernel_consumer_args_single_field_mirror_checked",
                "future_kernel_consumer_args_single_field_mirror_field_name",
                "future_kernel_consumer_args_single_field_mirror_row_count",
                "future_kernel_consumer_args_single_field_mirror_row_ok_count",
                "future_kernel_consumer_args_single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "future_kernel_args_descriptor_ptr_stub_summary": {
            key: future_kernel_args_descriptor_ptr_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "future_kernel_consumer_args_checked",
                "future_kernel_consumer_args_name",
                "future_kernel_consumer_args_mode",
                "future_kernel_consumer_args_source",
                *FUTURE_KERNEL_ARGS_LAYOUT_SUMMARY_KEYS,
                "future_kernel_consumer_args_row_count",
                "future_kernel_consumer_args_row_ok_count",
                "future_kernel_consumer_args_error_count",
                "future_kernel_consumer_args_payload_bytes",
                "future_kernel_consumer_args_passed_to_kernel",
                "future_kernel_consumer_args_changes_kernel_launch_args",
                "future_kernel_consumer_args_current_wna16_arg_compatible",
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation",
                "future_kernel_consumer_args_field_mask",
                "future_kernel_consumer_args_required_field_mask",
                "future_kernel_consumer_args_single_field_mirror_checked",
                "future_kernel_consumer_args_single_field_mirror_field_name",
                "future_kernel_consumer_args_single_field_mirror_row_count",
                "future_kernel_consumer_args_single_field_mirror_row_ok_count",
                "future_kernel_consumer_args_single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "future_kernel_args_packed_weight_stub_summary": {
            key: future_kernel_args_packed_weight_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "future_kernel_consumer_args_checked",
                "future_kernel_consumer_args_name",
                "future_kernel_consumer_args_mode",
                "future_kernel_consumer_args_source",
                *FUTURE_KERNEL_ARGS_LAYOUT_SUMMARY_KEYS,
                "future_kernel_consumer_args_row_count",
                "future_kernel_consumer_args_row_ok_count",
                "future_kernel_consumer_args_error_count",
                "future_kernel_consumer_args_payload_bytes",
                "future_kernel_consumer_args_passed_to_kernel",
                "future_kernel_consumer_args_changes_kernel_launch_args",
                "future_kernel_consumer_args_current_wna16_arg_compatible",
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation",
                "future_kernel_consumer_args_field_mask",
                "future_kernel_consumer_args_required_field_mask",
                "future_kernel_consumer_args_single_field_mirror_checked",
                "future_kernel_consumer_args_single_field_mirror_field_name",
                "future_kernel_consumer_args_single_field_mirror_row_count",
                "future_kernel_consumer_args_single_field_mirror_row_ok_count",
                "future_kernel_consumer_args_single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "future_kernel_args_aux_metadata_stub_summary": {
            key: future_kernel_args_aux_metadata_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "future_kernel_consumer_args_checked",
                "future_kernel_consumer_args_name",
                "future_kernel_consumer_args_mode",
                "future_kernel_consumer_args_source",
                *FUTURE_KERNEL_ARGS_LAYOUT_SUMMARY_KEYS,
                "future_kernel_consumer_args_row_count",
                "future_kernel_consumer_args_row_ok_count",
                "future_kernel_consumer_args_error_count",
                "future_kernel_consumer_args_payload_bytes",
                "future_kernel_consumer_args_passed_to_kernel",
                "future_kernel_consumer_args_changes_kernel_launch_args",
                "future_kernel_consumer_args_current_wna16_arg_compatible",
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation",
                "future_kernel_consumer_args_field_mask",
                "future_kernel_consumer_args_required_field_mask",
                "future_kernel_consumer_args_single_field_mirror_checked",
                "future_kernel_consumer_args_single_field_mirror_field_name",
                "future_kernel_consumer_args_single_field_mirror_row_count",
                "future_kernel_consumer_args_single_field_mirror_row_ok_count",
                "future_kernel_consumer_args_single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "future_kernel_args_compatible_path_stub_summary": {
            key: future_kernel_args_compatible_path_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "future_kernel_consumer_args_checked",
                "future_kernel_consumer_args_name",
                "future_kernel_consumer_args_mode",
                "future_kernel_consumer_args_source",
                *FUTURE_KERNEL_ARGS_LAYOUT_SUMMARY_KEYS,
                "future_kernel_consumer_args_row_count",
                "future_kernel_consumer_args_row_ok_count",
                "future_kernel_consumer_args_error_count",
                "future_kernel_consumer_args_payload_bytes",
                "future_kernel_consumer_args_passed_to_kernel",
                "future_kernel_consumer_args_changes_kernel_launch_args",
                "future_kernel_consumer_args_current_wna16_arg_compatible",
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation",
                "future_kernel_consumer_args_field_mask",
                "future_kernel_consumer_args_required_field_mask",
                "future_kernel_args_compatible_consumer_path_checked",
                "future_kernel_args_compatible_consumer_path_name",
                "future_kernel_args_compatible_consumer_path_mode",
                "future_kernel_args_compatible_consumer_path_source",
                "future_kernel_args_compatible_consumer_path_row_count",
                "future_kernel_args_compatible_consumer_path_row_ok_count",
                "future_kernel_args_compatible_consumer_path_error_count",
                "future_kernel_args_compatible_consumer_path_payload_bytes",
                "future_kernel_args_compatible_consumer_path_passed_to_kernel",
                "future_kernel_args_compatible_consumer_path_changes_kernel_launch_args",
                "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible",
                "future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "future_kernel_native_consumer_stub_summary": {
            key: future_kernel_native_consumer_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_descriptor_ptr_stub_summary": {
            key: future_kernel_native_consumer_descriptor_ptr_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_packed_weight_stub_summary": {
            key: future_kernel_native_consumer_packed_weight_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_aux_metadata_stub_summary": {
            key: future_kernel_native_consumer_aux_metadata_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_launch_stub_summary": {
            key: future_kernel_native_consumer_launch_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_LAUNCH_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_launch_descriptor_ptr_stub_summary": {
            key: future_kernel_native_consumer_launch_descriptor_ptr_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_LAUNCH_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_launch_packed_weight_stub_summary": {
            key: future_kernel_native_consumer_launch_packed_weight_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_LAUNCH_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_launch_aux_metadata_stub_summary": {
            key: future_kernel_native_consumer_launch_aux_metadata_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_LAUNCH_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_dispatch_stub_summary": {
            key: future_kernel_native_consumer_dispatch_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_DISPATCH_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary": {
            key: future_kernel_native_consumer_dispatch_descriptor_ptr_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_DISPATCH_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_dispatch_packed_weight_stub_summary": {
            key: future_kernel_native_consumer_dispatch_packed_weight_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_DISPATCH_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_dispatch_aux_metadata_stub_summary": {
            key: future_kernel_native_consumer_dispatch_aux_metadata_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_DISPATCH_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_request_ptr_stub_summary": {
            key: future_kernel_native_consumer_request_ptr_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_REQUEST_PTR_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_request_launch_stub_summary": {
            key: future_kernel_native_consumer_request_launch_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_REQUEST_LAUNCH_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_request_launch_ptr_stub_summary": {
            key: future_kernel_native_consumer_request_launch_ptr_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_REQUEST_LAUNCH_PTR_CONSUMER_SUMMARY_KEYS
        },
        # The arg-slot summaries below are projections of the same dispatch
        # payload used by the dispatch ABI canary.  They are top-level
        # observability aliases so readers do not need to mine the full
        # dispatch summary or artifact checker for arg-slot row counts.
        "future_kernel_native_consumer_dispatch_arg_slot_stub_summary": {
            key: future_kernel_native_consumer_dispatch_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_ARG_SLOT_CONSUMER_SUMMARY_KEYS
        },
        "future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_summary": {
            key: future_kernel_native_consumer_dispatch_stub_payload.get(key)
            for key in FUTURE_KERNEL_NATIVE_ARG_SLOT_CONSUMER_SUMMARY_KEYS
        },
        "preflight_summary": {
            "passed": preflight_payload.get("passed"),
            "failures": preflight_payload.get("failures"),
            "deferred_online_prelaunch_runner_evidence": (
                (preflight_payload.get("lab_gate_status_summary") or {}).get(
                    "deferred_online_prelaunch_runner_evidence"
                )
                if isinstance(
                    preflight_payload.get("lab_gate_status_summary"), dict
                )
                else None
            ),
        },
        "preflight_status_summary": {
            "passed": preflight_status_payload.get("passed"),
            "runtime_gate_evidence_deferred_count": (
                preflight_status_payload.get("runtime_gate_evidence_deferred_count")
            ),
            "strict_default_gate_evidence_deferred_count": (
                preflight_status_payload.get(
                    "strict_default_gate_evidence_deferred_count"
                )
            ),
            "required_evidence_passed": required_evidence.get("passed"),
            "required_evidence_present_count": required_evidence.get(
                "present_count"
            ),
            "required_evidence_passed_count": required_evidence.get("passed_count"),
            "required_evidence_required_count": required_evidence.get(
                "required_count"
            ),
            "optional_evidence_passed": optional_evidence.get("passed"),
            "optional_evidence_present_count": optional_evidence.get(
                "present_count"
            ),
            "optional_evidence_passed_count": optional_evidence.get("passed_count"),
            "optional_evidence_required_count": optional_evidence.get(
                "required_count"
            ),
            "native_typed_consumer_bridge_required": preflight_status_payload.get(
                "native_typed_consumer_bridge_required"
            ),
            "native_stub_online_invocation_canary_required": (
                preflight_status_payload.get(
                    "native_stub_online_invocation_canary_required"
                )
            ),
            "payload_bytes_required": preflight_status_payload.get(
                "payload_bytes_required"
            ),
            "passed_to_kernel_required": preflight_status_payload.get(
                "passed_to_kernel_required"
            ),
            "changes_kernel_launch_args_required": preflight_status_payload.get(
                "changes_kernel_launch_args_required"
            ),
        },
    }
    return result


def finalize_report_with_strict_preflight(
    *,
    args: argparse.Namespace,
    payload: dict[str, object],
    allow_runner_self_finalization: bool = False,
    step_prefix: str = "final",
) -> dict[str, object]:
    if args.dry_run or args.skip_preflight:
        return payload
    env = _base_env(gpu_index=args.gpu_index)
    steps = payload.setdefault("steps", {})
    if not isinstance(steps, dict):
        steps = {}
        payload["steps"] = steps
    preflight_output = _resolve_repo_path(args.preflight_output_json)
    preflight_status_output = _resolve_repo_path(args.preflight_status_output_json)
    preflight_status_check_output = _resolve_repo_path(
        args.preflight_status_check_output_json
    )
    # Final validation must use the same no-defer lab gate as the standalone
    # preflight; the runner should not weaken missing-evidence checks.
    preflight_step = f"{step_prefix}_preflight"
    status_step = f"{step_prefix}_preflight_status"
    status_check_step = f"{step_prefix}_preflight_status_check"
    steps[preflight_step] = _run(
        _preflight_command(
            output_json=preflight_output,
            summary_only=False,
            defer_runner=False,
            defer_artifact=False,
            allow_runner_self_finalization=allow_runner_self_finalization,
        ),
        env=env,
        dry_run=False,
        allow_failure=True,
    )
    steps[status_step] = _run(
        _preflight_command(
            output_json=preflight_status_output,
            summary_only=True,
            defer_runner=False,
            defer_artifact=False,
            allow_runner_self_finalization=allow_runner_self_finalization,
        ),
        env=env,
        dry_run=False,
        allow_failure=True,
    )
    steps[status_check_step] = _run(
        _preflight_status_check_command(
            summary_json=preflight_status_output,
            output_json=preflight_status_check_output,
        ),
        env=env,
        dry_run=False,
        allow_failure=True,
    )
    final_preflight_payload = _load_json_if_exists(preflight_output)
    final_status_payload = _load_json_if_exists(preflight_status_output)
    final_status_check_payload = _load_json_if_exists(preflight_status_check_output)
    final_preflight_summary = {
        "passed": final_preflight_payload.get("passed"),
        "failures": final_preflight_payload.get("failures"),
    }
    required_evidence = final_status_payload.get("required_evidence")
    if not isinstance(required_evidence, dict):
        required_evidence = {}
    optional_evidence = final_status_payload.get("optional_evidence")
    if not isinstance(optional_evidence, dict):
        optional_evidence = {}
    final_status_summary = {
        "passed": final_status_payload.get("passed"),
        "runtime_gate_evidence_deferred_count": final_status_payload.get(
            "runtime_gate_evidence_deferred_count"
        ),
        "strict_default_gate_evidence_deferred_count": final_status_payload.get(
            "strict_default_gate_evidence_deferred_count"
        ),
        "required_evidence_passed": required_evidence.get("passed"),
        "required_evidence_present_count": required_evidence.get("present_count"),
        "required_evidence_passed_count": required_evidence.get("passed_count"),
        "required_evidence_required_count": required_evidence.get("required_count"),
        "optional_evidence_passed": optional_evidence.get("passed"),
        "optional_evidence_present_count": optional_evidence.get("present_count"),
        "optional_evidence_passed_count": optional_evidence.get("passed_count"),
        "optional_evidence_required_count": optional_evidence.get("required_count"),
        "native_typed_consumer_bridge_required": final_status_payload.get(
            "native_typed_consumer_bridge_required"
        ),
        "native_stub_online_invocation_canary_required": final_status_payload.get(
            "native_stub_online_invocation_canary_required"
        ),
        "payload_bytes_required": final_status_payload.get("payload_bytes_required"),
        "passed_to_kernel_required": final_status_payload.get(
            "passed_to_kernel_required"
        ),
        "changes_kernel_launch_args_required": final_status_payload.get(
            "changes_kernel_launch_args_required"
        ),
    }
    final_preflight_summary["runner_self_finalization_allowed"] = bool(
        allow_runner_self_finalization
    )
    final_status_summary["runner_self_finalization_allowed"] = bool(
        allow_runner_self_finalization
    )
    payload["final_preflight_summary"] = final_preflight_summary
    payload["final_preflight_status_summary"] = final_status_summary
    payload["final_preflight_status_check_output_json"] = str(
        preflight_status_check_output
    )
    payload["final_preflight_status_check_summary"] = {
        "passed": final_status_check_payload.get("passed"),
        "failures": final_status_check_payload.get("failures"),
        "source": final_status_check_payload.get("source"),
        "online_merged_source_count": final_status_check_payload.get(
            "online_merged_source_count"
        ),
        "online_merged_row_count": final_status_check_payload.get(
            "online_merged_row_count"
        ),
        "online_merged_dispatch_active_rows": final_status_check_payload.get(
            "online_merged_dispatch_active_rows"
        ),
    }
    failures = payload.get("failures")
    if not isinstance(failures, list):
        failures = []
    if final_preflight_payload.get("passed") is not True:
        failures.append("final_preflight_not_passed")
    if final_status_payload.get("passed") is not True:
        failures.append("final_preflight_status_not_passed")
    if final_status_check_payload.get("passed") is not True:
        failures.append("final_preflight_status_check_not_passed")
    payload["failures"] = failures
    payload["passed"] = bool(payload.get("passed") is True and not failures)
    return payload


def finalize_report_with_artifact_check(
    *,
    args: argparse.Namespace,
    payload: dict[str, object],
    runner_json: Path,
    allow_bootstrap_preflight: bool = False,
) -> dict[str, object]:
    if args.dry_run or args.skip_preflight or args.skip_artifact_check:
        return payload
    env = _base_env(gpu_index=args.gpu_index)
    steps = payload.setdefault("steps", {})
    if not isinstance(steps, dict):
        steps = {}
        payload["steps"] = steps
    canonical_artifact_output = _resolve_repo_path(args.artifact_check_output_json)
    artifact_output = canonical_artifact_output
    if allow_bootstrap_preflight:
        artifact_output = artifact_output.with_name(
            f"{artifact_output.stem}_bootstrap{artifact_output.suffix}"
        )
    step_name = (
        "artifact_check_bootstrap"
        if allow_bootstrap_preflight
        else "artifact_check_final"
    )
    steps[step_name] = _run(
        _artifact_check_command(
            runner_json=runner_json,
            preflight_json=_resolve_repo_path(args.preflight_output_json),
            status_json=_resolve_repo_path(args.preflight_status_output_json),
            output_json=artifact_output,
            min_online_inputs=int(args.min_artifact_online_inputs),
            allow_bootstrap_preflight=allow_bootstrap_preflight,
        ),
        env=env,
        dry_run=False,
        allow_failure=True,
    )
    artifact_payload = _load_json_if_exists(artifact_output)
    if allow_bootstrap_preflight and artifact_payload:
        # The lab gate points at the canonical artifact-check path. During the
        # bootstrap stage, mirror the bootstrap payload there so the
        # self-finalization preflight can recognize the evidence as deliberately
        # self-referential. The later strict artifact-check pass overwrites this
        # path with the no-defer artifact before the final lab gate is accepted.
        canonical_artifact_output.parent.mkdir(parents=True, exist_ok=True)
        canonical_artifact_output.write_text(
            json.dumps(artifact_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    output_key = (
        "artifact_check_bootstrap_output_json"
        if allow_bootstrap_preflight
        else "artifact_check_output_json"
    )
    summary_key = (
        "artifact_check_bootstrap_summary"
        if allow_bootstrap_preflight
        else "artifact_check_summary"
    )
    payload[output_key] = str(artifact_output)
    artifact_summary = {
        "passed": artifact_payload.get("passed"),
        "bootstrap_preflight_allowed": bool(allow_bootstrap_preflight),
        "failures": artifact_payload.get("failures"),
        "runner_stub_row_count": artifact_payload.get("runner_stub_row_count"),
        "runner_stub_row_ok_count": artifact_payload.get("runner_stub_row_ok_count"),
        "require_all_field_mirror_stubs": artifact_payload.get(
            "require_all_field_mirror_stubs"
        ),
        "min_online_inputs": artifact_payload.get("min_online_inputs"),
        "runner_online_prelaunch_input_check_count": artifact_payload.get(
            "runner_online_prelaunch_input_check_count"
        ),
        "runner_online_prelaunch_input_row_counts": artifact_payload.get(
            "runner_online_prelaunch_input_row_counts"
        ),
        "runner_online_prelaunch_input_row_count_min": artifact_payload.get(
            "runner_online_prelaunch_input_row_count_min"
        ),
        "runner_online_prelaunch_input_row_count_max": artifact_payload.get(
            "runner_online_prelaunch_input_row_count_max"
        ),
        "runner_online_prelaunch_input_row_count_sum": artifact_payload.get(
            "runner_online_prelaunch_input_row_count_sum"
        ),
        "runner_online_prelaunch_input_row_count_diverse": artifact_payload.get(
            "runner_online_prelaunch_input_row_count_diverse"
        ),
        "runner_online_prelaunch_input_extra_check_count": artifact_payload.get(
            "runner_online_prelaunch_input_extra_check_count"
        ),
        "runner_online_prelaunch_input_extra_check_passed_count": artifact_payload.get(
            "runner_online_prelaunch_input_extra_check_passed_count"
        ),
        "runner_descriptor_ptr_mirror_stub_row_count": artifact_payload.get(
            "runner_descriptor_ptr_mirror_stub_row_count"
        ),
        "runner_descriptor_ptr_mirror_stub_row_ok_count": artifact_payload.get(
            "runner_descriptor_ptr_mirror_stub_row_ok_count"
        ),
        "runner_packed_weight_mirror_stub_row_count": artifact_payload.get(
            "runner_packed_weight_mirror_stub_row_count"
        ),
        "runner_packed_weight_mirror_stub_row_ok_count": artifact_payload.get(
            "runner_packed_weight_mirror_stub_row_ok_count"
        ),
        "runner_kernel_envelope_mirror_stub_row_count": artifact_payload.get(
            "runner_kernel_envelope_mirror_stub_row_count"
        ),
        "runner_kernel_envelope_mirror_stub_row_ok_count": artifact_payload.get(
            "runner_kernel_envelope_mirror_stub_row_ok_count"
        ),
        "runner_aux_metadata_mirror_stub_row_count": artifact_payload.get(
            "runner_aux_metadata_mirror_stub_row_count"
        ),
        "runner_aux_metadata_mirror_stub_row_ok_count": artifact_payload.get(
            "runner_aux_metadata_mirror_stub_row_ok_count"
        ),
        "runner_kernel_side_compatible_stub_row_count": artifact_payload.get(
            "runner_kernel_side_compatible_stub_row_count"
        ),
        "runner_kernel_side_compatible_stub_row_ok_count": artifact_payload.get(
            "runner_kernel_side_compatible_stub_row_ok_count"
        ),
        "runner_future_kernel_args_stub_row_count": artifact_payload.get(
            "runner_future_kernel_args_stub_row_count"
        ),
        "runner_future_kernel_args_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_args_stub_row_ok_count"
        ),
        "runner_future_kernel_args_descriptor_ptr_stub_row_count": artifact_payload.get(
            "runner_future_kernel_args_descriptor_ptr_stub_row_count"
        ),
        "runner_future_kernel_args_descriptor_ptr_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_args_descriptor_ptr_stub_row_ok_count"
        ),
        "runner_future_kernel_args_packed_weight_stub_row_count": artifact_payload.get(
            "runner_future_kernel_args_packed_weight_stub_row_count"
        ),
        "runner_future_kernel_args_packed_weight_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_args_packed_weight_stub_row_ok_count"
        ),
        "runner_future_kernel_args_aux_metadata_stub_row_count": artifact_payload.get(
            "runner_future_kernel_args_aux_metadata_stub_row_count"
        ),
        "runner_future_kernel_args_aux_metadata_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_args_aux_metadata_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_packed_weight_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_packed_weight_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_packed_weight_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_packed_weight_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_aux_metadata_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_aux_metadata_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_aux_metadata_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_aux_metadata_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_launch_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_launch_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_launch_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_launch_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_request_ptr_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_request_ptr_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_request_ptr_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_request_ptr_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_request_launch_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_request_launch_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_request_launch_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_request_launch_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_request_launch_ptr_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_request_launch_ptr_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_request_launch_ptr_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_request_launch_ptr_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_ok_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_row_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_row_count"
        ),
        "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_row_ok_count": artifact_payload.get(
            "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_row_ok_count"
        ),
        "stage1_deferred_count": artifact_payload.get("stage1_deferred_count"),
        "final_deferred_count": artifact_payload.get("final_deferred_count"),
        "status_deferred_count": artifact_payload.get("status_deferred_count"),
    }
    payload[summary_key] = artifact_summary
    failures = payload.get("failures")
    if not isinstance(failures, list):
        failures = []
    if artifact_payload.get("passed") is not True:
        failures.append("artifact_consistency_check_failed")
    payload["failures"] = failures
    payload["passed"] = bool(payload.get("passed") is True and not failures)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-config", type=Path, default=DEFAULT_TRACE_CONFIG)
    parser.add_argument("--gpu-index", type=int, default=1)
    parser.add_argument("--stub-device", type=int, default=0)
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument(
        "--max-online-inputs",
        type=int,
        default=1,
        help=(
            "Maximum exported online prelaunch inputs to feed through the "
            "native stub suite. Use 0 to check every exported input."
        ),
    )
    parser.add_argument(
        "--min-artifact-online-inputs",
        type=int,
        default=1,
        help="Minimum online prelaunch inputs required by the artifact checker.",
    )
    parser.add_argument("--stub-output-json", type=Path, default=DEFAULT_STUB_OUTPUT)
    parser.add_argument(
        "--per-field-stub-output-json",
        type=Path,
        default=DEFAULT_PER_FIELD_STUB_OUTPUT,
    )
    parser.add_argument(
        "--envelope-mirror-stub-output-json",
        type=Path,
        default=DEFAULT_ENVELOPE_MIRROR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--packed-weight-mirror-stub-output-json",
        type=Path,
        default=DEFAULT_PACKED_WEIGHT_MIRROR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--aux-metadata-mirror-stub-output-json",
        type=Path,
        default=DEFAULT_AUX_METADATA_MIRROR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--descriptor-ptr-mirror-stub-output-json",
        type=Path,
        default=DEFAULT_DESCRIPTOR_PTR_MIRROR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--kernel-side-compatible-stub-output-json",
        type=Path,
        default=DEFAULT_KERNEL_SIDE_COMPATIBLE_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-args-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_ARGS_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-args-descriptor-ptr-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_ARGS_DESCRIPTOR_PTR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-args-packed-weight-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_ARGS_PACKED_WEIGHT_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-args-aux-metadata-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_ARGS_AUX_METADATA_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-args-compatible-path-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_ARGS_COMPATIBLE_PATH_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-descriptor-ptr-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DESCRIPTOR_PTR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-packed-weight-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_PACKED_WEIGHT_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-aux-metadata-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_AUX_METADATA_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-launch-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-launch-descriptor-ptr-stub-output-json",
        type=Path,
        default=(
            DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_DESCRIPTOR_PTR_STUB_OUTPUT
        ),
    )
    parser.add_argument(
        "--future-kernel-native-consumer-launch-packed-weight-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_PACKED_WEIGHT_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-launch-aux-metadata-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_AUX_METADATA_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-dispatch-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-dispatch-descriptor-ptr-stub-output-json",
        type=Path,
        default=(
            DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_DESCRIPTOR_PTR_STUB_OUTPUT
        ),
    )
    parser.add_argument(
        "--future-kernel-native-consumer-dispatch-packed-weight-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PACKED_WEIGHT_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-dispatch-aux-metadata-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_AUX_METADATA_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-request-ptr-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-request-launch-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-kernel-native-consumer-request-launch-ptr-stub-output-json",
        type=Path,
        default=DEFAULT_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--future-native-dispatch-row-offset",
        type=int,
        default=0,
        help=(
            "Row offset passed to the future-native dispatch ABI stub. "
            "Defaults to the full-table dispatch window."
        ),
    )
    parser.add_argument(
        "--future-native-dispatch-row-limit",
        type=int,
        default=None,
        help=(
            "Exclusive row limit passed to the future-native dispatch ABI stub. "
            "Unset keeps the stub default of row_count."
        ),
    )
    parser.add_argument(
        "--future-native-dispatch-tail-window-size",
        type=int,
        default=None,
        help=(
            "Use a per-input tail dispatch window of this many rows for the "
            "future-native dispatch ABI stub. When set, it overrides the fixed "
            "row offset/limit for every exported typed-consumer input."
        ),
    )
    parser.add_argument(
        "--preflight-output-json",
        type=Path,
        default=DEFAULT_PREFLIGHT_OUTPUT,
    )
    parser.add_argument(
        "--preflight-status-output-json",
        type=Path,
        default=DEFAULT_PREFLIGHT_STATUS_OUTPUT,
    )
    parser.add_argument(
        "--preflight-status-check-output-json",
        type=Path,
        default=DEFAULT_PREFLIGHT_STATUS_CHECK_OUTPUT,
    )
    parser.add_argument(
        "--artifact-check-output-json",
        type=Path,
        default=DEFAULT_ARTIFACT_CHECK_OUTPUT,
    )
    parser.add_argument(
        "--pointer-source-observer-check-json",
        type=Path,
        default=DEFAULT_POINTER_SOURCE_OBSERVER_CHECK,
        help=(
            "Optional prelaunch pointer-source observer check artifact. "
            "When --require-pointer-source-observer-check is set, this must "
            "prove the real vLLM prelaunch expert_ids source is a device tensor."
        ),
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--skip-trace", action="store_true")
    parser.add_argument("--skip-stub", action="store_true")
    parser.add_argument("--skip-per-field-stub", action="store_true")
    parser.add_argument("--skip-envelope-mirror-stub", action="store_true")
    parser.add_argument("--skip-packed-weight-mirror-stub", action="store_true")
    parser.add_argument("--skip-aux-metadata-mirror-stub", action="store_true")
    parser.add_argument("--skip-descriptor-ptr-mirror-stub", action="store_true")
    parser.add_argument("--skip-kernel-side-compatible-stub", action="store_true")
    parser.add_argument("--skip-future-kernel-args-stub", action="store_true")
    parser.add_argument(
        "--skip-future-kernel-args-extra-field-stubs",
        action="store_true",
    )
    parser.add_argument(
        "--skip-future-kernel-args-compatible-path-stub",
        action="store_true",
    )
    parser.add_argument(
        "--skip-future-kernel-native-consumer-stub",
        action="store_true",
    )
    parser.add_argument(
        "--skip-future-kernel-native-consumer-extra-field-stubs",
        action="store_true",
    )
    parser.add_argument(
        "--skip-future-kernel-native-consumer-request-ptr-stub",
        action="store_true",
    )
    parser.add_argument(
        "--skip-future-kernel-native-consumer-request-launch-stub",
        action="store_true",
    )
    parser.add_argument(
        "--skip-future-kernel-native-consumer-request-launch-ptr-stub",
        action="store_true",
    )
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--skip-artifact-check", action="store_true")
    parser.add_argument(
        "--require-pointer-source-observer-check",
        action="store_true",
        help=(
            "Require the pointer-source observer artifact to pass before the "
            "native/typed consumer canary report can pass. This remains a "
            "no-op evidence gate and does not pass WNA16 kernel args."
        ),
    )
    parser.add_argument(
        "--finalize-existing",
        action="store_true",
        help=(
            "Load --output-json and rerun only the bootstrap/final artifact "
            "and preflight finalization steps. This is for closing the "
            "self-referential lab gate after the native stub evidence already "
            "exists; it does not rerun the vLLM trace or native stubs."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--stdout-mode",
        choices=("full", "summary", "none"),
        default="full",
        help=(
            "Control stdout verbosity. Use summary/none for larger multi-input "
            "stub sweeps; output JSON artifacts are always written."
        ),
    )
    return parser


def _stdout_summary(payload: dict[str, Any], *, output_json: Path) -> dict[str, Any]:
    artifact = payload.get("artifact_check_summary")
    artifact_summary = artifact if isinstance(artifact, dict) else {}
    preflight = payload.get("final_preflight_status_summary")
    preflight_summary = preflight if isinstance(preflight, dict) else {}
    return {
        "passed": payload.get("passed"),
        "failures": payload.get("failures", []),
        "output_json": str(output_json),
        "artifact_check_output_json": payload.get("artifact_check_output_json"),
        "artifact_check_passed": artifact_summary.get("passed"),
        "min_online_inputs": artifact_summary.get("min_online_inputs"),
        "online_prelaunch_input_check_count": artifact_summary.get(
            "runner_online_prelaunch_input_check_count"
        ),
        "online_prelaunch_input_extra_check_count": artifact_summary.get(
            "runner_online_prelaunch_input_extra_check_count"
        ),
        "online_prelaunch_input_extra_check_passed_count": artifact_summary.get(
            "runner_online_prelaunch_input_extra_check_passed_count"
        ),
        "final_preflight_passed": preflight_summary.get("passed"),
        "final_deferred_count": artifact_summary.get("final_deferred_count"),
        "status_deferred_count": artifact_summary.get("status_deferred_count"),
        "pointer_source_observer_check_required": payload.get(
            "pointer_source_observer_check_required"
        ),
        "pointer_source_observer_check_passed": payload.get(
            "pointer_source_observer_check_passed"
        ),
        "pointer_source_observer_gate_passed": payload.get(
            "pointer_source_observer_gate_passed"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = _resolve_repo_path(args.output_json)
    if args.finalize_existing:
        payload = _load_json_if_exists(output)
        if not payload:
            payload = {
                "passed": False,
                "failures": ["existing_runner_artifact_missing"],
            }
    else:
        payload = run_canary(args)
    write_report(output, payload)
    payload = finalize_report_with_artifact_check(
        args=args,
        payload=payload,
        runner_json=output,
        allow_bootstrap_preflight=True,
    )
    write_report(output, payload)
    payload = finalize_report_with_strict_preflight(
        args=args,
        payload=payload,
        allow_runner_self_finalization=True,
        step_prefix="self_finalization",
    )
    self_final_status = payload.get("final_preflight_status_summary")
    self_final_check = payload.get("final_preflight_status_check_summary")
    if (
        isinstance(self_final_status, dict)
        and self_final_status.get("passed") is True
        and isinstance(self_final_check, dict)
        and self_final_check.get("passed") is True
    ):
        payload["failures"] = []
        payload["passed"] = True
    write_report(output, payload)
    payload = finalize_report_with_artifact_check(
        args=args,
        payload=payload,
        runner_json=output,
        allow_bootstrap_preflight=False,
    )
    write_report(output, payload)
    payload = finalize_report_with_strict_preflight(
        args=args,
        payload=payload,
        allow_runner_self_finalization=False,
        step_prefix="final",
    )
    payload = _apply_pointer_source_observer_gate(payload, args)
    write_report(output, payload)
    if args.stdout_mode == "full":
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.stdout_mode == "summary":
        print(json.dumps(_stdout_summary(payload, output_json=output), sort_keys=True))
    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
