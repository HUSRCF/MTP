from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "run_awq_telemetry_ladder.py"
    spec = importlib.util.spec_from_file_location("run_awq_telemetry_ladder", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_attention_core_light_is_low_intrusion_mode() -> None:
    module = _load_module()
    MODES = module.MODES
    mode = MODES["attention_core_light"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "attention_core"
    assert mode["decoder_source_timing_mode"] == "attention_core"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["emit_descriptor_order_summaries"] is False
    assert mode["emit_transition_summaries"] is False


def test_attention_core_deep_splits_gdn_core() -> None:
    module = _load_module()
    mode = module.MODES["attention_core_deep"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "attention_core_deep"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["emit_descriptor_order_summaries"] is False
    assert mode["emit_transition_summaries"] is False


def test_attention_core_handoff_light_records_boundary_buckets() -> None:
    module = _load_module()
    mode = module.MODES["attention_core_handoff_light"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "attention_core_handoff_light"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["emit_descriptor_order_summaries"] is False
    assert mode["emit_transition_summaries"] is False


def test_attention_core_handoff_aggregate_uses_aggregate_component_logging() -> None:
    module = _load_module()
    mode = module.MODES["attention_core_handoff_aggregate"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "attention_core_handoff_light"
    assert mode["decoder_component_logging_mode"] == "attention_handoff_aggregate"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["emit_descriptor_order_summaries"] is False
    assert mode["emit_transition_summaries"] is False


def test_attention_core_handoff_counter_modes_use_flat_aggregate_logging() -> None:
    module = _load_module()

    expected = {
        "attention_core_handoff_aggregate_no_write": (
            "attention_handoff_aggregate_no_write"
        ),
        "attention_core_handoff_counter_only": "attention_handoff_counter_only",
        "attention_core_handoff_counter_only_no_write": (
            "attention_handoff_counter_only_no_write"
        ),
    }
    for name, logging_mode in expected.items():
        mode = module.MODES[name]
        assert mode["record_router_topk"] is False
        assert mode["emit_decoder_layer_timing"] is True
        assert mode["emit_decoder_component_timing"] is True
        assert mode["emit_moe_substage_timing"] is False
        assert mode["decoder_source_timing_mode"] == "attention_core_handoff_light"
        assert mode["decoder_component_logging_mode"] == logging_mode
        assert mode["moe_source_timing_mode"] == "off"
        assert mode["emit_wna16_kernel_timing"] is False
        assert mode["emit_summaries"] is True
        assert mode["emit_outcomes"] is False
        assert mode["outcome_logging_mode"] == "off"
        assert mode["emit_descriptor_order_summaries"] is False
        assert mode["emit_transition_summaries"] is False


def test_attention_total_only_keeps_moe_substage_off() -> None:
    module = _load_module()
    mode = module.MODES["attention_total_only"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["decoder_component_logging_mode"] == "rows"
    assert mode["moe_source_timing_mode"] == "off"


def test_decoder_layer_only_disables_component_and_moe_substage_timing() -> None:
    module = _load_module()
    mode = module.MODES["decoder_layer_only"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_production_like_explicitly_disables_source_timing() -> None:
    module = _load_module()

    for name in ("production_like", "production_like_force_shared_aux"):
        mode = module.MODES[name]
        assert mode["emit_decoder_component_timing"] is False
        assert mode["emit_moe_substage_timing"] is False
        assert mode["decoder_source_timing_mode"] == "off"
        assert mode["moe_source_timing_mode"] == "off"
        assert mode["emit_premap_summaries"] is False
        assert mode["emit_premap_address_manager_counters"] is False
        assert mode["emit_premap_consumer_mapping"] is False
        assert mode["premap_address_capacity_gate_path"] is None
        assert mode["premap_consumer_require_readonly_gate"] is False
        assert mode["premap_consumer_readonly_gate_path"] is None
        assert mode["premap_descriptor_prep_execution_mode"] == "off"
        assert mode["premap_kernel_arg_handoff_live_enabled"] is False
        assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is False
        assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
        assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is False
        assert (
            mode[
                "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live"
            ]
            is False
        )
        assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_premap_live_benchmark_modes_are_explicit_canaries() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]

    for name in (
        "premap_real_kernel_arg_mutation_observed_canary",
        "premap_single_field_replacement_live_observed_canary",
    ):
        mode = module.MODES[name]
        assert mode["record_router_topk"] is True
        assert mode["emit_premap_summaries"] is True
        assert mode["emit_premap_consumer_mapping"] is True
        assert mode["premap_risky_trace_canary"] is True
        assert mode["premap_consumer_require_readonly_gate"] is True
        assert mode["premap_descriptor_prep_execution_mode"] == (
            "readonly_descriptor_address_object"
        )
        assert mode["premap_kernel_arg_handoff_live_enabled"] is True
        assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is True
        assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is True
        assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is True
        assert mode["emit_decoder_layer_timing"] is False
        assert mode["emit_decoder_component_timing"] is False
        assert mode["emit_moe_substage_timing"] is False
        assert mode["decoder_source_timing_mode"] == "off"
        assert mode["moe_source_timing_mode"] == "off"
        assert mode["emit_wna16_kernel_timing"] is False
        assert mode["emit_outcomes"] is False
        assert mode["outcome_logging_mode"] == "off"
        assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]

    single_field = module.MODES["premap_single_field_replacement_live_observed_canary"]
    assert single_field["premap_consumer_readonly_gate_path"].endswith(
        "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
        "single_field_replacement_live_canary.yaml"
    )
    gate_path = root / single_field["premap_consumer_readonly_gate_path"]
    gate = yaml.safe_load(gate_path.read_text())
    assert gate["gate"]["check"]["allow_single_field_replacement_live"] is True
    assert single_field[
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"
    ] is True
    assert single_field[
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled"
    ] is True
    assert single_field[
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source"
    ] == "original_kernel_arg_identity"
    assert single_field["premap_kernel_arg_handoff_single_field_replacement_field"] == (
        "B_scale"
    )


def test_premap_live_minimal_keeps_capture_without_recording_topk() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    mode = module.MODES["premap_single_field_replacement_live_minimal"]

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is True
    assert mode["emit_premap_summaries"] is True
    assert mode["premap_summary_sample_period"] >= 1_000_000
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_mapping_sample_period"] >= 1_000_000
    assert mode["premap_consumer_resolve_real_handles"] is True
    assert mode["premap_risky_trace_canary"] is True
    assert mode["premap_kernel_arg_handoff_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is True
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_field"] == "B_scale"
    assert mode.get("emit_descriptor_layer_timing", False) is False
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]

    gate_path = root / mode["premap_consumer_readonly_gate_path"]
    gate = yaml.safe_load(gate_path.read_text())
    assert gate["gate"]["check"]["allow_single_field_replacement_live"] is True


def test_premap_live_minimal_identity_envelope_is_production_compatible() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    mode = module.MODES[
        "premap_single_field_replacement_live_minimal_identity_envelope"
    ]

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is True
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_resolve_real_handles"] is True
    assert mode["premap_consumer_require_readonly_gate"] is True
    assert mode["premap_kernel_arg_handoff_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is True
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is True
    assert mode["premap_kernel_arg_handoff_minimal_identity_envelope_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_field"] == "B_scale"
    assert mode[
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source"
    ] == "original_kernel_arg_identity"
    assert mode.get("emit_descriptor_layer_timing", False) is False
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"

    gate_path = root / mode["premap_consumer_readonly_gate_path"]
    gate = yaml.safe_load(gate_path.read_text())
    assert gate["gate"]["check"]["allow_single_field_replacement_live"] is True


def test_premap_live_producer_identity_envelope_skips_consumer_mapping() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    mode = module.MODES[
        "premap_single_field_replacement_live_producer_identity_envelope"
    ]

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_mapping_mode"] == "off"
    assert mode["premap_consumer_resolve_real_handles"] is False
    assert mode["premap_consumer_require_readonly_gate"] is True
    assert mode["premap_kernel_arg_handoff_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is True
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is True
    assert mode["premap_kernel_arg_handoff_minimal_identity_envelope_enabled"] is True
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled"
        ]
        is True
    )
    assert mode["premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_field"] == "B_scale"
    assert mode[
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source"
    ] == "original_kernel_arg_identity"
    assert mode.get("emit_descriptor_layer_timing", False) is False
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"

    gate_path = root / mode["premap_consumer_readonly_gate_path"]
    gate = yaml.safe_load(gate_path.read_text())
    assert gate["gate"]["check"]["allow_single_field_replacement_live"] is True


def test_premap_live_producer_identity_envelope_counter_off_keeps_live_path() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    mode = module.MODES[
        "premap_single_field_replacement_live_producer_identity_envelope_counter_off"
    ]

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_mapping_mode"] == "off"
    assert mode["premap_consumer_resolve_real_handles"] is False
    assert mode["premap_consumer_require_readonly_gate"] is True
    assert mode["premap_kernel_arg_handoff_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is True
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is True
    assert mode["premap_kernel_arg_handoff_minimal_identity_envelope_enabled"] is True
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled"
        ]
        is True
    )
    assert mode["premap_kernel_arg_handoff_live_counter_mode"] == "off"
    assert mode["premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_field"] == "B_scale"
    assert mode[
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source"
    ] == "original_kernel_arg_identity"
    assert mode.get("emit_descriptor_layer_timing", False) is False
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"

    gate_path = root / mode["premap_consumer_readonly_gate_path"]
    gate = yaml.safe_load(gate_path.read_text())
    assert gate["gate"]["check"]["allow_single_field_replacement_live"] is True


def test_premap_live_future_wna16_typed_slot_envelope_counter_off_keeps_live_path() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    mode = module.MODES[
        "premap_live_future_wna16_typed_slot_envelope_counter_off"
    ]

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_mapping_mode"] == "off"
    assert mode["premap_consumer_resolve_real_handles"] is False
    assert mode["premap_consumer_require_readonly_gate"] is True
    assert mode["premap_kernel_arg_handoff_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is True
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is True
    assert mode["premap_kernel_arg_handoff_minimal_identity_envelope_enabled"] is True
    assert (
        mode.get(
            "premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled",
            False,
        )
        is False
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is True
    )
    assert mode["premap_kernel_arg_handoff_live_counter_mode"] == "off"
    assert mode["premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_field"] == "B_scale"
    assert mode[
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source"
    ] == "original_kernel_arg_identity"
    assert mode.get("emit_descriptor_layer_timing", False) is False
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False


def test_production_batch_premap_live_typed_slot_envelope_stays_no_recorder() -> None:
    module = _load_module()
    mode = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_envelope_counter_off"
    ]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides["use_router_logits_recorder"] is False
    assert trace_overrides["capture_router_topk"] is False
    assert trace_overrides["capture_router_scores"] is False
    assert trace_overrides["allow_missing_router_trace"] is True
    assert (
        trace_overrides["allow_premap_live_config_without_router_recorder"]
        is True
    )
    assert vllm_overrides["use_router_logits_recorder"] is False
    assert vllm_overrides["enable_return_routed_experts"] is False
    assert vllm_overrides["max_num_seqs"] == 32
    assert vllm_overrides["engine_chunk_size"] == 32
    assert vllm_overrides["enforce_eager"] is True
    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is True
    )
    assert mode["premap_kernel_arg_handoff_live_counter_mode"] == "off"


def test_production_batch_graph_only_disables_enforce_eager() -> None:
    module = _load_module()
    eager = module.MODES["production_batch"]
    graph = module.MODES["production_batch_graph"]

    eager_trace = eager["trace_overrides"]
    graph_trace = graph["trace_overrides"]
    eager_vllm = eager_trace["vllm_overrides"]
    graph_vllm = graph_trace["vllm_overrides"]

    assert graph["runtime_shadow_enabled"] is False
    assert graph.get("record_router_topk", False) is False
    assert graph.get("emit_summaries", False) is False
    assert graph.get("emit_outcomes", False) is False
    assert graph_trace["use_router_logits_recorder"] is False
    assert graph_trace["capture_router_topk"] is False
    assert graph_trace["capture_router_scores"] is False
    assert graph_trace["allow_missing_router_trace"] is True
    assert graph_vllm["use_router_logits_recorder"] is False
    assert graph_vllm["enable_return_routed_experts"] is False
    assert graph_vllm["max_num_seqs"] == 32
    assert graph_vllm["engine_chunk_size"] == 32
    assert eager_vllm["enforce_eager"] is True
    assert graph_vllm["enforce_eager"] is False

    comparable_eager = dict(eager_vllm)
    comparable_graph = dict(graph_vllm)
    comparable_eager.pop("enforce_eager")
    comparable_graph.pop("enforce_eager")
    assert comparable_graph == comparable_eager


def test_production_batch_warmup_only_adds_warmup_overrides() -> None:
    module = _load_module()
    base = module.MODES["production_batch"]
    warmup = module.MODES["production_batch_warmup"]
    graph = module.MODES["production_batch_graph"]
    graph_warmup = module.MODES["production_batch_graph_warmup"]

    for base_mode, warmup_mode, enforce_eager in (
        (base, warmup, True),
        (graph, graph_warmup, False),
    ):
        base_trace = base_mode["trace_overrides"]
        warmup_trace = warmup_mode["trace_overrides"]
        base_vllm = base_trace["vllm_overrides"]
        warmup_vllm = warmup_trace["vllm_overrides"]

        assert warmup_mode["runtime_shadow_enabled"] is False
        assert warmup_trace["use_router_logits_recorder"] is False
        assert warmup_trace["capture_router_topk"] is False
        assert warmup_trace["capture_router_scores"] is False
        assert warmup_vllm["use_router_logits_recorder"] is False
        assert warmup_vllm["enable_return_routed_experts"] is False
        assert warmup_vllm["enforce_eager"] is enforce_eager
        assert warmup_vllm["warmup_prompt_count"] == 32
        assert warmup_vllm["warmup_max_tokens"] == 16

        comparable_base = dict(base_vllm)
        comparable_warmup = dict(warmup_vllm)
        comparable_warmup.pop("warmup_prompt_count")
        comparable_warmup.pop("warmup_max_tokens")
        assert comparable_warmup == comparable_base


def test_production_batch_payload_cache_ready_time_graph_warmup_is_accounting_only() -> None:
    module = _load_module()
    mode = module.MODES[
        "production_batch_premap_payload_cache_ready_time_graph_warmup_counter_off"
    ]
    graph_warmup = module.MODES["production_batch_graph_warmup"]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]
    graph_vllm = graph_warmup["trace_overrides"]["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides["allow_premap_live_config_without_router_recorder"] is True
    assert trace_overrides["use_router_logits_recorder"] is False
    assert trace_overrides["capture_router_topk"] is False
    assert trace_overrides["capture_router_scores"] is False
    assert vllm_overrides["enforce_eager"] is False
    assert vllm_overrides["warmup_prompt_count"] == 32
    assert vllm_overrides["warmup_max_tokens"] == 16
    assert vllm_overrides["engine_chunk_size"] == graph_vllm["engine_chunk_size"] == 32

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is False
    assert mode["emit_premap_payload_cache_manager_counters"] is True
    assert mode["premap_payload_cache_manager_mode"] == "ready_time"
    assert mode["premap_payload_cache_manager_capacity"] == 12_288
    assert mode["transition_summary_mode"] == "matrix_topk"
    assert mode["transition_topk_count"] == 8
    assert mode["transition_matrix_path"] == (
        "outputs/artifacts/transition_matrix_512sample_calibrated.pt"
    )
    assert mode["transition_premap_source"] == (
        "prelaunch_observed_transition_premap_shadow"
    )
    assert mode["premap_payload_cache_manager_issue_sources"] == [
        "prelaunch_observed_transition_premap_shadow"
    ]
    assert mode["premap_payload_cache_manager_demand_on_consumer"] is True
    assert mode["premap_payload_cache_manager_emit_consumer_rows"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_kernel_arg_handoff_live_enabled"] is False
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is False
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is False
    assert (
        mode["premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"]
        is False
    )
    assert mode["descriptor_order_reorder_mvp_enabled"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_production_batch_payload_cache_ready_time_eager_counter_off_is_accounting_only() -> None:
    module = _load_module()
    mode = module.MODES[
        "production_batch_premap_payload_cache_ready_time_counter_off"
    ]
    production_batch = module.MODES["production_batch"]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]
    base_vllm = production_batch["trace_overrides"]["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides["allow_premap_live_config_without_router_recorder"] is True
    assert trace_overrides["use_router_logits_recorder"] is False
    assert trace_overrides["capture_router_topk"] is False
    assert trace_overrides["capture_router_scores"] is False
    assert vllm_overrides == base_vllm

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is False
    assert mode["emit_premap_payload_cache_manager_counters"] is True
    assert mode["premap_payload_cache_manager_mode"] == "ready_time"
    assert mode["premap_payload_cache_manager_capacity"] == 12_288
    assert mode["transition_summary_mode"] == "matrix_topk"
    assert mode["transition_topk_count"] == 8
    assert mode["transition_matrix_path"] == (
        "outputs/artifacts/transition_matrix_512sample_calibrated.pt"
    )
    assert mode["transition_premap_source"] == (
        "prelaunch_observed_transition_premap_shadow"
    )
    assert mode["premap_payload_cache_manager_issue_sources"] == [
        "prelaunch_observed_transition_premap_shadow"
    ]
    assert mode["premap_payload_cache_manager_demand_on_consumer"] is True
    assert mode["premap_payload_cache_manager_emit_consumer_rows"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_kernel_arg_handoff_live_enabled"] is False
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is False
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is False
    assert (
        mode["premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"]
        is False
    )
    assert mode["descriptor_order_reorder_mvp_enabled"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_production_batch_premap_live_typed_slot_envelope_detailed_only_enables_counters() -> None:
    module = _load_module()
    detailed = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_envelope_detailed"
    ]
    counter_off = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_envelope_counter_off"
    ]

    assert detailed["runtime_shadow_enabled"] is False
    assert detailed["trace_overrides"] == counter_off["trace_overrides"]
    assert detailed["record_router_topk"] is False
    assert detailed["capture_router_topk"] is False
    assert detailed["emit_premap_consumer_mapping"] is False
    assert counter_off["premap_kernel_arg_handoff_live_counter_mode"] == "off"
    assert detailed["premap_kernel_arg_handoff_live_counter_mode"] == "detailed"


def test_production_batch_premap_live_gpu_assignment_envelope_stays_no_recorder_no_mapping() -> None:
    module = _load_module()
    mode = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off"
    ]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides["use_router_logits_recorder"] is False
    assert trace_overrides["capture_router_topk"] is False
    assert trace_overrides["capture_router_scores"] is False
    assert trace_overrides["allow_missing_router_trace"] is True
    assert (
        trace_overrides["allow_premap_live_config_without_router_recorder"]
        is True
    )
    assert vllm_overrides["use_router_logits_recorder"] is False
    assert vllm_overrides["enable_return_routed_experts"] is False
    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_mapping_mode"] == "off"
    assert mode["premap_consumer_resolve_real_handles"] is False
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is True
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled"
        ]
        is True
    )
    assert (
        mode.get(
            "premap_kernel_arg_handoff_gpu_assignment_validation_mode", "identity"
        )
        == "identity"
    )
    assert mode["premap_kernel_arg_handoff_prepared_table_materialization_mode"] == "off"
    assert (
        mode.get(
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled",
            False,
        )
        is False
    )
    assert mode["premap_kernel_arg_handoff_live_counter_mode"] == "off"


def test_production_batch_premap_live_gpu_assignment_trusted_refs_only_skips_identity_validation() -> None:
    module = _load_module()
    trusted = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_counter_off"
    ]
    base = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off"
    ]

    assert trusted["runtime_shadow_enabled"] is False
    assert trusted["trace_overrides"] == base["trace_overrides"]
    assert trusted["record_router_topk"] is False
    assert trusted["capture_router_topk"] is False
    assert trusted["emit_premap_consumer_mapping"] is False
    assert (
        trusted[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is True
    )
    assert (
        trusted[
            "premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled"
        ]
        is True
    )
    assert (
        trusted["premap_kernel_arg_handoff_gpu_assignment_validation_mode"]
        == "trusted_refs"
    )
    assert (
        trusted.get(
            "premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled",
            False,
        )
        is False
    )
    assert (
        trusted.get(
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled",
            False,
        )
        is False
    )
    assert trusted["premap_kernel_arg_handoff_prepared_table_materialization_mode"] == "off"
    assert trusted["premap_kernel_arg_handoff_live_counter_mode"] == "off"

    comparable_trusted = dict(trusted)
    comparable_base = dict(base)
    comparable_trusted.pop("premap_kernel_arg_handoff_gpu_assignment_validation_mode")
    assert comparable_trusted == comparable_base


def test_production_batch_gpu_assignment_envelope_graph_warmup_only_changes_vllm_posture() -> None:
    module = _load_module()
    pairs = (
        (
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off",
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off_graph_warmup",
            "identity",
        ),
        (
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_counter_off",
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_counter_off_graph_warmup",
            "trusted_refs",
        ),
        (
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_counter_off",
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_counter_off_graph_warmup",
            "identity",
        ),
        (
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_trust_producer_refs_counter_off",
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_trust_producer_refs_counter_off_graph_warmup",
            "identity",
        ),
    )

    for base_name, graph_name, validation_mode in pairs:
        base = module.MODES[base_name]
        graph = module.MODES[graph_name]
        base_trace = base["trace_overrides"]
        graph_trace = graph["trace_overrides"]
        base_vllm = base_trace["vllm_overrides"]
        graph_vllm = graph_trace["vllm_overrides"]

        assert graph["runtime_shadow_enabled"] is False
        assert graph_trace["use_router_logits_recorder"] is False
        assert graph_trace["capture_router_topk"] is False
        assert graph_trace["capture_router_scores"] is False
        assert graph_trace["allow_missing_router_trace"] is True
        assert (
            graph_trace["allow_premap_live_config_without_router_recorder"]
            is True
        )
        assert graph_vllm["use_router_logits_recorder"] is False
        assert graph_vllm["enable_return_routed_experts"] is False
        assert graph_vllm["enforce_eager"] is False
        assert graph_vllm["warmup_prompt_count"] == 32
        assert graph_vllm["warmup_max_tokens"] == 16
        assert graph["record_router_topk"] is False
        assert graph["capture_router_topk"] is False
        assert graph["emit_premap_consumer_mapping"] is False
        assert graph["premap_consumer_mapping_emit_rows"] is False
        assert graph["premap_consumer_mapping_mode"] == "off"
        assert graph["premap_consumer_resolve_real_handles"] is False
        assert (
            graph[
                "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
            ]
            is True
        )
        assert (
            graph[
                "premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled"
            ]
            is True
        )
        assert (
            graph.get(
                "premap_kernel_arg_handoff_gpu_assignment_validation_mode",
                "identity",
            )
            == validation_mode
        )
        assert graph["premap_kernel_arg_handoff_prepared_table_materialization_mode"] == "off"
        assert graph["premap_kernel_arg_handoff_live_counter_mode"] == "off"

        comparable_base_vllm = dict(base_vllm)
        comparable_graph_vllm = dict(graph_vllm)
        comparable_base_vllm.pop("enforce_eager")
        comparable_graph_vllm.pop("enforce_eager")
        comparable_graph_vllm.pop("warmup_prompt_count")
        comparable_graph_vllm.pop("warmup_max_tokens")
        assert comparable_graph_vllm == comparable_base_vllm

        comparable_base = dict(base)
        comparable_graph = dict(graph)
        comparable_base.pop("trace_overrides")
        comparable_graph.pop("trace_overrides")
        assert comparable_graph == comparable_base


def test_production_batch_premap_live_gpu_assignment_trusted_refs_detailed_only_enables_counters() -> None:
    module = _load_module()
    detailed = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_detailed"
    ]
    counter_off = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_counter_off"
    ]

    assert detailed["runtime_shadow_enabled"] is False
    assert detailed["trace_overrides"] == counter_off["trace_overrides"]
    assert detailed["record_router_topk"] is False
    assert detailed["capture_router_topk"] is False
    assert detailed["emit_premap_consumer_mapping"] is False
    assert (
        detailed["premap_kernel_arg_handoff_gpu_assignment_validation_mode"]
        == "trusted_refs"
    )
    assert counter_off["premap_kernel_arg_handoff_live_counter_mode"] == "off"
    assert detailed["premap_kernel_arg_handoff_live_counter_mode"] == "detailed"

    comparable_detailed = dict(detailed)
    comparable_counter_off = dict(counter_off)
    comparable_detailed["premap_kernel_arg_handoff_live_counter_mode"] = "off"
    assert comparable_detailed == comparable_counter_off


