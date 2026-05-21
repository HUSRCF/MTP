from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import asdict, dataclass

from mtp_expert_prefetch.runtime.premap import PremapAddressRecord, PremapPreparedPlan


@dataclass
class CacheManagerEntry:
    prefetched: bool
    used: bool = False


@dataclass(frozen=True)
class CacheManagerSnapshot:
    capacity: int
    resident_count: int
    issued_fetch_count: int
    used_fetch_count: int
    unused_fetch_count: int
    demand_count: int
    demand_hit_count: int
    demand_miss_count: int
    evicted_before_use_count: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class ControlledExpertCacheManager:
    """Bounded LRU expert-payload cache used by cache-lab runtime prototypes."""

    def __init__(self, *, capacity: int) -> None:
        self.capacity = int(capacity)
        self._cache: OrderedDict[tuple[int, int], CacheManagerEntry] = OrderedDict()
        self.issued_fetch_count = 0
        self.used_fetch_count = 0
        self.demand_count = 0
        self.demand_hit_count = 0
        self.demand_miss_count = 0
        self.evicted_before_use_count = 0

    def issue_prefetch(self, layer_idx: int, expert_idx: int) -> bool:
        """Issue a prefetch if the expert payload is not already resident."""

        key = (int(layer_idx), int(expert_idx))
        if key in self._cache:
            self._cache.move_to_end(key)
            return False
        self.issued_fetch_count += 1
        self._insert(key, CacheManagerEntry(prefetched=True, used=False))
        return True

    def demand(self, layer_idx: int, expert_idx: int) -> bool:
        """Consume a demanded expert payload and return whether it was resident."""

        self.demand_count += 1
        key = (int(layer_idx), int(expert_idx))
        entry = self._cache.get(key)
        if entry is None:
            self.demand_miss_count += 1
            self._insert(key, CacheManagerEntry(prefetched=False, used=True))
            return False
        self.demand_hit_count += 1
        if entry.prefetched and not entry.used:
            self.used_fetch_count += 1
        entry.used = True
        self._cache.move_to_end(key)
        return True

    def snapshot(self) -> CacheManagerSnapshot:
        unused_fetch_count = sum(
            1 for entry in self._cache.values() if entry.prefetched and not entry.used
        )
        return CacheManagerSnapshot(
            capacity=self.capacity,
            resident_count=len(self._cache),
            issued_fetch_count=self.issued_fetch_count,
            used_fetch_count=self.used_fetch_count,
            unused_fetch_count=unused_fetch_count,
            demand_count=self.demand_count,
            demand_hit_count=self.demand_hit_count,
            demand_miss_count=self.demand_miss_count,
            evicted_before_use_count=self.evicted_before_use_count,
        )

    def _insert(
        self,
        key: tuple[int, int],
        entry: CacheManagerEntry,
    ) -> None:
        if self.capacity <= 0:
            if entry.prefetched and not entry.used:
                self.evicted_before_use_count += 1
            return
        self._cache[key] = entry
        self._cache.move_to_end(key)
        while len(self._cache) > self.capacity:
            _, old = self._cache.popitem(last=False)
            if old.prefetched and not old.used:
                self.evicted_before_use_count += 1


@dataclass(frozen=True)
class PremapAddressHandle:
    """Stable descriptor/address object for a prepared expert address key.

    This is intentionally a descriptor/metadata handle, not a payload handle:
    it records enough information for a consumer to resolve packed-weight and
    scale/metadata descriptors without modeling expert weight transfer.
    """

    address_key: str
    layer_idx: int
    expert_id: int
    descriptor_bytes: int
    descriptor_ptr: str
    packed_weight_descriptor: str
    scale_metadata_handle: str
    payload_bytes: int = 0

    @classmethod
    def from_record(cls, record: PremapAddressRecord) -> PremapAddressHandle:
        address_key = str(record.address_key)
        return cls(
            address_key=address_key,
            layer_idx=int(record.layer_idx),
            expert_id=int(record.expert_id),
            descriptor_bytes=int(record.descriptor_bytes),
            descriptor_ptr=f"descriptor://{address_key}",
            packed_weight_descriptor=f"packed_weight_descriptor://{address_key}",
            scale_metadata_handle=f"scale_metadata://{address_key}",
            payload_bytes=0,
        )

    @property
    def handle_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | str]:
        return asdict(self)


