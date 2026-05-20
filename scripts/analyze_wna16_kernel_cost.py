#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path
from typing import Any


INSTRUCTION_PATTERNS: dict[str, str] = {
    "global_load": r"\b(global|flat|buffer)_load",
    "global_store": r"\b(global|flat|buffer)_store",
    "ds_load": r"\bds_.*load",
    "ds_store": r"\bds_.*store",
    "s_load": r"\bs_load",
    "branch": r"\b(s_cbranch|s_branch|s_setpc|s_swappc)",
    "s_cmp": r"\bs_cmp|\bs_bitcmp",
    "v_cmp": r"\bv_cmp",
    "waitcnt": r"\bs_waitcnt",
    "barrier": r"\bs_barrier",
    "wmma_mfma": r"\b(v_wmma|v_mfma)",
    "vector_alu": r"^\s*v_",
    "scalar_alu": r"^\s*s_",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _kernel_region(source: str, kernel_name: str) -> str:
    marker = f"tt.func public @{kernel_name}"
    start = source.find(marker)
    if start < 0:
        return source
    next_func = source.find("\n  tt.func", start + len(marker))
    if next_func < 0:
        return source[start:]
    return source[start:next_func]


def _parse_shape(source: str, kernel_name: str) -> dict[str, int | None]:
    source = _kernel_region(source, kernel_name)
    block_m = None
    n_const = None
    block_n = None
    m = re.search(r"cdiv__i32__\(1,\)cconstexpr_(\d+)_", source)
    n = re.search(r"cdiv____\(0,\)cconstexpr_(\d+)__\(1,\)cconstexpr_(\d+)_", source)
    if m:
        block_m = int(m.group(1))
    if n:
        n_const = int(n.group(1))
        block_n = int(n.group(2))
    return {"block_m": block_m, "n_const": n_const, "block_n": block_n}


def _candidate(
    cache_root: Path,
    kernel_name: str,
    shape: tuple[int, int, int],
    *,
    shared: int | None,
    num_warps: int | None,
    num_stages: int | None,
    target_backend: str,
    target_arch: str,
) -> Path:
    candidates: list[tuple[float, Path]] = []
    for source_path in cache_root.glob(f"*/{kernel_name}.source"):
        parsed = _parse_shape(source_path.read_text(errors="ignore"), kernel_name)
        if (
            parsed.get("block_m"),
            parsed.get("n_const"),
            parsed.get("block_n"),
            ) == shape:
            meta = _load_json(source_path.with_suffix(".json"))
            target = meta.get("target") or {}
            if (
                target.get("backend") != target_backend
                or target.get("arch") != target_arch
            ):
                continue
            if shared is not None and meta.get("shared") != shared:
                continue
            if num_warps is not None and meta.get("num_warps") != num_warps:
                continue
            if num_stages is not None and meta.get("num_stages") != num_stages:
                continue
            candidates.append((source_path.stat().st_mtime, source_path.parent))
    if not candidates:
        raise FileNotFoundError(f"no Triton cache entry for {kernel_name} shape={shape}")
    return sorted(candidates, reverse=True)[0][1]


def _instruction_lines(amdgcn: str) -> list[str]:
    out: list[str] = []
    for line in amdgcn.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith(".")
            or stripped.endswith(":")
            or stripped.startswith("//")
            or stripped.startswith(";")
            or stripped.startswith("---")
            or stripped.startswith("amdhsa")
        ):
            continue
        if re.match(r"^[a-z][a-z0-9_]+", stripped):
            out.append(stripped)
    return out


def _extract_metadata(amdgcn: str) -> dict[str, int]:
    keys = {
        ".amdhsa_next_free_vgpr": "vgpr",
        ".amdhsa_next_free_sgpr": "sgpr",
        ".amdhsa_kernarg_size": "kernarg_size",
        ".amdhsa_group_segment_fixed_size": "group_segment_fixed_size",
        ".amdhsa_private_segment_fixed_size": "private_segment_fixed_size",
    }
    result: dict[str, int] = {}
    for line in amdgcn.splitlines():
        for needle, name in keys.items():
            if needle in line:
                try:
                    result[name] = int(line.strip().split()[-1], 0)
                except Exception:
                    pass
    return result