def test_production_batch_gpu_assignment_kernel_variant_stays_separate_from_prepared_table_variant() -> None:
    module = _load_module()
    mode = module.MODES[
        "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_counter_off"
    ]
    trust_mode = module.MODES[
        "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_trust_producer_refs_counter_off"
    ]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides["use_router_logits_recorder"] is False
    assert trace_overrides["capture_router_topk"] is False
    assert (
        trace_overrides["allow_premap_live_config_without_router_recorder"]
        is True
    )
    assert vllm_overrides["use_router_logits_recorder"] is False
    assert vllm_overrides["enable_return_routed_experts"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert mode["premap_consumer_mapping_mode"] == "off"
    assert mode["premap_consumer_resolve_real_handles"] is False
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is True
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled"
        ]
        is True
    )
    assert (
        mode.get(
            "premap_kernel_arg_handoff_gpu_assignment_validation_mode", "identity"
        )
        == "identity"
    )
    assert (
        mode["premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled"]
        is True
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"
        ]
        is False
    )
    assert mode["premap_kernel_arg_handoff_prepared_table_materialization_mode"] == "off"
    assert mode["premap_kernel_arg_handoff_live_counter_mode"] == "off"

    assert (
        trust_mode[
            "premap_kernel_arg_handoff_gpu_assignment_kernel_variant_trust_producer_refs"
        ]
        is True
    )
    comparable_trust = dict(trust_mode)
    comparable_base = dict(mode)
    comparable_trust.pop(
        "premap_kernel_arg_handoff_gpu_assignment_kernel_variant_trust_producer_refs"
    )
    assert comparable_trust == comparable_base


