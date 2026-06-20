from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace

EXECUTOR_CALLS = []


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "sweep_premap_payload_cache_issue_stream_executor_lookahead.py"
    )
    spec = importlib.util.spec_from_file_location(
        "sweep_premap_payload_cache_issue_stream_executor_lookahead",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeExecutor:
    DEFAULT_ONLINE_CANARY_JSON = Path("reports/online.json")

    @staticmethod
    def build_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument("--online-canary-json", type=Path)
        parser.add_argument("--output-json", type=Path)
        parser.add_argument("--capacity", type=int)
        parser.add_argument("--queue-deadline-us", type=float)
        parser.add_argument("--event-interval-us", type=float)
        parser.add_argument("--event-timing-mode")
        parser.add_argument("--decode-token-us", type=float)
        parser.add_argument("--issue-lead-tokens", type=int)
        parser.add_argument("--layer-event-interval-us", type=float)
        parser.add_argument("--allow-config-token-source", action="store_true")
        parser.add_argument("--allow-empty-config-packets", action="store_true")
        parser.add_argument("--issue-arrival-us", type=float)
        parser.add_argument("--demand-gap-us", type=float)
        parser.add_argument("--min-demand-hit-rate", type=float)
        parser.add_argument("--max-ready-late-miss-rate", type=float)
        parser.add_argument("--min-used-per-issued-fetch", type=float)
        parser.add_argument("--measured-copy-json", type=Path)
        parser.add_argument("--measured-copy-stat")
        parser.add_argument("--measured-copy-experts", type=int)
        parser.add_argument("--measured-copy-pinned")
        return parser

    @staticmethod
    def run_issue_stream_executor(args):
        EXECUTOR_CALLS.append(args)
        passed = float(args.demand_gap_us) >= 250.0
        if getattr(args, "event_timing_mode", "packet_index") == "token_index":
            passed = int(args.issue_lead_tokens) >= 2
        return {
            "passed": passed,
            "payload_bytes": 0,
            "full_fetch_allowed": False,
            "ready_credit": False,
            "ready_before_demand_credit": False,
            "real_ready_credit_granted": False,
            "payload_transfer_enabled": False,
            "payload_deref_allowed": False,
            "kernel_arg_pass_allowed": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
            "full_fetch_block_reason": (
                "real_payload_runtime_not_enabled"
                if passed
                else "measured_copy_stream_deadline_miss"
            ),
            "demand_hit_rate": 1.0 if passed else 0.25,
            "ready_late_miss_rate": 0.0 if passed else 0.75,
            "used_per_issued_fetch": 1.0 if passed else 0.0,
            "queue_total_span_us": 123.0,
            "queue_service_us": 100.0,
            "queue_max_delay_us": 120.0,
            "measured_copy_us_per_batch": 100.0,
            "measured_copy_us_per_issue": 12.5,
            "token_index_count": 4 if args.event_timing_mode == "token_index" else 0,
            "token_index_min": 3 if args.event_timing_mode == "token_index" else None,
            "token_index_max": 6 if args.event_timing_mode == "token_index" else None,
            "token_source_decode_workload_count": (
                4 if args.event_timing_mode == "token_index" else 0
            ),
            "token_source_config_count": 0,
            "token_source_missing_count": 0,
            "allow_config_token_source": bool(args.allow_config_token_source),
            "allow_empty_config_packets": bool(args.allow_empty_config_packets),
            "issue_arrival_min_us": 100.0,
            "issue_arrival_max_us": 200.0,
            "demand_arrival_min_us": 300.0,
            "demand_arrival_max_us": 400.0,
            "failures": [] if passed else ["ready_late_miss_rate_above_threshold"],
        }


def test_stream_lookahead_sweep_finds_first_model_passing_row(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    EXECUTOR_CALLS.clear()
    monkeypatch.setattr(module, "_load_executor_module", lambda: _FakeExecutor)

    result = module.run_stream_lookahead_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=tmp_path / "copy.json",
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_timing_mode="packet_index",
            decode_token_us=75_000.0,
            issue_lead_token_values="0,1,2,4",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            allow_empty_config_packets=True,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="0,100,250,300",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is True
    assert result["first_model_passing_lookahead_us"] == 250.0
    assert result["rows"][0]["model_passed"] is False
    assert result["rows"][0]["safety_passed"] is True
    assert result["rows"][2]["model_passed"] is True
    assert result["rows"][2]["passed"] is True
    assert result["full_fetch_allowed"] is False
    assert result["payload_transfer_enabled"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert (tmp_path / "out.json").exists()
    assert [call.issue_lead_tokens for call in EXECUTOR_CALLS] == [0, 0, 0, 0]
    assert [call.demand_gap_us for call in EXECUTOR_CALLS] == [0.0, 100.0, 250.0, 300.0]


def test_stream_lookahead_sweep_supports_token_index_issue_lead_tokens(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    EXECUTOR_CALLS.clear()
    monkeypatch.setattr(module, "_load_executor_module", lambda: _FakeExecutor)

    result = module.run_stream_lookahead_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=tmp_path / "copy.json",
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_timing_mode="token_index",
            decode_token_us=100.0,
            issue_lead_token_values="0,1,2,4",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            allow_empty_config_packets=True,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="0,100,250,300",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is True
    assert result["event_timing_mode"] == "token_index"
    assert result["token_timing_enabled"] is True
    assert result["issue_lead_token_values"] == [0, 1, 2, 4]
    assert result["lookahead_us_values"] == [0.0, 100.0, 200.0, 400.0]
    assert result["configured_lookahead_us_values"] == [0.0, 100.0, 250.0, 300.0]
    assert result["requested_lookahead_us_values"] == [0.0, 100.0, 200.0, 400.0]
    assert result["first_model_passing_issue_lead_tokens"] == 2
    assert result["first_model_passing_lookahead_us"] == 200.0
    assert result["rows"][2]["issue_lead_tokens"] == 2
    assert result["rows"][2]["lookahead_us"] == 200.0
    assert result["rows"][2]["lookahead_us_kind"] == "requested_token_lead_us"
    assert result["rows"][2]["requested_lookahead_us"] == 200.0
    assert result["rows"][2]["requested_effective_ready_deadline_us"] == 400.0
    assert result["rows"][2]["observed_issue_to_demand_lead_min_us"] == 200.0
    assert result["rows"][2]["token_index_count"] == 4
    assert result["rows"][2]["token_source_decode_workload_count"] == 4
    assert result["rows"][2]["allow_empty_config_packets"] is True
    assert result["rows"][2]["passed"] is True
    assert [call.event_timing_mode for call in EXECUTOR_CALLS] == [
        "token_index",
        "token_index",
        "token_index",
        "token_index",
    ]
    assert [call.issue_lead_tokens for call in EXECUTOR_CALLS] == [0, 1, 2, 4]
    assert [call.demand_gap_us for call in EXECUTOR_CALLS] == [0.0, 100.0, 200.0, 400.0]
    assert not any(call.allow_config_token_source for call in EXECUTOR_CALLS)
    assert all(call.allow_empty_config_packets for call in EXECUTOR_CALLS)


def test_stream_lookahead_sweep_accepts_old_programmatic_namespace(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    EXECUTOR_CALLS.clear()
    monkeypatch.setattr(module, "_load_executor_module", lambda: _FakeExecutor)

    result = module.run_stream_lookahead_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=None,
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="0,250",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is True
    assert result["event_timing_mode"] == "packet_index"
    assert result["token_timing_enabled"] is False
    assert result["first_model_passing_lookahead_us"] == 250.0
    assert [call.issue_lead_tokens for call in EXECUTOR_CALLS] == [0, 0]


def test_stream_lookahead_sweep_rejects_nonfinite_lookahead_values(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    monkeypatch.setattr(module, "_load_executor_module", lambda: _FakeExecutor)

    try:
        module.run_stream_lookahead_sweep(
            SimpleNamespace(
                online_canary_json=tmp_path / "online.json",
                measured_copy_json=None,
                measured_copy_stat="p95",
                measured_copy_experts=8,
                measured_copy_pinned="true",
                capacity=12288,
                queue_deadline_us=200.0,
                event_interval_us=1.0,
                issue_arrival_us=0.0,
                lookahead_us_values="0,inf",
                min_demand_hit_rate=0.5,
                max_ready_late_miss_rate=0.2,
                min_used_per_issued_fetch=0.5,
                output_json=tmp_path / "out.json",
            )
        )
    except ValueError as exc:
        assert "lookahead sweep values must be finite" in str(exc)
    else:
        raise AssertionError("expected nonfinite lookahead rejection")


def test_stream_lookahead_sweep_rejects_full_fetch_allowed_row(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    EXECUTOR_CALLS.clear()

    class BadExecutor(_FakeExecutor):
        @staticmethod
        def run_issue_stream_executor(args):
            payload = _FakeExecutor.run_issue_stream_executor(args)
            payload["full_fetch_allowed"] = True
            return payload

    monkeypatch.setattr(module, "_load_executor_module", lambda: BadExecutor)

    result = module.run_stream_lookahead_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=None,
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_timing_mode="packet_index",
            decode_token_us=75_000.0,
            issue_lead_token_values="0,1,2,4",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="250",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert result["failures"] == ["row_0_full_fetch_allowed_not_false"]
    assert result["rows"][0]["model_passed"] is True
    assert result["rows"][0]["passed"] is False
    assert result["rows"][0]["safety_passed"] is False
    assert result["rows"][0]["safety_failures"] == [
        "row_0_full_fetch_allowed_not_false"
    ]


def test_stream_lookahead_sweep_rejects_missing_row_safety_flag(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    EXECUTOR_CALLS.clear()

    class MissingSafetyExecutor(_FakeExecutor):
        @staticmethod
        def run_issue_stream_executor(args):
            payload = _FakeExecutor.run_issue_stream_executor(args)
            payload.pop("kernel_arg_pass_allowed")
            return payload

    monkeypatch.setattr(module, "_load_executor_module", lambda: MissingSafetyExecutor)

    result = module.run_stream_lookahead_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=None,
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_timing_mode="packet_index",
            decode_token_us=75_000.0,
            issue_lead_token_values="0,1,2,4",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="250",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert result["failures"] == ["row_0_kernel_arg_pass_allowed_missing"]
    assert result["rows"][0]["passed"] is False
    assert result["rows"][0]["safety_failures"] == [
        "row_0_kernel_arg_pass_allowed_missing"
    ]


def test_stream_lookahead_sweep_rejects_payload_transfer_row(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    EXECUTOR_CALLS.clear()

    class UnsafeExecutor(_FakeExecutor):
        @staticmethod
        def run_issue_stream_executor(args):
            payload = _FakeExecutor.run_issue_stream_executor(args)
            payload["payload_transfer_enabled"] = True
            return payload

    monkeypatch.setattr(module, "_load_executor_module", lambda: UnsafeExecutor)

    result = module.run_stream_lookahead_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=None,
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_timing_mode="packet_index",
            decode_token_us=75_000.0,
            issue_lead_token_values="0,1,2,4",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="250",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert result["failures"] == ["row_0_payload_transfer_enabled_not_false"]


def test_stream_lookahead_sweep_rejects_bool_payload_bytes_row(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    EXECUTOR_CALLS.clear()

    class BoolPayloadExecutor(_FakeExecutor):
        @staticmethod
        def run_issue_stream_executor(args):
            payload = _FakeExecutor.run_issue_stream_executor(args)
            payload["payload_bytes"] = False
            return payload

    monkeypatch.setattr(module, "_load_executor_module", lambda: BoolPayloadExecutor)

    result = module.run_stream_lookahead_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=None,
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_timing_mode="packet_index",
            decode_token_us=75_000.0,
            issue_lead_token_values="0,1,2,4",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="250",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert result["failures"] == ["row_0_payload_bytes_not_zero"]
    assert result["rows"][0]["safety_failures"] == ["row_0_payload_bytes_not_zero"]
