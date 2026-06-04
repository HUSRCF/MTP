#!/usr/bin/env python3
"""Build and run the readonly premap typed native consumer stub."""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for _path in (REPO_ROOT, SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mtp_expert_prefetch.runtime.cache_manager import (  # noqa: E402
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
)


SRC = REPO_ROOT / "microbench" / "premap_kernel_consumer" / "premap_typed_consumer_stub.hip"
ABI_HEADER = (
    REPO_ROOT
    / "microbench"
    / "premap_kernel_consumer"
    / "premap_typed_consumer_abi_v1.h"
)
ADAPTER_HEADER = (
    REPO_ROOT
    / "microbench"
    / "premap_kernel_consumer"
    / "premap_typed_consumer_adapter_v1.h"
)
BUILD_DIR = REPO_ROOT / "microbench" / "premap_kernel_consumer" / "build"
ALLOWED_MACROS = {
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI",
}
FORBIDDEN_MACROS = {
    "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF",
    "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS",
}


def _schema_hash_words(schema_hash: str = PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH) -> tuple[str, str]:
    if len(schema_hash) != 64:
        raise ValueError(f"typed consumer schema hash must be 64 hex chars: {schema_hash}")
    int(schema_hash, 16)
    return schema_hash[:16], schema_hash[-16:]


def _macro_key(macros: list[str], offload_arch: str, schema_hash: str) -> str:
    payload = "|".join([offload_arch, schema_hash, *sorted(macros)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def validate_macros(macros: list[str]) -> list[str]:
    normalized = sorted({item.strip() for item in macros if item.strip()})
    forbidden = sorted(set(normalized) & FORBIDDEN_MACROS)
    if forbidden:
        raise ValueError(f"forbidden typed consumer macros: {forbidden}")
    unknown = sorted(set(normalized) - ALLOWED_MACROS)
    if unknown:
        raise ValueError(f"unsupported typed consumer macros: {unknown}")
    mirror_fields = {
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
    }
    enabled_mirror_fields = sorted(set(normalized) & mirror_fields)
    if len(enabled_mirror_fields) > 1:
        raise ValueError(
            "enable only one typed consumer single-field mirror macro: "
            f"{enabled_mirror_fields}"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer launch ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer dispatch ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer dispatch pointer ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer arg-slot ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer view ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer program-view ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer program-view pointer ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer kernel-arg packet ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer kernel entry-args ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer kernel entry-args pointer ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer launch-envelope args ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer launch-envelope args pointer ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer kernel launch descriptor ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer kernel launch context ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer invocation ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer invocation entry ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer endpoint ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer endpoint pointer ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI"
        )
    if (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI"
        in normalized
        and "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI"
        not in normalized
    ):
        raise ValueError(
            "future native consumer request pointer ABI requires "
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI"
        )
    return normalized


def build_command(
    *,
    macros: list[str],
    offload_arch: str,
    output: Path,
    schema_hash: str = PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
) -> list[str]:
    hash_hi, hash_lo = _schema_hash_words(schema_hash)
    compile_macros = [
        "-DMTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1=1",
        f"-DMTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI=0x{hash_hi}ULL",
        f"-DMTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO=0x{hash_lo}ULL",
        *[f"-D{macro}=1" for macro in validate_macros(macros)],
    ]
    return [
        "hipcc",
        "-O3",
        "--std=c++17",
        f"--offload-arch={offload_arch}",
        *compile_macros,
        str(SRC),
        "-o",
        str(output),
    ]


def run_cmd(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 and not allow_failure:
        msg = (
            "command failed with exit code "
            f"{result.returncode}: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        raise RuntimeError(msg)
    return result


def build(
    *,
    macros: list[str],
    offload_arch: str,
    force: bool,
    schema_hash: str = PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
) -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    checked = validate_macros(macros)
    bin_path = BUILD_DIR / f"premap_typed_consumer_stub_{_macro_key(checked, offload_arch, schema_hash)}"
    latest_source_mtime = max(
        SRC.stat().st_mtime,
        ABI_HEADER.stat().st_mtime,
        ADAPTER_HEADER.stat().st_mtime,
    )
    if bin_path.exists() and not force and bin_path.stat().st_mtime >= latest_source_mtime:
        return bin_path
    result = run_cmd(
        build_command(
            macros=checked,
            offload_arch=offload_arch,
            output=bin_path,
            schema_hash=schema_hash,
        )
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    return bin_path


def _write_array(path: Path, typecode: str, values: list[int]) -> None:
    data = array(typecode, [int(value) for value in values])
    with path.open("wb") as handle:
        data.tofile(handle)


def _input_prefix_from_json(path: Path) -> tuple[Path, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"typed consumer input JSON must be an object: {path}")
    required = [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "expert_id",
        "address_key_hash",
    ]
    arrays: dict[str, list[int]] = {}
    for key in required:
        value = payload.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(f"typed consumer input field must be a non-empty list: {key}")
        arrays[key] = [int(item) for item in value]
    row_count = len(arrays["descriptor_ptr"])
    aux_value = payload.get("aux_metadata_handle")
    if aux_value is None:
        arrays["aux_metadata_handle"] = [0] * row_count
    elif isinstance(aux_value, list):
        arrays["aux_metadata_handle"] = [int(item) for item in aux_value]
    else:
        raise ValueError(
            "typed consumer input field must be a list when present: aux_metadata_handle"
        )
    mismatched = [key for key, values in arrays.items() if len(values) != row_count]
    if mismatched:
        raise ValueError(f"typed consumer input field length mismatch: {mismatched}")
    digest = hashlib.sha256(
        json.dumps(arrays, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    prefix = BUILD_DIR / f"typed_consumer_input_{digest}"
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    _write_array(prefix.with_suffix(".descriptor_ptr.u64"), "Q", arrays["descriptor_ptr"])
    _write_array(
        prefix.with_suffix(".packed_weight_descriptor.u64"),
        "Q",
        arrays["packed_weight_descriptor"],
    )
    _write_array(prefix.with_suffix(".scale_metadata_handle.u64"), "Q", arrays["scale_metadata_handle"])
    _write_array(prefix.with_suffix(".aux_metadata_handle.u64"), "Q", arrays["aux_metadata_handle"])
    _write_array(prefix.with_suffix(".expert_id.i32"), "i", arrays["expert_id"])
    _write_array(prefix.with_suffix(".address_key_hash.u64"), "Q", arrays["address_key_hash"])
    return prefix, row_count


def run_stub(args: argparse.Namespace) -> dict[str, Any]:
    macros = validate_macros(args.macro or [])
    schema_hash = PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
    bin_path = build(
        macros=macros,
        offload_arch=args.offload_arch,
        force=args.force_build,
        schema_hash=schema_hash,
    )
    input_prefix = None
    rows = int(args.rows)
    if args.input_json is not None:
        input_prefix, rows = _input_prefix_from_json(args.input_json)
    dispatch_row_offset = int(args.dispatch_row_offset)
    dispatch_row_limit = (
        int(args.dispatch_row_limit)
        if args.dispatch_row_limit is not None
        else None
    )
    if dispatch_row_offset < 0:
        raise ValueError("dispatch-row-offset must be non-negative")
    if dispatch_row_limit is not None and (
        dispatch_row_limit <= dispatch_row_offset or dispatch_row_limit > rows
    ):
        raise ValueError("dispatch-row-limit must satisfy offset < limit <= rows")
    cmd = [
        str(bin_path),
        "--device",
        str(args.device),
        "--rows",
        str(rows),
        "--block-threads",
        str(args.block_threads),
        "--dispatch-row-offset",
        str(dispatch_row_offset),
    ]
    if dispatch_row_limit is not None:
        cmd.extend(["--dispatch-row-limit", str(dispatch_row_limit)])
    if input_prefix is not None:
        cmd.extend(["--input-prefix", str(input_prefix)])
    if args.omit_aux_pointer:
        cmd.append("--omit-aux-pointer")
    if args.fault_kernel_launch_descriptor_schema_hash:
        cmd.append("--fault-kernel-launch-descriptor-schema-hash")
    if args.fault_invocation_device_ordinal:
        cmd.append("--fault-invocation-device-ordinal")
    if args.fault_invocation_stream_domain:
        cmd.append("--fault-invocation-stream-domain")
    env = os.environ.copy()
    if args.hip_visible_devices is not None:
        env["HIP_VISIBLE_DEVICES"] = str(args.hip_visible_devices)
    fault_failure_allowed = bool(
        args.fault_kernel_launch_descriptor_schema_hash
        or args.fault_invocation_device_ordinal
        or args.fault_invocation_stream_domain
    )
    result = run_cmd(
        cmd,
        env=env,
        allow_failure=fault_failure_allowed,
    )
    try:
        decoded_payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        if not fault_failure_allowed:
            msg = (
                "native typed consumer emitted invalid JSON "
                f"with exit code {result.returncode}: {exc}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
            raise RuntimeError(msg) from exc
        decoded_payload = {
            "ok": False,
            "passed": False,
            "native_json_parse_error": str(exc),
            "native_stdout": result.stdout,
        }
    if not isinstance(decoded_payload, dict):
        msg = "native typed consumer JSON payload must be an object"
        if not fault_failure_allowed:
            raise RuntimeError(msg)
        decoded_payload = {
            "ok": False,
            "passed": False,
            "native_json_parse_error": msg,
            "native_stdout": result.stdout,
        }
    payload = decoded_payload
    payload["native_returncode"] = int(result.returncode)
    payload["fault_kernel_launch_descriptor_schema_hash"] = bool(
        args.fault_kernel_launch_descriptor_schema_hash
    )
    payload["fault_invocation_device_ordinal"] = bool(
        args.fault_invocation_device_ordinal
    )
    payload["fault_invocation_stream_domain"] = bool(
        args.fault_invocation_stream_domain
    )
    payload["binary"] = str(bin_path)
    payload["source"] = str(SRC)
    payload["abi_header"] = str(ABI_HEADER)
    payload["adapter_header"] = str(ADAPTER_HEADER)
    payload["requested_macros"] = macros
    payload["expected_schema_hash"] = schema_hash
    if input_prefix is not None:
        payload["input_json"] = str(args.input_json)
        payload["input_prefix"] = str(input_prefix)
    payload["requested_dispatch_row_offset"] = dispatch_row_offset
    payload["requested_dispatch_row_limit"] = dispatch_row_limit
    if result.stderr:
        payload["stderr"] = result.stderr
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--rows", type=int, default=1024)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--dispatch-row-offset", type=int, default=0)
    parser.add_argument("--dispatch-row-limit", type=int)
    parser.add_argument("--input-json", type=Path)
    parser.add_argument("--macro", action="append", default=[])
    parser.add_argument("--omit-aux-pointer", action="store_true")
    parser.add_argument(
        "--fault-kernel-launch-descriptor-schema-hash",
        action="store_true",
        help=(
            "Inject a schema-hash mismatch into the future native kernel-launch "
            "descriptor canary. This is a negative test hook only."
        ),
    )
    parser.add_argument(
        "--fault-invocation-device-ordinal",
        action="store_true",
        help=(
            "Inject a device-ordinal mismatch between the future native "
            "invocation object and its launch context. This is a negative "
            "test hook only."
        ),
    )
    parser.add_argument(
        "--fault-invocation-stream-domain",
        action="store_true",
        help=(
            "Inject a stream-domain mismatch between the future native "
            "invocation object and its launch context. This is a negative "
            "test hook only."
        ),
    )
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT
        / "outputs"
        / "reports"
        / "premap_kernel_consumer"
        / "typed_consumer_stub.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    macros = validate_macros(args.macro or [])
    dispatch_row_offset = int(args.dispatch_row_offset)
    dispatch_row_limit = (
        int(args.dispatch_row_limit)
        if args.dispatch_row_limit is not None
        else None
    )
    if dispatch_row_offset < 0:
        raise ValueError("dispatch-row-offset must be non-negative")
    if dispatch_row_limit is not None and dispatch_row_limit <= dispatch_row_offset:
        raise ValueError("dispatch-row-limit must be greater than dispatch-row-offset")
    if args.dry_run:
        schema_hash = PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
        key = _macro_key(macros, args.offload_arch, schema_hash)
        bin_path = BUILD_DIR / f"premap_typed_consumer_stub_{key}"
        payload: dict[str, Any] = {
            "ok": True,
            "dry_run": True,
            "source": str(SRC),
            "abi_header": str(ABI_HEADER),
            "adapter_header": str(ADAPTER_HEADER),
            "binary": str(bin_path),
            "requested_macros": macros,
            "build_command": build_command(
                macros=macros,
                offload_arch=args.offload_arch,
                output=bin_path,
                schema_hash=schema_hash,
            ),
            "expected_schema_hash": schema_hash,
            "requested_dispatch_row_offset": dispatch_row_offset,
            "requested_dispatch_row_limit": dispatch_row_limit,
            "fault_kernel_launch_descriptor_schema_hash": bool(
                args.fault_kernel_launch_descriptor_schema_hash
            ),
            "fault_invocation_device_ordinal": bool(
                args.fault_invocation_device_ordinal
            ),
            "fault_invocation_stream_domain": bool(
                args.fault_invocation_stream_domain
            ),
        }
    else:
        payload = run_stub(args)
    payload.setdefault("passed", bool(payload.get("ok", False)))
    payload.setdefault("failures", [] if payload.get("ok", False) else ["stub_not_ok"])
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