def test_production_batch_direct_topk_identity_uses_no_recorder_no_premap_package() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    mode = module.MODES[
        "production_batch_descriptor_order_direct_topk_identity_counter_off"
    ]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides["use_router_logits_recorder"] is False
    assert trace_overrides["capture_router_topk"] is False
    assert trace_overrides["capture_router_scores"] is False
    assert (
        trace_overrides["allow_premap_live_config_without_router_recorder"]
        is True
    )
    assert vllm_overrides["use_router_logits_recorder"] is False
    assert vllm_overrides["enable_return_routed_experts"] is False
    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_summaries"] is False
    assert mode["emit_outcomes"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is False
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_mapping_mode"] == "noop_assertion"
    assert mode["premap_consumer_resolve_real_handles"] is False
    assert mode["premap_consumer_require_readonly_gate"] is False
    assert "premap_consumer_readonly_gate_path" not in mode
    assert mode["premap_descriptor_prep_execution_mode"] == "off"
    assert mode["premap_kernel_arg_handoff_live_enabled"] is False
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is False
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is False
    assert mode["premap_kernel_arg_handoff_minimal_identity_envelope_enabled"] is False
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is False
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled"
        ]
        is False
    )
    assert (
        mode["premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled"]
        is False
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"
        ]
        is False
    )
    assert mode["descriptor_order_reorder_mvp_enabled"] is True
    assert mode["descriptor_order_reorder_mvp_apply_mode"] == "apply"
    assert (
        mode["descriptor_order_reorder_mvp_attribution_mode"]
        == "direct_topk_identity_kernel"
    )
    assert mode["descriptor_order_reorder_mvp_require_profitable"] is False
    assert mode["descriptor_order_emit_consumer_handle_events"] is False
    assert mode["emit_descriptor_order_summaries"] is False


