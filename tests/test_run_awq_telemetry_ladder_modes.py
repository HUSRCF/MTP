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
