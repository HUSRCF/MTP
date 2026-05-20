import json

from scripts.summarize_telemetry_ladder_repeats import build_summary


def test_repeat_summary_reports_neutral_candidate_and_blocks_final_gate() -> None:
    rows = [
        {
            "mode": "production_like",
            "repeat": 0,
            "returncode": 0,
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "generate_seconds_per_requested_output_token": 0.07175220724658203,
        },
        {
            "mode": "production_like",
            "repeat": 1,
            "returncode": 0,
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "generate_seconds_per_requested_output_token": 0.07225527638427734,
        },
        {
            "mode": "production_like",
            "repeat": 2,
            "returncode": 0,
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "generate_seconds_per_requested_output_token": 0.0733463613154297,
        },
        {
            "mode": "production_like_disable_shared_stream",
            "repeat": 0,
            "returncode": 0,
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "generate_seconds_per_requested_output_token": 0.07208290501269532,
        },
        {
            "mode": "production_like_disable_shared_stream",
            "repeat": 1,
            "returncode": 0,
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "generate_seconds_per_requested_output_token": 0.07282542470947265,
        },
        {
            "mode": "production_like_disable_shared_stream",
            "repeat": 2,
            "returncode": 0,
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "generate_seconds_per_requested_output_token": 0.07244251356054687,
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
        min_tail_samples=1,
    )

    baseline = summary["modes"]["production_like"]
    candidate = summary["modes"]["production_like_disable_shared_stream"]
    comparison = summary["comparisons"]["production_like_disable_shared_stream"]

    assert baseline["count"] == 3
    assert baseline["median"] == 0.07225527638427734
    assert candidate["median"] == 0.07244251356054687
    assert comparison["median_delta_pct"] > 0.0
    assert comparison["median_gate_pass"] is False
    assert comparison["final_gate_pass"] is False
    assert comparison["tail_latency_available"] is False
    assert comparison["context_consistent"] is True
    assert summary["excluded_failed_rows"] == []


def test_repeat_summary_accepts_wrapped_results_shape() -> None:
    rows = {
        "results": [
            {
                "mode": "production_like",
                "returncode": 0,
                "sample_count": 1,
                "requested_output_token_count": 1,
                "generate_seconds_per_requested_output_token": 1.0,
            },
            {
                "mode": "candidate",
                "returncode": 0,
                "sample_count": 1,
                "requested_output_token_count": 1,
                "generate_seconds_per_requested_output_token": 0.98,
            },
        ]
    }
    serialized = json.loads(json.dumps(rows))
    summary = build_summary(
        serialized["results"],
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
    )

    comp = summary["comparisons"]["candidate"]
    assert comp["median_delta_pct"] == -2.0000000000000018
    assert comp["median_gate_pass"] is True
    assert comp["final_gate_pass"] is False


def test_repeat_summary_excludes_failed_rows() -> None:
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
        },
        {
            "mode": "candidate",
            "repeat": 0,
            "returncode": 1,
            "generate_seconds_per_requested_output_token": 0.1,
        },
        {
            "mode": "candidate",
            "repeat": 1,
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.1,
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
        min_tail_samples=1,
    )

    assert summary["modes"]["candidate"]["values"] == [1.1]
    assert summary["excluded_failed_rows"] == [
        {"mode": "candidate", "repeat": 0, "returncode": 1}
    ]


def test_repeat_summary_flags_context_inconsistency() -> None:
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "generate_seconds_per_requested_output_token": 1.0,
        },
        {
            "mode": "candidate",
            "returncode": 0,
            "sample_count": 128,
            "requested_output_token_count": 8192,
            "generate_seconds_per_requested_output_token": 0.9,
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
        min_tail_samples=1,
    )

    comp = summary["comparisons"]["candidate"]
    assert summary["context_consistent"] is False
    assert comp["context_consistent"] is False
    assert comp["median_gate_pass"] is True
    assert comp["final_gate_pass"] is False
    assert comp["final_gate_reason"] == "context_inconsistent"


def test_repeat_summary_reports_invalid_mode_rows() -> None:
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
        },
        {
            "mode": None,
            "returncode": 0,
            "generate_seconds_per_requested_output_token": 0.5,
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
    )

    assert summary["invalid_rows"] == [
        {"reason": "invalid_mode", "mode": None, "repeat": None, "returncode": 0}
    ]


def test_repeat_summary_marks_insufficient_repeats() -> None:
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
        },
        {
            "mode": "candidate",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 0.9,
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
        min_repeats=3,
    )

    comp = summary["comparisons"]["candidate"]
    assert comp["repeat_count_gate_pass"] is False
    assert comp["median_gate_pass"] is True
    assert comp["final_gate_reason"] == "insufficient_repeats"


def test_repeat_summary_reports_invalid_returncode_rows() -> None:
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
        },
        {
            "mode": "candidate",
            "returncode": "oops",
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 0.9,
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
    )

    assert summary["invalid_rows"] == [
        {
            "reason": "invalid_returncode",
            "mode": "candidate",
            "repeat": None,
            "returncode": "oops",
        }
    ]
    assert "candidate" not in summary["modes"]


