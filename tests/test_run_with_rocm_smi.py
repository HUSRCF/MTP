import json
import sys

import pytest

from scripts import run_with_rocm_smi


def test_run_with_rocm_smi_rejects_empty_command(tmp_path) -> None:
    with pytest.raises(ValueError):
        run_with_rocm_smi.run_with_sampling(
            command=[],
            gpu=0,
            output=tmp_path / "samples.jsonl",
            interval_s=0,
        )


def test_run_with_rocm_smi_propagates_return_code_and_samples(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        run_with_rocm_smi,
        "_sample_once",
        lambda: {
            "card0": {
                "GPU use (%)": "12",
                "GPU Memory Allocated (VRAM%)": "34",
                "GPU Memory Read/Write Activity (%)": "5",
                "Average Graphics Package Power (W)": "67",
            }
        },
    )
    output = tmp_path / "samples.jsonl"
    return_code = run_with_rocm_smi.run_with_sampling(
        command=[
            sys.executable,
            "-c",
            "import time, sys; time.sleep(0.05); sys.exit(7)",
        ],
        gpu=0,
        output=output,
        interval_s=0.01,
    )

    assert return_code == 7
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert rows
    assert rows[0]["gpu_use_pct"] == 12.0
