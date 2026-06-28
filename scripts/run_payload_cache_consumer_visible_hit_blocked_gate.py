#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from mtp_expert_prefetch.runtime import (
    PayloadCacheLiveRuntimeAdapterPayloadIssueDemandHitPublicationBlockedCanary,
    build_payload_cache_live_payload_runtime_disabled_canary,
    build_payload_cache_live_payload_stage_preflight,
    build_payload_cache_live_runtime_adapter_accounting_dry_run_canary,
    build_payload_cache_live_runtime_adapter_constructor_binding_preflight,
    build_payload_cache_live_runtime_adapter_instantiation_canary,
    build_payload_cache_live_runtime_adapter_instance_construction_plan,
    build_payload_cache_live_runtime_adapter_materialization_preflight,
    build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary,
    build_payload_cache_live_runtime_adapter_object_shell_evidence,
    build_payload_cache_live_runtime_adapter_operation_rejection_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_completion_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_demand_hit_publication_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_payload_deref_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_ready_credit_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_residency_update_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary,
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
    "payload_cache_consumer_visible_hit_blocked_gate.json",
)
SOURCE_BOUND_QUEUE_BUDGET: dict[str, int | float | str] = {
    "cell_count": 60,
    "event_timing_mode": "token_index",
    "first_model_passing_capacity": 4096,
    "first_model_passing_issue_lead_tokens": 8,
    "first_model_passing_queue_deadline_us": 100.0,
    "first_model_passing_lookahead_us": 2_400_000.0,
    "shifted_issue_accounted_packet_count": 28,
    "shifted_issue_unique_issue_key_count": 16,
}
REQUEST_SOURCE = "queue_budget_first_model_passing_cell"


def build_consumer_visible_hit_blocked_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueDemandHitPublicationBlockedCanary
):
    return _build_consumer_visible_hit_blocked_canary()


def _source_binding_with_overrides(
    overrides: Mapping[str, int | float] | None,
) -> dict[str, int | float | str]:
    source_binding = dict(SOURCE_BOUND_QUEUE_BUDGET)
    if overrides:
        source_binding.update(overrides)
    return source_binding


def _build_consumer_visible_hit_blocked_canary(
    *,
    request_source_binding_overrides: Mapping[str, int | float] | None = None,
) -> PayloadCacheLiveRuntimeAdapterPayloadIssueDemandHitPublicationBlockedCanary:
    envelope_binding = _source_binding_with_overrides(None)
    request_binding = _source_binding_with_overrides(request_source_binding_overrides)
    envelope = build_payload_cache_queue_budget_runtime_envelope(
        cell_count=int(envelope_binding["cell_count"]),
        event_timing_mode=str(envelope_binding["event_timing_mode"]),
        first_model_passing_capacity=int(
            envelope_binding["first_model_passing_capacity"],
        ),
        first_model_passing_issue_lead_tokens=int(
            envelope_binding["first_model_passing_issue_lead_tokens"],
        ),
        first_model_passing_queue_deadline_us=float(
            envelope_binding["first_model_passing_queue_deadline_us"],
        ),
        first_model_passing_lookahead_us=float(
            envelope_binding["first_model_passing_lookahead_us"],
        ),
        shifted_issue_accounting_enabled=True,
        shifted_issue_accounted_packet_count=int(
            envelope_binding["shifted_issue_accounted_packet_count"],
        ),
        shifted_issue_unique_issue_key_count=int(
            envelope_binding["shifted_issue_unique_issue_key_count"],
        ),
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
    toggle = build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary(
        payloadless,
    )
    request = build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
        toggle,
        request_source=REQUEST_SOURCE,
        source_issue_packet_count=int(
            request_binding["shifted_issue_accounted_packet_count"],
        ),
        source_issue_unique_key_count=int(
            request_binding["shifted_issue_unique_issue_key_count"],
        ),
        source_queue_budget_capacity=int(
            request_binding["first_model_passing_capacity"],
        ),
        source_issue_lead_tokens=int(
            request_binding["first_model_passing_issue_lead_tokens"],
        ),
        source_queue_deadline_us=float(
            request_binding["first_model_passing_queue_deadline_us"],
        ),
    )
    issue_plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        request,
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        issue_plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    submit = build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
        entry,
    )
    admission = (
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )
    )
    dispatch = (
        build_payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary(
            admission,
        )
    )
    command = build_payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run(
        dispatch,
    )
    transport = (
        build_payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary(
            command,
        )
    )
    worker = (
        build_payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary(
            transport,
        )
    )
    copy_descriptor = (
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run(
            worker,
        )
    )
    copy_submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary(
            copy_descriptor,
        )
    )
    copy_dispatch = (
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary(
            copy_submit,
        )
    )
    copy_execution = (
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary(
            copy_dispatch,
        )
    )
    completion = (
        build_payload_cache_live_runtime_adapter_payload_issue_copy_completion_blocked_canary(
            copy_execution,
        )
    )
    ready = build_payload_cache_live_runtime_adapter_payload_issue_ready_credit_blocked_canary(
        completion,
    )
    residency = (
        build_payload_cache_live_runtime_adapter_payload_issue_residency_update_blocked_canary(
            ready,
        )
    )
    deref = build_payload_cache_live_runtime_adapter_payload_issue_payload_deref_blocked_canary(
        residency,
    )
    return build_payload_cache_live_runtime_adapter_payload_issue_demand_hit_publication_blocked_canary(
        deref,
    )


