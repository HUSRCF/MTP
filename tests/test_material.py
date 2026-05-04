from pathlib import Path

from mtp_expert_prefetch.data.material import fetch_text_material


def test_fetch_inline_material(tmp_path: Path) -> None:
    config = tmp_path / "data.yaml"
    output = tmp_path / "material.jsonl"
    config.write_text(
        "\n".join(
            [
                "name: tiny",
                "source: inline",
                "max_samples: 2",
                "texts:",
                '  - "alpha"',
                '  - "beta"',
            ]
        ),
        encoding="utf-8",
    )

    result = fetch_text_material(config, output)

    lines = result.read_text(encoding="utf-8").splitlines()
    assert result == output
    assert len(lines) == 2
    assert '"text": "alpha"' in lines[0]

