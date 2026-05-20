from __future__ import annotations

import pytest

from scripts.map_prefetch_amdahl import (
    _extract_shares,
    _normalize_stall_reduction,
    build_rows,
)


def test_extract_shares_prefers_low_intrusion_coarse() -> None:
    bottleneck = {
        "diagnostic_light_shares_pct": {
            "moe_apply": 10.0,
            "mlp_moe": 20.0,
        },
        "low_intrusion_coarse": {
            "attention_total_only": {
                "moe_apply_share_pct": 28.4,
                "mlp_moe_share_pct": 49.1,
            }
        },
    }

    assert _extract_shares(
        bottleneck,
        moe_apply_share_pct=None,
        mlp_moe_share_pct=None,
    ) == {
        "moe_apply": 28.4,
        "mlp_moe": 49.1,
    }


def test_build_rows_maps_local_reduction_to_amdahl_upper_bound() -> None:
    rows = build_rows(
        [
            {
                "report": "r.json",
                "policy": "p",
                "stall_reduction": 0.10,
                "delta_issued_tb": 1.0,
                "used_per_extra_byte": 0.2,
                "full_fetch_count": 3,
            }
        ],
        {"moe_apply": 30.0, "mlp_moe": 50.0},
    )

    row = rows[0]
    assert row["moe_apply_endpoint_saved_share_pct"] == pytest.approx(3.0)
    assert row["mlp_moe_endpoint_saved_share_pct"] == pytest.approx(5.0)
    assert row["moe_apply_endpoint_speedup_upper_pct"] == pytest.approx(
        (1 / 0.97 - 1) * 100
    )
    assert row["mlp_moe_endpoint_speedup_upper_pct"] == pytest.approx(
        (1 / 0.95 - 1) * 100
    )


def test_stall_reduction_percent_input_is_normalized() -> None:
    local, unit = _normalize_stall_reduction(7.2)

    assert local == pytest.approx(0.072)
    assert unit == "percent"


def test_ambiguous_above_one_stall_reduction_is_percent() -> None:
    local, unit = _normalize_stall_reduction(1.2)

    assert local == pytest.approx(0.012)
    assert unit == "percent"


def test_stall_reduction_rejects_unreasonable_units() -> None:
    with pytest.raises(ValueError, match="Unreasonable stall_reduction"):
        _normalize_stall_reduction(250.0)
