#!/usr/bin/env python3
"""Combine production-like TPOT A/B with the native producer stream contract."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _float(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if value is None:
        raise ValueError(f"missing float field {key}")
    return float(value)


def _int(data: dict[str, Any], key: str, default: int = 0) -> int:
    return int(data.get(key, default))


def _parse_int_field(value: Any, *, label: str) -> tuple[int, list[str]]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0, [f"{label}_not_int"]
    if not math.isfinite(float(value)):
        return 0, [f"{label}_not_finite"]
    if int(value) != float(value):
        return 0, [f"{label}_not_integral"]
    if value < 0:
        return 0, [f"{label}_negative"]
    return int(value), []


def _required_int_any(
    data: dict[str, Any],
    keys: tuple[str, ...],
    *,
    label: str,
) -> tuple[int, list[str]]:
    for key in keys:
        if key in data:
            return _parse_int_field(data[key], label=label)
    return 0, [f"{label}_missing"]


def _required_bool(
    data: dict[str, Any],
    key: str,
    *,
    label: str,
) -> tuple[bool, list[str]]:
    if key not in data:
        return False, [f"{label}_missing"]
    value = data[key]
    if not isinstance(value, bool):
        return False, [f"{label}_not_bool"]
    return value, []


def _required_false(
    data: dict[str, Any],
    key: str,
    *,
    label: str,
) -> tuple[bool, list[str]]:
    value, failures = _required_bool(data, key, label=label)
    if failures:
        return False, failures
    if value is not False:
        return value, [f"{label}_not_false"]
    return value, []


def _required_true(
    data: dict[str, Any],
    key: str,
    *,
    label: str,
) -> tuple[bool, list[str]]:
    value, failures = _required_bool(data, key, label=label)
    if failures:
        return False, failures
    if value is not True:
        return value, [f"{label}_not_true"]
    return value, []


def _required_nonempty_string(
    data: dict[str, Any],
    key: str,
    *,
    label: str,
) -> tuple[str, list[str]]:
    if key not in data:
        return "", [f"{label}_missing"]
    value = data[key]
    if not isinstance(value, str):
        return "", [f"{label}_not_string"]
    if not value:
        return "", [f"{label}_empty"]
    return value, []


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    baseline = _load_json(args.baseline_summary)
    candidate = _load_json(args.candidate_summary)
    contract = _load_json(args.online_contract)

    baseline_tpot = _float(baseline, "generate_seconds_per_requested_output_token")
    candidate_tpot = _float(candidate, "generate_seconds_per_requested_output_token")
    if not math.isfinite(baseline_tpot) or baseline_tpot <= 0:
        raise ValueError("baseline TPOT must be finite and positive")
    if not math.isfinite(candidate_tpot) or candidate_tpot <= 0:
        raise ValueError("candidate TPOT must be finite and positive")
    overhead_ratio = (candidate_tpot / baseline_tpot) - 1.0
    speedup_vs_baseline = baseline_tpot / candidate_tpot if candidate_tpot > 0 else 0.0
    max_overhead_ratio = float(args.max_overhead_ratio)
    contract_passed = contract.get("passed") is True
    candidate_payload_bytes, candidate_payload_failures = _required_int_any(
        candidate,
        (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes",
            "runtime_shadow_premap_payload_cache_direct_payload_bytes",
        ),
        label="candidate_payload_bytes",
    )
    candidate_kernel_arg_pass, candidate_kernel_arg_failures = _required_bool(
        candidate,
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed",
        label="candidate_kernel_arg_pass",
    )
    (
        candidate_changes_kernel_launch_args,
        candidate_kernel_launch_arg_failures,
    ) = _required_bool(
        candidate,
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args",
        label="candidate_changes_kernel_launch_args",
    )
    contract_payload_bytes, contract_payload_failures = _required_int_any(
        contract,
        ("payload_bytes",),
        label="contract_payload_bytes",
    )
    contract_ready_credit, contract_ready_failures = _required_false(
        contract,
        "ready_credit",
        label="contract_ready_credit",
    )
    contract_passed_to_kernel, contract_passed_failures = _required_false(
        contract,
        "passed_to_kernel",
        label="contract_passed_to_kernel",
    )
    (
        contract_changes_kernel_launch_args,
        contract_kernel_launch_failures,
    ) = _required_false(
        contract,
        "changes_kernel_launch_args",
        label="contract_changes_kernel_launch_args",
    )
    contract_uses_current_wna16_args, contract_uses_failures = _required_false(
        contract,
        "uses_current_wna16_args",
        label="contract_uses_current_wna16_args",
    )
    contract_passes_current_wna16_args, contract_passes_failures = _required_false(
        contract,
        "passes_current_wna16_args",
        label="contract_passes_current_wna16_args",
    )
    (
        contract_native_stream_graph_replay_required,
        contract_native_stream_graph_replay_required_failures,
    ) = _required_true(
        contract,
        "native_stream_graph_replay_required",
        label="contract_native_stream_graph_replay_required",
    )
    (
        contract_native_stream_graph_replay,
        contract_native_stream_graph_replay_failures,
    ) = _required_true(
        contract,
        "native_stream_graph_replay",
        label="contract_native_stream_graph_replay",
    )
    (
        contract_native_stream_requested_graph_replay,
        contract_native_stream_requested_graph_replay_failures,
    ) = _required_true(
        contract,
        "native_stream_requested_graph_replay",
        label="contract_native_stream_requested_graph_replay",
    )
    (
        contract_native_stream_is_current_wna16_fused_moe,
        contract_native_stream_wna16_failures,
    ) = _required_false(
        contract,
        "native_stream_is_current_wna16_fused_moe",
        label="contract_native_stream_is_current_wna16_fused_moe",
    )
    (
        contract_native_stream_measures_tpot,
        contract_native_stream_tpot_failures,
    ) = _required_false(
        contract,
        "native_stream_measures_tpot",
        label="contract_native_stream_measures_tpot",
    )
    (
        contract_expected_issue_candidate_count,
        contract_expected_issue_failures,
    ) = _required_int_any(
        contract,
        ("contract_expected_issue_candidate_count",),
        label="contract_expected_issue_candidate_count",
    )
    (
        contract_native_stream_issue_candidate_count,
        contract_native_issue_failures,
    ) = _required_int_any(
        contract,
        ("native_stream_issue_candidate_count",),
        label="contract_native_stream_issue_candidate_count",
    )
    (
        contract_native_stream_issue_candidate_hash,
        contract_native_hash_failures,
    ) = _required_nonempty_string(
        contract,
        "native_stream_issue_candidate_hash",
        label="contract_native_stream_issue_candidate_hash",
    )
    (
        contract_native_stream_persistent_state_on_device,
        contract_native_persistent_failures,
    ) = _required_true(
        contract,
        "native_stream_persistent_state_on_device",
        label="contract_native_stream_persistent_state_on_device",
    )
    (
        contract_native_stream_issue_generation_on_device,
        contract_native_issue_generation_failures,
    ) = _required_true(
        contract,
        "native_stream_issue_generation_on_device",
        label="contract_native_stream_issue_generation_on_device",
    )
    contract_issue_stream_failures: list[str] = []
    if (
        not contract_expected_issue_failures
        and contract_expected_issue_candidate_count <= 0
    ):
        contract_issue_stream_failures.append(
            "contract_expected_issue_candidate_count_nonpositive"
        )
    if not contract_native_issue_failures and (
        contract_native_stream_issue_candidate_count <= 0
    ):
        contract_issue_stream_failures.append(
            "contract_native_stream_issue_candidate_count_nonpositive"
        )
    if (
        not contract_expected_issue_failures
        and not contract_native_issue_failures
        and contract_native_stream_issue_candidate_count
        != contract_expected_issue_candidate_count
    ):
        contract_issue_stream_failures.append(
            "contract_native_stream_issue_candidate_count_mismatch"
        )
    candidate_safety_failures = [
        *candidate_payload_failures,
        *candidate_kernel_arg_failures,
        *candidate_kernel_launch_arg_failures,
    ]
    contract_safety_failures = [
        *contract_payload_failures,
        *contract_ready_failures,
        *contract_passed_failures,
        *contract_kernel_launch_failures,
        *contract_uses_failures,
        *contract_passes_failures,
        *contract_native_stream_graph_replay_required_failures,
        *contract_native_stream_graph_replay_failures,
        *contract_native_stream_requested_graph_replay_failures,
        *contract_native_stream_wna16_failures,
        *contract_native_stream_tpot_failures,
        *contract_expected_issue_failures,
        *contract_native_issue_failures,
        *contract_native_hash_failures,
        *contract_native_persistent_failures,
        *contract_native_issue_generation_failures,
        *contract_issue_stream_failures,
    ]
    production_ab_passed = (
        contract_passed
        and overhead_ratio <= max_overhead_ratio
        and not candidate_safety_failures
        and not contract_safety_failures
        and contract_payload_bytes == 0
        and not contract_ready_credit
        and not contract_passed_to_kernel
        and not contract_changes_kernel_launch_args
        and not contract_uses_current_wna16_args
        and not contract_passes_current_wna16_args
        and contract_native_stream_graph_replay_required
        and contract_native_stream_graph_replay
        and contract_native_stream_requested_graph_replay
        and not contract_native_stream_is_current_wna16_fused_moe
        and not contract_native_stream_measures_tpot
        and contract_native_stream_issue_candidate_count
        == contract_expected_issue_candidate_count
        and contract_native_stream_issue_candidate_count > 0
        and bool(contract_native_stream_issue_candidate_hash)
        and contract_native_stream_persistent_state_on_device
        and contract_native_stream_issue_generation_on_device
        and candidate_payload_bytes == 0
        and not candidate_kernel_arg_pass
        and not candidate_changes_kernel_launch_args
    )
    report_failures = (
        []
        if production_ab_passed
        else [
            reason
            for reason, active in (
                ("online_contract_failed", not contract_passed),
                ("tpot_overhead_over_threshold", overhead_ratio > max_overhead_ratio),
                ("contract_payload_bytes_nonzero", contract_payload_bytes != 0),
                ("candidate_payload_bytes_nonzero", candidate_payload_bytes != 0),
                ("candidate_kernel_arg_pass_enabled", candidate_kernel_arg_pass),
                (
                    "candidate_changes_kernel_launch_args",
                    candidate_changes_kernel_launch_args,
                ),
                (
                    "contract_native_stream_issue_candidate_count_mismatch",
                    contract_native_stream_issue_candidate_count
                    != contract_expected_issue_candidate_count,
                ),
            )
            if active
        ]
        + candidate_safety_failures
        + contract_safety_failures
    )

    return {
        "passed": production_ab_passed,
        "ok": production_ab_passed,
        "failures": report_failures,
        "mode": "payload_cache_stream_producer_production_like_ab_report",
        "baseline_summary": str(args.baseline_summary.resolve()),
        "candidate_summary": str(args.candidate_summary.resolve()),
        "online_contract": str(args.online_contract.resolve()),
        "baseline_tpot_s": baseline_tpot,
        "candidate_tpot_s": candidate_tpot,
        "candidate_overhead_ratio": overhead_ratio,
        "candidate_overhead_percent": overhead_ratio * 100.0,
        "candidate_speedup_vs_baseline": speedup_vs_baseline,
        "max_overhead_ratio": max_overhead_ratio,
        "max_overhead_percent": max_overhead_ratio * 100.0,
        "sample_count": _int(candidate, "sample_count"),
        "requested_output_token_count": _int(candidate, "requested_output_token_count"),
        "candidate_payload_bytes": candidate_payload_bytes,
        "candidate_kernel_arg_pass": candidate_kernel_arg_pass,
        "candidate_changes_kernel_launch_args": candidate_changes_kernel_launch_args,
        "candidate_runtime_execution_status": candidate.get(
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_status"
        ),
        "candidate_runtime_participation_status": candidate.get(
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_status"
        ),
        "candidate_online_transition_native_packet_count": _int(
            candidate,
            "runtime_shadow_premap_payload_cache_direct_transition_native_packet_count",
        ),
        "candidate_online_transition_issue_descriptor_count": _int(
            candidate,
            "runtime_shadow_premap_payload_cache_direct_transition_issue_descriptor_count",
        ),
        "candidate_online_transition_issue_previous_nonempty_count": _int(
            candidate,
            "runtime_shadow_premap_payload_cache_direct_transition_issue_previous_nonempty_count",
        ),
        "candidate_online_transition_issue_last_candidate_count": _int(
            candidate,
            "runtime_shadow_premap_payload_cache_direct_transition_issue_last_candidate_count",
        ),
        "candidate_online_transition_issue_last_candidate_hash": candidate.get(
            "runtime_shadow_premap_payload_cache_direct_transition_issue_last_candidate_hash"
        ),
        "online_transition_issue_last_candidate_present": bool(
            contract.get("online_transition_issue_last_candidate_present", False)
        ),
        "online_transition_issue_last_candidate_source": contract.get(
            "online_transition_issue_last_candidate_source"
        ),
        "online_transition_issue_last_candidate_count": _int(
            contract,
            "online_transition_issue_last_candidate_count",
        ),
        "online_transition_issue_last_candidate_first_expert": _int(
            contract,
            "online_transition_issue_last_candidate_first_expert",
            default=-1,
        ),
        "online_transition_issue_last_candidate_last_expert": _int(
            contract,
            "online_transition_issue_last_candidate_last_expert",
            default=-1,
        ),
        "online_transition_issue_last_candidate_hash": contract.get(
            "online_transition_issue_last_candidate_hash"
        ),
        "online_contract_passed": contract_passed,
        "online_contract_steps": _int(contract, "contract_steps"),
        "online_contract_layers": _int(contract, "contract_layers"),
        "online_contract_experts_per_layer": _int(
            contract,
            "contract_experts_per_layer",
        ),
        "online_contract_expected_issue_candidate_count": (
            contract_expected_issue_candidate_count
        ),
        "native_stream_issue_candidate_count": (
            contract_native_stream_issue_candidate_count
        ),
        "native_stream_first_issue_expert": _int(
            contract,
            "native_stream_first_issue_expert",
            default=-1,
        ),
        "native_stream_last_issue_expert": _int(
            contract,
            "native_stream_last_issue_expert",
            default=-1,
        ),
        "native_stream_issue_candidate_hash": (
            contract_native_stream_issue_candidate_hash
        ),
        "native_stream_previous_nonempty_packet_count": _int(
            contract,
            "native_stream_previous_nonempty_packet_count",
        ),
        "native_stream_persistent_state_on_device": (
            contract_native_stream_persistent_state_on_device
        ),
        "native_stream_issue_generation_on_device": (
            contract_native_stream_issue_generation_on_device
        ),
        "native_stream_vectorized_copy_used": bool(
            contract.get("native_stream_vectorized_copy_used", False)
        ),
        "native_stream_graph_replay_required": (
            contract_native_stream_graph_replay_required
        ),
        "native_stream_graph_replay": contract_native_stream_graph_replay,
        "native_stream_requested_graph_replay": (
            contract_native_stream_requested_graph_replay
        ),
        "payload_bytes": contract_payload_bytes,
        "ready_credit": contract_ready_credit,
        "passed_to_kernel": contract_passed_to_kernel,
        "changes_kernel_launch_args": contract_changes_kernel_launch_args,
        "uses_current_wna16_args": contract_uses_current_wna16_args,
        "passes_current_wna16_args": contract_passes_current_wna16_args,
        "benchmark_is_current_wna16_fused_moe": True,
        "measures_tpot": True,
        "native_stream_is_current_wna16_fused_moe": (
            contract_native_stream_is_current_wna16_fused_moe
        ),
        "native_stream_measures_tpot": contract_native_stream_measures_tpot,
        "performance_claim": (
            "production_like_overhead_with_native_stream_contract"
            if production_ab_passed
            else "production_like_ab_not_passed"
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-summary", type=Path, required=True)
    parser.add_argument("--candidate-summary", type=Path, required=True)
    parser.add_argument("--online-contract", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--max-overhead-ratio", type=float, default=0.02)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = build_report(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
