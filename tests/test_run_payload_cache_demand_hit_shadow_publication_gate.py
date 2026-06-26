from __future__ import annotations

import json
from pathlib import Path

from scripts import run_payload_cache_demand_hit_shadow_publication_gate as gate


def test_payload_cache_demand_hit_shadow_publication_gate_report() -> None:
    report = gate.build_report()

    assert report["passed"] is True
    assert report["failures"] == []
    assert report["source"] == "payload_cache_demand_hit_shadow_publication_gate"
    assert report["artifact_kind"] == "payload_cache_demand_hit_shadow_publication_gate"
    assert report["payload_bytes"] == 0
    assert report["demand_hit_payload_bytes"] == 0
    assert report["passed_to_kernel"] is False
    assert report["changes_kernel_launch_args"] is False
    assert report["kernel_arg_pass_allowed"] is False
    assert report["consumer_visible_payload_hit"] is False
    assert report["payload_deref_attempted"] is False
    assert report["payload_handle_deref_attempted"] is False
    assert report["demand_hit_shadow_publication_allowed"] is True
    assert report["demand_hit_published_to_shadow"] is True
    assert report["ready_credit"] is False
    assert report["demand_count"] == 2
    assert report["demand_hit_count"] == 1
    assert report["demand_miss_count"] == 1
    assert report["demand_hit_rate"] == 0.5

    canary = report["canary"]
    assert canary["publication_scope"] == "shadow_only"
    assert canary["decision"] == "blocked"
    assert canary["block_reason"] == "shadow_only_not_consumer_visible_payload_hit"
    assert canary["payload_deref_attempted"] is False
    assert canary["payload_handle_deref_attempted"] is False
    assert canary["measures_tpot"] is False
    assert canary["measures_vllm_latency"] is False


def test_payload_cache_demand_hit_shadow_publication_gate_cli(tmp_path: Path) -> None:
    output = tmp_path / "shadow_gate.json"

    rc = gate.main(["--output-json", str(output)])

    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["failures"] == []
    assert payload["payload_bytes"] == 0
    assert payload["consumer_visible_payload_hit"] is False
    assert payload["payload_deref_attempted"] is False
    assert payload["payload_handle_deref_attempted"] is False
    assert payload["demand_hit_shadow_publication_allowed"] is True
