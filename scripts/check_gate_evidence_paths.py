#!/usr/bin/env python3
"""Validate evidence_paths entries in a gate artifact YAML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def _resolve_path(root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    return candidate if candidate.is_absolute() else root / candidate


def check_gate_evidence_paths(
    gate_path: Path,
    *,
    root: Path,
    allow_missing: bool = False,
    require_json: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    gate_path = gate_path if gate_path.is_absolute() else root / gate_path
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    if not isinstance(gate, dict):
        raise ValueError(f"Gate artifact must be a mapping: {gate_path}")
    evidence_paths = gate.get("evidence_paths")
    if not isinstance(evidence_paths, dict):
        raise ValueError(f"Gate artifact has no evidence_paths mapping: {gate_path}")

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for label, raw_path in sorted(evidence_paths.items()):
        if not isinstance(label, str) or not isinstance(raw_path, str):
            failures.append(f"{label}:invalid_entry")
            rows.append(
                {
                    "label": str(label),
                    "path": str(raw_path),
                    "exists": False,
                    "valid_json": None,
                    "failure": "invalid_entry",
                }
            )
            continue

        path = _resolve_path(root, raw_path)
        row: dict[str, Any] = {
            "label": label,
            "path": raw_path,
            "exists": path.exists(),
            "valid_json": None,
        }
        if not path.exists():
            if not allow_missing:
                failures.append(f"{label}:missing")
                row["failure"] = "missing"
            rows.append(row)
            continue
        if not path.is_file():
            failures.append(f"{label}:not_file")
            row["failure"] = "not_file"
            rows.append(row)
            continue

        row["size_bytes"] = path.stat().st_size
        should_parse_json = require_json and raw_path.endswith(".json")
        if should_parse_json:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append(f"{label}:invalid_json")
                row["valid_json"] = False
                row["failure"] = f"invalid_json:{exc.msg}"
            else:
                row["valid_json"] = True
        rows.append(row)

    return {
        "gate_path": gate_path.relative_to(root).as_posix()
        if gate_path.is_relative_to(root)
        else str(gate_path),
        "evidence_path_count": len(rows),
        "missing_count": sum(1 for row in rows if not row["exists"]),
        "invalid_json_count": sum(row["valid_json"] is False for row in rows),
        "passed": not failures,
        "failures": failures,
        "rows": rows,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gate_path", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    missing_group = parser.add_mutually_exclusive_group()
    missing_group.add_argument(
        "--strict",
        action="store_true",
        help="Fail if an evidence path is missing. CLI default allows missing paths.",
    )
    missing_group.add_argument(
        "--allow-missing",
        action="store_true",
        help="Allow missing evidence paths. This is the CLI default.",
    )
    parser.add_argument(
        "--require-json",
        action="store_true",
        help="Parse evidence paths ending in .json and fail if they are invalid.",
    )
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_gate_evidence_paths(
        args.gate_path,
        root=args.root,
        allow_missing=not args.strict,
        require_json=args.require_json,
    )
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
