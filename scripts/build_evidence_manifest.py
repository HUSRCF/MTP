#!/usr/bin/env python3
"""Build a reproducible evidence manifest for experiment artifacts.

The manifest records content hashes for both files and directories.  Directory
hashes are tree digests over every contained file's relative path, size, and
SHA256 digest, so the artifact identity changes if any report file changes.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_directory(
    path: Path,
    *,
    exclude_paths: set[Path] | None = None,
) -> dict[str, Any]:
    excludes = {p.resolve() for p in exclude_paths or set()}
    files = sorted(
        p for p in path.rglob("*") if p.is_file() and p.resolve() not in excludes
    )
    digest = hashlib.sha256()
    file_rows: list[dict[str, Any]] = []
    for file_path in files:
        rel = file_path.relative_to(path).as_posix()
        file_digest = _sha256_file(file_path)
        size = file_path.stat().st_size
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
        file_rows.append(
            {
                "relative_path": rel,
                "size_bytes": size,
                "sha256": file_digest,
            }
        )
    return {
        "type": "directory",
        "sha256": digest.hexdigest(),
        "file_count": len(file_rows),
        "size_bytes": sum(int(row["size_bytes"]) for row in file_rows),
        "files": file_rows,
    }


def _parse_entry(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError(
            f"Invalid entry {raw!r}; expected LABEL=PATH."
        )
    label, path = raw.split("=", 1)
    label = label.strip()
    path = path.strip()
    if not label:
        raise argparse.ArgumentTypeError(f"Invalid entry {raw!r}; empty label.")
    if not path:
        raise argparse.ArgumentTypeError(f"Invalid entry {raw!r}; empty path.")
    return label, path


def build_manifest(
    entries: list[tuple[str, str]],
    *,
    root: Path,
    title: str,
    boundaries: list[str] | None = None,
    allow_missing: bool = False,
    exclude_paths: set[Path] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for label, raw_path in entries:
        candidate = Path(raw_path)
        path = candidate if candidate.is_absolute() else root / candidate
        rel_path = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        row: dict[str, Any] = {
            "label": label,
            "path": rel_path,
            "exists": path.exists(),
        }
        if not path.exists():
            row["type"] = "missing"
            missing.append(f"{label}={raw_path}")
        elif path.is_file():
            row.update(
                {
                    "type": "file",
                    "sha256": _sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        elif path.is_dir():
            row.update(_hash_directory(path, exclude_paths=exclude_paths))
        else:
            row["type"] = "unsupported"
            missing.append(f"{label}={raw_path}")
        rows.append(row)

    if missing and not allow_missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(f"Missing or unsupported evidence entries: {joined}")

    return {
        "title": title,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "root": str(root),
        "boundaries": list(boundaries or []),
        "entries": rows,
        "missing_count": len(missing),
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        f"# {manifest['title']}",
        "",
        f"Generated UTC: `{manifest['generated_at_utc']}`",
        "",
        f"Root: `{manifest['root']}`",
        "",
    ]
    boundaries = manifest.get("boundaries") or []
    if boundaries:
        lines.extend(["## Evidence Boundaries", ""])
        lines.extend(f"- {boundary}" for boundary in boundaries)
        lines.append("")
    lines.extend(
        [
            "## Entries",
            "",
            "| label | path | type | sha256 | files | size_bytes |",
            "|---|---|---:|---|---:|---:|",
        ]
    )
    for row in manifest["entries"]:
        sha = row.get("sha256", "")
        short_sha = f"`{sha}`" if sha else ""
        files = row.get("file_count", "")
        size = row.get("size_bytes", "")
        lines.append(
            f"| `{row['label']}` | `{row['path']}` | {row['type']} | "
            f"{short_sha} | {files} | {size} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--title", default="Experiment Evidence Manifest")
    parser.add_argument("--entry", action="append", type=_parse_entry, required=True)
    parser.add_argument("--boundary", action="append", default=[])
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    manifest = build_manifest(
        args.entry,
        root=args.root,
        title=args.title,
        boundaries=args.boundary,
        allow_missing=args.allow_missing,
        exclude_paths={
            args.output_json.resolve(),
            *(set() if args.output_md is None else {args.output_md.resolve()}),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(manifest), encoding="utf-8")


if __name__ == "__main__":
    main()
