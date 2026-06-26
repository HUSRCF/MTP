import json
from pathlib import Path

import torch
import pytest

from mtp_expert_prefetch.runtime import (
    AdmissionDecisionMasks,
    DescriptorOrderExecutionEvidence,
    DescriptorOrderRuntimeGate,
    OnlineShadowLogger,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PremapPayloadCacheProducerTransitionStatePacket,
    RuntimeShadowController,
    TileRequest,
    build_layer_tile_prior,
    build_premap_shadow_summary,
    hash_layer_tile_prior,
)
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowPolicyConfig,
    read_shadow_jsonl,
)
from mtp_expert_prefetch.tracing.vllm_router_trace import VllmRouterRecorder
from mtp_expert_prefetch.tracing.vllm_router_trace import (
    DecodeWorkloadTraceCollector,
    SharedExpertFusedGateUnsupportedError,
    _ACTIVE_DECODE_WORKLOAD_TRACE,
    _ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR,
    _add_premap_payload_cache_manager_snapshot_to_performance,
    _add_runtime_shadow_aggregate_to_performance,
    _apply_premap_payload_cache_measured_copy_envelope,
    _premap_kernel_arg_live_mutation_counters,
    _premap_payload_cache_export_nonempty_issue_summary,
    _premap_payload_cache_issue_hash,
    _premap_payload_cache_shifted_issue_runtime_shadow_summary,
    _record_premap_gpu_assignment_prelaunch_pointer_source_consumer_counters,
    _reset_premap_kernel_arg_live_mutation_counters,
    _set_premap_kernel_arg_live_mutation_counter_mode,
    _load_runtime_shadow_transition_matrix,
    _shared_expert_fused_gate_fallbackable,
    _run_shared_expert_output_gate_default_postprocess,
    _shared_expert_custom_gate_enabled,
    _shared_expert_fused_gate_unsupported,
    _unwrap_vllm_projection_output,
    set_active_runtime_shadow_controller,
    write_active_runtime_shadow_action_summary,
)


class _Sink:
    def __init__(self) -> None:
        self.events = []

    def write_outcome(self, event) -> None:
        self.events.append(event)

    def write_outcome_aggregate(self, event) -> None:
        self.events.append(event)

    def write_descriptor_order_min_summary(self, event) -> None:
        self.events.append(event)

    def write_premap_summary_from_descriptors(self, **kwargs):
        event = build_premap_shadow_summary(**kwargs)
        self.events.append(event)
        return event

    def write_premap_consumer_mapping(self, event) -> None:
        self.events.append(event)

    def write_descriptor_layer_timing(self, event) -> None:
        self.events.append(event)


class _OutcomeOnlySink:
    def __init__(self) -> None:
        self.events = []

    def write_outcome(self, event) -> None:
        self.events.append(event)


def test_recorder_adopts_decode_workload_token_provenance(tmp_path: Path):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_sample(3, {"id": "rec-3", "prompt_len": 100})
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[105],
        query_lens=[1],
        call_index=9,
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_premap_event_token_index=17,
        shadow_descriptor_order_event_token_index=19,
    )

    token = _ACTIVE_DECODE_WORKLOAD_TRACE.set(collector)
    try:
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2]], dtype=torch.long),
            topk_weights=torch.tensor([[0.7, 0.3]], dtype=torch.float32),
        )
    finally:
        _ACTIVE_DECODE_WORKLOAD_TRACE.reset(token)

    assert recorder.shadow_premap_event_token_index == 5
    assert recorder.shadow_descriptor_order_event_token_index == 5
    assert recorder.shadow_premap_event_token_index_source == (
        "decode_workload_collector"
    )
    assert recorder.shadow_descriptor_order_event_token_index_source == (
        "decode_workload_collector"
    )
    assert recorder.shadow_premap_event_sample_idx == 3
    assert recorder.shadow_premap_event_record_id == "rec-3"

    recorder.clear()
    assert recorder.shadow_premap_event_token_index == 17
    assert recorder.shadow_descriptor_order_event_token_index == 19
    assert recorder.shadow_premap_event_token_index_source == "config"
    assert recorder.shadow_descriptor_order_event_token_index_source == "config"
    assert recorder.shadow_premap_event_sample_idx is None
    assert recorder.shadow_premap_event_record_id is None


def test_collector_uses_input_ids_as_prompt_len_fallback(tmp_path: Path):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_sample(
        3,
        {"id": "rec-3"},
        torch.arange(100, dtype=torch.long),
    )
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[105],
        query_lens=[1],
        call_index=99,
    )

    assert collector.current_single_decode_token_index() == 5
    assert collector.current_single_decode_sample_idx() == 3
    assert collector.current_single_decode_record_id() == "rec-3"


def test_collector_batch_uses_input_ids_as_prompt_len_fallback(tmp_path: Path):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_batch_samples(
        [
            (1, {"id": "rec-1"}, torch.arange(100, dtype=torch.long), "a"),
            (2, {"id": "rec-2"}, torch.arange(200, dtype=torch.long), "b"),
        ]
    )
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[101, 202],
        query_lens=[1, 1],
        call_index=99,
    )

    assert collector._last_decode_generated_token_indices == [1, 2]


def test_recorder_does_not_adopt_batched_decode_token_provenance(tmp_path: Path):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_batch_samples(
        [
            (1, {"id": "rec-1", "prompt_len": 100}, None, None),
            (2, {"id": "rec-2", "prompt_len": 200}, None, None),
        ]
    )
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[101, 202],
        query_lens=[1, 1],
        call_index=9,
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_premap_event_token_index=17,
        shadow_descriptor_order_event_token_index=19,
    )

    token = _ACTIVE_DECODE_WORKLOAD_TRACE.set(collector)
    try:
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2], [3, 0]], dtype=torch.long),
            topk_weights=torch.tensor(
                [[0.7, 0.3], [0.6, 0.4]],
                dtype=torch.float32,
            ),
        )
    finally:
        _ACTIVE_DECODE_WORKLOAD_TRACE.reset(token)

    assert recorder.shadow_premap_event_token_index == 17
    assert recorder.shadow_descriptor_order_event_token_index == 19
    assert recorder.shadow_premap_event_token_index_source == "config"
    assert recorder.shadow_descriptor_order_event_token_index_source == "config"
    assert recorder.shadow_premap_event_sample_idx is None
    assert recorder.shadow_premap_event_record_id is None


def test_recorder_resets_stale_decode_token_on_batched_fallback(tmp_path: Path):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_sample(3, {"id": "rec-3", "prompt_len": 100})
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[105],
        query_lens=[1],
        call_index=9,
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_premap_event_token_index=17,
        shadow_descriptor_order_event_token_index=19,
    )

    token = _ACTIVE_DECODE_WORKLOAD_TRACE.set(collector)
    try:
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2]], dtype=torch.long),
            topk_weights=torch.tensor([[0.7, 0.3]], dtype=torch.float32),
        )
        assert recorder.shadow_premap_event_token_index == 5
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2], [3, 0]], dtype=torch.long),
            topk_weights=torch.tensor(
                [[0.7, 0.3], [0.6, 0.4]],
                dtype=torch.float32,
            ),
        )
    finally:
        _ACTIVE_DECODE_WORKLOAD_TRACE.reset(token)

    assert recorder.shadow_premap_event_token_index == 17
    assert recorder.shadow_descriptor_order_event_token_index == 19
    assert recorder.shadow_premap_event_token_index_source == "config"
    assert recorder.shadow_descriptor_order_event_token_index_source == "config"
    assert recorder.shadow_premap_event_sample_idx is None
    assert recorder.shadow_premap_event_record_id is None


def test_collector_clears_decode_token_when_prefill_filtered(tmp_path: Path):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_sample(3, {"id": "rec-3", "prompt_len": 100})
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[105],
        query_lens=[1],
        call_index=9,
    )
    assert collector.current_single_decode_token_index() == 5

    collector.clear_decode_token_provenance()
    assert collector.current_single_decode_token_index() is None


def test_collector_skip_clears_stale_decode_token(tmp_path: Path):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_sample(3, {"id": "rec-3", "prompt_len": 100})
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[105],
        query_lens=[1],
        call_index=9,
    )
    assert collector.current_single_decode_token_index() == 5

    collector._skip("max_rows")
    assert collector.current_single_decode_token_index() == 5


def test_collector_max_rows_refreshes_live_token_without_writing(tmp_path: Path):
    class _Builder:
        block_size = 16
        num_heads_q = 8
        num_heads_kv = 2
        headdim = 128
        sliding_window = None

    class _Metadata:
        query_start_loc = torch.tensor([0, 1], dtype=torch.int32)
        seq_lens = torch.tensor([105], dtype=torch.int32)
        block_table_tensor = torch.tensor([[7]], dtype=torch.int32)
        seq_start_loc = torch.tensor([0, 1], dtype=torch.int32)
        slot_mapping = torch.tensor([123], dtype=torch.int64)
        num_reqs = 1

    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
        max_rows=0,
    )
    collector._handle = object()
    collector.set_sample(3, {"id": "rec-3", "prompt_len": 100})

    collector.record_common_attention_metadata(
        builder=_Builder(),
        common_attn_metadata=_Metadata(),
    )

    assert collector.rows_written == 0
    assert collector.skipped_rows == 1
    assert collector.stats()["skip_reasons"] == {"max_rows": 1}
    assert collector.current_single_decode_token_index() == 5
    assert collector.current_single_decode_sample_idx() == 3
    assert collector.current_single_decode_record_id() == "rec-3"


def test_collector_non_max_rows_skip_clears_stale_decode_token(tmp_path: Path):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_sample(3, {"id": "rec-3", "prompt_len": 100})
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[105],
        query_lens=[1],
        call_index=9,
    )
    assert collector.current_single_decode_token_index() == 5

    collector._skip("phase_filter")
    assert collector.current_single_decode_token_index() is None


def test_collector_exception_path_clears_stale_decode_token(tmp_path: Path):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_sample(3, {"id": "rec-3", "prompt_len": 100})
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[105],
        query_lens=[1],
        call_index=9,
    )
    assert collector.current_single_decode_token_index() == 5

    def _boom(*, builder, common_attn_metadata):
        collector._remember_decode_token_indices(
            phase="decode",
            seq_lens=[106],
            query_lens=[1],
            call_index=10,
        )
        raise RuntimeError("synthetic metadata failure")

    collector._handle = object()
    collector._record_common_attention_metadata_impl = _boom
    collector.record_common_attention_metadata(
        builder=object(),
        common_attn_metadata=object(),
    )
    assert collector.error_count == 1
    assert collector.current_single_decode_token_index() is None


def test_native_input_export_refreshes_decode_token_without_record_topk(
    tmp_path: Path,
):
    class _Table:
        row_count = 1
        column_count = 4
        object_hash = "table-hash"
        schema_hash = PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        payload_bytes = 0
        ready_credit = False
        changes_router = False
        changes_descriptor_order = False
        passed_to_kernel = False
        changes_kernel_launch_args = False

        def to_native_typed_consumer_input_dict(self):
            return {
                "descriptor_ptr": [11],
                "packed_weight_descriptor": [33],
                "scale_metadata_handle": [55],
                "aux_metadata_handle": [0],
                "expert_id": [3],
                "address_key_hash": [77],
                "_meta": {
                    "schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
                    "row_count": 1,
                    "column_count": 4,
                    "table_object_hash": "table-hash",
                    "payload_bytes": 0,
                    "ready_credit": False,
                    "changes_router": False,
                    "changes_descriptor_order": False,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                },
            }

    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_sample(4, {"id": "rec-4", "prompt_len": 128})
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[131],
        query_lens=[1],
        call_index=10,
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_premap_native_typed_consumer_input_export_enabled=True,
        shadow_premap_native_typed_consumer_input_export_dir=str(tmp_path),
        shadow_premap_native_typed_consumer_input_export_max_tables=1,
    )

    token = _ACTIVE_DECODE_WORKLOAD_TRACE.set(collector)
    try:
        path = recorder._maybe_export_native_typed_consumer_input(
            _Table(),
            layer_id=0,
        )
    finally:
        _ACTIVE_DECODE_WORKLOAD_TRACE.reset(token)

    assert path is not None
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["_export_context"]["token_index"] == 3
    assert payload["_export_context"]["token_index_source"] == (
        "decode_workload_collector"
    )
    assert payload["_export_context"]["sample_idx"] == 4
    assert payload["_export_context"]["record_id"] == "rec-4"


def test_producer_state_packet_export_refreshes_decode_token_without_record_topk(
    tmp_path: Path,
):
    collector = DecodeWorkloadTraceCollector(
        path=tmp_path / "decode.jsonl",
        run_id="unit",
    )
    collector.set_sample(5, {"id": "rec-5", "prompt_len": 256})
    collector._remember_decode_token_indices(
        phase="decode",
        seq_lens=[260],
        query_lens=[1],
        call_index=12,
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_num_experts=8,
        shadow_premap_payload_cache_producer_state_packet_export_enabled=True,
        shadow_premap_payload_cache_producer_state_packet_export_dir=str(tmp_path),
        shadow_premap_payload_cache_producer_state_packet_export_max_packets=1,
    )
    packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=0,
        previous_experts=(1,),
        current_experts=(2,),
        state_owner="producer",
        issue_source="prelaunch_observed_transition_premap_shadow",
        transition_summary_mode="matrix_topk",
        transition_topk_count=1,
        max_num_experts=8,
    )

    token = _ACTIVE_DECODE_WORKLOAD_TRACE.set(collector)
    try:
        path = recorder._maybe_export_premap_payload_cache_producer_state_packet(
            packet,
            layer_id=0,
        )
    finally:
        _ACTIVE_DECODE_WORKLOAD_TRACE.reset(token)

    assert path is not None
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["_export_context"]["token_index"] == 4
    assert payload["_export_context"]["token_index_source"] == (
        "decode_workload_collector"
    )
    assert payload["_export_context"]["sample_idx"] == 5
    assert payload["_export_context"]["record_id"] == "rec-5"


def test_premap_payload_cache_manager_id_keeps_resident_legacy_format():
    resident = VllmRouterRecorder(
        top_k=2,
        shadow_emit_premap_payload_cache_manager_counters=True,
    )
    resident_manager = resident._ensure_premap_payload_cache_manager()
    resident_manager_id = resident._premap_payload_cache_manager_id()

    assert resident_manager is not None
    assert resident_manager_id == f"controlled_expert_payload_cache:{id(resident_manager)}"
    assert ":resident:" not in str(resident_manager_id)

    ready_time = VllmRouterRecorder(
        top_k=2,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_mode="ready_time",
        shadow_premap_payload_cache_manager_service_us_per_issue=1.0,
    )
    ready_time_manager = ready_time._ensure_premap_payload_cache_manager()
    ready_time_manager_id = ready_time._premap_payload_cache_manager_id()

    assert ready_time_manager is not None
    assert ready_time_manager_id == (
        f"controlled_expert_payload_cache:ready_time:{id(ready_time_manager)}"
    )


def test_premap_payload_cache_measured_copy_envelope_overrides_ready_time_options(
    tmp_path,
):
    measured_copy = tmp_path / "measured_copy.json"
    measured_copy.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "direction": "h2d",
                        "pinned": False,
                        "experts": 4,
                        "p95_ms": 0.4,
                        "p95_gbps": 9.0,
                    },
                    {
                        "direction": "h2d",
                        "pinned": True,
                        "experts": 8,
                        "p95_ms": 0.8,
                        "p95_gbps": 12.5,
                    },
                    {
                        "direction": "d2h",
                        "pinned": True,
                        "experts": 8,
                        "p95_ms": 0.1,
                        "p95_gbps": 99.0,
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    options = {
        "premap_payload_cache_manager_measured_copy_json": str(measured_copy),
        "premap_payload_cache_manager_measured_copy_stat": "p95",
        "premap_payload_cache_manager_measured_copy_experts": 6,
        "premap_payload_cache_manager_measured_copy_pinned": "true",
        "premap_payload_cache_manager_service_us_per_issue": 999.0,
        "premap_payload_cache_manager_queue_batch_size": 1,
    }

    resolved = _apply_premap_payload_cache_measured_copy_envelope(
        options,
        project_root=tmp_path,
    )

    assert resolved["premap_payload_cache_manager_service_us_per_issue"] == 100.0
    assert resolved["premap_payload_cache_manager_service_us_per_batch"] == 0.0
    assert resolved["premap_payload_cache_manager_queue_batch_size"] == 8
    assert resolved["premap_payload_cache_manager_measured_copy_selected_experts"] == 8
    assert resolved["premap_payload_cache_manager_measured_copy_requested_experts"] == 6
    assert resolved["premap_payload_cache_manager_measured_copy_pinned"] is True
    assert resolved["premap_payload_cache_manager_measured_copy_us_per_batch"] == 800.0
    assert resolved["premap_payload_cache_manager_measured_copy_us_per_issue"] == 100.0
    assert (
        resolved["premap_payload_cache_manager_measured_copy_effective_gbps"] == 12.5
    )


def test_premap_payload_cache_measured_copy_envelope_is_noop_without_path(tmp_path):
    options = {"premap_payload_cache_manager_service_us_per_issue": 7.0}

    resolved = _apply_premap_payload_cache_measured_copy_envelope(
        options,
        project_root=tmp_path,
    )

    assert resolved is options
    assert resolved["premap_payload_cache_manager_service_us_per_issue"] == 7.0


def test_premap_payload_cache_measured_copy_envelope_allows_any_pinned(tmp_path):
    measured_copy = tmp_path / "measured_copy_any.json"
    measured_copy.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "direction": "h2d",
                        "pinned": False,
                        "experts": 4,
                        "p50_ms": 0.2,
                        "p50_gbps": 10.0,
                    },
                    {
                        "direction": "h2d",
                        "pinned": True,
                        "experts": 16,
                        "p50_ms": 2.0,
                        "p50_gbps": 8.0,
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    resolved = _apply_premap_payload_cache_measured_copy_envelope(
        {
            "premap_payload_cache_manager_measured_copy_json": str(measured_copy),
            "premap_payload_cache_manager_measured_copy_stat": "p50",
            "premap_payload_cache_manager_measured_copy_experts": 5,
            "premap_payload_cache_manager_measured_copy_pinned": "any",
        },
        project_root=tmp_path,
    )

    assert resolved["premap_payload_cache_manager_measured_copy_selected_experts"] == 4
    assert resolved["premap_payload_cache_manager_measured_copy_pinned"] is False
    assert resolved["premap_payload_cache_manager_service_us_per_issue"] == 50.0


def test_premap_payload_cache_measured_copy_envelope_reports_bad_input(tmp_path):
    no_h2d = tmp_path / "no_h2d.json"
    no_h2d.write_text(json.dumps({"rows": [{"direction": "d2h"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="No matching H2D"):
        _apply_premap_payload_cache_measured_copy_envelope(
            {"premap_payload_cache_manager_measured_copy_json": str(no_h2d)},
            project_root=tmp_path,
        )

    missing_stat = tmp_path / "missing_stat.json"
    missing_stat.write_text(
        json.dumps({"rows": [{"direction": "h2d", "pinned": True, "experts": 1}]}),
        encoding="utf-8",
    )

    with pytest.raises(KeyError, match="p95_ms"):
        _apply_premap_payload_cache_measured_copy_envelope(
            {"premap_payload_cache_manager_measured_copy_json": str(missing_stat)},
            project_root=tmp_path,
        )


def test_runtime_shadow_transition_matrix_loader_reports_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="transition_matrix_path does not exist"):
        _load_runtime_shadow_transition_matrix(
            options={
                "transition_summary_mode": "matrix_topk",
                "transition_matrix_path": "missing_transition.pt",
            },
            project_root=tmp_path,
        )


def test_runtime_shadow_transition_matrix_loader_skips_path_for_previous_topk(tmp_path):
    assert (
        _load_runtime_shadow_transition_matrix(
            options={
                "transition_summary_mode": "previous_topk",
                "transition_matrix_path": "missing_transition.pt",
            },
            project_root=tmp_path,
        )
        is None
    )


def test_premap_payload_cache_manager_snapshot_flattens_without_jsonl_rows():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
    )
    manager = recorder._ensure_premap_payload_cache_manager()
    assert manager is not None
    manager.issue_prefetch(0, 1)
    manager.demand(0, 1)
    manager.demand(0, 2)

    performance = {}
    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test",
    )

    assert performance["runtime_shadow_premap_payload_cache_direct_snapshot_present"]
    assert performance["runtime_shadow_premap_payload_cache_direct_snapshot_source"] == (
        "unit_test"
    )
    assert performance["runtime_shadow_premap_payload_cache_direct_capacity"] == 4
    assert (
        performance["runtime_shadow_premap_payload_cache_direct_runtime_stage"]
        == "online_payload_cache_accounting_only"
    )
    assert performance["runtime_shadow_premap_payload_cache_direct_payload_bytes"] == 0
    assert (
        performance["runtime_shadow_premap_payload_cache_direct_ready_credit"] is False
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_real_ready_credit_granted"
        ]
        is False
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_payload_transfer_runtime_enabled"
        ]
        is False
    )
    assert performance["runtime_shadow_premap_payload_cache_direct_issue_sources"] == [
        "previous_token_transition_premap_shadow"
    ]
    assert (
        performance["runtime_shadow_premap_payload_cache_direct_demand_on_consumer"]
        is True
    )
    assert performance["runtime_shadow_premap_payload_cache_direct_issued_fetch_count"] == 1
    assert performance["runtime_shadow_premap_payload_cache_direct_used_fetch_count"] == 1
    assert performance["runtime_shadow_premap_payload_cache_direct_demand_count"] == 2
    assert performance["runtime_shadow_premap_payload_cache_direct_demand_hit_count"] == 1
    assert performance["runtime_shadow_premap_payload_cache_direct_demand_miss_count"] == 1
    assert performance["runtime_shadow_premap_payload_cache_direct_demand_hit_rate"] == 0.5
    assert (
        performance["runtime_shadow_premap_payload_cache_direct_used_per_issued_fetch"]
        == 1.0
    )
    assert (
        performance["runtime_shadow_premap_payload_cache_direct_ready_late_miss_rate"]
        == 0.0
    )
    participation_prefix = (
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_"
    )
    assert performance[f"{participation_prefix}present"] is True
    assert (
        performance[f"{participation_prefix}stage"]
        == "online_payload_cache_runtime_participation_dry_run"
    )
    assert (
        performance[f"{participation_prefix}status"]
        == "accounting_only_not_ready_time_manager:resident"
    )
    assert (
        performance[f"{participation_prefix}candidate_reason"]
        == performance[
            "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate_reason"
        ]
    )
    assert performance[f"{participation_prefix}consumes_manager_snapshot"] is True
    assert performance[f"{participation_prefix}payload_bytes"] == 0
    assert performance[f"{participation_prefix}ready_credit"] is False
    assert performance[f"{participation_prefix}real_ready_credit_granted"] is False
    assert performance[f"{participation_prefix}kernel_arg_pass_allowed"] is False
    assert performance[f"{participation_prefix}changes_kernel_launch_args"] is False
    assert performance[f"{participation_prefix}full_fetch_runtime_allowed"] is False
    assert (
        performance[f"{participation_prefix}payload_transfer_runtime_enabled"]
        is False
    )
    assert performance[f"{participation_prefix}issued_fetch_count"] == 1
    assert performance[f"{participation_prefix}used_fetch_count"] == 1
    assert performance[f"{participation_prefix}demand_count"] == 2
    assert performance[f"{participation_prefix}demand_hit_count"] == 1
    assert performance[f"{participation_prefix}issue_sources"] == [
        "previous_token_transition_premap_shadow"
    ]
    assert not performance[
        "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate"
    ]
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate_reason"
        ].startswith("not_ready_time_manager:")
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_transition_issue_attempt_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_transition_issue_error_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_transition_issue_last_error"
        ]
        is None
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_transition_native_packet_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_transition_native_packet_ready_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_transition_native_packet_last_hash"
        ]
        is None
    )


