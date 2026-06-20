from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


LOOKAHEAD_CALLS = []


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "sweep_premap_payload_cache_issue_stream_executor_queue_budget.py"
    )
    spec = importlib.util.spec_from_file_location(
        "sweep_premap_payload_cache_issue_stream_executor_queue_budget",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeLookahead:
    @staticmethod
    def run_stream_lookahead_sweep(args):
        LOOKAHEAD_CALLS.append(args)
        capacity = int(args.capacity)
        deadline = float(args.queue_deadline_us)
        passed = capacity >= 128 and deadline >= 1000.0
        rows = []
        for lead in [int(item) for item in args.issue_lead_token_values.split(",")]:
            row_passed = passed and lead >= 2
            rows.append(
                {
                    "issue_lead_tokens": lead,
                    "lookahead_us": float(lead) * float(args.decode_token_us),
                    "passed": row_passed,
                    "demand_hit_rate": 0.7 if row_passed else 0.2,
                    "ready_late_miss_rate": 0.3 if row_passed else 0.8,
                    "used_per_issued_fetch": 0.5 if row_passed else 0.0,
                }
            )
        first_row = next((row for row in rows if row["passed"]), None)
        return {
            "passed": first_row is not None,
            "failures": [],
            "first_model_passing_issue_lead_tokens": (
                None if first_row is None else first_row["issue_lead_tokens"]
            ),
            "first_model_passing_lookahead_us": (
                None if first_row is None else first_row["lookahead_us"]
            ),
            "rows": rows,
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
        }


def test_queue_budget_sweep_finds_first_passing_cell(monkeypatch, tmp_path: Path):
    module = _load_module()
    LOOKAHEAD_CALLS.clear()
    monkeypatch.setattr(module, "_load_lookahead_module", lambda: _FakeLookahead)

    result = module.run_queue_budget_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=tmp_path / "copy.json",
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity_values="64,128",
            queue_deadline_us_values="200,1000",
            event_timing_mode="token_index",
            decode_token_us=100.0,
            issue_lead_token_values="0,1,2,4",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            allow_empty_config_packets=True,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="0,100",
            min_demand_hit_rate=0.6,
            max_ready_late_miss_rate=0.4,
            min_used_per_issued_fetch=0.4,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is True
    assert result["first_passing_cell"] == {
        "capacity": 128,
        "queue_deadline_us": 1000.0,
        "issue_lead_tokens": 2,
        "lookahead_us": 200.0,
        "cell_index": 3,
    }
    assert result["cell_count"] == 4
    assert result["cells"][3]["passed"] is True
    assert result["cells"][3]["first_passing_row"]["issue_lead_tokens"] == 2
    assert result["full_fetch_allowed"] is False
    assert result["payload_transfer_enabled"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert (tmp_path / "out.json").exists()
    assert [(call.capacity, call.queue_deadline_us) for call in LOOKAHEAD_CALLS] == [
        (64, 200.0),
        (64, 1000.0),
        (128, 200.0),
        (128, 1000.0),
    ]
    assert all(call.allow_empty_config_packets for call in LOOKAHEAD_CALLS)


def test_queue_budget_sweep_rejects_unsafe_cell(monkeypatch, tmp_path: Path):
    module = _load_module()
    LOOKAHEAD_CALLS.clear()

    class UnsafeLookahead(_FakeLookahead):
        @staticmethod
        def run_stream_lookahead_sweep(args):
            payload = _FakeLookahead.run_stream_lookahead_sweep(args)
            payload["passed_to_kernel"] = True
            return payload

    monkeypatch.setattr(module, "_load_lookahead_module", lambda: UnsafeLookahead)

    result = module.run_queue_budget_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=None,
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity_values="128",
            queue_deadline_us_values="1000",
            event_timing_mode="token_index",
            decode_token_us=100.0,
            issue_lead_token_values="0,1,2",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            allow_empty_config_packets=True,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="0,100",
            min_demand_hit_rate=0.6,
            max_ready_late_miss_rate=0.4,
            min_used_per_issued_fetch=0.4,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert result["first_passing_cell"] is None
    assert result["first_model_passing_cell"] == {
        "capacity": 128,
        "queue_deadline_us": 1000.0,
        "issue_lead_tokens": 2,
        "lookahead_us": 200.0,
        "cell_index": 0,
    }
    assert result["failures"] == ["cell_0_passed_to_kernel_not_false"]
    assert result["cells"][0]["model_passed"] is True
    assert result["cells"][0]["safety_passed"] is False


def test_queue_budget_sweep_nulls_first_passing_cell_when_later_cell_is_unsafe(
    monkeypatch,
    tmp_path: Path,
):
    module = _load_module()
    LOOKAHEAD_CALLS.clear()

    class LaterUnsafeLookahead(_FakeLookahead):
        @staticmethod
        def run_stream_lookahead_sweep(args):
            payload = _FakeLookahead.run_stream_lookahead_sweep(args)
            if int(args.capacity) == 256:
                payload["payload_transfer_enabled"] = True
            return payload

    monkeypatch.setattr(module, "_load_lookahead_module", lambda: LaterUnsafeLookahead)

    result = module.run_queue_budget_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=None,
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity_values="128,256",
            queue_deadline_us_values="1000",
            event_timing_mode="token_index",
            decode_token_us=100.0,
            issue_lead_token_values="0,1,2",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            allow_empty_config_packets=True,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="0,100",
            min_demand_hit_rate=0.6,
            max_ready_late_miss_rate=0.4,
            min_used_per_issued_fetch=0.4,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert result["first_passing_cell"] is None
    assert result["first_model_passing_cell"] == {
        "capacity": 128,
        "queue_deadline_us": 1000.0,
        "issue_lead_tokens": 2,
        "lookahead_us": 200.0,
        "cell_index": 0,
    }
    assert result["failures"] == ["cell_1_payload_transfer_enabled_not_false"]
    assert result["cells"][0]["passed"] is True
    assert result["cells"][1]["passed"] is False


def test_queue_budget_sweep_promotes_child_failures(monkeypatch, tmp_path: Path):
    module = _load_module()
    LOOKAHEAD_CALLS.clear()

    class ChildFailureLookahead(_FakeLookahead):
        @staticmethod
        def run_stream_lookahead_sweep(args):
            payload = _FakeLookahead.run_stream_lookahead_sweep(args)
            if int(args.capacity) == 256:
                payload["failures"] = ["row_0_payload_transfer_enabled_not_false"]
                payload["passed"] = False
            return payload

    monkeypatch.setattr(module, "_load_lookahead_module", lambda: ChildFailureLookahead)

    result = module.run_queue_budget_sweep(
        SimpleNamespace(
            online_canary_json=tmp_path / "online.json",
            measured_copy_json=None,
            measured_copy_stat="p95",
            measured_copy_experts=8,
            measured_copy_pinned="true",
            capacity_values="128,256",
            queue_deadline_us_values="1000",
            event_timing_mode="token_index",
            decode_token_us=100.0,
            issue_lead_token_values="0,1,2",
            layer_event_interval_us=1.0,
            allow_config_token_source=False,
            allow_empty_config_packets=True,
            event_interval_us=1.0,
            issue_arrival_us=0.0,
            lookahead_us_values="0,100",
            min_demand_hit_rate=0.6,
            max_ready_late_miss_rate=0.4,
            min_used_per_issued_fetch=0.4,
            output_json=tmp_path / "out.json",
        )
    )

    assert result["passed"] is False
    assert result["first_passing_cell"] is None
    assert result["first_model_passing_cell"] == {
        "capacity": 128,
        "queue_deadline_us": 1000.0,
        "issue_lead_tokens": 2,
        "lookahead_us": 200.0,
        "cell_index": 0,
    }
    assert result["failures"] == ["cell_1_row_0_payload_transfer_enabled_not_false"]
    assert result["cells"][1]["model_passed"] is True
    assert result["cells"][1]["child_passed"] is False
    assert result["cells"][1]["safety_failures"] == [
        "cell_1_row_0_payload_transfer_enabled_not_false"
    ]


def test_queue_budget_sweep_rejects_unsorted_values(monkeypatch, tmp_path: Path):
    module = _load_module()
    monkeypatch.setattr(module, "_load_lookahead_module", lambda: _FakeLookahead)

    try:
        module.run_queue_budget_sweep(
            SimpleNamespace(
                online_canary_json=tmp_path / "online.json",
                measured_copy_json=None,
                measured_copy_stat="p95",
                measured_copy_experts=8,
                measured_copy_pinned="true",
                capacity_values="128,64",
                queue_deadline_us_values="1000",
                event_timing_mode="token_index",
                decode_token_us=100.0,
                issue_lead_token_values="0,1",
                layer_event_interval_us=1.0,
                allow_config_token_source=False,
                allow_empty_config_packets=True,
                event_interval_us=1.0,
                issue_arrival_us=0.0,
                lookahead_us_values="0,100",
                min_demand_hit_rate=0.6,
                max_ready_late_miss_rate=0.4,
                min_used_per_issued_fetch=0.4,
                output_json=tmp_path / "out.json",
            )
        )
    except ValueError as exc:
        assert "capacity sweep values must be sorted" in str(exc)
    else:
        raise AssertionError("expected unsorted capacity rejection")
