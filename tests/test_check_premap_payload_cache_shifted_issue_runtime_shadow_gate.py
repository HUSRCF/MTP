from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "check_premap_payload_cache_shifted_issue_runtime_shadow_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_premap_payload_cache_shifted_issue_runtime_shadow_gate",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _summary(**overrides):
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"
    base = {
        f"{prefix}enabled": True,
        f"{prefix}issue_lead_tokens": 1,
        f"{prefix}packet_count": 4,
        f"{prefix}schedulable_packet_count": 3,
        f"{prefix}empty_issue_exempt_count": 1,
        f"{prefix}safe_packet_count": 4,
        f"{prefix}unsafe_packet_count": 0,
        f"{prefix}invalid_packet_count": 0,
        f"{prefix}scan_error_count": 0,
        f"{prefix}clamped_issue_count": 0,
        f"{prefix}duplicate_demand_key_count": 0,
        f"{prefix}duplicate_issue_key_count": 0,
        f"{prefix}unique_demand_key_count": 3,
        f"{prefix}unique_issue_key_count": 3,
        f"{prefix}total_issue_candidates": 24,
        f"{prefix}issue_hash_count": 3,
        f"{prefix}issue_hash_unique_count": 3,
        f"{prefix}payload_bytes": 0,
        f"{prefix}ready_credit": False,
        f"{prefix}ready_before_demand_credit": False,
        f"{prefix}real_ready_credit_granted": False,
        f"{prefix}payload_transfer_enabled": False,
        f"{prefix}payload_deref_allowed": False,
        f"{prefix}kernel_arg_pass_allowed": False,
        f"{prefix}passed_to_kernel": False,
        f"{prefix}changes_kernel_launch_args": False,
        f"{prefix}uses_current_wna16_args": False,
        f"{prefix}passes_current_wna16_args": False,
        f"{prefix}measures_tpot": False,
        f"{prefix}measures_vllm_latency": False,
    }
    base.update(overrides)
    return base


def test_shifted_issue_runtime_shadow_gate_passes():
    module = _load_module()

    payload = module.check_summary(
        _summary(),
        min_packet_count=4,
        min_schedulable_packet_count=3,
        required_issue_lead_tokens=1,
    )

    assert payload["passed"] is True
    assert payload["failures"] == []
    assert payload["packet_count"] == 4
    assert payload["schedulable_packet_count"] == 3
    assert payload["payload_bytes"] == 0
    assert payload["passed_to_kernel"] is False
    assert payload["measures_tpot"] is False


def test_shifted_issue_runtime_shadow_gate_rejects_unsafe_schedulable_summary():
    module = _load_module()
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"

    payload = module.check_summary(
        _summary(
            **{
                f"{prefix}safe_packet_count": 3,
                f"{prefix}unsafe_packet_count": 1,
            }
        )
    )

    assert payload["passed"] is False
    assert "safe_packet_count_not_equal_packet_count" in payload["failures"]
    assert "unsafe_packet_count_nonzero:1" in payload["failures"]


def test_shifted_issue_runtime_shadow_gate_rejects_duplicate_issue_key():
    module = _load_module()
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"

    payload = module.check_summary(
        _summary(
            **{
                f"{prefix}duplicate_issue_key_count": 1,
                f"{prefix}unique_issue_key_count": 2,
            }
        )
    )

    assert payload["passed"] is False
    assert "duplicate_issue_key_count_nonzero:1" in payload["failures"]
    assert "unique_issue_key_count_mismatch" in payload["failures"]


def test_shifted_issue_runtime_shadow_gate_rejects_bool_payload_bytes():
    module = _load_module()
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"

    payload = module.check_summary(_summary(**{f"{prefix}payload_bytes": False}))

    assert payload["passed"] is False
    assert "payload_bytes_not_strict_zero" in payload["failures"]


def test_shifted_issue_runtime_shadow_gate_rejects_kernel_arg_flag():
    module = _load_module()
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"

    payload = module.check_summary(
        _summary(**{f"{prefix}passed_to_kernel": True})
    )

    assert payload["passed"] is False
    assert "passed_to_kernel_not_false" in payload["failures"]


def test_shifted_issue_runtime_shadow_gate_rejects_bool_count_field():
    module = _load_module()
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"

    payload = module.check_summary(
        _summary(**{f"{prefix}unsafe_packet_count": False})
    )

    assert payload["passed"] is False
    assert f"{prefix}unsafe_packet_count_not_int" in payload["failures"]


def test_shifted_issue_runtime_shadow_gate_rejects_missing_count_field():
    module = _load_module()
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"
    summary = _summary()
    del summary[f"{prefix}scan_error_count"]

    payload = module.check_summary(summary)

    assert payload["passed"] is False
    assert f"{prefix}scan_error_count_missing" in payload["failures"]


def test_shifted_issue_runtime_shadow_gate_rejects_missing_issue_hash_unique_count():
    module = _load_module()
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"
    summary = _summary()
    del summary[f"{prefix}issue_hash_unique_count"]

    payload = module.check_summary(summary)

    assert payload["passed"] is False
    assert f"{prefix}issue_hash_unique_count_missing" in payload["failures"]


def test_shifted_issue_runtime_shadow_gate_allows_issue_duplicate_only():
    module = _load_module()
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"

    issue_only = module.check_summary(
        _summary(
            **{
                f"{prefix}duplicate_issue_key_count": 1,
                f"{prefix}unique_issue_key_count": 2,
            }
        ),
        require_no_issue_duplicates=False,
    )
    assert issue_only["passed"] is True

    demand_duplicate = module.check_summary(
        _summary(
            **{
                f"{prefix}duplicate_demand_key_count": 1,
                f"{prefix}unique_demand_key_count": 2,
            }
        ),
        require_no_issue_duplicates=False,
    )
    assert demand_duplicate["passed"] is False
    assert (
        "duplicate_demand_key_count_nonzero:1" in demand_duplicate["failures"]
    )
