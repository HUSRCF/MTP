from __future__ import annotations

import json
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_descriptor_order_group_plan_consistency.py"
SPEC = importlib.util.spec_from_file_location("check_descriptor_order_group_plan_consistency", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_group_plan_consistency_script_reports_missing_fields_and_gate(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    shadow = tmp_path / "runtime_shadow.jsonl"
    shadow.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "descriptor_summary_min",
                        "descriptor_order_execution_mode": "two_level_group_plan",
                        "descriptor_group_plan_groups_per_cta": 8,
                        "descriptor_group_plan_group_count": 3,
                        "descriptor_group_plan_avg_group_size": 2.0,
                        "descriptor_group_plan_p95_group_size": 4.0,
                        "descriptor_group_plan_max_group_size": 5,
                        "descriptor_group_plan_cta_count": 1,
                        "descriptor_tile_request_count": 6,
                        "descriptor_unique_b_tiles": 3,
                        "descriptor_window_count": 1,
                    }
                ),
                json.dumps({"event_type": "outcome_aggregate", "outcome_count": 2}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "tile_elems": 1024,
                        "groups_per_cta": 8,
                        "allow_two_level_descriptor_order": True,
                    },
                    {
                        "tile_elems": 2048,
                        "groups_per_cta": 64,
                        "allow_two_level_descriptor_order": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "check_descriptor_order_group_plan_consistency.py",
            "--runtime-shadow-jsonl",
            str(shadow),
            "--gate-json",
            str(gate),
            "--tile-elems",
            "1024",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
    )

    MODULE.main()
    capsys.readouterr()
    report = json.loads(output_json.read_text(encoding="utf-8"))

    assert report["descriptor_event_count"] == 1
    assert report["missing_required_field_total"] == 0
    assert report["groups_per_cta_counts"] == {"8": 1}
    assert report["field_stats"]["descriptor_group_plan_group_count"]["mean"] == 3.0
    assert report["gate_summary"]["row_count"] == 1
    assert report["gate_summary"]["allowed_count"] == 1