def test_production_batch_source_block_ids_kernel_uses_non_identity_descriptor_order_only() -> None:
    module = _load_module()
    mode = module.MODES[
        "production_batch_descriptor_order_source_block_ids_kernel_counter_off"
    ]
    identity = module.MODES[
        "production_batch_descriptor_order_direct_topk_identity_counter_off"
    ]

    assert mode["runtime_shadow_enabled"] is False
    assert mode["trace_overrides"] == identity["trace_overrides"]
    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_summaries"] is False
    assert mode["emit_outcomes"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is False
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_mapping_mode"] == "noop_assertion"
    assert mode["premap_consumer_resolve_real_handles"] is False
    assert mode["premap_descriptor_prep_execution_mode"] == "off"
    assert mode["premap_kernel_arg_handoff_live_enabled"] is False
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is False
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is False
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled"
        ]
        is False
    )
    assert (
        mode["premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled"]
        is False
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"
        ]
        is False
    )
    assert mode["descriptor_order_reorder_mvp_enabled"] is True
    assert mode["descriptor_order_reorder_mvp_apply_mode"] == "apply"
    assert (
        mode["descriptor_order_reorder_mvp_attribution_mode"]
        == "source_block_ids_kernel"
    )
    assert mode["descriptor_order_reorder_mvp_require_profitable"] is False

    comparable_mode = dict(mode)
    comparable_identity = dict(identity)
    comparable_mode["descriptor_order_reorder_mvp_attribution_mode"] = (
        comparable_identity["descriptor_order_reorder_mvp_attribution_mode"]
    )
    assert comparable_mode == comparable_identity


def test_production_batch_direct_topk_identity_readonly_gate_preflight() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    from mtp_expert_prefetch.tracing.vllm_router_trace import (
        _apply_premap_consumer_readonly_gate,
        _runtime_shadow_options,
    )

    mode = module.MODES[
        "production_batch_descriptor_order_direct_topk_identity_counter_off"
    ]
    runtime_options = {
        key: value
        for key, value in mode.items()
        if key not in module._MODE_RESERVED_KEYS
    }
    trace_options = dict(mode["trace_overrides"])
    trace_options["runtime_shadow"] = {
        **runtime_options,
        "enabled": bool(mode["runtime_shadow_enabled"]),
    }
    vllm_options = dict(trace_options["vllm_overrides"])

    merged = _runtime_shadow_options(trace_options, vllm_options)
    updated = _apply_premap_consumer_readonly_gate(
        merged,
        project_root=root,
    )

    assert updated["premap_consumer_require_readonly_gate"] is False
    assert updated.get("premap_consumer_readonly_gate_path") is None
    assert updated["premap_kernel_arg_handoff_live_enabled"] is False
    assert updated["premap_descriptor_prep_execution_mode"] == "off"
    assert updated["emit_premap_consumer_mapping"] is True
    assert updated["premap_consumer_mapping_emit_rows"] is False
    assert updated["premap_consumer_mapping_mode"] == "noop_assertion"
    assert updated["premap_consumer_resolve_real_handles"] is False


