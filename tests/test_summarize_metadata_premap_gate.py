from __future__ import annotations

import json

from scripts.summarize_metadata_premap_gate import collect_rows, summarize


def test_metadata_premap_summary_filters_and_counts_positive_rows(tmp_path):
    path = tmp_path / "gate.json"
    path.write_text(
        json.dumps(
            [
                {
                    "report": "normal.json",
                    "policy": "transition_ready",
                    "metadata_count": 0,
                    "premap_count": 0,
                },
                {
                    "report": "normal.json",
                    "policy": "transition_top32_plus_gated_utility_keep_top_0.500",
                    "full_fetch_count": 3,
                    "metadata_count": 7,
                    "premap_count": 5,
                    "metadata_later_used_rate": 0.1,
                    "premap_later_used_rate": 0.2,
                    "metadata_net_setup_ms": -1.0,
                    "premap_net_setup_ms": 2.0,
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = collect_rows([("demo", path)])
    payload = summarize(rows)

    assert len(rows) == 1
    assert rows[0]["source"] == "demo"
    assert rows[0]["metadata_positive"] is False
    assert rows[0]["premap_positive"] is True
    assert payload["metadata_positive_count"] == 0
    assert payload["premap_positive_count"] == 1
