from scripts import sample_rocm_smi


def test_parse_number_handles_numeric_and_na() -> None:
    assert sample_rocm_smi._parse_number("17.0") == 17.0
    assert sample_rocm_smi._parse_number("0") == 0.0
    assert sample_rocm_smi._parse_number("N/A") is None
    assert sample_rocm_smi._parse_number(None) is None


def test_card_row_extracts_known_rocm_smi_fields() -> None:
    raw = {
        "card1": {
            "Average Graphics Package Power (W)": "42.5",
            "GPU use (%)": "77",
            "GPU Memory Allocated (VRAM%)": "63",
            "GPU Memory Read/Write Activity (%)": "12",
        }
    }
    row = sample_rocm_smi._card_row(raw, 1)
    assert row["gpu"] == 1
    assert row["gpu_use_pct"] == 77.0
    assert row["vram_allocated_pct"] == 63.0
    assert row["mem_rw_activity_pct"] == 12.0
    assert row["avg_graphics_power_w"] == 42.5

