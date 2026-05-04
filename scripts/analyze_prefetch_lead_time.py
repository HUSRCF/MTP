#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    analyze_descriptor_lead_time,
    load_descriptor_jsonl,
    write_lead_time_report,
)
from mtp_expert_prefetch.utils.config import find_project_root, resolve_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate whether prefetch descriptors have enough lead time before demand."
    )
    parser.add_argument("descriptors", type=Path, help="Descriptor JSONL from export_prefetch_premap_descriptors.py")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/lead_time_report.json"),
    )
    parser.add_argument("--num-layers", type=int, default=40)
    parser.add_argument("--layer-ms", type=float, default=1.0)
    parser.add_argument("--sampling-ms", type=float, default=0.0)
    parser.add_argument(
        "--mtp-delay-ms",
        type=float,
        default=0.0,
        help="Delay after token-t routing before MTP-token extras become available.",
    )
    parser.add_argument("--bandwidth-gbps", type=float, default=16.0)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.descriptors)
    descriptors_path = resolve_path(args.descriptors, base_dir=project_root)
    output = resolve_path(args.output, base_dir=project_root)
    descriptors = load_descriptor_jsonl(descriptors_path)
    report = analyze_descriptor_lead_time(
        descriptors,
        num_layers=int(args.num_layers),
        layer_ms=float(args.layer_ms),
        sampling_ms=float(args.sampling_ms),
        mtp_delay_ms=float(args.mtp_delay_ms),
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
    )
    write_lead_time_report(report, output)
    payload = report.as_dict()
    payload.update(
        {
            "ok": True,
            "descriptors": str(descriptors_path),
            "output": str(output),
        }
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
