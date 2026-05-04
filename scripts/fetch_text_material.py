from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.data.material import fetch_text_material


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch or materialize text data into JSONL.")
    parser.add_argument("config", type=Path, help="Data config YAML.")
    parser.add_argument("--output", type=Path, default=None, help="Output JSONL path.")
    args = parser.parse_args()

    output_path = fetch_text_material(args.config, args.output)
    print(output_path)


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