def test_production_batch_reuse_llm_modes_only_add_engine_reuse() -> None:
    module = _load_module()
    pairs = (
        (
            "production_batch",
            "production_batch_reuse_llm",
        ),
        (
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off",
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off_reuse_llm",
        ),
        (
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_counter_off",
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_counter_off_reuse_llm",
        ),
        (
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_detailed",
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_detailed_reuse_llm",
        ),
        (
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off_graph_warmup",
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off_graph_warmup_reuse_llm",
        ),
        (
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_counter_off_graph_warmup",
            "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_trusted_refs_counter_off_graph_warmup_reuse_llm",
        ),
        (
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_counter_off",
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_counter_off_reuse_llm",
        ),
        (
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_counter_off_graph_warmup",
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_counter_off_graph_warmup_reuse_llm",
        ),
        (
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_trust_producer_refs_counter_off_graph_warmup",
            "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_trust_producer_refs_counter_off_graph_warmup_reuse_llm",
        ),
        (
            "production_batch_descriptor_order_direct_topk_identity_counter_off",
            "production_batch_descriptor_order_direct_topk_identity_counter_off_reuse_llm",
        ),
        (
            "production_batch_descriptor_order_source_block_ids_kernel_counter_off",
            "production_batch_descriptor_order_source_block_ids_kernel_counter_off_reuse_llm",
        ),
        (
            "production_batch_graph",
            "production_batch_graph_reuse_llm",
        ),
        (
            "production_batch_warmup",
            "production_batch_warmup_reuse_llm",
        ),
        (
            "production_batch_graph_warmup",
            "production_batch_graph_warmup_reuse_llm",
        ),
        (
            "production_batch_premap_payload_cache_ready_time_graph_warmup_counter_off",
            "production_batch_premap_payload_cache_ready_time_graph_warmup_counter_off_reuse_llm",
        ),
        (
            "production_batch_premap_payload_cache_ready_time_counter_off",
            "production_batch_premap_payload_cache_ready_time_counter_off_reuse_llm",
        ),
    )

    for base_name, reuse_name in pairs:
        base = module.MODES[base_name]
        reuse = module.MODES[reuse_name]
        base_trace = base["trace_overrides"]
        reuse_trace = reuse["trace_overrides"]
        base_vllm = base_trace["vllm_overrides"]
        reuse_vllm = reuse_trace["vllm_overrides"]

        assert reuse["runtime_shadow_enabled"] is base["runtime_shadow_enabled"]
        assert reuse_trace["use_router_logits_recorder"] is False
        assert reuse_trace["capture_router_topk"] is False
        assert reuse_trace["capture_router_scores"] is False
        assert reuse_vllm["use_router_logits_recorder"] is False
        assert reuse_vllm["enable_return_routed_experts"] is False
        assert reuse_vllm["engine_chunk_size"] == base_vllm["engine_chunk_size"] == 32
        assert not bool(base_vllm.get("reuse_llm_across_chunks", False))
        assert reuse_vllm["reuse_llm_across_chunks"] is True

        comparable_base = dict(base_vllm)
        comparable_reuse = dict(reuse_vllm)
        comparable_reuse.pop("reuse_llm_across_chunks")
        assert comparable_reuse == comparable_base
        if base_name == "production_batch_graph":
            assert reuse_vllm["enforce_eager"] is False


def test_production_batch_premap_live_typed_slot_kernel_variant_uses_no_recorder_prepared_table() -> None:
    module = _load_module()
    mode = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_kernel_variant_counter_off"
    ]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides["use_router_logits_recorder"] is False
    assert trace_overrides["capture_router_topk"] is False
    assert trace_overrides["capture_router_scores"] is False
    assert trace_overrides["allow_missing_router_trace"] is True
    assert (
        trace_overrides["allow_premap_live_config_without_router_recorder"]
        is True
    )
    assert vllm_overrides["use_router_logits_recorder"] is False
    assert vllm_overrides["enable_return_routed_experts"] is False
    assert vllm_overrides["max_num_seqs"] == 32
    assert vllm_overrides["engine_chunk_size"] == 32
    assert vllm_overrides["enforce_eager"] is True
    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is True
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_mapping_mode"] == "noop_assertion"
    assert mode["premap_consumer_resolve_real_handles"] is True
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is True
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"
        ]
        is True
    )
    assert (
        mode["premap_kernel_arg_handoff_prepared_table_materialization_mode"]
        == "producer_native_adapter"
    )
    assert mode["premap_kernel_arg_handoff_live_counter_mode"] == "off"


def test_production_batch_premap_live_typed_slot_slim_kernel_variant_uses_no_recorder_prepared_table() -> None:
    module = _load_module()
    mode = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_slim_kernel_variant_counter_off"
    ]
    generic = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_kernel_variant_counter_off"
    ]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides == generic["trace_overrides"]
    assert vllm_overrides["use_router_logits_recorder"] is False
    assert vllm_overrides["enable_return_routed_experts"] is False
    assert vllm_overrides["max_num_seqs"] == 32
    assert vllm_overrides["engine_chunk_size"] == 32
    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_resolve_real_handles"] is True
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is True
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"
        ]
        is False
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_future_wna16_typed_slot_slim_kernel_variant_enabled"
        ]
        is True
    )
    assert (
        mode["premap_kernel_arg_handoff_prepared_table_materialization_mode"]
        == "producer_native_adapter"
    )
    assert mode["premap_kernel_arg_handoff_live_counter_mode"] == "off"


def test_production_batch_premap_live_typed_slot_slim_kernel_variant_graph_reuse_modes() -> None:
    module = _load_module()
    base = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_slim_kernel_variant_counter_off"
    ]
    graph = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_slim_kernel_variant_counter_off_graph_warmup"
    ]
    reuse = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_slim_kernel_variant_counter_off_graph_warmup_reuse_llm"
    ]

    base_vllm = base["trace_overrides"]["vllm_overrides"]
    graph_vllm = graph["trace_overrides"]["vllm_overrides"]
    reuse_vllm = reuse["trace_overrides"]["vllm_overrides"]

    assert graph["runtime_shadow_enabled"] is False
    assert graph["record_router_topk"] is False
    assert graph["capture_router_topk"] is False
    assert (
        graph[
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"
        ]
        is False
    )
    assert (
        graph[
            "premap_kernel_arg_handoff_future_wna16_typed_slot_slim_kernel_variant_enabled"
        ]
        is True
    )
    assert graph_vllm["enforce_eager"] is False
    assert graph_vllm["warmup_prompt_count"] == 32
    assert graph_vllm["warmup_max_tokens"] == 16
    assert not bool(base_vllm.get("reuse_llm_across_chunks", False))
    assert reuse_vllm["reuse_llm_across_chunks"] is True
    comparable_graph = dict(graph_vllm)
    comparable_reuse = dict(reuse_vllm)
    comparable_reuse.pop("reuse_llm_across_chunks")
    assert comparable_reuse == comparable_graph


def test_production_batch_premap_live_typed_slot_kernel_variant_detailed_only_enables_counters() -> None:
    module = _load_module()
    detailed = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_kernel_variant_detailed"
    ]
    counter_off = module.MODES[
        "production_batch_premap_live_future_wna16_typed_slot_kernel_variant_counter_off"
    ]

    assert detailed["runtime_shadow_enabled"] is False
    assert detailed["trace_overrides"] == counter_off["trace_overrides"]
    assert detailed["record_router_topk"] is False
    assert detailed["capture_router_topk"] is False
    assert detailed["emit_premap_consumer_mapping"] is True
    assert detailed["premap_consumer_mapping_emit_rows"] is False
    assert counter_off["premap_kernel_arg_handoff_live_counter_mode"] == "off"
    assert detailed["premap_kernel_arg_handoff_live_counter_mode"] == "detailed"


def test_production_batch_premap_live_prepared_alias_adapter_keeps_original_wna16_no_recorder() -> None:
    module = _load_module()
    mode = module.MODES[
        "production_batch_premap_live_prepared_alias_adapter_counter_off"
    ]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides["use_router_logits_recorder"] is False
    assert trace_overrides["capture_router_topk"] is False
    assert trace_overrides["capture_router_scores"] is False
    assert trace_overrides["allow_missing_router_trace"] is True
    assert (
        trace_overrides["allow_premap_live_config_without_router_recorder"]
        is True
    )
    assert vllm_overrides["use_router_logits_recorder"] is False
    assert vllm_overrides["enable_return_routed_experts"] is False
    assert vllm_overrides["max_num_seqs"] == 32
    assert vllm_overrides["engine_chunk_size"] == 32
    assert vllm_overrides["enforce_eager"] is True
    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is True
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_resolve_real_handles"] is True
    assert (
        mode["premap_kernel_arg_handoff_single_field_replacement_candidate_source"]
        == "prepared_handle_table"
    )
    assert (
        mode["premap_kernel_arg_handoff_prepared_table_materialization_mode"]
        == "original_kernel_arg_alias_after_prepared_handle_check"
    )
    assert (
        mode.get(
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled",
            False,
        )
        is False
    )
    assert mode["premap_kernel_arg_handoff_live_counter_mode"] == "off"


