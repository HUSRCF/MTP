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
