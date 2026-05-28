from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

from mtp_expert_prefetch.tracing.vllm_router_trace import _filter_vllm_engine_kwargs


def test_filter_vllm_engine_kwargs_keeps_attention_config(monkeypatch) -> None:
    fake_arg_utils = ModuleType("vllm.engine.arg_utils")

    class EngineArgs:
        def __init__(
            self,
            model: str,
            *,
            attention_config: dict[str, Any] | None = None,
        ) -> None:
            self.model = model
            self.attention_config = attention_config

    fake_arg_utils.EngineArgs = EngineArgs
    monkeypatch.setitem(sys.modules, "vllm.engine.arg_utils", fake_arg_utils)

    filtered = _filter_vllm_engine_kwargs(
        {
            "model": "local-model",
            "attention_config": {"backend": "FLASH_ATTN"},
            "unsupported": True,
        }
    )

    assert filtered == {
        "model": "local-model",
        "attention_config": {"backend": "FLASH_ATTN"},
    }
