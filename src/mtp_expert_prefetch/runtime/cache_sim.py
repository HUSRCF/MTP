from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from mtp_expert_prefetch.runtime.premap import ExpertPrefetchDescriptor


@dataclass(frozen=True)
class DescriptorCacheReport:
    capacity_per_layer: int
    expert_bytes: int
    num_descriptors: int
    hits: int
    misses: int
    evictions: int
    skipped: int
    hit_rate: float
    load_bytes: int
    skipped_bytes: int
    evicted_bytes: int
    by_priority: dict[str, dict[str, int | float]]
    by_source: dict[str, dict[str, int | float]]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def load_descriptor_jsonl(path: str | Path) -> list[ExpertPrefetchDescriptor]:
    descriptors = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            descriptors.append(
                ExpertPrefetchDescriptor(
                    sample_idx=int(item["sample_idx"]),
                    layer_idx=int(item["layer_idx"]),
                    expert_id=int(item["expert_id"]),
                    priority=int(item["priority"]),
                    source=str(item["source"]),
                    score=float(item["score"]),
                )
            )
    return descriptors


def simulate_descriptor_lru_cache(
    descriptors: Iterable[ExpertPrefetchDescriptor],
    *,
    capacity_per_layer: int,
    expert_bytes: int = 1_650_000,
    transfer_budget_bytes_per_sample_layer: int | None = None,
) -> DescriptorCacheReport:
    capacity_per_layer = int(capacity_per_layer)
    if capacity_per_layer <= 0:
        msg = "capacity_per_layer must be positive."
        raise ValueError(msg)
    layer_caches: dict[int, OrderedDict[int, None]] = {}
    hits = 0
    misses = 0
    evictions = 0
    skipped = 0
    by_priority: dict[str, dict[str, int]] = {}
    by_source: dict[str, dict[str, int]] = {}
    num_descriptors = 0
    current_group: tuple[int, int] | None = None
    group_loaded_bytes = 0

    sorted_descriptors = sorted(
        list(descriptors),
        key=lambda item: (
            item.sample_idx,
            item.layer_idx,
            item.priority,
            -item.score,
            item.expert_id,
        ),
    )
    for descriptor in sorted_descriptors:
        group = (descriptor.sample_idx, descriptor.layer_idx)
        if group != current_group:
            current_group = group
            group_loaded_bytes = 0
        num_descriptors += 1
        cache = layer_caches.setdefault(descriptor.layer_idx, OrderedDict())
        priority_bucket = by_priority.setdefault(str(descriptor.priority), _empty_counts())
        source_bucket = by_source.setdefault(descriptor.source, _empty_counts())
        if descriptor.expert_id in cache:
            hits += 1
            priority_bucket["hits"] += 1
            source_bucket["hits"] += 1
            cache.move_to_end(descriptor.expert_id)
            continue

        if (
            transfer_budget_bytes_per_sample_layer is not None
            and group_loaded_bytes + int(expert_bytes)
            > int(transfer_budget_bytes_per_sample_layer)
        ):
            skipped += 1
            priority_bucket["skipped"] += 1
            source_bucket["skipped"] += 1
            continue

        misses += 1
        priority_bucket["misses"] += 1
        source_bucket["misses"] += 1
        group_loaded_bytes += int(expert_bytes)
        if len(cache) >= capacity_per_layer:
            cache.popitem(last=False)
            evictions += 1
            priority_bucket["evictions"] += 1
            source_bucket["evictions"] += 1
        cache[descriptor.expert_id] = None

    report_priority = _finalize_counts(by_priority)
    report_source = _finalize_counts(by_source)
    return DescriptorCacheReport(
        capacity_per_layer=capacity_per_layer,
        expert_bytes=int(expert_bytes),
        num_descriptors=num_descriptors,
        hits=hits,
        misses=misses,
        evictions=evictions,
        skipped=skipped,
        hit_rate=hits / max(1, num_descriptors),
        load_bytes=int(misses * expert_bytes),
        skipped_bytes=int(skipped * expert_bytes),
        evicted_bytes=int(evictions * expert_bytes),
        by_priority=report_priority,
        by_source=report_source,
    )


