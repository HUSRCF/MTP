from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_future_wna16_assignment_variant_paired_tpot.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_future_wna16_assignment_variant_paired_tpot",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _write_sample_timing(path: Path, values: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for value in values:
        lines.append(
            json.dumps(
                {
                    "scope": "sample",
                    "status": "ok",
                    "requested_output_tokens": 10,
                    "generate_elapsed_us": value * 10 * 1_000_000,
                },
                sort_keys=True,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _perf(module, *, role: str) -> dict:
    payload = {
        "generate_seconds_per_requested_output_token": 1.0,
        "generate_wall_seconds": 100.0,
        "sample_count": 32,
        "requested_output_token_count": 2048,
        "decode_workload_trace_enabled": False,
        "runtime_shadow_enabled": False,
        "runtime_shadow_record_router_topk": False,
        "runtime_shadow_emit_decoder_layer_timing": False,
        "runtime_shadow_emit_decoder_component_timing": False,
        "runtime_shadow_emit_moe_substage_timing": False,
        "runtime_shadow_emit_engine_timing": False,
        "runtime_shadow_emit_wna16_kernel_timing": False,
        "runtime_shadow_emit_premap_summaries": False,
        "runtime_shadow_emit_premap_consumer_mapping": False,
        "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled": False,
        "runtime_shadow_decoder_source_timing_mode": "off",
        "runtime_shadow_moe_source_timing_mode": "off",
        "runtime_shadow_outcome_logging_mode": "off",
        "runtime_shadow_premap_kernel_arg_handoff_prepared_table_materialization_mode": "off",
    }
    if role == "baseline":
        payload.update(
            {
                key: False
                for key in module.BASELINE_FALSE_PERF_FIELDS
            }
        )
    else:
        payload.update(
            {
                key: True
                for key in module.CANDIDATE_TRUE_PERF_FIELDS
            }
        )
        payload.update(module.CANDIDATE_EQUAL_PERF_FIELDS)
    return payload


def _rows_and_files(tmp_path: Path, module, *, candidate_tpots: list[float]) -> list[dict]:
    rows = []
    baseline_tpots = [1.00, 1.02, 1.01]
    for role, mode, tpots in [
        ("baseline", module.DEFAULT_BASELINE_MODE, baseline_tpots),
        ("candidate", module.DEFAULT_CANDIDATE_MODE, candidate_tpots),
    ]:
        for repeat, tpot in enumerate(tpots):
            trace_dir = tmp_path / role / f"repeat_{repeat:02d}"
            perf = _perf(module, role=role)
            perf["generate_seconds_per_requested_output_token"] = tpot
            perf["generate_wall_seconds"] = tpot * 100
            _write_json(trace_dir / "performance_summary.json", perf)
            _write_sample_timing(
                trace_dir / "sample_timing.jsonl",
                [tpot, tpot * 1.01, tpot * 1.02],
            )
            rows.append(
                {
                    "mode": mode,
                    "repeat": repeat,
                    "returncode": 0,
                    "trace_dir": str(trace_dir),
                    "generate_seconds_per_requested_output_token": tpot,
                    "generate_wall_seconds": tpot * 100,
                    "sample_count": 32,
                    "requested_output_token_count": 2048,
                    "split_id": "external_prompt_gate_dolly_32_gen64_utilization",
                    "effective_max_tokens": 64,
                }
            )
    return rows


def test_paired_tpot_summary_passes_positive_candidate(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])

    summary = module.build_summary(
        rows,
        results_json=tmp_path / "results.json",
        max_allowed_p95_delta_pct=1.0,
        max_allowed_p99_delta_pct=1.0,
    )

    assert summary["passed"] is True
    assert summary["repeat_count"] == 3
    assert summary["candidate_positive_all_repeats"] is True
    assert summary["sample_tail_gate_pass"] is True
    assert summary["candidate_enables_gpu_assignment_kernel_variant"] is True
    assert summary["prepared_table_path_enabled"] is False
    assert summary["payload_bytes"] == 0
    assert summary["endpoint_or_chunk_tpot_only"] is True
    assert summary["tail_latency_claim_supported"] is True


def test_paired_tpot_summary_rejects_missing_candidate_repeat(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    rows = [
        row
        for row in rows
        if not (row["mode"] == module.DEFAULT_CANDIDATE_MODE and row["repeat"] == 2)
    ]

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert any("candidate_missing_repeats" in item for item in summary["failures"])
    assert "insufficient_paired_repeats" in summary["failures"]


def test_paired_tpot_summary_rejects_nonpositive_repeat(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.05, 0.98])

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert summary["candidate_positive_all_repeats"] is False
    assert "candidate_not_positive_all_repeats" in summary["failures"]


def test_paired_tpot_summary_rejects_candidate_without_live_variant(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    perf_path = tmp_path / "candidate" / "repeat_00" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf["runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled"] = False
    _write_json(perf_path, perf)

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "candidate_performance_runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled_not_true" in summary["failures"]


def test_paired_tpot_summary_rejects_prepared_table_materialization(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    perf_path = tmp_path / "candidate" / "repeat_00" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf["runtime_shadow_premap_kernel_arg_handoff_prepared_table_materialization_mode"] = "materialize"
    _write_json(perf_path, perf)

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "candidate_performance_runtime_shadow_premap_kernel_arg_handoff_prepared_table_materialization_mode_mismatch" in summary["failures"]


def test_paired_tpot_summary_rejects_typed_slot_variant_enabled(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    perf_path = tmp_path / "candidate" / "repeat_00" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf["runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled"] = True
    _write_json(perf_path, perf)

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "candidate_performance_runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled_not_false" in summary["failures"]


def test_paired_tpot_summary_rejects_baseline_live_handoff(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    perf_path = tmp_path / "baseline" / "repeat_00" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf["runtime_shadow_premap_kernel_arg_handoff_live_enabled"] = True
    _write_json(perf_path, perf)

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "baseline_performance_runtime_shadow_premap_kernel_arg_handoff_live_enabled_not_false" in summary["failures"]


def test_paired_tpot_summary_rejects_chunk_timing_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    timing = tmp_path / "candidate" / "repeat_00" / "sample_timing.jsonl"
    timing.write_text(
        json.dumps(
            {
                "scope": "chunk",
                "status": "ok",
                "requested_output_tokens": 100,
                "generate_elapsed_us": 123.0,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "candidate_chunk_timing_tpot_mismatch:0" in summary["failures"]


def test_paired_tpot_summary_rejects_one_bad_chunk_among_multiple(
    tmp_path: Path,
) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    timing = tmp_path / "candidate" / "repeat_00" / "sample_timing.jsonl"
    timing.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "scope": "chunk",
                        "status": "ok",
                        "requested_output_tokens": 100,
                        "generate_elapsed_us": 0.99 * 100 * 1_000_000,
                    },
                    sort_keys=True,
                ),
                json.dumps(
                    {
                        "scope": "chunk",
                        "status": "ok",
                        "requested_output_tokens": 100,
                        "generate_elapsed_us": 0.5 * 100 * 1_000_000,
                    },
                    sort_keys=True,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "candidate_chunk_timing_tpot_mismatch:0" in summary["failures"]


def test_paired_tpot_summary_rejects_missing_perf_tpot_and_wall(
    tmp_path: Path,
) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    perf_path = tmp_path / "candidate" / "repeat_00" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf.pop("generate_seconds_per_requested_output_token")
    perf.pop("generate_wall_seconds")
    _write_json(perf_path, perf)

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "candidate_performance_tpot_missing_or_invalid:0" in summary["failures"]
    assert "candidate_performance_generate_wall_missing_or_invalid:0" in summary["failures"]


def test_paired_tpot_summary_rejects_context_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    for row in rows:
        if row["mode"] == module.DEFAULT_CANDIDATE_MODE and row["repeat"] == 1:
            row["sample_count"] = 128

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "paired_context_mismatch" in summary["failures"]


def test_paired_tpot_summary_rejects_strict_expected_context_mismatch(
    tmp_path: Path,
) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    for row in rows:
        row["effective_max_tokens"] = 32

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert summary["context_consistent"] is True
    assert "strict_context_mismatch" in summary["failures"]


def test_paired_tpot_summary_allows_chunk_only_timing_by_default(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    for role in ("baseline", "candidate"):
        for repeat in range(3):
            row = next(
                item
                for item in rows
                if item["mode"]
                == (
                    module.DEFAULT_BASELINE_MODE
                    if role == "baseline"
                    else module.DEFAULT_CANDIDATE_MODE
                )
                and item["repeat"] == repeat
            )
            timing = tmp_path / role / f"repeat_{repeat:02d}" / "sample_timing.jsonl"
            timing.write_text(
                json.dumps(
                    {
                        "scope": "chunk",
                        "status": "ok",
                        "requested_output_tokens": 100,
                        "generate_elapsed_us": row["generate_seconds_per_requested_output_token"] * 100 * 1_000_000,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is True
    assert summary["sample_tail_available"] is False
    assert summary["sample_tail_gate_pass"] is None


def test_paired_tpot_summary_can_require_sample_tail(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, candidate_tpots=[0.99, 1.00, 0.98])
    for role in ("baseline", "candidate"):
        for repeat in range(3):
            row = next(
                item
                for item in rows
                if item["mode"]
                == (
                    module.DEFAULT_BASELINE_MODE
                    if role == "baseline"
                    else module.DEFAULT_CANDIDATE_MODE
                )
                and item["repeat"] == repeat
            )
            timing = tmp_path / role / f"repeat_{repeat:02d}" / "sample_timing.jsonl"
            timing.write_text(
                json.dumps(
                    {
                        "scope": "chunk",
                        "status": "ok",
                        "requested_output_tokens": 100,
                        "generate_elapsed_us": row["generate_seconds_per_requested_output_token"] * 100 * 1_000_000,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

    summary = module.build_summary(
        rows,
        results_json=tmp_path / "results.json",
        require_sample_tail=True,
    )

    assert summary["passed"] is False
    assert summary["sample_tail_required"] is True
    assert "sample_tail_required_but_unavailable" in summary["failures"]
