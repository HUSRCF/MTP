from __future__ import annotations

import json

from scripts.summarize_prefetch_event_ready_sweeps import summarize


def test_summarize_separates_any_positive_from_extra_issued(tmp_path):
    path = tmp_path / "sweep.json"
    path.write_text(
        json.dumps(
            {
                "copy_scale": 1.0,
                "base_config": {"queue_event_interval_us": 50.0},
                "max_inflight": [32, 33],
                "deadline_us": [0.0, 30000.0],
                "first_positive": {
                    "transition_top32_plus_utility_keep50": {
                        "max_inflight": 32,
                        "deadline_us": 30000.0,
                        "net_saved_ms_vs_transition": 1.0,
                        "extra_issued_vs_transition": 0,
                    }
                },
                "first_positive_mtp_extra_issued": {},
                "sweep_rows": [
                    {
                        "policy": "transition_top32_plus_utility_keep50",
                        "max_inflight": 33,
                        "deadline_us": 30000.0,
                        "net_saved_ms_vs_transition": -2.0,
                        "extra_issued_vs_transition": 10,
                        "late_miss_count": 3,
                        "late_completion_unused_count": 2,
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = summarize([("baseline", path)])

    assert payload["positive_any_count"] == 1
    assert payload["positive_mtp_extra_issued_count"] == 0
    row = payload["rows"][0]
    assert row["has_positive_any"] is True
    assert row["has_positive_mtp_extra_issued"] is False
    assert row["best_extra_issued"]["extra_issued_vs_transition"] == 10
    assert row["best_extra_issued"]["net_saved_ms_vs_transition"] == -2.0
