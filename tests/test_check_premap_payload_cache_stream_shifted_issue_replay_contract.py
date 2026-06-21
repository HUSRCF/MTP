from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "check_premap_payload_cache_stream_shifted_issue_replay_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_premap_payload_cache_stream_shifted_issue_replay_contract",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _safe_fields() -> dict[str, object]:
    return {
        "full_fetch_runtime_allowed": False,
        "full_fetch_allowed": False,
        "payload_bytes": 0,
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
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "wna16_benchmark_ready": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def _contract(
    *,
    passed: bool = True,
    clamped: int = 0,
    duplicate_issue: int = 0,
    allow_clamped: bool = False,
    allow_duplicate_issue: bool = False,
) -> dict[str, object]:
    schedulable = 4
    unique_issue = schedulable - duplicate_issue
    demand_tokens = [8, 16, 32, 48] if duplicate_issue or clamped else [32, 40, 48, 56]
    issue_tokens = [max(0, demand - 32) for demand in demand_tokens]
    clamped_rows = {index for index, demand in enumerate(demand_tokens) if demand < 32}
    return {
        **_safe_fields(),
        "artifact_kind": "premap_payload_cache_stream_shifted_issue_replay_contract",
        "passed": passed,
        "failures": [] if passed else ["duplicate_issue_keys_present"],
        "issue_lead_tokens": 32,
        "packet_count": 5,
        "schedulable_packet_count": schedulable,
        "empty_issue_exempt_count": 1,
        "clamped_issue_count": clamped,
        "duplicate_demand_key_count": 0,
        "duplicate_issue_key_count": duplicate_issue,
        "unique_demand_key_count": schedulable,
        "unique_issue_key_count": unique_issue,
        "total_issue_candidates": 32,
        "issue_hash_count": schedulable,
        "allow_clamped_issue_tokens": allow_clamped,
        "allow_duplicate_issue_keys": allow_duplicate_issue,
        "rows": [
            {
                "packet_index": index,
                "sample_idx": 0,
                "record_id": "record-0",
                "sequence_id": 0,
                "layer_id": 0,
                "demand_token_index": demand_tokens[index],
                "issue_token_index": issue_tokens[index],
                "issue_clamped_to_zero": index in clamped_rows,
            }
            for index in range(schedulable)
        ],
    }


def test_shifted_issue_replay_contract_check_accepts_bootstrap_coalescing():
    module = _load_module()
    payload = _contract(
        clamped=2,
        duplicate_issue=2,
        allow_clamped=True,
        allow_duplicate_issue=True,
    )

    result = module.check_shifted_issue_replay_contract(
        payload,
        required_issue_lead_tokens=32,
        min_schedulable_packet_count=4,
        require_bootstrap_clamp=True,
        require_issue_key_coalescing=True,
    )

    assert result["passed"] is True
    assert result["clamped_issue_count"] == 2
    assert result["duplicate_issue_key_count"] == 2
    assert result["unique_issue_key_count"] == 2
    assert result["row_clamped_issue_count"] == 2
    assert result["row_duplicate_demand_key_count"] == 0
    assert result["row_duplicate_issue_key_count"] == 2
    assert result["row_unique_demand_key_count"] == 4
    assert result["row_unique_issue_key_count"] == 2
    assert result["row_shift_relation_mismatch_count"] == 0
    assert result["row_clamp_relation_mismatch_count"] == 0
    assert result["full_fetch_runtime_allowed"] is False
    assert result["payload_transfer_enabled"] is False
    assert result["passed_to_kernel"] is False


def test_shifted_issue_replay_contract_check_rejects_strict_failure_by_default():
    module = _load_module()
    payload = _contract(passed=False, clamped=2, duplicate_issue=2)

    result = module.check_shifted_issue_replay_contract(payload)

    assert result["passed"] is False
    assert "contract_not_passed" in result["failures"]
    assert "contract_failures_not_empty" in result["failures"]
    assert "clamped_issue_count_nonzero:2" in result["failures"]
    assert "duplicate_issue_key_count_nonzero:2" in result["failures"]


def test_shifted_issue_replay_contract_check_rejects_missing_bootstrap_flags():
    module = _load_module()
    payload = _contract(clamped=2, duplicate_issue=2)

    result = module.check_shifted_issue_replay_contract(
        payload,
        require_bootstrap_clamp=True,
        require_issue_key_coalescing=True,
    )

    assert result["passed"] is False
    assert "bootstrap_clamp_not_allowed" in result["failures"]
    assert "issue_key_coalescing_not_allowed" in result["failures"]


def test_shifted_issue_replay_contract_check_rejects_payload_or_kernel_side_effect():
    module = _load_module()
    payload = _contract()
    payload["payload_transfer_enabled"] = True
    payload["uses_current_wna16_args"] = True
    payload["wna16_benchmark_ready"] = True

    result = module.check_shifted_issue_replay_contract(payload)

    assert result["passed"] is False
    assert "payload_transfer_enabled_not_false" in result["failures"]
    assert "uses_current_wna16_args_not_false" in result["failures"]
    assert "wna16_benchmark_ready_not_false" in result["failures"]
    assert result["source_payload_transfer_enabled"] is True
    assert result["source_uses_current_wna16_args"] is True
    assert result["source_wna16_benchmark_ready"] is True


def test_shifted_issue_replay_contract_check_rejects_row_count_mismatch():
    module = _load_module()
    payload = _contract(
        clamped=2,
        duplicate_issue=2,
        allow_clamped=True,
        allow_duplicate_issue=True,
    )
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[1]["issue_clamped_to_zero"] = False
    rows[1]["issue_token_index"] = 4

    result = module.check_shifted_issue_replay_contract(
        payload,
        require_bootstrap_clamp=True,
        require_issue_key_coalescing=True,
    )

    assert result["passed"] is False
    assert "row_clamped_issue_count_mismatch" in result["failures"]
    assert "row_duplicate_issue_key_count_mismatch" in result["failures"]
    assert "row_unique_issue_key_count_mismatch" in result["failures"]


def test_shifted_issue_replay_contract_check_rejects_unshifted_issue_token():
    module = _load_module()
    payload = _contract()
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[1]["issue_token_index"] = rows[1]["demand_token_index"]

    result = module.check_shifted_issue_replay_contract(payload)

    assert result["passed"] is False
    assert "row_1_issue_token_shift_mismatch" in result["failures"]
    assert result["row_shift_relation_mismatch_count"] == 1


def test_shifted_issue_replay_contract_check_rejects_clamp_relation_mismatch():
    module = _load_module()
    payload = _contract(
        clamped=2,
        duplicate_issue=2,
        allow_clamped=True,
        allow_duplicate_issue=True,
    )
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[0]["issue_clamped_to_zero"] = False

    result = module.check_shifted_issue_replay_contract(
        payload,
        require_bootstrap_clamp=True,
        require_issue_key_coalescing=True,
    )

    assert result["passed"] is False
    assert "row_0_issue_clamp_mismatch" in result["failures"]
    assert "row_clamped_issue_count_mismatch" in result["failures"]
    assert result["row_clamp_relation_mismatch_count"] == 1


def test_shifted_issue_replay_contract_check_rejects_row_demand_key_mismatch():
    module = _load_module()
    payload = _contract()
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[1]["demand_token_index"] = rows[0]["demand_token_index"]

    result = module.check_shifted_issue_replay_contract(payload)

    assert result["passed"] is False
    assert "row_duplicate_demand_key_count_mismatch" in result["failures"]
    assert "row_unique_demand_key_count_mismatch" in result["failures"]


def test_shifted_issue_replay_contract_check_cli_fails_by_default(tmp_path: Path):
    module = _load_module()
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps(_contract(passed=False)), encoding="utf-8")

    exit_code = module.main([str(contract)])

    assert exit_code == 1


def test_shifted_issue_replay_contract_check_cli_writes_report(tmp_path: Path):
    module = _load_module()
    contract = tmp_path / "contract.json"
    output = tmp_path / "check.json"
    contract.write_text(
        json.dumps(
            _contract(
                clamped=2,
                duplicate_issue=2,
                allow_clamped=True,
                allow_duplicate_issue=True,
            )
        ),
        encoding="utf-8",
    )

    exit_code = module.main(
        [
            str(contract),
            "--required-issue-lead-tokens",
            "32",
            "--min-schedulable-packet-count",
            "4",
            "--require-bootstrap-clamp",
            "--require-issue-key-coalescing",
            "--require-pass",
            "--output-json",
            str(output),
        ]
    )

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True
