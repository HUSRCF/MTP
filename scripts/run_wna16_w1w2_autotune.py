#!/usr/bin/env python3
"""Run WNA16 runtime override candidates separately for W1 and W2 buckets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


def _read_results(path: Path) -> list[dict[str, Any]]:
    results_path = path / "results.json"
    if not results_path.exists():
        return []
    return json.loads(results_path.read_text())


def _run_bucket(
    *,
    bucket: str,
    target_top_k: int,
    args: argparse.Namespace,
) -> tuple[int, list[dict[str, Any]]]:
    bucket_root = args.output_root / bucket
    command = [
        sys.executable,
        "scripts/run_wna16_config_sweep.py",
        "--override-mode",
        "runtime",
        "--gpu",
        str(args.gpu),
        "--conda-env",
        str(args.conda_env),
        "--base-config",
        str(args.base_config),
        "--output-root",
        str(bucket_root),
        "--max-samples",
        str(args.max_samples),
        "--max-tokens",
        str(args.max_tokens),
        "--start-sample",
        str(args.start_sample),
        "--runtime-override-max-tokens",
        str(args.runtime_override_max_tokens),
        "--runtime-override-route-product",
        str(args.runtime_override_route_product),
        "--runtime-override-target-top-k",
        str(target_top_k),
        "--candidates",
        *args.candidates,
    ]
    if args.emit_kernel_timing:
        command.append("--emit-kernel-timing")
        command.extend(["--kernel-timing-mode", str(args.kernel_timing_mode)])
    if args.emit_decoder_layer_timing:
        command.append("--emit-decoder-layer-timing")
    if args.disable_router_topk_recording:
        command.append("--disable-router-topk-recording")
    if args.continue_on_error:
        command.append("--continue-on-error")
    print(f"[wna16-w1w2] running {bucket} target_top_k={target_top_k}", flush=True)
    proc = subprocess.run(command, cwd=Path.cwd(), check=False)
    results = _read_results(bucket_root)
    for row in results:
        row["bucket"] = bucket
        row["target_top_k"] = target_top_k
    return proc.returncode, results


def _add_bucket_speedups(results: list[dict[str, Any]]) -> None:
    baselines: dict[str, float] = {}
    for row in results:
        if row.get("candidate") != "baseline_no_tuned_config":
            continue
        tpot = row.get("generate_seconds_per_requested_output_token")
        if tpot:
            baselines[str(row["bucket"])] = float(tpot)
    for row in results:
        tpot = row.get("generate_seconds_per_requested_output_token")
        baseline = baselines.get(str(row.get("bucket")))
        if tpot and baseline:
            row["speedup_vs_bucket_baseline"] = baseline / float(tpot)


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
        default=Path("outputs/reports/wna16_w1w2_autotune/awq_w7900_gpu1"),
    )
    parser.add_argument("--max-samples", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=8)
    parser.add_argument("--start-sample", type=int, default=128)
    parser.add_argument("--runtime-override-max-tokens", type=int, default=8)
    parser.add_argument("--runtime-override-route-product", type=int, default=8)
    parser.add_argument("--gpu", default="1")
    parser.add_argument("--conda-env", default="TRY")
    parser.add_argument(
        "--buckets",
        nargs="*",
        choices=("w1", "w2"),
        default=["w1", "w2"],
    )
    parser.add_argument(
        "--candidates",
        nargs="*",
        default=["baseline_no_tuned_config", "bm16_g1_w2_s2"],
    )
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument(
        "--emit-kernel-timing",
        action="store_true",
        help="Emit wna16_kernel_timing rows for W1/W2 attribution.",
    )
    parser.add_argument(
        "--kernel-timing-mode",
        choices=("host", "gpu_event"),
        default="host",
        help="Timing mode for WNA16 attribution rows.",
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
            "Forward diagnostic no-record_topk mode to the underlying WNA16 "
            "config sweep."
        ),
    )
    args = parser.parse_args()

    bucket_specs = {"w1": 8, "w2": 1}
    args.output_root.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, Any]] = []
    exit_code = 0
    for bucket in args.buckets:
        code, results = _run_bucket(
            bucket=bucket,
            target_top_k=bucket_specs[bucket],
            args=args,
        )
        all_results.extend(results)
        if code != 0 and not args.continue_on_error:
            exit_code = code
            break
    _add_bucket_speedups(all_results)
    (args.output_root / "results.json").write_text(
        json.dumps(all_results, indent=2) + "\n"
    )

    lines = [
        "# WNA16 W1/W2 Runtime Override Autotune",
        "",
        "Metric note: these are bucket-targeted end-to-end TPOT runs, not isolated micro-kernel timings.",
        "Kernel timing note: runs with `--emit-kernel-timing` are instrumented attribution runs and should not be used as telemetry-off TPOT claims.",
        "",
        f"base_config: `{args.base_config}`",
        f"max_samples: `{args.max_samples}`",
        f"max_tokens: `{args.max_tokens}`",
        f"runtime_override_max_tokens: `{args.runtime_override_max_tokens}`",
        f"runtime_override_route_product: `{args.runtime_override_route_product}`",
        f"kernel_timing_mode: `{args.kernel_timing_mode if args.emit_kernel_timing else 'off'}`",
        f"decoder_layer_timing: `{bool(args.emit_decoder_layer_timing)}`",
        "",
        "| bucket | target_top_k | candidate | TPOT | speedup | returncode |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for row in all_results:
        tpot = row.get("generate_seconds_per_requested_output_token")
        speedup = row.get("speedup_vs_bucket_baseline")
        lines.append(
            "| {bucket} | {target_top_k} | {candidate} | {tpot} | {speedup} | {returncode} |".format(
                bucket=row.get("bucket", ""),
                target_top_k=row.get("target_top_k", ""),
                candidate=row.get("candidate", ""),
                tpot=f"{float(tpot):.6f}" if tpot else "",
                speedup=f"{float(speedup):.4f}x" if speedup else "",
                returncode=row.get("returncode", ""),
            )
        )
    (args.output_root / "summary.md").write_text("\n".join(lines) + "\n")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