def test_premap_payload_cache_manager_snapshot_reports_missing_enabled_manager():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
    )

    performance = {}
    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_missing",
    )

    assert (
        performance["runtime_shadow_premap_payload_cache_direct_snapshot_present"]
        is False
    )
    assert performance["runtime_shadow_premap_payload_cache_direct_snapshot_source"] == (
        "unit_test_missing"
    )
    assert "runtime_shadow_premap_payload_cache_direct_demand_count" not in performance


def test_premap_payload_cache_manager_snapshot_marks_unused_fetch_not_candidate():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_mode="ready_time",
    )
    manager = recorder._ensure_premap_payload_cache_manager()
    assert manager is not None
    manager.issue_prefetch(0, 1, arrival_us=0.0)
    manager.demand(0, 2, arrival_us=1.0)

    performance = {}
    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_unused_fetch",
    )

    assert (
        performance["runtime_shadow_premap_payload_cache_direct_issued_fetch_count"]
        == 1
    )
    assert performance["runtime_shadow_premap_payload_cache_direct_used_fetch_count"] == 0
    assert (
        performance["runtime_shadow_premap_payload_cache_direct_used_per_issued_fetch"]
        == 0.0
    )
    assert not performance[
        "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate"
    ]
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate_reason"
        ]
        == "no_used_fetch"
    )


def test_premap_payload_cache_manager_snapshot_marks_no_issue_not_candidate():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_mode="ready_time",
    )
    manager = recorder._ensure_premap_payload_cache_manager()
    assert manager is not None
    manager.demand(0, 2, arrival_us=1.0)

    performance = {}
    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_no_issue",
    )

    assert (
        performance["runtime_shadow_premap_payload_cache_direct_issued_fetch_count"]
        == 0
    )
    assert not performance[
        "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate"
    ]
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate_reason"
        ]
        == "no_issued_fetch"
    )


def test_premap_payload_cache_manager_snapshot_marks_all_late_not_candidate():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_mode="ready_time",
        shadow_premap_payload_cache_manager_service_us_per_issue=10.0,
        shadow_premap_payload_cache_manager_queue_batch_size=1,
        shadow_premap_payload_cache_manager_queue_deadline_us=1.0,
    )
    manager = recorder._ensure_premap_payload_cache_manager()
    assert manager is not None
    manager.issue_prefetch(0, 1, arrival_us=0.0)
    manager.demand(0, 1, arrival_us=1.0)

    performance = {}
    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_all_late",
    )

    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_ready_late_miss_count"
        ]
        == 1
    )
    assert (
        performance["runtime_shadow_premap_payload_cache_direct_ready_late_miss_rate"]
        == 1.0
    )
    assert not performance[
        "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate"
    ]
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate_reason"
        ]
        == "all_demands_ready_late"
    )


def test_premap_payload_cache_manager_snapshot_flattens_ready_time_fields():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_mode="ready_time",
        shadow_premap_payload_cache_manager_service_us_per_issue=5.0,
        shadow_premap_payload_cache_manager_queue_batch_size=2,
        shadow_premap_payload_cache_manager_queue_deadline_us=10.0,
    )
    manager = recorder._ensure_premap_payload_cache_manager()
    assert manager is not None
    manager.issue_prefetch(0, 1, arrival_us=0.0)
    manager.issue_prefetch(0, 2, arrival_us=1.0)
    manager.demand(0, 1, arrival_us=20.0)

    performance = {}
    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_ready_time",
    )

    assert performance["runtime_shadow_premap_payload_cache_direct_manager_mode"] == (
        "ready_time"
    )
    assert (
        performance["runtime_shadow_premap_payload_cache_direct_runtime_stage"]
        == "online_ready_time_payload_cache_accounting_only"
    )
    assert performance["runtime_shadow_premap_payload_cache_direct_queue_batch_size"] == 2
    assert performance["runtime_shadow_premap_payload_cache_direct_queue_deadline_us"] == (
        10.0
    )
    assert performance["runtime_shadow_premap_payload_cache_direct_queue_batch_count"] >= 1
    assert (
        performance["runtime_shadow_premap_payload_cache_direct_queue_service_us"]
        >= 10.0
    )
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_late_completion_unused_count"
        ]
        >= 0
    )
    assert performance[
        "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate"
    ]
    participation_prefix = (
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_"
    )
    assert (
        performance[f"{participation_prefix}stage"]
        == "online_ready_time_payload_cache_runtime_participation_dry_run"
    )
    assert (
        performance[f"{participation_prefix}status"]
        == "ready_time_candidate_requires_lab_gate"
    )
    assert (
        performance[f"{participation_prefix}candidate_reason"]
        == performance[
            "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate_reason"
        ]
    )
    assert performance[f"{participation_prefix}queue_batch_size"] == 2
    assert performance[f"{participation_prefix}queue_deadline_us"] == 10.0
    assert performance[f"{participation_prefix}payload_bytes"] == 0
    assert performance[f"{participation_prefix}full_fetch_runtime_allowed"] is False
    plan_prefix = "runtime_shadow_premap_payload_cache_direct_runtime_plan_"
    assert (
        performance[f"{plan_prefix}stage"]
        == "payload_cache_runtime_plan_lab_gate_dry_run"
    )
    assert (
        performance[f"{plan_prefix}status"]
        == "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    assert performance[f"{plan_prefix}participation_status"] == (
        "ready_time_candidate_requires_lab_gate"
    )
    assert performance[f"{plan_prefix}consumes_participation"] is True
    assert performance[f"{plan_prefix}live_payload_runtime_enabled"] is False
    assert performance[f"{plan_prefix}planned_issue_count"] == 0
    assert performance[f"{plan_prefix}payload_bytes"] == 0
    assert performance[f"{plan_prefix}ready_credit"] is False
    assert performance[f"{plan_prefix}kernel_arg_pass_allowed"] is False
    assert performance[f"{plan_prefix}changes_kernel_launch_args"] is False
    assert performance[f"{plan_prefix}full_fetch_runtime_allowed"] is False
    execution_prefix = "runtime_shadow_premap_payload_cache_direct_runtime_execution_"
    assert (
        performance[f"{execution_prefix}stage"]
        == "payload_cache_runtime_execution_lab_gate_dry_run"
    )
    assert performance[f"{execution_prefix}status"] == (
        f"blocked_by_runtime_plan:{performance[f'{plan_prefix}status']}"
    )
    assert performance[f"{execution_prefix}plan_status"] == performance[
        f"{plan_prefix}status"
    ]
    assert performance[f"{execution_prefix}consumes_plan"] is True
    assert performance[f"{execution_prefix}decision"] == "blocked"
    assert performance[f"{execution_prefix}block_reason"] == performance[
        f"{plan_prefix}status"
    ]
    assert (
        performance[f"{execution_prefix}execution_mode"]
        == "payloadless_lab_gate_dry_run"
    )
    assert performance[f"{execution_prefix}live_payload_runtime_enabled"] is False
    assert performance[f"{execution_prefix}payload_transfer_runtime_enabled"] is False
    assert performance[f"{execution_prefix}issued_payload_count"] == 0
    assert performance[f"{execution_prefix}payload_bytes"] == 0
    assert performance[f"{execution_prefix}ready_credit"] is False
    assert performance[f"{execution_prefix}real_ready_credit_granted"] is False
    assert performance[f"{execution_prefix}kernel_arg_pass_allowed"] is False
    assert performance[f"{execution_prefix}changes_kernel_launch_args"] is False
    assert performance[f"{execution_prefix}full_fetch_runtime_allowed"] is False
    assert (
        performance[
            "runtime_shadow_premap_payload_cache_direct_full_fetch_ready_time_gate_candidate_reason"
        ]
        == "candidate_requires_ready_time_gate"
    )


def test_premap_payload_cache_prelaunch_observed_transition_issues_before_next_demand():
    transition = torch.zeros((1, 1, 4, 4), dtype=torch.float32)
    transition[0, 0, 1, 2] = 1.0
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_issue_sources=(
            "prelaunch_observed_transition_premap_shadow",
        ),
        shadow_transition_premap_source=(
            "prelaunch_observed_transition_premap_shadow"
        ),
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=1,
        shadow_transition_matrix=transition,
    )

    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=0,
        active_experts=[1],
    )
    manager = recorder._ensure_premap_payload_cache_manager()
    assert manager is not None
    first = manager.snapshot()
    assert first.issued_fetch_count == 0
    assert first.demand_count == 1
    assert first.demand_hit_count == 0

    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=0,
        active_experts=[2],
    )
    second = manager.snapshot()
    assert second.issued_fetch_count == 1
    assert second.demand_count == 2
    assert second.demand_hit_count == 1
    assert second.used_fetch_count == 1
    assert recorder._premap_payload_cache_transition_issue_attempt_count == 2
    assert recorder._premap_payload_cache_transition_issue_previous_nonempty_count == 1
    assert recorder._premap_payload_cache_transition_issue_descriptor_count == 1
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 1
    assert recorder._premap_payload_cache_transition_issue_last_candidate_first_expert == 2
    assert recorder._premap_payload_cache_transition_issue_last_candidate_last_expert == 2
    assert (
        recorder._premap_payload_cache_transition_issue_last_candidate_hash
        == _premap_payload_cache_issue_hash([2])
    )
    assert recorder._premap_payload_cache_transition_issue_error_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_error is None
    assert recorder._premap_payload_cache_transition_consumer_update_count == 2
    assert recorder._premap_payload_cache_transition_producer_update_count == 0


def test_premap_payload_cache_producer_transition_owner_issues_before_next_demand(
    tmp_path: Path,
):
    transition = torch.zeros((1, 1, 4, 4), dtype=torch.float32)
    transition[0, 0, 1, 2] = 1.0
    export_path_list: list[str] = []
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_issue_sources=(
            "prelaunch_observed_transition_premap_shadow",
        ),
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_transition_premap_source=(
            "prelaunch_observed_transition_premap_shadow"
        ),
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=1,
        shadow_transition_matrix=transition,
        shadow_premap_payload_cache_producer_state_packet_export_enabled=True,
        shadow_premap_payload_cache_producer_state_packet_export_dir=str(tmp_path),
        shadow_premap_payload_cache_producer_state_packet_export_max_packets=2,
        shadow_premap_payload_cache_producer_state_packet_export_paths=(
            export_path_list
        ),
    )
    recorder.request_id = "producer/sample"
    recorder.sequence_id = 7
    recorder.shadow_premap_event_token_index = 11

    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.tensor([0], dtype=torch.long),
        expert_ids=torch.tensor([1], dtype=torch.long),
        num_tokens_post_padded=torch.tensor([1], dtype=torch.long),
        block_size=1,
    )
    manager = recorder._ensure_premap_payload_cache_manager()
    assert manager is not None
    first = manager.snapshot()
    assert first.issued_fetch_count == 0
    assert first.demand_count == 1
    assert first.demand_hit_count == 0

    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.tensor([0], dtype=torch.long),
        expert_ids=torch.tensor([2], dtype=torch.long),
        num_tokens_post_padded=torch.tensor([1], dtype=torch.long),
        block_size=1,
    )
    second = manager.snapshot()
    assert second.issued_fetch_count == 1
    assert second.demand_count == 2
    assert second.demand_hit_count == 1
    assert second.used_fetch_count == 1
    assert recorder._premap_payload_cache_transition_issue_attempt_count == 2
    assert recorder._premap_payload_cache_transition_issue_previous_nonempty_count == 1
    assert recorder._premap_payload_cache_transition_issue_descriptor_count == 1
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 1
    assert recorder._premap_payload_cache_transition_issue_last_candidate_first_expert == 2
    assert recorder._premap_payload_cache_transition_issue_last_candidate_last_expert == 2
    assert (
        recorder._premap_payload_cache_transition_issue_last_candidate_hash
        == _premap_payload_cache_issue_hash([2])
    )
    assert recorder._premap_payload_cache_transition_issue_error_count == 0
    assert recorder._premap_payload_cache_transition_consumer_update_count == 0
    assert recorder._premap_payload_cache_transition_producer_update_count == 2
    assert recorder._premap_payload_cache_transition_native_packet_count == 2
    assert recorder._premap_payload_cache_transition_native_packet_ready_count == 2
    assert recorder._premap_payload_cache_transition_native_packet_last_hash is not None
    assert recorder._premap_payload_cache_transition_native_packet_last_previous_count == 1
    assert recorder._premap_payload_cache_transition_native_packet_last_current_count == 1
    export_paths = sorted(
        tmp_path.glob("premap_payload_cache_producer_state_packet_*.json")
    )
    assert len(export_paths) == 2
    assert "producer_sample" in export_paths[0].name
    first_payload = json.loads(export_paths[0].read_text(encoding="utf-8"))
    second_payload = json.loads(export_paths[1].read_text(encoding="utf-8"))
    assert first_payload["previous_experts"] == []
    assert first_payload["current_experts"] == [1]
    assert second_payload["previous_experts"] == [1]
    assert second_payload["current_experts"] == [2]
    assert second_payload["ready"] is True
    assert second_payload["payload_bytes"] == 0
    assert second_payload["issued_payload_count"] == 0
    assert second_payload["ready_credit"] is False
    assert second_payload["live_payload_runtime_enabled"] is False
    assert second_payload["payload_transfer_runtime_enabled"] is False
    assert second_payload["payload_deref_runtime_allowed"] is False
    assert second_payload["full_fetch_runtime_allowed"] is False
    assert second_payload["live_runtime_instantiated"] is False
    assert second_payload["passed_to_kernel"] is False
    assert second_payload["changes_kernel_launch_args"] is False
    assert second_payload["_export_context"]["source"] == (
        "vllm_prelaunch_payload_cache_producer_transition_state_packet"
    )
    assert second_payload["_export_context"]["layer_id"] == 0
    assert second_payload["_export_context"]["token_index"] == 11
    assert second_payload["_export_context"]["issued_payload_count"] == 0
    assert second_payload["_export_context"]["live_payload_runtime_enabled"] is False
    assert second_payload["_export_context"]["payload_transfer_runtime_enabled"] is False
    assert second_payload["_export_context"]["payload_deref_runtime_allowed"] is False
    assert second_payload["_export_context"]["full_fetch_runtime_allowed"] is False
    assert second_payload["_export_context"]["live_runtime_instantiated"] is False
    assert recorder._premap_payload_cache_producer_state_packet_export_count == 2
    assert export_path_list == [str(path) for path in export_paths]


def test_premap_payload_cache_snapshot_embeds_online_stream_contract():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_transition_topk_count=2,
    )

    per_step_experts = (
        ((1, 2), (3, 4)),
        ((2, 5), (4, 6)),
        ((5, 7), (0, 6)),
        ((1, 7), (0, 3)),
    )
    for step_layers in per_step_experts:
        for layer_id, experts in enumerate(step_layers):
            recorder.maybe_reorder_prepared_expert_assignment(
                layer_id=layer_id,
                sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
                expert_ids=torch.tensor(list(experts), dtype=torch.long),
                num_tokens_post_padded=torch.tensor([2], dtype=torch.long),
                block_size=1,
            )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 4,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_online_stream_contract",
    )

    prefix = "runtime_shadow_premap_payload_cache_direct_online_stream_contract_"
    assert performance[f"{prefix}present"] is True
    assert performance[f"{prefix}passed"] is True
    assert performance[f"{prefix}failures"] == []
    assert performance[f"{prefix}source"] == "online_producer_performance_summary"
    assert performance[f"{prefix}steps"] == 4
    assert performance[f"{prefix}layers"] == 2
    assert performance[f"{prefix}experts_per_layer"] == 2
    assert performance[f"{prefix}transition_topk_count"] == 2
    assert performance[f"{prefix}issue_candidates_per_packet"] == 2
    assert performance[f"{prefix}packet_count"] == 8
    assert performance[f"{prefix}observed_packet_count"] == 8
    assert performance[f"{prefix}expected_packet_count"] == 8
    assert performance[f"{prefix}packet_count_matches_expected"] is True
    assert performance[f"{prefix}previous_nonempty_packet_count"] == 6
    assert performance[f"{prefix}observed_previous_nonempty_packet_count"] == 6
    assert performance[f"{prefix}expected_previous_nonempty_packet_count"] == 6
    assert performance[f"{prefix}issue_candidate_count"] == 12
    assert performance[f"{prefix}observed_issue_candidate_count"] == 12
    assert performance[f"{prefix}expected_issue_candidate_count"] == 12
    assert performance[f"{prefix}issue_last_candidate_present"] is True
    assert performance[f"{prefix}issue_last_candidate_count"] == 2
    assert performance[f"{prefix}issue_last_candidate_first_expert"] == 0
    assert performance[f"{prefix}issue_last_candidate_last_expert"] == 6
    assert isinstance(performance[f"{prefix}issue_last_candidate_hash"], str)
    assert performance[f"{prefix}payload_bytes"] == 0
    assert performance[f"{prefix}ready_credit"] is False
    assert performance[f"{prefix}ready_before_demand_credit"] is False
    assert performance[f"{prefix}real_ready_credit_granted"] is False
    assert performance[f"{prefix}payload_transfer_enabled"] is False
    assert performance[f"{prefix}payload_deref_allowed"] is False
    assert performance[f"{prefix}kernel_arg_pass"] is False
    assert performance[f"{prefix}kernel_arg_pass_allowed"] is False
    assert performance[f"{prefix}passed_to_kernel"] is False
    assert performance[f"{prefix}changes_kernel_launch_args"] is False
    assert performance[f"{prefix}current_wna16_arg_compatible"] is False
    assert performance[f"{prefix}uses_current_wna16_args"] is False
    assert performance[f"{prefix}passes_current_wna16_args"] is False
    assert performance[f"{prefix}measures_tpot"] is False
    assert performance[f"{prefix}measures_vllm_latency"] is False