def _request_matches_envelope_source_binding(
    payload: Mapping[str, Any],
    source_binding: Mapping[str, int | float],
) -> bool:
    return (
        payload.get("request_source") == REQUEST_SOURCE
        and payload.get("source_issue_packet_count")
        == source_binding["shifted_issue_accounted_packet_count"]
        and payload.get("source_issue_unique_key_count")
        == source_binding["shifted_issue_unique_issue_key_count"]
        and payload.get("source_queue_budget_capacity")
        == source_binding["first_model_passing_capacity"]
        and payload.get("source_issue_lead_tokens")
        == source_binding["first_model_passing_issue_lead_tokens"]
        and payload.get("source_queue_deadline_us")
        == source_binding["first_model_passing_queue_deadline_us"]
    )


def build_report(
    *,
    request_source_binding_overrides: Mapping[str, int | float] | None = None,
) -> dict[str, Any]:
    canary = _build_consumer_visible_hit_blocked_canary(
        request_source_binding_overrides=request_source_binding_overrides,
    )
    payload = canary.as_dict()
    failures: list[str] = []
    request_matches_envelope_source_binding = _request_matches_envelope_source_binding(
        payload,
        SOURCE_BOUND_QUEUE_BUDGET,
    )
    expected = {
        "stage": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_demand_hit_publication_blocked_canary"
        ),
        "payload_issue_demand_hit_publication_schema": (
            "payload_cache_runtime_payload_issue_demand_hit_publication_v1"
        ),
        "payload_issue_demand_hit_publication_canary_created": True,
        "payload_issue_payload_deref_consumed": True,
        "demand_hit_publication_checked": True,
        "demand_hit_publication_rejected": True,
        "demand_hit_publication_allowed": False,
        "demand_hit_published": False,
        "consumer_visible_payload_hit": False,
        "prefetched_demand_hit": False,
        "payload_deref_attempted": False,
        "payload_handle_deref_attempted": False,
        "payload_marked_resident": False,
        "resident_payload_ready": False,
        "ready_credit_granted": False,
        "ready_before_demand_credit_granted": False,
        "real_payload_ready": False,
        "copy_completed": False,
        "request_source": "queue_budget_first_model_passing_cell",
        "requested_payload_bytes": 64,
        "source_issue_packet_count": 28,
        "source_issue_unique_key_count": 16,
        "source_queue_budget_capacity": 4096,
        "source_issue_lead_tokens": 8,
        "source_queue_deadline_us": 100.0,
        "decision": "blocked",
        "block_reason": "payload_transfer_disabled",
        "execution_mode": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_demand_hit_publication_blocked_canary"
        ),
        "live_payload_runtime_enabled": False,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "live_runtime_instantiated": False,
    }
    if not request_matches_envelope_source_binding:
        failures.append("request_source_binding_mismatch")
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            failures.append(f"{key}_mismatch")
    for key in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "command_packet_count",
        "transport_work_count",
        "transport_worker_dispatch_count",
        "copy_descriptor_count",
        "copy_completion_count",
        "ready_credit_count",
        "residency_update_count",
        "resident_payload_count",
        "payload_handle_deref_count",
        "demand_hit_publication_count",
        "consumer_visible_payload_hit_count",
        "demand_hit_count",
        "issued_payload_count",
        "payload_bytes",
        "resident_payload_bytes",
        "dereferenced_payload_bytes",
        "demand_hit_payload_bytes",
    ):
        if payload.get(key) != 0:
            failures.append(f"{key}_nonzero")

    return {
        "schema_version": 1,
        "passed": not failures,
        "failures": failures,
        "source": "payload_cache_consumer_visible_hit_blocked_gate",
        "artifact_kind": "payload_cache_consumer_visible_hit_blocked_gate",
        "cell_count": SOURCE_BOUND_QUEUE_BUDGET["cell_count"],
        "event_timing_mode": SOURCE_BOUND_QUEUE_BUDGET["event_timing_mode"],
        "first_model_passing_lookahead_us": SOURCE_BOUND_QUEUE_BUDGET[
            "first_model_passing_lookahead_us"
        ],
        "decision": payload["decision"],
        "block_reason": payload["block_reason"],
        "execution_mode": payload["execution_mode"],
        "request_source": payload["request_source"],
        "request_layer_idx": payload["request_layer_idx"],
        "request_expert_idx": payload["request_expert_idx"],
        "requested_payload_bytes": payload["requested_payload_bytes"],
        "request_matches_envelope_source_binding": (
            request_matches_envelope_source_binding
        ),
        "source_issue_packet_count": payload["source_issue_packet_count"],
        "source_issue_unique_key_count": payload["source_issue_unique_key_count"],
        "source_queue_budget_capacity": payload["source_queue_budget_capacity"],
        "source_issue_lead_tokens": payload["source_issue_lead_tokens"],
        "source_queue_deadline_us": payload["source_queue_deadline_us"],
        "payload_bytes": payload["payload_bytes"],
        "resident_payload_bytes": payload["resident_payload_bytes"],
        "dereferenced_payload_bytes": payload["dereferenced_payload_bytes"],
        "demand_hit_payload_bytes": payload["demand_hit_payload_bytes"],
        "issued_payload_count": payload["issued_payload_count"],
        "resident_payload_count": payload["resident_payload_count"],
        "demand_hit_count": payload["demand_hit_count"],
        "demand_hit_publication_count": payload["demand_hit_publication_count"],
        "consumer_visible_payload_hit_count": payload[
            "consumer_visible_payload_hit_count"
        ],
        "payload_deref_attempted": payload["payload_deref_attempted"],
        "payload_handle_deref_attempted": payload["payload_handle_deref_attempted"],
        "demand_hit_publication_allowed": payload["demand_hit_publication_allowed"],
        "demand_hit_published": payload["demand_hit_published"],
        "consumer_visible_payload_hit": payload["consumer_visible_payload_hit"],
        "prefetched_demand_hit": payload["prefetched_demand_hit"],
        "ready_credit": payload["ready_credit"],
        "ready_before_demand_credit": payload["ready_before_demand_credit"],
        "real_ready_credit_granted": payload["real_ready_credit_granted"],
        "live_payload_runtime_enabled": payload["live_payload_runtime_enabled"],
        "payload_transfer_runtime_enabled": payload[
            "payload_transfer_runtime_enabled"
        ],
        "payload_deref_allowed": payload["payload_deref_allowed"],
        "payload_deref_runtime_allowed": payload["payload_deref_runtime_allowed"],
        "kernel_arg_pass_allowed": payload["kernel_arg_pass_allowed"],
        "passed_to_kernel": payload["passed_to_kernel"],
        "changes_kernel_launch_args": payload["changes_kernel_launch_args"],
        "full_fetch_runtime_allowed": payload["full_fetch_runtime_allowed"],
        "uses_current_wna16_args": payload["uses_current_wna16_args"],
        "passes_current_wna16_args": payload["passes_current_wna16_args"],
        "measures_tpot": payload["measures_tpot"],
        "measures_vllm_latency": payload["measures_vllm_latency"],
        "live_runtime_instantiated": payload["live_runtime_instantiated"],
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