def analyze_kernel(cache_dir: Path, kernel_name: str) -> dict[str, Any]:
    json_path = cache_dir / f"{kernel_name}.json"
    source_path = cache_dir / f"{kernel_name}.source"
    amdgcn_path = cache_dir / f"{kernel_name}.amdgcn"
    hsaco_path = cache_dir / f"{kernel_name}.hsaco"
    llir_path = cache_dir / f"{kernel_name}.llir"
    ttgir_path = cache_dir / f"{kernel_name}.ttgir"
    source = source_path.read_text(errors="ignore")
    amdgcn = amdgcn_path.read_text(errors="ignore")
    instructions = _instruction_lines(amdgcn)
    counts = {
        name: sum(1 for inst in instructions if re.search(pattern, inst))
        for name, pattern in INSTRUCTION_PATTERNS.items()
    }
    metadata = _extract_metadata(amdgcn)
    triton_meta = _load_json(json_path)
    return {
        "kernel_name": kernel_name,
        "cache_dir": str(cache_dir),
        "shape": _parse_shape(source, kernel_name),
        "triton": {
            "shared": triton_meta.get("shared"),
            "num_warps": triton_meta.get("num_warps"),
            "num_stages": triton_meta.get("num_stages"),
            "target": triton_meta.get("target"),
        },
        "metadata": metadata,
        "line_count": len(amdgcn.splitlines()),
        "instruction_like_count": len(instructions),
        "instruction_counts": counts,
        "file_sizes": {
            "source": source_path.stat().st_size if source_path.exists() else None,
            "amdgcn": amdgcn_path.stat().st_size if amdgcn_path.exists() else None,
            "hsaco": hsaco_path.stat().st_size if hsaco_path.exists() else None,
            "llir": llir_path.stat().st_size if llir_path.exists() else None,
            "ttgir": ttgir_path.stat().st_size if ttgir_path.exists() else None,
        },
    }


def _quantiles(values: list[float]) -> dict[str, float]:
    values = sorted(values)
    if not values:
        return {}
    def q(p: float) -> float:
        return values[min(len(values) - 1, int(round((len(values) - 1) * p)))]
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "p50": q(0.50),
        "p95": q(0.95),
        "p99": q(0.99),
        "max": values[-1],
    }


