#!/usr/bin/env python3
"""Scan runtime gate YAML files with the evidence_paths checker."""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.check_gate_evidence_paths import check_gate_evidence_paths


def _path_label(path: Path, *, root: Path) -> str:
    path = path.resolve()
    root = root.resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


def _matching_gate_paths(pattern: str, *, root: Path) -> list[Path]:
    candidate = Path(pattern)
    raw_pattern = str(candidate if candidate.is_absolute() else root / candidate)
    return [Path(path) for path in sorted(glob.glob(raw_pattern))]


def _error_result(path: Path, *, root: Path, exc: Exception) -> dict[str, Any]:
    return {
        "gate_path": _path_label(path, root=root),
        "evidence_paths_section_missing": None,
        "evidence_path_count": 0,
        "missing_count": 0,
        "invalid_json_count": 0,
        "passed": False,
        "failures": [f"{type(exc).__name__}:{exc}"],
        "rows": [],
    }


def scan_runtime_gate_evidence_paths(
    pattern: str,
    *,
    root: Path,
    allow_missing: bool = True,
    allow_missing_section: bool = True,
    require_json: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    paths = _matching_gate_paths(pattern, root=root)
    results: list[dict[str, Any]] = []
    for path in paths:
        try:
            result = check_gate_evidence_paths(
                path,
                root=root,
                allow_missing=allow_missing,
                allow_missing_section=allow_missing_section,
                require_json=require_json,
            )
        except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
            result = _error_result(path, root=root, exc=exc)
        results.append(result)

    failures: list[str] = []
    pattern_failure_count = 0
    if not paths:
        failures.append(f"pattern_no_matches:{pattern}")
        pattern_failure_count = 1
    for result in results:
        if not result.get("passed", False):
            gate_path = str(result.get("gate_path", "<unknown>"))
            gate_failures = result.get("failures") or ["unknown_failure"]
            for failure in gate_failures:
                failures.append(f"{gate_path}:{failure}")

    evidence_section_present = sum(
        result.get("evidence_paths_section_missing") is False for result in results
    )
    evidence_section_missing = sum(
        result.get("evidence_paths_section_missing") is True for result in results
    )
    return {
        "pattern": pattern,
        "gate_count": len(results),
        "passed_gate_count": sum(result.get("passed", False) for result in results),
        "failed_gate_count": sum(not result.get("passed", False) for result in results),
        "pattern_failure_count": pattern_failure_count,
        "evidence_section_present_count": evidence_section_present,
        "evidence_section_missing_count": evidence_section_missing,
        "evidence_path_count": sum(
            int(result.get("evidence_path_count", 0)) for result in results
        ),
        "missing_count": sum(int(result.get("missing_count", 0)) for result in results),
        "invalid_json_count": sum(
            int(result.get("invalid_json_count", 0)) for result in results
        ),
        "passed": not failures,
        "failures": failures,
        "results": results,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", default="configs/runtime/*.yaml")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any evidence path is missing.",
    )
    parser.add_argument(
        "--require-evidence-section",
        action="store_true",
        help="Fail if a scanned YAML file has no evidence_paths section.",
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
    result = scan_runtime_gate_evidence_paths(
        args.pattern,
        root=args.root,
        allow_missing=not args.strict,
        allow_missing_section=not args.require_evidence_section,
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