def test_premap_payload_cache_graph_visible_producer_contract_counts_stream():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_premap_payload_cache_graph_visible_producer_enabled=True,
        shadow_transition_topk_count=2,
    )

    per_step_experts = (
        ((1, 2), (3, 4)),
        ((2, 5), (4, 6)),
        ((5, 7), (0, 6)),
        ((1, 7), (0, 3)),
    )
    for step_layers in per_step_experts:
        for layer_id, experts in enumerate(step_layers):
            recorder.maybe_reorder_prepared_expert_assignment(
                layer_id=layer_id,
                sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
                expert_ids=torch.tensor(list(experts), dtype=torch.long),
                num_tokens_post_padded=torch.tensor([2], dtype=torch.long),
                block_size=1,
            )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 4,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_graph_visible_producer_contract",
    )

    prefix = "runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_"
    assert performance[f"{prefix}enabled"] is True
    assert performance[f"{prefix}present"] is True
    assert performance[f"{prefix}passed"] is True
    assert performance[f"{prefix}failures"] == []
    assert performance[f"{prefix}source"] == "captured_torch_tensor_state"
    assert performance[f"{prefix}steps"] == 4
    assert performance[f"{prefix}layers"] == 2
    assert performance[f"{prefix}experts_per_layer"] == 2
    assert performance[f"{prefix}transition_topk_count"] == 2
    assert performance[f"{prefix}issue_candidates_per_packet"] == 2
    assert performance[f"{prefix}observed_packet_count"] == 8
    assert performance[f"{prefix}expected_packet_count"] == 8
    assert performance[f"{prefix}observed_previous_nonempty_packet_count"] == 6
    assert performance[f"{prefix}expected_previous_nonempty_packet_count"] == 6
    assert performance[f"{prefix}observed_issue_candidate_count"] == 12
    assert performance[f"{prefix}expected_issue_candidate_count"] == 12
    assert performance[f"{prefix}contract_boundary"] == (
        "captured_torch_tensor_state_visibility_canary"
    )
    assert performance[f"{prefix}captured_replay_required"] is True
    assert performance[f"{prefix}captured_replay_passed"] is True
    assert performance[f"{prefix}transition_state_on_device"] is True
    assert performance[f"{prefix}issue_generation_on_device"] is True
    assert performance[f"{prefix}python_transition_skipped"] is False
    assert performance[f"{prefix}capture_once_per_layer_suspected"] is False
    assert performance[f"{prefix}replay_update_status"] == (
        "complete_replay_updates_observed"
    )
    assert performance[f"{prefix}production_candidate"] is True
    assert performance[f"{prefix}payload_bytes"] == 0
    assert performance[f"{prefix}ready_credit"] is False
    assert performance[f"{prefix}passed_to_kernel"] is False
    assert performance[f"{prefix}changes_kernel_launch_args"] is False

    boundary_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "online_inside_graph_producer_boundary_contract_"
    )
    assert performance[f"{boundary_prefix}enabled"] is True
    assert performance[f"{boundary_prefix}present"] is True
    assert performance[f"{boundary_prefix}passed"] is False
    assert performance[f"{boundary_prefix}transition_state_on_device"] is True
    assert performance[f"{boundary_prefix}issue_generation_on_device"] is True
    assert performance[f"{boundary_prefix}python_transition_skipped"] is False
    assert "python_transition_extraction_not_skipped" in performance[
        f"{boundary_prefix}failures"
    ]
    assert performance[f"{boundary_prefix}native_runtime"] is False
    assert performance[f"{boundary_prefix}inprocess_native_op"] is False
    assert performance[f"{boundary_prefix}kernel_arg_pass"] is False
    assert performance[f"{boundary_prefix}passed_to_kernel"] is False
    assert performance[f"{boundary_prefix}changes_kernel_launch_args"] is False

    replay_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "vllm_replay_visible_native_producer_contract_"
    )
    assert performance[f"{replay_prefix}enabled"] is False
    assert performance[f"{replay_prefix}present"] is False
    assert performance[f"{replay_prefix}passed"] is False
    assert performance[f"{replay_prefix}mode"] == (
        "payload_cache_vllm_replay_visible_native_producer_contract"
    )
    assert performance[f"{replay_prefix}contract_boundary"] == (
        "inprocess_vllm_replay_visible_native_producer_op"
    )
    assert performance[f"{replay_prefix}source_kind"] == (
        "missing_vllm_prelaunch_inprocess_native_producer"
    )
    assert "vllm_replay_visible_native_producer_disabled" in performance[
        f"{replay_prefix}failures"
    ]
    assert performance[f"{replay_prefix}native_runtime"] is False
    assert performance[f"{replay_prefix}inprocess_native_op"] is False
    assert performance[f"{replay_prefix}vllm_replay_visible"] is False
    assert performance[f"{replay_prefix}expected_packet_count"] == 8
    assert performance[f"{replay_prefix}expected_issue_candidate_count"] == 12
    assert performance[f"{replay_prefix}packet_count"] == 0
    assert performance[f"{replay_prefix}issue_candidate_count"] == 0
    assert performance[f"{replay_prefix}payload_bytes"] == 0
    assert performance[f"{replay_prefix}ready_credit"] is False
    assert performance[f"{replay_prefix}kernel_arg_pass"] is False
    assert performance[f"{replay_prefix}passed_to_kernel"] is False
    assert performance[f"{replay_prefix}changes_kernel_launch_args"] is False
    assert performance[f"{replay_prefix}payload_deref_allowed"] is False
    assert performance[f"{replay_prefix}ready_before_demand_credit"] is False
    assert performance[f"{replay_prefix}real_ready_credit_granted"] is False
    assert performance[f"{replay_prefix}kernel_arg_pass_allowed"] is False
    assert performance[f"{replay_prefix}measures_vllm_latency"] is False


def test_premap_payload_cache_inside_graph_producer_boundary_skips_python_transition():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_premap_payload_cache_graph_visible_producer_enabled=True,
        shadow_premap_payload_cache_graph_visible_producer_skip_python_transition=True,
        shadow_transition_topk_count=2,
    )

    per_step_experts = (
        ((1, 2), (3, 4)),
        ((2, 5), (4, 6)),
        ((5, 7), (0, 6)),
        ((1, 7), (0, 3)),
    )
    for step_layers in per_step_experts:
        for layer_id, experts in enumerate(step_layers):
            recorder.maybe_reorder_prepared_expert_assignment(
                layer_id=layer_id,
                sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
                expert_ids=torch.tensor(list(experts), dtype=torch.long),
                num_tokens_post_padded=torch.tensor([2], dtype=torch.long),
                block_size=1,
            )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 4,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_inside_graph_boundary",
    )

    graph_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "graph_visible_producer_contract_"
    )
    assert performance[f"{graph_prefix}passed"] is True
    assert performance[f"{graph_prefix}transition_state_on_device"] is True
    assert performance[f"{graph_prefix}issue_generation_on_device"] is True
    assert performance[f"{graph_prefix}python_transition_skipped"] is True
    assert performance[f"{graph_prefix}observed_packet_count"] == 8
    assert performance[f"{graph_prefix}expected_packet_count"] == 8
    assert performance[f"{graph_prefix}observed_issue_candidate_count"] == 12
    assert performance[f"{graph_prefix}expected_issue_candidate_count"] == 12
    assert performance[f"{graph_prefix}last_issue_candidate_count"] == 2
    assert performance[f"{graph_prefix}last_issue_candidate_first_expert"] >= 0
    assert performance[f"{graph_prefix}last_issue_candidate_last_expert"] >= 0
    assert performance[f"{graph_prefix}issue_candidate_expert_sum"] > 0

    boundary_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "online_inside_graph_producer_boundary_contract_"
    )
    assert performance[f"{boundary_prefix}enabled"] is True
    assert performance[f"{boundary_prefix}present"] is True
    assert performance[f"{boundary_prefix}passed"] is True
    assert performance[f"{boundary_prefix}failures"] == []
    assert performance[f"{boundary_prefix}contract_boundary"] == (
        "online_inside_graph_tensor_producer"
    )
    assert performance[f"{boundary_prefix}transition_state_on_device"] is True
    assert performance[f"{boundary_prefix}issue_generation_on_device"] is True
    assert performance[f"{boundary_prefix}python_transition_skipped"] is True
    assert performance[f"{boundary_prefix}native_runtime"] is False
    assert performance[f"{boundary_prefix}inprocess_native_op"] is False
    assert performance[f"{boundary_prefix}payload_bytes"] == 0
    assert performance[f"{boundary_prefix}ready_credit"] is False
    assert performance[f"{boundary_prefix}kernel_arg_pass"] is False
    assert performance[f"{boundary_prefix}passed_to_kernel"] is False
    assert performance[f"{boundary_prefix}changes_kernel_launch_args"] is False

    online_prefix = (
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_"
    )
    assert performance[f"{online_prefix}present"] is False
    assert performance[f"{online_prefix}passed"] is False
    assert recorder._premap_payload_cache_transition_native_packet_count == 0


def test_premap_payload_cache_vllm_replay_visible_native_producer_contract_fails_closed_when_enabled_without_backend():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_premap_payload_cache_graph_visible_producer_enabled=True,
        shadow_premap_payload_cache_graph_visible_producer_skip_python_transition=True,
        shadow_premap_payload_cache_vllm_replay_visible_native_producer_enabled=True,
        shadow_transition_topk_count=2,
    )

    per_step_experts = (
        ((1, 2), (3, 4)),
        ((2, 5), (4, 6)),
        ((5, 7), (0, 6)),
        ((1, 7), (0, 3)),
    )
    for step_layers in per_step_experts:
        for layer_id, experts in enumerate(step_layers):
            recorder.maybe_reorder_prepared_expert_assignment(
                layer_id=layer_id,
                sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
                expert_ids=torch.tensor(list(experts), dtype=torch.long),
                num_tokens_post_padded=torch.tensor([2], dtype=torch.long),
                block_size=1,
            )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 4,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_vllm_replay_visible_native_producer_contract",
    )

    graph_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "graph_visible_producer_contract_"
    )
    assert performance[f"{graph_prefix}passed"] is True

    boundary_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "online_inside_graph_producer_boundary_contract_"
    )
    assert performance[f"{boundary_prefix}passed"] is True

    replay_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "vllm_replay_visible_native_producer_contract_"
    )
    assert performance[f"{replay_prefix}enabled"] is True
    assert performance[f"{replay_prefix}present"] is False
    assert performance[f"{replay_prefix}passed"] is False
    assert performance[f"{replay_prefix}failures"] == [
        "native_runtime_not_connected",
        "inprocess_native_op_not_connected",
        "vllm_replay_visible_updates_missing",
    ]
    assert performance[f"{replay_prefix}mode"] == (
        "payload_cache_vllm_replay_visible_native_producer_contract"
    )
    assert performance[f"{replay_prefix}contract_boundary"] == (
        "inprocess_vllm_replay_visible_native_producer_op"
    )
    assert performance[f"{replay_prefix}source_kind"] == (
        "missing_vllm_prelaunch_inprocess_native_producer"
    )
    assert performance[f"{replay_prefix}native_runtime"] is False
    assert performance[f"{replay_prefix}inprocess_native_op"] is False
    assert performance[f"{replay_prefix}vllm_replay_visible"] is False
    assert performance[f"{replay_prefix}prelaunch_callable_native_session"] is False
    assert performance[f"{replay_prefix}post_export_native_replay"] is False
    assert performance[f"{replay_prefix}standalone_native_replay"] is False
    assert performance[f"{replay_prefix}native_graph_replay"] is False
    assert performance[f"{replay_prefix}transition_state_on_device"] is False
    assert performance[f"{replay_prefix}persistent_state_on_device"] is False
    assert performance[f"{replay_prefix}issue_generation_on_device"] is False
    assert performance[f"{replay_prefix}python_transition_skipped"] is False
    assert performance[f"{replay_prefix}expected_packet_count"] == 8
    assert performance[f"{replay_prefix}expected_issue_candidate_count"] == 12
    assert performance[f"{replay_prefix}packet_count"] == 0
    assert performance[f"{replay_prefix}issue_candidate_count"] == 0
    assert performance[f"{replay_prefix}producer_update_count"] == 0
    assert performance[f"{replay_prefix}replay_visible_update_count"] == 0
    assert performance[f"{replay_prefix}prelaunch_probe_count"] == 8
    assert performance[f"{replay_prefix}prelaunch_abi_ready_count"] == 0
    assert performance[f"{replay_prefix}prelaunch_abi_blocked_count"] == 8
    assert performance[f"{replay_prefix}prelaunch_device_tensor_count"] == 0
    assert performance[f"{replay_prefix}prelaunch_host_tensor_count"] == 8
    assert performance[f"{replay_prefix}prelaunch_int32_count"] == 0
    assert performance[f"{replay_prefix}prelaunch_dtype_mismatch_count"] == 8
    assert (
        performance[
            f"{replay_prefix}prelaunch_current_count_host_scalar_available_count"
        ]
        == 8
    )
    assert (
        performance[f"{replay_prefix}prelaunch_native_session_update_v1_abi_ready"]
        is False
    )
    assert performance[f"{replay_prefix}prelaunch_last_block_reason"] == (
        "current_expert_not_device_tensor;current_expert_dtype_not_int32"
    )
    assert performance[f"{replay_prefix}prelaunch_last_expert_dtype"] == "torch.int64"
    assert performance[f"{replay_prefix}prelaunch_last_expert_device"] == "cpu"
    assert performance[f"{replay_prefix}prelaunch_last_expert_ndim"] == 1
    assert performance[f"{replay_prefix}prelaunch_last_expert_numel"] == 2
    assert performance[f"{replay_prefix}prelaunch_last_block_size"] == 1
    assert performance[f"{replay_prefix}prelaunch_last_current_count_source_kind"] == (
        "num_tokens_post_padded_host_tensor"
    )
    assert performance[f"{replay_prefix}payload_bytes"] == 0
    assert performance[f"{replay_prefix}payload_transfer_enabled"] is False
    assert performance[f"{replay_prefix}ready_credit"] is False
    assert performance[f"{replay_prefix}ready_before_demand_credit"] is False
    assert performance[f"{replay_prefix}real_ready_credit_granted"] is False
    assert performance[f"{replay_prefix}payload_deref_allowed"] is False
    assert performance[f"{replay_prefix}kernel_arg_pass"] is False
    assert performance[f"{replay_prefix}kernel_arg_pass_allowed"] is False
    assert performance[f"{replay_prefix}passed_to_kernel"] is False
    assert performance[f"{replay_prefix}changes_kernel_launch_args"] is False
    assert performance[f"{replay_prefix}current_wna16_arg_compatible"] is False
    assert performance[f"{replay_prefix}uses_current_wna16_args"] is False
    assert performance[f"{replay_prefix}passes_current_wna16_args"] is False
    assert performance[f"{replay_prefix}measures_tpot"] is False
    assert performance[f"{replay_prefix}measures_vllm_latency"] is False


def test_premap_payload_cache_vllm_replay_visible_native_producer_contract_emits_without_manager_counters():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=False,
        shadow_premap_payload_cache_vllm_replay_visible_native_producer_enabled=True,
    )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 4,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_vllm_replay_visible_no_manager_counters",
    )

    assert "runtime_shadow_premap_payload_cache_direct_snapshot_present" not in performance
    graph_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "graph_visible_producer_contract_"
    )
    assert f"{graph_prefix}enabled" not in performance

    replay_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "vllm_replay_visible_native_producer_contract_"
    )
    assert performance[f"{replay_prefix}enabled"] is True
    assert performance[f"{replay_prefix}present"] is False
    assert performance[f"{replay_prefix}passed"] is False
    assert performance[f"{replay_prefix}failures"] == [
        "native_runtime_not_connected",
        "inprocess_native_op_not_connected",
        "vllm_replay_visible_updates_missing",
    ]
    assert performance[f"{replay_prefix}expected_packet_count"] == 0
    assert performance[f"{replay_prefix}expected_issue_candidate_count"] == 0
    assert performance[f"{replay_prefix}packet_count"] == 0
    assert performance[f"{replay_prefix}issue_candidate_count"] == 0
    assert performance[f"{replay_prefix}prelaunch_probe_count"] == 0
    assert performance[f"{replay_prefix}prelaunch_abi_ready_count"] == 0
    assert performance[f"{replay_prefix}prelaunch_abi_blocked_count"] == 0
    assert (
        performance[f"{replay_prefix}prelaunch_native_session_update_v1_abi_ready"]
        is False
    )
    assert performance[f"{replay_prefix}source_kind"] == (
        "missing_vllm_prelaunch_inprocess_native_producer"
    )
    assert performance[f"{replay_prefix}payload_bytes"] == 0
    assert performance[f"{replay_prefix}payload_transfer_enabled"] is False
    assert performance[f"{replay_prefix}payload_deref_allowed"] is False
    assert performance[f"{replay_prefix}ready_credit"] is False
    assert performance[f"{replay_prefix}ready_before_demand_credit"] is False
    assert performance[f"{replay_prefix}real_ready_credit_granted"] is False
    assert performance[f"{replay_prefix}kernel_arg_pass"] is False
    assert performance[f"{replay_prefix}kernel_arg_pass_allowed"] is False
    assert performance[f"{replay_prefix}passed_to_kernel"] is False
    assert performance[f"{replay_prefix}changes_kernel_launch_args"] is False
    assert performance[f"{replay_prefix}current_wna16_arg_compatible"] is False
    assert performance[f"{replay_prefix}uses_current_wna16_args"] is False
    assert performance[f"{replay_prefix}passes_current_wna16_args"] is False
    assert performance[f"{replay_prefix}measures_tpot"] is False
    assert performance[f"{replay_prefix}measures_vllm_latency"] is False


def test_premap_payload_cache_vllm_replay_visible_native_producer_probe_rejects_nonscalar_current_count():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=False,
        shadow_premap_payload_cache_vllm_replay_visible_native_producer_enabled=True,
    )
    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
        expert_ids=torch.tensor([1, 2], dtype=torch.int32),
        num_tokens_post_padded=torch.tensor([2, 3], dtype=torch.long),
        block_size=1,
    )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 1,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_vllm_replay_visible_nonscalar_current_count",
    )

    replay_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "vllm_replay_visible_native_producer_contract_"
    )
    assert performance[f"{replay_prefix}prelaunch_probe_count"] == 1
    assert performance[f"{replay_prefix}prelaunch_abi_ready_count"] == 0
    assert performance[f"{replay_prefix}prelaunch_abi_blocked_count"] == 1
    assert performance[f"{replay_prefix}prelaunch_int32_count"] == 1
    assert (
        performance[
            f"{replay_prefix}prelaunch_current_count_host_scalar_available_count"
        ]
        == 0
    )
    assert performance[f"{replay_prefix}prelaunch_last_block_reason"] == (
        "current_expert_not_device_tensor;current_count_not_scalar"
    )


def test_premap_payload_cache_inside_graph_producer_boundary_accepts_empty_issue_candidates():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_premap_payload_cache_graph_visible_producer_enabled=True,
        shadow_premap_payload_cache_graph_visible_producer_skip_python_transition=True,
        shadow_transition_topk_count=2,
    )

    for layer_id, experts in enumerate(((1, 2), (3, 4))):
        recorder.maybe_reorder_prepared_expert_assignment(
            layer_id=layer_id,
            sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
            expert_ids=torch.tensor(list(experts), dtype=torch.long),
            num_tokens_post_padded=torch.tensor([2], dtype=torch.long),
            block_size=1,
        )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 1,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_inside_graph_boundary_empty_issue",
    )

    graph_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "graph_visible_producer_contract_"
    )
    assert performance[f"{graph_prefix}present"] is True
    assert performance[f"{graph_prefix}has_packets"] is True
    assert performance[f"{graph_prefix}passed"] is True
    assert performance[f"{graph_prefix}observed_packet_count"] == 2
    assert performance[f"{graph_prefix}expected_packet_count"] == 2
    assert performance[f"{graph_prefix}observed_previous_nonempty_packet_count"] == 0
    assert performance[f"{graph_prefix}expected_previous_nonempty_packet_count"] == 0
    assert performance[f"{graph_prefix}observed_issue_candidate_count"] == 0
    assert performance[f"{graph_prefix}expected_issue_candidate_count"] == 0

    boundary_prefix = (
        "runtime_shadow_premap_payload_cache_direct_"
        "online_inside_graph_producer_boundary_contract_"
    )
    assert performance[f"{boundary_prefix}passed"] is True
    assert performance[f"{boundary_prefix}failures"] == []
    assert performance[f"{boundary_prefix}python_transition_skipped"] is True
    assert performance[f"{boundary_prefix}payload_bytes"] == 0
    assert performance[f"{boundary_prefix}kernel_arg_pass"] is False
    assert performance[f"{boundary_prefix}passed_to_kernel"] is False


def test_premap_payload_cache_graph_visible_producer_resize_preserves_transition_state():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_premap_payload_cache_graph_visible_producer_enabled=True,
        shadow_premap_payload_cache_graph_visible_producer_skip_python_transition=True,
        shadow_transition_topk_count=2,
    )

    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
        expert_ids=torch.tensor([1, 2], dtype=torch.long),
        num_tokens_post_padded=torch.tensor([2], dtype=torch.long),
        block_size=1,
    )
    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.tensor([0, 1, 2], dtype=torch.long),
        expert_ids=torch.tensor([3, 4, 5], dtype=torch.long),
        num_tokens_post_padded=torch.tensor([3], dtype=torch.long),
        block_size=1,
    )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 2,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_graph_visible_resize_preserves_state",
    )

    prefix = "runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_"
    assert performance[f"{prefix}passed"] is True
    assert performance[f"{prefix}observed_packet_count"] == 2
    assert performance[f"{prefix}expected_packet_count"] == 2
    assert performance[f"{prefix}observed_previous_nonempty_packet_count"] == 1
    assert performance[f"{prefix}expected_previous_nonempty_packet_count"] == 1
    assert performance[f"{prefix}observed_issue_candidate_count"] == 2
    assert performance[f"{prefix}expected_issue_candidate_count"] == 2
    assert performance[f"{prefix}experts_per_layer"] == 3
    assert performance[f"{prefix}last_issue_candidate_count"] == 2
    assert performance[f"{prefix}last_issue_candidate_first_expert"] == 1
    assert performance[f"{prefix}last_issue_candidate_last_expert"] == 2


def test_premap_payload_cache_graph_visible_producer_contract_flags_capture_once_per_layer():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_premap_payload_cache_graph_visible_producer_enabled=True,
        shadow_transition_topk_count=2,
    )

    for layer_id, experts in enumerate(((1, 2), (3, 4))):
        recorder.maybe_reorder_prepared_expert_assignment(
            layer_id=layer_id,
            sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
            expert_ids=torch.tensor(list(experts), dtype=torch.long),
            num_tokens_post_padded=torch.tensor([2], dtype=torch.long),
            block_size=1,
        )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 4,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_graph_visible_capture_once",
    )

    prefix = "runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_"
    assert performance[f"{prefix}enabled"] is True
    assert performance[f"{prefix}present"] is True
    assert performance[f"{prefix}passed"] is False
    assert performance[f"{prefix}observed_packet_count"] == 2
    assert performance[f"{prefix}expected_packet_count"] == 8
    assert performance[f"{prefix}observed_issue_candidate_count"] == 0
    assert performance[f"{prefix}expected_issue_candidate_count"] == 12
    assert performance[f"{prefix}capture_once_per_layer_suspected"] is True
    assert performance[f"{prefix}replay_update_status"] == (
        "capture_once_per_layer_no_replay_updates"
    )
    assert performance[f"{prefix}captured_replay_required"] is True
    assert performance[f"{prefix}captured_replay_passed"] is False
    assert performance[f"{prefix}production_candidate"] is False
    assert "observed_packet_count_mismatch" in performance[f"{prefix}failures"]
    assert "observed_issue_candidate_count_mismatch" in performance[f"{prefix}failures"]


def test_premap_payload_cache_graph_visible_producer_contract_disabled_not_required():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_transition_topk_count=2,
    )
    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
        expert_ids=torch.tensor([1, 2], dtype=torch.long),
        num_tokens_post_padded=torch.tensor([2], dtype=torch.long),
        block_size=1,
    )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 4,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_graph_visible_disabled",
    )

    prefix = "runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_"
    assert performance[f"{prefix}enabled"] is False
    assert performance[f"{prefix}present"] is False
    assert performance[f"{prefix}passed"] is False
    assert performance[f"{prefix}captured_replay_required"] is False
    assert performance[f"{prefix}captured_replay_passed"] is False
    assert performance[f"{prefix}capture_once_per_layer_suspected"] is False
    assert performance[f"{prefix}replay_update_status"] == "disabled"
    assert performance[f"{prefix}production_candidate"] is False
    assert "graph_visible_producer_disabled" in performance[f"{prefix}failures"]


