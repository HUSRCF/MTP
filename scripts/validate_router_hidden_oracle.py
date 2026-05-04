#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PROJECT_SRC))

from mtp_expert_prefetch.evaluation import (  # noqa: E402
    analyze_router_hidden_oracle,
    write_router_hidden_oracle_report,
)
from mtp_expert_prefetch.utils.config import (  # noqa: E402
    find_project_root,
    load_yaml,
    resolve_path,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate same-token MoE router input hidden oracle traces."
    )
    parser.add_argument("config", type=Path)
    args = parser.parse_args()

    project_root = find_project_root(args.config)
    config = load_yaml(resolve_path(args.config, base_dir=project_root))
    manifest_path = resolve_path(config["manifest_path"], base_dir=project_root)
    output_path = resolve_path(config["output_path"], base_dir=project_root)

    report = analyze_router_hidden_oracle(manifest_path)
    write_router_hidden_oracle_report(report, output_path)
    result = report.as_dict()
    result["output_path"] = str(output_path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
