from __future__ import annotations

import importlib.util
import os
from importlib.machinery import ModuleSpec
from typing import Any


if os.environ.get("MTP_PREFETCH_DISABLE_FLASH_ATTN_PROBE") == "1":
    _original_find_spec = importlib.util.find_spec

    def _find_spec_without_flash_attn(
        name: str,
        package: str | None = None,
    ) -> ModuleSpec | None:
        if name == "flash_attn" or name.startswith("flash_attn."):
            return None
        return _original_find_spec(name, package)

    importlib.util.find_spec = _find_spec_without_flash_attn  # type: ignore[assignment]
