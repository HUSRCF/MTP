from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowOutcomeEvent,
    ShadowSummaryEvent,
    aggregate_shadow_events,
    read_shadow_jsonl,
)


class OnlineShadowLogger:
    """Append-only runtime shadow logger using the canonical JSONL schema.

    Serving/runtime integrations should write one `ShadowSummaryEvent` when an
    action decision is made and one `ShadowOutcomeEvent` after the true router
    result is known. This class intentionally does not make policy decisions;
    it only preserves the schema used by offline replay.
    """

    def __init__(self, path: str | Path, *, flush_every: int = 1) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.flush_every = max(1, int(flush_every))
        self._handle = self.path.open("a", encoding="utf-8")
        self._pending = 0
        self._closed = False

    def write_summary(self, event: ShadowSummaryEvent) -> None:
        self.write_event(event)

    def write_outcome(self, event: ShadowOutcomeEvent) -> None:
        self.write_event(event)

    def write_event(self, event: ShadowSummaryEvent | ShadowOutcomeEvent | dict[str, Any]) -> None:
        if self._closed:
            msg = "Cannot write to a closed OnlineShadowLogger."
            raise RuntimeError(msg)
        payload = event.as_dict() if hasattr(event, "as_dict") else dict(event)
        self._handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        self._pending += 1
        if self._pending >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        if self._closed:
            return
        self._handle.flush()
        self._pending = 0

    def close(self) -> None:
        if self._closed:
            return
        self.flush()
        self._handle.close()
        self._closed = True

    def aggregate(self) -> dict[str, Any]:
        self.flush()
        return aggregate_shadow_events(read_shadow_jsonl(self.path))

    def __enter__(self) -> OnlineShadowLogger:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
