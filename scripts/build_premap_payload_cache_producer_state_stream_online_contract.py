#!/usr/bin/env python3
"""Materialize the online producer-state stream contract from a vLLM run.

The production-like graph-warmup payload-cache path currently exposes online
producer counters in performance_summary.json, but Python prelaunch state does
not persist across captured decode steps.  This bridge turns those online
counters into the native stream-producer input contract and validates that the
GPU-side persistent producer can generate non-empty issue candidates under the
same stream dimensions.

This is still payloadless:
- no payload bytes are moved,
- no ready credit is granted,
- no current WNA16 kernel arguments are passed or mutated.
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

from scripts import run_premap_payload_cache_producer_state_stream_stub as stream_stub


PREFIX = "runtime_shadow_premap_payload_cache_direct_"
ONLINE_CONTRACT_PREFIX = f"{PREFIX}online_stream_contract_"
STREAM_CONTRACT_REQUIRED_FALSE_FIELDS = (
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "payload_transfer_enabled",
    "payload_deref_allowed",
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
STREAM_CONTRACT_REQUIRED_ZERO_FIELDS = ("payload_bytes",)
REQUIRED_LAYER_SOURCE_KEYS = (
    f"{PREFIX}transition_native_packet_unique_layer_count",
)
OPTIONAL_LAYER_SOURCE_KEYS = (
    "decoder_layer_count",
    f"{ONLINE_CONTRACT_PREFIX}layers",
)
REQUIRED_EXPERT_SOURCE_KEYS = (
    f"{PREFIX}transition_native_packet_last_current_count",
)
OPTIONAL_EXPERT_SOURCE_KEYS = (f"{ONLINE_CONTRACT_PREFIX}experts_per_layer",)


def _load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _int_value(data: dict[str, Any], key: str, *, default: int | None = None) -> int:
    value = data.get(key, default)
    if value is None:
        raise ValueError(f"missing required integer field: {key}")
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"{key} must be non-negative")
    return parsed


def _steps_from_summary(summary: dict[str, Any], *, override: int | None) -> int:
    if override is not None:
        return int(override)
    embedded_steps = summary.get(f"{ONLINE_CONTRACT_PREFIX}steps")
    if embedded_steps is not None and int(embedded_steps) > 0:
        return int(embedded_steps)
    sample_count = _int_value(summary, "sample_count")
    requested_output_token_count = _int_value(summary, "requested_output_token_count")
    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    if requested_output_token_count <= 0:
        raise ValueError("requested_output_token_count must be positive")
    if requested_output_token_count % sample_count != 0:
        raise ValueError(
            "requested_output_token_count must be divisible by sample_count "
            "to infer decode steps"
    )
    return requested_output_token_count // sample_count


def _raw_step_consistency_failures(
    summary: dict[str, Any],
    *,
    steps: int,
) -> list[str]:
    failures: list[str] = []
    try:
        sample_count = _int_value(summary, "sample_count")
        requested_output_token_count = _int_value(
            summary,
            "requested_output_token_count",
        )
    except ValueError as exc:
        return [f"raw_step_source_invalid:{exc}"]
    if sample_count <= 0:
        failures.append("raw_step_sample_count_nonpositive")
    if requested_output_token_count <= 0:
        failures.append("raw_step_requested_output_token_count_nonpositive")
    if failures:
        return failures
    if requested_output_token_count % sample_count != 0:
        failures.append("raw_step_requested_output_token_count_not_divisible")
        return failures
    raw_steps = requested_output_token_count // sample_count
    if int(raw_steps) != int(steps):
        failures.append(
            "raw_step_embedded_mismatch:"
            f"raw={raw_steps},selected={int(steps)}"
        )
    return failures


def _layers_from_summary(summary: dict[str, Any], *, override: int | None) -> int:
    if override is not None:
        return int(override)
    embedded_layers = summary.get(f"{ONLINE_CONTRACT_PREFIX}layers")
    if embedded_layers is not None and int(embedded_layers) > 0:
        return int(embedded_layers)
    for key in (
        f"{PREFIX}transition_native_packet_unique_layer_count",
        f"{PREFIX}transition_producer_update_count",
        "decoder_layer_count",
    ):
        value = summary.get(key)
        if value is not None and int(value) > 0:
            return int(value)
    raise ValueError("could not infer layer count from performance summary")


def _experts_per_layer_from_summary(
    summary: dict[str, Any],
    *,
    override: int | None,
) -> int:
    if override is not None:
        return int(override)
    embedded_experts_per_layer = summary.get(
        f"{ONLINE_CONTRACT_PREFIX}experts_per_layer"
    )
    if (
        embedded_experts_per_layer is not None
        and int(embedded_experts_per_layer) > 0
    ):
        return int(embedded_experts_per_layer)
    value = summary.get(f"{PREFIX}transition_native_packet_last_current_count")
    if value is not None and int(value) > 0:
        return int(value)
    layers = _layers_from_summary(summary, override=None)
    demand_count = int(summary.get(f"{PREFIX}demand_count", 0))
    if layers > 0 and demand_count > 0:
        return max(1, demand_count // layers)
    raise ValueError("could not infer experts_per_layer from performance summary")


def _int_sources(summary: dict[str, Any], keys: tuple[str, ...]) -> dict[str, int]:
    sources: dict[str, int] = {}
    for key in keys:
        value = summary.get(key)
        if value is not None:
            sources[key] = int(value)
    return sources


def _optional_int(summary: dict[str, Any], key: str, default: int = 0) -> int:
    value = summary.get(key)
    if value is None:
        return int(default)
    return int(value)


def _optional_str(summary: dict[str, Any], key: str) -> str | None:
    value = summary.get(key)
    if value is None:
        return None
    return str(value)


def _required_source_failures(
    sources: dict[str, int],
    keys: tuple[str, ...],
    *,
    prefix: str,
) -> list[str]:
    failures: list[str] = []
    for key in keys:
        if key not in sources:
            failures.append(f"{prefix}_source_missing:{key}")
        elif int(sources[key]) <= 0:
            failures.append(f"{prefix}_source_nonpositive:{key}={sources[key]}")
    return failures


def _safety_field_failures(
    data: dict[str, Any],
    *,
    source: str,
    prefix: str = "",
    require_present: bool = False,
) -> list[str]:
    failures: list[str] = []
    for field in STREAM_CONTRACT_REQUIRED_ZERO_FIELDS:
        key = f"{prefix}{field}"
        if key not in data:
            if require_present:
                failures.append(f"{source}_{field}_missing")
            continue
        try:
            value = int(data[key])
        except (TypeError, ValueError):
            failures.append(f"{source}_{field}_invalid")
            continue
        if value != 0:
            failures.append(f"{source}_{field}_mismatch")
    for field in STREAM_CONTRACT_REQUIRED_FALSE_FIELDS:
        key = f"{prefix}{field}"
        if key not in data:
            if require_present:
                failures.append(f"{source}_{field}_missing")
            continue
        if data[key] is not False:
            failures.append(f"{source}_{field}_mismatch")
    return failures


def _performance_summary_safety_failures(summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    failures.extend(
        _safety_field_failures(
            summary,
            source="performance_summary",
            require_present=False,
        )
    )
    failures.extend(
        _safety_field_failures(
            summary,
            source="performance_summary_direct",
            prefix=PREFIX,
            require_present=False,
        )
    )
    direct_false_aliases = {
        "payload_transfer_runtime_enabled": (
            f"{PREFIX}payload_transfer_runtime_enabled"
        ),
        "full_fetch_runtime_allowed": f"{PREFIX}full_fetch_runtime_allowed",
    }
    for field, key in direct_false_aliases.items():
        if key in summary and summary[key] is not False:
            failures.append(f"performance_summary_direct_{field}_mismatch")
    runtime_execution_prefix = f"{PREFIX}runtime_execution_"
    failures.extend(
        _safety_field_failures(
            summary,
            source="performance_summary_runtime_execution",
            prefix=runtime_execution_prefix,
            require_present=False,
        )
    )
    runtime_execution_zero_aliases = {
        "payload_bytes": f"{runtime_execution_prefix}payload_bytes",
        "issued_payload_count": f"{runtime_execution_prefix}issued_payload_count",
    }
    runtime_execution_false_aliases = {
        "ready_credit": f"{runtime_execution_prefix}ready_credit",
        "real_ready_credit_granted": (
            f"{runtime_execution_prefix}real_ready_credit_granted"
        ),
        "payload_transfer_runtime_enabled": (
            f"{runtime_execution_prefix}payload_transfer_runtime_enabled"
        ),
        "full_fetch_runtime_allowed": (
            f"{runtime_execution_prefix}full_fetch_runtime_allowed"
        ),
        "live_payload_runtime_enabled": (
            f"{runtime_execution_prefix}live_payload_runtime_enabled"
        ),
        "kernel_arg_pass_allowed": (
            f"{runtime_execution_prefix}kernel_arg_pass_allowed"
        ),
    }
    for field, key in runtime_execution_zero_aliases.items():
        if key not in summary:
            continue
        try:
            value = int(summary[key])
        except (TypeError, ValueError):
            failures.append(f"performance_summary_runtime_execution_{field}_invalid")
            continue
        if value != 0:
            failures.append(f"performance_summary_runtime_execution_{field}_mismatch")
    for field, key in runtime_execution_false_aliases.items():
        if key in summary and summary[key] is not False:
            failures.append(f"performance_summary_runtime_execution_{field}_mismatch")
    return failures


def _dimension_consistency(
    summary: dict[str, Any],
    *,
    layers: int,
    experts_per_layer: int,
) -> tuple[dict[str, Any], list[str]]:
    layer_sources = _int_sources(
        summary, (*REQUIRED_LAYER_SOURCE_KEYS, *OPTIONAL_LAYER_SOURCE_KEYS)
    )
    layer_required_failures = _required_source_failures(
        layer_sources,
        REQUIRED_LAYER_SOURCE_KEYS,
        prefix="layer",
    )
    layer_mismatches = [
        f"layer_source_mismatch:{key}={value}"
        for key, value in layer_sources.items()
        if int(value) > 0 and int(value) != int(layers)
    ]
    expert_sources = _int_sources(
        summary, (*REQUIRED_EXPERT_SOURCE_KEYS, *OPTIONAL_EXPERT_SOURCE_KEYS)
    )
    expert_required_failures = _required_source_failures(
        expert_sources,
        REQUIRED_EXPERT_SOURCE_KEYS,
        prefix="expert",
    )
    expert_mismatches = [
        f"expert_source_mismatch:{key}={value}"
        for key, value in expert_sources.items()
        if int(value) > 0 and int(value) != int(experts_per_layer)
    ]
    failures = [
        *layer_required_failures,
        *layer_mismatches,
        *expert_required_failures,
        *expert_mismatches,
    ]
    return (
        {
            "layer_sources": layer_sources,
            "expert_sources": expert_sources,
            "required_layer_source_keys": list(REQUIRED_LAYER_SOURCE_KEYS),
            "required_expert_source_keys": list(REQUIRED_EXPERT_SOURCE_KEYS),
            "optional_layer_source_keys": list(OPTIONAL_LAYER_SOURCE_KEYS),
            "optional_expert_source_keys": list(OPTIONAL_EXPERT_SOURCE_KEYS),
            "layer_source_count": len(layer_sources),
            "expert_source_count": len(expert_sources),
            "all_layer_sources_match": not layer_required_failures
            and not layer_mismatches,
            "all_expert_sources_match": not expert_required_failures
            and not expert_mismatches,
        },
        failures,
    )


def _build_stub_args(args: argparse.Namespace, *, steps: int, layers: int, experts_per_layer: int) -> argparse.Namespace:
    return argparse.Namespace(
        device=int(args.device),
        steps=int(steps),
        layers=int(layers),
        experts_per_layer=int(experts_per_layer),
        transition_topk_count=int(args.transition_topk_count),
        max_num_experts=int(args.max_num_experts),
        step_shift=int(args.step_shift),
        layer_stride=int(args.layer_stride),
        state_hash_base=int(args.state_hash_base),
        disable_vectorized_copy=bool(args.disable_vectorized_copy),
        graph_replay=bool(args.graph_replay),
        offload_arch=str(args.offload_arch),
        hip_visible_devices=args.hip_visible_devices,
        force_build=bool(args.force_build),
        output_json=args.native_output_json,
        packet_stream_bin=None,
    )


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    performance_summary = args.performance_summary.resolve()
    summary = _load_json_object(performance_summary)
    steps = _steps_from_summary(summary, override=args.steps)
    layers = _layers_from_summary(summary, override=args.layers)
    experts_per_layer = _experts_per_layer_from_summary(
        summary,
        override=args.experts_per_layer,
    )
    stub_args = _build_stub_args(
        args,
        steps=steps,
        layers=layers,
        experts_per_layer=experts_per_layer,
    )
    native = stream_stub.run_stub(stub_args)
    args.native_output_json.parent.mkdir(parents=True, exist_ok=True)
    args.native_output_json.write_text(
        json.dumps(native, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    dimension_sources, dimension_failures = _dimension_consistency(
        summary,
        layers=layers,
        experts_per_layer=experts_per_layer,
    )
    expected_issue_per_packet = (
        experts_per_layer
        if int(args.transition_topk_count) == 0
        else min(experts_per_layer, int(args.transition_topk_count))
    )
    expected_packet_count = max(0, steps) * layers
    expected_previous_nonempty_packet_count = max(0, steps - 1) * layers
    expected_issue_count = max(0, steps - 1) * layers * expected_issue_per_packet
    failures: list[str] = [
        *_raw_step_consistency_failures(summary, steps=steps),
        *dimension_failures,
        *_performance_summary_safety_failures(summary),
    ]
    embedded_contract_present = bool(
        summary.get(f"{ONLINE_CONTRACT_PREFIX}present", False)
    )
    embedded_contract_passed = summary.get(f"{ONLINE_CONTRACT_PREFIX}passed")
    embedded_contract_failures = summary.get(f"{ONLINE_CONTRACT_PREFIX}failures")
    embedded_expected_issue_count = summary.get(
        f"{ONLINE_CONTRACT_PREFIX}expected_issue_candidate_count"
    )
    embedded_issue_count = summary.get(f"{ONLINE_CONTRACT_PREFIX}issue_candidate_count")
    direct_observed_packet_count = _optional_int(
        summary,
        f"{PREFIX}transition_native_packet_count",
        default=0,
    )
    direct_producer_update_count = summary.get(
        f"{PREFIX}transition_producer_update_count"
    )
    if direct_producer_update_count is None:
        failures.append(
            f"packet_source_missing:{PREFIX}transition_producer_update_count"
        )
        parsed_producer_update_count = -1
    else:
        parsed_producer_update_count = int(direct_producer_update_count)
        if parsed_producer_update_count <= 0:
            failures.append(
                "packet_source_nonpositive:"
                f"{PREFIX}transition_producer_update_count="
                f"{parsed_producer_update_count}"
            )
        elif parsed_producer_update_count != direct_observed_packet_count:
            failures.append("producer_update_count_mismatch")
    embedded_observed_packet_count = _optional_int(
        summary,
        f"{ONLINE_CONTRACT_PREFIX}observed_packet_count",
        default=_optional_int(
            summary,
            f"{ONLINE_CONTRACT_PREFIX}packet_count",
            default=direct_observed_packet_count,
        ),
    )
    direct_previous_nonempty_packet_count = _optional_int(
        summary,
        f"{PREFIX}transition_native_packet_previous_nonempty_count",
        default=_optional_int(
            summary,
            f"{PREFIX}transition_issue_previous_nonempty_count",
            default=0,
        ),
    )
    embedded_previous_nonempty_packet_count = _optional_int(
        summary,
        f"{ONLINE_CONTRACT_PREFIX}observed_previous_nonempty_packet_count",
        default=_optional_int(
            summary,
            f"{ONLINE_CONTRACT_PREFIX}previous_nonempty_packet_count",
            default=direct_previous_nonempty_packet_count,
        ),
    )
    direct_issue_candidate_count = _optional_int(
        summary,
        f"{PREFIX}transition_native_packet_issue_candidate_count",
        default=_optional_int(
            summary,
            f"{PREFIX}transition_issue_descriptor_count",
            default=0,
        ),
    )
    embedded_observed_issue_candidate_count = _optional_int(
        summary,
        f"{ONLINE_CONTRACT_PREFIX}observed_issue_candidate_count",
        default=_optional_int(
            summary,
            f"{ONLINE_CONTRACT_PREFIX}issue_candidate_count",
            default=direct_issue_candidate_count,
        ),
    )
    if direct_observed_packet_count != expected_packet_count:
        failures.append("online_observed_packet_count_mismatch")
    if direct_previous_nonempty_packet_count != expected_previous_nonempty_packet_count:
        failures.append("online_previous_nonempty_packet_count_mismatch")
    if direct_issue_candidate_count != expected_issue_count:
        failures.append("online_issue_candidate_count_mismatch")
    direct_issue_identity_keys = {
        "count": f"{PREFIX}transition_native_packet_last_issue_candidate_count",
        "first": f"{PREFIX}transition_native_packet_last_issue_candidate_first_expert",
        "last": f"{PREFIX}transition_native_packet_last_issue_candidate_last_expert",
        "hash": f"{PREFIX}transition_native_packet_last_issue_candidate_hash",
    }
    embedded_issue_identity_keys = {
        "count": f"{ONLINE_CONTRACT_PREFIX}issue_last_candidate_count",
        "first": f"{ONLINE_CONTRACT_PREFIX}issue_last_candidate_first_expert",
        "last": f"{ONLINE_CONTRACT_PREFIX}issue_last_candidate_last_expert",
        "hash": f"{ONLINE_CONTRACT_PREFIX}issue_last_candidate_hash",
    }
    direct_issue_identity_present = any(
        key in summary for key in direct_issue_identity_keys.values()
    )
    embedded_issue_identity_present = any(
        key in summary for key in embedded_issue_identity_keys.values()
    )
    direct_issue_identity_count = _optional_int(
        summary,
        direct_issue_identity_keys["count"],
        default=0,
    )
    embedded_issue_identity_count = _optional_int(
        summary,
        embedded_issue_identity_keys["count"],
        default=direct_issue_identity_count,
    )
    direct_issue_identity_first = _optional_int(
        summary,
        direct_issue_identity_keys["first"],
        default=-1,
    )
    embedded_issue_identity_first = _optional_int(
        summary,
        embedded_issue_identity_keys["first"],
        default=direct_issue_identity_first,
    )
    direct_issue_identity_last = _optional_int(
        summary,
        direct_issue_identity_keys["last"],
        default=-1,
    )
    embedded_issue_identity_last = _optional_int(
        summary,
        embedded_issue_identity_keys["last"],
        default=direct_issue_identity_last,
    )
    direct_issue_identity_hash = _optional_str(
        summary,
        direct_issue_identity_keys["hash"],
    )
    embedded_issue_identity_hash = _optional_str(
        summary,
        embedded_issue_identity_keys["hash"],
    )
    online_issue_identity_source = (
        "embedded_online_stream_contract"
        if embedded_issue_identity_present
        else "performance_summary"
        if direct_issue_identity_present
        else "absent"
    )
    online_issue_identity_count = int(
        embedded_issue_identity_count
        if embedded_issue_identity_present
        else direct_issue_identity_count
    )
    online_issue_identity_first = int(
        embedded_issue_identity_first
        if embedded_issue_identity_present
        else direct_issue_identity_first
    )
    online_issue_identity_last = int(
        embedded_issue_identity_last
        if embedded_issue_identity_present
        else direct_issue_identity_last
    )
    online_issue_identity_hash = (
        embedded_issue_identity_hash
        if embedded_issue_identity_present
        else direct_issue_identity_hash
    )
    if embedded_issue_identity_present and direct_issue_identity_present:
        if embedded_issue_identity_count != direct_issue_identity_count:
            failures.append("embedded_issue_last_candidate_count_mismatch")
        if embedded_issue_identity_first != direct_issue_identity_first:
            failures.append("embedded_issue_last_candidate_first_expert_mismatch")
        if embedded_issue_identity_last != direct_issue_identity_last:
            failures.append("embedded_issue_last_candidate_last_expert_mismatch")
        if embedded_issue_identity_hash != direct_issue_identity_hash:
            failures.append("embedded_issue_last_candidate_hash_mismatch")
    if online_issue_identity_count == 0 and online_issue_identity_hash is not None:
        failures.append("online_issue_identity_hash_without_count")
    if online_issue_identity_count > 0:
        if online_issue_identity_hash is None:
            failures.append("online_issue_identity_count_without_hash")
        if online_issue_identity_first < 0 or online_issue_identity_last < 0:
            failures.append("online_issue_identity_expert_missing")
    if embedded_contract_present:
        failures.extend(
            _safety_field_failures(
                summary,
                source="embedded_online_stream_contract",
                prefix=ONLINE_CONTRACT_PREFIX,
                require_present=True,
            )
        )
        if embedded_contract_passed is not True:
            failures.append("embedded_online_stream_contract_not_passed")
        if embedded_contract_failures not in ([], None):
            failures.append("embedded_online_stream_contract_failures_not_empty")
        if (
            embedded_expected_issue_count is not None
            and int(embedded_expected_issue_count) != int(expected_issue_count)
        ):
            failures.append("embedded_expected_issue_candidate_count_mismatch")
        if embedded_issue_count is not None and int(embedded_issue_count) != int(
            expected_issue_count
        ):
            failures.append("embedded_issue_candidate_count_mismatch")
        if embedded_observed_packet_count != expected_packet_count:
            failures.append("embedded_observed_packet_count_mismatch")
        if (
            embedded_previous_nonempty_packet_count
            != expected_previous_nonempty_packet_count
        ):
            failures.append("embedded_previous_nonempty_packet_count_mismatch")
        if embedded_observed_issue_candidate_count != expected_issue_count:
            failures.append("embedded_observed_issue_candidate_count_mismatch")
    if native.get("ok") is not True:
        failures.append("native_stream_stub_not_ok")
    native_graph_replay = native.get("native_graph_replay")
    native_requested_graph_replay = native.get("requested_graph_replay")
    if bool(args.graph_replay):
        if native_graph_replay is not True:
            failures.append("native_graph_replay_not_enabled")
        if native_requested_graph_replay is not True:
            failures.append("native_requested_graph_replay_not_enabled")
    if native.get("issue_candidate_count") != expected_issue_count:
        failures.append("issue_candidate_count_mismatch")
    if (
        int(native.get("previous_nonempty_packet_count", -1))
        != expected_previous_nonempty_packet_count
    ):
        failures.append("previous_nonempty_packet_count_mismatch")
    native_expected_values = [("payload_bytes", 0)]
    native_expected_values.extend(
        (key, False) for key in STREAM_CONTRACT_REQUIRED_FALSE_FIELDS
    )
    for key, expected in native_expected_values:
        if native.get(key) != expected:
            failures.append(f"native_{key}_mismatch")
    online_previous_nonempty = int(
        summary.get(f"{PREFIX}transition_issue_previous_nonempty_count", 0)
    )
    online_issue_descriptors = int(
        summary.get(f"{PREFIX}transition_issue_descriptor_count", 0)
    )
    passed = not failures
    return {
        "passed": passed,
        "ok": passed,
        "failures": failures,
        "mode": "payload_cache_producer_state_stream_online_contract",
        "performance_summary": str(performance_summary),
        "native_stream_output_json": str(args.native_output_json),
        "sample_count": int(summary.get("sample_count", 0)),
        "requested_output_token_count": int(
            summary.get("requested_output_token_count", 0)
        ),
        "online_transition_state_owner": summary.get(
            f"{PREFIX}transition_state_owner"
        ),
        "online_transition_native_packet_count": int(
            summary.get(f"{PREFIX}transition_native_packet_count", 0)
        ),
        "online_transition_native_packet_ready_count": int(
            summary.get(f"{PREFIX}transition_native_packet_ready_count", 0)
        ),
        "online_transition_native_packet_last_current_count": int(
            summary.get(f"{PREFIX}transition_native_packet_last_current_count", 0)
        ),
        "online_transition_issue_previous_nonempty_count": online_previous_nonempty,
        "online_transition_issue_descriptor_count": online_issue_descriptors,
        "online_transition_issue_last_candidate_present": bool(
            online_issue_identity_count > 0
            and online_issue_identity_hash is not None
        ),
        "online_transition_issue_last_candidate_source": online_issue_identity_source,
        "online_transition_issue_last_candidate_count": online_issue_identity_count,
        "online_transition_issue_last_candidate_first_expert": (
            online_issue_identity_first
        ),
        "online_transition_issue_last_candidate_last_expert": (
            online_issue_identity_last
        ),
        "online_transition_issue_last_candidate_hash": online_issue_identity_hash,
        "online_python_prelaunch_state_empty": bool(
            online_previous_nonempty == 0 and online_issue_descriptors == 0
        ),
        "contract_steps": int(steps),
        "contract_layers": int(layers),
        "contract_experts_per_layer": int(experts_per_layer),
        "contract_transition_topk_count": int(args.transition_topk_count),
        "contract_expected_packet_count": int(expected_packet_count),
        "contract_expected_previous_nonempty_packet_count": int(
            expected_previous_nonempty_packet_count
        ),
        "contract_expected_issue_candidate_count": int(expected_issue_count),
        "online_observed_packet_count": int(direct_observed_packet_count),
        "online_producer_update_count": int(parsed_producer_update_count),
        "online_observed_previous_nonempty_packet_count": int(
            direct_previous_nonempty_packet_count
        ),
        "online_observed_issue_candidate_count": int(direct_issue_candidate_count),
        "embedded_online_stream_contract_present": embedded_contract_present,
        "embedded_online_stream_contract_passed": embedded_contract_passed,
        "embedded_online_stream_contract_failures": embedded_contract_failures,
        "embedded_online_stream_contract_expected_issue_candidate_count": (
            None
            if embedded_expected_issue_count is None
            else int(embedded_expected_issue_count)
        ),
        "embedded_online_stream_contract_observed_packet_count": int(
            embedded_observed_packet_count
        ),
        "embedded_online_stream_contract_observed_previous_nonempty_packet_count": int(
            embedded_previous_nonempty_packet_count
        ),
        "embedded_online_stream_contract_observed_issue_candidate_count": int(
            embedded_observed_issue_candidate_count
        ),
        "embedded_online_stream_contract_issue_candidate_count": (
            None if embedded_issue_count is None else int(embedded_issue_count)
        ),
        "contract_dimension_sources": dimension_sources,
        "contract_dimension_consistency_failures": dimension_failures,
        "native_stream_issue_candidate_count": int(
            native.get("issue_candidate_count", 0)
        ),
        "native_stream_first_issue_expert": int(native.get("first_issue_expert", -1)),
        "native_stream_last_issue_expert": int(native.get("last_issue_expert", -1)),
        "native_stream_issue_candidate_hash": native.get("issue_candidate_hash"),
        "native_stream_previous_nonempty_packet_count": int(
            native.get("previous_nonempty_packet_count", 0)
        ),
        "native_stream_packet_count": int(native.get("packet_count", 0)),
        "native_stream_graph_replay_required": bool(args.graph_replay),
        "native_stream_graph_replay": bool(native.get("native_graph_replay", False)),
        "native_stream_requested_graph_replay": bool(
            native.get("requested_graph_replay", False)
        ),
        "native_stream_vectorized_copy_used": bool(
            native.get("vectorized_copy_used", False)
        ),
        "native_stream_persistent_state_on_device": bool(
            native.get("persistent_state_on_device", False)
        ),
        "native_stream_issue_generation_on_device": bool(
            native.get("issue_generation_on_device", False)
        ),
        "native_stream_gpu_elapsed_ms": native.get("gpu_elapsed_ms"),
        "payload_bytes": 0,
        **{key: False for key in STREAM_CONTRACT_REQUIRED_FALSE_FIELDS},
        "production_like_ab_ready": passed,
        "benchmark_is_current_wna16_fused_moe": False,
        "measures_tpot": False,
        "native_stream_is_current_wna16_fused_moe": False,
        "native_stream_measures_tpot": False,
        "native_stream": native,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--performance-summary", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--native-output-json", type=Path, required=True)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--steps", type=int)
    parser.add_argument("--layers", type=int)
    parser.add_argument("--experts-per-layer", type=int)
    parser.add_argument("--transition-topk-count", type=int, default=8)
    parser.add_argument("--max-num-experts", type=int, default=256)
    parser.add_argument("--step-shift", type=int, default=1)
    parser.add_argument("--layer-stride", type=int, default=17)
    parser.add_argument("--state-hash-base", type=int, default=0x8A45D2C91FE01237)
    parser.add_argument("--disable-vectorized-copy", action="store_true")
    parser.add_argument(
        "--graph-replay",
        dest="graph_replay",
        action="store_true",
        default=True,
        help="Require the native producer canary to run through HIP graph replay.",
    )
    parser.add_argument(
        "--no-graph-replay",
        dest="graph_replay",
        action="store_false",
        help="Diagnostic-only escape hatch: use normal native launches.",
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
