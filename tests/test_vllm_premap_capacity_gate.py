from pathlib import Path

import pytest
import yaml

from mtp_expert_prefetch.tracing.vllm_router_trace import (
    _apply_premap_address_capacity_gate,
    _apply_premap_consumer_readonly_gate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_gate(path, *, capacity=12288):
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "artifact_id: test_premap_capacity_gate",
                "capacity_gate:",
                f"  recommended_capacity_entries: {capacity}",
                "evidence_paths:",
                "  capacity_sensitivity_json: outputs/test.json",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_readonly_gate(path, *, passed=True, payload_bytes=0):
    status = "passed" if passed else "failed"
    gate_passed = "true" if passed else "false"
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "artifact_id: test_premap_consumer_readonly_gate",
                f"status: {status}",
                "contract:",
                f"  payload_bytes_required: {payload_bytes}",
                "  ready_credit_required: false",
                "  changes_router_required: false",
                "  changes_descriptor_order_required: false",
                "  address_key_scope: layer_expert",
                "  descriptor_bytes: 4096",
                "  handle_resolution: read_only",
                "gate:",
                f"  passed: {gate_passed}",
                "  failures: []",
                "  metrics:",
                "    premap_consumer_mapping_count: 2",
                "evidence_paths:",
                "  longrun_summary: outputs/longrun.json",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_apply_premap_address_capacity_gate_sets_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    _write_gate(gate, capacity=12288)

    options = _apply_premap_address_capacity_gate(
        {
            "enabled": True,
            "premap_address_capacity_gate_path": str(gate),
        },
        project_root=tmp_path,
    )

    assert options["premap_address_manager_capacity"] == 12288
    assert options["premap_address_capacity_gate_id"] == "test_premap_capacity_gate"
    assert options["premap_address_capacity_gate_resolved_path"] == str(gate)
    assert options["premap_address_capacity_gate_recommended_capacity"] == 12288
    assert options["premap_address_capacity_gate_evidence_paths"] == {
        "capacity_sensitivity_json": "outputs/test.json"
    }


def test_apply_premap_consumer_readonly_gate_sets_precondition_metadata(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_required"] is True
    assert (
        options["premap_consumer_readonly_gate_id"]
        == "test_premap_consumer_readonly_gate"
    )
    assert options["premap_consumer_readonly_gate_resolved_path"] == str(gate)
    assert options["premap_consumer_readonly_gate_passed"] is True
    assert options["premap_consumer_readonly_gate_failures"] == []
    assert options["premap_consumer_readonly_gate_metrics"] == {
        "premap_consumer_mapping_count": 2
    }
    assert options["premap_consumer_readonly_gate_evidence_paths"] == {
        "longrun_summary": "outputs/longrun.json"
    }


def test_apply_premap_consumer_readonly_gate_rejects_missing_required_path(tmp_path):
    with pytest.raises(ValueError, match="requires premap_consumer_readonly_gate_path"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_require_readonly_gate": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_failed_gate(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate, passed=False)

    with pytest.raises(ValueError, match="did not pass"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_non_bool_passed(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)
    text = gate.read_text(encoding="utf-8")
    gate.write_text(text.replace("  passed: true", "  passed: 'false'"), encoding="utf-8")

    with pytest.raises(TypeError, match="gate.passed"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_readonly_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_payload_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate, payload_bytes=4096)

    with pytest.raises(ValueError, match="violates the no-op contract"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_readonly_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_non_noop_runtime_mode(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)

    with pytest.raises(ValueError, match="mapping_mode=noop_assertion"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "apply",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_descriptor_size_mismatch(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)

    with pytest.raises(ValueError, match="descriptor size"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_descriptor_bytes": 8192,
            },
            project_root=tmp_path,
        )


def test_apply_premap_address_capacity_gate_accepts_matching_inline_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    _write_gate(gate, capacity=8192)

    options = _apply_premap_address_capacity_gate(
        {
            "enabled": True,
            "premap_address_capacity_gate_path": str(gate),
            "premap_address_manager_capacity": 8192,
        },
        project_root=tmp_path,
    )

    assert options["premap_address_manager_capacity"] == 8192


def test_apply_premap_address_capacity_gate_rejects_mismatched_inline_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    _write_gate(gate, capacity=12288)

    with pytest.raises(ValueError, match="does not match"):
        _apply_premap_address_capacity_gate(
            {
                "enabled": True,
                "premap_address_capacity_gate_path": str(gate),
                "premap_address_manager_capacity": 8192,
            },
            project_root=tmp_path,
        )


def test_apply_premap_address_capacity_gate_rejects_missing_capacity_gate(tmp_path):
    gate = tmp_path / "gate.yaml"
    gate.write_text("schema_version: 1\nartifact_id: bad_gate\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing `capacity_gate`"):
        _apply_premap_address_capacity_gate(
            {
                "enabled": True,
                "premap_address_capacity_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_address_capacity_gate_rejects_missing_recommended_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    gate.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "artifact_id: bad_gate",
                "capacity_gate:",
                "  low_footprint_capacity_entries: 8192",
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="recommended_capacity_entries"):
        _apply_premap_address_capacity_gate(
            {
                "enabled": True,
                "premap_address_capacity_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_address_capacity_gate_rejects_non_numeric_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    gate.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "artifact_id: bad_gate",
                "capacity_gate:",
                "  recommended_capacity_entries: not-a-number",
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        _apply_premap_address_capacity_gate(
            {
                "enabled": True,
                "premap_address_capacity_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


@pytest.mark.parametrize(
    ("sample_count", "expected_end"),
    [
        (128, 127),
        (512, 511),
    ],
)
def test_default_longrun_audit_config_uses_premap_capacity_gate(
    sample_count, expected_end
):
    config_path = PROJECT_ROOT / (
        "configs/trace/"
        f"router_mtp_trace_external_prompt_gate_dolly_{sample_count}_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["data"] == f"configs/data/external_prompt_gate_dolly_{sample_count}.yaml"
    assert config["trace"]["max_samples"] == sample_count
    assert config["trace"]["expected_sample_end"] == expected_end
    shadow = config["trace"]["runtime_shadow"]

    assert shadow["writer_mode"] == "jsonl_batched"
    assert shadow["outcome_logging_mode"] == "off"
    assert shadow["record_router_topk"] is True
    assert shadow["emit_premap_summaries"] is True
    assert shadow["emit_premap_address_manager_counters"] is True
    assert shadow["premap_summary_sample_period"] == (
        32 if sample_count == 128 else 64
    )
    assert (
        shadow["premap_address_capacity_gate_path"]
        == "configs/runtime/premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml"
    )
    gate = yaml.safe_load(
        (
            PROJECT_ROOT / shadow["premap_address_capacity_gate_path"]
        ).read_text(encoding="utf-8")
    )
    evidence_paths = gate["evidence_paths"]
    assert (
        evidence_paths["premap_only_longrun_summary_md"]
        == "docs/premap_longrun_audit_summary.md"
    )
    assert "premap_only_longrun_512_json" in evidence_paths
    assert "premap_only_longrun_512_gate_json" in evidence_paths
    assert "premap_address_manager_capacity" not in shadow
    assert shadow["emit_premap_consumer_mapping"] is True
    assert shadow["premap_consumer_mapping_mode"] == "noop_assertion"
    assert shadow["premap_consumer_mapping_source"] == (
        "fused_moe_prepare_expert_assignment"
    )
    assert shadow["premap_consumer_resolve_real_handles"] is True
    assert shadow["premap_consumer_mapping_sample_period"] == (
        32 if sample_count == 128 else 64
    )
    assert shadow["premap_consumer_require_readonly_gate"] is True
    assert (
        shadow["premap_consumer_readonly_gate_path"]
        == "configs/runtime/premap_consumer_readonly_gate_dolly512_gen64_awq_w7900_gpu1.yaml"
    )
    readonly_gate = yaml.safe_load(
        (
            PROJECT_ROOT / shadow["premap_consumer_readonly_gate_path"]
        ).read_text(encoding="utf-8")
    )
    assert readonly_gate["status"] == "passed"
    assert readonly_gate["gate"]["passed"] is True
    assert readonly_gate["contract"]["payload_bytes_required"] == 0
    assert readonly_gate["contract"]["ready_credit_required"] is False
    assert readonly_gate["contract"]["changes_router_required"] is False
    assert readonly_gate["contract"]["changes_descriptor_order_required"] is False
    assert (
        readonly_gate["gate"]["metrics"][
            "premap_consumer_real_descriptor_handle_hit_rate"
        ]
        == 1.0
    )
    assert shadow["premap_policy"] == "premap_only_with_consumer_mapping_noop"
    assert shadow["premap_source"] == "current_router_topk_premap_shadow"
    assert shadow["premap_descriptor_bytes"] == 4096
    assert shadow["emit_outcomes"] is False
    assert shadow["emit_descriptor_order_summaries"] is False
    assert shadow["descriptor_order_metrics_mode"] == "count_only"
    assert shadow["descriptor_order_event_mode"] == "minimal"
    assert shadow["emit_decoder_layer_timing"] is False
    assert shadow["emit_decoder_component_timing"] is False
    assert shadow["emit_moe_substage_timing"] is False
    assert shadow["emit_engine_timing"] is False
    assert shadow["emit_wna16_kernel_timing"] is False
    assert shadow["decoder_source_timing_mode"] == "off"
    assert shadow["moe_source_timing_mode"] == "off"
