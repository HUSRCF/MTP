from __future__ import annotations

from scripts.summarize_prefetch_cache_lab import extract_rows


def test_extract_rows_skips_existing_summary_payload(tmp_path):
    report = tmp_path / "summary.json"

    assert extract_rows(report, [{"already": "summarized"}]) == []


def test_extract_rows_converts_us_to_ms_and_keeps_gate_fields(tmp_path):
    report = tmp_path / "r.json"
    payload = {
        "metadata": {
            "campaign": "production_like_action_replay",
            "dataset": "aya",
            "split": "heldout512",
            "trace_source": "runtime_shadow",
            "run_tag": "normal",
            "max_token_examples": 512,
        },
        "config": {
            "transition_topk": 32,
            "cache_capacity": 4,
            "bandwidth_gbps": 6.0,
            "overlap_factor": 0.5,
            "manager_us_per_issue": 7.0,
            "lookup_us_per_demand": 0.25,
            "decision_us_per_token_layer": 0.5,
            "measured_copy_us_per_issue": 11.0,
            "measured_copy_stat": "p95",
            "measured_copy_effective_gbps": 3.3,
            "max_inflight_prefetches": 2,
            "queue_model": "event",
            "queue_batch_size": 4,
            "queue_coalesce_scope": "global",
            "queue_policy": "drop",
            "queue_admission_policy": "score",
            "queue_wait_us_per_overflow": 11.0,
            "queue_event_interval_us": 2.0,
            "queue_deadline_us": 3.0,
            "stress_fallback": False,
        },
        "demand_stream_hash": "demand-hash",
        "true_router_stream_hash": "router-hash",
        "policy_config_hash": "policy-hash",
        "stream_shapes": {
            "demand_stream_rows": 11,
            "true_router_stream_rows": 22,
        },
        "rows": [
            {
                "policy": "transition_top32_plus_utility_keep50",
                "demand_hit_rate": 0.75,
                "issued_fetch_count": 3,
                "used_per_issued_fetch": 0.5,
                "evicted_before_use_count": 1,
                "demand_stall_us": 2000.0,
                "prefetch_dma_us": 3000.0,
                "prefetch_queue_wait_us": 20.0,
                "prefetch_queue_model": "per_token_layer_burst_overflow",
                "prefetch_queue_backpressure_semantics": "burst semantics",
                "prefetch_queue_policy": "drop",
                "prefetch_queue_admission_policy": "score",
                "prefetch_queue_batch_size": 4,
                "prefetch_queue_coalesce_scope": "global",
                "prefetch_queue_batch_count": 2,
                "prefetch_queue_service_us": 3000.0,
                "prefetch_queue_total_span_us": 5000.0,
                "prefetch_queue_max_delay_us": 400.0,
                "prefetch_queue_event_interval_us": 2.0,
                "prefetch_queue_deadline_us": 3.0,
                "prefetch_ready_late_miss_count": 7,
                "prefetch_late_completion_unused_count": 5,
                "prefetch_backpressure_dropped_count": 1,
                "prefetch_queue_pressure": 0.25,
                "prefetch_queue_overflow_count": 2,
                "prefetch_max_issue_burst": 4,
                "total_cost_us": 4000.0,
                "net_saved_us_vs_transition": 500.0,
                "net_saved_us_vs_no_prefetch": 600.0,
                "stress_shutdown_count": 2,
            }
        ],
    }

    rows = extract_rows(report, payload)

    assert rows == [
        {
            "report": "r.json",
            "campaign": "production_like_action_replay",
            "dataset": "aya",
            "split": "heldout512",
            "trace_source": "runtime_shadow",
            "run_tag": "normal",
            "max_token_examples": 512,
            "policy": "transition_top32_plus_utility_keep50",
            "transition_topk": 32,
            "cache_capacity": 4,
            "bandwidth_gbps": 6.0,
            "overlap_factor": 0.5,
            "manager_us_per_issue": 7.0,
            "lookup_us_per_demand": 0.25,
            "decision_us_per_token_layer": 0.5,
            "measured_copy_us_per_issue": 11.0,
            "measured_copy_stat": "p95",
            "measured_copy_effective_gbps": 3.3,
            "max_inflight_prefetches": 2,
            "queue_model": "event",
            "queue_batch_size": 4,
            "queue_coalesce_scope": "global",
            "queue_policy": "drop",
            "queue_admission_policy": "score",
            "queue_wait_us_per_overflow": 11.0,
            "queue_event_interval_us": 2.0,
            "queue_deadline_us": 3.0,
            "stress_fallback": False,
            "demand_stream_hash": "demand-hash",
            "true_router_stream_hash": "router-hash",
            "policy_config_hash": "policy-hash",
            "demand_stream_rows": 11,
            "true_router_stream_rows": 22,
            "demand_hit_rate": 0.75,
            "issued_fetch_count": 3,
            "used_per_issued_fetch": 0.5,
            "evicted_before_use_count": 1,
            "demand_stall_ms": 2.0,
            "prefetch_dma_ms": 3.0,
            "prefetch_queue_wait_ms": 0.02,
            "prefetch_queue_model": "per_token_layer_burst_overflow",
            "prefetch_queue_backpressure_semantics": "burst semantics",
            "prefetch_queue_policy": "drop",
            "prefetch_queue_admission_policy": "score",
            "prefetch_queue_batch_size": 4,
            "prefetch_queue_coalesce_scope": "global",
            "prefetch_queue_batch_count": 2,
            "prefetch_queue_service_ms": 3.0,
            "prefetch_queue_total_span_ms": 5.0,
            "prefetch_queue_max_delay_ms": 0.4,
            "prefetch_queue_event_interval_us": 2.0,
            "prefetch_queue_deadline_us": 3.0,
            "prefetch_ready_late_miss_count": 7,
            "prefetch_late_completion_unused_count": 5,
            "prefetch_backpressure_dropped_count": 1,
            "prefetch_queue_pressure": 0.25,
            "prefetch_queue_overflow_count": 2,
            "prefetch_max_issue_burst": 4,
            "total_cost_ms": 4.0,
            "net_saved_ms_vs_transition": 0.5,
            "net_saved_ms_vs_no_prefetch": 0.6,
            "stress_shutdown_count": 2,
        }
    ]


def test_extract_rows_defaults_old_queue_reports_to_token_layer(tmp_path):
    report = tmp_path / "old.json"
    payload = {
        "metadata": {},
        "config": {"transition_topk": 32},
        "rows": [
            {
                "policy": "transition_top32",
                "total_cost_us": 1000.0,
            }
        ],
    }

    rows = extract_rows(report, payload)

    assert rows[0]["queue_coalesce_scope"] == "token_layer"
    assert rows[0]["prefetch_queue_coalesce_scope"] == "token_layer"