@dataclass
class PremapAddressCacheEntry:
    descriptor_bytes: int
    handle: PremapAddressHandle
    prepared_count: int = 1


@dataclass(frozen=True)
class PremapAddressManagerSnapshot:
    capacity: int | None
    resident_address_count: int
    prepared_plan_count: int
    prepared_record_count: int
    new_address_count: int
    reused_address_count: int
    evicted_address_count: int
    prepared_descriptor_actual_bytes: int
    resident_descriptor_bytes: int
    payload_bytes: int

    def as_dict(self) -> dict[str, int | None]:
        return asdict(self)


@dataclass(frozen=True)
class PremapReadonlyConsumerResult:
    """Read-only consumer lookup result for prepared descriptor handles.

    The consumer path intentionally does not mutate cache residency or mark
    experts ready.  It only checks whether an already prepared address key can
    still resolve to the expected descriptor/address handle.
    """

    lookup_count: int
    handle_hit_count: int
    handle_miss_count: int
    evicted_before_consume_count: int
    stale_handle_count: int
    handle_parity_ok: bool | None

    def as_dict(self) -> dict[str, int | bool | None]:
        return asdict(self)


class ControlledPremapAddressManager:
    """Bounded descriptor/address shim for premap-only runtime prototypes.

    This manager tracks descriptor/address handles prepared from
    `PremapPreparedPlan`. It intentionally never moves expert payload bytes and
    never marks experts ready; it only models descriptor/address residency and
    reuse for the lower-risk premap action path.
    """

    def __init__(self, *, capacity: int | None = None) -> None:
        self.capacity = None if capacity is None else int(capacity)
        self._addresses: OrderedDict[str, PremapAddressCacheEntry] = OrderedDict()
        # Manager-lifetime eviction history.  The vLLM shadow recorder keeps
        # this manager across `clear()` calls to model a long-lived descriptor
        # cache, so an evicted-before-consume count means the current consumer
        # asks for a key that was prepared earlier in this manager lifetime and
        # later evicted before being prepared again.
        self._evicted_address_keys: set[str] = set()
        self.prepared_plan_count = 0
        self.prepared_record_count = 0
        self.new_address_count = 0
        self.reused_address_count = 0
        self.evicted_address_count = 0
        self.prepared_descriptor_actual_bytes = 0
        self.payload_bytes = 0

    def prepare(self, plan: PremapPreparedPlan) -> PremapAddressManagerSnapshot:
        """Prepare descriptor/address handles from a plan and return a snapshot."""

        self.prepared_plan_count += 1
        self.prepared_record_count += int(plan.descriptor_count)
        self.prepared_descriptor_actual_bytes += int(plan.actual_bytes)
        self.payload_bytes += int(plan.payload_bytes)
        for record in plan.records:
            key = str(record.address_key)
            entry = self._addresses.get(key)
            if entry is None:
                self.new_address_count += 1
                handle = PremapAddressHandle.from_record(record)
                self._evicted_address_keys.discard(key)
                self._addresses[key] = PremapAddressCacheEntry(
                    descriptor_bytes=int(record.descriptor_bytes),
                    handle=handle,
                    prepared_count=1,
                )
                self._addresses.move_to_end(key)
                self._evict_if_needed()
            else:
                self.reused_address_count += 1
                handle = PremapAddressHandle.from_record(record)
                self._evicted_address_keys.discard(key)
                entry.descriptor_bytes = int(record.descriptor_bytes)
                entry.handle = handle
                entry.prepared_count += 1
                self._addresses.move_to_end(key)
        return self.snapshot()

    @staticmethod
    def address_key(
        *,
        layer_idx: int,
        expert_id: int,
        address_namespace: str = "expert_weight_descriptor",
    ) -> str:
        namespace = str(address_namespace or "expert_weight_descriptor")
        return f"{namespace}:l{int(layer_idx)}:e{int(expert_id)}"

    def contains_address_key(self, address_key: str) -> bool:
        """Return whether an address handle is resident without mutating LRU state."""

        return str(address_key) in self._addresses

    def resolve_address_key(self, address_key: str) -> PremapAddressHandle | None:
        """Resolve a prepared descriptor/address object without mutating LRU state."""

        entry = self._addresses.get(str(address_key))
        return entry.handle if entry is not None else None

    def resolve_layer_expert(
        self,
        *,
        layer_idx: int,
        expert_id: int,
        address_namespace: str = "expert_weight_descriptor",
    ) -> PremapAddressHandle | None:
        return self.resolve_address_key(
            self.address_key(
                layer_idx=int(layer_idx),
                expert_id=int(expert_id),
                address_namespace=address_namespace,
            )
        )

    def consume_readonly(
        self,
        address_keys: Iterable[str],
        *,
        expected_handle_hash_by_address_key: dict[str, str] | None = None,
    ) -> PremapReadonlyConsumerResult:
        """Validate that consumer address keys resolve to resident handles.

        This models the runtime consumer's descriptor/address lookup without
        moving payloads, mutating LRU state, or granting ready credit.
        """

        expected = expected_handle_hash_by_address_key or {}
        lookup_count = 0
        handle_hit_count = 0
        handle_miss_count = 0
        evicted_before_consume_count = 0
        stale_handle_count = 0
        checked_parity_count = 0
        for raw_key in address_keys:
            lookup_count += 1
            key = str(raw_key)
            entry = self._addresses.get(key)
            if entry is None:
                handle_miss_count += 1
                if key in self._evicted_address_keys:
                    evicted_before_consume_count += 1
                continue
            handle_hit_count += 1
            expected_hash = expected.get(key)
            if expected_hash is None:
                continue
            checked_parity_count += 1
            if str(expected_hash) != str(entry.handle.handle_hash):
                stale_handle_count += 1
        parity_ok = None
        if expected:
            parity_ok = (
                checked_parity_count == len(expected)
                and stale_handle_count == 0
                and handle_miss_count == 0
            )
        return PremapReadonlyConsumerResult(
            lookup_count=lookup_count,
            handle_hit_count=handle_hit_count,
            handle_miss_count=handle_miss_count,
            evicted_before_consume_count=evicted_before_consume_count,
            stale_handle_count=stale_handle_count,
            handle_parity_ok=parity_ok,
        )

    def contains_layer_expert(
        self,
        *,
        layer_idx: int,
        expert_id: int,
        address_namespace: str = "expert_weight_descriptor",
    ) -> bool:
        return self.contains_address_key(
            self.address_key(
                layer_idx=int(layer_idx),
                expert_id=int(expert_id),
                address_namespace=address_namespace,
            )
        )

    def snapshot(self) -> PremapAddressManagerSnapshot:
        return PremapAddressManagerSnapshot(
            capacity=self.capacity,
            resident_address_count=len(self._addresses),
            prepared_plan_count=self.prepared_plan_count,
            prepared_record_count=self.prepared_record_count,
            new_address_count=self.new_address_count,
            reused_address_count=self.reused_address_count,
            evicted_address_count=self.evicted_address_count,
            prepared_descriptor_actual_bytes=self.prepared_descriptor_actual_bytes,
            resident_descriptor_bytes=sum(
                int(entry.descriptor_bytes) for entry in self._addresses.values()
            ),
            payload_bytes=self.payload_bytes,
        )

    def _evict_if_needed(self) -> None:
        if self.capacity is None:
            return
        if self.capacity <= 0:
            self._evicted_address_keys.update(self._addresses)
            self.evicted_address_count += len(self._addresses)
            self._addresses.clear()
            return
        while len(self._addresses) > self.capacity:
            old_key, _old_entry = self._addresses.popitem(last=False)
            self._evicted_address_keys.add(str(old_key))
            self.evicted_address_count += 1