def test_production_batch_premap_live_prepared_alias_adapter_detailed_only_enables_counters() -> None:
    module = _load_module()
    detailed = module.MODES[
        "production_batch_premap_live_prepared_alias_adapter_detailed"
    ]
    counter_off = module.MODES[
        "production_batch_premap_live_prepared_alias_adapter_counter_off"
    ]

    assert detailed["runtime_shadow_enabled"] is False
    assert detailed["trace_overrides"] == counter_off["trace_overrides"]
    assert detailed["record_router_topk"] is False
    assert detailed["capture_router_topk"] is False
    assert detailed["emit_premap_consumer_mapping"] is True
    assert detailed["premap_consumer_mapping_emit_rows"] is False
    assert (
        detailed["premap_kernel_arg_handoff_prepared_table_materialization_mode"]
        == "original_kernel_arg_alias_after_prepared_handle_check"
    )
    assert counter_off["premap_kernel_arg_handoff_live_counter_mode"] == "off"
    assert detailed["premap_kernel_arg_handoff_live_counter_mode"] == "detailed"


def test_production_batch_premap_prelaunch_mapping_only_is_attribution_only() -> None:
    module = _load_module()
    mode = module.MODES["production_batch_premap_prelaunch_mapping_only_counter_off"]
    trace_overrides = mode["trace_overrides"]
    vllm_overrides = trace_overrides["vllm_overrides"]

    assert mode["runtime_shadow_enabled"] is False
    assert trace_overrides["use_router_logits_recorder"] is False
    assert trace_overrides["capture_router_topk"] is False
    assert trace_overrides["capture_router_scores"] is False
    assert trace_overrides["allow_missing_router_trace"] is True
    assert (
        trace_overrides["allow_premap_live_config_without_router_recorder"]
        is True
    )
    assert vllm_overrides["use_router_logits_recorder"] is False
    assert vllm_overrides["enable_return_routed_experts"] is False
    assert vllm_overrides["max_num_seqs"] == 32
    assert vllm_overrides["engine_chunk_size"] == 32
    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is True
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_resolve_real_handles"] is False
    assert mode["premap_consumer_require_readonly_gate"] is False
    assert mode["premap_consumer_readonly_gate_path"] is None
    assert mode["premap_descriptor_prep_execution_mode"] == "off"
    assert mode["premap_kernel_arg_handoff_live_enabled"] is False
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is False
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is False
    assert (
        mode["premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"]
        is False
    )
    assert (
        mode["premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"]
        is False
    )


def test_premap_live_future_wna16_typed_slot_kernel_variant_counter_off_uses_independent_variant() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    mode = module.MODES[
        "premap_live_future_wna16_typed_slot_kernel_variant_counter_off"
    ]

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is True
    assert mode["emit_premap_summaries"] is True
    assert mode["emit_premap_address_manager_counters"] is True
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_mapping_mode"] == "noop_assertion"
    assert mode["premap_consumer_mapping_source"] == "fused_moe_prepare_expert_assignment"
    assert mode["premap_consumer_resolve_real_handles"] is True
    assert mode["premap_consumer_require_readonly_gate"] is True
    assert mode["premap_descriptor_prep_execution_mode"] == "readonly_descriptor_address_object"
    assert mode["premap_kernel_arg_handoff_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is True
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is True
    assert mode["premap_kernel_arg_handoff_minimal_identity_envelope_enabled"] is True
    assert (
        mode.get(
            "premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled",
            False,
        )
        is False
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled"
        ]
        is True
    )
    assert (
        mode[
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"
        ]
        is True
    )
    assert (
        mode["premap_kernel_arg_handoff_prepared_table_materialization_mode"]
        == "producer_native_adapter"
    )
    assert mode["premap_kernel_arg_handoff_live_counter_mode"] == "off"
    assert mode["premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_live_enabled"] is True
    assert mode[
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source"
    ] == "original_kernel_arg_identity"
    assert mode["premap_policy"] == "premap_only_with_consumer_mapping_noop"
    assert mode["premap_descriptor_bytes"] == 4096
    assert mode["emit_wna16_kernel_timing"] is False

    gate_path = root / mode["premap_consumer_readonly_gate_path"]
    gate = yaml.safe_load(gate_path.read_text())
    assert gate["gate"]["check"]["allow_single_field_replacement_live"] is True


def test_premap_live_future_wna16_typed_slot_kernel_variant_prepared_table_strict_enables_counters() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    strict = module.MODES[
        "premap_live_future_wna16_typed_slot_kernel_variant_prepared_table_strict"
    ]
    base = module.MODES[
        "premap_live_future_wna16_typed_slot_kernel_variant_counter_off"
    ]

    for key in (
        "emit_premap_summaries",
        "emit_premap_address_manager_counters",
        "emit_premap_consumer_mapping",
        "premap_consumer_resolve_real_handles",
        "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled",
    ):
        assert strict[key] == base[key]
    assert strict["premap_kernel_arg_handoff_live_counter_mode"] == "detailed"
    assert base["premap_kernel_arg_handoff_live_counter_mode"] == "off"
    assert (
        strict["premap_kernel_arg_handoff_prepared_table_materialization_mode"]
        == "producer_native_adapter"
    )
    assert (
        strict["premap_risky_trace_canary_scope"]
        == "benchmark_premap_live_future_wna16_typed_slot_kernel_variant_prepared_table_strict"
    )
    assert strict["emit_outcomes"] is False
    assert strict["outcome_logging_mode"] == "off"

    gate_path = root / strict["premap_consumer_readonly_gate_path"]
    gate = yaml.safe_load(gate_path.read_text())
    assert gate["gate"]["check"]["allow_single_field_replacement_live"] is True


