#!/usr/bin/env python3
"""Inspect HIP device ISA as a fallback when rocprof counters are not trusted."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "reports" / "rocwmma_smoke" / "static_isa_inspection"
DEFAULT_OBJCOPY = "llvm-objcopy"
DEFAULT_BUNDLER = "clang-offload-bundler"
DEFAULT_OBJDUMP = "llvm-objdump"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--target", default="gfx1100")
    parser.add_argument("--kernel-regex", action="append", default=None)
    parser.add_argument("--llvm-objcopy", default=DEFAULT_OBJCOPY)
    parser.add_argument("--clang-offload-bundler", default=DEFAULT_BUNDLER)
    parser.add_argument("--llvm-objdump", default=DEFAULT_OBJDUMP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def sanitize_name(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path.name)


def extract_device_object(args: argparse.Namespace) -> tuple[Path, list[str], list[dict[str, Any]]]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = sanitize_name(args.binary)
    fatbin = args.output_dir / f"{stem}.hip_fatbin"
    device_obj = args.output_dir / f"{stem}.{args.target}.o"
    commands: list[dict[str, Any]] = []

    cmd = [args.llvm_objcopy, f"--dump-section=.hip_fatbin={fatbin}", str(args.binary)]
    completed = run(cmd)
    commands.append({"cmd": cmd, "returncode": completed.returncode, "stderr": completed.stderr})

    list_cmd = [args.clang_offload_bundler, "--list", "--type=o", f"--input={fatbin}"]
    listed = run(list_cmd)
    commands.append({"cmd": list_cmd, "returncode": listed.returncode, "stderr": listed.stderr})
    bundle_ids = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
    target_ids = [bundle for bundle in bundle_ids if args.target in bundle]
    if not target_ids:
        raise RuntimeError(f"no bundle id contains target {args.target!r}; found {bundle_ids}")
    target_id = target_ids[0]

    unbundle_cmd = [
        args.clang_offload_bundler,
        "--unbundle",
        "--type=o",
        f"--targets={target_id}",
        f"--input={fatbin}",
        f"--output={device_obj}",
    ]
    unbundled = run(unbundle_cmd)
    commands.append({"cmd": unbundle_cmd, "returncode": unbundled.returncode, "stderr": unbundled.stderr})
    return device_obj, bundle_ids, commands


def instruction_bucket(mnemonic: str) -> str | None:
    if mnemonic.startswith("global_load") or mnemonic.startswith("buffer_load") or mnemonic.startswith("flat_load"):
        return "global_load"
    if mnemonic.startswith("global_store") or mnemonic.startswith("buffer_store") or mnemonic.startswith("flat_store"):
        return "global_store"
    if mnemonic.startswith("global_atomic") or mnemonic.startswith("buffer_atomic") or mnemonic.startswith("flat_atomic"):
        return "global_atomic"
    if mnemonic.startswith("ds_load"):
        return "lds_load"
    if mnemonic.startswith("ds_store"):
        return "lds_store"
    if mnemonic.startswith("ds_"):
        return "lds_other"
    if mnemonic.startswith("s_load"):
        return "scalar_load"
    if mnemonic.startswith("s_waitcnt"):
        return "waitcnt"
    if mnemonic == "s_barrier":
        return "barrier"
    if "wmma" in mnemonic or "wmmac" in mnemonic or "mma" in mnemonic:
        return "wmma_or_matrix"
    if mnemonic.startswith(("v_fma", "v_fmac", "v_mad", "v_dot")):
        return "valu_fma"
    return None


def parse_objdump(text: str, kernel_patterns: list[str] | None) -> dict[str, Any]:
    compiled = [re.compile(pattern) for pattern in kernel_patterns or []]
    kernels: dict[str, dict[str, Any]] = {}
    current: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = re.match(r"^[0-9a-fA-F]+ <(.+)>:$", line)
        if match:
            current = match.group(1)
            kernels.setdefault(
                current,
                {
                    "symbol": current,
                    "selected": not compiled or any(pattern.search(current) for pattern in compiled),
                    "instruction_count": 0,
                    "mnemonic_counts": Counter(),
                    "bucket_counts": Counter(),
                },
            )
            continue
        if current is None:
            continue
        stripped = line.strip()
        if not stripped or stripped == "...":
            continue
        # llvm-objdump lines look like:
        #   global_load_b32 v3, v[5:6], off // ...
        mnemonic = stripped.split(None, 1)[0]
        if mnemonic.endswith(":") or mnemonic.startswith("//"):
            continue
        entry = kernels[current]
        entry["instruction_count"] += 1
        entry["mnemonic_counts"][mnemonic] += 1
        bucket = instruction_bucket(mnemonic)
        if bucket is not None:
            entry["bucket_counts"][bucket] += 1

    selected = {name: item for name, item in kernels.items() if item["selected"]}
    aggregate = {
        "kernel_count": len(selected),
        "instruction_count": sum(item["instruction_count"] for item in selected.values()),
        "bucket_counts": Counter(),
    }
    for item in selected.values():
        aggregate["bucket_counts"].update(item["bucket_counts"])

    def derived(bucket_counts: Counter[str]) -> dict[str, Any]:
        matrix = float(bucket_counts.get("wmma_or_matrix", 0))
        lds_total = float(bucket_counts.get("lds_load", 0) + bucket_counts.get("lds_store", 0))
        if matrix <= 0.0:
            return {
                "global_load_to_wmma_ratio": None,
                "lds_load_store_to_wmma_ratio": None,
            }
        return {
            "global_load_to_wmma_ratio": float(bucket_counts.get("global_load", 0)) / matrix,
            "lds_load_store_to_wmma_ratio": lds_total / matrix,
        }

    def normalize(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": item["symbol"],
            "selected": item["selected"],
            "instruction_count": item["instruction_count"],
            "bucket_counts": dict(sorted(item["bucket_counts"].items())),
            "derived": derived(item["bucket_counts"]),
            "top_mnemonics": dict(item["mnemonic_counts"].most_common(24)),
        }

    return {
        "aggregate_selected": {
            "kernel_count": aggregate["kernel_count"],
            "instruction_count": aggregate["instruction_count"],
            "bucket_counts": dict(sorted(aggregate["bucket_counts"].items())),
            "derived": derived(aggregate["bucket_counts"]),
        },
        "kernels": {name: normalize(item) for name, item in sorted(kernels.items())},
    }


def write_markdown(report: dict[str, Any]) -> str:
    agg = report["inspection"]["aggregate_selected"]
    lines = [
        "# HIP ISA Static Inspection",
        "",
        "This is a fallback diagnostic for cases where rocprof counter values are",
        "marked non-informative. It counts instruction mnemonics in the gfx target",
        "device object and should be used as supporting evidence, not as a hardware",
        "traffic counter.",
        "",
        "## Summary",
        "",
        f"- Binary: `{report['config']['binary']}`",
        f"- Target: `{report['config']['target']}`",
        f"- Bundle ids: `{', '.join(report['bundle_ids'])}`",
        f"- Selected kernels: `{agg['kernel_count']}`",
        f"- Selected instructions: `{agg['instruction_count']}`",
        "",
        "## Selected Bucket Counts",
        "",
        "| bucket | count |",
        "|---|---:|",
    ]
    for bucket, count in agg["bucket_counts"].items():
        lines.append(f"| {bucket} | {count} |")
    lines.extend(
        [
            "",
            "## Per Kernel",
            "",
            "| selected | symbol | instructions | global/WMMA | LDS load+store/WMMA | buckets |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for kernel in report["inspection"]["kernels"].values():
        buckets = ", ".join(f"{key}={value}" for key, value in kernel["bucket_counts"].items()) or "none"
        global_ratio = _fmt_optional(kernel["derived"]["global_load_to_wmma_ratio"])
        lds_ratio = _fmt_optional(kernel["derived"]["lds_load_store_to_wmma_ratio"])
        lines.append(
            "| {selected} | `{symbol}` | {inst} | {global_ratio} | {lds_ratio} | {buckets} |".format(
                selected=kernel["selected"],
                symbol=kernel["symbol"],
                inst=kernel["instruction_count"],
                global_ratio=global_ratio,
                lds_ratio=lds_ratio,
                buckets=buckets,
            )
        )
    lines.append("")
    return "\n".join(lines)


def _fmt_optional(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def main() -> None:
    args = parse_args()
    device_obj, bundle_ids, commands = extract_device_object(args)
    objdump_cmd = [args.llvm_objdump, "-d", str(device_obj)]
    objdumped = run(objdump_cmd)
    commands.append({"cmd": objdump_cmd, "returncode": objdumped.returncode, "stderr": objdumped.stderr})

    report = {
        "ok": True,
        "config": {
            "binary": str(args.binary),
            "target": args.target,
            "kernel_regex": args.kernel_regex or [],
            "output_dir": str(args.output_dir),
        },
        "bundle_ids": bundle_ids,
        "device_object": str(device_obj),
        "commands": commands,
        "inspection": parse_objdump(objdumped.stdout, args.kernel_regex),
    }
    json_path = args.output_dir / f"{sanitize_name(args.binary)}.{args.target}.isa_static.json"
    md_path = args.output_dir / f"{sanitize_name(args.binary)}.{args.target}.isa_static.md"
    raw_path = args.output_dir / f"{sanitize_name(args.binary)}.{args.target}.objdump.txt"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(write_markdown(report), encoding="utf-8")
    raw_path.write_text(objdumped.stdout, encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {raw_path}")


if __name__ == "__main__":
    main()
