#!/usr/bin/env python3
"""Run the in-process native producer-state canary.

This is the next boundary after the standalone HIP producer-state stream stub:
Python loads a HIP shared library in-process and calls a fixed C ABI that keeps
transition state on device and generates issue candidates in a native graph
replay.  It is still not a vLLM/PyTorch graph-visible op and it does not move
payloads or pass current WNA16 kernel arguments.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = (
    REPO_ROOT
    / "microbench"
    / "premap_kernel_consumer"
    / "premap_payload_cache_inprocess_native_producer_stub.hip"
)
ABI_HEADER = (
    REPO_ROOT
    / "microbench"
    / "premap_kernel_consumer"
    / "premap_typed_consumer_abi_v1.h"
)
BUILD_DIR = REPO_ROOT / "microbench" / "premap_kernel_consumer" / "build"
MAX_NATIVE_STREAM_COUNT = 65536


class InprocessProducerResult(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_uint32),
        ("ok", ctypes.c_uint32),
        ("passed", ctypes.c_uint32),
        ("native_returncode", ctypes.c_uint32),
        ("steps", ctypes.c_uint32),
        ("layers", ctypes.c_uint32),
        ("experts_per_layer", ctypes.c_uint32),
        ("transition_topk_count", ctypes.c_uint32),
        ("packet_count", ctypes.c_uint64),
        ("previous_nonempty_packet_count", ctypes.c_uint64),
        ("current_nonempty_packet_count", ctypes.c_uint64),
        ("issue_candidate_count", ctypes.c_uint64),
        ("expected_issue_candidate_count", ctypes.c_uint64),
        ("issue_candidate_hash", ctypes.c_uint64),
        ("first_issue_expert", ctypes.c_int32),
        ("last_issue_expert", ctypes.c_int32),
        ("ready_layer_count", ctypes.c_uint32),
        ("error_count", ctypes.c_uint32),
        ("gpu_elapsed_ms", ctypes.c_float),
        ("persistent_state_on_device", ctypes.c_uint32),
        ("issue_generation_on_device", ctypes.c_uint32),
        ("native_graph_replay", ctypes.c_uint32),
        ("native_stub_invoked", ctypes.c_uint32),
        ("vectorized_copy_requested", ctypes.c_uint32),
        ("vectorized_copy_used", ctypes.c_uint32),
        ("payload_bytes", ctypes.c_uint32),
        ("payload_transfer_enabled", ctypes.c_uint32),
        ("payload_deref_allowed", ctypes.c_uint32),
        ("ready_credit", ctypes.c_uint32),
        ("ready_before_demand_credit", ctypes.c_uint32),
        ("real_ready_credit_granted", ctypes.c_uint32),
        ("passed_to_kernel", ctypes.c_uint32),
        ("changes_kernel_launch_args", ctypes.c_uint32),
        ("kernel_arg_pass", ctypes.c_uint32),
        ("kernel_arg_pass_allowed", ctypes.c_uint32),
        ("current_wna16_arg_compatible", ctypes.c_uint32),
        ("uses_current_wna16_args", ctypes.c_uint32),
        ("passes_current_wna16_args", ctypes.c_uint32),
        ("measures_tpot", ctypes.c_uint32),
        ("measures_vllm_latency", ctypes.c_uint32),
    ]


def _build_key(offload_arch: str) -> str:
    latest = "|".join(
        [
            offload_arch,
            SRC.read_text(encoding="utf-8"),
            ABI_HEADER.read_text(encoding="utf-8"),
        ]
    )
    return hashlib.sha256(latest.encode("utf-8")).hexdigest()[:12]


def build_command(*, offload_arch: str, output: Path) -> list[str]:
    return [
        "hipcc",
        "-O3",
        "--std=c++17",
        "-shared",
        "-fPIC",
        f"--offload-arch={offload_arch}",
        str(SRC),
        "-o",
        str(output),
    ]


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _validate_count(value: int, name: str, *, allow_zero: bool = False) -> int:
    parsed = int(value)
    if parsed < 0 or (parsed == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {qualifier}")
    if parsed > MAX_NATIVE_STREAM_COUNT:
        raise ValueError(
            f"{name} exceeds native in-process canary safety bound "
            f"{MAX_NATIVE_STREAM_COUNT}"
        )
    return parsed


def build(*, offload_arch: str, force: bool) -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    library = BUILD_DIR / (
        f"premap_payload_cache_inprocess_native_producer_{_build_key(offload_arch)}.so"
    )
    latest_source_mtime = max(SRC.stat().st_mtime, ABI_HEADER.stat().st_mtime)
    if library.exists() and not force and library.stat().st_mtime >= latest_source_mtime:
        return library
    result = run_cmd(build_command(offload_arch=offload_arch, output=library))
    if result.returncode != 0:
        raise RuntimeError(
            "failed to build in-process native producer stub\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    return library


def _bool_flag(value: int) -> bool:
    return bool(int(value))


def _payload_from_result(
    result: InprocessProducerResult,
    *,
    native_returncode: int,
    library: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    ok = bool(result.ok) and native_returncode == 0
    failures: list[str] = []
    if not ok:
        failures.append("inprocess_native_producer_not_ok")
    if result.issue_candidate_count != result.expected_issue_candidate_count:
        failures.append("issue_candidate_count_mismatch")
    if result.issue_candidate_count <= 0:
        failures.append("issue_candidate_count_empty")
    if result.error_count != 0:
        failures.append("native_error_count_nonzero")
    if result.ready_layer_count != result.layers:
        failures.append("ready_layer_count_mismatch")
    if not _bool_flag(result.persistent_state_on_device):
        failures.append("persistent_state_not_on_device")
    if not _bool_flag(result.issue_generation_on_device):
        failures.append("issue_generation_not_on_device")
    if not _bool_flag(result.native_graph_replay):
        failures.append("native_graph_replay_not_enabled")
    for field in (
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "kernel_arg_pass",
        "kernel_arg_pass_allowed",
        "current_wna16_arg_compatible",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if _bool_flag(getattr(result, field)):
            failures.append(f"{field}_unexpectedly_enabled")
    if int(result.payload_bytes) != 0:
        failures.append("payload_bytes_nonzero")
    payload = {
        "ok": ok and not failures,
        "passed": ok and not failures,
        "failures": failures,
        "mode": "payload_cache_producer_transition_state_inprocess_native_canary",
        "abi_name": "premap_payload_cache_producer_transition_state_abi_v1",
        "abi_field_count": 9,
        "inprocess_native_op": True,
        "native_runtime": True,
        "native_shared_library": True,
        "native_stub_invoked": _bool_flag(result.native_stub_invoked),
        "native_returncode": int(native_returncode),
        "native_result_returncode": int(result.native_returncode),
        "native_graph_replay": _bool_flag(result.native_graph_replay),
        "vllm_replay_visible": False,
        "torch_graph_replay_visible": False,
        "ready_for_vllm_prelaunch_canary": ok and not failures,
        "persistent_state_on_device": _bool_flag(result.persistent_state_on_device),
        "issue_generation_on_device": _bool_flag(result.issue_generation_on_device),
        "steps": int(result.steps),
        "layers": int(result.layers),
        "experts_per_layer": int(result.experts_per_layer),
        "transition_topk_count": int(result.transition_topk_count),
        "packet_count": int(result.packet_count),
        "previous_nonempty_packet_count": int(result.previous_nonempty_packet_count),
        "current_nonempty_packet_count": int(result.current_nonempty_packet_count),
        "issue_candidate_count": int(result.issue_candidate_count),
        "expected_issue_candidate_count": int(result.expected_issue_candidate_count),
        "first_issue_expert": int(result.first_issue_expert),
        "last_issue_expert": int(result.last_issue_expert),
        "issue_candidate_hash": f"{int(result.issue_candidate_hash):016x}",
        "ready_layer_count": int(result.ready_layer_count),
        "error_count": int(result.error_count),
        "gpu_elapsed_ms": float(result.gpu_elapsed_ms),
        "vectorized_copy_requested": _bool_flag(result.vectorized_copy_requested),
        "vectorized_copy_used": _bool_flag(result.vectorized_copy_used),
        "payload_bytes": int(result.payload_bytes),
        "payload_transfer_enabled": _bool_flag(result.payload_transfer_enabled),
        "payload_deref_allowed": _bool_flag(result.payload_deref_allowed),
        "ready_credit": _bool_flag(result.ready_credit),
        "ready_before_demand_credit": _bool_flag(result.ready_before_demand_credit),
        "real_ready_credit_granted": _bool_flag(result.real_ready_credit_granted),
        "passed_to_kernel": _bool_flag(result.passed_to_kernel),
        "changes_kernel_launch_args": _bool_flag(result.changes_kernel_launch_args),
        "kernel_arg_pass": _bool_flag(result.kernel_arg_pass),
        "kernel_arg_pass_allowed": _bool_flag(result.kernel_arg_pass_allowed),
        "current_wna16_arg_compatible": _bool_flag(
            result.current_wna16_arg_compatible
        ),
        "uses_current_wna16_args": _bool_flag(result.uses_current_wna16_args),
        "passes_current_wna16_args": _bool_flag(result.passes_current_wna16_args),
        "measures_tpot": _bool_flag(result.measures_tpot),
        "measures_vllm_latency": _bool_flag(result.measures_vllm_latency),
        "shared_library": str(library),
        "source": str(SRC),
        "abi_header": str(ABI_HEADER),
        "offload_arch": str(args.offload_arch),
        "requested_steps": int(args.steps),
        "requested_layers": int(args.layers),
        "requested_experts_per_layer": int(args.experts_per_layer),
        "requested_transition_topk_count": int(args.transition_topk_count),
        "requested_graph_replay": bool(args.graph_replay),
        "requested_disable_vectorized_copy": bool(args.disable_vectorized_copy),
    }
    return payload


def run_stub(args: argparse.Namespace) -> dict[str, Any]:
    library = build(offload_arch=args.offload_arch, force=args.force_build)
    steps = _validate_count(args.steps, "steps")
    layers = _validate_count(args.layers, "layers")
    experts_per_layer = _validate_count(args.experts_per_layer, "experts-per-layer")
    transition_topk_count = _validate_count(
        args.transition_topk_count,
        "transition-topk-count",
        allow_zero=True,
    )
    max_num_experts = _validate_count(args.max_num_experts, "max-num-experts")
    step_shift = _validate_count(args.step_shift, "step-shift", allow_zero=True)
    layer_stride = _validate_count(args.layer_stride, "layer-stride", allow_zero=True)
    lib = ctypes.CDLL(str(library))
    fn = lib.premap_payload_cache_inprocess_producer_run_v1
    fn.argtypes = [
        ctypes.c_int,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(InprocessProducerResult),
    ]
    fn.restype = ctypes.c_int
    result = InprocessProducerResult()
    native_returncode = int(
        fn(
            int(args.device),
            int(steps),
            int(layers),
            int(experts_per_layer),
            int(transition_topk_count),
            int(max_num_experts),
            int(step_shift),
            int(layer_stride),
            0 if args.disable_vectorized_copy else 1,
            1 if args.graph_replay else 0,
            ctypes.byref(result),
        )
    )
    return _payload_from_result(
        result,
        native_returncode=native_returncode,
        library=library,
        args=args,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--layers", type=int, default=40)
    parser.add_argument("--experts-per-layer", type=int, default=8)
    parser.add_argument("--transition-topk-count", type=int, default=8)
    parser.add_argument("--max-num-experts", type=int, default=256)
    parser.add_argument("--step-shift", type=int, default=1)
    parser.add_argument("--layer-stride", type=int, default=17)
    parser.add_argument("--disable-vectorized-copy", action="store_true")
    parser.add_argument("--graph-replay", action="store_true")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT
        / "outputs"
        / "reports"
        / "premap_kernel_consumer"
        / "payload_cache_producer_state_inprocess_native_stub.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_stub(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