def test_repeat_summary_reports_missing_tpot_rows() -> None:
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
        },
        {
            "mode": "candidate",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
    )

    assert summary["invalid_rows"] == [
        {
            "reason": "missing_tpot",
            "mode": "candidate",
            "repeat": None,
            "returncode": 0,
        }
    ]
    assert "candidate" not in summary["modes"]


def test_repeat_summary_reports_nonfinite_tpot_rows() -> None:
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
        },
        {
            "mode": "candidate",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": "nan",
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
    )

    assert summary["invalid_rows"] == [
        {
            "reason": "missing_tpot",
            "mode": "candidate",
            "repeat": None,
            "returncode": 0,
        }
    ]
    assert "candidate" not in summary["modes"]


def test_repeat_summary_reports_missing_returncode_rows() -> None:
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
        },
        {
            "mode": "candidate",
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 0.9,
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
    )

    assert summary["invalid_rows"] == [
        {
            "reason": "missing_returncode",
            "mode": "candidate",
            "repeat": None,
            "returncode": None,
        }
    ]


def test_repeat_summary_reports_invalid_context_rows() -> None:
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
        },
        {
            "mode": "candidate",
            "returncode": 0,
            "sample_count": "bad",
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 0.9,
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
    )

    assert summary["invalid_rows"] == [
        {
            "reason": "invalid_context_value",
            "mode": "candidate",
            "repeat": None,
            "field": "sample_count",
            "value": "bad",
        }
    ]


def test_repeat_summary_uses_sample_timing_tail_latency(tmp_path) -> None:
    base_dir = tmp_path / "base"
    cand_dir = tmp_path / "cand"
    base_dir.mkdir()
    cand_dir.mkdir()
    (base_dir / "sample_timing.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "scope": "sample",
                    "sample_idx": idx,
                    "requested_output_tokens": 10,
                    "generate_elapsed_us": elapsed,
                    "status": "ok",
                }
            )
            for idx, elapsed in enumerate([1000, 1100, 1200])
        )
        + "\n"
    )
    (cand_dir / "sample_timing.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "scope": "sample",
                    "sample_idx": idx,
                    "requested_output_tokens": 10,
                    "generate_elapsed_us": elapsed,
                    "status": "ok",
                }
            )
            for idx, elapsed in enumerate([900, 1000, 1300])
        )
        + "\n"
    )
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 3,
            "requested_output_token_count": 30,
            "generate_seconds_per_requested_output_token": 0.00011,
            "trace_dir": str(base_dir),
        },
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 3,
            "requested_output_token_count": 30,
            "generate_seconds_per_requested_output_token": 0.00011,
            "trace_dir": str(base_dir),
        },
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 3,
            "requested_output_token_count": 30,
            "generate_seconds_per_requested_output_token": 0.00011,
            "trace_dir": str(base_dir),
        },
        {
            "mode": "candidate",
            "returncode": 0,
            "sample_count": 3,
            "requested_output_token_count": 30,
            "generate_seconds_per_requested_output_token": 0.000105,
            "trace_dir": str(cand_dir),
        },
        {
            "mode": "candidate",
            "returncode": 0,
            "sample_count": 3,
            "requested_output_token_count": 30,
            "generate_seconds_per_requested_output_token": 0.000105,
            "trace_dir": str(cand_dir),
        },
        {
            "mode": "candidate",
            "returncode": 0,
            "sample_count": 3,
            "requested_output_token_count": 30,
            "generate_seconds_per_requested_output_token": 0.000105,
            "trace_dir": str(cand_dir),
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
        min_tail_samples=1,
    )

    comp = summary["comparisons"]["candidate"]
    assert comp["tail_latency_available"] is True
    assert comp["tail_latency_gate_pass"] is False
    assert comp["p99_delta_pct"] > 0.0
    assert comp["final_gate_reason"] == "tail_latency_regression"


def test_repeat_summary_final_gate_can_pass_with_statistical_evidence(tmp_path) -> None:
    base_dir = tmp_path / "base"
    cand_dir = tmp_path / "cand"
    base_dir.mkdir()
    cand_dir.mkdir()
    for directory, elapsed_values in (
        (base_dir, [1200, 1300, 1400]),
        (cand_dir, [900, 1000, 1100]),
    ):
        (directory / "sample_timing.jsonl").write_text(
            "\n".join(
                json.dumps(
                    {
                        "scope": "sample",
                        "sample_idx": idx,
                        "requested_output_tokens": 10,
                        "generate_elapsed_us": elapsed,
                        "status": "ok",
                    }
                )
                for idx, elapsed in enumerate(elapsed_values)
            )
            + "\n"
        )
    rows = []
    for _ in range(3):
        rows.append(
            {
                "mode": "production_like",
                "returncode": 0,
                "sample_count": 3,
                "requested_output_token_count": 30,
                "generate_seconds_per_requested_output_token": 0.00013,
                "trace_dir": str(base_dir),
            }
        )
        rows.append(
            {
                "mode": "candidate",
                "returncode": 0,
                "sample_count": 3,
                "requested_output_token_count": 30,
                "generate_seconds_per_requested_output_token": 0.00010,
                "trace_dir": str(cand_dir),
            }
        )

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
        min_tail_samples=1,
    )

    comp = summary["comparisons"]["candidate"]
    assert comp["median_gate_pass"] is True
    assert comp["tail_latency_gate_pass"] is True
    assert comp["final_gate_pass"] is True
    assert comp["final_gate_reason"] == "passed"