def test_premap_payload_cache_online_stream_contract_rejects_graph_once_per_layer():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=8,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_transition_topk_count=2,
    )

    for layer_id, experts in enumerate(((1, 2), (3, 4))):
        recorder.maybe_reorder_prepared_expert_assignment(
            layer_id=layer_id,
            sorted_token_ids=torch.tensor([0, 1], dtype=torch.long),
            expert_ids=torch.tensor(list(experts), dtype=torch.long),
            num_tokens_post_padded=torch.tensor([2], dtype=torch.long),
            block_size=1,
        )
    performance = {
        "sample_count": 1,
        "requested_output_token_count": 4,
    }

    _add_premap_payload_cache_manager_snapshot_to_performance(
        performance,
        recorder,
        source="unit_test_online_stream_contract",
    )

    prefix = "runtime_shadow_premap_payload_cache_direct_online_stream_contract_"
    assert performance[f"{prefix}present"] is True
    assert performance[f"{prefix}passed"] is False
    assert performance[f"{prefix}observed_packet_count"] == 2
    assert performance[f"{prefix}expected_packet_count"] == 8
    assert performance[f"{prefix}packet_count_matches_expected"] is False
    assert "observed_packet_count_mismatch" in performance[f"{prefix}failures"]
    assert (
        "observed_previous_nonempty_packet_count_mismatch"
        in performance[f"{prefix}failures"]
    )
    assert "observed_issue_candidate_count_mismatch" in performance[f"{prefix}failures"]


def test_premap_payload_cache_producer_transition_owner_skips_consumer_updates():
    transition = torch.zeros((1, 1, 4, 4), dtype=torch.float32)
    transition[0, 0, 1, 2] = 1.0
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_issue_sources=(
            "prelaunch_observed_transition_premap_shadow",
        ),
        shadow_premap_payload_cache_transition_state_owner="producer",
        shadow_transition_premap_source=(
            "prelaunch_observed_transition_premap_shadow"
        ),
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=1,
        shadow_transition_matrix=transition,
    )

    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=0,
        active_experts=[1],
    )
    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=0,
        active_experts=[2],
    )

    assert recorder._shadow_premap_payload_cache_manager is None
    assert recorder._premap_payload_cache_last_active_experts_by_layer == {}
    assert recorder._premap_payload_cache_transition_issue_attempt_count == 0
    assert recorder._premap_payload_cache_transition_consumer_update_count == 0
    assert recorder._premap_payload_cache_transition_producer_update_count == 0
    assert recorder._premap_payload_cache_transition_native_packet_count == 0


def test_premap_payload_cache_producer_transition_owner_skips_unavailable_handle():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
    )

    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=None,
        expert_ids=torch.tensor([1], dtype=torch.long),
        num_tokens_post_padded=torch.tensor([1], dtype=torch.long),
        block_size=1,
    )

    assert recorder._shadow_premap_payload_cache_manager is None
    assert recorder._premap_payload_cache_last_active_experts_by_layer == {}
    assert recorder._premap_payload_cache_transition_issue_attempt_count == 0
    assert recorder._premap_payload_cache_transition_consumer_update_count == 0
    assert recorder._premap_payload_cache_transition_producer_update_count == 0


def test_premap_payload_cache_producer_transition_owner_clears_valid_empty_handle():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_transition_state_owner="producer",
    )
    recorder._premap_payload_cache_last_active_experts_by_layer[0] = (1,)

    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.tensor([0], dtype=torch.long),
        expert_ids=torch.tensor([1], dtype=torch.long),
        num_tokens_post_padded=torch.tensor([0], dtype=torch.long),
        block_size=1,
    )

    assert recorder._shadow_premap_payload_cache_manager is not None
    assert recorder._premap_payload_cache_last_active_experts_by_layer[0] == ()
    assert recorder._premap_payload_cache_transition_consumer_update_count == 0
    assert recorder._premap_payload_cache_transition_producer_update_count == 1
    assert recorder._premap_payload_cache_transition_native_packet_count == 1
    assert recorder._premap_payload_cache_transition_native_packet_ready_count == 1
    assert recorder._premap_payload_cache_transition_native_packet_last_previous_count == 1
    assert recorder._premap_payload_cache_transition_native_packet_last_current_count == 0


def test_premap_payload_cache_transition_state_owner_rejects_invalid_value():
    with pytest.raises(
        ValueError,
        match="shadow_premap_payload_cache_transition_state_owner must be one of",
    ):
        VllmRouterRecorder(
            top_k=2,
            shadow_premap_payload_cache_transition_state_owner="prodducer",
        )


def test_premap_payload_cache_transition_state_clear_is_sample_scoped():
    transition = torch.zeros((1, 1, 4, 4), dtype=torch.float32)
    transition[0, 0, 1, 2] = 1.0
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_issue_sources=(
            "prelaunch_observed_transition_premap_shadow",
        ),
        shadow_transition_premap_source=(
            "prelaunch_observed_transition_premap_shadow"
        ),
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=1,
        shadow_transition_matrix=transition,
    )

    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=0,
        active_experts=[1],
    )
    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=0,
        active_experts=[2],
    )
    recorder._premap_payload_cache_transition_issue_last_error = "old_error"

    recorder.clear()

    assert recorder._premap_payload_cache_last_active_experts_by_layer == {}
    assert recorder._premap_payload_cache_transition_issue_attempt_count == 0
    assert recorder._premap_payload_cache_transition_issue_previous_nonempty_count == 0
    assert recorder._premap_payload_cache_transition_issue_descriptor_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_candidate_first_expert == -1
    assert recorder._premap_payload_cache_transition_issue_last_candidate_last_expert == -1
    assert recorder._premap_payload_cache_transition_issue_last_candidate_hash is None
    assert recorder._premap_payload_cache_transition_issue_error_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_error is None
    assert recorder._premap_payload_cache_transition_consumer_update_count == 0
    assert recorder._premap_payload_cache_transition_producer_update_count == 0
    assert recorder._premap_payload_cache_transition_native_packet_count == 0
    assert recorder._premap_payload_cache_transition_native_packet_ready_count == 0
    assert recorder._premap_payload_cache_transition_native_packet_last_hash is None


def test_premap_payload_cache_transition_disallowed_source_does_not_count_attempt():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_issue_sources=("other_source",),
        shadow_transition_premap_source=(
            "prelaunch_observed_transition_premap_shadow"
        ),
        shadow_transition_summary_mode="previous_topk",
    )

    snapshot = recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
        layer_id=0,
        previous_experts=[1],
    )

    assert snapshot is None
    assert recorder._premap_payload_cache_transition_issue_attempt_count == 0
    assert recorder._premap_payload_cache_transition_issue_previous_nonempty_count == 0
    assert recorder._premap_payload_cache_transition_issue_descriptor_count == 0
    assert recorder._premap_payload_cache_transition_issue_error_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_error is None
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_candidate_hash is None


def test_premap_payload_cache_transition_issue_identity_clears_on_non_issue_paths():
    transition = torch.zeros((1, 1, 4, 4), dtype=torch.float32)
    transition[0, 0, 1, 2] = 1.0
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_issue_sources=(
            "prelaunch_observed_transition_premap_shadow",
        ),
        shadow_transition_premap_source=(
            "prelaunch_observed_transition_premap_shadow"
        ),
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=1,
        shadow_transition_matrix=transition,
    )

    recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
        layer_id=0,
        previous_experts=[1],
    )
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 1
    assert (
        recorder._premap_payload_cache_transition_issue_last_candidate_hash
        == _premap_payload_cache_issue_hash([2])
    )

    recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
        layer_id=0,
        previous_experts=[],
    )
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_candidate_hash is None

    recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
        layer_id=0,
        previous_experts=[1],
    )
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 1
    recorder.shadow_premap_payload_cache_manager_issue_sources = ("other_source",)
    recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
        layer_id=0,
        previous_experts=[1],
    )
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_candidate_hash is None

    recorder.shadow_premap_payload_cache_manager_issue_sources = (
        "prelaunch_observed_transition_premap_shadow",
    )
    recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
        layer_id=0,
        previous_experts=[1],
    )
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 1
    recorder.shadow_transition_matrix = None
    recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
        layer_id=0,
        previous_experts=[1],
    )
    assert recorder._premap_payload_cache_transition_issue_error_count == 1
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_candidate_hash is None


def test_premap_payload_cache_transition_issue_identity_clears_on_manager_error(
    monkeypatch: pytest.MonkeyPatch,
):
    class _FailingIssueManager:
        def issue_prefetch(self, layer_idx: int, expert_idx: int) -> bool:
            raise RuntimeError("synthetic issue failure")

        def snapshot(self):
            return None

    transition = torch.zeros((1, 1, 4, 4), dtype=torch.float32)
    transition[0, 0, 1, 2] = 1.0
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_issue_sources=(
            "prelaunch_observed_transition_premap_shadow",
        ),
        shadow_transition_premap_source=(
            "prelaunch_observed_transition_premap_shadow"
        ),
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=1,
        shadow_transition_matrix=transition,
    )
    failing_manager = _FailingIssueManager()
    monkeypatch.setattr(
        recorder,
        "_ensure_premap_payload_cache_manager",
        lambda: failing_manager,
    )

    snapshot = recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
        layer_id=0,
        previous_experts=[1],
    )

    assert snapshot is None
    assert recorder._premap_payload_cache_transition_issue_descriptor_count == 1
    assert recorder._premap_payload_cache_transition_issue_error_count == 1
    assert "synthetic issue failure" in (
        recorder._premap_payload_cache_transition_issue_last_error or ""
    )
    assert recorder._premap_payload_cache_transition_issue_last_candidate_count == 0
    assert recorder._premap_payload_cache_transition_issue_last_candidate_hash is None


def test_premap_payload_cache_transition_issue_error_is_recorded():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_issue_sources=(
            "prelaunch_observed_transition_premap_shadow",
        ),
        shadow_transition_premap_source=(
            "prelaunch_observed_transition_premap_shadow"
        ),
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_matrix=None,
    )

    snapshot = recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
        layer_id=0,
        previous_experts=[1],
    )

    assert snapshot is not None
    assert snapshot.demand_count == 0
    assert snapshot.issued_fetch_count == 0
    assert recorder._premap_payload_cache_transition_issue_attempt_count == 1
    assert recorder._premap_payload_cache_transition_issue_previous_nonempty_count == 1
    assert recorder._premap_payload_cache_transition_issue_descriptor_count == 0
    assert recorder._premap_payload_cache_transition_issue_error_count == 1
    assert recorder._premap_payload_cache_transition_issue_last_error is not None
    assert "matrix_topk transition summary requires shadow_transition_matrix" in (
        recorder._premap_payload_cache_transition_issue_last_error
    )


def test_premap_payload_cache_transition_issue_strict_reraises_config_error():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_num_experts=4,
        shadow_emit_premap_payload_cache_manager_counters=True,
        shadow_premap_payload_cache_manager_capacity=4,
        shadow_premap_payload_cache_manager_issue_sources=(
            "prelaunch_observed_transition_premap_shadow",
        ),
        shadow_premap_payload_cache_transition_issue_strict=True,
        shadow_transition_premap_source=(
            "prelaunch_observed_transition_premap_shadow"
        ),
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_matrix=None,
    )

    with pytest.raises(
        ValueError,
        match="matrix_topk transition summary requires shadow_transition_matrix",
    ):
        recorder._issue_premap_payload_cache_from_prelaunch_observed_transition(
            layer_id=0,
            previous_experts=[1],
        )

    assert recorder._premap_payload_cache_transition_issue_attempt_count == 1
    assert recorder._premap_payload_cache_transition_issue_previous_nonempty_count == 1
    assert recorder._premap_payload_cache_transition_issue_descriptor_count == 0
    assert recorder._premap_payload_cache_transition_issue_error_count == 1
    assert recorder._premap_payload_cache_transition_issue_last_error is not None


def test_runtime_shadow_aggregate_fields_are_flattened_to_performance_summary():
    aggregate = {
        "premap_consumer_mapping_count": 3,
        "premap_consumer_real_descriptor_handle_hit_count": 7,
        "premap_consumer_real_descriptor_handle_miss_count": 1,
        "premap_consumer_real_descriptor_handle_packed_weight_hit_count": 7,
        "premap_consumer_real_descriptor_handle_packed_weight_miss_count": 1,
        "premap_consumer_real_descriptor_handle_scale_metadata_hit_count": 6,
        "premap_consumer_real_descriptor_handle_scale_metadata_miss_count": 2,
        "premap_consumer_real_descriptor_handle_aux_metadata_hit_count": 5,
        "premap_consumer_real_descriptor_handle_aux_metadata_miss_count": 3,
        "premap_consumer_real_descriptor_handle_resolver_disabled_count": 11,
        "premap_consumer_real_descriptor_handle_consumer_layer_missing_count": 12,
        "premap_consumer_real_descriptor_handle_expert_map_miss_count": 13,
        "premap_consumer_real_descriptor_handle_no_handle_parts_count": 14,
        "premap_consumer_readonly_lookup_count": 15,
        "premap_consumer_readonly_handle_hit_rate": 0.875,
        "premap_consumer_readonly_evicted_before_consume_count": 2,
        "premap_consumer_readonly_stale_handle_count": 1,
        "premap_consumer_readonly_handle_parity_ok_rate": 0.75,
        "premap_consumer_descriptor_prep_real_handle_count": 16,
        "premap_consumer_descriptor_prep_real_handle_miss_count": 0,
        "premap_consumer_descriptor_prep_real_handle_hit_rate": 1.0,
        "premap_consumer_descriptor_prep_real_handle_backed_count": 4,
        "premap_consumer_descriptor_prep_real_handle_backed_rate": 1.0,
        "premap_consumer_descriptor_prep_consumer_object_count": 16,
        "premap_consumer_descriptor_prep_consumer_object_rate": 1.0,
        "premap_consumer_descriptor_prep_consumer_object_read_lookup_count": 16,
        "premap_consumer_descriptor_prep_consumer_object_read_hit_count": 16,
        "premap_consumer_descriptor_prep_consumer_object_read_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_object_stale_count": 0,
        "premap_consumer_descriptor_prep_consumer_object_read_hit_rate": 1.0,
        "premap_consumer_descriptor_prep_consumer_object_stale_rate": 0.0,
        "premap_consumer_descriptor_prep_consumer_object_read_ok_rate": 1.0,
        "premap_consumer_descriptor_prep_consumer_shim_executed_count": 4,
        "premap_consumer_descriptor_prep_consumer_shim_ok_count": 4,
        "premap_consumer_descriptor_prep_consumer_shim_ok_rate": 1.0,
        "premap_consumer_descriptor_prep_consumer_shim_object_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max": 4,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count": 4,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate": 0.0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count": 4,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate": 1.0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count": 4,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate": 1.0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count": 4,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_count": 4,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate": 1.0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_count": 4,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_rate": 1.0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max": 4,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash": "schema-hash",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_checked_count": 4,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_missing_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_mismatch_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count": 64,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count": 48,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count": 16,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes": 0,
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count": 0,
        "premap_consumer_prelaunch_boundary_checked_count": 4,
        "premap_consumer_prelaunch_boundary_aligned_count": 4,
        "premap_consumer_prelaunch_boundary_aligned_rate": 1.0,
        "premap_consumer_prelaunch_handle_available_count": 4,
        "premap_consumer_prelaunch_handle_available_rate": 1.0,
        "premap_consumer_prelaunch_block_count": 16,
        "premap_consumer_prelaunch_block_size_max": 16,
        "premap_consumer_prelaunch_unique_expert_count": 16,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count": 4,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_count": 4,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate": 1.0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_count": 4,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate": 1.0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count": 16,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max": 4,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count": 16,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count": 0,
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count": 0,
        "unrelated_debug_key": 99,
    }
    performance: dict[str, object] = {}

    _add_runtime_shadow_aggregate_to_performance(performance, aggregate)

    assert performance["runtime_shadow_aggregate_premap_consumer_mapping_count"] == 3
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_hit_count"
        ]
        == 7
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_aux_metadata_miss_count"
        ]
        == 3
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_no_handle_parts_count"
        ]
        == 14
    )
    assert performance["runtime_shadow_aggregate_premap_consumer_readonly_lookup_count"] == 15
    assert (
        performance["runtime_shadow_aggregate_premap_consumer_readonly_handle_hit_rate"]
        == 0.875
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_readonly_evicted_before_consume_count"
        ]
        == 2
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_readonly_handle_parity_ok_rate"
        ]
        == 0.75
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_real_handle_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_real_handle_backed_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_read_lookup_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_read_hit_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_read_hit_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_read_ok_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_executed_count"
        ]
        == 4
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_ok_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max"
        ]
        == 4
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count"
        ]
        == 4
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max"
        ]
        == 4
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count"
        ]
        == 4
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count"
        ]
        == 64
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count"
        ]
        == 48
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_prelaunch_boundary_checked_count"
        ]
        == 4
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_prelaunch_boundary_aligned_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_prelaunch_handle_available_rate"
        ]
        == 1.0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_prelaunch_block_count"
        ]
        == 16
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_violation_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        performance[
            "runtime_shadow_aggregate_premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count"
        ]
        == 0
    )
    assert "runtime_shadow_aggregate_unrelated_debug_key" not in performance


def test_recorder_exports_native_typed_consumer_input_sample(tmp_path):
    class _Table:
        row_count = 2
        column_count = 4
        object_hash = "table-hash"
        schema_hash = PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        payload_bytes = 0
        ready_credit = False
        changes_router = False
        changes_descriptor_order = False
        passed_to_kernel = False
        changes_kernel_launch_args = False

        def to_native_typed_consumer_input_dict(self):
            return {
                "descriptor_ptr": [11, 22],
                "packed_weight_descriptor": [33, 44],
                "scale_metadata_handle": [55, 66],
                "aux_metadata_handle": [0, 0],
                "expert_id": [3, 7],
                "address_key_hash": [77, 88],
                "_meta": {
                    "schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
                    "row_count": 2,
                    "column_count": 4,
                    "table_object_hash": "table-hash",
                    "payload_bytes": 0,
                    "ready_credit": False,
                    "changes_router": False,
                    "changes_descriptor_order": False,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                },
            }

    recorder = VllmRouterRecorder(
        top_k=8,
        shadow_premap_native_typed_consumer_input_export_enabled=True,
        shadow_premap_native_typed_consumer_input_export_dir=str(tmp_path),
        shadow_premap_native_typed_consumer_input_export_max_tables=1,
        shadow_premap_native_typed_consumer_input_export_max_rows=8,
    )
    recorder.request_id = "sample/with spaces"
    recorder.sequence_id = 5
    recorder.shadow_premap_event_token_index = 9

    path = recorder._maybe_export_native_typed_consumer_input(_Table(), layer_id=12)
    assert path is not None
    assert path.exists()
    assert "sample_with_spaces" in path.name
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["descriptor_ptr"] == [11, 22]
    assert payload["_meta"]["payload_bytes"] == 0
    assert payload["_meta"]["passed_to_kernel"] is False
    assert payload["_export_context"]["layer_id"] == 12
    assert payload["_export_context"]["ready_credit"] is False
    assert payload["_export_context"]["changes_router"] is False
    assert payload["_export_context"]["changes_descriptor_order"] is False

    second = recorder._maybe_export_native_typed_consumer_input(_Table(), layer_id=13)
    assert second is None
    assert len(list(tmp_path.glob("premap_native_typed_consumer_input_*.json"))) == 1


def test_premap_native_typed_consumer_input_export_respects_stride(tmp_path: Path):
    class _Table:
        row_count = 2
        column_count = 4
        object_hash = "table-hash"
        schema_hash = PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        payload_bytes = 0
        ready_credit = False
        changes_router = False
        changes_descriptor_order = False
        passed_to_kernel = False
        changes_kernel_launch_args = False

        def to_native_typed_consumer_input_dict(self):
            return {
                "descriptor_ptr": [11, 22],
                "packed_weight_descriptor": [33, 44],
                "scale_metadata_handle": [55, 66],
                "aux_metadata_handle": [0, 0],
                "expert_id": [3, 7],
                "address_key_hash": [77, 88],
                "_meta": {
                    "schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
                    "row_count": 2,
                    "column_count": 4,
                    "table_object_hash": "table-hash",
                    "payload_bytes": 0,
                    "ready_credit": False,
                    "changes_router": False,
                    "changes_descriptor_order": False,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                },
            }

    recorder = VllmRouterRecorder(
        top_k=8,
        shadow_premap_native_typed_consumer_input_export_enabled=True,
        shadow_premap_native_typed_consumer_input_export_dir=str(tmp_path),
        shadow_premap_native_typed_consumer_input_export_max_tables=2,
        shadow_premap_native_typed_consumer_input_export_max_rows=8,
        shadow_premap_native_typed_consumer_input_export_stride=2,
    )
    recorder.request_id = "sample"
    recorder.sequence_id = 5
    recorder.shadow_premap_event_token_index = 9

    first = recorder._maybe_export_native_typed_consumer_input(_Table(), layer_id=10)
    second = recorder._maybe_export_native_typed_consumer_input(_Table(), layer_id=11)
    third = recorder._maybe_export_native_typed_consumer_input(_Table(), layer_id=12)
    fourth = recorder._maybe_export_native_typed_consumer_input(_Table(), layer_id=13)

    assert first is not None
    assert second is None
    assert third is not None
    assert fourth is None
    assert "layer10" in first.name
    assert "layer12" in third.name
    assert len(list(tmp_path.glob("premap_native_typed_consumer_input_*.json"))) == 2