def simulate_descriptor_priority_cache(
    descriptors: Iterable[ExpertPrefetchDescriptor],
    *,
    capacity_per_layer: int,
    expert_bytes: int = 1_650_000,
    transfer_budget_bytes_per_sample_layer: int | None = None,
    protected_max_priority: int = 3,
) -> DescriptorCacheReport:
    """Simulate an LRU cache where MTP extras cannot evict transition entries.

    Priorities numerically less than or equal to `protected_max_priority`
    represent protected candidates, currently P2/P3 transition entries. A less
    important candidate such as P4/P5 may only evict another unprotected entry.
    Protected incoming candidates can evict any LRU entry, preferring
    unprotected entries when one exists.
    """
    capacity_per_layer = int(capacity_per_layer)
    if capacity_per_layer <= 0:
        msg = "capacity_per_layer must be positive."
        raise ValueError(msg)
    protected_max_priority = int(protected_max_priority)

    layer_caches: dict[int, OrderedDict[int, int]] = {}
    hits = 0
    misses = 0
    evictions = 0
    skipped = 0
    by_priority: dict[str, dict[str, int]] = {}
    by_source: dict[str, dict[str, int]] = {}
    num_descriptors = 0
    current_group: tuple[int, int] | None = None
    group_loaded_bytes = 0

    sorted_descriptors = sorted(
        list(descriptors),
        key=lambda item: (
            item.sample_idx,
            item.layer_idx,
            item.priority,
            -item.score,
            item.expert_id,
        ),
    )
    for descriptor in sorted_descriptors:
        group = (descriptor.sample_idx, descriptor.layer_idx)
        if group != current_group:
            current_group = group
            group_loaded_bytes = 0
        num_descriptors += 1
        cache = layer_caches.setdefault(descriptor.layer_idx, OrderedDict())
        priority_bucket = by_priority.setdefault(str(descriptor.priority), _empty_counts())
        source_bucket = by_source.setdefault(descriptor.source, _empty_counts())

        if descriptor.expert_id in cache:
            hits += 1
            priority_bucket["hits"] += 1
            source_bucket["hits"] += 1
            cache[descriptor.expert_id] = min(
                int(cache[descriptor.expert_id]),
                int(descriptor.priority),
            )
            cache.move_to_end(descriptor.expert_id)
            continue

        if (
            transfer_budget_bytes_per_sample_layer is not None
            and group_loaded_bytes + int(expert_bytes)
            > int(transfer_budget_bytes_per_sample_layer)
        ):
            skipped += 1
            priority_bucket["skipped"] += 1
            source_bucket["skipped"] += 1
            continue

        evict_key: int | None = None
        if len(cache) >= capacity_per_layer:
            evict_key = _select_priority_eviction_key(
                cache,
                incoming_priority=int(descriptor.priority),
                protected_max_priority=protected_max_priority,
            )
            if evict_key is None:
                skipped += 1
                priority_bucket["skipped"] += 1
                source_bucket["skipped"] += 1
                continue

        misses += 1
        priority_bucket["misses"] += 1
        source_bucket["misses"] += 1
        group_loaded_bytes += int(expert_bytes)
        if evict_key is not None:
            del cache[evict_key]
            evictions += 1
            priority_bucket["evictions"] += 1
            source_bucket["evictions"] += 1
        cache[descriptor.expert_id] = int(descriptor.priority)

    report_priority = _finalize_counts(by_priority)
    report_source = _finalize_counts(by_source)
    return DescriptorCacheReport(
        capacity_per_layer=capacity_per_layer,
        expert_bytes=int(expert_bytes),
        num_descriptors=num_descriptors,
        hits=hits,
        misses=misses,
        evictions=evictions,
        skipped=skipped,
        hit_rate=hits / max(1, num_descriptors),
        load_bytes=int(misses * expert_bytes),
        skipped_bytes=int(skipped * expert_bytes),
        evicted_bytes=int(evictions * expert_bytes),
        by_priority=report_priority,
        by_source=report_source,
    )


def _select_priority_eviction_key(
    cache: OrderedDict[int, int],
    *,
    incoming_priority: int,
    protected_max_priority: int,
) -> int | None:
    unprotected_keys = [
        expert_id
        for expert_id, priority in cache.items()
        if int(priority) > int(protected_max_priority)
    ]
    if int(incoming_priority) > int(protected_max_priority):
        return unprotected_keys[0] if unprotected_keys else None
    if unprotected_keys:
        return unprotected_keys[0]
    return next(iter(cache), None)


def write_descriptor_cache_report(report: DescriptorCacheReport, output: str | Path) -> Path:
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def _empty_counts() -> dict[str, int]:
    return {"hits": 0, "misses": 0, "evictions": 0, "skipped": 0}


def _finalize_counts(
    buckets: dict[str, dict[str, int]],
) -> dict[str, dict[str, int | float]]:
    result = {}
    for name, counts in buckets.items():
        admitted = int(counts["hits"] + counts["misses"])
        total = int(admitted + counts["skipped"])
        result[name] = {
            "hits": int(counts["hits"]),
            "misses": int(counts["misses"]),
            "evictions": int(counts["evictions"]),
            "skipped": int(counts["skipped"]),
            "total": total,
            "hit_rate": counts["hits"] / max(1, admitted),
            "admitted_rate": admitted / max(1, total),
        }
    return result
