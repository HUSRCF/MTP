from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def find_project_root(start: str | Path | None = None) -> Path:
    """Find the nearest parent containing pyproject.toml."""
    current = Path(start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for path in (current, *current.parents):
        if (path / "pyproject.toml").exists():
            return path

    return current


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        msg = f"Expected a mapping in YAML config: {path}"
        raise TypeError(msg)
    return data


def resolve_path(path: str | Path, *, base_dir: str | Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (Path(base_dir) if base_dir else find_project_root()) / candidate