def analyze_runtime_shadow(path: Path) -> dict[str, Any]:
    timings: list[float] = []
    plan_build: list[float] = []
    wna16_by_bucket: dict[str, list[float]] = {}
    wna16_gpu_by_bucket: dict[str, list[float]] = {}
    wna16_override_by_bucket: dict[str, list[float]] = {}
    wna16_override_gpu_by_bucket: dict[str, list[float]] = {}
    wna16_counts: dict[str, int] = {}
    wna16_status: dict[str, int] = {}
    fallback: dict[str, int] = {}
    selected: dict[str, int] = {}
    with path.open() as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("event_type") == "wna16_kernel_timing":
                bucket = str(row.get("wna16_bucket") or "unknown")
                elapsed = row.get("wna16_kernel_elapsed_us")
                if elapsed is not None:
                    wna16_by_bucket.setdefault(bucket, []).append(float(elapsed))
                    if row.get("wna16_config_override_applied"):
                        wna16_override_by_bucket.setdefault(bucket, []).append(
                            float(elapsed)
                        )
                gpu_elapsed = row.get("wna16_kernel_gpu_elapsed_us")
                if gpu_elapsed is not None:
                    wna16_gpu_by_bucket.setdefault(bucket, []).append(float(gpu_elapsed))
                    if row.get("wna16_config_override_applied"):
                        wna16_override_gpu_by_bucket.setdefault(bucket, []).append(
                            float(gpu_elapsed)
                        )
                key = f"{bucket}:topk={row.get('wna16_top_k')}:M={row.get('wna16_num_tokens')}"
                wna16_counts[key] = wna16_counts.get(key, 0) + 1
                status_key = str(row.get("wna16_status") or "unknown")
                wna16_status[status_key] = wna16_status.get(status_key, 0) + 1
                continue
            if (
                row.get("event_type") != "descriptor_layer_timing"
                or row.get("descriptor_order_layer_phase") != "decode"
            ):
                continue
            if "descriptor_order_layer_apply_us" in row:
                timings.append(float(row["descriptor_order_layer_apply_us"]))
            if row.get("descriptor_order_consumer_handle_plan_build_us") is not None:
                plan_build.append(float(row["descriptor_order_consumer_handle_plan_build_us"]))
            key = str(row.get("descriptor_order_reorder_mvp_fallback_reason"))
            fallback[key] = fallback.get(key, 0) + 1
            key = str(row.get("descriptor_order_reorder_mvp_selected_policy"))
            selected[key] = selected.get(key, 0) + 1
    return {
        "decode_layer_apply_us": _quantiles(timings),
        "plan_build_us": _quantiles(plan_build),
        "wna16_kernel_us_by_bucket": {
            bucket: _quantiles(values)
            for bucket, values in sorted(wna16_by_bucket.items())
        },
        "wna16_override_kernel_us_by_bucket": {
            bucket: _quantiles(values)
            for bucket, values in sorted(wna16_override_by_bucket.items())
        },
        "wna16_kernel_gpu_us_by_bucket": {
            bucket: _quantiles(values)
            for bucket, values in sorted(wna16_gpu_by_bucket.items())
        },
        "wna16_override_kernel_gpu_us_by_bucket": {
            bucket: _quantiles(values)
            for bucket, values in sorted(wna16_override_gpu_by_bucket.items())
        },
        "wna16_kernel_counts": wna16_counts,
        "wna16_kernel_status_counts": wna16_status,
        "selected_policy_counts": selected,
        "fallback_reason_counts": fallback,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-root", type=Path, default=Path.home() / ".triton/cache")
    parser.add_argument("--shape", default="64,1024,64", help="BLOCK_M,N,BLOCK_N")
    parser.add_argument("--shared", type=int)
    parser.add_argument("--num-warps", type=int, default=4)
    parser.add_argument("--num-stages", type=int, default=2)
    parser.add_argument("--target-backend", default="hip")
    parser.add_argument("--target-arch", default="gfx1100")
    parser.add_argument("--base-kernel-name", default="fused_moe_kernel_gptq_awq")
    parser.add_argument(
        "--candidate-kernel-name",
        default="fused_moe_kernel_gptq_awq_indirect",
    )
    parser.add_argument("--base-cache-dir", type=Path)
    parser.add_argument("--candidate-cache-dir", type=Path)
    parser.add_argument(
        "--indirect-cache-dir",
        type=Path,
        help="Deprecated alias for --candidate-cache-dir.",
    )
    parser.add_argument("--runtime-shadow", type=Path)
    parser.add_argument(
        "--runtime-only",
        action="store_true",
        help="Only analyze runtime_shadow timing rows; skip Triton cache analysis.",
    )
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    shape = tuple(int(x) for x in args.shape.split(","))
    if len(shape) != 3:
        raise ValueError("--shape must be BLOCK_M,N,BLOCK_N")

    result: dict[str, Any] = {
        "shape": {"block_m": shape[0], "n_const": shape[1], "block_n": shape[2]},
    }
    if not args.runtime_only:
        base_dir = args.base_cache_dir or _candidate(
            args.cache_root,
            args.base_kernel_name,
            shape,
            shared=args.shared,
            num_warps=args.num_warps,
            num_stages=args.num_stages,
            target_backend=args.target_backend,
            target_arch=args.target_arch,
        )
        candidate_cache_dir = args.candidate_cache_dir or args.indirect_cache_dir
        candidate_dir = candidate_cache_dir or _candidate(
            args.cache_root,
            args.candidate_kernel_name,
            shape,
            shared=args.shared,
            num_warps=args.num_warps,
            num_stages=args.num_stages,
            target_backend=args.target_backend,
            target_arch=args.target_arch,
        )
        result.update(
            {
                "base": analyze_kernel(base_dir, args.base_kernel_name),
                "candidate": analyze_kernel(candidate_dir, args.candidate_kernel_name),
            }
        )
        # Backward-compatible aliases for existing notebooks/scripts that still
        # compare "indirect" against "base".
        result["indirect"] = result["candidate"]
        deltas: dict[str, Any] = {}
        for section in ["metadata", "file_sizes", "instruction_counts"]:
            deltas[section] = {}
            for key, val in result["candidate"][section].items():
                base_val = result["base"][section].get(key)
                if isinstance(val, (int, float)) and isinstance(base_val, (int, float)):
                    deltas[section][key] = val - base_val
        deltas["line_count"] = (
            result["candidate"]["line_count"] - result["base"]["line_count"]
        )
        deltas["instruction_like_count"] = (
            result["candidate"]["instruction_like_count"]
            - result["base"]["instruction_like_count"]
        )
        result["delta_candidate_minus_base"] = deltas
        result["delta_indirect_minus_base"] = deltas
    if args.runtime_shadow is not None:
        result["runtime_shadow"] = analyze_runtime_shadow(args.runtime_shadow)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
