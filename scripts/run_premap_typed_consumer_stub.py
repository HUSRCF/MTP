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
from typing import Any

from mtp_expert_prefetch.runtime.cache_manager import (
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "microbench" / "premap_kernel_consumer" / "premap_typed_consumer_stub.hip"
BUILD_DIR = REPO_ROOT / "microbench" / "premap_kernel_consumer" / "build"
ALLOWED_MACROS = {
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
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
    if result.returncode != 0:
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
    if bin_path.exists() and not force and bin_path.stat().st_mtime >= SRC.stat().st_mtime:
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
    cmd = [
        str(bin_path),
        "--device",
        str(args.device),
        "--rows",
        str(rows),
        "--block-threads",
        str(args.block_threads),
    ]
    if input_prefix is not None:
        cmd.extend(["--input-prefix", str(input_prefix)])
    if args.omit_aux_pointer:
        cmd.append("--omit-aux-pointer")
    env = os.environ.copy()
    if args.hip_visible_devices is not None:
        env["HIP_VISIBLE_DEVICES"] = str(args.hip_visible_devices)
    result = run_cmd(cmd, env=env)
    payload = json.loads(result.stdout)
    payload["binary"] = str(bin_path)
    payload["source"] = str(SRC)
    payload["requested_macros"] = macros
    payload["expected_schema_hash"] = schema_hash
    if input_prefix is not None:
        payload["input_json"] = str(args.input_json)
        payload["input_prefix"] = str(input_prefix)
    if result.stderr:
        payload["stderr"] = result.stderr
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--rows", type=int, default=1024)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--input-json", type=Path)
    parser.add_argument("--macro", action="append", default=[])
    parser.add_argument("--omit-aux-pointer", action="store_true")
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
    if args.dry_run:
        schema_hash = PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
        key = _macro_key(macros, args.offload_arch, schema_hash)
        bin_path = BUILD_DIR / f"premap_typed_consumer_stub_{key}"
        payload: dict[str, Any] = {
            "ok": True,
            "dry_run": True,
            "source": str(SRC),
            "binary": str(bin_path),
            "requested_macros": macros,
            "build_command": build_command(
                macros=macros,
                offload_arch=args.offload_arch,
                output=bin_path,
                schema_hash=schema_hash,
            ),
            "expected_schema_hash": schema_hash,
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
