from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.tracing.router_mtp import trace_router_mtp


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect router/MTP traces from a frozen model.")
    parser.add_argument("config", type=Path, help="Trace config YAML.")
    args = parser.parse_args()

    manifest_path = trace_router_mtp(args.config)
    print(manifest_path)


if __name__ == "__main__":
    main()
