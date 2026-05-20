#!/usr/bin/env python3
"""Run a small WNA16 MoE config sweep through vLLM trace configs.

The default mode uses the project runtime override hook instead of static vLLM
JSON config files.  This only changes M/GROUP/SPLIT/warps/stages and leaves
vLLM's W1/W2-specific BLOCK_SIZE_N/K selection intact.
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


W7900_AWQ_CONFIG_NAME = (
    "E=256,N=512,device_name=AMD_Radeon_PRO_W7900_Dual_Slot_,"
    "dtype=int4_w4a16.json"
)


def _candidate_entries(
    *,
    block_m: int,
    group_m: int,
    split_k: int,
    num_warps: int,
    num_stages: int,
    keys: tuple[int, ...] = (1, 2, 4, 8, 16, 32, 64, 128),
) -> dict[str, Any]:
    data: dict[str, Any] = {"triton_version": "3.6.0"}
    for key in keys:
        data[str(key)] = {
            "BLOCK_SIZE_M": int(block_m),
            "GROUP_SIZE_M": int(group_m),
            "SPLIT_K": int(split_k),
            "num_warps": int(num_warps),
            "num_stages": int(num_stages),
        }
    return data


def _candidate_override(
    *,
    block_m: int,
    group_m: int,
    split_k: int = 1,
    num_warps: int | None = None,
    num_stages: int | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "BLOCK_SIZE_M": int(block_m),
        "GROUP_SIZE_M": int(group_m),
        "SPLIT_K": int(split_k),
    }
    if num_warps is not None:
        data["num_warps"] = int(num_warps)
    if num_stages is not None:
        data["num_stages"] = int(num_stages)
    return data


def _default_runtime_candidates() -> dict[str, dict[str, Any] | None]:
    return {
        "baseline_no_tuned_config": None,
        "bm16_g1_default": _candidate_override(block_m=16, group_m=1),
        "bm16_g1_w1_s2": _candidate_override(
            block_m=16,
            group_m=1,
            split_k=1,
            num_warps=1,
            num_stages=2,
        ),
        "bm16_g1_w1_s3": _candidate_override(
            block_m=16,
            group_m=1,
            split_k=1,
            num_warps=1,
            num_stages=3,
        ),
        "bm16_g1_w2_s2": _candidate_override(
            block_m=16,
            group_m=1,
            split_k=1,
            num_warps=2,
            num_stages=2,
        ),
        "bm16_g1_w2_s3": _candidate_override(
            block_m=16,
            group_m=1,
            split_k=1,
            num_warps=2,
            num_stages=3,
        ),
        "bm16_g1_w4_s2": _candidate_override(
            block_m=16,
            group_m=1,
            split_k=1,
            num_warps=4,
            num_stages=2,
        ),
        "bm16_g1_w4_s3": _candidate_override(
            block_m=16,
            group_m=1,
            split_k=1,
            num_warps=4,
            num_stages=3,
        ),
        "bm32_g1_w2_s2": _candidate_override(
            block_m=32,
            group_m=1,
            split_k=1,
            num_warps=2,
            num_stages=2,
        ),
        "bm32_g4_w2_s2": _candidate_override(
            block_m=32,
            group_m=4,
            split_k=1,
            num_warps=2,
            num_stages=2,
        ),
        "bm64_g1_w4_s2": _candidate_override(
            block_m=64,
            group_m=1,
            split_k=1,
            num_warps=4,
            num_stages=2,
        ),
    }


def _default_static_candidates() -> dict[str, dict[str, Any] | None]:
    return {
        "baseline_no_tuned_config": None,
        "bm16_g1_w1_s2": _candidate_entries(
            block_m=16,
            group_m=1,
            split_k=1,
            num_warps=1,
            num_stages=2,
        ),
        "bm16_g1_w2_s2": _candidate_entries(
            block_m=16,
            group_m=1,
            split_k=1,
            num_warps=2,
            num_stages=2,
        ),
        "bm16_g1_w4_s2": _candidate_entries(
            block_m=16,
            group_m=1,
            split_k=1,
            num_warps=4,
            num_stages=2,
        ),
        "bm32_g1_w2_s2": _candidate_entries(
            block_m=32,
            group_m=1,
            split_k=1,
            num_warps=2,
            num_stages=2,
        ),
        "bm32_g4_w2_s2": _candidate_entries(
            block_m=32,
            group_m=4,
            split_k=1,
            num_warps=2,
            num_stages=2,
        ),
        "bm64_g1_w4_s2": _candidate_entries(
            block_m=64,
            group_m=1,
            split_k=1,
            num_warps=4,
            num_stages=2,
        ),
        "r8060s_full_bn16_k64": {
            "triton_version": "3.6.0",
            "1": {
                "BLOCK_SIZE_M": 16,
                "BLOCK_SIZE_N": 16,
                "BLOCK_SIZE_K": 64,
                "GROUP_SIZE_M": 1,
                "SPLIT_K": 1,
                "num_warps": 2,
                "num_stages": 2,
                "waves_per_eu": 4,
            },
            "2": {
                "BLOCK_SIZE_M": 16,
                "BLOCK_SIZE_N": 16,
                "BLOCK_SIZE_K": 64,
                "GROUP_SIZE_M": 1,
                "SPLIT_K": 1,
                "num_warps": 1,
                "num_stages": 2,
                "waves_per_eu": 4,
            },
            "4": {
                "BLOCK_SIZE_M": 32,
                "BLOCK_SIZE_N": 16,
                "BLOCK_SIZE_K": 64,
                "GROUP_SIZE_M": 1,
                "SPLIT_K": 1,
                "num_warps": 2,
                "num_stages": 2,
                "waves_per_eu": 2,
            },
            "8": {
                "BLOCK_SIZE_M": 32,
                "BLOCK_SIZE_N": 16,
                "BLOCK_SIZE_K": 64,
                "GROUP_SIZE_M": 1,
                "SPLIT_K": 1,
                "num_warps": 2,
                "num_stages": 2,
                "waves_per_eu": 2,
            },
            "16": {
                "BLOCK_SIZE_M": 32,
                "BLOCK_SIZE_N": 16,
                "BLOCK_SIZE_K": 64,
                "GROUP_SIZE_M": 4,
                "SPLIT_K": 1,
                "num_warps": 2,
                "num_stages": 2,
                "waves_per_eu": 0,
            },
            "32": {
                "BLOCK_SIZE_M": 32,
                "BLOCK_SIZE_N": 16,
                "BLOCK_SIZE_K": 64,
                "GROUP_SIZE_M": 4,
                "SPLIT_K": 1,
                "num_warps": 2,
                "num_stages": 2,
                "waves_per_eu": 0,
            },
        },
    }


def _write_candidate_config(root: Path, name: str, data: dict[str, Any]) -> Path:
    folder = root / "tuned_configs" / name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / W7900_AWQ_CONFIG_NAME
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return folder


def _write_trace_config(
    *,
    base_config: Path,
    output_root: Path,
    candidate_name: str,
    max_samples: int | None,
    max_tokens: int | None,
    start_sample: int | None,
    runtime_override: dict[str, Any] | None,
    runtime_override_max_tokens: int | None,
    runtime_override_route_product: int | None,
    runtime_override_target_top_k: int | None,
    emit_kernel_timing: bool,
    kernel_timing_mode: str,
    emit_decoder_layer_timing: bool,
    record_router_topk: bool,
) -> Path:
    cfg = yaml.safe_load(base_config.read_text())
    output_dir = output_root / "traces" / candidate_name
    cfg["output_dir"] = str(output_dir)
    trace = cfg.setdefault("trace", {})
    if max_samples is not None:
        trace["max_samples"] = int(max_samples)
    if max_tokens is not None:
        trace["max_tokens"] = int(max_tokens)
    if start_sample is not None:
        trace["start_sample"] = int(start_sample)
    shadow = trace.setdefault("runtime_shadow", {})
    shadow["output_path"] = str(output_dir / "runtime_shadow.jsonl")
    if emit_kernel_timing:
        shadow["emit_summaries"] = True
        shadow["emit_outcomes"] = False
        shadow["outcome_logging_mode"] = "off"
        shadow["emit_wna16_kernel_timing"] = True
        shadow["wna16_kernel_timing_mode"] = str(kernel_timing_mode)
    else:
        shadow["emit_wna16_kernel_timing"] = False
    if emit_decoder_layer_timing:
        shadow["emit_summaries"] = True
        shadow["emit_decoder_layer_timing"] = True
    shadow["record_router_topk"] = bool(record_router_topk)
    if runtime_override is not None:
        shadow["wna16_config_override"] = dict(runtime_override)
        shadow["wna16_config_override_preserve_dynamic_nk"] = True
        if runtime_override_max_tokens is not None:
            shadow["wna16_config_override_max_tokens"] = int(
                runtime_override_max_tokens
            )
        if runtime_override_route_product is not None:
            shadow["wna16_config_override_route_product"] = int(
                runtime_override_route_product
            )
        if runtime_override_target_top_k is not None:
            shadow["wna16_config_override_target_top_k"] = int(
                runtime_override_target_top_k
            )
    else:
        shadow.pop("wna16_config_override", None)
        shadow.pop("wna16_config_override_preserve_dynamic_nk", None)
        shadow.pop("wna16_config_override_max_tokens", None)
        shadow.pop("wna16_config_override_route_product", None)
        shadow.pop("wna16_config_override_target_top_k", None)
    config_path = output_root / "trace_configs" / f"{candidate_name}.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return config_path


def _read_perf(trace_dir: Path) -> dict[str, Any]:
    path = trace_dir / "performance_summary.json"
    if not path.exists():
        return {"performance_summary_missing": True}
    data = json.loads(path.read_text())
    return {
        "generate_seconds_per_requested_output_token": data.get(
            "generate_seconds_per_requested_output_token"
        ),
        "generate_wall_seconds": data.get("generate_wall_seconds"),
        "total_trace_wall_seconds": data.get("total_trace_wall_seconds"),
        "requested_output_token_count": data.get("requested_output_token_count"),
        "sample_count": data.get("sample_count"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-config",
        type=Path,
        default=Path(
            "configs/trace/"
            "router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_attr_"
            "no_order_gpu1_decode_heldout128_gen8_diagnostic_off.yaml"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/reports/wna16_runtime_override_sweep/awq_w7900_gpu1"),
    )
    parser.add_argument("--max-samples", type=int, default=32)
    parser.add_argument("--max-tokens", type=int, default=8)
    parser.add_argument("--start-sample", type=int, default=128)
    parser.add_argument("--gpu", default="1")
    parser.add_argument("--conda-env", default="TRY")
    parser.add_argument(
        "--override-mode",
        choices=("runtime", "static"),
        default="runtime",
        help=(
            "runtime writes trace runtime_shadow.wna16_config_override and "
            "preserves dynamic N/K; static writes VLLM_TUNED_CONFIG_FOLDER JSON."
        ),
    )
    parser.add_argument(
        "--runtime-override-max-tokens",
        type=int,
        default=8,
        help=(
            "Only apply runtime WNA16 overrides when A.shape[0] is at most this "
            "value. Use 0 to apply to all token counts."
        ),
    )
    parser.add_argument(
        "--runtime-override-route-product",
        type=int,
        default=8,
        help=(
            "Only apply runtime WNA16 overrides when A.shape[0] * top_k equals "
            "this value. Use 0 to disable the route-product guard."
        ),
    )
    parser.add_argument(
        "--runtime-override-target-top-k",
        type=int,
        choices=(1, 8),
        default=None,
        help="Apply runtime override only to a specific WNA16 projection bucket.",
    )
    parser.add_argument(
        "--emit-kernel-timing",
        action="store_true",
        help="Enable runtime shadow summary writes for wna16_kernel_timing rows.",
    )
    parser.add_argument(
        "--kernel-timing-mode",
        choices=("host", "gpu_event"),
        default="host",
        help="Timing mode for wna16_kernel_timing rows.",
    )
    parser.add_argument(
        "--emit-decoder-layer-timing",
        action="store_true",
        help="Emit decoder_layer_timing rows for non-MoE generate attribution.",
    )
    parser.add_argument(
        "--disable-router-topk-recording",
        action="store_true",
        help=(
            "Keep decoder/MoE timing hooks but skip record_topk CPU copies and "
            "shadow outcome/descriptor summaries. This is a diagnostic-only "
            "telemetry-off mode for select_experts attribution."
        ),
    )
    parser.add_argument(
        "--candidates",
        nargs="*",
        default=["baseline_no_tuned_config", "bm16_g1_default", "bm32_g1_w2_s2"],
        help="Candidate names. Use 'all' to run every built-in candidate.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Record failing candidates and continue the sweep.",
    )
    args = parser.parse_args()

    candidates = (
        _default_runtime_candidates()
        if args.override_mode == "runtime"
        else _default_static_candidates()
    )
    selected = list(args.candidates)
    if selected == ["all"]:
        selected = list(candidates)
    unknown = [name for name in selected if name not in candidates]
    if unknown:
        raise SystemExit(f"unknown candidates: {unknown}")

    args.output_root.mkdir(parents=True, exist_ok=True)
    results = []
    for name in selected:
        candidate_data = candidates[name]
        runtime_override = candidate_data if args.override_mode == "runtime" else None
        tuned_data = candidate_data if args.override_mode == "static" else None
        tuned_folder = None
        if tuned_data is not None:
            tuned_folder = _write_candidate_config(args.output_root, name, tuned_data)
        trace_config = _write_trace_config(
            base_config=args.base_config,
            output_root=args.output_root,
            candidate_name=name,
            max_samples=args.max_samples,
            max_tokens=args.max_tokens,
            start_sample=args.start_sample,
            runtime_override=runtime_override,
            runtime_override_max_tokens=(
                args.runtime_override_max_tokens
                if args.override_mode == "runtime"
                and args.runtime_override_max_tokens > 0
                else None
            ),
            runtime_override_route_product=(
                args.runtime_override_route_product
                if args.override_mode == "runtime"
                else None
            ),
            runtime_override_target_top_k=(
                args.runtime_override_target_top_k
                if args.override_mode == "runtime"
                else None
            ),
            emit_kernel_timing=bool(args.emit_kernel_timing),
            kernel_timing_mode=str(args.kernel_timing_mode),
            emit_decoder_layer_timing=bool(args.emit_decoder_layer_timing),
            record_router_topk=not bool(args.disable_router_topk_recording),
        )
        env = os.environ.copy()
        env["HIP_VISIBLE_DEVICES"] = str(args.gpu)
        env["PYTHONPATH"] = "src"
        if tuned_folder is not None:
            env["VLLM_TUNED_CONFIG_FOLDER"] = str(tuned_folder.resolve())
        else:
            env.pop("VLLM_TUNED_CONFIG_FOLDER", None)
        command = [
            "conda",
            "run",
            "-n",
            args.conda_env,
            "python",
            "scripts/trace_router_mtp.py",
            str(trace_config),
        ]
        print(f"[wna16-sweep] running {name}", flush=True)
        proc = subprocess.run(
            command,
            cwd=Path.cwd(),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        log_path = args.output_root / "logs" / f"{name}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(proc.stdout)
        trace_dir = args.output_root / "traces" / name
        row = {
            "candidate": name,
            "override_mode": args.override_mode,
            "runtime_override": runtime_override,
            "runtime_override_max_tokens": (
                args.runtime_override_max_tokens
                if args.override_mode == "runtime"
                and args.runtime_override_max_tokens > 0
                else None
            ),
            "runtime_override_route_product": (
                args.runtime_override_route_product
                if args.override_mode == "runtime"
                else None
            ),
            "runtime_override_target_top_k": (
                args.runtime_override_target_top_k
                if args.override_mode == "runtime"
                else None
            ),
            "returncode": proc.returncode,
            "trace_config": str(trace_config),
            "tuned_config_folder": str(tuned_folder) if tuned_folder else None,
            "log_path": str(log_path),
            **_read_perf(trace_dir),
        }
        results.append(row)
        (args.output_root / "results.json").write_text(
            json.dumps(results, indent=2) + "\n"
        )
        print(json.dumps(row, indent=2), flush=True)
        if proc.returncode != 0 and not args.continue_on_error:
            raise SystemExit(proc.returncode)

    baseline = next(
        (
            row
            for row in results
            if row["candidate"] == "baseline_no_tuned_config"
            and row.get("generate_seconds_per_requested_output_token")
        ),
        None,
    )
    if baseline:
        base_tpot = float(baseline["generate_seconds_per_requested_output_token"])
        for row in results:
            tpot = row.get("generate_seconds_per_requested_output_token")
            if tpot:
                row["speedup_vs_baseline"] = base_tpot / float(tpot)
    (args.output_root / "results.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )
    md_lines = [
        "# WNA16 AWQ W7900 Config Sweep",
        "",
        f"base_config: `{args.base_config}`",
        f"override_mode: `{args.override_mode}`",
        f"max_samples: `{args.max_samples}`",
        f"max_tokens: `{args.max_tokens}`",
        "",
        "| candidate | TPOT | speedup | returncode |",
        "|---|---:|---:|---:|",
    ]
    for row in results:
        tpot = row.get("generate_seconds_per_requested_output_token")
        speedup = row.get("speedup_vs_baseline")
        md_lines.append(
            "| {candidate} | {tpot} | {speedup} | {returncode} |".format(
                candidate=row["candidate"],
                tpot=f"{float(tpot):.6f}" if tpot else "",
                speedup=f"{float(speedup):.4f}x" if speedup else "",
                returncode=row["returncode"],
            )
        )
    (args.output_root / "summary.md").write_text("\n".join(md_lines) + "\n")


if __name__ == "__main__":
    main()