def test_premap_payload_cache_producer_state_packet_export_respects_stride(
    tmp_path: Path,
):
    packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=4,
        previous_experts=(1,),
        current_experts=(2,),
        state_owner="producer",
        issue_source="prelaunch_observed_transition_premap_shadow",
        transition_summary_mode="matrix_topk",
        transition_topk_count=8,
        max_num_experts=16,
    )
    assert packet.ready
    recorder = VllmRouterRecorder(
        top_k=8,
        shadow_num_experts=16,
        shadow_premap_payload_cache_producer_state_packet_export_enabled=True,
        shadow_premap_payload_cache_producer_state_packet_export_dir=str(tmp_path),
        shadow_premap_payload_cache_producer_state_packet_export_max_packets=2,
        shadow_premap_payload_cache_producer_state_packet_export_stride=2,
        shadow_premap_payload_cache_producer_state_packet_export_paths=[],
    )
    recorder.request_id = "packet"
    recorder.sequence_id = 3
    recorder.shadow_premap_event_token_index = 5

    first = recorder._maybe_export_premap_payload_cache_producer_state_packet(
        packet,
        layer_id=4,
    )
    second = recorder._maybe_export_premap_payload_cache_producer_state_packet(
        packet,
        layer_id=5,
    )
    third = recorder._maybe_export_premap_payload_cache_producer_state_packet(
        packet,
        layer_id=6,
    )
    fourth = recorder._maybe_export_premap_payload_cache_producer_state_packet(
        packet,
        layer_id=7,
    )

    assert first is not None
    assert second is None
    assert third is not None
    assert fourth is None
    assert "layer4" in first.name
    assert "layer6" in third.name
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["previous_experts"] == [1]
    assert payload["current_experts"] == [2]
    assert payload["native_abi_field_count"] > 0
    assert payload["payload_bytes"] == 0
    assert payload["issued_payload_count"] == 0
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["payload_transfer_enabled"] is False
    assert payload["live_payload_runtime_enabled"] is False
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["payload_deref_runtime_allowed"] is False
    assert payload["kernel_arg_pass"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["full_fetch_runtime_allowed"] is False
    assert payload["live_runtime_instantiated"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False
    assert payload["issue_candidate_count"] == 1
    assert payload["issue_candidate_first_expert"] == 1
    assert payload["issue_candidate_last_expert"] == 1
    assert payload["issue_candidate_hash"] == "082f2307b4e88e77"
    assert payload["_export_context"]["payload_bytes"] == 0
    assert payload["_export_context"]["issued_payload_count"] == 0
    assert payload["_export_context"]["ready_credit"] is False
    assert payload["_export_context"]["ready_before_demand_credit"] is False
    assert payload["_export_context"]["payload_transfer_enabled"] is False
    assert payload["_export_context"]["live_payload_runtime_enabled"] is False
    assert payload["_export_context"]["payload_transfer_runtime_enabled"] is False
    assert payload["_export_context"]["payload_deref_allowed"] is False
    assert payload["_export_context"]["payload_deref_runtime_allowed"] is False
    assert payload["_export_context"]["kernel_arg_pass"] is False
    assert payload["_export_context"]["kernel_arg_pass_allowed"] is False
    assert payload["_export_context"]["full_fetch_runtime_allowed"] is False
    assert payload["_export_context"]["live_runtime_instantiated"] is False
    assert payload["_export_context"]["real_ready_credit_granted"] is False
    assert payload["_export_context"]["passed_to_kernel"] is False
    assert payload["_export_context"]["changes_kernel_launch_args"] is False
    assert payload["_export_context"]["uses_current_wna16_args"] is False
    assert payload["_export_context"]["passes_current_wna16_args"] is False
    assert payload["_export_context"]["measures_tpot"] is False
    assert payload["_export_context"]["measures_vllm_latency"] is False
    assert payload["_export_context"]["issue_candidate_count"] == 1
    assert payload["_export_context"]["issue_candidate_first_expert"] == 1
    assert payload["_export_context"]["issue_candidate_last_expert"] == 1
    assert payload["_export_context"]["issue_candidate_hash"] == "082f2307b4e88e77"
    assert payload["_export_context"]["state_hash"] == packet.state_hash
    assert (
        recorder._premap_payload_cache_producer_state_packet_export_nonempty_issue_count
        == 2
    )
    assert (
        recorder._premap_payload_cache_producer_state_packet_export_first_nonempty_issue_index
        == 0
    )
    assert (
        recorder._premap_payload_cache_producer_state_packet_export_first_nonempty_issue_path
        == str(first)
    )
    assert (
        recorder._premap_payload_cache_producer_state_packet_export_first_nonempty_issue_count
        == 1
    )
    assert (
        recorder._premap_payload_cache_producer_state_packet_export_first_nonempty_issue_hash
        == "082f2307b4e88e77"
    )
    assert (
        len(list(tmp_path.glob("premap_payload_cache_producer_state_packet_*.json")))
        == 2
    )


def test_premap_payload_cache_export_nonempty_issue_summary(tmp_path: Path):
    empty = tmp_path / "empty.json"
    nonempty = tmp_path / "nonempty.json"
    bad = tmp_path / "bad.json"
    empty.write_text(
        json.dumps(
            {
                "previous_experts": [],
                "transition_topk_count": 8,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    nonempty.write_text(
        json.dumps(
            {
                "previous_experts": [1, 3],
                "transition_topk_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    bad.write_text("not json\n", encoding="utf-8")

    summary = _premap_payload_cache_export_nonempty_issue_summary(
        [empty, nonempty, bad]
    )

    assert summary == {
        "nonempty_issue_count": 1,
        "first_nonempty_issue_index": 1,
        "first_nonempty_issue_path": str(nonempty),
        "first_nonempty_issue_count": 1,
        "first_nonempty_issue_hash": "082f2307b4e88e77",
        "scan_error_count": 1,
    }


def test_premap_payload_cache_export_nonempty_issue_summary_keeps_first_index_zero(
    tmp_path: Path,
):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(
        json.dumps(
            {
                "previous_experts": [2],
                "transition_topk_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    second.write_text(
        json.dumps(
            {
                "previous_experts": [1],
                "transition_topk_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([first, second])

    assert summary["nonempty_issue_count"] == 2
    assert summary["first_nonempty_issue_index"] == 0
    assert summary["first_nonempty_issue_path"] == str(first)
    assert summary["first_nonempty_issue_count"] == 1
    assert summary["first_nonempty_issue_hash"] == "08395307b4f1348c"
    assert summary["scan_error_count"] == 0


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_malformed_self_described_issue(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed.json"
    valid = tmp_path / "valid.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": [],
                "transition_topk_count": 8,
                "issue_candidate_count": 1,
                "issue_candidate_hash": "082f2307b4e88e77",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    valid.write_text(
        json.dumps(
            {
                "previous_experts": [1],
                "transition_topk_count": 1,
                "issue_candidate_experts": [1],
                "issue_candidate_count": 1,
                "issue_candidate_first_expert": 1,
                "issue_candidate_last_expert": 1,
                "issue_candidate_hash": "082f2307b4e88e77",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary(
        [malformed, valid]
    )

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 1
    assert summary["first_nonempty_issue_index"] == 1
    assert summary["first_nonempty_issue_path"] == str(valid)
    assert summary["first_nonempty_issue_hash"] == "082f2307b4e88e77"


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_negative_topk(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed_negative_topk.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": [1, 2],
                "transition_topk_count": -1,
                "issue_candidate_count": 1,
                "issue_candidate_hash": "082f2307b4e88e77",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([malformed])

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 0
    assert summary["first_nonempty_issue_index"] == -1
    assert summary["first_nonempty_issue_path"] is None


def _write_shifted_issue_packet(
    path: Path,
    *,
    token_index: int,
    layer_id: int = 0,
    issue_experts: list[int] | None = None,
    token_source: str = "decode_workload_collector",
    sample_idx: int | None = 0,
    record_id: str | None = "rec-0",
    payload_bytes=0,
):
    if issue_experts is None:
        issue_experts = [1]
    issue_hash = _premap_payload_cache_issue_hash(issue_experts)
    payload = {
        "layer_id": layer_id,
        "ready": True,
        "issue_candidate_experts": issue_experts,
        "issue_candidate_count": len(issue_experts),
        "issue_candidate_first_expert": issue_experts[0] if issue_experts else -1,
        "issue_candidate_last_expert": issue_experts[-1] if issue_experts else -1,
        "issue_candidate_hash": issue_hash,
        "payload_bytes": payload_bytes,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "real_ready_credit_granted": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "_export_context": {
            "layer_id": layer_id,
            "token_index": token_index,
            "token_index_source": token_source,
            "sample_idx": sample_idx,
            "record_id": record_id,
            "sequence_id": 0,
            "issue_candidate_count": len(issue_experts),
            "issue_candidate_first_expert": (
                issue_experts[0] if issue_experts else -1
            ),
            "issue_candidate_last_expert": (
                issue_experts[-1] if issue_experts else -1
            ),
            "issue_candidate_hash": issue_hash,
            "payload_bytes": payload_bytes,
            "ready_credit": False,
            "ready_before_demand_credit": False,
            "payload_transfer_enabled": False,
            "payload_deref_allowed": False,
            "kernel_arg_pass": False,
            "kernel_arg_pass_allowed": False,
            "real_ready_credit_granted": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
        },
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _load_shifted_issue_packet(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_shifted_issue_packet(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_premap_payload_cache_shifted_issue_runtime_shadow_summary(tmp_path: Path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write_shifted_issue_packet(first, token_index=3, issue_experts=[1, 2])
    _write_shifted_issue_packet(second, token_index=4, issue_experts=[2])

    summary = _premap_payload_cache_shifted_issue_runtime_shadow_summary(
        [first, second],
        issue_lead_tokens=1,
    )

    assert summary["enabled"] is True
    assert summary["issue_lead_tokens"] == 1
    assert summary["packet_count"] == 2
    assert summary["schedulable_packet_count"] == 2
    assert summary["empty_issue_exempt_count"] == 0
    assert summary["safe_packet_count"] == 2
    assert summary["unsafe_packet_count"] == 0
    assert summary["invalid_packet_count"] == 0
    assert summary["clamped_issue_count"] == 0
    assert summary["duplicate_demand_key_count"] == 0
    assert summary["duplicate_issue_key_count"] == 0
    assert summary["unique_demand_key_count"] == 2
    assert summary["unique_issue_key_count"] == 2
    assert summary["total_issue_candidates"] == 3
    assert summary["payload_bytes"] == 0
    assert summary["passed_to_kernel"] is False
    assert summary["measures_tpot"] is False


def test_premap_payload_cache_shifted_issue_runtime_shadow_summary_empty_config_exempt(
    tmp_path: Path,
):
    packet = tmp_path / "empty_config.json"
    _write_shifted_issue_packet(
        packet,
        token_index=-1,
        issue_experts=[],
        token_source="config",
        sample_idx=None,
        record_id=None,
    )

    summary = _premap_payload_cache_shifted_issue_runtime_shadow_summary(
        [packet],
        issue_lead_tokens=1,
        allow_empty_config_packets=True,
    )

    assert summary["packet_count"] == 1
    assert summary["safe_packet_count"] == 1
    assert summary["schedulable_packet_count"] == 0
    assert summary["empty_issue_exempt_count"] == 1
    assert summary["invalid_packet_count"] == 0


def test_premap_payload_cache_shifted_issue_runtime_shadow_summary_rejects_bool_payload_bytes(
    tmp_path: Path,
):
    packet = tmp_path / "bool_payload.json"
    _write_shifted_issue_packet(
        packet,
        token_index=2,
        issue_experts=[1],
        payload_bytes=False,
    )

    summary = _premap_payload_cache_shifted_issue_runtime_shadow_summary(
        [packet],
        issue_lead_tokens=1,
    )

    assert summary["packet_count"] == 1
    assert summary["safe_packet_count"] == 0
    assert summary["unsafe_packet_count"] == 1
    assert summary["schedulable_packet_count"] == 0


def test_premap_payload_cache_shifted_issue_runtime_shadow_summary_invalid_source_not_schedulable(
    tmp_path: Path,
):
    packet = tmp_path / "invalid_source.json"
    _write_shifted_issue_packet(
        packet,
        token_index=2,
        issue_experts=[1],
        token_source="manual",
    )

    summary = _premap_payload_cache_shifted_issue_runtime_shadow_summary(
        [packet],
        issue_lead_tokens=1,
    )

    assert summary["packet_count"] == 1
    assert summary["invalid_packet_count"] == 1
    assert summary["schedulable_packet_count"] == 0
    assert summary["total_issue_candidates"] == 0
    assert summary["unique_demand_key_count"] == 0
    assert summary["unique_issue_key_count"] == 0


def test_premap_payload_cache_shifted_issue_runtime_shadow_summary_rejects_bool_issue_count(
    tmp_path: Path,
):
    packet = tmp_path / "bool_issue_count.json"
    _write_shifted_issue_packet(packet, token_index=2, issue_experts=[1])
    payload = _load_shifted_issue_packet(packet)
    payload["issue_candidate_count"] = True
    payload["_export_context"]["issue_candidate_count"] = True
    _dump_shifted_issue_packet(packet, payload)

    summary = _premap_payload_cache_shifted_issue_runtime_shadow_summary(
        [packet],
        issue_lead_tokens=1,
    )

    assert summary["packet_count"] == 1
    assert summary["invalid_packet_count"] == 1
    assert summary["schedulable_packet_count"] == 0


def test_premap_payload_cache_shifted_issue_runtime_shadow_summary_large_payload_bytes_unsafe(
    tmp_path: Path,
):
    packet = tmp_path / "large_payload_bytes.json"
    _write_shifted_issue_packet(
        packet,
        token_index=2,
        issue_experts=[1],
        payload_bytes=10**500,
    )

    summary = _premap_payload_cache_shifted_issue_runtime_shadow_summary(
        [packet],
        issue_lead_tokens=1,
    )

    assert summary["packet_count"] == 1
    assert summary["safe_packet_count"] == 0
    assert summary["unsafe_packet_count"] == 1
    assert summary["schedulable_packet_count"] == 0


def test_premap_payload_cache_shifted_issue_runtime_shadow_summary_rejects_context_bool_issue_count(
    tmp_path: Path,
):
    packet = tmp_path / "context_bool_issue_count.json"
    _write_shifted_issue_packet(packet, token_index=2, issue_experts=[1])
    payload = _load_shifted_issue_packet(packet)
    payload["_export_context"]["issue_candidate_count"] = True
    _dump_shifted_issue_packet(packet, payload)

    summary = _premap_payload_cache_shifted_issue_runtime_shadow_summary(
        [packet],
        issue_lead_tokens=1,
    )

    assert summary["packet_count"] == 1
    assert summary["safe_packet_count"] == 1
    assert summary["invalid_packet_count"] == 1
    assert summary["schedulable_packet_count"] == 0


def test_premap_payload_cache_shifted_issue_runtime_shadow_summary_rejects_context_bool_layer_id(
    tmp_path: Path,
):
    packet = tmp_path / "context_bool_layer_id.json"
    _write_shifted_issue_packet(packet, token_index=2, issue_experts=[1])
    payload = _load_shifted_issue_packet(packet)
    payload["_export_context"]["layer_id"] = True
    _dump_shifted_issue_packet(packet, payload)

    summary = _premap_payload_cache_shifted_issue_runtime_shadow_summary(
        [packet],
        issue_lead_tokens=1,
    )

    assert summary["packet_count"] == 1
    assert summary["safe_packet_count"] == 1
    assert summary["invalid_packet_count"] == 1
    assert summary["schedulable_packet_count"] == 0


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_nonlist_previous_experts(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed_nonlist_previous.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": "12",
                "transition_topk_count": 1,
                "issue_candidate_count": 1,
                "issue_candidate_hash": "082f2307b4e88e77",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([malformed])

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 0
    assert summary["first_nonempty_issue_index"] == -1
    assert summary["first_nonempty_issue_path"] is None


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_negative_previous_experts(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed_negative_previous.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": [-1, 5],
                "transition_topk_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([malformed])

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 0
    assert summary["first_nonempty_issue_index"] == -1
    assert summary["first_nonempty_issue_path"] is None


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_bad_issue_bounds(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed_bad_bounds.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": [1, 2],
                "transition_topk_count": 1,
                "issue_candidate_experts": [1],
                "issue_candidate_count": 1,
                "issue_candidate_first_expert": 2,
                "issue_candidate_last_expert": 1,
                "issue_candidate_hash": "082f2307b4e88e77",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([malformed])

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 0


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_bad_issue_expert_list(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed_bad_issue_list.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": [1, 2],
                "transition_topk_count": 1,
                "issue_candidate_experts": [2],
                "issue_candidate_count": 1,
                "issue_candidate_first_expert": 1,
                "issue_candidate_last_expert": 1,
                "issue_candidate_hash": "082f2307b4e88e77",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([malformed])

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 0


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_null_issue_expert_list(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed_null_issue_list.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": [1],
                "transition_topk_count": 1,
                "issue_candidate_experts": None,
                "issue_candidate_count": 1,
                "issue_candidate_first_expert": 1,
                "issue_candidate_last_expert": 1,
                "issue_candidate_hash": "082f2307b4e88e77",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([malformed])

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 0


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_unknown_issue_prefix(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed_unknown_issue_prefix.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": [1],
                "transition_topk_count": 1,
                "issue_candidate_debug": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([malformed])

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 0


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_numeric_issue_hash(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed_numeric_issue_hash.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": [11, 0],
                "transition_topk_count": 2,
                "issue_candidate_experts": [11, 0],
                "issue_candidate_count": 2,
                "issue_candidate_first_expert": 11,
                "issue_candidate_last_expert": 0,
                "issue_candidate_hash": 2742631898372054,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([malformed])

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 0


def test_premap_payload_cache_export_nonempty_issue_summary_rejects_partial_issue_fields(
    tmp_path: Path,
):
    malformed = tmp_path / "malformed_partial_issue_fields.json"
    malformed.write_text(
        json.dumps(
            {
                "previous_experts": [1],
                "transition_topk_count": 1,
                "issue_candidate_count": 1,
                "issue_candidate_hash": "082f2307b4e88e77",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _premap_payload_cache_export_nonempty_issue_summary([malformed])

    assert summary["scan_error_count"] == 1
    assert summary["nonempty_issue_count"] == 0


class _ExpertGate(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(torch.ones(1, 2))

    def forward(self, hidden_states: torch.Tensor):
        return hidden_states @ self.weight.t(), None


class _FakeAwqConsumerLayer(torch.nn.Module):
    def __init__(self, num_experts: int = 6) -> None:
        super().__init__()
        self.register_buffer("expert_map", torch.arange(num_experts, dtype=torch.int32))
        self.register_buffer(
            "w13_weight_packed",
            torch.arange(num_experts * 4, dtype=torch.int32).reshape(num_experts, 4),
        )
        self.register_buffer(
            "w2_weight_packed",
            torch.arange(num_experts * 4, dtype=torch.int32).reshape(num_experts, 4),
        )
        self.register_buffer(
            "w13_weight_scale",
            torch.arange(num_experts * 2, dtype=torch.float32).reshape(num_experts, 2),
        )
        self.register_buffer(
            "w2_weight_scale",
            torch.arange(num_experts * 2, dtype=torch.float32).reshape(num_experts, 2),
        )


def _assert_kernel_arg_shadow_table_event(consumer: dict[str, object]) -> None:
    assert consumer["premap_consumer_descriptor_prep_kernel_arg_shadow_table_mode"] == (
        "readonly_kernel_arg_shadow_table"
    )
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_order_source"
    ] == "canonical_address_key_order"
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count"
    ] == 2
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count"
    ] == 4
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
    ]
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_order_hash"
    ]
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ordered_row_hash"
    ]
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count"
    ] == 2
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count"
    ] == 0
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count"
    ] == 0
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok"
    ] is True
    assert consumer["premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok"] is True
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes"
    ] == 0
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit"
    ] is False
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_router"
    ] is False
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_descriptor_order"
    ] is False
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_kernel_launch_args"
    ] is False
    assert consumer[
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel"
    ] is False


def _assert_consumer_shim_table_consume_event(consumer: dict[str, object]) -> None:
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
    ] == "readonly_consume_kernel_arg_shadow_table"
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
    ] == "canonical_address_key_order"
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
        ]
        is True
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count"
        ]
        == 8
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count"
        ]
        == 6
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count"
        ]
        == 0
    )
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_hit_counts"
    ] == {
        "descriptor_ptr": 2,
        "packed_weight_descriptor": 2,
        "scale_metadata_handle": 2,
        "aux_metadata_handle": 0,
    }
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_miss_counts"
    ] == {
        "descriptor_ptr": 0,
        "packed_weight_descriptor": 0,
        "scale_metadata_handle": 0,
        "aux_metadata_handle": 2,
    }
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode"
        ]
        == "readonly_kernel_arg_handoff_dry_run"
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready"
        ]
        is True
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count"
        ]
        == 4
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count"
        ]
        == 6
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode"
        ]
        == "readonly_kernel_arg_handoff_shadow_slot"
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready"
        ]
        is True
    )
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash"
    ]
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_table_object_hash"
        ]
        == consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_hash"
        ]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count"
        ]
        == 4
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count"
        ]
        == 6
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode"
        ]
        == "readonly_kernel_arg_handoff_mirror"
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready"
        ]
        is True
    )
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash"
    ]
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash"
        ]
        == consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash"
        ]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_table_object_hash"
        ]
        == consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_hash"
        ]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count"
        ]
        == 4
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count"
        ]
        == 6
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode"
        ]
        == "readonly_kernel_arg_handoff_attempt"
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready"
        ]
        is True
    )
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash"
    ]
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash"
        ]
        == consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash"
        ]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash"
        ]
        == consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash"
        ]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_table_object_hash"
        ]
        == consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_hash"
        ]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count"
        ]
        == 4
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready"
        ]
        is True
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked"
        ]
        is True
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason"
        ]
        == "kernel_arg_handoff_disabled_noop_gate"
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode"
        ]
        == "readonly_kernel_arg_handoff_live_toggle"
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready"
        ]
        is True
    )
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash"
    ]
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash"
        ]
        == consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash"
        ]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash"
        ]
        == consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_hash"
        ]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed"
        ]
        is True
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready"
        ]
        is True
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked"
        ]
        is True
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
        ]
        == "kernel_arg_handoff_live_disabled"
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_changes_kernel_launch_args"
        ]
        is False
    )


def _assert_consumer_shim_prep_execution_dry_run_event(
    consumer: dict[str, object],
) -> None:
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_mode"
    ] == "readonly_descriptor_address_prep_execution_dry_run"
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_source"
    ] == "kernel_arg_shadow_table_object"
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok"
        ]
        is True
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count"
        ]
        == 4
    )
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash"
    ]
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_object_hash"
    ]
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok"
        ]
        is True
    )
    for field in (
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count",
    ):
        assert consumer[field] == 2
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count"
        ]
        == 8
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count"
        ]
        == 6
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count"
        ]
        == 0
    )
    for field in (
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count",
    ):
        assert consumer[field] == 2
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count"
        ]
        == 0
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel"
        ]
        is False
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes"
        ]
        == 0
    )


