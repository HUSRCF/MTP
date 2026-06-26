#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mtp_expert_prefetch.runtime import (
    PayloadCacheLiveRuntimeAdapterDemandHitShadowPublicationCanary,
    build_payload_cache_live_payload_runtime_disabled_canary,
    build_payload_cache_live_payload_stage_preflight,
    build_payload_cache_live_runtime_adapter_accounting_dry_run_canary,
    build_payload_cache_live_runtime_adapter_constructor_binding_preflight,
    build_payload_cache_live_runtime_adapter_demand_hit_shadow_publication_canary,
    build_payload_cache_live_runtime_adapter_instantiation_canary,
    build_payload_cache_live_runtime_adapter_instance_construction_plan,
    build_payload_cache_live_runtime_adapter_materialization_preflight,
    build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary,
    build_payload_cache_live_runtime_adapter_object_shell_evidence,
    build_payload_cache_live_runtime_adapter_operation_rejection_canary,
    build_payload_cache_live_runtime_adapter_payloadless_instance_canary,
    build_payload_cache_live_runtime_adapter_state_object_preflight,
    build_payload_cache_live_runtime_adapter_state_validation_artifact,
    build_payload_cache_live_runtime_adapter_state_validation_preflight,
    build_payload_cache_live_runtime_object_adapter_preflight,
    build_payload_cache_live_runtime_object_construction_preflight,
    build_payload_cache_live_runtime_state_shape_check,
    build_payload_cache_manager_implementation_artifact,
    build_payload_cache_manager_runtime_skeleton,
    build_payload_cache_manager_runtime_snapshot_artifact,
    build_payload_cache_queue_budget_runtime_envelope,
    build_payload_cache_snapshot_backed_live_runtime_disabled_canary,
    build_payload_cache_snapshot_backed_live_runtime_preflight,
)

DEFAULT_OUTPUT_JSON = Path(
    "outputs/reports/premap_payload_cache/"
    "payload_cache_demand_hit_shadow_publication_gate.json",
)


def build_shadow_publication_canary() -> (
    PayloadCacheLiveRuntimeAdapterDemandHitShadowPublicationCanary
):
    envelope = build_payload_cache_queue_budget_runtime_envelope(
        cell_count=60,
        event_timing_mode="token_index",
        first_model_passing_capacity=4096,
        first_model_passing_issue_lead_tokens=32,
        first_model_passing_queue_deadline_us=100.0,
        first_model_passing_lookahead_us=2_400_000.0,
        shifted_issue_accounting_enabled=True,
        shifted_issue_accounted_packet_count=28,
        shifted_issue_unique_issue_key_count=16,
    )
    stage = build_payload_cache_live_payload_stage_preflight(envelope)
    runtime = build_payload_cache_live_payload_runtime_disabled_canary(
        stage,
        envelope,
    )
    manager = build_payload_cache_manager_implementation_artifact(runtime, envelope)
    skeleton = build_payload_cache_manager_runtime_skeleton(manager)
    snapshot = build_payload_cache_manager_runtime_snapshot_artifact(skeleton)
    backed_preflight = build_payload_cache_snapshot_backed_live_runtime_preflight(
        snapshot,
    )
    backed_disabled = build_payload_cache_snapshot_backed_live_runtime_disabled_canary(
        backed_preflight,
    )
    state_shape = build_payload_cache_live_runtime_state_shape_check(backed_disabled)
    object_construction = build_payload_cache_live_runtime_object_construction_preflight(
        state_shape,
    )
    object_adapter = build_payload_cache_live_runtime_object_adapter_preflight(
        object_construction,
    )
    materialization = build_payload_cache_live_runtime_adapter_materialization_preflight(
        object_adapter,
    )
    state_object = build_payload_cache_live_runtime_adapter_state_object_preflight(
        materialization,
    )
    state_validation = build_payload_cache_live_runtime_adapter_state_validation_preflight(
        state_object,
    )
    validation_artifact = build_payload_cache_live_runtime_adapter_state_validation_artifact(
        state_validation,
    )
    instantiation = build_payload_cache_live_runtime_adapter_instantiation_canary(
        validation_artifact,
    )
    binding = build_payload_cache_live_runtime_adapter_constructor_binding_preflight(
        instantiation,
    )
    plan = build_payload_cache_live_runtime_adapter_instance_construction_plan(binding)
    shell = build_payload_cache_live_runtime_adapter_object_shell_evidence(plan)
    rejection = build_payload_cache_live_runtime_adapter_operation_rejection_canary(shell)
    accounting = build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(
        rejection,
    )
    mixed = build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(
        accounting,
    )
    payloadless = build_payload_cache_live_runtime_adapter_payloadless_instance_canary(
        mixed,
    )
    return build_payload_cache_live_runtime_adapter_demand_hit_shadow_publication_canary(
        payloadless,
    )


def build_report() -> dict[str, Any]:
    canary = build_shadow_publication_canary()
    payload = canary.as_dict()
    failures: list[str] = []
    expected = {
        "publication_scope": "shadow_only",
        "demand_hit_shadow_publication_allowed": True,
        "demand_hit_published_to_shadow": True,
        "consumer_visible_payload_hit": False,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "payload_bytes": 0,
        "demand_hit_payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
        "payload_deref_attempted": False,
        "payload_handle_deref_attempted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "live_runtime_instantiated": False,
        "decision": "blocked",
        "block_reason": "shadow_only_not_consumer_visible_payload_hit",
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            failures.append(f"{key}_mismatch")
    if payload.get("demand_hit_rate") != 0.5:
        failures.append("demand_hit_rate_mismatch")

    return {
        "passed": not failures,
        "failures": failures,
        "source": "payload_cache_demand_hit_shadow_publication_gate",
        "artifact_kind": "payload_cache_demand_hit_shadow_publication_gate",
        "payload_bytes": payload["payload_bytes"],
        "demand_hit_payload_bytes": payload["demand_hit_payload_bytes"],
        "passed_to_kernel": payload["passed_to_kernel"],
        "changes_kernel_launch_args": payload["changes_kernel_launch_args"],
        "kernel_arg_pass_allowed": payload["kernel_arg_pass_allowed"],
        "consumer_visible_payload_hit": payload["consumer_visible_payload_hit"],
        "payload_deref_attempted": payload["payload_deref_attempted"],
        "payload_handle_deref_attempted": payload["payload_handle_deref_attempted"],
        "demand_hit_shadow_publication_allowed": payload[
            "demand_hit_shadow_publication_allowed"
        ],
        "demand_hit_published_to_shadow": payload["demand_hit_published_to_shadow"],
        "ready_credit": payload["ready_credit"],
        "demand_count": payload["demand_count"],
        "demand_hit_count": payload["demand_hit_count"],
        "demand_miss_count": payload["demand_miss_count"],
        "demand_hit_rate": payload["demand_hit_rate"],
        "canary": payload,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = build_report()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
