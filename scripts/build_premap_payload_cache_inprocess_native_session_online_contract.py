#!/usr/bin/env python3
"""Build an online-dimension native session producer contract.

This bridges a passed vLLM online producer-state stream contract to the
prelaunch-callable in-process native session canary.  It is one boundary closer
to the online producer than the whole-stream native replay because the native
session updates persistent device state one packet at a time.

This artifact still does not claim vLLM/prelaunch external pointer evidence when
``--native-generated-current`` is used.  It also does not move payloads, grant
ready credit, pass current WNA16 kernel arguments, or measure endpoint latency.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for _path in (REPO_ROOT, SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts import run_premap_payload_cache_inprocess_native_session_stub as session_stub
from scripts.build_premap_payload_cache_producer_state_stream_online_contract import (
    ONLINE_CONTRACT_PREFIX,
    PREFIX,
    STREAM_CONTRACT_REQUIRED_FALSE_FIELDS,
    _dimension_consistency,
    _experts_per_layer_from_summary,
    _int_value,
    _layers_from_summary,
    _load_json_object,
    _optional_int,
    _raw_step_consistency_failures,
    _steps_from_summary,
)


def _build_session_args(
    args: argparse.Namespace,
    *,
    steps: int,
    layers: int,
    experts_per_layer: int,
    transition_topk_count: int,
) -> argparse.Namespace:
    return argparse.Namespace(
        device=int(args.device),
        steps=int(steps),
        layers=int(layers),
        experts_per_layer=int(experts_per_layer),
        transition_topk_count=int(transition_topk_count),
        max_num_experts=int(args.max_num_experts),
        step_shift=int(args.step_shift),
        layer_stride=int(args.layer_stride),
        disable_vectorized_copy=bool(args.disable_vectorized_copy),
        native_generated_current=bool(args.native_generated_current),
        offload_arch=str(args.offload_arch),
        force_build=bool(args.force_build),
        output_json=args.native_output_json,
    )


def _online_dimensions(
    summary: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[int, int, int, int, dict[str, Any], list[str]]:
    source_is_online_stream_contract = (
        summary.get("mode") == "payload_cache_producer_state_stream_online_contract"
    )
    dimension_failures: list[str] = []
    if source_is_online_stream_contract and summary.get("contract_steps") is not None:
        source_steps = int(summary["contract_steps"])
        if args.steps is not None and int(args.steps) != source_steps:
            dimension_failures.append("contract_steps_cli_override_mismatch")
        steps = source_steps
    else:
        steps = _steps_from_summary(summary, override=args.steps)
    if args.layers is not None:
        layers = int(args.layers)
        if (
            source_is_online_stream_contract
            and summary.get("contract_layers") is not None
            and layers != int(summary["contract_layers"])
        ):
            dimension_failures.append("contract_layers_cli_override_mismatch")
    elif source_is_online_stream_contract and summary.get("contract_layers") is not None:
        layers = int(summary["contract_layers"])
    else:
        layers = _layers_from_summary(summary, override=None)
    if args.experts_per_layer is not None:
        experts_per_layer = int(args.experts_per_layer)
        if (
            source_is_online_stream_contract
            and summary.get("contract_experts_per_layer") is not None
            and experts_per_layer != int(summary["contract_experts_per_layer"])
        ):
            dimension_failures.append(
                "contract_experts_per_layer_cli_override_mismatch"
            )
    elif (
        source_is_online_stream_contract
        and summary.get("contract_experts_per_layer") is not None
    ):
        experts_per_layer = int(summary["contract_experts_per_layer"])
    else:
        experts_per_layer = _experts_per_layer_from_summary(
            summary,
            override=None,
        )
    if (
        source_is_online_stream_contract
        and summary.get("contract_transition_topk_count") is not None
    ):
        source_transition_topk_count = int(summary["contract_transition_topk_count"])
        if (
            args.transition_topk_count is not None
            and int(args.transition_topk_count) != source_transition_topk_count
        ):
            dimension_failures.append(
                "contract_transition_topk_count_cli_override_mismatch"
            )
        transition_topk_count = source_transition_topk_count
    else:
        transition_topk_count = (
            8 if args.transition_topk_count is None else int(args.transition_topk_count)
        )
    if source_is_online_stream_contract:
        dimension_sources = summary.get("contract_dimension_sources")
        if not isinstance(dimension_sources, dict):
            dimension_sources = {}
        source_dimension_failures = summary.get(
            "contract_dimension_consistency_failures"
        )
        if isinstance(source_dimension_failures, list):
            dimension_failures.extend(str(item) for item in source_dimension_failures)
        else:
            dimension_failures.append("contract_dimension_consistency_failures_missing")
    else:
        dimension_sources, source_dimension_failures = _dimension_consistency(
            summary,
            layers=layers,
            experts_per_layer=experts_per_layer,
        )
        dimension_failures.extend(source_dimension_failures)
    return (
        steps,
        layers,
        experts_per_layer,
        transition_topk_count,
        dimension_sources,
        dimension_failures,
    )


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    performance_summary = args.performance_summary.resolve()
    summary = _load_json_object(performance_summary)
    source_is_online_stream_contract = (
        summary.get("mode") == "payload_cache_producer_state_stream_online_contract"
    )
    source_kind = (
        "derived_payload_cache_producer_state_stream_online_contract"
        if source_is_online_stream_contract
        else "raw_vllm_performance_summary"
    )
    source_failures = summary.get("failures")
    source_passed = summary.get("passed")
    (
        steps,
        layers,
        experts_per_layer,
        transition_topk_count,
        dimension_sources,
        dimension_failures,
    ) = _online_dimensions(summary, args)

    expected_issue_per_packet = (
        experts_per_layer
        if transition_topk_count == 0
        else min(experts_per_layer, transition_topk_count)
    )
    expected_packet_count = max(0, steps) * layers
    expected_previous_nonempty_packet_count = max(0, steps - 1) * layers
    expected_issue_count = (
        max(0, steps - 1) * layers * expected_issue_per_packet
    )

    direct_observed_packet_count = _optional_int(
        summary,
        f"{PREFIX}transition_native_packet_count",
        default=_optional_int(summary, "native_stream_packet_count", default=0),
    )
    direct_previous_nonempty_packet_count = _optional_int(
        summary,
        f"{PREFIX}transition_native_packet_previous_nonempty_count",
        default=_optional_int(
            summary,
            "native_stream_previous_nonempty_packet_count",
            default=0,
        ),
    )
    direct_issue_candidate_count = _optional_int(
        summary,
        f"{PREFIX}transition_native_packet_issue_candidate_count",
        default=_optional_int(summary, "native_stream_issue_candidate_count", default=0),
    )
    producer_update_count = summary.get(f"{PREFIX}transition_producer_update_count")
    failures: list[str] = [
        *_raw_step_consistency_failures(summary, steps=steps),
        *dimension_failures,
    ]
    if not source_is_online_stream_contract:
        failures.append("source_stream_online_contract_required")
    if source_is_online_stream_contract:
        if source_passed is not True:
            failures.append("source_stream_online_contract_not_passed")
        if source_failures not in ([], None):
            failures.append("source_stream_online_contract_failures_not_empty")
        if summary.get("payload_bytes") != 0:
            failures.append("source_stream_online_contract_payload_bytes_nonzero")
        for key in STREAM_CONTRACT_REQUIRED_FALSE_FIELDS:
            if summary.get(key) is not False:
                failures.append(f"source_stream_online_contract_{key}_mismatch")
    if producer_update_count is None and not source_is_online_stream_contract:
        failures.append(
            f"packet_source_missing:{PREFIX}transition_producer_update_count"
        )
        parsed_producer_update_count = -1
    elif producer_update_count is None:
        parsed_producer_update_count = int(direct_observed_packet_count)
    else:
        parsed_producer_update_count = int(producer_update_count)
        if parsed_producer_update_count != direct_observed_packet_count:
            failures.append("producer_update_count_mismatch")
    if direct_observed_packet_count != expected_packet_count:
        failures.append("online_observed_packet_count_mismatch")
    if direct_previous_nonempty_packet_count != expected_previous_nonempty_packet_count:
        failures.append("online_previous_nonempty_packet_count_mismatch")
    if direct_issue_candidate_count != expected_issue_count:
        failures.append("online_issue_candidate_count_mismatch")

    embedded_contract_present = bool(
        summary.get(f"{ONLINE_CONTRACT_PREFIX}present", False)
    )
    embedded_contract_passed = summary.get(f"{ONLINE_CONTRACT_PREFIX}passed")
    embedded_issue_count = summary.get(f"{ONLINE_CONTRACT_PREFIX}issue_candidate_count")
    if embedded_contract_present:
        if embedded_contract_passed is not True:
            failures.append("embedded_online_stream_contract_not_passed")
        if embedded_issue_count is not None and int(embedded_issue_count) != int(
            expected_issue_count
        ):
            failures.append("embedded_issue_candidate_count_mismatch")

    native_args = _build_session_args(
        args,
        steps=steps,
        layers=layers,
        experts_per_layer=experts_per_layer,
        transition_topk_count=transition_topk_count,
    )
    native = session_stub.run_session_stub(native_args)
    args.native_output_json.parent.mkdir(parents=True, exist_ok=True)
    args.native_output_json.write_text(
        json.dumps(native, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if native.get("passed") is not True or native.get("ok") is not True:
        failures.append("inprocess_native_session_not_passed")
    if native.get("issue_candidate_count") != expected_issue_count:
        failures.append("native_session_issue_candidate_count_mismatch")
    if (
        int(native.get("previous_nonempty_packet_count", -1))
        != expected_previous_nonempty_packet_count
    ):
        failures.append("native_session_previous_nonempty_packet_count_mismatch")
    current_expert_ptr_source_kind = str(
        native.get("current_expert_ptr_source_kind") or ""
    )
    if native.get("current_expert_ptr_source") == "native_generated_device_scratch":
        if native.get("external_current_expert_ptr_source") is not False:
            failures.append("native_session_external_source_mismatch")
        if current_expert_ptr_source_kind != "native_scratch_smoke":
            failures.append("native_session_current_expert_ptr_source_kind_mismatch")
        if native.get("ready_for_external_pointer_smoke") is not False:
            failures.append("native_session_external_pointer_smoke_ready_unexpected")
        if native.get("ready_for_vllm_prelaunch_canary") is not False:
            failures.append("native_session_vllm_prelaunch_ready_unexpected")
    elif native.get("current_expert_ptr_source") == "torch_device_tensor":
        if native.get("external_current_expert_ptr_source") is not True:
            failures.append("native_session_external_source_mismatch")
        if current_expert_ptr_source_kind != "external_torch_device_tensor_smoke":
            failures.append("native_session_current_expert_ptr_source_kind_mismatch")
        if native.get("ready_for_external_pointer_smoke") is not True:
            failures.append("native_session_external_pointer_smoke_not_ready")
        if native.get("ready_for_vllm_prelaunch_canary") is not False:
            failures.append("native_session_vllm_prelaunch_ready_unexpected")
    else:
        failures.append("native_session_current_expert_ptr_source_invalid")
    for key, expected in (
        ("payload_bytes", 0),
        ("ready_credit", False),
        ("kernel_arg_pass", False),
        ("kernel_arg_pass_allowed", False),
        ("passed_to_kernel", False),
        ("changes_kernel_launch_args", False),
        ("uses_current_wna16_args", False),
        ("passes_current_wna16_args", False),
        ("measures_tpot", False),
        ("measures_vllm_latency", False),
    ):
        if native.get(key) != expected:
            failures.append(f"native_session_{key}_mismatch")

    passed = not failures
    return {
        "passed": passed,
        "ok": passed,
        "failures": failures,
        "mode": "payload_cache_producer_state_inprocess_native_session_online_contract",
        "source_kind": source_kind,
        "source_is_online_stream_contract": bool(source_is_online_stream_contract),
        "source_stream_online_contract_passed": (
            source_passed if source_is_online_stream_contract else None
        ),
        "source_stream_online_contract_failures": (
            source_failures if source_is_online_stream_contract else None
        ),
        "source_is_raw_vllm_performance_summary": bool(
            not source_is_online_stream_contract
        ),
        "performance_summary": str(performance_summary),
        "native_session_output_json": str(args.native_output_json),
        "sample_count": _int_value(summary, "sample_count", default=0),
        "requested_output_token_count": _int_value(
            summary,
            "requested_output_token_count",
            default=0,
        ),
        "online_transition_state_owner": summary.get(
            f"{PREFIX}transition_state_owner"
        ),
        "online_observed_packet_count": int(direct_observed_packet_count),
        "online_producer_update_count": int(parsed_producer_update_count),
        "online_observed_previous_nonempty_packet_count": int(
            direct_previous_nonempty_packet_count
        ),
        "online_observed_issue_candidate_count": int(direct_issue_candidate_count),
        "contract_steps": int(steps),
        "contract_layers": int(layers),
        "contract_experts_per_layer": int(experts_per_layer),
        "contract_transition_topk_count": int(transition_topk_count),
        "contract_expected_packet_count": int(expected_packet_count),
        "contract_expected_previous_nonempty_packet_count": int(
            expected_previous_nonempty_packet_count
        ),
        "contract_expected_issue_candidate_count": int(expected_issue_count),
        "contract_dimension_sources": dimension_sources,
        "contract_dimension_consistency_failures": dimension_failures,
        "embedded_online_stream_contract_present": embedded_contract_present,
        "embedded_online_stream_contract_passed": embedded_contract_passed,
        "embedded_online_stream_contract_issue_candidate_count": (
            None if embedded_issue_count is None else int(embedded_issue_count)
        ),
        "inprocess_native_op": True,
        "native_runtime": True,
        "native_shared_library": True,
        "native_graph_replay": False,
        "native_stub_invoked": bool(native.get("native_stub_invoked", False)),
        "prelaunch_callable_native_session": True,
        "current_expert_ptr_source": native.get("current_expert_ptr_source"),
        "current_expert_ptr_source_kind": native.get("current_expert_ptr_source_kind"),
        "external_current_expert_ptr_source": bool(
            native.get("external_current_expert_ptr_source", False)
        ),
        "ready_for_native_session_smoke": bool(
            native.get("ready_for_native_session_smoke", False)
        ),
        "ready_for_external_pointer_smoke": bool(
            native.get("ready_for_external_pointer_smoke", False)
        ),
        "ready_for_vllm_prelaunch_canary": bool(
            native.get("ready_for_vllm_prelaunch_canary", False)
        ),
        "native_session_issue_candidate_count": int(
            native.get("issue_candidate_count", 0)
        ),
        "native_session_expected_issue_candidate_count": int(
            native.get("expected_issue_candidate_count", 0)
        ),
        "native_session_previous_nonempty_packet_count": int(
            native.get("previous_nonempty_packet_count", 0)
        ),
        "native_session_packet_count": int(native.get("packet_count", 0)),
        "native_session_gpu_elapsed_ms": native.get("gpu_elapsed_ms"),
        "persistent_state_on_device": bool(
            native.get("persistent_state_on_device", False)
        ),
        "issue_generation_on_device": bool(
            native.get("issue_generation_on_device", False)
        ),
        "vllm_replay_visible": False,
        "torch_graph_replay_visible": False,
        "graph_visible": False,
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "native": native,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--performance-summary", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--native-output-json", type=Path, required=True)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--steps", type=int)
    parser.add_argument("--layers", type=int)
    parser.add_argument("--experts-per-layer", type=int)
    parser.add_argument("--transition-topk-count", type=int)
    parser.add_argument("--max-num-experts", type=int, default=256)
    parser.add_argument("--step-shift", type=int, default=1)
    parser.add_argument("--layer-stride", type=int, default=17)
    parser.add_argument("--disable-vectorized-copy", action="store_true")
    parser.add_argument(
        "--native-generated-current",
        action="store_true",
        help=(
            "Use native scratch current-row generation for smoke runs. This "
            "does not prove external vLLM/prelaunch pointer sourcing."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = build_contract(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