def test_vllm_router_recorder_shadow_sink_is_optional():
    recorder = VllmRouterRecorder(top_k=2)
    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [3, 4]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
    )

    assert len(recorder.calls) == 1


def test_shared_expert_custom_gate_enabled_in_minimal_modes() -> None:
    default_recorder = VllmRouterRecorder(top_k=2)
    assert _shared_expert_custom_gate_enabled(default_recorder) is False

    inplace_recorder = VllmRouterRecorder(
        top_k=2,
        shadow_shared_expert_output_gate_postprocess="inplace",
    )
    assert _shared_expert_custom_gate_enabled(inplace_recorder) is True

    fused_recorder = VllmRouterRecorder(
        top_k=2,
        shadow_shared_expert_output_gate_postprocess="fused_triton",
    )
    assert _shared_expert_custom_gate_enabled(fused_recorder) is True


def test_shared_expert_default_postprocess_inplace_matches_default() -> None:
    hidden = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    out = torch.tensor([[2.0, 3.0], [4.0, 5.0]])
    gate = _ExpertGate()

    expected = _run_shared_expert_output_gate_default_postprocess(
        hidden_states=hidden,
        out=out.clone(),
        expert_gate=gate,
        postprocess="default",
    )
    actual = _run_shared_expert_output_gate_default_postprocess(
        hidden_states=hidden,
        out=out.clone(),
        expert_gate=gate,
        postprocess="inplace",
    )

    torch.testing.assert_close(actual, expected)


def test_shared_expert_default_postprocess_accepts_tensor_gate_output() -> None:
    hidden = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    out = torch.tensor([[2.0, 3.0], [4.0, 5.0]])
    gate = torch.nn.Linear(2, 1, bias=False)
    torch.nn.init.ones_(gate.weight)

    expected_gate = torch.sigmoid(hidden @ gate.weight.t())
    expected = out * expected_gate
    actual = _run_shared_expert_output_gate_default_postprocess(
        hidden_states=hidden,
        out=out.clone(),
        expert_gate=gate,
        postprocess="default",
    )

    torch.testing.assert_close(actual, expected)


def test_unwrap_vllm_projection_output_accepts_tensor_or_tuple() -> None:
    value = torch.tensor([[1.0]])
    assert _unwrap_vllm_projection_output(value) is value
    assert _unwrap_vllm_projection_output((value, None)) is value

    with pytest.raises(TypeError):
        _unwrap_vllm_projection_output((None, value))


def test_shared_expert_fused_unsupported_error_is_detected() -> None:
    assert _shared_expert_fused_gate_unsupported(
        SharedExpertFusedGateUnsupportedError(
            "fused shared gate requires a bias-free weight parameter"
        )
    )
    assert not _shared_expert_fused_gate_unsupported(
        RuntimeError("fused shared gate requires a bias-free weight parameter")
    )
    assert not _shared_expert_fused_gate_unsupported(RuntimeError("other failure"))


def test_shared_expert_fused_gate_runtime_errors_are_fallbackable_except_oom() -> None:
    assert _shared_expert_fused_gate_fallbackable(
        SharedExpertFusedGateUnsupportedError("unsupported")
    )
    assert _shared_expert_fused_gate_fallbackable(
        RuntimeError("triton launch failed")
    )
    assert not _shared_expert_fused_gate_fallbackable(
        RuntimeError("HIP error: out of memory")
    )


def test_vllm_router_recorder_writes_shadow_outcome_events():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )
    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [3, 4]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
    )

    assert len(sink.events) == 2
    first = sink.events[0].as_dict()
    second = sink.events[1].as_dict()
    assert first["event_type"] == "outcome"
    assert first["shadow_event_id"] == "req:5:10:3"
    assert first["true_topk_experts"] == [1, 2]
    assert first["true_topk_weights"] == pytest.approx([0.8, 0.2])
    assert first["top1_ready"] is False
    assert first["weighted_top1_miss"] == pytest.approx(0.8)
    assert second["shadow_event_id"] == "req:5:11:3"
    assert second["true_topk_experts"] == [3, 4]


def test_decoder_component_handoff_aggregate_flushes_per_layer_phase_bucket():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=15.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=4,
        component="attention_linear_handoff_out_proj",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention",
        elapsed_us=50.0,
        num_tokens=1,
        phase="decode",
    )

    assert len(sink.events) == 1
    assert sink.events[0]["event_type"] == "decoder_component_timing"
    recorder.flush_decoder_component_aggregates()

    aggregate_events = [
        event for event in sink.events if event["event_type"] == "decoder_component_aggregate"
    ]
    assert len(aggregate_events) == 2
    by_layer = {event["layer"]: event for event in aggregate_events}
    layer3 = by_layer[3]
    layer4 = by_layer[4]
    assert layer3["shadow_event_id"] == "req:7:-1:3"
    assert layer3["decoder_component_aggregate_count"] == 2
    assert layer3["decoder_component_aggregate_components"][
        "attention_linear_handoff_norm"
    ] == {"sum_us": 25.0, "count": 2}
    assert layer4["decoder_component_aggregate_components"][
        "attention_linear_handoff_out_proj"
    ] == {"sum_us": 20.0, "count": 1}

    recorder.flush_decoder_component_aggregates()
    assert len(
        [
            event
            for event in sink.events
            if event["event_type"] == "decoder_component_aggregate"
        ]
    ) == 2


def test_decoder_component_handoff_counter_only_flushes_fixed_component_payload():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_counter_only",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=15.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_out_proj",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
    )

    recorder.flush_decoder_component_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "decoder_component_aggregate"
    assert event["decoder_component_aggregate_mode"] == "attention_handoff_counter_only"
    assert event["decoder_component_aggregate_count"] == 3
    assert event["decoder_component_aggregate_components"][
        "attention_linear_handoff_norm"
    ] == {"sum_us": 25.0, "count": 2}
    assert event["decoder_component_aggregate_components"][
        "attention_linear_handoff_out_proj"
    ] == {"sum_us": 20.0, "count": 1}


def test_decoder_component_handoff_no_write_drops_aggregates_on_flush():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_counter_only_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.flush_decoder_component_aggregates()

    assert sink.events == []


def test_decoder_component_handoff_aggregate_no_write_drops_aggregates_on_flush():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_aggregate_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.flush_decoder_component_aggregates()

    assert len(sink.events) == 1
    assert sink.events[0]["event_type"] == "decoder_component_timing"
    assert sink.events[0]["decoder_component"] == "attention"


def test_decoder_component_handoff_counter_only_falls_back_for_unknown_handoff():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_counter_only",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_new_component",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.flush_decoder_component_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "decoder_component_timing"
    assert event["decoder_component"] == "attention_linear_handoff_new_component"
    assert event["decoder_component_logging_fallback"] == "unknown_handoff_component"


def test_decoder_component_handoff_counter_no_write_drops_unknown_handoff():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_counter_only_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_new_component",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.flush_decoder_component_aggregates()

    assert sink.events == []


def test_moe_substage_aggregate_flushes_per_layer_phase_bucket():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_direct_layer",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_direct_layer",
        elapsed_us=15.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_output_gate",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="fallback",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="quant_method_apply",
        elapsed_us=50.0,
        num_tokens=1,
        phase="decode",
        status="not_shared",
    )

    assert sink.events == []
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "moe_substage_aggregate"
    assert event["shadow_event_id"] == "req:7:-1:3"
    assert event["moe_substage_aggregate_count"] == 3
    assert event["moe_substage_aggregate_component_count"] == 3
    assert event["moe_substage_aggregate_count_match"] is True
    assert event["moe_substage_aggregate_components"][
        "experts_shared_direct_layer"
    ] == {
        "sum_us": 25.0,
        "raw_sum_us": 25.0,
        "count": 2,
        "estimated_count": 2,
        "status_counts": {"ok": 2},
        "estimated_status_counts": {"ok": 2},
        "sample_period": 1,
    }
    assert event["moe_substage_aggregate_components"][
        "experts_shared_output_gate"
    ] == {
        "sum_us": 20.0,
        "raw_sum_us": 20.0,
        "count": 1,
        "estimated_count": 1,
        "status_counts": {"fallback": 1},
        "estimated_status_counts": {"fallback": 1},
        "sample_period": 1,
    }
    assert "quant_method_apply" not in event["moe_substage_aggregate_components"]


def test_moe_substage_shared_body_mode_only_records_direct_layer():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared_body",
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    for substage in (
        "experts_shared_determine_order",
        "experts_shared_w1",
        "experts_shared_direct_layer",
        "experts_shared_output_gate",
        "quant_method_apply",
    ):
        recorder.write_moe_substage_timing(
            layer_id=3,
            substage=substage,
            elapsed_us=10.0,
            num_tokens=1,
            phase="decode",
            status="ok",
        )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "moe_substage_aggregate"
    assert event["moe_substage_aggregate_count"] == 1
    assert event["moe_substage_aggregate_component_count"] == 1
    assert event["moe_substage_aggregate_count_match"] is True
    assert set(event["moe_substage_aggregate_components"]) == {
        "experts_shared_direct_layer",
    }


def test_moe_substage_shared_body_regions_records_only_body_buckets():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared_body_regions",
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    for substage in (
        "experts_shared_determine_order",
        "experts_shared_direct_layer",
        "experts_shared_body_core",
        "experts_shared_body_gate_proj",
        "experts_shared_body_gate_apply",
        "experts_shared_body_gate_fused",
        "experts_shared_w1",
        "experts_shared_output_gate",
        "quant_method_apply",
    ):
        recorder.write_moe_substage_timing(
            layer_id=3,
            substage=substage,
            elapsed_us=10.0,
            num_tokens=1,
            phase="decode",
            status="ok",
        )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "moe_substage_aggregate"
    assert event["moe_substage_aggregate_count"] == 5
    assert event["moe_substage_aggregate_component_count"] == 5
    assert event["moe_substage_aggregate_count_match"] is True
    assert set(event["moe_substage_aggregate_components"]) == {
        "experts_shared_direct_layer",
        "experts_shared_body_core",
        "experts_shared_body_gate_proj",
        "experts_shared_body_gate_apply",
        "experts_shared_body_gate_fused",
    }


@pytest.mark.parametrize("mode", ["shared_direct", "shared_coarse"])
def test_moe_substage_shared_body_aliases_only_record_direct_layer(mode: str):
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode=mode,
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_w1",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_direct_layer",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["moe_substage_aggregate_count"] == 1
    assert set(event["moe_substage_aggregate_components"]) == {
        "experts_shared_direct_layer",
    }


@pytest.mark.parametrize("mode", ["shared_direct_regions", "shared_coarse_regions"])
def test_moe_substage_shared_body_regions_aliases_record_body_buckets(mode: str):
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode=mode,
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_w1",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_body_core",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_body_gate_apply",
        elapsed_us=30.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["moe_substage_aggregate_count"] == 2
    assert set(event["moe_substage_aggregate_components"]) == {
        "experts_shared_body_core",
        "experts_shared_body_gate_apply",
    }


def test_moe_substage_aggregate_no_write_drops_flushed_payloads():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared_body_regions",
        shadow_moe_substage_logging_mode="aggregate_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_body_core",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.flush_moe_substage_aggregates()

    assert sink.events == []


def test_moe_substage_shared_aggregate_no_write_drops_flushed_payloads():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared_body_regions",
        shadow_moe_substage_logging_mode="shared_aggregate_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_body_core",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.flush_moe_substage_aggregates()

    assert sink.events == []


def test_moe_substage_sampled_aggregate_scales_decode_samples():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
        shadow_moe_substage_logging_mode="sampled_aggregate",
        shadow_moe_substage_sample_period=2,
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    for elapsed_us in (10.0, 20.0, 30.0):
        recorder.write_moe_substage_timing(
            layer_id=3,
            substage="experts_shared_direct_layer",
            elapsed_us=elapsed_us,
            num_tokens=1,
            phase="decode",
            status="ok",
        )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    component = event["moe_substage_aggregate_components"][
        "experts_shared_direct_layer"
    ]
    assert event["moe_substage_aggregate_count"] == 2
    assert event["moe_substage_sample_period"] == 2
    assert component["count"] == 2
    assert component["estimated_count"] == 4
    assert component["raw_sum_us"] == 40.0
    assert component["sum_us"] == 80.0
    assert component["sample_period"] == 2
    assert component["status_counts"] == {"ok": 2}
    assert component["estimated_status_counts"] == {"ok": 4}


def test_moe_substage_shared_sampled_aggregate_scales_decode_samples():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
        shadow_moe_substage_logging_mode="shared_sampled_aggregate",
        shadow_moe_substage_sample_period=2,
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    for elapsed_us in (10.0, 20.0, 30.0):
        recorder.write_moe_substage_timing(
            layer_id=3,
            substage="experts_shared_direct_layer",
            elapsed_us=elapsed_us,
            num_tokens=1,
            phase="decode",
            status="ok",
        )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    component = event["moe_substage_aggregate_components"][
        "experts_shared_direct_layer"
    ]
    assert event["moe_substage_aggregate_mode"] == "shared_sampled_aggregate"
    assert event["moe_substage_aggregate_count"] == 2
    assert event["moe_substage_aggregate_component_count"] == 2
    assert event["moe_substage_aggregate_count_match"] is True
    assert event["moe_substage_sample_period"] == 2
    assert component["count"] == 2
    assert component["estimated_count"] == 4
    assert component["raw_sum_us"] == 40.0
    assert component["sum_us"] == 80.0
    assert component["sample_period"] == 2


def test_moe_substage_shared_sampled_aggregate_samples_per_substage():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
        shadow_moe_substage_logging_mode="shared_sampled_aggregate",
        shadow_moe_substage_sample_period=2,
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    for substage, base_us in (
        ("experts_shared_direct_layer", 10.0),
        ("experts_shared_output_gate", 100.0),
    ):
        for i in range(3):
            recorder.write_moe_substage_timing(
                layer_id=3,
                substage=substage,
                elapsed_us=base_us + float(i),
                num_tokens=1,
                phase="decode",
                status="ok",
            )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    components = event["moe_substage_aggregate_components"]
    assert event["moe_substage_aggregate_count"] == 4
    assert event["moe_substage_aggregate_component_count"] == 4
    assert event["moe_substage_aggregate_count_match"] is True
    assert event["moe_substage_sample_period"] == 2
    direct = components["experts_shared_direct_layer"]
    gate = components["experts_shared_output_gate"]
    assert direct["count"] == 2
    assert direct["estimated_count"] == 4
    assert direct["raw_sum_us"] == 22.0
    assert direct["sum_us"] == 44.0
    assert gate["count"] == 2
    assert gate["estimated_count"] == 4
    assert gate["raw_sum_us"] == 202.0
    assert gate["sum_us"] == 404.0


def test_vllm_router_recorder_writes_aggregate_shadow_outcome():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="aggregate",
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )
    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [3, 2]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "outcome_aggregate"
    assert row["shadow_event_id"] == "req:5:10:3"
    assert row["token_start"] == 10
    assert row["token_end"] == 12
    assert row["token_count"] == 2
    assert row["top_k"] == 2
    assert row["topk_entry_count"] == 4
    assert row["routed_expert_count"] == 3
    assert row["top1_weight_mean"] == pytest.approx(0.7)


def test_vllm_router_recorder_aggregate_requires_aggregate_sink():
    sink = _OutcomeOnlySink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="aggregate",
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )

    with pytest.raises(TypeError, match="write_outcome_aggregate"):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )


def test_vllm_router_recorder_can_disable_shadow_outcomes():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )
    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [3, 4]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
    )

    assert sink.events == []


def test_vllm_router_recorder_premap_summary_works_with_outcomes_off():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_num_experts=6,
        shadow_premap_descriptor_bytes=64,
        shadow_premap_policy="premap_only",
        shadow_premap_source="current_router_topk_premap_shadow",
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [2, 7], [-1, 3]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3], [0.1, 0.6]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "premap_summary"
    assert row["request_id"] == "req"
    assert row["sequence_id"] == 5
    assert row["token_index"] == -1
    assert row["layer"] == 3
    assert row["premap_policy"] == "premap_only"
    assert row["premap_source"] == "current_router_topk_premap_shadow"
    assert row["premap_descriptor_count"] == 3
    assert row["premap_unique_experts"] == 3
    assert row["premap_actual_bytes"] == 3 * 64
    assert row["premap_payload_bytes"] == 0
    assert row["premap_full_fetch_count"] == 0
    assert row["premap_metadata_count"] == 0
    assert row["premap_changes_router"] is False
    assert row["premap_changes_descriptor_order"] is False
    assert row["premap_ready_credit"] is False


def test_vllm_router_recorder_premap_summary_can_be_sampled_without_skipping_manager():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_premap_summary_sample_period=3,
        shadow_premap_address_manager_capacity=8,
        shadow_premap_descriptor_bytes=64,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    for _ in range(4):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )

    rows = [event.as_dict() for event in sink.events]
    premap_rows = [row for row in rows if row["event_type"] == "premap_summary"]
    assert len(premap_rows) == 2
    assert premap_rows[0]["premap_address_new_count"] == 2
    # Unsampled calls still update the address manager, so the second sampled
    # event observes the fourth prepare call rather than call two.
    assert premap_rows[1]["premap_address_reused_count"] == 6
    assert recorder._last_premap_address_mapping_by_layer[3]["prepare_plan_count"] == 4
    assert recorder._last_premap_address_mapping_by_layer[3]["prepare_record_count"] == 8


def test_vllm_router_recorder_no_sink_prelaunch_premap_reprepares_after_eviction():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=None,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_address_manager_counters=True,
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_consumer_mapping_emit_rows=False,
        shadow_premap_address_manager_capacity=2,
        shadow_premap_descriptor_bytes=64,
        shadow_num_experts=8,
        request_id="req",
        sequence_id=5,
    )

    layer3_keys = recorder._premap_address_keys_for_experts(
        layer_id=3,
        expert_ids=[1, 2],
    )
    layer4_keys = recorder._premap_address_keys_for_experts(
        layer_id=4,
        expert_ids=[3, 4],
    )

    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        prelaunch_boundary_source="fused_moe_prepare_expert_assignment",
    )
    manager = recorder._shadow_premap_address_manager
    assert manager is not None
    assert manager.prepared_plan_count == 1
    assert all(manager.contains_address_key(key) for key in layer3_keys)

    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=4,
        active_experts=[3, 4],
        prelaunch_boundary_source="fused_moe_prepare_expert_assignment",
    )
    assert manager.prepared_plan_count == 2
    assert all(manager.contains_address_key(key) for key in layer4_keys)
    assert not any(manager.contains_address_key(key) for key in layer3_keys)

    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        prelaunch_boundary_source="fused_moe_prepare_expert_assignment",
    )
    assert manager.prepared_plan_count == 3
    assert all(manager.contains_address_key(key) for key in layer3_keys)
    assert recorder._last_premap_address_mapping_by_layer[3]["prepare_plan_count"] == 3
    assert recorder._last_premap_address_mapping_by_layer[3]["address_key_count"] == 2


def test_vllm_router_recorder_premap_summary_can_emit_address_manager_counters():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_premap_address_manager_capacity=4,
        shadow_num_experts=6,
        shadow_premap_descriptor_bytes=64,
        request_id="req",
        sequence_id=5,
    )

    for _ in range(2):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )

    rows = [event.as_dict() for event in sink.events]
    assert len(rows) == 2
    assert rows[0]["premap_address_manager_capacity"] == 4
    assert rows[0]["premap_address_new_count"] == 2
    assert rows[0]["premap_address_reused_count"] == 0
    assert rows[0]["premap_address_resident_count"] == 2
    assert rows[0]["premap_address_resident_descriptor_bytes"] == 128
    assert rows[0]["premap_payload_bytes"] == 0

    assert rows[1]["premap_address_new_count"] == 2
    assert rows[1]["premap_address_reused_count"] == 2
    assert rows[1]["premap_address_resident_count"] == 2
    assert rows[1]["premap_address_reuse_rate"] == 0.5
    assert rows[1]["premap_address_eviction_pressure"] == 0.0
    assert rows[1]["premap_payload_bytes"] == 0


