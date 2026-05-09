import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_descriptor_consumer_micro_runtime.py"
    )
    spec = importlib.util.spec_from_file_location("run_descriptor_consumer_micro_runtime", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_infer_num_tiles_uses_observed_tile_id_range():
    module = _load_module()
    requests = [SimpleNamespace(tile_id=0), SimpleNamespace(tile_id=7)]

    assert module._infer_num_tiles(requests) == 8


def test_summarize_net_saved_us_includes_build_and_export_costs():
    module = _load_module()
    rows = [
        {
            "device": 0,
            "tile_elems": 1024,
            "tiles_per_cta": 32,
            "cache_flush_elems": 0,
            "policy": "no_order",
            "us_per_tile": 1.0,
            "wall_ms_mean": 10.0,
            "checksum": 11.0,
            "tile_count": 100,
        },
        {
            "device": 0,
            "tile_elems": 1024,
            "tiles_per_cta": 32,
            "cache_flush_elems": 0,
            "policy": "layer_prior_frequency",
            "us_per_tile": 0.8,
            "wall_ms_mean": 8.0,
            "checksum": 11.0,
            "tile_count": 100,
        },
    ]
    summary = module._summarize(
        rows,
        policy_meta={
            "no_order": {
                "same_multiset_as_no_order": True,
                "order_build_us": {"median": 1.0},
                "order_export_us": 1.0,
            },
            "layer_prior_frequency": {
                "same_multiset_as_no_order": True,
                "order_build_us": {"median": 3.0},
                "order_export_us": 2.0,
            },
        },
        cpp_builder={
            "modes": {
                "layer_prior_plan": {"ok": True, "build_us_median": 5.0},
                "layer_prior_materialized": {"ok": True, "build_us_median": 8.0},
            }
        },
    )

    layer_row = next(
        row for row in summary["stability"] if row["policy"] == "layer_prior_frequency"
    )
    assert layer_row["consumer_saved_us_median_vs_no_order"] == pytest.approx(20.0)
    assert layer_row["net_saved_us_after_python_order_build"] == pytest.approx(15.0)
    assert layer_row["net_saved_us_after_cpp_plan_build"] == pytest.approx(15.0)
    assert layer_row["net_saved_us_after_cpp_materialized_build"] == pytest.approx(12.0)


def test_summarize_skips_net_when_multiset_mismatch():
    module = _load_module()
    rows = [
        {
            "device": 0,
            "tile_elems": 1024,
            "tiles_per_cta": 32,
            "cache_flush_elems": 0,
            "policy": "no_order",
            "us_per_tile": 1.0,
            "wall_ms_mean": 10.0,
            "checksum": 11.0,
            "tile_count": 100,
        },
        {
            "device": 0,
            "tile_elems": 1024,
            "tiles_per_cta": 32,
            "cache_flush_elems": 0,
            "policy": "layer_prior_frequency",
            "us_per_tile": 0.8,
            "wall_ms_mean": 8.0,
            "checksum": 12.0,
            "tile_count": 100,
        },
    ]

    summary = module._summarize(
        rows,
        policy_meta={
            "no_order": {"same_multiset_as_no_order": True},
            "layer_prior_frequency": {"same_multiset_as_no_order": False},
        },
        cpp_builder={
            "modes": {
                "layer_prior_plan": {"ok": True, "build_us_median": 5.0},
                "layer_prior_materialized": {"ok": True, "build_us_median": 8.0},
            }
        },
    )

    layer_row = next(
        row for row in summary["stability"] if row["policy"] == "layer_prior_frequency"
    )
    assert layer_row["consumer_saved_us_median_vs_no_order"] is None
    assert layer_row["net_saved_us_after_python_order_build"] is None
    assert layer_row["net_saved_us_after_cpp_plan_build"] is None


def test_execution_mvp_selects_two_level_when_gate_allows():
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
    summary = {
        "stability": [
            {
                "device": 0,
                "tile_elems": 1024,
                "tiles_per_cta": 8,
                "cache_flush_elems": 0,
                "policy": "no_order",
                "us_per_tile": {"median": 1.0},
                "checksum_delta_abs_vs_no_order": 0.0,
            },
            {
                "device": 0,
                "tile_elems": 1024,
                "tiles_per_cta": 8,
                "cache_flush_elems": 0,
                "policy": "layer_prior_frequency_two_level",
                "us_per_tile": {"median": 0.8},
                "checksum_delta_abs_vs_no_order": 0.0,
            },
        ]
    }

    report = module._execution_mvp_report(
        summary,
        gate=gate,
        execution_policy="layer_prior_frequency_two_level",
    )

    assert report["allow_count"] == 1
    assert report["fallback_count"] == 0
    assert report["decisions"][0]["selected_policy"] == "layer_prior_frequency_two_level"
    assert report["decisions"][0]["gate_reason"] == "allowed"
    assert report["decisions"][0]["execution_reason"] == "allowed"
    assert report["decisions"][0]["speedup_median_vs_no_order"] == pytest.approx(1.25)


def test_execution_mvp_falls_back_on_checksum_mismatch():
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
    summary = {
        "stability": [
            {
                "device": 0,
                "tile_elems": 1024,
                "tiles_per_cta": 8,
                "cache_flush_elems": 0,
                "policy": "no_order",
                "us_per_tile": {"median": 1.0},
                "checksum_delta_abs_vs_no_order": 0.0,
            },
            {
                "device": 0,
                "tile_elems": 1024,
                "tiles_per_cta": 8,
                "cache_flush_elems": 0,
                "policy": "layer_prior_frequency_two_level",
                "us_per_tile": {"median": 0.8},
                "checksum_delta_abs_vs_no_order": 1.0,
            },
        ]
    }

    report = module._execution_mvp_report(
        summary,
        gate=gate,
        execution_policy="layer_prior_frequency_two_level",
    )

    assert report["allow_count"] == 0
    assert report["fallback_count"] == 1
    assert report["decisions"][0]["selected_policy"] == "no_order"
    assert report["decisions"][0]["gate_reason"] == "same_multiset_false"
    assert report["decisions"][0]["execution_reason"] == "same_multiset_false"


def test_execution_mvp_falls_back_when_candidate_not_profitable():
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
    summary = {
        "stability": [
            {
                "device": 0,
                "tile_elems": 1024,
                "tiles_per_cta": 8,
                "cache_flush_elems": 0,
                "policy": "no_order",
                "us_per_tile": {"median": 1.0},
                "checksum_delta_abs_vs_no_order": 0.0,
            },
            {
                "device": 0,
                "tile_elems": 1024,
                "tiles_per_cta": 8,
                "cache_flush_elems": 0,
                "policy": "layer_prior_frequency_two_level",
                "us_per_tile": {"median": 1.2},
                "checksum_delta_abs_vs_no_order": 0.0,
            },
        ]
    }

    report = module._execution_mvp_report(
        summary,
        gate=gate,
        execution_policy="layer_prior_frequency_two_level",
    )

    assert report["allow_count"] == 0
    assert report["fallback_count"] == 1
    assert report["decisions"][0]["gate_reason"] == "allowed"
    assert report["decisions"][0]["execution_reason"] == "not_profitable"
    assert report["decisions"][0]["selected_policy"] == "no_order"


def test_execution_mvp_falls_back_on_unsupported_envelope():
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
    summary = {
        "stability": [
            {
                "device": 1,
                "tile_elems": 1024,
                "tiles_per_cta": 12,
                "cache_flush_elems": 0,
                "policy": "no_order",
                "us_per_tile": {"median": 1.0},
                "checksum_delta_abs_vs_no_order": 0.0,
            },
            {
                "device": 1,
                "tile_elems": 1024,
                "tiles_per_cta": 12,
                "cache_flush_elems": 0,
                "policy": "layer_prior_frequency_two_level",
                "us_per_tile": {"median": 0.5},
                "checksum_delta_abs_vs_no_order": 0.0,
            },
        ]
    }

    report = module._execution_mvp_report(
        summary,
        gate=gate,
        execution_policy="layer_prior_frequency_two_level",
    )

    assert report["allow_count"] == 0
    assert report["fallback_count"] == 1
    assert report["decisions"][0]["selected_policy"] == "no_order"
    assert report["decisions"][0]["gate_reason"] == "groups_per_cta_unmeasured"


def test_execution_mvp_falls_back_on_unmeasured_device_when_group_supported():
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
    summary = {
        "stability": [
            {
                "device": 1,
                "tile_elems": 1024,
                "tiles_per_cta": 8,
                "cache_flush_elems": 0,
                "policy": "no_order",
                "us_per_tile": {"median": 1.0},
                "checksum_delta_abs_vs_no_order": 0.0,
            },
            {
                "device": 1,
                "tile_elems": 1024,
                "tiles_per_cta": 8,
                "cache_flush_elems": 0,
                "policy": "layer_prior_frequency_two_level",
                "us_per_tile": {"median": 0.5},
                "checksum_delta_abs_vs_no_order": 0.0,
            },
        ]
    }

    report = module._execution_mvp_report(
        summary,
        gate=gate,
        execution_policy="layer_prior_frequency_two_level",
    )

    assert report["allow_count"] == 0
    assert report["fallback_count"] == 1
    assert report["decisions"][0]["selected_policy"] == "no_order"
    assert report["decisions"][0]["gate_reason"] == "device_unmeasured"
