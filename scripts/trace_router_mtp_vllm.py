from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PROJECT_SRC))

from mtp_expert_prefetch.tracing.vllm_router_trace import trace_router_mtp_vllm  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace Qwen3.6 MoE router top-k with vLLM.")
    parser.add_argument("config", help="Path to a vLLM router trace YAML config.")
    args = parser.parse_args()
    manifest_path = trace_router_mtp_vllm(args.config)
    print(manifest_path)


if __name__ == "__main__":
    main()
