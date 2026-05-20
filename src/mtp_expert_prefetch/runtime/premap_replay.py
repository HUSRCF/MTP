from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from mtp_expert_prefetch.runtime.cache_manager import ControlledPremapAddressManager
from mtp_expert_prefetch.runtime.premap import (
    ExpertPrefetchDescriptor,
    prepare_premap_address_plan,
)


@dataclass(frozen=True)
class PremapAddressReplayReport:
    capacity: int | None
    event_count: int
    descriptor_count: int
    new_address_count: int
    reused_address_count: int
    reuse_rate: float
    evicted_address_count: int
    eviction_pressure: float
    resident_address_count: int
    resident_descriptor_bytes: int
    prepared_descriptor_actual_bytes: int
    payload_bytes: int
    max_resident_address_count: int
    max_resident_descriptor_bytes: int

    def as_dict(self) -> dict[str, int | float | None]:
        return asdict(self)


def load_premap_descriptor_jsonl(path: str | Path) -> list[ExpertPrefetchDescriptor]:
    descriptors: list[ExpertPrefetchDescriptor] = []
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            try:
                descriptors.append(
                    ExpertPrefetchDescriptor(
                        sample_idx=int(row["sample_idx"]),
                        layer_idx=int(row["layer_idx"]),
                        expert_id=int(row["expert_id"]),
                        priority=int(row["priority"]),
                        source=str(row["source"]),
                        score=float(row.get("score", 0.0)),
                    )
                )
            except KeyError as exc:
                msg = f"Missing descriptor field {exc.args[0]!r} at {path}:{line_number}"
                raise ValueError(msg) from exc
    return descriptors


def group_premap_descriptors_by_sample_layer(
    descriptors: Iterable[ExpertPrefetchDescriptor],
) -> list[list[ExpertPrefetchDescriptor]]:
    grouped: dict[tuple[int, int], list[ExpertPrefetchDescriptor]] = {}
    for descriptor in descriptors:
        key = (int(descriptor.sample_idx), int(descriptor.layer_idx))
        grouped.setdefault(key, []).append(descriptor)
    return list(grouped.values())


def replay_premap_address_manager(
    descriptor_groups: Iterable[list[ExpertPrefetchDescriptor]],
    *,
    capacity: int | None,
    descriptor_bytes: int = 4_096,
    address_namespace: str = "expert_weight_descriptor",
) -> PremapAddressReplayReport:
    manager = ControlledPremapAddressManager(capacity=capacity)
    event_count = 0
    max_resident_address_count = 0
    max_resident_descriptor_bytes = 0
    for group in descriptor_groups:
        event_count += 1
        plan = prepare_premap_address_plan(
            group,
            descriptor_bytes=descriptor_bytes,
            address_namespace=address_namespace,
        )
        snapshot = manager.prepare(plan)
        max_resident_address_count = max(
            max_resident_address_count,
            int(snapshot.resident_address_count),
        )
        max_resident_descriptor_bytes = max(
            max_resident_descriptor_bytes,
            int(snapshot.resident_descriptor_bytes),
        )
    final = manager.snapshot()
    descriptor_count = int(final.prepared_record_count)
    reuse_rate = (
        float(final.reused_address_count) / float(descriptor_count)
        if descriptor_count > 0
        else 0.0
    )
    eviction_pressure = (
        float(final.evicted_address_count) / float(max(1, final.new_address_count))
        if final.new_address_count > 0
        else 0.0
    )
    return PremapAddressReplayReport(
        capacity=capacity,
        event_count=event_count,
        descriptor_count=descriptor_count,
        new_address_count=int(final.new_address_count),
        reused_address_count=int(final.reused_address_count),
        reuse_rate=reuse_rate,
        evicted_address_count=int(final.evicted_address_count),
        eviction_pressure=eviction_pressure,
        resident_address_count=int(final.resident_address_count),
        resident_descriptor_bytes=int(final.resident_descriptor_bytes),
        prepared_descriptor_actual_bytes=int(final.prepared_descriptor_actual_bytes),
        payload_bytes=int(final.payload_bytes),
        max_resident_address_count=max_resident_address_count,
        max_resident_descriptor_bytes=max_resident_descriptor_bytes,
    )