def test_vllm_router_recorder_premap_consumer_mapping_hits_prepared_addresses():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_consumer_readonly_gate_required=True,
        shadow_premap_consumer_readonly_gate_id="readonly-gate",
        shadow_premap_consumer_readonly_gate_path="configs/runtime/readonly.yaml",
        shadow_premap_consumer_readonly_gate_passed=True,
        shadow_premap_descriptor_prep_execution_mode=(
            "readonly_descriptor_address_object"
        ),
        shadow_premap_address_manager_capacity=4,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2]]),
        topk_weights=torch.tensor([[0.8, 0.2]]),
    )
    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=3,
        sorted_token_ids=torch.arange(4, dtype=torch.int32),
        expert_ids=torch.tensor([1, 2], dtype=torch.int32),
        num_tokens_post_padded=torch.tensor([4], dtype=torch.int32),
        block_size=2,
    )

    rows = [event.as_dict() for event in sink.events]
    assert [row["event_type"] for row in rows] == [
        "premap_summary",
        "premap_consumer_mapping",
    ]
    consumer = rows[1]
    assert consumer["premap_consumer_mapping_source"] == (
        "fused_moe_prepare_expert_assignment"
    )
    assert consumer["premap_consumer_readonly_gate_required"] is True
    assert consumer["premap_consumer_readonly_gate_id"] == "readonly-gate"
    assert consumer["premap_consumer_readonly_gate_path"] == (
        "configs/runtime/readonly.yaml"
    )
    assert consumer["premap_consumer_readonly_gate_passed"] is True
    assert consumer["premap_consumer_expert_count"] == 2
    assert consumer["premap_consumer_unique_expert_count"] == 2
    assert consumer["premap_consumer_address_hit_count"] == 2
    assert consumer["premap_consumer_address_miss_count"] == 0
    assert consumer["premap_consumer_descriptor_handle_hit_count"] == 2
    assert consumer["premap_consumer_descriptor_handle_miss_count"] == 0
    assert consumer["premap_consumer_descriptor_handle_hash"]
    assert consumer["premap_consumer_expected_descriptor_handle_hash"] == (
        consumer["premap_consumer_descriptor_handle_hash"]
    )
    assert consumer["premap_consumer_descriptor_handle_parity_ok"] is True
    assert consumer["premap_consumer_readonly_lookup_count"] == 2
    assert consumer["premap_consumer_readonly_handle_hit_count"] == 2
    assert consumer["premap_consumer_readonly_handle_miss_count"] == 0
    assert consumer["premap_consumer_readonly_evicted_before_consume_count"] == 0
    assert consumer["premap_consumer_readonly_stale_handle_count"] == 0
    assert consumer["premap_consumer_readonly_handle_parity_ok"] is True
    assert consumer["premap_consumer_descriptor_prep_execution_mode"] == (
        "readonly_descriptor_address_object"
    )
    assert consumer["premap_consumer_descriptor_prep_lookup_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_handle_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_missing_handle_count"] == 0
    assert consumer["premap_consumer_descriptor_prep_descriptor_ptr_count"] == 2
    assert (
        consumer["premap_consumer_descriptor_prep_packed_weight_descriptor_count"]
        == 2
    )
    assert consumer["premap_consumer_descriptor_prep_scale_metadata_handle_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_real_handle_count"] == 0
    assert consumer["premap_consumer_descriptor_prep_real_handle_miss_count"] == 0
    assert consumer["premap_consumer_descriptor_prep_real_handle_backed"] is False
    assert consumer["premap_consumer_descriptor_prep_consumer_object_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_consumer_object_hash"]
    assert (
        consumer["premap_consumer_descriptor_prep_consumer_object_read_lookup_count"]
        == 2
    )
    assert consumer["premap_consumer_descriptor_prep_consumer_object_read_hit_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_consumer_object_read_miss_count"] == 0
    assert consumer["premap_consumer_descriptor_prep_consumer_object_stale_count"] == 0
    assert consumer["premap_consumer_descriptor_prep_consumer_object_read_hash"] == (
        consumer["premap_consumer_descriptor_prep_consumer_object_hash"]
    )
    assert consumer["premap_consumer_descriptor_prep_consumer_object_read_ok"] is True
    assert consumer["premap_consumer_descriptor_prep_consumer_shim_mode"] == (
        "readonly_prelaunch_consumer_shim"
    )
    assert consumer["premap_consumer_descriptor_prep_consumer_shim_object_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_consumer_shim_object_hash"] == (
        consumer["premap_consumer_descriptor_prep_consumer_object_hash"]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count"
        ]
        == 4
    )
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_schema_hash"
    ]
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes"
        ]
        == 0
    )
    assert consumer["premap_consumer_descriptor_prep_consumer_shim_ok"] is True
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_changes_kernel_launch_args"
        ]
        is False
    )
    _assert_consumer_shim_table_consume_event(consumer)
    _assert_consumer_shim_prep_execution_dry_run_event(consumer)
    _assert_kernel_arg_shadow_table_event(consumer)
    assert consumer["premap_consumer_descriptor_prep_handle_hash"]
    assert consumer["premap_consumer_descriptor_prep_execution_ok"] is True
    assert consumer["premap_consumer_expected_prepare_plan_count"] == 1
    assert consumer["premap_consumer_observed_prepare_plan_count"] == 1
    assert consumer["premap_consumer_expected_prepare_record_count"] == 2
    assert consumer["premap_consumer_observed_prepare_record_count"] == 2
    assert consumer["premap_consumer_lookup_after_prepare"] is True
    assert consumer["premap_consumer_all_hit"] is True
    assert consumer["premap_consumer_parity_ok"] is True
    assert consumer["premap_consumer_payload_bytes"] == 0
    assert consumer["premap_consumer_changes_router"] is False
    assert consumer["premap_consumer_changes_descriptor_order"] is False
    assert consumer["premap_consumer_ready_credit"] is False


def test_vllm_router_recorder_premap_descriptor_prep_uses_real_handles():
    sink = _Sink()
    consumer_layer = _FakeAwqConsumerLayer(num_experts=6)
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_address_manager_capacity=4,
        shadow_premap_consumer_resolve_real_handles=True,
        shadow_premap_consumer_readonly_gate_required=True,
        shadow_premap_consumer_readonly_gate_id="readonly-gate",
        shadow_premap_consumer_readonly_gate_path="configs/runtime/readonly.yaml",
        shadow_premap_consumer_readonly_gate_passed=True,
        shadow_premap_descriptor_prep_execution_mode=(
            "readonly_descriptor_address_object"
        ),
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2]]),
        topk_weights=torch.tensor([[0.8, 0.2]]),
    )
    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        consumer_layer=consumer_layer,
    )

    consumer = [
        event.as_dict()
        for event in sink.events
        if event.as_dict()["event_type"] == "premap_consumer_mapping"
    ][0]
    assert consumer["premap_consumer_address_hit_count"] == 2
    assert consumer["premap_consumer_address_miss_count"] == 0
    assert consumer["premap_consumer_readonly_handle_parity_ok"] is True
    assert consumer["premap_consumer_real_descriptor_handle_hit_count"] == 2
    assert consumer["premap_consumer_real_descriptor_handle_miss_count"] == 0
    assert consumer["premap_consumer_real_descriptor_handle_available"] is True
    assert consumer["premap_consumer_real_descriptor_handle_source_hit_counts"] == {
        "packed_weight": 2,
        "scale_metadata": 2,
        "aux_metadata": 0,
    }
    assert consumer["premap_consumer_descriptor_prep_execution_mode"] == (
        "readonly_descriptor_address_object"
    )
    assert consumer["premap_consumer_descriptor_prep_handle_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_missing_handle_count"] == 0
    assert consumer["premap_consumer_descriptor_prep_real_handle_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_real_handle_miss_count"] == 0
    assert consumer["premap_consumer_descriptor_prep_real_handle_backed"] is True
    assert consumer["premap_consumer_descriptor_prep_real_handle_hash"]
    assert consumer["premap_consumer_descriptor_prep_consumer_object_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_consumer_object_hash"]
    assert (
        consumer["premap_consumer_descriptor_prep_consumer_object_read_lookup_count"]
        == 2
    )
    assert consumer["premap_consumer_descriptor_prep_consumer_object_read_hit_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_consumer_object_read_miss_count"] == 0
    assert consumer["premap_consumer_descriptor_prep_consumer_object_stale_count"] == 0
    assert consumer["premap_consumer_descriptor_prep_consumer_object_read_hash"] == (
        consumer["premap_consumer_descriptor_prep_consumer_object_hash"]
    )
    assert consumer["premap_consumer_descriptor_prep_consumer_object_read_ok"] is True
    assert consumer["premap_consumer_descriptor_prep_consumer_shim_mode"] == (
        "readonly_prelaunch_consumer_shim"
    )
    assert consumer["premap_consumer_descriptor_prep_consumer_shim_object_count"] == 2
    assert consumer["premap_consumer_descriptor_prep_consumer_shim_object_hash"] == (
        consumer["premap_consumer_descriptor_prep_consumer_object_hash"]
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
        ]
        == 2
    )
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count"
        ]
        == 4
    )
    assert consumer[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_schema_hash"
    ]
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes"
        ]
        == 0
    )
    assert consumer["premap_consumer_descriptor_prep_consumer_shim_ok"] is True
    assert (
        consumer[
            "premap_consumer_descriptor_prep_consumer_shim_changes_kernel_launch_args"
        ]
        is False
    )
    _assert_consumer_shim_table_consume_event(consumer)
    _assert_consumer_shim_prep_execution_dry_run_event(consumer)
    _assert_kernel_arg_shadow_table_event(consumer)
    assert consumer["premap_consumer_descriptor_prep_execution_ok"] is True
    assert consumer["premap_consumer_payload_bytes"] == 0
    assert consumer["premap_consumer_ready_credit"] is False
    assert consumer["premap_consumer_changes_router"] is False
    assert consumer["premap_consumer_changes_descriptor_order"] is False


def test_vllm_router_recorder_premap_descriptor_prep_requires_passed_gate():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_consumer_readonly_gate_required=True,
        shadow_premap_consumer_readonly_gate_id="readonly-gate",
        shadow_premap_consumer_readonly_gate_path="configs/runtime/readonly.yaml",
        shadow_premap_consumer_readonly_gate_passed=False,
        shadow_premap_descriptor_prep_execution_mode=(
            "readonly_descriptor_address_object"
        ),
        shadow_premap_address_manager_capacity=4,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2]]),
        topk_weights=torch.tensor([[0.8, 0.2]]),
    )
    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=3,
        sorted_token_ids=torch.arange(4, dtype=torch.int32),
        expert_ids=torch.tensor([1, 2], dtype=torch.int32),
        num_tokens_post_padded=torch.tensor([4], dtype=torch.int32),
        block_size=2,
    )

    consumer = [event.as_dict() for event in sink.events][-1]
    assert consumer["event_type"] == "premap_consumer_mapping"
    assert consumer["premap_consumer_descriptor_prep_execution_mode"] == (
        "readonly_descriptor_address_object"
    )
    assert (
        consumer["premap_consumer_descriptor_prep_blocked_reason"]
        == "readonly_gate_not_passed"
    )
    assert "premap_consumer_descriptor_prep_execution_ok" not in consumer
    assert "premap_consumer_descriptor_prep_handle_count" not in consumer
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
        not in consumer
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
        not in consumer
    )
    assert consumer["premap_consumer_payload_bytes"] == 0
    assert consumer["premap_consumer_ready_credit"] is False


def test_vllm_router_recorder_premap_consumer_real_handle_lifecycle_and_eviction():
    sink = _Sink()
    consumer_layer = _FakeAwqConsumerLayer(num_experts=6)
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_address_manager_capacity=1,
        shadow_premap_consumer_resolve_real_handles=True,
        shadow_premap_consumer_readonly_gate_required=True,
        shadow_premap_consumer_readonly_gate_id="readonly-gate",
        shadow_premap_consumer_readonly_gate_path="configs/runtime/readonly.yaml",
        shadow_premap_consumer_readonly_gate_passed=True,
        shadow_premap_descriptor_prep_execution_mode=(
            "readonly_descriptor_address_object"
        ),
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2]]),
        topk_weights=torch.tensor([[0.8, 0.2]]),
    )
    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        consumer_layer=consumer_layer,
    )
    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        consumer_layer=consumer_layer,
    )

    rows = [event.as_dict() for event in sink.events]
    consumer_rows = [
        row for row in rows if row["event_type"] == "premap_consumer_mapping"
    ]
    assert len(consumer_rows) == 2

    first = consumer_rows[0]
    assert first["premap_consumer_address_hit_count"] == 1
    assert first["premap_consumer_address_miss_count"] == 1
    assert first["premap_consumer_descriptor_handle_hit_count"] == 1
    assert first["premap_consumer_descriptor_handle_miss_count"] == 1
    assert first["premap_consumer_readonly_lookup_count"] == 2
    assert first["premap_consumer_readonly_handle_hit_count"] == 1
    assert first["premap_consumer_readonly_handle_miss_count"] == 1
    assert first["premap_consumer_readonly_evicted_before_consume_count"] == 1
    assert first["premap_consumer_readonly_stale_handle_count"] == 0
    assert first["premap_consumer_readonly_handle_parity_ok"] is False
    assert first["premap_consumer_descriptor_prep_execution_mode"] == (
        "readonly_descriptor_address_object"
    )
    assert (
        first["premap_consumer_descriptor_prep_blocked_reason"]
        == "readonly_consumer_failed"
    )
    assert "premap_consumer_descriptor_prep_execution_ok" not in first
    assert first["premap_consumer_real_descriptor_handle_hit_count"] == 2
    assert first["premap_consumer_real_descriptor_handle_miss_count"] == 0
    assert first["premap_consumer_real_descriptor_handle_available"] is True
    assert first["premap_consumer_real_descriptor_handle_source_hashes"][
        "packed_weight"
    ]
    assert first["premap_consumer_real_descriptor_handle_source_hashes"][
        "scale_metadata"
    ]
    assert first["premap_consumer_real_descriptor_handle_source_hit_counts"] == {
        "packed_weight": 2,
        "scale_metadata": 2,
        "aux_metadata": 0,
    }
    assert first["premap_consumer_real_descriptor_handle_source_miss_counts"] == {
        "packed_weight": 0,
        "scale_metadata": 0,
        "aux_metadata": 2,
    }
    assert first["premap_consumer_real_descriptor_handle_new_binding_count"] == 2
    assert first["premap_consumer_real_descriptor_handle_reused_binding_count"] == 0
    assert first["premap_consumer_real_descriptor_handle_binding_mismatch_count"] == 0
    assert first["premap_consumer_real_descriptor_handle_for_address_miss_count"] == 1
    assert first["premap_consumer_all_hit"] is False
    assert first["premap_consumer_parity_ok"] is False
    assert first["premap_consumer_payload_bytes"] == 0
    assert first["premap_consumer_changes_router"] is False
    assert first["premap_consumer_changes_descriptor_order"] is False
    assert first["premap_consumer_ready_credit"] is False

    second = consumer_rows[1]
    assert second["premap_consumer_real_descriptor_handle_new_binding_count"] == 0
    assert second["premap_consumer_real_descriptor_handle_reused_binding_count"] == 2
    assert second["premap_consumer_real_descriptor_handle_binding_mismatch_count"] == 0
    assert second["premap_consumer_real_descriptor_handle_for_address_miss_count"] == 1
    assert second["premap_consumer_readonly_handle_hit_count"] == 1
    assert second["premap_consumer_readonly_handle_miss_count"] == 1
    assert second["premap_consumer_readonly_evicted_before_consume_count"] == 1
    assert second["premap_consumer_readonly_handle_parity_ok"] is False
    assert (
        second["premap_consumer_descriptor_prep_blocked_reason"]
        == "readonly_consumer_failed"
    )


def test_vllm_router_recorder_premap_real_handle_binding_survives_clear():
    sink = _Sink()
    consumer_layer = _FakeAwqConsumerLayer(num_experts=6)
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_consumer_resolve_real_handles=True,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        consumer_layer=consumer_layer,
    )
    recorder.clear()
    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        consumer_layer=consumer_layer,
    )

    rows = [event.as_dict() for event in sink.events]
    assert len(rows) == 2
    assert rows[0]["premap_consumer_real_descriptor_handle_new_binding_count"] == 2
    assert rows[0]["premap_consumer_real_descriptor_handle_reused_binding_count"] == 0
    assert rows[1]["premap_consumer_real_descriptor_handle_new_binding_count"] == 0
    assert rows[1]["premap_consumer_real_descriptor_handle_reused_binding_count"] == 2
    assert rows[1]["premap_consumer_real_descriptor_handle_binding_mismatch_count"] == 0


def test_vllm_router_recorder_premap_consumer_mapping_can_be_sampled():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_consumer_mapping_sample_period=3,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    for _ in range(7):
        recorder._write_premap_consumer_mapping_from_experts(
            layer_id=3,
            active_experts=[1, 2],
            consumer_layer=None,
        )

    rows = [event.as_dict() for event in sink.events]
    assert len(rows) == 3
    assert all(row["event_type"] == "premap_consumer_mapping" for row in rows)


def test_vllm_router_recorder_premap_summary_requires_supported_sink():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=_OutcomeOnlySink(),
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        request_id="req",
        sequence_id=5,
    )

    with pytest.raises(TypeError, match="write_premap_summary_from_descriptors"):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )


def test_vllm_router_recorder_transition_premap_summary_works_with_outcomes_off():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_transition_premap_summary=True,
        shadow_num_experts=6,
        shadow_transition_summary_mode="previous_topk",
        shadow_premap_descriptor_bytes=16,
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [2, 3], [4, 5]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3], [0.6, 0.4]]),
    )

    assert len(sink.events) == 2
    rows = [event.as_dict() for event in sink.events]
    assert [row["event_type"] for row in rows] == ["premap_summary", "premap_summary"]
    assert [row["token_index"] for row in rows] == [11, 12]
    assert [row["premap_descriptor_count"] for row in rows] == [2, 2]
    assert [row["premap_actual_bytes"] for row in rows] == [32, 32]
    assert {row["premap_source"] for row in rows} == {
        "previous_token_transition_premap_shadow"
    }
    assert all(row["premap_payload_bytes"] == 0 for row in rows)
    assert all(row["premap_full_fetch_count"] == 0 for row in rows)
    assert all(row["premap_metadata_count"] == 0 for row in rows)
    assert all(row["premap_changes_router"] is False for row in rows)
    assert all(row["premap_changes_descriptor_order"] is False for row in rows)
    assert all(row["premap_ready_credit"] is False for row in rows)


def test_vllm_router_recorder_transition_premap_summary_requires_supported_sink():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=_OutcomeOnlySink(),
        shadow_outcome_logging_mode="off",
        shadow_emit_transition_premap_summary=True,
        request_id="req",
        sequence_id=5,
    )

    with pytest.raises(TypeError, match="write_premap_summary_from_descriptors"):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2], [2, 3]]),
            topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3]]),
        )


def test_vllm_router_recorder_matrix_topk_transition_premap_summary():
    sink = _Sink()
    transition = torch.zeros((1, 4, 6, 6), dtype=torch.float32)
    # Previous expert 1 predicts experts 4, 2, then 3 for layer 3.
    transition[0, 3, 1, 4] = 0.9
    transition[0, 3, 1, 2] = 0.8
    transition[0, 3, 1, 3] = 0.7
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_transition_premap_summary=True,
        shadow_num_experts=6,
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=2,
        shadow_transition_matrix=transition,
        shadow_premap_policy="transition_matrix_top2_premap_only",
        shadow_transition_premap_source="matrix_topk_transition_premap_shadow",
        shadow_premap_descriptor_bytes=32,
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 0], [2, 3]]),
        topk_weights=torch.tensor([[1.0, 0.0], [0.7, 0.3]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "premap_summary"
    assert row["token_index"] == 11
    assert row["premap_policy"] == "transition_matrix_top2_premap_only"
    assert row["premap_source"] == "matrix_topk_transition_premap_shadow"
    assert row["premap_descriptor_count"] == 2
    assert row["premap_unique_experts"] == 2
    assert row["premap_actual_bytes"] == 64
    assert row["premap_payload_bytes"] == 0
    assert row["premap_ready_credit"] is False


def test_vllm_router_recorder_matrix_topk_transition_premap_ignores_oob_previous():
    sink = _Sink()
    transition = torch.zeros((1, 4, 6, 6), dtype=torch.float32)
    transition[0, 3, 1, 4] = 0.9
    transition[0, 3, 1, 2] = 0.8
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_transition_premap_summary=True,
        shadow_num_experts=6,
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=2,
        shadow_transition_matrix=transition,
        shadow_premap_policy="transition_matrix_top2_premap_only",
        shadow_transition_premap_source="matrix_topk_transition_premap_shadow",
        request_id="req",
        sequence_id=5,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[99, 1], [2, 3]]),
        topk_weights=torch.tensor([[0.5, 0.5], [0.7, 0.3]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "premap_summary"
    assert row["premap_descriptor_count"] == 2
    assert "premap_error" not in row
    assert row["premap_payload_bytes"] == 0


def test_vllm_router_recorder_can_disable_descriptor_layer_timing():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_descriptor_layer_timing=False,
        request_id="req",
        sequence_id=5,
    )

    recorder.write_descriptor_layer_timing(
        layer_id=3,
        apply_us=10.0,
        num_tokens=1,
        phase="decode",
    )

    assert sink.events == []


def test_vllm_router_recorder_outcome_logging_mode_aliases_and_invalid():
    recorder = VllmRouterRecorder(top_k=2)

    recorder.shadow_outcome_logging_mode = " none "
    assert recorder._resolved_outcome_logging_mode() == "off"
    recorder.shadow_outcome_logging_mode = "FALSE"
    assert recorder._resolved_outcome_logging_mode() == "off"
    recorder.shadow_outcome_logging_mode = "1"
    assert recorder._resolved_outcome_logging_mode() == "full"

    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="bad-mode",
    )
    with pytest.raises(ValueError, match="Unsupported shadow_outcome_logging_mode"):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )


def test_transition_summary_forces_full_outcomes_when_outcome_mode_off(tmp_path):
    path = tmp_path / "transition_shadow_force_full.jsonl"
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_transition_summary=True,
            shadow_outcome_logging_mode="off",
            shadow_num_experts=6,
            request_id="req",
            sequence_id=0,
            token_offset=0,
        )
        recorder.record_topk(
            layer_id=1,
            topk_ids=torch.tensor([[1, 2], [2, 3]]),
            topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["outcome", "summary", "outcome"]
    assert rows[2]["join_status"] == "joined"


def test_active_runtime_shadow_hook_joins_with_vllm_router_outcome(tmp_path):
    shape = (1, 1, 1, 5)
    full_fetch = torch.zeros(shape, dtype=torch.bool)
    full_fetch[..., 1] = True
    metadata = torch.zeros(shape, dtype=torch.bool)
    metadata[..., 2] = True
    premap = torch.zeros(shape, dtype=torch.bool)
    premap[..., 3] = True
    skipped = torch.zeros(shape, dtype=torch.bool)
    skipped[..., 4] = True
    empty = torch.zeros(shape, dtype=torch.bool)
    ready = torch.zeros(shape, dtype=torch.bool)
    ready[..., 1] = True
    decisions = AdmissionDecisionMasks(
        admitted_full_fetch=full_fetch,
        admitted_metadata=metadata,
        admitted_premap=premap,
        skipped_not_novel=empty,
        skipped_rank_cap=empty,
        skipped_below_threshold=skipped,
        skipped_invalid_score=empty,
        skipped_policy=empty,
    )
    event_id = ShadowEventId("req", 5, 10, 3)
    policy = ShadowPolicyConfig(
        policy_mode="default",
        optimization_goal="stall_reduction",
        action_keep_fraction=0.5,
        metadata_score_ratio=0.95,
        full_fetch_max_extra=4,
        metadata_max_extra=1,
        premap_max_extra=1,
    )
    path = tmp_path / "runtime_shadow.jsonl"

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        set_active_runtime_shadow_controller(controller)
        try:
            summary = write_active_runtime_shadow_action_summary(
                event_id=event_id,
                policy=policy,
                decisions=decisions,
                ready_mask=ready,
            )
        finally:
            set_active_runtime_shadow_controller(None)
        assert summary is not None
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            request_id="req",
            sequence_id=5,
            token_offset=10,
        )
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["summary", "outcome"]
    outcome = rows[1]
    assert outcome["join_status"] == "joined"
    assert outcome["full_fetch_used_count"] == 1
    assert outcome["metadata_later_used_count"] == 1
    assert outcome["covered_mass"] == pytest.approx(0.8)
    assert outcome["top1_ready"] is True


