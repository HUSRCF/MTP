#!/usr/bin/env python3
"""Materialize the vLLM replay-visible native producer contract.

The online performance summary stores the future native-producer boundary under
flat ``runtime_shadow_*`` keys.  This helper strips that prefix into the exact
contract shape consumed by
``check_premap_payload_cache_vllm_replay_visible_native_producer.py``.

It does not run a native op, move payload bytes, grant readiness, or pass kernel
arguments.  Current fail-closed summaries should materialize successfully but
still fail the positive contract checker.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import (
    check_premap_payload_cache_vllm_replay_visible_count_ptr_readiness
    as count_ptr_checker,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PREFIX = (
    "runtime_shadow_premap_payload_cache_direct_"
    "vllm_replay_visible_native_producer_contract_"
)
CONTRACT_MODE = "payload_cache_vllm_replay_visible_native_producer_contract"
CONTRACT_BOUNDARY = "inprocess_vllm_replay_visible_native_producer_op"
CONTRACT_FIELDS = (
    "enabled",
    "present",
    "passed",
    "failures",
    "mode",
    "contract_boundary",
    "source_kind",
    "native_runtime",
    "inprocess_native_op",
    "vllm_replay_visible",
    "prelaunch_callable_native_session",
    "post_export_native_replay",
    "standalone_native_replay",
    "native_graph_replay",
    "transition_state_on_device",
    "persistent_state_on_device",
    "issue_generation_on_device",
    "python_transition_skipped",
    "packet_count",
    "expected_packet_count",
    "issue_candidate_count",
    "expected_issue_candidate_count",
    "expected_issue_candidate_count_source",
    "producer_update_count",
    "replay_visible_update_count",
    "current_expert_ptr_source_kind",
    "source_is_online_stream_contract",
    "source_is_raw_vllm_performance_summary",
    "ready_for_payload_cache_runtime_lab_gate",
    "next_boundary",
    "payload_bytes",
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "kernel_arg_pass",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "current_wna16_arg_compatible",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)
OPTIONAL_CONTRACT_FIELDS = (
    "ready",
    "prelaunch_probe_count",
    "prelaunch_probe_summary_scope",
    "prelaunch_probe_summary_run_sample_count",
    "expected_packet_count_source",
    "graph_visible_expected_packet_count_present",
    "prelaunch_independent_previous_nonempty_packet_count",
    "prelaunch_independent_previous_nonempty_issue_candidate_count",
    "native_session_previous_nonempty_packet_count",
    "prelaunch_abi_ready_count",
    "prelaunch_abi_blocked_count",
    "prelaunch_device_tensor_count",
    "prelaunch_host_tensor_count",
    "prelaunch_int32_count",
    "prelaunch_dtype_mismatch_count",
    "prelaunch_current_count_device_tensor_count",
    "prelaunch_current_count_device_scalar_int32_count",
    "prelaunch_current_count_host_scalar_available_count",
    "prelaunch_native_session_update_v1_abi_ready",
    "prelaunch_native_session_update_count_ptr_v1_abi_ready_count",
    "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count",
    "prelaunch_native_session_update_count_ptr_v1_abi_ready",
    "prelaunch_last_block_reason",
    "prelaunch_last_count_ptr_block_reason",
    "prelaunch_last_expert_dtype",
    "prelaunch_last_expert_device",
    "prelaunch_last_expert_ndim",
    "prelaunch_last_expert_numel",
    "prelaunch_last_block_size",
    "prelaunch_last_current_count_source_kind",
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def materialize_contract(
    performance_summary: dict[str, Any],
    *,
    performance_summary_path: Path | None = None,
) -> dict[str, Any]:
    materializer_failures: list[str] = []
    contract: dict[str, Any] = {
        "materialized_from_performance_summary": True,
        "input_prefix": CONTRACT_PREFIX,
    }
    if performance_summary_path is not None:
        contract["performance_summary"] = str(performance_summary_path)

    for field in CONTRACT_FIELDS:
        key = f"{CONTRACT_PREFIX}{field}"
        if key not in performance_summary:
            materializer_failures.append(f"{field}_missing")
            continue
        contract[field] = performance_summary[key]
    for field in OPTIONAL_CONTRACT_FIELDS:
        key = f"{CONTRACT_PREFIX}{field}"
        if key in performance_summary:
            contract[field] = performance_summary[key]
    contract.setdefault("ready", False)

    input_failures = contract.get("failures")
    if input_failures is None:
        input_failures_list: list[Any] = []
    elif isinstance(input_failures, list):
        input_failures_list = list(input_failures)
    else:
        input_failures_list = [input_failures]
        materializer_failures.append("failures_not_list")
    contract["failures"] = [
        *(str(value) for value in input_failures_list),
        *materializer_failures,
    ]
    contract["ok"] = bool(contract.get("passed") is True and not contract["failures"])
    contract["passed"] = bool(contract.get("passed") is True and not contract["failures"])
    contract.setdefault("mode", CONTRACT_MODE)
    contract.setdefault("contract_boundary", CONTRACT_BOUNDARY)
    contract["materializer_passed"] = not materializer_failures
    contract["materializer_failures"] = materializer_failures
    return contract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--performance-summary", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument(
        "--require-materializer-pass",
        action="store_true",
        help=(
            "Require the prefixed contract surface to be complete. This is the "
            "default; the flag is kept for explicit gate readability."
        ),
    )
    parser.add_argument(
        "--require-contract-pass",
        action="store_true",
        help="Return nonzero unless the materialized positive contract itself passes.",
    )
    parser.add_argument(
        "--count-ptr-readiness-output-json",
        type=Path,
        help=(
            "Optionally write the future count-pointer readiness checker output "
            "for this materialized contract."
        ),
    )
    parser.add_argument(
        "--require-count-ptr-readiness",
        action="store_true",
        help=(
            "Return nonzero unless the optional count-pointer readiness checker "
            "output passes."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    performance_summary_path = _resolve(args.performance_summary)
    output_json = _resolve(args.output_json)
    result = materialize_contract(
        _load_json(performance_summary_path),
        performance_summary_path=performance_summary_path,
    )
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    count_ptr_result: dict[str, Any] | None = None
    if (
        args.count_ptr_readiness_output_json is not None
        or args.require_count_ptr_readiness
    ):
        count_ptr_result = count_ptr_checker.check_contract(result)
        if args.count_ptr_readiness_output_json is not None:
            count_ptr_output_json = _resolve(args.count_ptr_readiness_output_json)
            count_ptr_output_json.parent.mkdir(parents=True, exist_ok=True)
            count_ptr_output_json.write_text(
                json.dumps(count_ptr_result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not bool(result.get("materializer_passed")):
        return 1
    if bool(args.require_contract_pass) and not bool(result.get("passed")):
        return 1
    if bool(args.require_count_ptr_readiness) and not bool(
        (count_ptr_result or {}).get("passed")
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