def test_repeat_summary_can_require_external_parity(tmp_path) -> None:
    base_dir = tmp_path / "base"
    cand_dir = tmp_path / "cand"
    base_dir.mkdir()
    cand_dir.mkdir()
    for directory, elapsed in ((base_dir, 1200), (cand_dir, 900)):
        (directory / "sample_timing.jsonl").write_text(
            json.dumps(
                {
                    "scope": "sample",
                    "sample_idx": 0,
                    "requested_output_tokens": 10,
                    "generate_elapsed_us": elapsed,
                    "status": "ok",
                }
            )
            + "\n"
        )
    rows = []
    for _ in range(3):
        rows.extend(
            [
                {
                    "mode": "production_like",
                    "returncode": 0,
                    "sample_count": 1,
                    "requested_output_token_count": 10,
                    "generate_seconds_per_requested_output_token": 0.00012,
                    "trace_dir": str(base_dir),
                },
                {
                    "mode": "candidate",
                    "returncode": 0,
                    "sample_count": 1,
                    "requested_output_token_count": 10,
                    "generate_seconds_per_requested_output_token": 0.00009,
                    "trace_dir": str(cand_dir),
                },
            ]
        )

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
        min_tail_samples=1,
        require_parity=True,
        parity_available=False,
    )

    comp = summary["comparisons"]["candidate"]
    assert comp["final_gate_pass"] is False
    assert comp["final_gate_reason"] == "parity_not_available"


def test_repeat_summary_marks_insufficient_tail_samples(tmp_path) -> None:
    base_dir = tmp_path / "base"
    cand_dir = tmp_path / "cand"
    base_dir.mkdir()
    cand_dir.mkdir()
    for directory, elapsed in ((base_dir, 1000), (cand_dir, 900)):
        (directory / "sample_timing.jsonl").write_text(
            json.dumps(
                {
                    "scope": "sample",
                    "sample_idx": 0,
                    "requested_output_tokens": 10,
                    "generate_elapsed_us": elapsed,
                    "status": "ok",
                }
            )
            + "\n"
        )
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 10,
            "generate_seconds_per_requested_output_token": 0.0001,
            "trace_dir": str(base_dir),
        },
        {
            "mode": "candidate",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 10,
            "generate_seconds_per_requested_output_token": 0.00009,
            "trace_dir": str(cand_dir),
        },
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
        min_repeats=1,
        min_tail_samples=30,
    )

    comp = summary["comparisons"]["candidate"]
    assert comp["tail_latency_available"] is True
    assert comp["tail_count_gate_pass"] is False
    assert comp["final_gate_reason"] == "insufficient_tail_samples"


def test_repeat_summary_reports_invalid_sample_timing_json(tmp_path) -> None:
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    (trace_dir / "sample_timing.jsonl").write_text("{bad json\n")
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
            "trace_dir": str(trace_dir),
        }
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
    )

    assert summary["invalid_rows"] == [
        {
            "reason": "invalid_sample_timing_json",
            "path": str(trace_dir / "sample_timing.jsonl"),
            "line_no": 1,
        }
    ]
    assert summary["modes"]["production_like"]["sample_timing_tpot"] == {
        "available": False,
        "count": 0,
    }


def test_repeat_summary_reports_bad_sample_timing_rows(tmp_path) -> None:
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    (trace_dir / "sample_timing.jsonl").write_text(
        "\n".join(
            [
                json.dumps(["not", "an", "object"]),
                json.dumps(
                    {
                        "scope": "sample",
                        "status": "error",
                        "requested_output_tokens": 1,
                        "generate_elapsed_us": 1,
                    }
                ),
                json.dumps(
                    {
                        "scope": "sample",
                        "status": "ok",
                        "requested_output_tokens": "bad",
                        "generate_elapsed_us": 1,
                    }
                ),
                json.dumps(
                    {
                        "scope": "sample",
                        "status": "ok",
                        "requested_output_tokens": 1,
                        "generate_elapsed_us": "nan",
                    }
                ),
            ]
        )
        + "\n"
    )
    rows = [
        {
            "mode": "production_like",
            "returncode": 0,
            "sample_count": 1,
            "requested_output_token_count": 1,
            "generate_seconds_per_requested_output_token": 1.0,
            "trace_dir": str(trace_dir),
        }
    ]

    summary = build_summary(
        rows,
        baseline_mode="production_like",
        min_median_improvement_pct=1.0,
    )

    assert [row["reason"] for row in summary["invalid_rows"]] == [
        "invalid_sample_timing_row",
        "sample_timing_status_not_ok",
        "invalid_sample_timing_tokens",
        "invalid_sample_timing_elapsed_us",
    ]