def test_vllm_router_recorder_descriptor_min_summary_records_gate_decision():
    sink = _Sink()
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=3),
            TileRequest(0, 1, 1, 1, layer_idx=3),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    gate = DescriptorOrderRuntimeGate(
        policy="layer_prior_frequency",
        execution_mode="two_level_group_plan",
        tile_elems=(1024,),
        groups_per_cta=(8,),
        devices=(0,),
        diagnostic_groups_per_cta=(16,),
        disable_groups_per_cta_min=64,
        prior_id="prior-test",
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_descriptor_order_summary=True,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prior_id="prior-test",
        shadow_descriptor_order_prior_hash="hash-test",
        shadow_descriptor_order_metrics_mode="count_only",
        shadow_descriptor_order_event_mode="minimal",
        shadow_descriptor_order_runtime_gate=gate,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_device=0,
        request_id="req",
        sequence_id=0,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [2, 3]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "descriptor_summary_min"
    assert row["descriptor_order_execution_mode"] == "two_level_group_plan"
    assert row["descriptor_group_plan_groups_per_cta"] == 8
    assert row["descriptor_order_gate_allow"] is False
    assert row["descriptor_order_gate_reason"] == "same_multiset_missing"
    assert row["descriptor_order_gate_tile_elems"] == 1024
    assert row["descriptor_order_gate_device"] == 0


def test_vllm_router_recorder_descriptor_min_summary_uses_consumer_evidence():
    sink = _Sink()
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=3),
            TileRequest(0, 1, 1, 1, layer_idx=3),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    gate = DescriptorOrderRuntimeGate(
        policy="layer_prior_frequency",
        execution_mode="two_level_group_plan",
        tile_elems=(1024,),
        groups_per_cta=(8,),
        devices=(0,),
        diagnostic_groups_per_cta=(16,),
        disable_groups_per_cta_min=64,
        prior_id="prior-test",
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_descriptor_order_summary=True,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prior_id="prior-test",
        shadow_descriptor_order_prior_hash="hash-test",
        shadow_descriptor_order_metrics_mode="count_only",
        shadow_descriptor_order_event_mode="minimal",
        shadow_descriptor_order_runtime_gate=gate,
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
        shadow_descriptor_order_evidence_cache_flush_elems=0,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_device=0,
        request_id="req",
        sequence_id=0,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [2, 3]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3]]),
    )

    row = sink.events[0].as_dict()
    assert row["descriptor_order_gate_allow"] is True
    assert row["descriptor_order_gate_reason"] == "allowed"
    assert row["descriptor_order_gate_evidence_found"] is True
    assert row["descriptor_order_gate_checksum_delta"] == 0.0
    assert row["descriptor_order_gate_speedup_median_vs_no_order"] == pytest.approx(1.2)


def test_vllm_router_recorder_emits_previous_token_transition_summaries(tmp_path):
    path = tmp_path / "transition_shadow.jsonl"
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_transition_summary=True,
            shadow_num_experts=6,
            request_id="req",
            sequence_id=0,
            token_offset=0,
        )
        recorder.record_topk(
            layer_id=1,
            topk_ids=torch.tensor([[1, 2], [2, 3], [4, 5]]),
            topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3], [0.6, 0.4]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == [
        "outcome",
        "summary",
        "outcome",
        "summary",
        "outcome",
    ]
    assert rows[0]["shadow_event_id"] == "req:0:0:1"
    assert rows[0]["join_status"] == "outcome_only"
    assert rows[1]["shadow_event_id"] == "req:0:1:1"
    assert rows[1]["policy_mode"] == "transition_only_shadow"
    assert rows[1]["transition_topk_count"] == 2
    assert rows[2]["shadow_event_id"] == "req:0:1:1"
    assert rows[2]["join_status"] == "joined"
    assert rows[2]["covered_mass"] == pytest.approx(0.7)
    assert rows[2]["top1_ready"] is True
    assert rows[4]["join_status"] == "joined"


def test_vllm_router_recorder_emits_matrix_topk_transition_summaries(tmp_path):
    path = tmp_path / "matrix_transition_shadow.jsonl"
    transition = torch.zeros(1, 1, 6, 6)
    transition[0, 0, 1, 4] = 10.0
    transition[0, 0, 2, 5] = 9.0
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_transition_summary=True,
            shadow_num_experts=6,
            shadow_transition_topk_count=2,
            shadow_transition_summary_mode="matrix_topk",
            shadow_transition_matrix=transition,
            request_id="req",
            sequence_id=0,
            token_offset=0,
        )
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2], [4, 5]]),
            topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["outcome", "summary", "outcome"]
    assert rows[1]["policy_reason"] == "matrix_topk_transition_summary"
    assert rows[2]["join_status"] == "joined"
    assert rows[2]["covered_mass"] == pytest.approx(1.0)
    assert rows[2]["top1_ready"] is True


def test_vllm_router_recorder_emits_descriptor_order_summary(tmp_path):
    path = tmp_path / "descriptor_order_shadow.jsonl"
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 2, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-v1"},
    )
    prior_hash = hash_layer_tile_prior(prior)

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_descriptor_order_summary=True,
            shadow_descriptor_order_prior=prior,
            shadow_descriptor_order_prior_id="prior-v1",
            shadow_descriptor_order_prior_hash=prior_hash,
            shadow_descriptor_order_tiles_per_expert=1,
            shadow_descriptor_order_token_window_size=1,
            request_id="req",
            sequence_id=0,
            token_offset=10,
        )
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2], [1, 3]]),
            topk_weights=torch.tensor([[0.7, 0.3], [0.6, 0.4]]),
        )
        aggregate = controller.aggregate()

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["outcome", "outcome", "summary"]
    summary = rows[-1]
    assert summary["shadow_event_id"] == "req:0:-1:0"
    assert summary["policy_mode"] == "descriptor_order_shadow"
    assert summary["descriptor_order_policy"] == "layer_prior_frequency"
    assert summary["descriptor_order_prior_id"] == "prior-v1"
    assert summary["descriptor_order_prior_hash"] == prior_hash
    assert summary["descriptor_tile_request_count"] == 4
    assert summary["descriptor_order_metrics"]["window_count"] == 2
    assert summary["descriptor_same_multiset"] is True
    assert summary["descriptor_order_changed"] is True
    assert summary["candidate_construction_us"] >= 0.0
    assert summary["descriptor_order_build_us"] >= 0.0
    assert summary["decision_us"] >= summary["candidate_construction_us"]
    assert aggregate["descriptor_order_summary_count"] == 1
    assert aggregate["controller_stats"]["written_summary_count"] == 1


def test_vllm_router_recorder_emits_descriptor_order_min_summary(tmp_path):
    path = tmp_path / "descriptor_order_min_shadow.jsonl"
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-v1"},
    )
    prior_hash = hash_layer_tile_prior(prior)

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_descriptor_order_summary=True,
            shadow_descriptor_order_prior=prior,
            shadow_descriptor_order_prior_id="prior-v1",
            shadow_descriptor_order_prior_hash=prior_hash,
            shadow_descriptor_order_metrics_mode="count_only",
            shadow_descriptor_order_event_mode="minimal",
            shadow_descriptor_order_execution_mode="two_level_group_plan",
            shadow_descriptor_order_groups_per_cta=4,
            shadow_descriptor_order_token_window_size=1,
            request_id="req",
            sequence_id=0,
            token_offset=10,
        )
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2], [1, 3]]),
            topk_weights=torch.tensor([[0.7, 0.3], [0.6, 0.4]]),
        )
        aggregate = controller.aggregate()

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == [
        "outcome",
        "outcome",
        "descriptor_summary_min",
    ]
    summary = rows[-1]
    assert summary["shadow_event_id"] == "req:0:-1:0"
    assert summary["descriptor_order_policy"] == "layer_prior_frequency"
    assert summary["descriptor_order_metrics_mode"] == "count_only"
    assert summary["descriptor_order_prior_hash"] == prior_hash
    assert summary["descriptor_tile_request_count"] == 4
    assert summary["descriptor_unique_b_tiles"] == 3
    assert summary["descriptor_window_count"] == 2
    assert summary["descriptor_order_execution_mode"] == "two_level_group_plan"
    assert summary["descriptor_group_plan_groups_per_cta"] == 4
    assert summary["descriptor_group_plan_group_count"] == 4
    assert summary["descriptor_group_plan_avg_group_size"] == 1.0
    assert summary["descriptor_group_plan_p95_group_size"] == 1.0
    assert summary["descriptor_group_plan_max_group_size"] == 1
    assert summary["descriptor_group_plan_cta_count"] == 1
    assert "descriptor_order_metrics" not in summary
    assert "full_fetch_count" not in summary
    assert aggregate["descriptor_summary_min_count"] == 1
    assert aggregate["descriptor_order_summary_count"] == 1


def test_vllm_descriptor_order_summary_is_noop_without_prior(tmp_path):
    path = tmp_path / "descriptor_order_missing_prior.jsonl"
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_descriptor_order_summary=True,
            request_id="req",
            sequence_id=0,
            token_offset=10,
        )
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.7, 0.3]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["outcome"]


def test_vllm_matrix_topk_transition_is_weighted_and_stable(tmp_path):
    path = tmp_path / "matrix_transition_weighted_shadow.jsonl"
    transition = torch.zeros(1, 1, 6, 6)
    transition[0, 0, 1, 4] = 1.0
    transition[0, 0, 2, 5] = 10.0
    transition[0, 0, 1, 0] = 0.5
    transition[0, 0, 2, 0] = 0.5
    transition[0, 0, 1, 3] = 0.5
    transition[0, 0, 2, 3] = 0.5
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=3,
            shadow_outcome_sink=controller,
            shadow_emit_transition_summary=True,
            shadow_num_experts=6,
            shadow_transition_topk_count=3,
            shadow_transition_summary_mode="matrix_topk",
            shadow_transition_matrix=transition,
            request_id="req",
            sequence_id=0,
            token_offset=0,
        )
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2, 0], [4, 0, 3]]),
            topk_weights=torch.tensor([[8.0, 2.0, 0.0], [0.6, 0.3, 0.1]]),
        )

    rows = read_shadow_jsonl(path)
    assert rows[1]["full_fetch_count"] == 0
    assert rows[2]["join_status"] == "joined"
    # Weight renormalization makes expert 4 outrank expert 5. Experts 0 and 3
    # tie, so expert-id ascending tie-break includes expert 0 for top3.
    assert rows[2]["covered_mass"] == pytest.approx(0.9)
    assert rows[2]["top1_ready"] is True


def test_premap_consumer_mapping_emit_rows_false_does_not_require_row_sink():
    class SinkWithoutPremapRows:
        pass

    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=SinkWithoutPremapRows(),
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_consumer_mapping_emit_rows=False,
        shadow_premap_consumer_mapping_mode="noop_assertion",
        shadow_num_experts=8,
    )

    sorted_token_ids = torch.arange(8, dtype=torch.int32)
    expert_ids = torch.tensor([1, 2], dtype=torch.int32)
    num_tokens_post_padded = torch.tensor([8], dtype=torch.int32)

    out = recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=sorted_token_ids,
        expert_ids=expert_ids,
        num_tokens_post_padded=num_tokens_post_padded,
        block_size=4,
    )

    assert out[0] is sorted_token_ids
    assert out[1] is expert_ids
    assert out[2] is num_tokens_post_padded


def test_gpu_assignment_prelaunch_pointer_source_canary_is_opt_in():
    _set_premap_kernel_arg_live_mutation_counter_mode("detailed")
    _reset_premap_kernel_arg_live_mutation_counters()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled=True,
        shadow_premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled=True,
    )
    package = {"producer_future_wna16_typed_slot_envelope": True}
    expert_ids = torch.tensor([1, 2], dtype=torch.int32)

    recorder._attach_premap_producer_gpu_assignment_envelope(
        package,
        source="unit",
        available=True,
        sorted_token_ids=None,
        expert_ids=expert_ids,
        num_tokens_post_padded=torch.tensor([2], dtype=torch.int32),
    )

    assert package["producer_gpu_assignment_envelope"] is True
    assert "producer_gpu_assignment_current_expert_ptr_source_kind" not in package
    counters = _premap_kernel_arg_live_mutation_counters()
    assert counters["package_producer_gpu_assignment_envelope_count"] == 1
    assert counters["gpu_assignment_prelaunch_current_expert_ptr_seen_count"] == 0


def test_gpu_assignment_prelaunch_pointer_source_canary_marks_cpu_as_host_not_ready():
    _set_premap_kernel_arg_live_mutation_counter_mode("detailed")
    _reset_premap_kernel_arg_live_mutation_counters()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled=True,
        shadow_premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled=True,
        shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled=True,
    )
    package = {"producer_future_wna16_typed_slot_envelope": True}
    expert_ids = torch.tensor([1, 2], dtype=torch.int32)

    recorder._attach_premap_producer_gpu_assignment_envelope(
        package,
        source="unit",
        available=True,
        sorted_token_ids=None,
        expert_ids=expert_ids,
        num_tokens_post_padded=torch.tensor([2], dtype=torch.int32),
    )

    assert (
        package["producer_gpu_assignment_current_expert_ptr_source_kind"]
        == "vllm_prelaunch_host_tensor"
    )
    assert (
        package[
            "producer_gpu_assignment_current_expert_ptr_ready_for_vllm_prelaunch_canary"
        ]
        is False
    )
    ptr_meta = package["producer_gpu_assignment_current_expert_ptr_meta"]
    assert ptr_meta["device"] == "cpu"
    assert ptr_meta["dtype"] == "torch.int32"
    assert ptr_meta["shape"] == (2,)
    assert ptr_meta["data_ptr"] == int(expert_ids.data_ptr())
    counters = _premap_kernel_arg_live_mutation_counters()
    assert counters["gpu_assignment_prelaunch_current_expert_ptr_seen_count"] == 1
    assert (
        counters["gpu_assignment_prelaunch_current_expert_ptr_unavailable_count"]
        == 1
    )
    assert counters["gpu_assignment_prelaunch_current_expert_ptr_non_device_count"] == 1
    assert counters["gpu_assignment_prelaunch_current_expert_ptr_available_count"] == 0
    assert counters["gpu_assignment_prelaunch_current_expert_ptr_vllm_device_count"] == 0


def test_gpu_assignment_prelaunch_pointer_source_observer_does_not_require_live_package():
    _set_premap_kernel_arg_live_mutation_counter_mode("detailed")
    _reset_premap_kernel_arg_live_mutation_counters()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled=True,
    )
    sorted_token_ids = torch.arange(8, dtype=torch.int32)
    expert_ids = torch.tensor([1, 2], dtype=torch.int32)
    num_tokens_post_padded = torch.tensor([8], dtype=torch.int32)

    out = recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=sorted_token_ids,
        expert_ids=expert_ids,
        num_tokens_post_padded=num_tokens_post_padded,
        block_size=4,
    )

    assert out[0] is sorted_token_ids
    assert out[1] is expert_ids
    assert out[2] is num_tokens_post_padded
    counters = _premap_kernel_arg_live_mutation_counters()
    assert counters["package_producer_gpu_assignment_envelope_count"] == 0
    assert (
        counters[
            "gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count"
        ]
        == 1
    )
    assert (
        counters[
            "gpu_assignment_prelaunch_current_expert_ptr_observer_unavailable_count"
        ]
        == 1
    )
    assert (
        counters[
            "gpu_assignment_prelaunch_current_expert_ptr_observer_non_device_count"
        ]
        == 1
    )
    assert (
        counters[
            "gpu_assignment_prelaunch_current_expert_ptr_observer_available_count"
        ]
        == 0
    )
    assert (
        counters[
            "gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count"
        ]
        == 0
    )


def test_readonly_future_typed_slot_producer_installs_live_package_without_mutation():
    _set_premap_kernel_arg_live_mutation_counter_mode("detailed")
    _reset_premap_kernel_arg_live_mutation_counters()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_premap_consumer_readonly_gate_required=True,
        shadow_premap_consumer_readonly_gate_passed=True,
        shadow_premap_consumer_readonly_gate_id="unit_readonly_gate",
        shadow_premap_kernel_arg_handoff_minimal_identity_envelope_enabled=True,
        shadow_premap_kernel_arg_handoff_live_enabled=True,
        shadow_premap_kernel_arg_handoff_live_consumer_connected=True,
        shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled=False,
        shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled=False,
        shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled=False,
        shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled=False,
        shadow_premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled=True,
        shadow_premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled=True,
        shadow_premap_kernel_arg_handoff_gpu_assignment_validation_mode="trusted_refs",
        shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled=True,
    )
    sorted_token_ids = torch.arange(8, dtype=torch.int32)
    expert_ids = torch.tensor([1, 2], dtype=torch.int32)
    num_tokens_post_padded = torch.tensor([8], dtype=torch.int32)
    context: dict[str, object] = {}
    token = _ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR.set(context)
    try:
        out = recorder.maybe_reorder_prepared_expert_assignment(
            layer_id=0,
            sorted_token_ids=sorted_token_ids,
            expert_ids=expert_ids,
            num_tokens_post_padded=num_tokens_post_padded,
            block_size=4,
        )
    finally:
        _ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR.reset(token)

    assert out[0] is sorted_token_ids
    assert out[1] is expert_ids
    assert out[2] is num_tokens_post_padded
    package = context["premap_kernel_arg_live_mutation_package"]
    assert isinstance(package, dict)
    assert package["source"] == (
        "producer_future_wna16_typed_slot_readonly_live_package"
    )
    assert package["block_reason"] == "kernel_arg_handoff_readonly_live_consumer"
    assert package["producer_future_wna16_typed_slot_envelope"] is True
    assert package["producer_gpu_assignment_envelope"] is True
    assert package["producer_gpu_assignment_expert_ids"] is expert_ids
    assert package["producer_gpu_assignment_available"] is True
    assert (
        package["producer_gpu_assignment_current_expert_ptr_source_kind"]
        == "vllm_prelaunch_host_tensor"
    )
    counters = _premap_kernel_arg_live_mutation_counters()
    assert counters["package_producer_future_wna16_typed_slot_envelope_count"] == 1
    assert counters["package_producer_gpu_assignment_envelope_count"] == 1
    assert counters["single_field_replacement_live_passed_to_kernel_count"] == 0
    assert counters["single_field_replacement_dry_run_passed_to_kernel_count"] == 0


def test_readonly_future_typed_slot_producer_replaces_stale_mutation_package():
    _set_premap_kernel_arg_live_mutation_counter_mode("detailed")
    _reset_premap_kernel_arg_live_mutation_counters()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_premap_consumer_readonly_gate_required=True,
        shadow_premap_consumer_readonly_gate_passed=True,
        shadow_premap_consumer_readonly_gate_id="unit_readonly_gate",
        shadow_premap_kernel_arg_handoff_minimal_identity_envelope_enabled=True,
        shadow_premap_kernel_arg_handoff_live_enabled=True,
        shadow_premap_kernel_arg_handoff_live_consumer_connected=True,
        shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled=False,
        shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled=False,
        shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled=False,
        shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled=False,
        shadow_premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled=True,
        shadow_premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled=True,
        shadow_premap_kernel_arg_handoff_gpu_assignment_validation_mode="trusted_refs",
        shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled=True,
    )
    sorted_token_ids = torch.arange(8, dtype=torch.int32)
    expert_ids = torch.tensor([1, 2], dtype=torch.int32)
    num_tokens_post_padded = torch.tensor([8], dtype=torch.int32)
    stale_package = {
        "layer_id": 0,
        "source": "producer_future_wna16_typed_slot_live_kernel_arg_package",
        "block_reason": "kernel_arg_handoff_real_kernel_arg_mutation_live",
        "producer_future_wna16_typed_slot_envelope": True,
    }
    context: dict[str, object] = {
        "premap_kernel_arg_live_mutation_package": stale_package
    }
    token = _ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR.set(context)
    try:
        recorder.maybe_reorder_prepared_expert_assignment(
            layer_id=0,
            sorted_token_ids=sorted_token_ids,
            expert_ids=expert_ids,
            num_tokens_post_padded=num_tokens_post_padded,
            block_size=4,
        )
    finally:
        _ACTIVE_MOE_ASSIGNMENT_CONTEXT_VAR.reset(token)

    package = context["premap_kernel_arg_live_mutation_package"]
    assert isinstance(package, dict)
    assert package is not stale_package
    assert package["source"] == (
        "producer_future_wna16_typed_slot_readonly_live_package"
    )
    assert package["block_reason"] == "kernel_arg_handoff_readonly_live_consumer"
    assert package["producer_gpu_assignment_expert_ids"] is expert_ids


def test_gpu_assignment_trusted_refs_pointer_source_counters_derive_ready_from_source_kind():
    _set_premap_kernel_arg_live_mutation_counter_mode("detailed")
    _reset_premap_kernel_arg_live_mutation_counters()

    _record_premap_gpu_assignment_prelaunch_pointer_source_consumer_counters(
        {
            "producer_gpu_assignment_current_expert_ptr_source_kind": (
                "vllm_prelaunch_host_tensor"
            ),
            "producer_gpu_assignment_current_expert_ptr_ready_for_vllm_prelaunch_canary": (
                True
            ),
        }
    )

    counters = _premap_kernel_arg_live_mutation_counters()
    assert (
        counters[
            "gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_seen_count"
        ]
        == 1
    )
    assert (
        counters[
            "gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_unavailable_count"
        ]
        == 1
    )
    assert (
        counters[
            "gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_non_device_count"
        ]
        == 1
    )
    assert (
        counters[
            "gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_ready_source_mismatch_count"
        ]
        == 1
    )
    assert (
        counters[
            "gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_available_count"
        ]
        == 0
    )
    assert (
        counters[
            "gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_vllm_device_count"
        ]
        == 0
    )
