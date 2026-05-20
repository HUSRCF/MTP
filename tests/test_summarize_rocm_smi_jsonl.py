import json

from scripts import summarize_rocm_smi_jsonl


def test_summarize_rocm_smi_jsonl_fields(tmp_path) -> None:
    path = tmp_path / "samples.jsonl"
    rows = [
        {
            "ok": True,
            "elapsed_s": 0.0,
            "gpu_use_pct": 10,
            "vram_allocated_pct": 50,
            "mem_rw_activity_pct": 3,
            "avg_graphics_power_w": 20,
        },
        {
            "ok": True,
            "elapsed_s": 1.0,
            "gpu_use_pct": 30,
            "vram_allocated_pct": 60,
            "mem_rw_activity_pct": 5,
            "avg_graphics_power_w": 40,
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    summary = summarize_rocm_smi_jsonl.summarize(path)

    assert summary["row_count"] == 2
    assert summary["ok_count"] == 2
    assert summary["fields"]["gpu_use_pct"]["mean"] == 20
    assert summary["fields"]["vram_allocated_pct"]["p50"] == 55


def test_summarize_rocm_smi_jsonl_elapsed_filter(tmp_path) -> None:
    path = tmp_path / "samples.jsonl"
    rows = [
        {"ok": True, "elapsed_s": 0.0, "gpu_use_pct": 10},
        {"ok": True, "elapsed_s": 5.0, "gpu_use_pct": 90},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    summary = summarize_rocm_smi_jsonl.summarize(path, elapsed_min_s=1.0)

    assert summary["row_count"] == 1
    assert summary["fields"]["gpu_use_pct"]["mean"] == 90
