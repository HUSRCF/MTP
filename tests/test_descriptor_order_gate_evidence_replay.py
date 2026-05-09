import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "replay_descriptor_order_gate_evidence.py"
    )
    spec = importlib.util.spec_from_file_location(
        "replay_descriptor_order_gate_evidence",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_descriptor_order_gate_evidence_replay_allows_matching_cell(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.yaml"
    gate_path.write_text(
        """
schema_version: 1
policy: layer_prior_frequency
execution_mode: two_level_group_plan
contract:
  same_multiset_required: true
  checksum_delta_required: 0.0
initial_runtime_gate:
  tile_elems: [1024]
  groups_per_cta: [8]
  devices: [0]
disable:
  groups_per_cta_min: 64
  unmeasured_tile_elems: true
  unmeasured_devices: true
  checksum_mismatch: true
  same_multiset_false: true
""".strip()
        + "\n",
        encoding="utf-8",
    )
    consumer_report = tmp_path / "consumer.json"
    consumer_report.write_text(
        json.dumps(
            {
                "summary": {
                    "stability": [
                        {
                            "policy": "layer_prior_frequency_two_level",
                            "device": 0,
                            "tile_elems": 1024,
                            "tiles_per_cta": 8,
                            "cache_flush_elems": 0,
                            "checksum_delta_abs_vs_no_order": 0.0,
                            "speedup_median_vs_no_order": 1.2,
                        }
                    ]
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    rows = [
        {
            "event_type": "descriptor_summary_min",
            "shadow_event_id": "req:0:-1:0",
            "descriptor_order_execution_mode": "two_level_group_plan",
            "descriptor_group_plan_groups_per_cta": 8,
            "descriptor_group_plan_group_count": 17,
            "descriptor_group_plan_avg_group_size": 2.0,
            "descriptor_group_plan_p95_group_size": 4.0,
            "descriptor_group_plan_max_group_size": 5,
            "descriptor_order_gate_allow": False,
            "descriptor_order_gate_reason": "same_multiset_missing",
            "descriptor_order_gate_tile_elems": 1024,
            "descriptor_order_gate_device": 0,
        }
    ]
    shadow = tmp_path / "shadow.jsonl"
    shadow.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    gate = module.DescriptorOrderRuntimeGate.from_config(gate_path, base_dir=tmp_path)
    evidence = module._load_evidence(
        consumer_report,
        policy="layer_prior_frequency_two_level",
        cache_flush_elems=0,
        checksum_tolerance=0.0,
    )
    enriched, report = module._replay(
        module._read_jsonl(shadow),
        gate=gate,
        evidence=evidence,
        cache_flush_elems=0,
    )

    assert report["descriptor_event_count"] == 1
    assert report["evidence_found_count"] == 1
    assert report["original_gate_reason_counts"] == {"same_multiset_missing": 1}
    assert report["replay_gate_allow_counts"] == {"True": 1}
    assert report["replay_gate_reason_counts"] == {"allowed": 1}
    assert enriched[0]["descriptor_order_gate_replay_allow"] is True
    assert enriched[0]["descriptor_order_gate_replay_reason"] == "allowed"
    assert enriched[0]["descriptor_order_gate_replay_same_multiset"] is True
    assert enriched[0]["descriptor_order_gate_replay_checksum_delta"] == 0.0


def test_descriptor_order_gate_evidence_replay_keeps_missing_evidence_closed(tmp_path: Path):
    module = _load_module()
    gate = module.DescriptorOrderRuntimeGate(
        policy="layer_prior_frequency",
        execution_mode="two_level_group_plan",
        tile_elems=(1024,),
        groups_per_cta=(8,),
        devices=(0,),
        diagnostic_groups_per_cta=(),
        disable_groups_per_cta_min=64,
    )
    rows = [
        {
            "event_type": "descriptor_summary_min",
            "descriptor_order_execution_mode": "two_level_group_plan",
            "descriptor_group_plan_groups_per_cta": 8,
            "descriptor_order_gate_tile_elems": 1024,
            "descriptor_order_gate_device": 0,
        }
    ]

    enriched, report = module._replay(
        rows,
        gate=gate,
        evidence={},
        cache_flush_elems=0,
    )

    assert report["evidence_found_count"] == 0
    assert report["replay_gate_allow_counts"] == {"False": 1}
    assert report["replay_gate_reason_counts"] == {"same_multiset_missing": 1}
    assert enriched[0]["descriptor_order_gate_replay_allow"] is False
    assert enriched[0]["descriptor_order_gate_replay_reason"] == "same_multiset_missing"
