from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"expected object in {path}")
    return payload


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path | None = None,
) -> int:
    if log_path is None:
        return subprocess.run(cmd, cwd=str(cwd), env=env, check=False).returncode
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return int(process.returncode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("traceData/vllm_decode_block_table_v2/length_sweep_manifest.json"),
    )
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--only-lengths", nargs="*", type=int, default=None)
    parser.add_argument("--require-rows", type=int, default=1)
    parser.add_argument("--require-decode-only", action="store_true")
    parser.add_argument("--require-provenance", action="store_true")
    parser.add_argument("--require-kv-cache-layout-available", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    manifest_path = root / args.manifest
    manifest = _load_json(manifest_path)
    runs = manifest.get("runs")
    if not isinstance(runs, list):
        raise TypeError(f"manifest has no runs list: {manifest_path}")
    only_lengths = set(args.only_lengths or [])
    env = dict(os.environ)
    env["HIP_VISIBLE_DEVICES"] = str(int(args.gpu))
    env["CUDA_VISIBLE_DEVICES"] = str(int(args.gpu))
    env["PYTHONPATH"] = ".:src"
    output_rows: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            raise TypeError("manifest run must be object")
        prompt_length = int(run["prompt_length"])
        if only_lengths and prompt_length not in only_lengths:
            continue
        run_id = str(run["run_id"])
        trace_config = root / str(run["config"])
        trace_path = root / str(run["decode_trace"])
        check_path = trace_path.with_suffix(".check.json")
        log_path = manifest_path.parent / f"run_{run_id}.log"
        if args.skip_existing and trace_path.exists() and check_path.exists():
            print(f"[skip] {run_id} existing trace/check")
            output_rows.append(
                {
                    "run_id": run_id,
                    "prompt_length": prompt_length,
                    "trace": str(trace_path.relative_to(root)),
                    "check": str(check_path.relative_to(root)),
                    "log": str(log_path.relative_to(root)),
                    "skipped": True,
                }
            )
            continue
        print(f"[trace] {run_id} -> {trace_path}")
        trace_rc = _run(
            [args.python, "scripts/trace_router_mtp.py", str(trace_config)],
            cwd=root,
            env=env,
            log_path=log_path,
        )
        if trace_rc != 0:
            print(f"[error] {run_id} trace failed rc={trace_rc}; log={log_path}")
            return trace_rc
        print(f"[check] {run_id} -> {check_path}")
        check_cmd = [
            args.python,
            "scripts/check_vllm_decode_workload_trace.py",
            str(trace_path),
            "--summary-json",
            str(check_path),
            "--require-rows",
            str(int(args.require_rows)),
        ]
        if bool(args.require_decode_only):
            check_cmd.append("--require-decode-only")
        if bool(args.require_provenance):
            check_cmd.append("--require-provenance")
        if bool(args.require_kv_cache_layout_available):
            check_cmd.append("--require-kv-cache-layout-available")
        check_rc = _run(check_cmd, cwd=root, env=env)
        if check_rc != 0:
            print(f"[error] {run_id} check failed rc={check_rc}; check={check_path}")
            return check_rc
        output_rows.append(
            {
                "run_id": run_id,
                "prompt_length": prompt_length,
                "trace": str(trace_path.relative_to(root)),
                "check": str(check_path.relative_to(root)),
                "log": str(log_path.relative_to(root)),
                "skipped": False,
            }
        )
    status_path = manifest_path.parent / "v2_sweep_run_status.json"
    status_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "manifest": str(manifest_path.relative_to(root)),
                "gpu": int(args.gpu),
                "runs": output_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(status_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
