from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "sweep_premap_payload_cache_stream_earlier_issue_lead_tokens.py"
    )
    spec = importlib.util.spec_from_file_location(
        "sweep_premap_payload_cache_stream_earlier_issue_lead_tokens",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _safe_fields() -> dict:
    return {
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "full_fetch_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


class _FakeStreamSweep:
    DEFAULT_ONLINE_CANARY_JSON = Path("reports/online.json")
    DEFAULT_MEASURED_COPY_JSON = Path("reports/measured_copy.json")

    @staticmethod
    def build_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument("--online-canary-json", type=Path)
        parser.add_argument("--measured-copy-json", type=Path)
        parser.add_argument("--measured-copy-stat")
        parser.add_argument("--measured-copy-experts", type=int)
        parser.add_argument("--measured-copy-pinned")
        parser.add_argument("--capacity", type=int)
        parser.add_argument("--queue-deadline-us", type=float)
        parser.add_argument("--event-interval-us", type=float)
        parser.add_argument("--issue-arrival-us", type=float)
        parser.add_argument("--lookahead-us-values")
        parser.add_argument("--min-demand-hit-rate", type=float)
        parser.add_argument("--max-ready-late-miss-rate", type=float)
        parser.add_argument("--min-used-per-issued-fetch", type=float)
        parser.add_argument("--output-json", type=Path)
        return parser

    @staticmethod
    def run_stream_lookahead_sweep(args):
        lookahead_values = [
            float(item) for item in str(args.lookahead_us_values).split(",") if item
        ]
        rows = []
        for lookahead_us in lookahead_values:
            model_passed = lookahead_us >= 150_000.0
            rows.append(
                {
                    **_safe_fields(),
                    "lookahead_us": lookahead_us,
                    "effective_ready_deadline_us": lookahead_us
                    + float(args.queue_deadline_us),
                    "model_passed": model_passed,
                    "safety_passed": True,
                    "safety_failures": [],
                    "passed": model_passed,
                    "demand_hit_rate": 0.9 if model_passed else 0.2,
                    "ready_late_miss_rate": 0.0 if model_passed else 0.8,
                    "used_per_issued_fetch": 0.8 if model_passed else 0.0,
                    "full_fetch_block_reason": (
                        "real_payload_runtime_not_enabled"
                        if model_passed
                        else "insufficient_lead_tokens"
                    ),
                }
            )
        return {
            **_safe_fields(),
            "artifact_kind": "premap_payload_cache_issue_stream_executor_lookahead_sweep",
            "passed": True,
            "failures": [],
            "lookahead_us_values": lookahead_values,
            "rows": rows,
        }


def test_lead_token_sweep_finds_first_passing_lead(monkeypatch, tmp_path: Path):
    module = _load_module()
    monkeypatch.setattr(module, "_load_stream_sweep_module", lambda: _FakeStreamSweep)

    result = module.run_earlier_issue_lead_token_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=tmp_path / "copy.json",
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            decode_token_us=75_000.0,
            lead_token_values="0,1,2,3,4",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is True
    assert result["first_model_passing_lead_tokens"] == 2
    assert result["first_model_passing_lookahead_us"] == 150_000.0
    assert result["full_fetch_runtime_allowed"] is False
    assert result["payload_transfer_enabled"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["rows"][2]["model_passed"] is True
    assert (tmp_path / "out.json").exists()


def test_lead_token_sweep_rejects_unsafe_underlying_row(monkeypatch, tmp_path: Path):
    module = _load_module()

    class UnsafeSweep(_FakeStreamSweep):
        @staticmethod
        def run_stream_lookahead_sweep(args):
            payload = _FakeStreamSweep.run_stream_lookahead_sweep(args)
            payload["rows"][1]["payload_transfer_enabled"] = True
            return payload

    monkeypatch.setattr(module, "_load_stream_sweep_module", lambda: UnsafeSweep)

    result = module.run_earlier_issue_lead_token_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=tmp_path / "copy.json",
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            decode_token_us=75_000.0,
            lead_token_values="0,1,2",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert "stream_sweep_row_1_payload_transfer_enabled_not_false" in result[
        "failures"
    ]
    assert result["full_fetch_runtime_allowed"] is False


def test_lead_token_sweep_rejects_unsafe_underlying_top_level(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()

    class UnsafeTopLevelSweep(_FakeStreamSweep):
        @staticmethod
        def run_stream_lookahead_sweep(args):
            payload = _FakeStreamSweep.run_stream_lookahead_sweep(args)
            payload["payload_transfer_enabled"] = True
            return payload

    monkeypatch.setattr(module, "_load_stream_sweep_module", lambda: UnsafeTopLevelSweep)

    result = module.run_earlier_issue_lead_token_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=tmp_path / "copy.json",
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            decode_token_us=75_000.0,
            lead_token_values="0,1,2",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert "stream_sweep_payload_transfer_enabled_not_false" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_lead_token_sweep_handles_malformed_rows_fail_closed(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()

    class MalformedRowsSweep(_FakeStreamSweep):
        @staticmethod
        def run_stream_lookahead_sweep(args):
            payload = _FakeStreamSweep.run_stream_lookahead_sweep(args)
            payload["rows"][1] = "not-a-row"
            return payload

    monkeypatch.setattr(module, "_load_stream_sweep_module", lambda: MalformedRowsSweep)

    result = module.run_earlier_issue_lead_token_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=tmp_path / "copy.json",
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            decode_token_us=75_000.0,
            lead_token_values="0,1,2",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert "stream_sweep_row_1_not_object" in result["failures"]
    assert result["rows"][1]["malformed_row"] is True
    assert result["rows"][1]["passed"] is False


def test_lead_token_sweep_rejects_truthy_non_bool_model_passed(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()

    class NonBoolPassedSweep(_FakeStreamSweep):
        @staticmethod
        def run_stream_lookahead_sweep(args):
            payload = _FakeStreamSweep.run_stream_lookahead_sweep(args)
            payload["rows"][2]["model_passed"] = "true"
            payload["rows"][2]["passed"] = True
            return payload

    monkeypatch.setattr(module, "_load_stream_sweep_module", lambda: NonBoolPassedSweep)

    result = module.run_earlier_issue_lead_token_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=tmp_path / "copy.json",
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity=12288,
            queue_deadline_us=200.0,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            decode_token_us=75_000.0,
            lead_token_values="0,1,2",
            min_demand_hit_rate=0.5,
            max_ready_late_miss_rate=0.2,
            min_used_per_issued_fetch=0.5,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert "stream_sweep_row_2_model_passed_invalid" in result["failures"]
    assert result["rows"][2]["model_passed"] is False


def test_lead_token_sweep_rejects_unsorted_lead_values():
    module = _load_module()

    try:
        module._parse_nonnegative_ints("2,1", label="lead token")  # noqa: SLF001
    except ValueError as exc:
        assert "sorted" in str(exc)
    else:
        raise AssertionError("expected unsorted lead values to be rejected")


def test_lead_token_sweep_build_parser_loads_defaults():
    module = _load_module()

    args = module.build_parser().parse_args([])

    assert args.online_canary_json is not None
    assert args.measured_copy_json is not None
    assert args.decode_token_us > 0


def test_lead_token_sweep_rejects_nonfinite_decode_token_us(monkeypatch, tmp_path: Path):
    module = _load_module()
    monkeypatch.setattr(module, "_load_stream_sweep_module", lambda: _FakeStreamSweep)

    try:
        module.run_earlier_issue_lead_token_sweep(
            SimpleNamespace(
                online_canary_json=tmp_path / "online.json",
                measured_copy_json=tmp_path / "copy.json",
                measured_copy_stat="p95",
                measured_copy_experts=8,
                measured_copy_pinned="true",
                capacity=12288,
                queue_deadline_us=200.0,
                event_interval_us=1.0,
                issue_arrival_us=0.0,
                decode_token_us=float("inf"),
                lead_token_values="0,1,2",
                min_demand_hit_rate=0.5,
                max_ready_late_miss_rate=0.2,
                min_used_per_issued_fetch=0.5,
                output_json=tmp_path / "out.json",
            )
        )
    except ValueError as exc:
        assert "positive finite" in str(exc)
    else:
        raise AssertionError("expected nonfinite decode-token-us to be rejected")
