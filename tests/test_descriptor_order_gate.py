from __future__ import annotations

import torch
from pathlib import Path

from mtp_expert_prefetch.runtime import (
    DescriptorOrderRuntimeGate,
    TileRequest,
    build_layer_tile_prior,
    build_noop_descriptor_order_assertion,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_CONFIG = REPO_ROOT / "configs/runtime/descriptor_order_two_level_gate.yaml"
PRIOR_PATH = REPO_ROOT / "outputs/reports/tile_order_cache/layer_prior_frequency_384calib.json"


def test_descriptor_order_runtime_gate_loads_config_and_decides() -> None:
    gate = DescriptorOrderRuntimeGate.from_config(GATE_CONFIG)

    allowed = gate.decide(
        tile_elems=1024,
        groups_per_cta=8,
        device=0,
        group_count=17,
        avg_group_size=2.0,
        p95_group_size=4.0,
        max_group_size=8,
        same_multiset=True,
        checksum_delta=0.0,
    )
    diagnostic = gate.decide(tile_elems=1024, groups_per_cta=16, device=0)
    disabled = gate.decide(tile_elems=1024, groups_per_cta=64, device=0)
    unknown_tile = gate.decide(tile_elems=4096, groups_per_cta=8, device=0)
    unknown_group = gate.decide(tile_elems=1024, groups_per_cta=12, device=0)
    missing_device = gate.decide(tile_elems=1024, groups_per_cta=8)
    unknown_device = gate.decide(tile_elems=1024, groups_per_cta=8, device=7)
    missing_multiset = gate.decide(tile_elems=1024, groups_per_cta=8, device=0)
    multiset_mismatch = gate.decide(
        tile_elems=1024,
        groups_per_cta=8,
        device=0,
        same_multiset=False,
    )
    checksum_mismatch = gate.decide(
        tile_elems=1024,
        groups_per_cta=8,
        device=0,
        same_multiset=True,
        checksum_delta=1.0,
    )
    missing_checksum = gate.decide(
        tile_elems=1024,
        groups_per_cta=8,
        device=0,
        same_multiset=True,
    )
    envelope_first = gate.decide(
        tile_elems=1024,
        groups_per_cta=12,
        device=0,
        same_multiset=False,
        checksum_delta=1.0,
    )
    mode_first = gate.decide(
        tile_elems=1024,
        groups_per_cta=12,
        device=0,
        execution_mode="materialized_reorder",
        same_multiset=False,
        checksum_delta=1.0,
    )

    assert gate.execution_mode == "two_level_group_plan"
    assert gate.prior_id == "layer_prior_frequency_384calib"
    assert gate.prior_path == PRIOR_PATH
    assert allowed.allow is True
    assert allowed.reason == "allowed"
    assert allowed.cta_count == 3
    assert diagnostic.allow is False
    assert diagnostic.reason == "groups_per_cta_diagnostic_only"
    assert disabled.allow is False
    assert disabled.reason == "groups_per_cta_disabled"
    assert unknown_tile.allow is False
    assert unknown_tile.reason == "tile_elems_unmeasured"
    assert unknown_group.allow is False
    assert unknown_group.reason == "groups_per_cta_unmeasured"
    assert missing_device.allow is False
    assert missing_device.reason == "device_missing"
    assert unknown_device.allow is False
    assert unknown_device.reason == "device_unmeasured"
    assert missing_multiset.allow is False
    assert missing_multiset.reason == "same_multiset_missing"
    assert multiset_mismatch.allow is False
    assert multiset_mismatch.reason == "same_multiset_false"
    assert checksum_mismatch.allow is False
    assert checksum_mismatch.reason == "checksum_mismatch"
    assert missing_checksum.allow is False
    assert missing_checksum.reason == "checksum_delta_missing"
    assert envelope_first.allow is False
    assert envelope_first.reason == "groups_per_cta_unmeasured"
    assert mode_first.allow is False
    assert mode_first.reason == "execution_mode_mismatch"


def test_descriptor_order_runtime_gate_base_dir_override(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "gate.yaml"
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    config_path.write_text(
        """
schema_version: 1
policy: layer_prior_frequency
execution_mode: two_level_group_plan
contract:
  prior_id: prior-test
  prior_path: priors/prior.json
initial_runtime_gate:
  tile_elems: [1024]
  groups_per_cta: [8]
  devices: [0]
disable:
  groups_per_cta_min: 64
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    gate = DescriptorOrderRuntimeGate.from_config(config_path, base_dir=Path("base"))

    assert gate.prior_path == base_dir / "priors/prior.json"
    assert gate.source_path == config_path.resolve()


def test_noop_descriptor_order_assertion_preserves_router_tensors_and_gates() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    gate = DescriptorOrderRuntimeGate.from_config(GATE_CONFIG)
    topk_ids = torch.tensor([[1, 2], [2, 3]], dtype=torch.long)
    topk_weights = torch.tensor([[0.4, 0.6], [0.7, 0.3]], dtype=torch.float32)
    before_ids = topk_ids.clone()
    before_weights = topk_weights.clone()

    report, decision = build_noop_descriptor_order_assertion(
        layer_id=0,
        topk_ids=topk_ids,
        topk_weights=topk_weights,
        prior=prior,
        gate=gate,
        tile_elems=1024,
        groups_per_cta=8,
        device=1,
        token_window_size=1,
        same_multiset_evidence=True,
        checksum_delta_evidence=0.0,
    )

    assert torch.equal(topk_ids, before_ids)
    assert torch.equal(topk_weights, before_weights)
    assert report is not None
    assert report.policy == "layer_prior_frequency"
    assert report.descriptor_count == 4
    assert report.metrics["metrics_mode"] == "count_only"
    assert report.metrics["group_plan"]["group_count"] == 4
    assert decision.allow is True
    assert decision.reason == "allowed"
    assert decision.group_count == 4
    assert decision.cta_count == 1


def test_noop_descriptor_order_assertion_requires_explicit_correctness_evidence() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    gate = DescriptorOrderRuntimeGate.from_config(GATE_CONFIG)
    topk_ids = torch.tensor([[1, 2], [2, 3]], dtype=torch.long)
    topk_weights = torch.tensor([[0.4, 0.6], [0.7, 0.3]], dtype=torch.float32)

    report, decision = build_noop_descriptor_order_assertion(
        layer_id=0,
        topk_ids=topk_ids,
        topk_weights=topk_weights,
        prior=prior,
        gate=gate,
        tile_elems=1024,
        groups_per_cta=8,
        device=1,
        token_window_size=1,
    )

    assert report is not None
    assert report.metrics["metrics_mode"] == "count_only"
    assert report.tile_multiset_hash is None
    assert report.order_hash is None
    assert decision.allow is False
    assert decision.reason == "same_multiset_missing"
