from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path


def iter_inline_texts(config: dict[str, Any]) -> Iterator[dict[str, Any]]:
    texts = config.get("texts", [])
    if not isinstance(texts, list):
        msg = "`texts` must be a list for inline material configs."
        raise TypeError(msg)

    max_samples = int(config.get("max_samples", len(texts)))
    for idx, text in enumerate(texts[:max_samples]):
        if not isinstance(text, str):
            msg = f"Inline text at index {idx} is not a string."
            raise TypeError(msg)
        yield {
            "id": f"{config.get('name', 'inline')}-{idx:06d}",
            "source": config.get("name", "inline"),
            "text": text,
            "meta": {"source_type": "inline", "index": idx},
        }


def render_text(row: dict[str, Any], config: dict[str, Any]) -> str | None:
    """Render a dataset row into the causal-LM text used for trace collection."""
    if "text_template" in config:
        try:
            return str(config["text_template"]).format(**row)
        except KeyError as exc:
            msg = f"Missing field for text_template: {exc}"
            raise KeyError(msg) from exc

    if "text_fields" in config:
        pieces = []
        for field in config["text_fields"]:
            value = row.get(field)
            if isinstance(value, str) and value.strip():
                pieces.append(value.strip())
        return "\n\n".join(pieces) if pieces else None

    text_field = config.get("text_field", "text")
    value = row.get(text_field)
    return value if isinstance(value, str) else None


def iter_huggingface_texts(config: dict[str, Any]) -> Iterator[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        msg = "Hugging Face material configs require `datasets`."
        raise RuntimeError(msg) from exc

    dataset_name = config["dataset_name"]
    subset = config.get("subset")
    split = config.get("split", "train")
    streaming = bool(config.get("streaming", True))
    max_samples = int(config.get("max_samples", 1024))

    dataset = load_dataset(dataset_name, subset, split=split, streaming=streaming)
    for idx, row in enumerate(dataset):
        if idx >= max_samples:
            break
        text = render_text(row, config)
        if not isinstance(text, str) or not text.strip():
            continue
        yield {
            "id": f"{config.get('name', dataset_name)}-{idx:06d}",
            "source": config.get("name", dataset_name),
            "text": text,
            "meta": {
                "source_type": "huggingface",
                "dataset_name": dataset_name,
                "subset": subset,
                "split": split,
                "index": idx,
                "language": row.get("language") or row.get("language_code"),
                "task_type": row.get("task_type"),
            },
        }


def iter_text_material(config: dict[str, Any]) -> Iterator[dict[str, Any]]:
    source = str(config.get("source", "inline")).lower()
    if source == "inline":
        yield from iter_inline_texts(config)
    elif source in {"hf", "huggingface", "datasets"}:
        yield from iter_huggingface_texts(config)
    else:
        msg = f"Unsupported material source: {source}"
        raise ValueError(msg)


def write_jsonl(records: Iterable[dict[str, Any]], output_path: str | Path) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def fetch_text_material(config_path: str | Path, output_path: str | Path | None = None) -> Path:
    config_path = Path(config_path)
    config = load_yaml(config_path)
    project_root = find_project_root(config_path)

    if output_path is None:
        name = config.get("name", config_path.stem)
        output_path = project_root / "data" / "raw" / f"{name}.jsonl"
    else:
        output_path = resolve_path(output_path, base_dir=project_root)

    count = write_jsonl(iter_text_material(config), output_path)
    if count == 0:
        msg = f"No text material was written from config: {config_path}"
        raise RuntimeError(msg)
    return Path(output_path)