def test_premap_prepared_handle_table_live_canary_is_explicitly_diagnostic() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    mode = module.MODES[
        "premap_single_field_replacement_live_prepared_handle_table_canary"
    ]

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is True
    assert mode["emit_premap_summaries"] is True
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_mapping_emit_rows"] is False
    assert mode["premap_consumer_resolve_real_handles"] is True
    assert mode["premap_consumer_require_readonly_gate"] is True
    assert mode["premap_risky_trace_canary"] is True
    assert mode["premap_kernel_arg_handoff_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is True
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_live_enabled"] is True
    assert (
        mode[
            "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live"
        ]
        is True
    )
    assert mode[
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source"
    ] == "prepared_handle_table"
    assert mode["premap_kernel_arg_handoff_single_field_replacement_field"] == "B_scale"
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["emit_outcomes"] is False


def test_premap_prepared_alias_adapter_keeps_wna16_arg_type_boundary() -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    mode = module.MODES[
        "premap_single_field_replacement_live_prepared_alias_adapter"
    ]

    assert mode["record_router_topk"] is False
    assert mode["capture_router_topk"] is True
    assert mode["emit_premap_consumer_mapping"] is True
    assert mode["premap_consumer_resolve_real_handles"] is True
    assert mode["premap_kernel_arg_handoff_live_enabled"] is True
    assert mode["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert mode["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is True
    assert mode["premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"] is True
    assert mode["premap_kernel_arg_handoff_single_field_replacement_live_enabled"] is True
    assert (
        mode[
            "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live"
        ]
        is False
    )
    assert mode[
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source"
    ] == "prepared_handle_table"
    assert mode[
        "premap_kernel_arg_handoff_prepared_table_materialization_mode"
    ] == "original_kernel_arg_alias_after_prepared_handle_check"
    assert mode["premap_kernel_arg_handoff_single_field_replacement_field"] == "B_scale"
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"

    gate_path = root / mode["premap_consumer_readonly_gate_path"]
    gate = yaml.safe_load(gate_path.read_text())
    assert gate["gate"]["check"][
        "allow_single_field_replacement_prepared_table_candidate_source"
    ] is True
    assert gate["contract"]["single_field_replacement_candidate_source"] == (
        "prepared_handle_table"
    )


def test_force_shared_aux_modes_clear_disable_shared_stream_env() -> None:
    module = _load_module()

    for name in ("production_like_force_shared_aux", "diagnostic_light_force_shared_aux"):
        mode = module.MODES[name]
        assert mode["shared_experts_force_aux_stream"] is True
        assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_diagnostic_light_force_shared_aux_keeps_diagnostic_timing() -> None:
    module = _load_module()
    mode = module.MODES["diagnostic_light_force_shared_aux"]

    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_write_mode_config_does_not_emit_reserved_env_keys(tmp_path: Path) -> None:
    module = _load_module()
    base = tmp_path / "base.yaml"
    base.write_text("trace:\n  runtime_shadow: {}\n")

    config_path = module._write_mode_config(
        base_config=base,
        output_root=tmp_path / "out",
        mode="production_like_disable_shared_stream",
        repeat=0,
        max_samples=1,
        max_tokens=2,
        start_sample=3,
    )

    data = yaml.safe_load(config_path.read_text())
    shadow = data["trace"]["runtime_shadow"]
    assert "env" not in shadow
    assert "unset_env" not in shadow
    assert shadow["enabled"] is True
    assert shadow["record_router_topk"] is False


def test_production_batch_write_mode_config_uses_no_recorder_batch_path(
    tmp_path: Path,
) -> None:
    module = _load_module()
    base = tmp_path / "base.yaml"
    base.write_text(
        "model: model.yaml\n"
        "output_dir: old\n"
        "trace:\n"
        "  use_router_logits_recorder: true\n"
        "  capture_router_topk: true\n"
        "  capture_router_scores: true\n"
        "  start_sample: 0\n"
        "  runtime_shadow:\n"
        "    enabled: true\n"
    )

    config_path = module._write_mode_config(
        base_config=base,
        output_root=tmp_path / "out",
        mode="production_batch",
        repeat=0,
        max_samples=32,
        max_tokens=64,
        start_sample=None,
    )

    data = yaml.safe_load(config_path.read_text())
    trace = data["trace"]
    shadow = trace["runtime_shadow"]
    overrides = trace["vllm_overrides"]

    assert trace["use_router_logits_recorder"] is False
    assert trace["capture_router_topk"] is False
    assert trace["capture_router_scores"] is False
    assert trace["allow_missing_router_trace"] is True
    assert shadow["enabled"] is False
    assert overrides["use_router_logits_recorder"] is False
    assert overrides["enable_return_routed_experts"] is False
    assert overrides["max_num_seqs"] == 32
    assert overrides["engine_chunk_size"] == 32
    assert overrides["enforce_eager"] is True


def test_shared_expert_light_is_moe_only_source_mode() -> None:
    module = _load_module()
    mode = module.MODES["shared_expert_light"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "shared"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_decoder_coarse_light_uses_only_coarse_decoder_and_shared_moe_timing() -> None:
    module = _load_module()
    mode = module.MODES["decoder_coarse_light"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "qwen3_5"
    assert mode["decoder_component_logging_mode"] == "rows"
    assert mode["moe_source_timing_mode"] == "shared"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["emit_descriptor_order_summaries"] is False
    assert mode["emit_transition_summaries"] is False
    assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_decoder_component_light_avoids_decoder_source_copy_timing() -> None:
    module = _load_module()
    mode = module.MODES["decoder_component_light"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["decoder_component_logging_mode"] == "rows"
    assert mode["moe_source_timing_mode"] == "shared"
    assert mode["moe_substage_logging_mode"] == "aggregate"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_decoder_component_sampled_light_samples_shared_moe_substages() -> None:
    module = _load_module()
    mode = module.MODES["decoder_component_sampled_light"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["decoder_component_logging_mode"] == "rows"
    assert mode["moe_source_timing_mode"] == "shared"
    assert mode["moe_substage_logging_mode"] == "sampled_aggregate"
    assert mode["moe_substage_sample_period"] == 8
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_decoder_shared_body_light_records_only_coarse_shared_body() -> None:
    module = _load_module()
    mode = module.MODES["decoder_shared_body_light"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["decoder_component_logging_mode"] == "rows"
    assert mode["moe_source_timing_mode"] == "shared_body"
    assert mode["moe_substage_logging_mode"] == "aggregate"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_shared_body_total_only_disables_decoder_component_timing() -> None:
    module = _load_module()
    mode = module.MODES["shared_body_total_only"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "shared_body"
    assert mode["moe_substage_logging_mode"] == "aggregate"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_decoder_shared_body_regions_light_records_few_body_regions() -> None:
    module = _load_module()
    mode = module.MODES["decoder_shared_body_regions_light"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["decoder_component_logging_mode"] == "rows"
    assert mode["moe_source_timing_mode"] == "shared_body_regions"
    assert mode["moe_substage_logging_mode"] == "aggregate"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_shared_body_regions_no_write_keeps_region_timing_without_rows() -> None:
    module = _load_module()
    mode = module.MODES["shared_body_regions_no_write"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "shared_body_regions"
    assert mode["moe_substage_logging_mode"] == "aggregate_no_write"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_shared_gate_ablation_is_diagnostic_only() -> None:
    module = _load_module()
    mode = module.MODES["shared_gate_ablation"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "shared"
    assert mode["shared_expert_output_gate_ablation"] == "unity"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_shared_gate_inplace_keeps_gate_enabled() -> None:
    module = _load_module()
    mode = module.MODES["shared_gate_inplace"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "shared"
    assert mode["shared_expert_output_gate_postprocess"] == "inplace"
    assert "shared_expert_output_gate_ablation" not in mode
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_shared_gate_fused_keeps_gate_semantics_enabled() -> None:
    module = _load_module()
    mode = module.MODES["shared_gate_fused"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "shared"
    assert mode["shared_expert_output_gate_postprocess"] == "fused_triton"
    assert "shared_expert_output_gate_ablation" not in mode
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_shared_gate_fused_minimal_disables_diagnostic_timing() -> None:
    module = _load_module()
    mode = module.MODES["shared_gate_fused_minimal"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["shared_expert_output_gate_postprocess"] == "fused_triton"
    assert "shared_expert_output_gate_ablation" not in mode
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_shared_gate_inplace_minimal_disables_diagnostic_timing() -> None:
    module = _load_module()
    mode = module.MODES["shared_gate_inplace_minimal"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["shared_expert_output_gate_postprocess"] == "inplace"
    assert "shared_expert_output_gate_ablation" not in mode
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_production_like_no_packed_recurrent_uses_env_only() -> None:
    module = _load_module()
    mode = module.MODES["production_like_no_packed_recurrent"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert mode["premap_address_capacity_gate_path"] is None
    assert mode["premap_consumer_require_readonly_gate"] is False
    assert mode["premap_consumer_readonly_gate_path"] is None
    assert mode["premap_descriptor_prep_execution_mode"] == "off"
    assert mode["premap_kernel_arg_handoff_live_enabled"] is False
    assert mode["env"] == {"VLLM_ENABLE_FLA_PACKED_RECURRENT_DECODE": "0"}


def test_production_like_disable_shared_stream_uses_env_only() -> None:
    module = _load_module()
    mode = module.MODES["production_like_disable_shared_stream"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is False
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is False
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["emit_descriptor_order_summaries"] is False
    assert mode["emit_transition_summaries"] is False
    assert mode["emit_premap_summaries"] is False
    assert mode["emit_premap_address_manager_counters"] is False
    assert mode["emit_premap_consumer_mapping"] is False
    assert mode["premap_address_capacity_gate_path"] is None
    assert mode["premap_consumer_require_readonly_gate"] is False
    assert mode["premap_consumer_readonly_gate_path"] is None
    assert mode["premap_descriptor_prep_execution_mode"] == "off"
    assert mode["premap_kernel_arg_handoff_live_enabled"] is False
    assert mode["env"] == {"VLLM_DISABLE_SHARED_EXPERTS_STREAM": "1"}
    assert "unset_env" not in mode


def test_engine_light_enables_only_engine_timing() -> None:
    module = _load_module()
    mode = module.MODES["engine_light"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is False
    assert mode["emit_moe_substage_timing"] is False
    assert mode["emit_engine_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["moe_source_timing_mode"] == "off"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"


def test_diagnostic_coarse_breakdown_combines_only_low_intrusion_totals() -> None:
    module = _load_module()
    mode = module.MODES["diagnostic_coarse_breakdown"]

    assert mode["record_router_topk"] is False
    assert mode["emit_decoder_layer_timing"] is True
    assert mode["emit_decoder_component_timing"] is True
    assert mode["emit_moe_substage_timing"] is True
    assert mode["emit_engine_timing"] is True
    assert mode["decoder_source_timing_mode"] == "off"
    assert mode["decoder_component_logging_mode"] == "rows"
    assert mode["moe_source_timing_mode"] == "shared_body"
    assert mode["moe_substage_logging_mode"] == "aggregate"
    assert mode["emit_wna16_kernel_timing"] is False
    assert mode["emit_summaries"] is True
    assert mode["emit_outcomes"] is False
    assert mode["outcome_logging_mode"] == "off"
    assert mode["emit_descriptor_order_summaries"] is False
    assert mode["emit_transition_summaries"] is False
    assert mode["unset_env"] == ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"]


def test_independent_heldout128_gen64_base_config_is_production_like() -> None:
    root = Path(__file__).resolve().parents[1]
    config_path = (
        root
        / "configs"
        / "trace"
        / "router_mtp_trace_aya_dataset_awq_vllm_gpu1_decode_independent_heldout128_gen64_base.yaml"
    )
    data = yaml.safe_load(config_path.read_text())
    trace = data["trace"]
    shadow = trace["runtime_shadow"]

    assert trace["split_id"] == "aya_dataset_512_indices_384_511_independent_heldout128_gen64"
    assert trace["split_source"] == "data/traces/aya_dataset_512_autoround/manifest.jsonl"
    assert trace["expected_sample_start"] == 384
    assert trace["expected_sample_end"] == 511
    assert trace["start_sample"] == 384
    assert trace["max_samples"] == 128
    assert trace["max_tokens"] == 64
    assert shadow["record_router_topk"] is False
    assert shadow["emit_decoder_layer_timing"] is False
    assert shadow["emit_decoder_component_timing"] is False
    assert shadow["emit_moe_substage_timing"] is False
    assert shadow["emit_engine_timing"] is False
    assert shadow["emit_wna16_kernel_timing"] is False
    assert shadow["decoder_source_timing_mode"] == "off"
    assert shadow["moe_source_timing_mode"] == "off"
    assert shadow["outcome_logging_mode"] == "off"


def test_independent_heldout_base_config_split_survives_ladder_write(tmp_path: Path) -> None:
    module = _load_module()
    root = Path(__file__).resolve().parents[1]
    base_config = (
        root
        / "configs"
        / "trace"
        / "router_mtp_trace_aya_dataset_awq_vllm_gpu1_decode_independent_heldout128_gen64_base.yaml"
    )

    generated = module._write_mode_config(
        base_config=base_config,
        output_root=tmp_path / "ladder",
        mode="production_like",
        repeat=0,
        max_samples=None,
        max_tokens=None,
        start_sample=None,
    )

    data = yaml.safe_load(generated.read_text())
    trace = data["trace"]
    shadow = trace["runtime_shadow"]
    assert trace["split_id"] == "aya_dataset_512_indices_384_511_independent_heldout128_gen64"
    assert trace["expected_sample_start"] == 384
    assert trace["expected_sample_end"] == 511
    assert trace["start_sample"] == 384
    assert trace["max_samples"] == 128
    assert trace["max_tokens"] == 64
    assert shadow["record_router_topk"] is False
    assert shadow["emit_decoder_layer_timing"] is False
    assert shadow["emit_decoder_component_timing"] is False
    assert shadow["emit_moe_substage_timing"] is False
    assert shadow["outcome_logging_mode"] == "off"


def test_write_mode_config_rejects_split_metadata_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    base = tmp_path / "base.yaml"
    base.write_text(
        "\n".join(
            [
                "trace:",
                "  start_sample: 384",
                "  max_samples: 128",
                "  max_tokens: 64",
                "  expected_sample_start: 384",
                "  expected_sample_end: 511",
                "  runtime_shadow: {}",
            ]
        )
        + "\n"
    )

    try:
        module._write_mode_config(
            base_config=base,
            output_root=tmp_path / "out",
            mode="production_like",
            repeat=0,
            max_samples=1,
            max_tokens=None,
            start_sample=None,
        )
    except ValueError as exc:
        assert "split metadata mismatch" in str(exc)
    else:
        raise AssertionError("expected split metadata mismatch")


def test_split_source_compare_accepts_equivalent_relative_paths() -> None:
    module = _load_module()
    trace = {
        "start_sample": 384,
        "max_samples": 128,
        "max_tokens": 64,
        "expected_sample_start": 384,
        "expected_sample_end": 511,
        "split_source": "./data/traces/aya_dataset_512_autoround/manifest.jsonl",
        "token_source_manifest": "data/traces/aya_dataset_512_autoround/manifest.jsonl",
    }
    split = module._resolve_trace_split(
        trace=trace,
        base_config=Path("base.yaml"),
        max_samples=None,
        max_tokens=None,
        start_sample=None,
    )

    report = module._validate_trace_split_metadata(
        trace=trace,
        split=split,
        base_config=Path("base.yaml"),
    )
    assert report["expected_range_checked"] is True
    assert report["split_source_match_checked"] is True
    assert report["split_source_resolved_match"] == str(
        (Path.cwd() / "data/traces/aya_dataset_512_autoround/manifest.jsonl").resolve(
            strict=False
        )
    )


def test_split_source_compare_accepts_base_config_relative_paths(tmp_path: Path) -> None:
    module = _load_module()
    config_dir = tmp_path / "configs" / "trace"
    config_dir.mkdir(parents=True)
    base_config = config_dir / "base.yaml"
    base_config.write_text("trace: {}\n")
    manifest = config_dir / "manifests" / "heldout.jsonl"
    manifest.parent.mkdir()
    trace = {
        "start_sample": 384,
        "max_samples": 128,
        "max_tokens": 64,
        "expected_sample_start": 384,
        "expected_sample_end": 511,
        "split_source": "manifests/heldout.jsonl",
        "token_source_manifest": str(manifest),
    }
    split = module._resolve_trace_split(
        trace=trace,
        base_config=base_config,
        max_samples=None,
        max_tokens=None,
        start_sample=None,
    )

    report = module._validate_trace_split_metadata(
        trace=trace,
        split=split,
        base_config=base_config,
    )
    assert report["split_source_match_checked"] is True
    assert report["split_source_resolved_match"] == str(manifest.resolve(strict=False))


def test_trace_split_summary_uses_effective_base_values(tmp_path: Path) -> None:
    module = _load_module()
    base = tmp_path / "base.yaml"
    base.write_text(
        "\n".join(
            [
                "trace:",
                "  start_sample: 384",
                "  max_samples: 128",
                "  max_tokens: 64",
                "  runtime_shadow: {}",
            ]
        )
        + "\n"
    )
    trace = yaml.safe_load(base.read_text())["trace"]

    split = module._resolve_trace_split(
        trace=trace,
        base_config=base,
        max_samples=None,
        max_tokens=None,
        start_sample=None,
    )

    assert split == {"max_samples": 128, "max_tokens": 64, "start_sample": 384}


def test_non_decoder_source_ladder_modes_reset_decoder_source_timing() -> None:
    module = _load_module()

    for name, mode in module.MODES.items():
        if name in {
            "decoder_source",
            "decoder_coarse_light",
            "attention_source",
            "attention_core_light",
            "attention_core_deep",
            "attention_core_handoff_light",
            "attention_core_handoff_aggregate",
            "attention_core_handoff_aggregate_no_write",
            "attention_core_handoff_counter_only",
            "attention_core_handoff_counter_only_no_write",
        }:
            continue
        assert mode.get("decoder_source_timing_mode") == "off", name
