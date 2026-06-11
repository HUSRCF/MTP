from __future__ import annotations

import hashlib
import json
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass, field
from functools import cached_property

from mtp_expert_prefetch.runtime.premap import PremapAddressRecord, PremapPreparedPlan

PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
PREMAP_SINGLE_FIELD_HANDLE_HANDOFF_CANARY_FIELDS = (
    "aux_metadata_handle",
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
)
PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH = hashlib.sha256(
    "|".join(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS).encode("utf-8")
).hexdigest()
PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME = (
    "fused_moe_awq_wna16_prelaunch_descriptor_address_v1"
)
PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS = (
    "sorted_token_ids_ref",
    "expert_ids_ref",
    "num_tokens_post_padded_ref",
    "descriptor_ptr_table_ref",
    "packed_weight_descriptor_table_ref",
    "scale_metadata_handle_table_ref",
    "aux_metadata_handle_table_ref",
    "row_order_hash",
    "ordered_row_hash",
)
PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH = hashlib.sha256(
    "|".join(PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS).encode("utf-8")
).hexdigest()
PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME = (
    "fused_moe_awq_wna16_semantic_handle_table_v1"
)
PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS = (
    "address_key",
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
    "row_order_hash",
    "ordered_row_hash",
)
PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH = hashlib.sha256(
    "|".join(PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS).encode("utf-8")
).hexdigest()
PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME = (
    "fused_moe_awq_wna16_kernel_side_consumer_schema_v1"
)
PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS = (
    "semantic_handle_table_ref",
    "descriptor_ptr_handle_ref",
    "packed_weight_descriptor_handle_ref",
    "scale_metadata_handle_ref",
    "aux_metadata_handle_ref",
    "row_order_hash",
    "ordered_row_hash",
    "semantic_adapter_hash",
)
PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH = hashlib.sha256(
    "|".join(PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS).encode("utf-8")
).hexdigest()
PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME = (
    "fused_moe_awq_wna16_kernel_side_typed_consumer_object_v1"
)
PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_FIELDS = (
    "kernel_side_consumer_schema_adapter_ref",
    "semantic_handle_table_ref",
    "descriptor_ptr_handle_ref",
    "packed_weight_descriptor_handle_ref",
    "scale_metadata_handle_ref",
    "aux_metadata_handle_ref",
    "row_order_hash",
    "ordered_row_hash",
    "consumer_row_count",
    "consumer_column_count",
    "consumer_block_reason",
)
PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH = hashlib.sha256(
    "|".join(PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_FIELDS).encode("utf-8")
).hexdigest()
PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_NAME = (
    "premap_kernel_side_typed_consumer_path_v1"
)
PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_MODE = "readonly_typed_row_consumer_path"
PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_SOURCE = (
    "vllm_prelaunch_prepared_handle_table"
)
PREMAP_WNA16_ADJACENT_TYPED_SLOT_NAME = (
    "premap_wna16_adjacent_typed_consumer_slot_v1"
)
PREMAP_WNA16_ADJACENT_TYPED_SLOT_MODE = (
    "readonly_wna16_adjacent_typed_consumer_slot"
)
PREMAP_WNA16_ADJACENT_TYPED_SLOT_SOURCE = (
    "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
)
PREMAP_WNA16_ADJACENT_TYPED_SLOT_PACKET_CHAIN_DEPTH = 14
PREMAP_WNA16_ADJACENT_TYPED_SLOT_FIELD_MASK = 15


def premap_single_field_handle_handoff_mirror_mode(field_name: str) -> str:
    field = str(field_name)
    if field not in PREMAP_SINGLE_FIELD_HANDLE_HANDOFF_CANARY_FIELDS:
        msg = (
            "premap single-field handoff canary only supports "
            f"{list(PREMAP_SINGLE_FIELD_HANDLE_HANDOFF_CANARY_FIELDS)}; got {field!r}"
        )
        raise ValueError(msg)
    return f"readonly_{field}_mirror"


def _premap_semantic_adapter_hash_attr_for_field(field_name: str) -> str:
    field = str(field_name)
    mapping = {
        "descriptor_ptr": "descriptor_ptr_handle_hash",
        "packed_weight_descriptor": "packed_weight_descriptor_handle_hash",
        "scale_metadata_handle": "scale_metadata_handle_hash",
        "aux_metadata_handle": "aux_metadata_handle_hash",
    }
    try:
        return mapping[field]
    except KeyError as exc:
        msg = f"unsupported premap semantic adapter field: {field!r}"
        raise ValueError(msg) from exc


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
class ReadyTimeCacheManagerSnapshot(CacheManagerSnapshot):
    """Snapshot for ready-before-demand payload cache accounting."""

    ready_late_miss_count: int
    late_completion_unused_count: int
    queue_batch_count: int
    queue_service_us: float
    queue_total_span_us: float
    queue_wait_us: float
    queue_max_delay_us: float
    queue_event_interval_us: float
    queue_deadline_us: float
    queue_batch_size: int


class ReadyTimeExpertCacheManager:
    """Bounded expert-payload cache with ready-before-demand semantics.

    This is the runtime primitive for the controlled payload/cache-manager path.
    A prefetched expert is a demand hit only after its virtual transfer
    completion time is no later than the demand deadline.  The class does not
    move payload bytes; it accounts for service time, batching, and late
    completion so the online path can graduate beyond resident-only accounting
    before any real DMA/cache-manager integration.
    """

    def __init__(
        self,
        *,
        capacity: int,
        service_us_per_issue: float = 0.0,
        service_us_per_batch: float = 0.0,
        queue_batch_size: int = 1,
        queue_deadline_us: float = 0.0,
    ) -> None:
        self.capacity = int(capacity)
        self.service_us_per_issue = max(0.0, float(service_us_per_issue))
        self.service_us_per_batch = max(0.0, float(service_us_per_batch))
        self.queue_batch_size = max(1, int(queue_batch_size) or 1)
        self.queue_deadline_us = max(0.0, float(queue_deadline_us))

        self._cache: OrderedDict[tuple[int, int], CacheManagerEntry] = OrderedDict()
        self._pending_keys: list[tuple[int, int]] = []
        self._pending_first_arrival_us: float | None = None
        self._completions: deque[tuple[float, list[tuple[int, int]]]] = deque()
        self._inflight: set[tuple[int, int]] = set()
        self._server_available_us = 0.0
        self._last_completion_us = 0.0
        self._last_arrival_us = 0.0

        self.issued_fetch_count = 0
        self.used_fetch_count = 0
        self.demand_count = 0
        self.demand_hit_count = 0
        self.demand_miss_count = 0
        self.evicted_before_use_count = 0
        self.ready_late_miss_count = 0
        self.late_completion_unused_count = 0
        self.queue_batch_count = 0
        self.queue_service_us = 0.0
        self.queue_wait_us = 0.0
        self.queue_max_delay_us = 0.0

    def issue_prefetch(
        self,
        layer_idx: int,
        expert_idx: int,
        *,
        arrival_us: float,
    ) -> bool:
        """Issue one virtual payload transfer unless resident or in flight."""

        key = (int(layer_idx), int(expert_idx))
        self.advance_to(arrival_us)
        if key in self._cache:
            self._cache.move_to_end(key)
            return False
        if key in self._inflight:
            return False
        self.issued_fetch_count += 1
        self._inflight.add(key)
        if not self._pending_keys:
            self._pending_first_arrival_us = float(arrival_us)
        self._pending_keys.append(key)
        self._flush_full_batches(ready_us=float(arrival_us))
        return True

    def issue_prefetches(
        self,
        layer_idx: int,
        expert_indices: list[int] | tuple[int, ...],
        *,
        arrival_us: float,
    ) -> int:
        """Issue a token/layer burst and return the number of new transfers."""

        issued = 0
        for expert_idx in expert_indices:
            if self.issue_prefetch(
                int(layer_idx),
                int(expert_idx),
                arrival_us=float(arrival_us),
            ):
                issued += 1
        return issued

    def demand(
        self,
        layer_idx: int,
        expert_idx: int,
        *,
        arrival_us: float,
    ) -> bool:
        """Demand one expert and require completion by arrival + deadline."""

        demand_deadline_us = float(arrival_us) + self.queue_deadline_us
        self._flush_due_pending(demand_deadline_us)
        self._drain_ready(demand_deadline_us)
        self.demand_count += 1
        key = (int(layer_idx), int(expert_idx))
        entry = self._cache.get(key)
        if entry is not None:
            self.demand_hit_count += 1
            if entry.prefetched and not entry.used:
                self.used_fetch_count += 1
            entry.used = True
            self._cache.move_to_end(key)
            return True
        if key in self._inflight:
            self.ready_late_miss_count += 1
        self.demand_miss_count += 1
        self._insert(key, CacheManagerEntry(prefetched=False, used=True))
        return False

    def advance_to(self, arrival_us: float) -> None:
        """Advance virtual time and materialize transfers ready by arrival."""

        arrival = max(0.0, float(arrival_us))
        self._last_arrival_us = max(self._last_arrival_us, arrival)
        self._flush_due_pending(arrival)
        self._drain_ready(arrival)

    def finish(self) -> None:
        """Flush outstanding virtual transfers for final accounting."""

        if self._pending_keys and self._pending_first_arrival_us is not None:
            first_arrival_us = self._pending_first_arrival_us
            ready_us = (
                first_arrival_us + self.queue_deadline_us
                if self.queue_deadline_us > 0.0
                else self._last_arrival_us
            )
            keys = list(self._pending_keys)
            self._pending_keys.clear()
            self._pending_first_arrival_us = None
            self._flush_pending(
                keys,
                ready_us=ready_us,
                first_arrival_us=first_arrival_us,
            )
        self._drain_ready(float("inf"))

    def snapshot(self) -> ReadyTimeCacheManagerSnapshot:
        resident_unused_fetch_count = sum(
            1 for entry in self._cache.values() if entry.prefetched and not entry.used
        )
        unused_fetch_count = (
            resident_unused_fetch_count + self.late_completion_unused_count
        )
        return ReadyTimeCacheManagerSnapshot(
            capacity=self.capacity,
            resident_count=len(self._cache),
            issued_fetch_count=self.issued_fetch_count,
            used_fetch_count=self.used_fetch_count,
            unused_fetch_count=unused_fetch_count,
            demand_count=self.demand_count,
            demand_hit_count=self.demand_hit_count,
            demand_miss_count=self.demand_miss_count,
            evicted_before_use_count=self.evicted_before_use_count,
            ready_late_miss_count=self.ready_late_miss_count,
            late_completion_unused_count=self.late_completion_unused_count,
            queue_batch_count=self.queue_batch_count,
            queue_service_us=float(self.queue_service_us),
            queue_total_span_us=(
                float(max(0.0, self._last_completion_us))
                if self.issued_fetch_count
                else 0.0
            ),
            queue_wait_us=float(self.queue_wait_us),
            queue_max_delay_us=float(self.queue_max_delay_us),
            queue_event_interval_us=0.0,
            queue_deadline_us=float(self.queue_deadline_us),
            queue_batch_size=int(self.queue_batch_size),
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

    def _batch_service_us(self, count: int) -> float:
        return self.service_us_per_batch + self.service_us_per_issue * float(count)

    def _flush_pending(
        self,
        keys: list[tuple[int, int]],
        *,
        ready_us: float,
        first_arrival_us: float,
    ) -> None:
        if not keys:
            return
        service_us = self._batch_service_us(len(keys))
        start_us = max(self._server_available_us, float(ready_us))
        wait_us = max(0.0, start_us - float(ready_us))
        completion_us = start_us + service_us
        self.queue_batch_count += 1
        self.queue_service_us += service_us
        self.queue_wait_us += wait_us
        self.queue_max_delay_us = max(
            self.queue_max_delay_us,
            completion_us - float(first_arrival_us),
        )
        self._server_available_us = completion_us
        self._last_completion_us = completion_us
        self._completions.append((completion_us, list(keys)))

    def _flush_full_batches(self, *, ready_us: float) -> None:
        while len(self._pending_keys) >= self.queue_batch_size:
            first_arrival_us = (
                float(ready_us)
                if self._pending_first_arrival_us is None
                else self._pending_first_arrival_us
            )
            keys = self._pending_keys[: self.queue_batch_size]
            del self._pending_keys[: self.queue_batch_size]
            self._flush_pending(
                keys,
                ready_us=float(ready_us),
                first_arrival_us=first_arrival_us,
            )
            self._pending_first_arrival_us = (
                float(ready_us) if self._pending_keys else None
            )

    def _flush_due_pending(self, arrival_us: float) -> None:
        if (
            self._pending_keys
            and self._pending_first_arrival_us is not None
            and self.queue_deadline_us > 0.0
            and float(arrival_us)
            >= self._pending_first_arrival_us + self.queue_deadline_us
        ):
            first_arrival_us = self._pending_first_arrival_us
            keys = list(self._pending_keys)
            self._pending_keys.clear()
            self._pending_first_arrival_us = None
            self._flush_pending(
                keys,
                ready_us=first_arrival_us + self.queue_deadline_us,
                first_arrival_us=first_arrival_us,
            )

    def _drain_ready(self, ready_time_us: float) -> None:
        while self._completions and self._completions[0][0] <= ready_time_us:
            _, keys = self._completions.popleft()
            for key in keys:
                self._inflight.discard(key)
                entry = self._cache.get(key)
                if entry is not None:
                    if not entry.prefetched:
                        self.late_completion_unused_count += 1
                    self._cache.move_to_end(key)
                    continue
                self._insert(key, CacheManagerEntry(prefetched=True, used=False))


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


@dataclass(frozen=True)
class PremapRealDescriptorHandle:
    """Read-only signature of a live vLLM/AWQ descriptor/address handle.

    The object is intentionally a runtime-address signature, not a payload
    wrapper: it records which live packed-weight / scale / auxiliary metadata
    source classes were resolvable for an expert without copying or mutating the
    tensors behind those handles.
    """

    expert_id: int
    local_expert_id: int
    handle_hash: str
    address_key: str | None = None
    packed_weight_descriptor: str | None = None
    scale_metadata_handle: str | None = None
    aux_metadata_handle: str | None = None
    payload_bytes: int = 0

    @property
    def descriptor_ptr(self) -> str:
        return f"real_descriptor://{self.handle_hash}"

    def as_dict(self) -> dict[str, int | str | None]:
        return asdict(self)


@dataclass(frozen=True)
class PremapDescriptorConsumerObject:
    """Read-only descriptor/address object handed to a runtime consumer.

    This is the first executable object-shaped contract above hash-only
    telemetry.  It contains the descriptor/address handles that a consumer can
    dereference, but it still carries no expert payload, grants no ready credit,
    and does not change routing or descriptor visitation order.
    """

    address_key: str
    descriptor_ptr: str
    packed_weight_descriptor: str
    scale_metadata_handle: str
    aux_metadata_handle: str | None
    handle_hash: str
    real_handle_hash: str | None = None
    payload_bytes: int = 0
    ready_credit: bool = False
    changes_router: bool = False
    changes_descriptor_order: bool = False

    @property
    def object_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str | None]:
        return asdict(self)


@dataclass(frozen=True)
class PremapKernelArgShadowTableRow:
    """One prepared descriptor/address row for a future kernel handoff.

    The row is an in-memory consumer object only.  It mirrors the handle table
    schema a kernel integration could consume later, but it is never passed to
    a kernel in this dry-run path.
    """

    address_key: str
    descriptor_ptr: str
    packed_weight_descriptor: str
    scale_metadata_handle: str
    aux_metadata_handle: str | None
    object_hash: str
    payload_bytes: int = 0
    passed_to_kernel: bool = False

    @property
    def row_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str | None]:
        return asdict(self)


def _handle_to_native_u64(value: str | int | None) -> int:
    """Convert a readonly handle token into a deterministic native u64 value.

    This is a handle identity bridge for the native consumer stub. It never
    dereferences payload and does not claim that semantic string handles are
    current WNA16 kernel pointers.
    """

    if value is None:
        return 0
    if isinstance(value, int):
        return int(value) & 0xFFFFFFFFFFFFFFFF
    text = str(value)
    if not text:
        return 0
    try:
        parsed = int(text, 0)
    except ValueError:
        parsed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    parsed &= 0xFFFFFFFFFFFFFFFF
    return parsed if parsed != 0 else 1


def _u64_to_signed_i64(value: int) -> int:
    raw = int(value) & 0xFFFFFFFFFFFFFFFF
    if raw >= (1 << 63):
        return raw - (1 << 64)
    return raw


def _mix64(value: int) -> int:
    value = int(value) & 0xFFFFFFFFFFFFFFFF
    value ^= value >> 33
    value = (value * 0xFF51AFD7ED558CCD) & 0xFFFFFFFFFFFFFFFF
    value ^= value >> 33
    value = (value * 0xC4CEB9FE1A85EC53) & 0xFFFFFFFFFFFFFFFF
    value ^= value >> 33
    return value & 0xFFFFFFFFFFFFFFFF


def _digest_to_u64(value: str | None) -> int:
    text = str(value or "")
    if not text:
        return 0
    digest = text if len(text) >= 16 else hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) & 0xFFFFFFFFFFFFFFFF


def _expert_id_from_address_key(address_key: str) -> int:
    text = str(address_key)
    marker = ":e"
    if marker not in text:
        return -1
    try:
        return int(text.rsplit(marker, 1)[1])
    except ValueError:
        return -1


@dataclass(frozen=True)
class PremapKernelArgShadowTableObject:
    """Immutable handle table object consumed by the no-op prelaunch shim."""

    execution_mode: str
    row_order_source: str
    rows: tuple[PremapKernelArgShadowTableRow, ...]
    schema_hash: str = PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    payload_bytes: int = 0
    ready_credit: bool = False
    changes_router: bool = False
    changes_descriptor_order: bool = False
    changes_kernel_launch_args: bool = False
    passed_to_kernel: bool = False

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        return len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)

    @property
    def row_order_hash(self) -> str:
        payload = "|".join(row.address_key for row in self.rows).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def ordered_row_hash(self) -> str:
        payload = "|".join(
            f"{row.address_key}:{row.object_hash}" for row in self.rows
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def object_hash(self) -> str:
        payload = json.dumps(
            {
                "execution_mode": self.execution_mode,
                "row_order_source": self.row_order_source,
                "schema_hash": self.schema_hash,
                "payload_bytes": int(self.payload_bytes),
                "ready_credit": bool(self.ready_credit),
                "changes_router": bool(self.changes_router),
                "changes_descriptor_order": bool(self.changes_descriptor_order),
                "changes_kernel_launch_args": bool(
                    self.changes_kernel_launch_args
                ),
                "passed_to_kernel": bool(self.passed_to_kernel),
                "rows": [row.row_hash for row in self.rows],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def lifecycle_ok(self) -> bool:
        return (
            int(self.payload_bytes) == 0
            and all(int(row.payload_bytes) == 0 for row in self.rows)
            and not bool(self.ready_credit)
            and not bool(self.changes_router)
            and not bool(self.changes_descriptor_order)
            and not bool(self.changes_kernel_launch_args)
            and not bool(self.passed_to_kernel)
            and not any(bool(row.passed_to_kernel) for row in self.rows)
        )

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "execution_mode": str(self.execution_mode),
            "row_order_source": str(self.row_order_source),
            "row_count": int(self.row_count),
            "column_count": int(self.column_count),
            "schema_hash": str(self.schema_hash),
            "row_order_hash": self.row_order_hash,
            "ordered_row_hash": self.ordered_row_hash,
            "object_hash": self.object_hash,
            "payload_bytes": int(self.payload_bytes),
            "ready_credit": bool(self.ready_credit),
            "changes_router": bool(self.changes_router),
            "changes_descriptor_order": bool(self.changes_descriptor_order),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
            "passed_to_kernel": bool(self.passed_to_kernel),
        }

    @cached_property
    def native_typed_consumer_columns_u64(
        self,
    ) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
        """Packed native handle identities for a future typed kernel consumer.

        The table object is immutable for the current dry-run contract, so the
        string-handle to deterministic-u64 conversion can be cached once per
        table.  This is the lowest-level producer representation before a real
        C++/HIP consumer; it still does not dereference payload or mutate launch
        args.
        """

        return (
            tuple(_handle_to_native_u64(row.descriptor_ptr) for row in self.rows),
            tuple(
                _handle_to_native_u64(row.packed_weight_descriptor)
                for row in self.rows
            ),
            tuple(_handle_to_native_u64(row.scale_metadata_handle) for row in self.rows),
            tuple(_handle_to_native_u64(row.aux_metadata_handle) for row in self.rows),
        )

    @cached_property
    def native_typed_consumer_columns_i64(
        self,
    ) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
        """Signed int64 view of the packed native columns for torch staging."""

        return tuple(  # type: ignore[return-value]
            tuple(_u64_to_signed_i64(value) for value in column)
            for column in self.native_typed_consumer_columns_u64
        )

    def to_native_typed_consumer_input_dict(self) -> dict[str, object]:
        """Export the table in the JSON shape accepted by the native stub.

        The output is only a no-op bridge artifact for
        `scripts/run_premap_typed_consumer_stub.py --input-json`. It contains
        deterministic u64 handle identities, not payload contents, and is not a
        WNA16 launch-argument object.
        """

        native_columns = self.native_typed_consumer_columns_u64
        return {
            "descriptor_ptr": list(native_columns[0]),
            "packed_weight_descriptor": list(native_columns[1]),
            "scale_metadata_handle": list(native_columns[2]),
            "aux_metadata_handle": list(native_columns[3]),
            "expert_id": [
                _expert_id_from_address_key(row.address_key) for row in self.rows
            ],
            "address_key_hash": [
                _handle_to_native_u64(row.address_key) for row in self.rows
            ],
            "_meta": {
                "schema_hash": self.schema_hash,
                "row_count": self.row_count,
                "column_count": self.column_count,
                "row_order_hash": self.row_order_hash,
                "ordered_row_hash": self.ordered_row_hash,
                "table_object_hash": self.object_hash,
                "payload_bytes": self.payload_bytes,
                "ready_credit": self.ready_credit,
                "changes_router": self.changes_router,
                "changes_descriptor_order": self.changes_descriptor_order,
                "passed_to_kernel": self.passed_to_kernel,
                "changes_kernel_launch_args": self.changes_kernel_launch_args,
            },
        }

    def copy_native_typed_consumer_columns_to(
        self,
        columns: tuple[object, object, object, object],
        *,
        offset: int = 0,
        signed_i64: bool = False,
    ) -> int:
        """Copy typed handle columns directly into preallocated producer buffers.

        This is the hot-path producer form of `to_native_typed_consumer_input_dict`.
        It avoids building intermediate Python lists/dicts and lets a native or
        persistent adapter own the destination buffers.  The handles remain
        deterministic u64 identities; this still does not dereference payload or
        imply compatibility with the current WNA16 launch args.
        """

        if len(columns) != len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS):
            msg = (
                "copy_native_typed_consumer_columns_to expected four columns; "
                f"got {len(columns)}."
            )
            raise ValueError(msg)
        base = int(offset)
        descriptor_ptr, packed_weight_descriptor, scale_metadata_handle, aux_metadata_handle = (
            columns
        )
        source_columns = (
            self.native_typed_consumer_columns_i64
            if bool(signed_i64)
            else self.native_typed_consumer_columns_u64
        )
        for output_column, source_values in zip(
            (
                descriptor_ptr,
                packed_weight_descriptor,
                scale_metadata_handle,
                aux_metadata_handle,
            ),
            source_columns,
            strict=True,
        ):
            for row_index, value in enumerate(source_values):
                output_column[base + int(row_index)] = int(value)  # type: ignore[index]
        return int(self.row_count)


@dataclass(frozen=True)
class PremapKernelArgHandoffShadowSlot:
    """Readonly package that mirrors a future kernel-argument handoff.

    The slot is the last no-op object before a real kernel integration.  It
    points at the prepared handle table identity and records the exact schema
    and source availability that a future kernel consumer would require, but it
    is intentionally not passed to a kernel.
    """

    mode: str
    table_object_hash: str
    row_count: int
    column_count: int
    schema_hash: str
    row_order_hash: str
    ordered_row_hash: str
    required_source_hit_count: int
    required_source_miss_count: int
    optional_source_hit_count: int
    optional_source_miss_count: int
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.mode == "readonly_kernel_arg_handoff_shadow_slot"
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(self.schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and bool(self.table_object_hash)
            and bool(self.row_order_hash)
            and bool(self.ordered_row_hash)
            and int(self.required_source_hit_count) == int(self.row_count) * 3
            and int(self.required_source_miss_count) == 0
            and int(self.optional_source_hit_count)
            + int(self.optional_source_miss_count)
            == int(self.row_count)
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
        )

    @property
    def slot_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "ready": bool(self.ready),
            "table_object_hash": str(self.table_object_hash),
            "row_count": int(self.row_count),
            "column_count": int(self.column_count),
            "schema_hash": str(self.schema_hash),
            "row_order_hash": str(self.row_order_hash),
            "ordered_row_hash": str(self.ordered_row_hash),
            "required_source_hit_count": int(self.required_source_hit_count),
            "required_source_miss_count": int(self.required_source_miss_count),
            "optional_source_hit_count": int(self.optional_source_hit_count),
            "optional_source_miss_count": int(self.optional_source_miss_count),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
        }


@dataclass(frozen=True)
class PremapKernelArgHandoffMirrorObject:
    """No-op mirror of the future fused-MoE/AWQ kernel argument package.

    The mirror projects the prepared handle table into the argument arrays a
    future kernel handoff would consume.  It records only identities and hashes;
    the current path never passes this object to a kernel and never changes the
    live launch arguments.
    """

    mode: str
    slot_hash: str
    table_object_hash: str
    row_count: int
    column_count: int
    schema_hash: str
    row_order_hash: str
    ordered_row_hash: str
    descriptor_ptr_arg_hash: str
    packed_weight_descriptor_arg_hash: str
    scale_metadata_handle_arg_hash: str
    aux_metadata_handle_arg_hash: str
    required_source_hit_count: int
    required_source_miss_count: int
    optional_source_hit_count: int
    optional_source_miss_count: int
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.mode == "readonly_kernel_arg_handoff_mirror"
            and bool(self.slot_hash)
            and bool(self.table_object_hash)
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(self.schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and bool(self.row_order_hash)
            and bool(self.ordered_row_hash)
            and bool(self.descriptor_ptr_arg_hash)
            and bool(self.packed_weight_descriptor_arg_hash)
            and bool(self.scale_metadata_handle_arg_hash)
            and bool(self.aux_metadata_handle_arg_hash)
            and int(self.required_source_hit_count) == int(self.row_count) * 3
            and int(self.required_source_miss_count) == 0
            and int(self.optional_source_hit_count)
            + int(self.optional_source_miss_count)
            == int(self.row_count)
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
        )

    @property
    def mirror_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "ready": bool(self.ready),
            "slot_hash": str(self.slot_hash),
            "table_object_hash": str(self.table_object_hash),
            "row_count": int(self.row_count),
            "column_count": int(self.column_count),
            "schema_hash": str(self.schema_hash),
            "row_order_hash": str(self.row_order_hash),
            "ordered_row_hash": str(self.ordered_row_hash),
            "descriptor_ptr_arg_hash": str(self.descriptor_ptr_arg_hash),
            "packed_weight_descriptor_arg_hash": str(
                self.packed_weight_descriptor_arg_hash
            ),
            "scale_metadata_handle_arg_hash": str(
                self.scale_metadata_handle_arg_hash
            ),
            "aux_metadata_handle_arg_hash": str(self.aux_metadata_handle_arg_hash),
            "required_source_hit_count": int(self.required_source_hit_count),
            "required_source_miss_count": int(self.required_source_miss_count),
            "optional_source_hit_count": int(self.optional_source_hit_count),
            "optional_source_miss_count": int(self.optional_source_miss_count),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
        }


@dataclass(frozen=True)
class PremapKernelArgPrelaunchLaunchSchemaMirror:
    """Readonly mirror shaped like a future fused-MoE/AWQ launch package.

    This is deliberately stricter than `PremapKernelArgHandoffMirrorObject`:
    it records the launch-side reference slots a future kernel consumer would
    expect to receive.  The current path still keeps it as a shadow object only;
    no payload is moved, no ready credit is granted, and no kernel launch
    argument is mutated or replaced.
    """

    mode: str
    handoff_mirror_hash: str
    slot_hash: str
    table_object_hash: str
    row_count: int
    column_count: int
    table_schema_hash: str
    launch_schema_name: str
    launch_schema_hash: str
    launch_arg_field_count: int
    row_order_hash: str
    ordered_row_hash: str
    descriptor_ptr_arg_hash: str
    packed_weight_descriptor_arg_hash: str
    scale_metadata_handle_arg_hash: str
    aux_metadata_handle_arg_hash: str
    required_source_hit_count: int
    required_source_miss_count: int
    optional_source_hit_count: int
    optional_source_miss_count: int
    handle_field_read_count: int
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.mode == "readonly_kernel_arg_handoff_launch_schema_mirror"
            and bool(self.handoff_mirror_hash)
            and bool(self.slot_hash)
            and bool(self.table_object_hash)
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(self.table_schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and str(self.launch_schema_name)
            == PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME
            and str(self.launch_schema_hash)
            == PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH
            and int(self.launch_arg_field_count)
            == len(PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS)
            and bool(self.row_order_hash)
            and bool(self.ordered_row_hash)
            and bool(self.descriptor_ptr_arg_hash)
            and bool(self.packed_weight_descriptor_arg_hash)
            and bool(self.scale_metadata_handle_arg_hash)
            and bool(self.aux_metadata_handle_arg_hash)
            and int(self.handle_field_read_count)
            == int(self.row_count)
            * len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and int(self.required_source_hit_count) == int(self.row_count) * 3
            and int(self.required_source_miss_count) == 0
            and int(self.optional_source_hit_count)
            + int(self.optional_source_miss_count)
            == int(self.row_count)
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
        )

    @property
    def launch_schema_mirror_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "ready": bool(self.ready),
            "handoff_mirror_hash": str(self.handoff_mirror_hash),
            "slot_hash": str(self.slot_hash),
            "table_object_hash": str(self.table_object_hash),
            "row_count": int(self.row_count),
            "column_count": int(self.column_count),
            "table_schema_hash": str(self.table_schema_hash),
            "launch_schema_name": str(self.launch_schema_name),
            "launch_schema_hash": str(self.launch_schema_hash),
            "launch_arg_field_count": int(self.launch_arg_field_count),
            "row_order_hash": str(self.row_order_hash),
            "ordered_row_hash": str(self.ordered_row_hash),
            "descriptor_ptr_arg_hash": str(self.descriptor_ptr_arg_hash),
            "packed_weight_descriptor_arg_hash": str(
                self.packed_weight_descriptor_arg_hash
            ),
            "scale_metadata_handle_arg_hash": str(
                self.scale_metadata_handle_arg_hash
            ),
            "aux_metadata_handle_arg_hash": str(self.aux_metadata_handle_arg_hash),
            "required_source_hit_count": int(self.required_source_hit_count),
            "required_source_miss_count": int(self.required_source_miss_count),
            "optional_source_hit_count": int(self.optional_source_hit_count),
            "optional_source_miss_count": int(self.optional_source_miss_count),
            "handle_field_read_count": int(self.handle_field_read_count),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
        }


@dataclass(frozen=True)
class PremapKernelArgSemanticHandleAdapterObject:
    """Typed no-op schema for future kernel-side handle consumption.

    This object is intentionally not a tensor-argument replacement.  It defines
    the semantic descriptor/address table a future kernel can consume once a
    real kernel schema exists.  The current path only verifies schema, handle
    availability, and lifecycle; it must never be passed to a kernel.
    """

    mode: str
    table_object_hash: str
    launch_schema_mirror_hash: str
    row_count: int
    column_count: int
    table_schema_hash: str
    semantic_schema_name: str
    semantic_schema_hash: str
    semantic_field_count: int
    row_order_hash: str
    ordered_row_hash: str
    descriptor_ptr_handle_hash: str
    packed_weight_descriptor_handle_hash: str
    scale_metadata_handle_hash: str
    aux_metadata_handle_hash: str
    required_source_hit_count: int
    required_source_miss_count: int
    optional_source_hit_count: int
    optional_source_miss_count: int
    handle_field_read_count: int
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    live_compatible_with_current_wna16_args: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.mode == "readonly_kernel_arg_semantic_handle_adapter"
            and bool(self.table_object_hash)
            and bool(self.launch_schema_mirror_hash)
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(self.table_schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and str(self.semantic_schema_name)
            == PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME
            and str(self.semantic_schema_hash)
            == PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
            and int(self.semantic_field_count)
            == len(PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS)
            and bool(self.row_order_hash)
            and bool(self.ordered_row_hash)
            and bool(self.descriptor_ptr_handle_hash)
            and bool(self.packed_weight_descriptor_handle_hash)
            and bool(self.scale_metadata_handle_hash)
            and bool(self.aux_metadata_handle_hash)
            and int(self.handle_field_read_count)
            == int(self.row_count)
            * len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and int(self.required_source_hit_count) == int(self.row_count) * 3
            and int(self.required_source_miss_count) == 0
            and int(self.optional_source_hit_count)
            + int(self.optional_source_miss_count)
            == int(self.row_count)
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
            and not bool(self.live_compatible_with_current_wna16_args)
        )

    @property
    def adapter_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "ready": bool(self.ready),
            "table_object_hash": str(self.table_object_hash),
            "launch_schema_mirror_hash": str(self.launch_schema_mirror_hash),
            "row_count": int(self.row_count),
            "column_count": int(self.column_count),
            "table_schema_hash": str(self.table_schema_hash),
            "semantic_schema_name": str(self.semantic_schema_name),
            "semantic_schema_hash": str(self.semantic_schema_hash),
            "semantic_field_count": int(self.semantic_field_count),
            "row_order_hash": str(self.row_order_hash),
            "ordered_row_hash": str(self.ordered_row_hash),
            "descriptor_ptr_handle_hash": str(self.descriptor_ptr_handle_hash),
            "packed_weight_descriptor_handle_hash": str(
                self.packed_weight_descriptor_handle_hash
            ),
            "scale_metadata_handle_hash": str(self.scale_metadata_handle_hash),
            "aux_metadata_handle_hash": str(self.aux_metadata_handle_hash),
            "required_source_hit_count": int(self.required_source_hit_count),
            "required_source_miss_count": int(self.required_source_miss_count),
            "optional_source_hit_count": int(self.optional_source_hit_count),
            "optional_source_miss_count": int(self.optional_source_miss_count),
            "handle_field_read_count": int(self.handle_field_read_count),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
            "live_compatible_with_current_wna16_args": bool(
                self.live_compatible_with_current_wna16_args
            ),
        }


@dataclass(frozen=True)
class PremapSingleFieldHandleHandoffCanary:
    """Readonly canary for one future kernel-side handle field.

    This is not a current WNA16 argument replacement.  It proves that the
    prepared typed table can expose one field a future kernel consumer would
    accept.  Live handoff is deliberately disabled here, so the object remains
    a parity/no-crash/fallback gate.
    """

    mode: str
    field_name: str
    source: str
    mirror_mode: str
    mirror_field_name: str
    mirror_source: str
    table_object_hash: str
    semantic_adapter_hash: str
    row_count: int
    field_handle_count: int
    field_handle_nonzero_count: int
    field_handle_zero_count: int
    field_handle_hash: str
    semantic_field_hash: str
    mirror_handle_hash: str
    mirror_schema_hash: str
    mirror_ready: bool
    parity_ok_count: int
    parity_mismatch_count: int
    kernel_side_typed_consumer_compatible: bool
    current_wna16_arg_compatible: bool
    live_enabled: bool
    blocked: bool
    block_reason: str
    payload_bytes: int = 0
    ready_credit: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    live_compatible_with_current_wna16_args: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.mode == "readonly_single_field_handle_handoff_canary"
            and self.field_name in PREMAP_SINGLE_FIELD_HANDLE_HANDOFF_CANARY_FIELDS
            and self.source == "semantic_handle_table"
            and self.mirror_mode
            == premap_single_field_handle_handoff_mirror_mode(self.field_name)
            and self.mirror_field_name == self.field_name
            and self.mirror_source == self.source
            and bool(self.table_object_hash)
            and bool(self.semantic_adapter_hash)
            and int(self.row_count) > 0
            and int(self.field_handle_count) == int(self.row_count)
            and int(self.field_handle_nonzero_count) == int(self.row_count)
            and int(self.field_handle_zero_count) == 0
            and bool(self.field_handle_hash)
            and str(self.field_handle_hash) == str(self.semantic_field_hash)
            and str(self.mirror_handle_hash) == str(self.field_handle_hash)
            and str(self.mirror_schema_hash)
            == PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
            and bool(self.mirror_ready)
            and int(self.parity_ok_count) == int(self.row_count)
            and int(self.parity_mismatch_count) == 0
            and bool(self.kernel_side_typed_consumer_compatible)
            and not bool(self.current_wna16_arg_compatible)
            and not bool(self.live_enabled)
            and bool(self.blocked)
            and self.block_reason == "single_field_handoff_live_disabled"
            and int(self.payload_bytes) == 0
            and not bool(self.ready_credit)
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
            and not bool(self.live_compatible_with_current_wna16_args)
        )

    @property
    def canary_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "ready": bool(self.ready),
            "field_name": str(self.field_name),
            "source": str(self.source),
            "mirror_mode": str(self.mirror_mode),
            "mirror_field_name": str(self.mirror_field_name),
            "mirror_source": str(self.mirror_source),
            "table_object_hash": str(self.table_object_hash),
            "semantic_adapter_hash": str(self.semantic_adapter_hash),
            "row_count": int(self.row_count),
            "field_handle_count": int(self.field_handle_count),
            "field_handle_nonzero_count": int(self.field_handle_nonzero_count),
            "field_handle_zero_count": int(self.field_handle_zero_count),
            "field_handle_hash": str(self.field_handle_hash),
            "semantic_field_hash": str(self.semantic_field_hash),
            "mirror_handle_hash": str(self.mirror_handle_hash),
            "mirror_schema_hash": str(self.mirror_schema_hash),
            "mirror_ready": bool(self.mirror_ready),
            "parity_ok_count": int(self.parity_ok_count),
            "parity_mismatch_count": int(self.parity_mismatch_count),
            "kernel_side_typed_consumer_compatible": bool(
                self.kernel_side_typed_consumer_compatible
            ),
            "current_wna16_arg_compatible": bool(
                self.current_wna16_arg_compatible
            ),
            "live_enabled": bool(self.live_enabled),
            "blocked": bool(self.blocked),
            "block_reason": str(self.block_reason),
            "payload_bytes": int(self.payload_bytes),
            "ready_credit": bool(self.ready_credit),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
            "live_compatible_with_current_wna16_args": bool(
                self.live_compatible_with_current_wna16_args
            ),
        }


@dataclass(frozen=True)
class PremapKernelSideConsumerSchemaAdapterObject:
    """Readonly schema envelope for a future kernel-side consumer.

    The semantic adapter proves the prepared handle table has the right typed
    fields.  This object is the next boundary: it mirrors the schema a future
    fused-MoE/AWQ kernel-side consumer would receive, while explicitly keeping
    payload movement and kernel argument mutation disabled.  Live canaries may
    report enabled/connected states, but the adapter remains a blocked shadow
    object until a later kernel-side consumer is implemented.
    """

    mode: str
    semantic_adapter_hash: str
    semantic_adapter_ready: bool
    table_object_hash: str
    launch_schema_mirror_hash: str
    row_count: int
    column_count: int
    table_schema_hash: str
    semantic_schema_hash: str
    kernel_side_schema_name: str
    kernel_side_schema_hash: str
    kernel_side_field_count: int
    row_order_hash: str
    ordered_row_hash: str
    required_source_hit_count: int
    required_source_miss_count: int
    optional_source_hit_count: int
    optional_source_miss_count: int
    handle_field_read_count: int
    consumer_schema_present: bool
    consumer_connected: bool
    live_enabled: bool
    live_eligible: bool
    blocked: bool
    block_reason: str
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    live_compatible_with_current_wna16_args: bool = False

    @property
    def ready(self) -> bool:
        base_ok = (
            self.mode == "readonly_kernel_side_consumer_schema_adapter"
            and bool(self.semantic_adapter_hash)
            and bool(self.semantic_adapter_ready)
            and bool(self.table_object_hash)
            and bool(self.launch_schema_mirror_hash)
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(self.table_schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and str(self.semantic_schema_hash)
            == PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
            and str(self.kernel_side_schema_name)
            == PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME
            and str(self.kernel_side_schema_hash)
            == PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH
            and int(self.kernel_side_field_count)
            == len(PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS)
            and bool(self.row_order_hash)
            and bool(self.ordered_row_hash)
            and int(self.handle_field_read_count)
            == int(self.row_count)
            * len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and int(self.required_source_hit_count) == int(self.row_count) * 3
            and int(self.required_source_miss_count) == 0
            and int(self.optional_source_hit_count)
            + int(self.optional_source_miss_count)
            == int(self.row_count)
            and bool(self.consumer_schema_present)
            and bool(self.blocked)
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
            and not bool(self.live_compatible_with_current_wna16_args)
        )
        if not base_ok:
            return False
        if not bool(self.live_enabled):
            return (
                not bool(self.consumer_connected)
                and not bool(self.live_eligible)
                and str(self.block_reason) == "kernel_side_consumer_live_disabled"
            )
        if not bool(self.live_eligible):
            return (
                not bool(self.consumer_connected)
                and str(self.block_reason) == "kernel_side_consumer_not_eligible"
            )
        if not bool(self.consumer_connected):
            return str(self.block_reason) == "kernel_side_consumer_not_connected"
        return str(self.block_reason) in {
            "kernel_side_consumer_kernel_arg_pass_disabled",
            "kernel_side_consumer_shadow_only_kernel_arg_pass_enabled",
        }

    @property
    def adapter_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "ready": bool(self.ready),
            "semantic_adapter_hash": str(self.semantic_adapter_hash),
            "semantic_adapter_ready": bool(self.semantic_adapter_ready),
            "table_object_hash": str(self.table_object_hash),
            "launch_schema_mirror_hash": str(self.launch_schema_mirror_hash),
            "row_count": int(self.row_count),
            "column_count": int(self.column_count),
            "table_schema_hash": str(self.table_schema_hash),
            "semantic_schema_hash": str(self.semantic_schema_hash),
            "kernel_side_schema_name": str(self.kernel_side_schema_name),
            "kernel_side_schema_hash": str(self.kernel_side_schema_hash),
            "kernel_side_field_count": int(self.kernel_side_field_count),
            "row_order_hash": str(self.row_order_hash),
            "ordered_row_hash": str(self.ordered_row_hash),
            "required_source_hit_count": int(self.required_source_hit_count),
            "required_source_miss_count": int(self.required_source_miss_count),
            "optional_source_hit_count": int(self.optional_source_hit_count),
            "optional_source_miss_count": int(self.optional_source_miss_count),
            "handle_field_read_count": int(self.handle_field_read_count),
            "consumer_schema_present": bool(self.consumer_schema_present),
            "consumer_connected": bool(self.consumer_connected),
            "live_enabled": bool(self.live_enabled),
            "live_eligible": bool(self.live_eligible),
            "blocked": bool(self.blocked),
            "block_reason": str(self.block_reason),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
            "live_compatible_with_current_wna16_args": bool(
                self.live_compatible_with_current_wna16_args
            ),
        }


@dataclass(frozen=True)
class PremapKernelSideTypedConsumerObject:
    """Readonly typed object matching the future kernel-side consumer shape.

    This is one boundary closer to the eventual kernel consumer than the schema
    adapter: it binds the semantic handle hashes to a concrete typed object
    shape.  It is still a shadow-only object and must not move payload, mark
    ready residency, or mutate kernel launch arguments.
    """

    mode: str
    kernel_side_adapter_hash: str
    kernel_side_adapter_ready: bool
    semantic_adapter_hash: str
    table_object_hash: str
    launch_schema_mirror_hash: str
    row_count: int
    column_count: int
    table_schema_hash: str
    semantic_schema_hash: str
    kernel_side_schema_hash: str
    typed_consumer_schema_name: str
    typed_consumer_schema_hash: str
    typed_consumer_field_count: int
    row_order_hash: str
    ordered_row_hash: str
    descriptor_ptr_handle_hash: str
    packed_weight_descriptor_handle_hash: str
    scale_metadata_handle_hash: str
    aux_metadata_handle_hash: str
    required_source_hit_count: int
    required_source_miss_count: int
    optional_source_hit_count: int
    optional_source_miss_count: int
    handle_field_read_count: int
    consumer_object_present: bool
    consumer_connected: bool
    live_enabled: bool
    live_eligible: bool
    blocked: bool
    block_reason: str
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    live_compatible_with_current_wna16_args: bool = False

    @property
    def ready(self) -> bool:
        base_ok = (
            self.mode == "readonly_kernel_side_typed_consumer_object"
            and bool(self.kernel_side_adapter_hash)
            and bool(self.kernel_side_adapter_ready)
            and bool(self.semantic_adapter_hash)
            and bool(self.table_object_hash)
            and bool(self.launch_schema_mirror_hash)
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(self.table_schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and str(self.semantic_schema_hash)
            == PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
            and str(self.kernel_side_schema_hash)
            == PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH
            and str(self.typed_consumer_schema_name)
            == PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME
            and str(self.typed_consumer_schema_hash)
            == PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
            and int(self.typed_consumer_field_count)
            == len(PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_FIELDS)
            and bool(self.row_order_hash)
            and bool(self.ordered_row_hash)
            and bool(self.descriptor_ptr_handle_hash)
            and bool(self.packed_weight_descriptor_handle_hash)
            and bool(self.scale_metadata_handle_hash)
            and bool(self.aux_metadata_handle_hash)
            and int(self.handle_field_read_count)
            == int(self.row_count)
            * len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and int(self.required_source_hit_count) == int(self.row_count) * 3
            and int(self.required_source_miss_count) == 0
            and int(self.optional_source_hit_count)
            + int(self.optional_source_miss_count)
            == int(self.row_count)
            and bool(self.consumer_object_present)
            and bool(self.blocked)
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
            and not bool(self.live_compatible_with_current_wna16_args)
        )
        if not base_ok:
            return False
        if not bool(self.live_enabled):
            return (
                not bool(self.consumer_connected)
                and not bool(self.live_eligible)
                and str(self.block_reason)
                == "kernel_side_typed_consumer_live_disabled"
            )
        if not bool(self.live_eligible):
            return (
                not bool(self.consumer_connected)
                and str(self.block_reason)
                == "kernel_side_typed_consumer_not_eligible"
            )
        if not bool(self.consumer_connected):
            return (
                str(self.block_reason)
                == "kernel_side_typed_consumer_not_connected"
            )
        return str(self.block_reason) in {
            "kernel_side_typed_consumer_kernel_arg_pass_disabled",
            "kernel_side_typed_consumer_shadow_only_kernel_arg_pass_enabled",
        }

    @property
    def object_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "ready": bool(self.ready),
            "kernel_side_adapter_hash": str(self.kernel_side_adapter_hash),
            "kernel_side_adapter_ready": bool(self.kernel_side_adapter_ready),
            "semantic_adapter_hash": str(self.semantic_adapter_hash),
            "table_object_hash": str(self.table_object_hash),
            "launch_schema_mirror_hash": str(self.launch_schema_mirror_hash),
            "row_count": int(self.row_count),
            "column_count": int(self.column_count),
            "table_schema_hash": str(self.table_schema_hash),
            "semantic_schema_hash": str(self.semantic_schema_hash),
            "kernel_side_schema_hash": str(self.kernel_side_schema_hash),
            "typed_consumer_schema_name": str(self.typed_consumer_schema_name),
            "typed_consumer_schema_hash": str(self.typed_consumer_schema_hash),
            "typed_consumer_field_count": int(self.typed_consumer_field_count),
            "row_order_hash": str(self.row_order_hash),
            "ordered_row_hash": str(self.ordered_row_hash),
            "descriptor_ptr_handle_hash": str(self.descriptor_ptr_handle_hash),
            "packed_weight_descriptor_handle_hash": str(
                self.packed_weight_descriptor_handle_hash
            ),
            "scale_metadata_handle_hash": str(self.scale_metadata_handle_hash),
            "aux_metadata_handle_hash": str(self.aux_metadata_handle_hash),
            "required_source_hit_count": int(self.required_source_hit_count),
            "required_source_miss_count": int(self.required_source_miss_count),
            "optional_source_hit_count": int(self.optional_source_hit_count),
            "optional_source_miss_count": int(self.optional_source_miss_count),
            "handle_field_read_count": int(self.handle_field_read_count),
            "consumer_object_present": bool(self.consumer_object_present),
            "consumer_connected": bool(self.consumer_connected),
            "live_enabled": bool(self.live_enabled),
            "live_eligible": bool(self.live_eligible),
            "blocked": bool(self.blocked),
            "block_reason": str(self.block_reason),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
            "live_compatible_with_current_wna16_args": bool(
                self.live_compatible_with_current_wna16_args
            ),
        }


@dataclass(frozen=True)
class PremapKernelArgHandoffAttemptRecord:
    """No-op record for a future kernel-argument handoff attempt.

    This is intentionally one step past the mirror object: the runtime has a
    complete argument-package mirror, but the lab gate still blocks passing it
    to the live fused-MoE/AWQ kernel.  The record exists only for audit and
    fallback accounting.
    """

    mode: str
    mirror_hash: str
    slot_hash: str
    table_object_hash: str
    row_count: int
    column_count: int
    schema_hash: str
    mirror_ready: bool
    gate_allowed: bool
    blocked: bool
    block_reason: str
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False

    @property
    def record_ready(self) -> bool:
        return (
            self.mode == "readonly_kernel_arg_handoff_attempt"
            and bool(self.mirror_hash)
            and bool(self.slot_hash)
            and bool(self.table_object_hash)
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(self.schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and bool(self.mirror_ready)
            and not bool(self.gate_allowed)
            and bool(self.blocked)
            and str(self.block_reason) == "kernel_arg_handoff_disabled_noop_gate"
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
        )

    @property
    def attempt_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "record_ready": bool(self.record_ready),
            "mirror_hash": str(self.mirror_hash),
            "slot_hash": str(self.slot_hash),
            "table_object_hash": str(self.table_object_hash),
            "row_count": int(self.row_count),
            "column_count": int(self.column_count),
            "schema_hash": str(self.schema_hash),
            "mirror_ready": bool(self.mirror_ready),
            "gate_allowed": bool(self.gate_allowed),
            "blocked": bool(self.blocked),
            "block_reason": str(self.block_reason),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
        }


@dataclass(frozen=True)
class PremapKernelArgHandoffLiveToggleRecord:
    """Audit record for the default-disabled live kernel-arg handoff switch.

    The toggle is deliberately separate from the no-op handoff attempt.  It
    lets lab configs prove that a future live handoff switch exists and is
    gate-protected, while the current runtime still refuses to pass the mirror
    package to the fused-MoE/AWQ kernel.
    """

    mode: str
    attempt_hash: str
    table_object_hash: str
    enabled: bool
    lab_gate_passed: bool
    attempt_record_ready: bool
    live_eligible: bool
    blocked: bool
    block_reason: str
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False

    @property
    def record_ready(self) -> bool:
        base_ok = (
            self.mode == "readonly_kernel_arg_handoff_live_toggle"
            and bool(self.attempt_hash)
            and bool(self.table_object_hash)
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
        )
        if not base_ok:
            return False
        if not bool(self.enabled):
            return (
                bool(self.lab_gate_passed)
                and bool(self.attempt_record_ready)
                and not bool(self.live_eligible)
                and bool(self.blocked)
                and str(self.block_reason) == "kernel_arg_handoff_live_disabled"
            )
        if not bool(self.lab_gate_passed):
            return (
                not bool(self.live_eligible)
                and bool(self.blocked)
                and str(self.block_reason)
                == "kernel_arg_handoff_lab_gate_not_passed"
            )
        if not bool(self.attempt_record_ready):
            return (
                not bool(self.live_eligible)
                and bool(self.blocked)
                and str(self.block_reason)
                == "kernel_arg_handoff_attempt_not_ready"
            )
        return (
            bool(self.live_eligible)
            and bool(self.blocked)
            and str(self.block_reason)
            == "kernel_arg_handoff_kernel_consumer_not_connected"
        )

    @property
    def toggle_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "record_ready": bool(self.record_ready),
            "attempt_hash": str(self.attempt_hash),
            "table_object_hash": str(self.table_object_hash),
            "enabled": bool(self.enabled),
            "lab_gate_passed": bool(self.lab_gate_passed),
            "attempt_record_ready": bool(self.attempt_record_ready),
            "live_eligible": bool(self.live_eligible),
            "blocked": bool(self.blocked),
            "block_reason": str(self.block_reason),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
        }


@dataclass(frozen=True)
class PremapKernelArgHandoffLiveNoopIntegrationRecord:
    """Final no-op integration point before a real kernel-arg handoff.

    This record joins the live toggle with the launch-schema mirror.  It proves
    that the runtime can form the final handoff decision from the prepared
    table object without mutating the actual fused-MoE/AWQ kernel launch.
    """

    mode: str
    live_toggle_hash: str
    launch_schema_mirror_hash: str
    table_object_hash: str
    enabled: bool
    lab_gate_passed: bool
    live_toggle_record_ready: bool
    launch_schema_ready: bool
    live_eligible: bool
    consumer_connected: bool
    blocked: bool
    block_reason: str
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False

    @property
    def record_ready(self) -> bool:
        base_ok = (
            self.mode == "readonly_kernel_arg_handoff_live_noop_integration"
            and bool(self.live_toggle_hash)
            and bool(self.launch_schema_mirror_hash)
            and bool(self.table_object_hash)
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
            and bool(self.blocked)
        )
        if not base_ok:
            return False
        if not bool(self.enabled):
            return (
                bool(self.lab_gate_passed)
                and bool(self.live_toggle_record_ready)
                and bool(self.launch_schema_ready)
                and not bool(self.live_eligible)
                and str(self.block_reason) == "kernel_arg_handoff_live_disabled"
            )
        if not bool(self.lab_gate_passed):
            return (
                not bool(self.live_eligible)
                and str(self.block_reason)
                == "kernel_arg_handoff_lab_gate_not_passed"
            )
        if not bool(self.live_toggle_record_ready):
            return (
                not bool(self.live_eligible)
                and str(self.block_reason)
                == "kernel_arg_handoff_live_toggle_not_ready"
            )
        if not bool(self.launch_schema_ready):
            return (
                not bool(self.live_eligible)
                and str(self.block_reason)
                == "kernel_arg_handoff_launch_schema_not_ready"
            )
        return (
            bool(self.live_eligible)
            and (
                (
                    not bool(self.consumer_connected)
                    and str(self.block_reason)
                    == "kernel_arg_handoff_kernel_consumer_not_connected"
                )
                or (
                    bool(self.consumer_connected)
                    and str(self.block_reason)
                    == "kernel_arg_handoff_kernel_arg_pass_disabled"
                )
            )
        )

    @property
    def integration_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "record_ready": bool(self.record_ready),
            "live_toggle_hash": str(self.live_toggle_hash),
            "launch_schema_mirror_hash": str(self.launch_schema_mirror_hash),
            "table_object_hash": str(self.table_object_hash),
            "enabled": bool(self.enabled),
            "lab_gate_passed": bool(self.lab_gate_passed),
            "live_toggle_record_ready": bool(self.live_toggle_record_ready),
            "launch_schema_ready": bool(self.launch_schema_ready),
            "live_eligible": bool(self.live_eligible),
            "consumer_connected": bool(self.consumer_connected),
            "blocked": bool(self.blocked),
            "block_reason": str(self.block_reason),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
        }


@dataclass(frozen=True)
class PremapKernelArgHandoffLiveConsumerAdapterRecord:
    """No-op adapter envelope for a future live kernel-arg consumer.

    This is one step past the live no-op integration record: a prelaunch-side
    consumer adapter object exists and can observe the prepared handoff table.
    By default it remains blocked and read-only.  In the explicit live-pass
    gate, the adapter may accept the kernel-argument package while payload
    movement remains disabled.
    """

    mode: str
    live_noop_integration_hash: str
    launch_schema_mirror_hash: str
    table_object_hash: str
    enabled: bool
    lab_gate_passed: bool
    live_noop_integration_record_ready: bool
    live_noop_integration_blocked: bool
    live_noop_integration_block_reason: str
    consumer_adapter_present: bool
    consumer_connected: bool
    live_eligible: bool
    blocked: bool
    block_reason: str
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    adapter_contract_live_pass: bool = False
    real_kernel_arg_handoff: bool = False

    @property
    def record_ready(self) -> bool:
        base_ok = (
            self.mode == "readonly_kernel_arg_handoff_live_consumer_adapter"
            and bool(self.live_noop_integration_hash)
            and bool(self.launch_schema_mirror_hash)
            and bool(self.table_object_hash)
            and bool(self.consumer_adapter_present)
            and int(self.payload_bytes) == 0
        )
        if not base_ok:
            return False
        if not bool(self.live_noop_integration_record_ready):
            return (
                not bool(self.live_eligible)
                and str(self.block_reason)
                == "kernel_arg_handoff_live_noop_integration_not_ready"
            )
        if not bool(self.enabled):
            return (
                bool(self.lab_gate_passed)
                and bool(self.live_noop_integration_blocked)
                and str(self.live_noop_integration_block_reason)
                == "kernel_arg_handoff_live_disabled"
                and not bool(self.live_eligible)
                and str(self.block_reason) == "kernel_arg_handoff_live_disabled"
            )
        if not bool(self.lab_gate_passed):
            return (
                not bool(self.live_eligible)
                and str(self.block_reason)
                == "kernel_arg_handoff_lab_gate_not_passed"
            )
        if not bool(self.live_eligible):
            return False
        if not bool(self.consumer_connected):
            return (
                bool(self.blocked)
                and not bool(self.passed_to_kernel)
                and not bool(self.changes_kernel_launch_args)
                and str(self.block_reason)
                == "kernel_arg_handoff_kernel_consumer_not_connected"
            )
        if bool(self.passed_to_kernel) or bool(self.changes_kernel_launch_args):
            if bool(self.real_kernel_arg_handoff):
                return (
                    not bool(self.blocked)
                    and bool(self.passed_to_kernel)
                    and bool(self.changes_kernel_launch_args)
                    and bool(self.adapter_contract_live_pass)
                    and str(self.block_reason)
                    == "kernel_arg_handoff_real_kernel_arg_mutation_live"
                )
            return (
                not bool(self.blocked)
                and bool(self.passed_to_kernel)
                and bool(self.changes_kernel_launch_args)
                and bool(self.adapter_contract_live_pass)
                and not bool(self.real_kernel_arg_handoff)
                and str(self.block_reason)
                == "kernel_arg_handoff_kernel_arg_pass_live"
            )
        return (
            bool(self.blocked)
            and str(self.block_reason)
            == "kernel_arg_handoff_kernel_arg_pass_disabled"
        )

    @property
    def adapter_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def as_dict(self) -> dict[str, int | bool | str]:
        return {
            "mode": str(self.mode),
            "record_ready": bool(self.record_ready),
            "live_noop_integration_hash": str(self.live_noop_integration_hash),
            "launch_schema_mirror_hash": str(self.launch_schema_mirror_hash),
            "table_object_hash": str(self.table_object_hash),
            "enabled": bool(self.enabled),
            "lab_gate_passed": bool(self.lab_gate_passed),
            "live_noop_integration_record_ready": bool(
                self.live_noop_integration_record_ready
            ),
            "live_noop_integration_blocked": bool(
                self.live_noop_integration_blocked
            ),
            "live_noop_integration_block_reason": str(
                self.live_noop_integration_block_reason
            ),
            "consumer_adapter_present": bool(self.consumer_adapter_present),
            "consumer_connected": bool(self.consumer_connected),
            "live_eligible": bool(self.live_eligible),
            "blocked": bool(self.blocked),
            "block_reason": str(self.block_reason),
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
            "adapter_contract_live_pass": bool(self.adapter_contract_live_pass),
            "real_kernel_arg_handoff": bool(self.real_kernel_arg_handoff),
        }


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


@dataclass(frozen=True)
class PremapDescriptorPrepExecutionResult:
    """Read-only descriptor/address prep execution result.

    This is the smallest runtime-consumer contract above a pure lookup: the
    consumer resolves already prepared descriptor/address objects into concrete
    descriptor pointer, packed-weight descriptor, and scale metadata handles.
    It still does not transfer payloads, mutate cache residency, or grant ready
    credit.
    """

    execution_mode: str
    lookup_count: int
    prepared_handle_count: int
    missing_handle_count: int
    descriptor_ptr_count: int
    packed_weight_descriptor_count: int
    scale_metadata_handle_count: int
    payload_bytes: int
    ready_credit: bool
    changes_router: bool
    changes_descriptor_order: bool
    handle_hash: str | None
    execution_ok: bool
    real_descriptor_handle_count: int = 0
    real_descriptor_handle_miss_count: int = 0
    real_descriptor_handle_backed: bool = False
    real_descriptor_handle_hash: str | None = None
    consumer_object_count: int = 0
    consumer_object_hash: str | None = None
    consumer_object_hash_by_address_key: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, int | bool | str | None | dict[str, str]]:
        return asdict(self)


@dataclass(frozen=True)
class PremapDescriptorConsumerReadResult:
    """No-op runtime consumer read of descriptor prep objects.

    This models the prelaunch consumer dereferencing already-prepared
    descriptor/address objects.  It deliberately validates object availability
    and lifecycle parity only; it does not move payloads or mutate residency.
    """

    lookup_count: int
    object_hit_count: int
    object_miss_count: int
    stale_object_count: int
    checked_object_count: int
    object_hash: str | None
    read_ok: bool
    object_hash_by_address_key: dict[str, str] = field(default_factory=dict)
    payload_bytes: int = 0
    ready_credit: bool = False
    changes_router: bool = False
    changes_descriptor_order: bool = False

    def as_dict(self) -> dict[str, int | bool | str | None | dict[str, str]]:
        return asdict(self)


@dataclass(frozen=True)
class PremapKernelSideTypedRowConsumerPathCheck:
    """Readonly online check for the future kernel-side typed row consumer path.

    This mirrors the native stub's row-consumer contract at the vLLM prelaunch
    boundary without invoking a kernel, moving payloads, or mutating launch
    arguments.  It is intentionally a future-ABI check rather than a current
    WNA16 argument compatibility claim.
    """

    mode: str
    path_name: str
    source: str
    input_hash: str
    table_object_hash: str
    schema_hash: str
    row_count: int
    column_count: int
    row_ok_count: int
    error_count: int
    hash_accumulator: str
    failures: tuple[str, ...] = ()
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    current_wna16_arg_compatible: bool = False

    @property
    def checked(self) -> bool:
        return self.mode == PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_MODE

    @property
    def ready(self) -> bool:
        return (
            self.checked
            and self.path_name == PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_NAME
            and self.source == PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_SOURCE
            and bool(self.input_hash)
            and bool(self.table_object_hash)
            and self.schema_hash == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and int(self.row_ok_count) == int(self.row_count)
            and int(self.error_count) == 0
            and bool(self.hash_accumulator)
            and not self.failures
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
            and not bool(self.current_wna16_arg_compatible)
        )

    def as_dict(self) -> dict[str, int | bool | str | tuple[str, ...]]:
        return {
            "mode": self.mode,
            "path_name": self.path_name,
            "source": self.source,
            "checked": self.checked,
            "ready": self.ready,
            "input_hash": self.input_hash,
            "table_object_hash": self.table_object_hash,
            "schema_hash": self.schema_hash,
            "row_count": int(self.row_count),
            "column_count": int(self.column_count),
            "row_ok_count": int(self.row_ok_count),
            "error_count": int(self.error_count),
            "hash_accumulator": self.hash_accumulator,
            "failure_count": len(self.failures),
            "failures": self.failures,
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
            "current_wna16_arg_compatible": bool(
                self.current_wna16_arg_compatible
            ),
        }


@dataclass(frozen=True)
class PremapWna16AdjacentTypedSlotCheck:
    """Readonly online envelope for a future WNA16 typed-slot consumer.

    This is the vLLM-prelaunch producer-side counterpart of the standalone
    native stub's `PremapFutureKernelNativeConsumerWna16AdjacentTypedSlotV1`.
    It deliberately describes a future typed ABI slot instead of claiming
    compatibility with the current WNA16 tensor argument list.
    """

    name: str
    mode: str
    source: str
    input_hash: str
    table_object_hash: str
    schema_hash: str
    row_count: int
    row_ok_count: int
    error_count: int
    field_mask: int
    descriptor_ptr_read_row_ok_count: int
    packed_weight_descriptor_read_row_ok_count: int
    scale_metadata_handle_read_row_ok_count: int
    aux_metadata_handle_read_row_ok_count: int
    expert_id_read_row_ok_count: int
    address_key_hash_read_row_ok_count: int
    row_metadata_read_row_ok_count: int
    row_hash_accumulator: str
    field_read_hash_accumulator: str
    row_metadata_hash_accumulator: str
    failures: tuple[str, ...] = ()
    packet_chain_depth: int = PREMAP_WNA16_ADJACENT_TYPED_SLOT_PACKET_CHAIN_DEPTH
    payload_bytes: int = 0
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False
    current_wna16_arg_compatible: bool = False
    requires_wna16_arg_reinterpretation: bool = False
    explicit_typed_abi_slot: bool = True
    reuses_current_wna16_arg_slot: bool = False

    @property
    def checked(self) -> bool:
        return self.mode == PREMAP_WNA16_ADJACENT_TYPED_SLOT_MODE

    @property
    def all_handle_fields_read(self) -> bool:
        return (
            int(self.descriptor_ptr_read_row_ok_count) == int(self.row_count)
            and int(self.packed_weight_descriptor_read_row_ok_count)
            == int(self.row_count)
            and int(self.scale_metadata_handle_read_row_ok_count)
            == int(self.row_count)
            and int(self.aux_metadata_handle_read_row_ok_count) == int(self.row_count)
        )

    @property
    def ready(self) -> bool:
        return (
            self.checked
            and self.name == PREMAP_WNA16_ADJACENT_TYPED_SLOT_NAME
            and self.source == PREMAP_WNA16_ADJACENT_TYPED_SLOT_SOURCE
            and bool(self.input_hash)
            and bool(self.table_object_hash)
            and self.schema_hash == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and int(self.row_count) > 0
            and int(self.row_ok_count) == int(self.row_count)
            and int(self.error_count) == 0
            and int(self.field_mask) == PREMAP_WNA16_ADJACENT_TYPED_SLOT_FIELD_MASK
            and bool(self.all_handle_fields_read)
            and int(self.expert_id_read_row_ok_count) == int(self.row_count)
            and int(self.address_key_hash_read_row_ok_count) == int(self.row_count)
            and int(self.row_metadata_read_row_ok_count) == int(self.row_count)
            and int(self.packet_chain_depth)
            == PREMAP_WNA16_ADJACENT_TYPED_SLOT_PACKET_CHAIN_DEPTH
            and bool(self.row_hash_accumulator)
            and bool(self.field_read_hash_accumulator)
            and bool(self.row_metadata_hash_accumulator)
            and not self.failures
            and int(self.payload_bytes) == 0
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
            and not bool(self.current_wna16_arg_compatible)
            and not bool(self.requires_wna16_arg_reinterpretation)
            and bool(self.explicit_typed_abi_slot)
            and not bool(self.reuses_current_wna16_arg_slot)
        )

    def as_dict(self) -> dict[str, int | bool | str | tuple[str, ...]]:
        return {
            "name": self.name,
            "mode": self.mode,
            "source": self.source,
            "checked": self.checked,
            "ready": self.ready,
            "input_hash": self.input_hash,
            "table_object_hash": self.table_object_hash,
            "schema_hash": self.schema_hash,
            "row_count": int(self.row_count),
            "row_ok_count": int(self.row_ok_count),
            "error_count": int(self.error_count),
            "all_handle_fields_read": bool(self.all_handle_fields_read),
            "packet_chain_depth": int(self.packet_chain_depth),
            "field_mask": int(self.field_mask),
            "descriptor_ptr_read_row_ok_count": int(
                self.descriptor_ptr_read_row_ok_count
            ),
            "packed_weight_descriptor_read_row_ok_count": int(
                self.packed_weight_descriptor_read_row_ok_count
            ),
            "scale_metadata_handle_read_row_ok_count": int(
                self.scale_metadata_handle_read_row_ok_count
            ),
            "aux_metadata_handle_read_row_ok_count": int(
                self.aux_metadata_handle_read_row_ok_count
            ),
            "expert_id_read_row_ok_count": int(self.expert_id_read_row_ok_count),
            "address_key_hash_read_row_ok_count": int(
                self.address_key_hash_read_row_ok_count
            ),
            "row_metadata_read_row_ok_count": int(
                self.row_metadata_read_row_ok_count
            ),
            "row_hash_accumulator": self.row_hash_accumulator,
            "field_read_hash_accumulator": self.field_read_hash_accumulator,
            "row_metadata_hash_accumulator": self.row_metadata_hash_accumulator,
            "failure_count": len(self.failures),
            "failures": self.failures,
            "payload_bytes": int(self.payload_bytes),
            "passed_to_kernel": bool(self.passed_to_kernel),
            "changes_kernel_launch_args": bool(self.changes_kernel_launch_args),
            "current_wna16_arg_compatible": bool(
                self.current_wna16_arg_compatible
            ),
            "requires_wna16_arg_reinterpretation": bool(
                self.requires_wna16_arg_reinterpretation
            ),
            "explicit_typed_abi_slot": bool(self.explicit_typed_abi_slot),
            "reuses_current_wna16_arg_slot": bool(
                self.reuses_current_wna16_arg_slot
            ),
        }


@dataclass(frozen=True)
class PremapDescriptorConsumerShimResult:
    """Explicit no-op consumer shim for prepared descriptor objects.

    This is the handoff point immediately before a future real consumer would
    receive descriptor/address objects.  The current shim only validates that a
    readable object set exists and records that no runtime side effects were
    introduced.
    """

    execution_mode: str
    object_count: int
    object_hash: str | None
    read_ok: bool
    shim_ok: bool
    handle_table_row_count: int
    handle_table_column_count: int
    handle_table_schema_hash: str
    handle_table_read_ok: bool | None = None
    handle_table_lifecycle_ok: bool | None = None
    handle_table_per_row_parity_ok_count: int | None = None
    handle_table_row_miss_count: int | None = None
    handle_table_stale_row_count: int | None = None
    handle_table_passed_to_kernel: bool = False
    handle_table_payload_bytes: int = 0
    handle_table_consume_ok: bool | None = None
    handle_table_consume_lifecycle_ok: bool | None = None
    handle_table_consume_row_count: int | None = None
    handle_table_consume_column_count: int | None = None
    handle_table_consume_schema_hash: str | None = None
    handle_table_consume_mode: str | None = None
    handle_table_consume_source: str | None = None
    handle_table_consume_row_order_hash: str | None = None
    handle_table_consume_ordered_row_hash: str | None = None
    handle_table_consume_per_row_parity_ok_count: int | None = None
    handle_table_consume_row_miss_count: int | None = None
    handle_table_consume_stale_row_count: int | None = None
    handle_table_consume_handle_field_read_count: int | None = None
    handle_table_consume_required_handle_field_available_count: int | None = None
    handle_table_consume_optional_handle_field_available_count: int | None = None
    handle_table_consume_descriptor_ptr_field_read_count: int | None = None
    handle_table_consume_packed_weight_descriptor_field_read_count: int | None = None
    handle_table_consume_scale_metadata_handle_field_read_count: int | None = None
    handle_table_consume_aux_metadata_handle_field_read_count: int | None = None
    handle_table_consume_descriptor_ptr_field_available_count: int | None = None
    handle_table_consume_packed_weight_descriptor_field_available_count: int | None = None
    handle_table_consume_scale_metadata_handle_field_available_count: int | None = None
    handle_table_consume_aux_metadata_handle_field_available_count: int | None = None
    handle_table_consume_source_hit_counts: dict[str, int] | None = None
    handle_table_consume_source_miss_counts: dict[str, int] | None = None
    handle_table_consume_passed_to_kernel: bool = False
    handle_table_consume_payload_bytes: int = 0
    kernel_arg_handoff_dry_run_mode: str | None = None
    kernel_arg_handoff_dry_run_ready: bool | None = None
    kernel_arg_handoff_dry_run_row_count: int | None = None
    kernel_arg_handoff_dry_run_column_count: int | None = None
    kernel_arg_handoff_dry_run_schema_hash: str | None = None
    kernel_arg_handoff_dry_run_required_source_hit_count: int | None = None
    kernel_arg_handoff_dry_run_required_source_miss_count: int | None = None
    kernel_arg_handoff_dry_run_optional_source_hit_count: int | None = None
    kernel_arg_handoff_dry_run_optional_source_miss_count: int | None = None
    kernel_arg_handoff_dry_run_payload_bytes: int = 0
    kernel_arg_handoff_dry_run_passed_to_kernel: bool = False
    kernel_arg_handoff_shadow_slot_mode: str | None = None
    kernel_arg_handoff_shadow_slot_ready: bool | None = None
    kernel_arg_handoff_shadow_slot_hash: str | None = None
    kernel_arg_handoff_shadow_slot_table_object_hash: str | None = None
    kernel_arg_handoff_shadow_slot_row_count: int | None = None
    kernel_arg_handoff_shadow_slot_column_count: int | None = None
    kernel_arg_handoff_shadow_slot_schema_hash: str | None = None
    kernel_arg_handoff_shadow_slot_required_source_hit_count: int | None = None
    kernel_arg_handoff_shadow_slot_required_source_miss_count: int | None = None
    kernel_arg_handoff_shadow_slot_optional_source_hit_count: int | None = None
    kernel_arg_handoff_shadow_slot_optional_source_miss_count: int | None = None
    kernel_arg_handoff_shadow_slot_payload_bytes: int = 0
    kernel_arg_handoff_shadow_slot_passed_to_kernel: bool = False
    kernel_arg_handoff_shadow_slot_changes_kernel_launch_args: bool = False
    kernel_arg_handoff_mirror_mode: str | None = None
    kernel_arg_handoff_mirror_ready: bool | None = None
    kernel_arg_handoff_mirror_hash: str | None = None
    kernel_arg_handoff_mirror_slot_hash: str | None = None
    kernel_arg_handoff_mirror_table_object_hash: str | None = None
    kernel_arg_handoff_mirror_row_count: int | None = None
    kernel_arg_handoff_mirror_column_count: int | None = None
    kernel_arg_handoff_mirror_schema_hash: str | None = None
    kernel_arg_handoff_mirror_required_source_hit_count: int | None = None
    kernel_arg_handoff_mirror_required_source_miss_count: int | None = None
    kernel_arg_handoff_mirror_optional_source_hit_count: int | None = None
    kernel_arg_handoff_mirror_optional_source_miss_count: int | None = None
    kernel_arg_handoff_mirror_payload_bytes: int = 0
    kernel_arg_handoff_mirror_passed_to_kernel: bool = False
    kernel_arg_handoff_mirror_changes_kernel_launch_args: bool = False
    kernel_arg_handoff_launch_schema_mirror_mode: str | None = None
    kernel_arg_handoff_launch_schema_mirror_ready: bool | None = None
    kernel_arg_handoff_launch_schema_mirror_hash: str | None = None
    kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash: str | None = None
    kernel_arg_handoff_launch_schema_mirror_slot_hash: str | None = None
    kernel_arg_handoff_launch_schema_mirror_table_object_hash: str | None = None
    kernel_arg_handoff_launch_schema_mirror_row_count: int | None = None
    kernel_arg_handoff_launch_schema_mirror_column_count: int | None = None
    kernel_arg_handoff_launch_schema_mirror_table_schema_hash: str | None = None
    kernel_arg_handoff_launch_schema_mirror_launch_schema_name: str | None = None
    kernel_arg_handoff_launch_schema_mirror_launch_schema_hash: str | None = None
    kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count: int | None = None
    kernel_arg_handoff_launch_schema_mirror_required_source_hit_count: int | None = None
    kernel_arg_handoff_launch_schema_mirror_required_source_miss_count: int | None = None
    kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count: int | None = None
    kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count: int | None = None
    kernel_arg_handoff_launch_schema_mirror_handle_field_read_count: int | None = None
    kernel_arg_handoff_launch_schema_mirror_payload_bytes: int = 0
    kernel_arg_handoff_launch_schema_mirror_passed_to_kernel: bool = False
    kernel_arg_handoff_launch_schema_mirror_changes_kernel_launch_args: bool = False
    kernel_arg_handoff_attempt_mode: str | None = None
    kernel_arg_handoff_attempt_record_ready: bool | None = None
    kernel_arg_handoff_attempt_hash: str | None = None
    kernel_arg_handoff_attempt_mirror_hash: str | None = None
    kernel_arg_handoff_attempt_slot_hash: str | None = None
    kernel_arg_handoff_attempt_table_object_hash: str | None = None
    kernel_arg_handoff_attempt_row_count: int | None = None
    kernel_arg_handoff_attempt_column_count: int | None = None
    kernel_arg_handoff_attempt_schema_hash: str | None = None
    kernel_arg_handoff_attempt_mirror_ready: bool | None = None
    kernel_arg_handoff_attempt_gate_allowed: bool | None = None
    kernel_arg_handoff_attempt_blocked: bool | None = None
    kernel_arg_handoff_attempt_block_reason: str | None = None
    kernel_arg_handoff_attempt_payload_bytes: int = 0
    kernel_arg_handoff_attempt_passed_to_kernel: bool = False
    kernel_arg_handoff_attempt_changes_kernel_launch_args: bool = False
    kernel_arg_handoff_live_toggle_mode: str | None = None
    kernel_arg_handoff_live_toggle_record_ready: bool | None = None
    kernel_arg_handoff_live_toggle_hash: str | None = None
    kernel_arg_handoff_live_toggle_attempt_hash: str | None = None
    kernel_arg_handoff_live_toggle_table_object_hash: str | None = None
    kernel_arg_handoff_live_toggle_enabled: bool | None = None
    kernel_arg_handoff_live_toggle_lab_gate_passed: bool | None = None
    kernel_arg_handoff_live_toggle_attempt_record_ready: bool | None = None
    kernel_arg_handoff_live_toggle_live_eligible: bool | None = None
    kernel_arg_handoff_live_toggle_blocked: bool | None = None
    kernel_arg_handoff_live_toggle_block_reason: str | None = None
    kernel_arg_handoff_live_toggle_payload_bytes: int = 0
    kernel_arg_handoff_live_toggle_passed_to_kernel: bool = False
    kernel_arg_handoff_live_toggle_changes_kernel_launch_args: bool = False
    kernel_arg_handoff_live_noop_integration_mode: str | None = None
    kernel_arg_handoff_live_noop_integration_record_ready: bool | None = None
    kernel_arg_handoff_live_noop_integration_hash: str | None = None
    kernel_arg_handoff_live_noop_integration_live_toggle_hash: str | None = None
    kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash: (
        str | None
    ) = None
    kernel_arg_handoff_live_noop_integration_table_object_hash: str | None = None
    kernel_arg_handoff_live_noop_integration_enabled: bool | None = None
    kernel_arg_handoff_live_noop_integration_lab_gate_passed: bool | None = None
    kernel_arg_handoff_live_noop_integration_live_toggle_record_ready: (
        bool | None
    ) = None
    kernel_arg_handoff_live_noop_integration_launch_schema_ready: (
        bool | None
    ) = None
    kernel_arg_handoff_live_noop_integration_live_eligible: bool | None = None
    kernel_arg_handoff_live_noop_integration_consumer_connected: bool | None = None
    kernel_arg_handoff_live_noop_integration_blocked: bool | None = None
    kernel_arg_handoff_live_noop_integration_block_reason: str | None = None
    kernel_arg_handoff_live_noop_integration_payload_bytes: int = 0
    kernel_arg_handoff_live_noop_integration_passed_to_kernel: bool = False
    kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args: bool = False
    kernel_arg_handoff_live_consumer_adapter_mode: str | None = None
    kernel_arg_handoff_live_consumer_adapter_record_ready: bool | None = None
    kernel_arg_handoff_live_consumer_adapter_hash: str | None = None
    kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash: (
        str | None
    ) = None
    kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash: (
        str | None
    ) = None
    kernel_arg_handoff_live_consumer_adapter_table_object_hash: str | None = None
    kernel_arg_handoff_live_consumer_adapter_enabled: bool | None = None
    kernel_arg_handoff_live_consumer_adapter_lab_gate_passed: bool | None = None
    kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready: (
        bool | None
    ) = None
    kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked: (
        bool | None
    ) = None
    kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason: (
        str | None
    ) = None
    kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present: (
        bool | None
    ) = None
    kernel_arg_handoff_live_consumer_adapter_consumer_connected: bool | None = None
    kernel_arg_handoff_live_consumer_adapter_live_eligible: bool | None = None
    kernel_arg_handoff_live_consumer_adapter_blocked: bool | None = None
    kernel_arg_handoff_live_consumer_adapter_block_reason: str | None = None
    kernel_arg_handoff_live_consumer_adapter_payload_bytes: int = 0
    kernel_arg_handoff_live_consumer_adapter_passed_to_kernel: bool = False
    kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args: bool = False
    kernel_arg_handoff_live_consumer_adapter_contract_live_pass: bool = False
    kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff: bool = False
    kernel_arg_semantic_handle_adapter_mode: str | None = None
    kernel_arg_semantic_handle_adapter_ready: bool | None = None
    kernel_arg_semantic_handle_adapter_hash: str | None = None
    kernel_arg_semantic_handle_adapter_table_object_hash: str | None = None
    kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash: str | None = None
    kernel_arg_semantic_handle_adapter_row_count: int | None = None
    kernel_arg_semantic_handle_adapter_column_count: int | None = None
    kernel_arg_semantic_handle_adapter_table_schema_hash: str | None = None
    kernel_arg_semantic_handle_adapter_semantic_schema_name: str | None = None
    kernel_arg_semantic_handle_adapter_semantic_schema_hash: str | None = None
    kernel_arg_semantic_handle_adapter_semantic_field_count: int | None = None
    kernel_arg_semantic_handle_adapter_required_source_hit_count: int | None = None
    kernel_arg_semantic_handle_adapter_required_source_miss_count: int | None = None
    kernel_arg_semantic_handle_adapter_optional_source_hit_count: int | None = None
    kernel_arg_semantic_handle_adapter_optional_source_miss_count: int | None = None
    kernel_arg_semantic_handle_adapter_handle_field_read_count: int | None = None
    kernel_arg_semantic_handle_adapter_payload_bytes: int = 0
    kernel_arg_semantic_handle_adapter_passed_to_kernel: bool = False
    kernel_arg_semantic_handle_adapter_changes_kernel_launch_args: bool = False
    kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args: (
        bool
    ) = False
    single_field_handle_handoff_canary_mode: str | None = None
    single_field_handle_handoff_canary_ready: bool | None = None
    single_field_handle_handoff_canary_hash: str | None = None
    single_field_handle_handoff_canary_field_name: str | None = None
    single_field_handle_handoff_canary_source: str | None = None
    single_field_handle_handoff_canary_mirror_mode: str | None = None
    single_field_handle_handoff_canary_mirror_ready: bool | None = None
    single_field_handle_handoff_canary_mirror_field_name: str | None = None
    single_field_handle_handoff_canary_mirror_source: str | None = None
    single_field_handle_handoff_canary_table_object_hash: str | None = None
    single_field_handle_handoff_canary_semantic_adapter_hash: str | None = None
    single_field_handle_handoff_canary_row_count: int | None = None
    single_field_handle_handoff_canary_field_handle_count: int | None = None
    single_field_handle_handoff_canary_field_handle_nonzero_count: int | None = None
    single_field_handle_handoff_canary_field_handle_zero_count: int | None = None
    single_field_handle_handoff_canary_field_handle_hash: str | None = None
    single_field_handle_handoff_canary_semantic_field_hash: str | None = None
    single_field_handle_handoff_canary_mirror_handle_hash: str | None = None
    single_field_handle_handoff_canary_mirror_schema_hash: str | None = None
    single_field_handle_handoff_canary_parity_ok_count: int | None = None
    single_field_handle_handoff_canary_parity_mismatch_count: int | None = None
    single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible: (
        bool | None
    ) = None
    single_field_handle_handoff_canary_current_wna16_arg_compatible: (
        bool | None
    ) = None
    single_field_handle_handoff_canary_live_enabled: bool | None = None
    single_field_handle_handoff_canary_blocked: bool | None = None
    single_field_handle_handoff_canary_block_reason: str | None = None
    single_field_handle_handoff_canary_payload_bytes: int = 0
    single_field_handle_handoff_canary_ready_credit: bool = False
    single_field_handle_handoff_canary_passed_to_kernel: bool = False
    single_field_handle_handoff_canary_changes_kernel_launch_args: bool = False
    single_field_handle_handoff_canary_live_compatible_with_current_wna16_args: (
        bool
    ) = False
    kernel_side_consumer_schema_adapter_mode: str | None = None
    kernel_side_consumer_schema_adapter_ready: bool | None = None
    kernel_side_consumer_schema_adapter_hash: str | None = None
    kernel_side_consumer_schema_adapter_semantic_adapter_hash: str | None = None
    kernel_side_consumer_schema_adapter_table_object_hash: str | None = None
    kernel_side_consumer_schema_adapter_launch_schema_mirror_hash: str | None = None
    kernel_side_consumer_schema_adapter_row_count: int | None = None
    kernel_side_consumer_schema_adapter_column_count: int | None = None
    kernel_side_consumer_schema_adapter_table_schema_hash: str | None = None
    kernel_side_consumer_schema_adapter_semantic_schema_hash: str | None = None
    kernel_side_consumer_schema_adapter_kernel_side_schema_name: str | None = None
    kernel_side_consumer_schema_adapter_kernel_side_schema_hash: str | None = None
    kernel_side_consumer_schema_adapter_kernel_side_field_count: int | None = None
    kernel_side_consumer_schema_adapter_required_source_hit_count: int | None = None
    kernel_side_consumer_schema_adapter_required_source_miss_count: int | None = None
    kernel_side_consumer_schema_adapter_optional_source_hit_count: int | None = None
    kernel_side_consumer_schema_adapter_optional_source_miss_count: int | None = None
    kernel_side_consumer_schema_adapter_handle_field_read_count: int | None = None
    kernel_side_consumer_schema_adapter_consumer_schema_present: bool | None = None
    kernel_side_consumer_schema_adapter_consumer_connected: bool | None = None
    kernel_side_consumer_schema_adapter_live_enabled: bool | None = None
    kernel_side_consumer_schema_adapter_live_eligible: bool | None = None
    kernel_side_consumer_schema_adapter_blocked: bool | None = None
    kernel_side_consumer_schema_adapter_block_reason: str | None = None
    kernel_side_consumer_schema_adapter_payload_bytes: int = 0
    kernel_side_consumer_schema_adapter_passed_to_kernel: bool = False
    kernel_side_consumer_schema_adapter_changes_kernel_launch_args: bool = False
    kernel_side_consumer_schema_adapter_live_compatible_with_current_wna16_args: (
        bool
    ) = False
    kernel_side_typed_consumer_object_mode: str | None = None
    kernel_side_typed_consumer_object_ready: bool | None = None
    kernel_side_typed_consumer_object_hash: str | None = None
    kernel_side_typed_consumer_object_kernel_side_adapter_hash: str | None = None
    kernel_side_typed_consumer_object_semantic_adapter_hash: str | None = None
    kernel_side_typed_consumer_object_table_object_hash: str | None = None
    kernel_side_typed_consumer_object_launch_schema_mirror_hash: str | None = None
    kernel_side_typed_consumer_object_row_count: int | None = None
    kernel_side_typed_consumer_object_column_count: int | None = None
    kernel_side_typed_consumer_object_table_schema_hash: str | None = None
    kernel_side_typed_consumer_object_semantic_schema_hash: str | None = None
    kernel_side_typed_consumer_object_kernel_side_schema_hash: str | None = None
    kernel_side_typed_consumer_object_typed_consumer_schema_name: str | None = None
    kernel_side_typed_consumer_object_typed_consumer_schema_hash: str | None = None
    kernel_side_typed_consumer_object_typed_consumer_field_count: int | None = None
    kernel_side_typed_consumer_object_required_source_hit_count: int | None = None
    kernel_side_typed_consumer_object_required_source_miss_count: int | None = None
    kernel_side_typed_consumer_object_optional_source_hit_count: int | None = None
    kernel_side_typed_consumer_object_optional_source_miss_count: int | None = None
    kernel_side_typed_consumer_object_handle_field_read_count: int | None = None
    kernel_side_typed_consumer_object_consumer_object_present: bool | None = None
    kernel_side_typed_consumer_object_consumer_connected: bool | None = None
    kernel_side_typed_consumer_object_live_enabled: bool | None = None
    kernel_side_typed_consumer_object_live_eligible: bool | None = None
    kernel_side_typed_consumer_object_blocked: bool | None = None
    kernel_side_typed_consumer_object_block_reason: str | None = None
    kernel_side_typed_consumer_object_payload_bytes: int = 0
    kernel_side_typed_consumer_object_passed_to_kernel: bool = False
    kernel_side_typed_consumer_object_changes_kernel_launch_args: bool = False
    kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args: (
        bool
    ) = False
    native_typed_consumer_bridge_mode: str | None = None
    native_typed_consumer_bridge_checked: bool | None = None
    native_typed_consumer_bridge_ok: bool | None = None
    native_typed_consumer_bridge_input_hash: str | None = None
    native_typed_consumer_bridge_table_object_hash: str | None = None
    native_typed_consumer_bridge_schema_hash: str | None = None
    native_typed_consumer_bridge_row_count: int | None = None
    native_typed_consumer_bridge_column_count: int | None = None
    native_typed_consumer_bridge_required_handle_nonzero_count: int | None = None
    native_typed_consumer_bridge_required_handle_zero_count: int | None = None
    native_typed_consumer_bridge_optional_handle_nonzero_count: int | None = None
    native_typed_consumer_bridge_optional_handle_zero_count: int | None = None
    native_typed_consumer_bridge_expert_id_valid_count: int | None = None
    native_typed_consumer_bridge_expert_id_invalid_count: int | None = None
    native_typed_consumer_bridge_address_key_hash_nonzero_count: int | None = None
    native_typed_consumer_bridge_address_key_hash_zero_count: int | None = None
    native_typed_consumer_bridge_failure_count: int | None = None
    native_typed_consumer_bridge_failures: tuple[str, ...] | None = None
    native_typed_consumer_bridge_payload_bytes: int = 0
    native_typed_consumer_bridge_ready_credit: bool = False
    native_typed_consumer_bridge_changes_router: bool = False
    native_typed_consumer_bridge_changes_descriptor_order: bool = False
    native_typed_consumer_bridge_passed_to_kernel: bool = False
    native_typed_consumer_bridge_changes_kernel_launch_args: bool = False
    native_stub_online_invocation_mode: str | None = None
    native_stub_online_invocation_checked: bool | None = None
    native_stub_online_invocation_ready: bool | None = None
    native_stub_online_invocation_ok: bool | None = None
    native_stub_online_invocation_native_checker_invoked: bool | None = None
    native_stub_online_invocation_native_bridge_ok: bool | None = None
    native_stub_online_invocation_package_hash: str | None = None
    native_stub_online_invocation_input_hash: str | None = None
    native_stub_online_invocation_table_object_hash: str | None = None
    native_stub_online_invocation_schema_hash: str | None = None
    native_stub_online_invocation_row_count: int | None = None
    native_stub_online_invocation_column_count: int | None = None
    native_stub_online_invocation_required_handle_nonzero_count: int | None = None
    native_stub_online_invocation_required_handle_zero_count: int | None = None
    native_stub_online_invocation_optional_handle_nonzero_count: int | None = None
    native_stub_online_invocation_optional_handle_zero_count: int | None = None
    native_stub_online_invocation_expert_id_valid_count: int | None = None
    native_stub_online_invocation_expert_id_invalid_count: int | None = None
    native_stub_online_invocation_address_key_hash_nonzero_count: int | None = None
    native_stub_online_invocation_address_key_hash_zero_count: int | None = None
    native_stub_online_invocation_requested: bool | None = None
    native_stub_online_invocation_native_stub_invoked: bool | None = None
    native_stub_online_invocation_blocked: bool | None = None
    native_stub_online_invocation_block_reason: str | None = None
    native_stub_online_invocation_failure_count: int | None = None
    native_stub_online_invocation_failures: tuple[str, ...] | None = None
    native_stub_online_invocation_payload_bytes: int = 0
    native_stub_online_invocation_ready_credit: bool = False
    native_stub_online_invocation_changes_router: bool = False
    native_stub_online_invocation_changes_descriptor_order: bool = False
    native_stub_online_invocation_passed_to_kernel: bool = False
    native_stub_online_invocation_changes_kernel_launch_args: bool = False
    kernel_side_typed_row_consumer_path_mode: str | None = None
    kernel_side_typed_row_consumer_path_name: str | None = None
    kernel_side_typed_row_consumer_path_source: str | None = None
    kernel_side_typed_row_consumer_path_checked: bool | None = None
    kernel_side_typed_row_consumer_path_ready: bool | None = None
    kernel_side_typed_row_consumer_path_input_hash: str | None = None
    kernel_side_typed_row_consumer_path_table_object_hash: str | None = None
    kernel_side_typed_row_consumer_path_schema_hash: str | None = None
    kernel_side_typed_row_consumer_path_row_count: int | None = None
    kernel_side_typed_row_consumer_path_column_count: int | None = None
    kernel_side_typed_row_consumer_path_row_ok_count: int | None = None
    kernel_side_typed_row_consumer_path_error_count: int | None = None
    kernel_side_typed_row_consumer_path_hash_accumulator: str | None = None
    kernel_side_typed_row_consumer_path_failure_count: int | None = None
    kernel_side_typed_row_consumer_path_failures: tuple[str, ...] | None = None
    kernel_side_typed_row_consumer_path_payload_bytes: int = 0
    kernel_side_typed_row_consumer_path_passed_to_kernel: bool = False
    kernel_side_typed_row_consumer_path_changes_kernel_launch_args: bool = False
    kernel_side_typed_row_consumer_path_current_wna16_arg_compatible: bool = False
    wna16_adjacent_typed_slot_name: str | None = None
    wna16_adjacent_typed_slot_mode: str | None = None
    wna16_adjacent_typed_slot_source: str | None = None
    wna16_adjacent_typed_slot_checked: bool | None = None
    wna16_adjacent_typed_slot_ready: bool | None = None
    wna16_adjacent_typed_slot_input_hash: str | None = None
    wna16_adjacent_typed_slot_table_object_hash: str | None = None
    wna16_adjacent_typed_slot_schema_hash: str | None = None
    wna16_adjacent_typed_slot_row_count: int | None = None
    wna16_adjacent_typed_slot_row_ok_count: int | None = None
    wna16_adjacent_typed_slot_error_count: int | None = None
    wna16_adjacent_typed_slot_all_handle_fields_read: bool | None = None
    wna16_adjacent_typed_slot_packet_chain_depth: int | None = None
    wna16_adjacent_typed_slot_field_mask: int | None = None
    wna16_adjacent_typed_slot_descriptor_ptr_read_row_ok_count: int | None = None
    wna16_adjacent_typed_slot_packed_weight_descriptor_read_row_ok_count: (
        int | None
    ) = None
    wna16_adjacent_typed_slot_scale_metadata_handle_read_row_ok_count: (
        int | None
    ) = None
    wna16_adjacent_typed_slot_aux_metadata_handle_read_row_ok_count: int | None = None
    wna16_adjacent_typed_slot_expert_id_read_row_ok_count: int | None = None
    wna16_adjacent_typed_slot_address_key_hash_read_row_ok_count: int | None = None
    wna16_adjacent_typed_slot_row_metadata_read_row_ok_count: int | None = None
    wna16_adjacent_typed_slot_row_hash_accumulator: str | None = None
    wna16_adjacent_typed_slot_field_read_hash_accumulator: str | None = None
    wna16_adjacent_typed_slot_row_metadata_hash_accumulator: str | None = None
    wna16_adjacent_typed_slot_failure_count: int | None = None
    wna16_adjacent_typed_slot_failures: tuple[str, ...] | None = None
    wna16_adjacent_typed_slot_payload_bytes: int = 0
    wna16_adjacent_typed_slot_passed_to_kernel: bool = False
    wna16_adjacent_typed_slot_changes_kernel_launch_args: bool = False
    wna16_adjacent_typed_slot_current_wna16_arg_compatible: bool = False
    wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation: bool = False
    wna16_adjacent_typed_slot_explicit_typed_abi_slot: bool = True
    wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot: bool = False
    handle_table_object_consumed: bool | None = None
    handle_table_object_hash: str | None = None
    handle_table_object_row_count: int | None = None
    handle_table_object_lifecycle_ok: bool | None = None
    handle_table_object_passed_to_kernel: bool = False
    handle_table_object_payload_bytes: int = 0
    prep_execution_dry_run_mode: str | None = None
    prep_execution_dry_run_source: str | None = None
    prep_execution_dry_run_ok: bool | None = None
    prep_execution_dry_run_row_count: int | None = None
    prep_execution_dry_run_column_count: int | None = None
    prep_execution_dry_run_schema_hash: str | None = None
    prep_execution_dry_run_object_hash: str | None = None
    prep_execution_dry_run_lifecycle_ok: bool | None = None
    prep_execution_dry_run_row_handle_parity_ok_count: int | None = None
    prep_execution_dry_run_descriptor_ptr_parity_ok_count: int | None = None
    prep_execution_dry_run_packed_weight_descriptor_parity_ok_count: int | None = None
    prep_execution_dry_run_scale_metadata_handle_parity_ok_count: int | None = None
    prep_execution_dry_run_aux_metadata_handle_parity_ok_count: int | None = None
    prep_execution_dry_run_row_handle_miss_count: int | None = None
    prep_execution_dry_run_handle_field_read_count: int | None = None
    prep_execution_dry_run_required_handle_field_available_count: int | None = None
    prep_execution_dry_run_optional_handle_field_available_count: int | None = None
    prep_execution_dry_run_descriptor_ptr_field_read_count: int | None = None
    prep_execution_dry_run_packed_weight_descriptor_field_read_count: int | None = None
    prep_execution_dry_run_scale_metadata_handle_field_read_count: int | None = None
    prep_execution_dry_run_aux_metadata_handle_field_read_count: int | None = None
    prep_execution_dry_run_descriptor_ptr_field_available_count: int | None = None
    prep_execution_dry_run_packed_weight_descriptor_field_available_count: int | None = None
    prep_execution_dry_run_scale_metadata_handle_field_available_count: int | None = None
    prep_execution_dry_run_aux_metadata_handle_field_available_count: int | None = None
    prep_execution_dry_run_passed_to_kernel: bool = False
    prep_execution_dry_run_payload_bytes: int = 0
    payload_bytes: int = 0
    ready_credit: bool = False
    changes_router: bool = False
    changes_descriptor_order: bool = False
    changes_kernel_launch_args: bool = False

    def as_dict(self) -> dict[str, int | bool | str | None]:
        return asdict(self)


@dataclass(frozen=True)
class PremapDescriptorAddressPrepDryRunResult:
    """Readonly execution-shaped descriptor/address prep contract.

    This is the smallest consumer-side execution object before a real kernel
    handoff.  It validates the already-prepared handle table shape and identity
    but deliberately does not pass the table to a kernel or move payload bytes.
    """

    execution_mode: str
    source: str
    row_count: int
    column_count: int
    schema_hash: str
    table_object_hash: str
    row_order_hash: str
    ordered_row_hash: str
    lifecycle_ok: bool
    execution_ok: bool
    row_handle_parity_ok_count: int
    descriptor_ptr_parity_ok_count: int
    packed_weight_descriptor_parity_ok_count: int
    scale_metadata_handle_parity_ok_count: int
    aux_metadata_handle_parity_ok_count: int
    row_handle_miss_count: int
    handle_field_read_count: int
    required_handle_field_available_count: int
    optional_handle_field_available_count: int
    descriptor_ptr_field_read_count: int
    packed_weight_descriptor_field_read_count: int
    scale_metadata_handle_field_read_count: int
    aux_metadata_handle_field_read_count: int
    descriptor_ptr_field_available_count: int
    packed_weight_descriptor_field_available_count: int
    scale_metadata_handle_field_available_count: int
    aux_metadata_handle_field_available_count: int
    payload_bytes: int = 0
    ready_credit: bool = False
    changes_router: bool = False
    changes_descriptor_order: bool = False
    changes_kernel_launch_args: bool = False
    passed_to_kernel: bool = False

    def as_dict(self) -> dict[str, int | bool | str]:
        return asdict(self)


@dataclass(frozen=True)
class PremapKernelArgShadowTableResult:
    """No-op shadow table for future kernel argument handoff.

    This object records the shape and row-order/parity hashes of the table that
    a real kernel integration could consume later.  The table is not passed to
    any kernel in this path.
    """

    execution_mode: str
    row_order_source: str
    row_count: int
    column_count: int
    schema_hash: str
    row_order_hash: str
    ordered_row_hash: str
    per_row_parity_ok_count: int
    row_miss_count: int
    stale_row_count: int
    lifecycle_ok: bool
    table_ok: bool
    payload_bytes: int = 0
    ready_credit: bool = False
    changes_router: bool = False
    changes_descriptor_order: bool = False
    changes_kernel_launch_args: bool = False
    passed_to_kernel: bool = False

    def as_dict(self) -> dict[str, int | bool | str | None]:
        return asdict(self)


@dataclass(frozen=True)
class PremapNativeTypedConsumerBridgeCheck:
    """Readonly checker for the native typed-consumer input bridge.

    This mirrors the cheap contract checks performed by the standalone HIP
    typed-consumer stub, but stays in-process for the vLLM prelaunch no-op
    path.  It validates the table-to-native-input shape only; it does not call
    a kernel, dereference payloads, or mutate launch arguments.
    """

    mode: str
    input_hash: str
    table_object_hash: str
    schema_hash: str
    row_count: int
    column_count: int
    required_handle_nonzero_count: int
    required_handle_zero_count: int
    optional_handle_nonzero_count: int
    optional_handle_zero_count: int
    expert_id_valid_count: int
    expert_id_invalid_count: int
    address_key_hash_nonzero_count: int
    address_key_hash_zero_count: int
    failures: tuple[str, ...] = ()
    payload_bytes: int = 0
    ready_credit: bool = False
    changes_router: bool = False
    changes_descriptor_order: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False

    @property
    def ok(self) -> bool:
        return (
            self.mode == "readonly_native_typed_consumer_bridge_check"
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(self.schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and bool(self.input_hash)
            and bool(self.table_object_hash)
            and int(self.required_handle_nonzero_count) == int(self.row_count) * 3
            and int(self.required_handle_zero_count) == 0
            and int(self.optional_handle_nonzero_count)
            + int(self.optional_handle_zero_count)
            == int(self.row_count)
            and int(self.expert_id_valid_count) == int(self.row_count)
            and int(self.expert_id_invalid_count) == 0
            and int(self.address_key_hash_nonzero_count) == int(self.row_count)
            and int(self.address_key_hash_zero_count) == 0
            and int(self.payload_bytes) == 0
            and not bool(self.ready_credit)
            and not bool(self.changes_router)
            and not bool(self.changes_descriptor_order)
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
            and not self.failures
        )

    def as_dict(self) -> dict[str, int | bool | str | tuple[str, ...]]:
        payload = asdict(self)
        payload["ok"] = bool(self.ok)
        return payload


@dataclass(frozen=True)
class PremapNativeStubOnlineInvocationCanary:
    """Live-disabled native-stub invocation package for online prelaunch checks.

    The vLLM prelaunch shim already has a Python-side native bridge checker.
    This object records the next boundary: the exact typed-consumer input that
    a native checker/stub would consume.  The package is constructed and hashed,
    but live invocation is intentionally blocked here: no HIP stub is launched,
    no payload is dereferenced, and no real WNA16 kernel arguments are touched.
    """

    mode: str
    native_checker_invoked: bool
    native_bridge_ok: bool
    package_hash: str
    input_hash: str
    table_object_hash: str
    schema_hash: str
    row_count: int
    column_count: int
    required_handle_nonzero_count: int
    required_handle_zero_count: int
    optional_handle_nonzero_count: int
    optional_handle_zero_count: int
    expert_id_valid_count: int
    expert_id_invalid_count: int
    address_key_hash_nonzero_count: int
    address_key_hash_zero_count: int
    invocation_requested: bool
    native_stub_invoked: bool
    invocation_blocked: bool
    invocation_block_reason: str
    failures: tuple[str, ...] = ()
    payload_bytes: int = 0
    ready_credit: bool = False
    changes_router: bool = False
    changes_descriptor_order: bool = False
    passed_to_kernel: bool = False
    changes_kernel_launch_args: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.mode == "readonly_native_stub_online_invocation_canary"
            and bool(self.native_checker_invoked)
            and bool(self.native_bridge_ok)
            and bool(self.package_hash)
            and bool(self.input_hash)
            and bool(self.table_object_hash)
            and int(self.row_count) > 0
            and int(self.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(self.schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and int(self.required_handle_nonzero_count) == int(self.row_count) * 3
            and int(self.required_handle_zero_count) == 0
            and int(self.optional_handle_nonzero_count)
            + int(self.optional_handle_zero_count)
            == int(self.row_count)
            and int(self.expert_id_valid_count) == int(self.row_count)
            and int(self.expert_id_invalid_count) == 0
            and int(self.address_key_hash_nonzero_count) == int(self.row_count)
            and int(self.address_key_hash_zero_count) == 0
            and bool(self.invocation_requested)
            and not bool(self.native_stub_invoked)
            and bool(self.invocation_blocked)
            and self.invocation_block_reason == "native_stub_live_disabled"
            and int(self.payload_bytes) == 0
            and not bool(self.ready_credit)
            and not bool(self.changes_router)
            and not bool(self.changes_descriptor_order)
            and not bool(self.passed_to_kernel)
            and not bool(self.changes_kernel_launch_args)
            and not self.failures
        )

    @property
    def ok(self) -> bool:
        return bool(self.ready)

    def as_dict(self) -> dict[str, int | bool | str | tuple[str, ...]]:
        payload = asdict(self)
        payload["ready"] = bool(self.ready)
        payload["ok"] = bool(self.ok)
        return payload


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

    def execute_descriptor_prep_readonly(
        self,
        address_keys: Iterable[str],
        *,
        execution_mode: str = "readonly_descriptor_address_object",
        real_descriptor_handles_by_address_key: (
            dict[str, PremapRealDescriptorHandle] | None
        ) = None,
    ) -> PremapDescriptorPrepExecutionResult:
        """Resolve prepared descriptor/address objects for a runtime consumer.

        The method deliberately reads the existing entries directly instead of
        using `resolve_address_key()`, to make the no-mutation contract explicit:
        no LRU move, no payload movement, and no ready-credit side effect.
        """

        lookup_count = 0
        prepared_handle_count = 0
        missing_handle_count = 0
        descriptor_ptr_count = 0
        packed_weight_descriptor_count = 0
        scale_metadata_handle_count = 0
        real_descriptor_handle_count = 0
        real_descriptor_handle_miss_count = 0
        payload_bytes = 0
        hash_parts: list[str] = []
        real_hash_parts: list[str] = []
        consumer_object_hashes: list[str] = []
        consumer_object_hash_by_address_key: dict[str, str] = {}
        real_handles = real_descriptor_handles_by_address_key
        for raw_key in address_keys:
            lookup_count += 1
            key = str(raw_key)
            entry = self._addresses.get(key)
            if entry is None:
                missing_handle_count += 1
                continue
            handle = entry.handle
            real_handle = real_handles.get(key) if real_handles is not None else None
            if real_handles is not None:
                if real_handle is None or (
                    real_handle.address_key is not None
                    and str(real_handle.address_key) != key
                ):
                    real_descriptor_handle_miss_count += 1
                    continue
                real_descriptor_handle_count += 1
                real_hash_parts.append(
                    "|".join(
                        str(part)
                        for part in (
                            key,
                            real_handle.expert_id,
                            real_handle.local_expert_id,
                            real_handle.address_key,
                            real_handle.handle_hash,
                            real_handle.packed_weight_descriptor,
                            real_handle.scale_metadata_handle,
                            real_handle.aux_metadata_handle,
                        )
                    )
                )
            prepared_handle_count += 1
            payload_bytes += int(handle.payload_bytes)
            if real_handle is not None:
                payload_bytes += int(real_handle.payload_bytes)
            hash_parts.append(f"address_key:{key}")
            descriptor_ptr = (
                real_handle.descriptor_ptr if real_handle is not None else handle.descriptor_ptr
            )
            if descriptor_ptr:
                descriptor_ptr_count += 1
                hash_parts.append(f"descriptor_ptr:{descriptor_ptr}")
            packed_descriptor = (
                real_handle.packed_weight_descriptor
                if real_handle is not None
                else handle.packed_weight_descriptor
            )
            if packed_descriptor:
                packed_weight_descriptor_count += 1
                hash_parts.append(f"packed_weight_descriptor:{packed_descriptor}")
            scale_descriptor = (
                real_handle.scale_metadata_handle
                if real_handle is not None
                else handle.scale_metadata_handle
            )
            if scale_descriptor:
                scale_metadata_handle_count += 1
                hash_parts.append(f"scale_metadata_handle:{scale_descriptor}")
            hash_parts.append(f"handle_hash:{handle.handle_hash}")
            if real_handle is not None:
                hash_parts.append(f"real_handle_hash:{real_handle.handle_hash}")
            consumer_object = self._build_descriptor_consumer_object(
                key=key,
                handle=handle,
                real_handle=real_handle,
            )
            if consumer_object is not None:
                consumer_object_hashes.append(consumer_object.object_hash)
                consumer_object_hash_by_address_key[key] = consumer_object.object_hash
        handle_hash = None
        if hash_parts:
            payload = "|".join(sorted(hash_parts)).encode("utf-8")
            handle_hash = hashlib.sha256(payload).hexdigest()
        real_descriptor_handle_hash = None
        if real_hash_parts:
            real_payload = "|".join(sorted(real_hash_parts)).encode("utf-8")
            real_descriptor_handle_hash = hashlib.sha256(real_payload).hexdigest()
        consumer_object_hash = None
        if consumer_object_hashes:
            object_payload = "|".join(sorted(consumer_object_hashes)).encode("utf-8")
            consumer_object_hash = hashlib.sha256(object_payload).hexdigest()
        real_backed = real_handles is not None
        real_ok = (
            not real_backed
            or (
                real_descriptor_handle_count == prepared_handle_count
                and real_descriptor_handle_miss_count == 0
            )
        )
        consumer_object_count = len(consumer_object_hashes)
        return PremapDescriptorPrepExecutionResult(
            execution_mode=str(execution_mode),
            lookup_count=lookup_count,
            prepared_handle_count=prepared_handle_count,
            missing_handle_count=missing_handle_count,
            descriptor_ptr_count=descriptor_ptr_count,
            packed_weight_descriptor_count=packed_weight_descriptor_count,
            scale_metadata_handle_count=scale_metadata_handle_count,
            real_descriptor_handle_count=real_descriptor_handle_count,
            real_descriptor_handle_miss_count=real_descriptor_handle_miss_count,
            real_descriptor_handle_backed=real_backed,
            real_descriptor_handle_hash=real_descriptor_handle_hash,
            consumer_object_count=consumer_object_count,
            consumer_object_hash=consumer_object_hash,
            consumer_object_hash_by_address_key=consumer_object_hash_by_address_key,
            payload_bytes=payload_bytes,
            ready_credit=False,
            changes_router=False,
            changes_descriptor_order=False,
            handle_hash=handle_hash,
            execution_ok=(
                lookup_count > 0
                and missing_handle_count == 0
                and payload_bytes == 0
                and descriptor_ptr_count == prepared_handle_count
                and packed_weight_descriptor_count == prepared_handle_count
                and scale_metadata_handle_count == prepared_handle_count
                and consumer_object_count == prepared_handle_count
                and real_ok
            ),
        )

    def read_descriptor_consumer_objects_readonly(
        self,
        address_keys: Iterable[str],
        *,
        expected_object_hash_by_address_key: dict[str, str] | None = None,
        real_descriptor_handles_by_address_key: (
            dict[str, PremapRealDescriptorHandle] | None
        ) = None,
    ) -> PremapDescriptorConsumerReadResult:
        """Read prepared descriptor objects from the prelaunch consumer handle.

        The result verifies that the same object-shaped descriptor/address
        handles remain readable after prep.  It is still a strict no-op:
        no LRU update, no payload movement, no ready credit, and no router/order
        mutation.
        """

        expected = expected_object_hash_by_address_key or {}
        real_handles = real_descriptor_handles_by_address_key
        lookup_count = 0
        object_hit_count = 0
        object_miss_count = 0
        stale_object_count = 0
        checked_object_count = 0
        payload_bytes = 0
        object_hashes: list[str] = []
        object_hash_by_address_key: dict[str, str] = {}
        for raw_key in address_keys:
            lookup_count += 1
            key = str(raw_key)
            entry = self._addresses.get(key)
            if entry is None:
                object_miss_count += 1
                continue
            handle = entry.handle
            real_handle = real_handles.get(key) if real_handles is not None else None
            if real_handles is not None and (
                real_handle is None
                or (
                    real_handle.address_key is not None
                    and str(real_handle.address_key) != key
                )
            ):
                object_miss_count += 1
                continue
            payload_bytes += int(handle.payload_bytes)
            if real_handle is not None:
                payload_bytes += int(real_handle.payload_bytes)
            consumer_object = self._build_descriptor_consumer_object(
                key=key,
                handle=handle,
                real_handle=real_handle,
            )
            if consumer_object is None:
                object_miss_count += 1
                continue
            object_hit_count += 1
            object_hashes.append(consumer_object.object_hash)
            object_hash_by_address_key[key] = consumer_object.object_hash
            if expected and key in expected:
                checked_object_count += 1
                if str(expected[key]) != str(consumer_object.object_hash):
                    stale_object_count += 1
        object_hash = None
        if object_hashes:
            payload = "|".join(sorted(object_hashes)).encode("utf-8")
            object_hash = hashlib.sha256(payload).hexdigest()
        expected_ok = not expected or checked_object_count == len(expected)
        read_ok = (
            lookup_count > 0
            and object_hit_count == lookup_count
            and object_miss_count == 0
            and stale_object_count == 0
            and payload_bytes == 0
            and expected_ok
        )
        return PremapDescriptorConsumerReadResult(
            lookup_count=lookup_count,
            object_hit_count=object_hit_count,
            object_miss_count=object_miss_count,
            stale_object_count=stale_object_count,
            checked_object_count=checked_object_count,
            object_hash=object_hash,
            read_ok=bool(read_ok),
            object_hash_by_address_key=object_hash_by_address_key,
            payload_bytes=payload_bytes,
            ready_credit=False,
            changes_router=False,
            changes_descriptor_order=False,
        )

    def validate_native_typed_consumer_bridge_readonly(
        self,
        table_object: PremapKernelArgShadowTableObject,
    ) -> PremapNativeTypedConsumerBridgeCheck:
        """Validate the native typed-consumer bridge shape without a kernel call."""

        native_input = table_object.to_native_typed_consumer_input_dict()
        failures: list[str] = []
        meta = native_input.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
            failures.append("missing_meta")
        row_count = int(meta.get("row_count", table_object.row_count) or 0)
        column_count = int(meta.get("column_count", table_object.column_count) or 0)
        schema_hash = str(meta.get("schema_hash", table_object.schema_hash) or "")
        payload_bytes = int(meta.get("payload_bytes", 0) or 0)
        ready_credit = bool(meta.get("ready_credit", False))
        changes_router = bool(meta.get("changes_router", False))
        changes_descriptor_order = bool(meta.get("changes_descriptor_order", False))
        passed_to_kernel = bool(meta.get("passed_to_kernel", False))
        changes_kernel_launch_args = bool(
            meta.get("changes_kernel_launch_args", False)
        )
        if row_count != int(table_object.row_count):
            failures.append("row_count_mismatch")
        if column_count != int(table_object.column_count):
            failures.append("column_count_mismatch")
        if schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
            failures.append("schema_hash_mismatch")
        if str(meta.get("table_object_hash", "")) != str(table_object.object_hash):
            failures.append("table_object_hash_mismatch")
        if str(meta.get("row_order_hash", "")) != str(table_object.row_order_hash):
            failures.append("row_order_hash_mismatch")
        if str(meta.get("ordered_row_hash", "")) != str(table_object.ordered_row_hash):
            failures.append("ordered_row_hash_mismatch")
        if payload_bytes != 0:
            failures.append("payload_bytes_nonzero")
        if ready_credit:
            failures.append("ready_credit_true")
        if changes_router:
            failures.append("changes_router_true")
        if changes_descriptor_order:
            failures.append("changes_descriptor_order_true")
        if passed_to_kernel:
            failures.append("passed_to_kernel_true")
        if changes_kernel_launch_args:
            failures.append("changes_kernel_launch_args_true")

        def as_int_list(field: str, *, required: bool = True) -> list[int]:
            value = native_input.get(field)
            if value is None:
                if required:
                    failures.append(f"{field}_missing")
                return []
            if not isinstance(value, list):
                failures.append(f"{field}_not_list")
                return []
            if len(value) != row_count:
                failures.append(f"{field}_length_mismatch")
            out: list[int] = []
            for item in value:
                try:
                    out.append(int(item) & 0xFFFFFFFFFFFFFFFF)
                except (TypeError, ValueError):
                    failures.append(f"{field}_non_int")
                    out.append(0)
            return out

        descriptor_ptr = as_int_list("descriptor_ptr")
        packed_weight_descriptor = as_int_list("packed_weight_descriptor")
        scale_metadata_handle = as_int_list("scale_metadata_handle")
        aux_metadata_handle = as_int_list("aux_metadata_handle", required=False)
        if "aux_metadata_handle" not in native_input:
            aux_metadata_handle = [0 for _ in range(row_count)]
        expert_id = as_int_list("expert_id")
        address_key_hash = as_int_list("address_key_hash")

        required_values = (
            descriptor_ptr + packed_weight_descriptor + scale_metadata_handle
        )
        required_nonzero = sum(1 for value in required_values if int(value) != 0)
        required_zero = len(required_values) - required_nonzero
        optional_nonzero = sum(1 for value in aux_metadata_handle if int(value) != 0)
        optional_zero = max(0, row_count - optional_nonzero)
        expert_valid = sum(1 for value in expert_id if int(value) >= 0)
        expert_invalid = max(0, row_count - expert_valid)
        address_nonzero = sum(1 for value in address_key_hash if int(value) != 0)
        address_zero = max(0, row_count - address_nonzero)
        input_hash = hashlib.sha256(
            json.dumps(native_input, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        return PremapNativeTypedConsumerBridgeCheck(
            mode="readonly_native_typed_consumer_bridge_check",
            input_hash=input_hash,
            table_object_hash=table_object.object_hash,
            schema_hash=schema_hash,
            row_count=row_count,
            column_count=column_count,
            required_handle_nonzero_count=required_nonzero,
            required_handle_zero_count=required_zero,
            optional_handle_nonzero_count=optional_nonzero,
            optional_handle_zero_count=optional_zero,
            expert_id_valid_count=expert_valid,
            expert_id_invalid_count=expert_invalid,
            address_key_hash_nonzero_count=address_nonzero,
            address_key_hash_zero_count=address_zero,
            failures=tuple(failures),
            payload_bytes=payload_bytes,
            ready_credit=ready_credit,
            changes_router=changes_router,
            changes_descriptor_order=changes_descriptor_order,
            passed_to_kernel=passed_to_kernel,
            changes_kernel_launch_args=changes_kernel_launch_args,
        )

    def validate_kernel_side_typed_row_consumer_path_readonly(
        self,
        table_object: PremapKernelArgShadowTableObject,
    ) -> PremapKernelSideTypedRowConsumerPathCheck:
        """Validate the future kernel-side typed row consumer path online.

        This is the in-process/vLLM-prelaunch counterpart of the native stub's
        `premap_typed_consumer_kernel_side_consume_row_v1` path.  It iterates
        the prepared typed table row by row and checks only handle visibility,
        lifetime metadata, and schema shape.  It does not invoke the native
        stub and never mutates a live kernel launch.
        """

        native_input = table_object.to_native_typed_consumer_input_dict()
        failures: list[str] = []
        meta = native_input.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
            failures.append("missing_meta")
        row_count = int(meta.get("row_count", table_object.row_count) or 0)
        column_count = int(meta.get("column_count", table_object.column_count) or 0)
        schema_hash = str(meta.get("schema_hash", table_object.schema_hash) or "")
        payload_bytes = int(meta.get("payload_bytes", 0) or 0)
        passed_to_kernel = bool(meta.get("passed_to_kernel", False))
        changes_kernel_launch_args = bool(
            meta.get("changes_kernel_launch_args", False)
        )
        if row_count != int(table_object.row_count):
            failures.append("row_count_mismatch")
        if column_count != int(table_object.column_count):
            failures.append("column_count_mismatch")
        if schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
            failures.append("schema_hash_mismatch")
        if payload_bytes != 0:
            failures.append("payload_bytes_nonzero")
        if passed_to_kernel:
            failures.append("passed_to_kernel_true")
        if changes_kernel_launch_args:
            failures.append("changes_kernel_launch_args_true")

        def as_int_list(field: str, *, required: bool = True) -> list[int]:
            value = native_input.get(field)
            if value is None:
                if required:
                    failures.append(f"{field}_missing")
                return []
            if not isinstance(value, list):
                failures.append(f"{field}_not_list")
                return []
            if len(value) != row_count:
                failures.append(f"{field}_length_mismatch")
            out: list[int] = []
            for item in value:
                try:
                    out.append(int(item) & 0xFFFFFFFFFFFFFFFF)
                except (TypeError, ValueError):
                    failures.append(f"{field}_non_int")
                    out.append(0)
            return out

        descriptor_ptr = as_int_list("descriptor_ptr")
        packed_weight_descriptor = as_int_list("packed_weight_descriptor")
        scale_metadata_handle = as_int_list("scale_metadata_handle")
        aux_metadata_handle = as_int_list("aux_metadata_handle", required=False)
        if "aux_metadata_handle" not in native_input:
            aux_metadata_handle = [0 for _ in range(row_count)]
        expert_id = as_int_list("expert_id")
        address_key_hash = as_int_list("address_key_hash")

        row_order_hash = _digest_to_u64(str(meta.get("row_order_hash", "")))
        ordered_row_hash = _digest_to_u64(str(meta.get("ordered_row_hash", "")))
        row_ok_count = 0
        hash_acc = 0
        for row_index in range(row_count):
            descriptor = descriptor_ptr[row_index] if row_index < len(descriptor_ptr) else 0
            packed = (
                packed_weight_descriptor[row_index]
                if row_index < len(packed_weight_descriptor)
                else 0
            )
            scale = (
                scale_metadata_handle[row_index]
                if row_index < len(scale_metadata_handle)
                else 0
            )
            aux = (
                aux_metadata_handle[row_index]
                if row_index < len(aux_metadata_handle)
                else 0
            )
            expert = expert_id[row_index] if row_index < len(expert_id) else -1
            address = (
                address_key_hash[row_index]
                if row_index < len(address_key_hash)
                else 0
            )
            required_visible = descriptor != 0 and packed != 0 and scale != 0
            lifetime_valid = address != 0 and int(expert) >= 0
            row_ok = (
                required_visible
                and lifetime_valid
                and row_index < row_count
                and column_count == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            )
            row_ok_count += int(row_ok)
            row_hash = (
                _mix64(descriptor)
                ^ _mix64(packed + 0x1000)
                ^ _mix64(scale + 0x2000)
                ^ _mix64(aux + 0x3000)
                ^ _mix64(address + int(expert))
                ^ _mix64(row_index)
                ^ _mix64(row_order_hash)
                ^ _mix64(ordered_row_hash)
            )
            hash_acc ^= _mix64(row_hash + row_index)
        input_hash = hashlib.sha256(
            json.dumps(native_input, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        return PremapKernelSideTypedRowConsumerPathCheck(
            mode=PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_MODE,
            path_name=PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_NAME,
            source=PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_SOURCE,
            input_hash=input_hash,
            table_object_hash=table_object.object_hash,
            schema_hash=schema_hash,
            row_count=row_count,
            column_count=column_count,
            row_ok_count=row_ok_count,
            error_count=max(0, row_count - row_ok_count),
            hash_accumulator=f"{hash_acc:016x}",
            failures=tuple(failures),
            payload_bytes=payload_bytes,
            passed_to_kernel=passed_to_kernel,
            changes_kernel_launch_args=changes_kernel_launch_args,
            current_wna16_arg_compatible=False,
        )

    def build_wna16_adjacent_typed_slot_readonly(
        self,
        table_object: PremapKernelArgShadowTableObject,
    ) -> PremapWna16AdjacentTypedSlotCheck:
        """Build the online envelope for a future WNA16 typed-slot consumer.

        This mirrors the standalone native stub's WNA16-adjacent typed slot at
        the vLLM prelaunch boundary.  The current WNA16 kernel is still not
        called with this object; this only proves that the producer/native
        adapter can emit the future slot contract directly from the prepared
        handle table.
        """

        native_input = table_object.to_native_typed_consumer_input_dict()
        failures: list[str] = []
        meta = native_input.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
            failures.append("missing_meta")
        row_count = int(meta.get("row_count", table_object.row_count) or 0)
        schema_hash = str(meta.get("schema_hash", table_object.schema_hash) or "")
        payload_bytes = int(meta.get("payload_bytes", 0) or 0)
        passed_to_kernel = bool(meta.get("passed_to_kernel", False))
        changes_kernel_launch_args = bool(
            meta.get("changes_kernel_launch_args", False)
        )
        if row_count != int(table_object.row_count):
            failures.append("row_count_mismatch")
        if schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
            failures.append("schema_hash_mismatch")
        if payload_bytes != 0:
            failures.append("payload_bytes_nonzero")
        if passed_to_kernel:
            failures.append("passed_to_kernel_true")
        if changes_kernel_launch_args:
            failures.append("changes_kernel_launch_args_true")

        def as_int_list(field: str, *, required: bool = True) -> list[int]:
            value = native_input.get(field)
            if value is None:
                if required:
                    failures.append(f"{field}_missing")
                return []
            if not isinstance(value, list):
                failures.append(f"{field}_not_list")
                return []
            if len(value) != row_count:
                failures.append(f"{field}_length_mismatch")
            out: list[int] = []
            for item in value:
                try:
                    out.append(int(item) & 0xFFFFFFFFFFFFFFFF)
                except (TypeError, ValueError):
                    failures.append(f"{field}_non_int")
                    out.append(0)
            return out

        descriptor_ptr = as_int_list("descriptor_ptr")
        packed_weight_descriptor = as_int_list("packed_weight_descriptor")
        scale_metadata_handle = as_int_list("scale_metadata_handle")
        aux_metadata_handle = as_int_list("aux_metadata_handle", required=False)
        if "aux_metadata_handle" not in native_input:
            aux_metadata_handle = [0 for _ in range(row_count)]
        expert_id = as_int_list("expert_id")
        address_key_hash = as_int_list("address_key_hash")

        row_order_hash = _digest_to_u64(str(meta.get("row_order_hash", "")))
        ordered_row_hash = _digest_to_u64(str(meta.get("ordered_row_hash", "")))
        row_ok_count = 0
        descriptor_read_ok = 0
        packed_read_ok = 0
        scale_read_ok = 0
        aux_read_ok = 0
        expert_read_ok = 0
        address_read_ok = 0
        row_metadata_read_ok = 0
        row_hash_acc = 0
        field_read_hash_acc = 0
        row_metadata_hash_acc = 0
        for row_index in range(row_count):
            has_descriptor = row_index < len(descriptor_ptr)
            has_packed = row_index < len(packed_weight_descriptor)
            has_scale = row_index < len(scale_metadata_handle)
            has_aux = row_index < len(aux_metadata_handle)
            has_expert = row_index < len(expert_id)
            has_address = row_index < len(address_key_hash)
            descriptor = descriptor_ptr[row_index] if has_descriptor else 0
            packed = packed_weight_descriptor[row_index] if has_packed else 0
            scale = scale_metadata_handle[row_index] if has_scale else 0
            aux = aux_metadata_handle[row_index] if has_aux else 0
            expert = expert_id[row_index] if has_expert else -1
            address = address_key_hash[row_index] if has_address else 0
            descriptor_visible = has_descriptor and descriptor != 0
            packed_visible = has_packed and packed != 0
            scale_visible = has_scale and scale != 0
            aux_read = has_aux
            expert_valid = has_expert and int(expert) >= 0
            address_visible = has_address and address != 0
            row_metadata_ok = expert_valid and address_visible
            descriptor_read_ok += int(descriptor_visible)
            packed_read_ok += int(packed_visible)
            scale_read_ok += int(scale_visible)
            aux_read_ok += int(aux_read)
            expert_read_ok += int(expert_valid)
            address_read_ok += int(address_visible)
            row_metadata_read_ok += int(row_metadata_ok)
            row_ok = (
                descriptor_visible
                and packed_visible
                and scale_visible
                and aux_read
                and row_metadata_ok
            )
            row_ok_count += int(row_ok)
            row_hash = (
                _mix64(descriptor)
                ^ _mix64(packed + 0x1111)
                ^ _mix64(scale + 0x2222)
                ^ _mix64(aux + 0x3333)
                ^ _mix64(address + int(expert))
                ^ _mix64(row_index)
                ^ _mix64(row_order_hash)
                ^ _mix64(ordered_row_hash)
            )
            field_hash = (
                _mix64(PREMAP_WNA16_ADJACENT_TYPED_SLOT_FIELD_MASK)
                ^ _mix64(int(descriptor_visible))
                ^ _mix64(int(packed_visible) + 0x10)
                ^ _mix64(int(scale_visible) + 0x20)
                ^ _mix64(int(aux_read) + 0x30)
                ^ _mix64(row_index)
            )
            metadata_hash = (
                _mix64(address)
                ^ _mix64(int(expert) + 0x4444)
                ^ _mix64(row_index)
                ^ _mix64(row_order_hash)
                ^ _mix64(ordered_row_hash)
            )
            row_hash_acc ^= _mix64(row_hash + row_index)
            field_read_hash_acc ^= _mix64(field_hash + row_index)
            row_metadata_hash_acc ^= _mix64(metadata_hash + row_index)
        input_hash = hashlib.sha256(
            json.dumps(native_input, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        return PremapWna16AdjacentTypedSlotCheck(
            name=PREMAP_WNA16_ADJACENT_TYPED_SLOT_NAME,
            mode=PREMAP_WNA16_ADJACENT_TYPED_SLOT_MODE,
            source=PREMAP_WNA16_ADJACENT_TYPED_SLOT_SOURCE,
            input_hash=input_hash,
            table_object_hash=table_object.object_hash,
            schema_hash=schema_hash,
            row_count=row_count,
            row_ok_count=row_ok_count,
            error_count=max(0, row_count - row_ok_count),
            field_mask=PREMAP_WNA16_ADJACENT_TYPED_SLOT_FIELD_MASK,
            descriptor_ptr_read_row_ok_count=descriptor_read_ok,
            packed_weight_descriptor_read_row_ok_count=packed_read_ok,
            scale_metadata_handle_read_row_ok_count=scale_read_ok,
            aux_metadata_handle_read_row_ok_count=aux_read_ok,
            expert_id_read_row_ok_count=expert_read_ok,
            address_key_hash_read_row_ok_count=address_read_ok,
            row_metadata_read_row_ok_count=row_metadata_read_ok,
            row_hash_accumulator=f"{row_hash_acc:016x}",
            field_read_hash_accumulator=f"{field_read_hash_acc:016x}",
            row_metadata_hash_accumulator=f"{row_metadata_hash_acc:016x}",
            failures=tuple(failures),
            payload_bytes=payload_bytes,
            passed_to_kernel=passed_to_kernel,
            changes_kernel_launch_args=changes_kernel_launch_args,
        )

    def build_native_stub_online_invocation_canary_readonly(
        self,
        table_object: PremapKernelArgShadowTableObject,
        native_bridge_check: PremapNativeTypedConsumerBridgeCheck | None,
    ) -> PremapNativeStubOnlineInvocationCanary:
        """Build a live-disabled native-stub invocation package.

        This is the online canary version of the standalone native stub path:
        the prelaunch shim constructs the typed input and records the exact
        package a native consumer would receive, while deliberately blocking
        the real stub/kernel invocation.
        """

        native_input = table_object.to_native_typed_consumer_input_dict()
        current_input_hash = hashlib.sha256(
            json.dumps(native_input, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        bridge_ok = bool(native_bridge_check.ok) if native_bridge_check else False
        failures: list[str] = []
        if native_bridge_check is None:
            failures.append("native_bridge_check_missing")
        elif not native_bridge_check.ok:
            failures.append("native_bridge_check_failed")
        if native_bridge_check is not None:
            if str(native_bridge_check.input_hash) != current_input_hash:
                failures.append("native_bridge_input_hash_mismatch")
            if str(native_bridge_check.table_object_hash) != str(
                table_object.object_hash
            ):
                failures.append("native_bridge_table_object_hash_mismatch")
            if str(native_bridge_check.schema_hash) != str(table_object.schema_hash):
                failures.append("native_bridge_schema_hash_mismatch")
            if int(native_bridge_check.row_count) != int(table_object.row_count):
                failures.append("native_bridge_row_count_mismatch")
            if int(native_bridge_check.column_count) != int(table_object.column_count):
                failures.append("native_bridge_column_count_mismatch")
        mode = "readonly_native_stub_online_invocation_canary"
        package = {
            "mode": mode,
            "live_disabled": True,
            "native_stub_invoked": False,
            "native_bridge_input_hash": (
                native_bridge_check.input_hash if native_bridge_check else None
            ),
            "table_object_hash": table_object.object_hash,
            "schema_hash": table_object.schema_hash,
            "row_count": int(table_object.row_count),
            "column_count": int(table_object.column_count),
            "native_input": native_input,
        }
        package_hash = hashlib.sha256(
            json.dumps(package, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        return PremapNativeStubOnlineInvocationCanary(
            mode=mode,
            native_checker_invoked=native_bridge_check is not None,
            native_bridge_ok=bridge_ok,
            package_hash=package_hash,
            input_hash=native_bridge_check.input_hash if native_bridge_check else "",
            table_object_hash=table_object.object_hash,
            schema_hash=table_object.schema_hash,
            row_count=int(table_object.row_count),
            column_count=int(table_object.column_count),
            required_handle_nonzero_count=(
                native_bridge_check.required_handle_nonzero_count
                if native_bridge_check
                else 0
            ),
            required_handle_zero_count=(
                native_bridge_check.required_handle_zero_count
                if native_bridge_check
                else 0
            ),
            optional_handle_nonzero_count=(
                native_bridge_check.optional_handle_nonzero_count
                if native_bridge_check
                else 0
            ),
            optional_handle_zero_count=(
                native_bridge_check.optional_handle_zero_count
                if native_bridge_check
                else 0
            ),
            expert_id_valid_count=(
                native_bridge_check.expert_id_valid_count if native_bridge_check else 0
            ),
            expert_id_invalid_count=(
                native_bridge_check.expert_id_invalid_count
                if native_bridge_check
                else 0
            ),
            address_key_hash_nonzero_count=(
                native_bridge_check.address_key_hash_nonzero_count
                if native_bridge_check
                else 0
            ),
            address_key_hash_zero_count=(
                native_bridge_check.address_key_hash_zero_count
                if native_bridge_check
                else 0
            ),
            invocation_requested=True,
            native_stub_invoked=False,
            invocation_blocked=True,
            invocation_block_reason="native_stub_live_disabled",
            failures=tuple(failures),
            payload_bytes=0,
            ready_credit=(
                native_bridge_check.ready_credit if native_bridge_check else False
            ),
            changes_router=(
                native_bridge_check.changes_router if native_bridge_check else False
            ),
            changes_descriptor_order=(
                native_bridge_check.changes_descriptor_order
                if native_bridge_check
                else False
            ),
            passed_to_kernel=False,
            changes_kernel_launch_args=False,
        )

    def execute_descriptor_consumer_shim_readonly(
        self,
        read_result: PremapDescriptorConsumerReadResult,
        *,
        kernel_arg_shadow_table_result: PremapKernelArgShadowTableResult | None = None,
        kernel_arg_shadow_table_object: PremapKernelArgShadowTableObject | None = None,
        descriptor_address_prep_dry_run_result: (
            PremapDescriptorAddressPrepDryRunResult | None
        ) = None,
        kernel_arg_handoff_live_enabled: bool = False,
        kernel_arg_handoff_consumer_connected: bool = False,
        kernel_arg_handoff_kernel_arg_pass_enabled: bool = False,
        kernel_arg_handoff_real_kernel_arg_mutation_enabled: bool = False,
        kernel_arg_handoff_lab_gate_passed: bool = False,
        single_field_handle_handoff_canary_field: str = "scale_metadata_handle",
        execution_mode: str = "readonly_prelaunch_consumer_shim",
    ) -> PremapDescriptorConsumerShimResult:
        """Run the minimal prelaunch consumer shim without side effects."""

        table_result = kernel_arg_shadow_table_result
        table_object = kernel_arg_shadow_table_object
        prep_dry_run = descriptor_address_prep_dry_run_result
        table_read_ok = None
        table_lifecycle_ok = None
        table_parity_count = None
        table_row_miss_count = None
        table_stale_row_count = None
        table_passed_to_kernel = False
        handle_table_row_count = int(read_result.object_hit_count)
        handle_table_column_count = len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
        handle_table_schema_hash = PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        handle_table_payload_bytes = 0
        handle_table_kernel_mutation = False
        table_consume_ok = None
        table_consume_lifecycle_ok = None
        table_consume_row_count = None
        table_consume_column_count = None
        table_consume_schema_hash = None
        table_consume_mode = None
        table_consume_source = None
        table_consume_row_order_hash = None
        table_consume_ordered_row_hash = None
        table_consume_parity_count = None
        table_consume_row_miss_count = None
        table_consume_stale_row_count = None
        table_consume_handle_field_read_count = None
        table_consume_required_handle_field_available_count = None
        table_consume_optional_handle_field_available_count = None
        table_consume_descriptor_ptr_field_read_count = None
        table_consume_packed_weight_descriptor_field_read_count = None
        table_consume_scale_metadata_handle_field_read_count = None
        table_consume_aux_metadata_handle_field_read_count = None
        table_consume_descriptor_ptr_field_available_count = None
        table_consume_packed_weight_descriptor_field_available_count = None
        table_consume_scale_metadata_handle_field_available_count = None
        table_consume_aux_metadata_handle_field_available_count = None
        table_consume_source_hit_counts = None
        table_consume_source_miss_counts = None
        table_consume_passed_to_kernel = False
        table_consume_payload_bytes = 0
        table_object_consumed = None
        table_object_hash = None
        table_object_row_count = None
        table_object_lifecycle_ok = None
        table_object_passed_to_kernel = False
        table_object_payload_bytes = 0
        native_bridge_check: PremapNativeTypedConsumerBridgeCheck | None = None
        native_stub_canary: PremapNativeStubOnlineInvocationCanary | None = None
        kernel_side_typed_row_consumer_path: (
            PremapKernelSideTypedRowConsumerPathCheck | None
        ) = None
        wna16_adjacent_typed_slot: PremapWna16AdjacentTypedSlotCheck | None = None
        prep_dry_run_mode = None
        prep_dry_run_source = None
        prep_dry_run_ok = None
        prep_dry_run_row_count = None
        prep_dry_run_column_count = None
        prep_dry_run_schema_hash = None
        prep_dry_run_object_hash = None
        prep_dry_run_lifecycle_ok = None
        prep_dry_run_row_handle_parity_ok_count = None
        prep_dry_run_descriptor_ptr_parity_ok_count = None
        prep_dry_run_packed_weight_descriptor_parity_ok_count = None
        prep_dry_run_scale_metadata_handle_parity_ok_count = None
        prep_dry_run_aux_metadata_handle_parity_ok_count = None
        prep_dry_run_row_handle_miss_count = None
        prep_dry_run_handle_field_read_count = None
        prep_dry_run_required_handle_field_available_count = None
        prep_dry_run_optional_handle_field_available_count = None
        prep_dry_run_descriptor_ptr_field_read_count = None
        prep_dry_run_packed_weight_descriptor_field_read_count = None
        prep_dry_run_scale_metadata_handle_field_read_count = None
        prep_dry_run_aux_metadata_handle_field_read_count = None
        prep_dry_run_descriptor_ptr_field_available_count = None
        prep_dry_run_packed_weight_descriptor_field_available_count = None
        prep_dry_run_scale_metadata_handle_field_available_count = None
        prep_dry_run_aux_metadata_handle_field_available_count = None
        prep_dry_run_passed_to_kernel = False
        prep_dry_run_payload_bytes = 0
        if table_result is not None:
            table_lifecycle_ok = bool(table_result.lifecycle_ok)
            table_parity_count = int(table_result.per_row_parity_ok_count)
            table_row_miss_count = int(table_result.row_miss_count)
            table_stale_row_count = int(table_result.stale_row_count)
            table_passed_to_kernel = bool(table_result.passed_to_kernel)
            handle_table_row_count = int(table_result.row_count)
            handle_table_column_count = int(table_result.column_count)
            handle_table_schema_hash = str(table_result.schema_hash)
            handle_table_payload_bytes = int(table_result.payload_bytes)
            handle_table_kernel_mutation = bool(
                table_result.changes_kernel_launch_args
            )
            table_read_ok = (
                bool(table_result.table_ok)
                and bool(table_result.lifecycle_ok)
                and int(table_result.row_count) == int(read_result.object_hit_count)
                and int(table_result.per_row_parity_ok_count) == int(table_result.row_count)
                and int(table_result.row_miss_count) == 0
                and int(table_result.stale_row_count) == 0
                and int(table_result.payload_bytes) == 0
                and not bool(table_result.ready_credit)
                and not bool(table_result.changes_router)
                and not bool(table_result.changes_descriptor_order)
                and not bool(table_result.changes_kernel_launch_args)
                and not bool(table_result.passed_to_kernel)
            )
            table_consume_lifecycle_ok = table_lifecycle_ok
            table_consume_row_count = int(table_result.row_count)
            table_consume_column_count = int(table_result.column_count)
            table_consume_schema_hash = str(table_result.schema_hash)
            table_consume_mode = "readonly_consume_kernel_arg_shadow_table"
            table_consume_source = str(table_result.row_order_source)
            table_consume_row_order_hash = str(table_result.row_order_hash)
            table_consume_ordered_row_hash = str(table_result.ordered_row_hash)
            table_consume_parity_count = table_parity_count
            table_consume_row_miss_count = table_row_miss_count
            table_consume_stale_row_count = table_stale_row_count
            table_consume_passed_to_kernel = table_passed_to_kernel
            table_consume_payload_bytes = handle_table_payload_bytes
            table_consume_ok = (
                table_read_ok is True
                and int(table_result.column_count)
                == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
                and str(table_result.schema_hash)
                == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
                and bool(table_result.row_order_hash)
                and bool(table_result.ordered_row_hash)
            )
        if table_result is not None and table_object is not None:
            table_object_consumed = True
            table_object_hash = str(table_object.object_hash)
            table_object_row_count = int(table_object.row_count)
            table_object_lifecycle_ok = bool(table_object.lifecycle_ok)
            table_object_passed_to_kernel = bool(table_object.passed_to_kernel)
            table_object_payload_bytes = int(table_object.payload_bytes)
            table_consume_handle_field_read_count = 0
            table_consume_required_handle_field_available_count = 0
            table_consume_optional_handle_field_available_count = 0
            table_consume_descriptor_ptr_field_read_count = 0
            table_consume_packed_weight_descriptor_field_read_count = 0
            table_consume_scale_metadata_handle_field_read_count = 0
            table_consume_aux_metadata_handle_field_read_count = 0
            table_consume_descriptor_ptr_field_available_count = 0
            table_consume_packed_weight_descriptor_field_available_count = 0
            table_consume_scale_metadata_handle_field_available_count = 0
            table_consume_aux_metadata_handle_field_available_count = 0
            table_consume_source_hit_counts = {
                "descriptor_ptr": 0,
                "packed_weight_descriptor": 0,
                "scale_metadata_handle": 0,
                "aux_metadata_handle": 0,
            }
            table_consume_source_miss_counts = {
                "descriptor_ptr": 0,
                "packed_weight_descriptor": 0,
                "scale_metadata_handle": 0,
                "aux_metadata_handle": 0,
            }
            for row in table_object.rows:
                descriptor_ptr = row.descriptor_ptr
                packed_weight_descriptor = row.packed_weight_descriptor
                scale_metadata_handle = row.scale_metadata_handle
                aux_metadata_handle = row.aux_metadata_handle
                table_consume_handle_field_read_count += len(
                    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS
                )
                table_consume_descriptor_ptr_field_read_count += 1
                table_consume_packed_weight_descriptor_field_read_count += 1
                table_consume_scale_metadata_handle_field_read_count += 1
                table_consume_aux_metadata_handle_field_read_count += 1
                table_consume_required_handle_field_available_count += int(
                    bool(descriptor_ptr)
                )
                table_consume_required_handle_field_available_count += int(
                    bool(packed_weight_descriptor)
                )
                table_consume_required_handle_field_available_count += int(
                    bool(scale_metadata_handle)
                )
                table_consume_optional_handle_field_available_count += int(
                    aux_metadata_handle is not None
                )
                table_consume_descriptor_ptr_field_available_count += int(
                    bool(descriptor_ptr)
                )
                table_consume_packed_weight_descriptor_field_available_count += int(
                    bool(packed_weight_descriptor)
                )
                table_consume_scale_metadata_handle_field_available_count += int(
                    bool(scale_metadata_handle)
                )
                table_consume_aux_metadata_handle_field_available_count += int(
                    aux_metadata_handle is not None
                )
                table_consume_source_hit_counts["descriptor_ptr"] += int(
                    bool(descriptor_ptr)
                )
                table_consume_source_miss_counts["descriptor_ptr"] += int(
                    not bool(descriptor_ptr)
                )
                table_consume_source_hit_counts["packed_weight_descriptor"] += int(
                    bool(packed_weight_descriptor)
                )
                table_consume_source_miss_counts["packed_weight_descriptor"] += int(
                    not bool(packed_weight_descriptor)
                )
                table_consume_source_hit_counts["scale_metadata_handle"] += int(
                    bool(scale_metadata_handle)
                )
                table_consume_source_miss_counts["scale_metadata_handle"] += int(
                    not bool(scale_metadata_handle)
                )
                table_consume_source_hit_counts["aux_metadata_handle"] += int(
                    aux_metadata_handle is not None
                )
                table_consume_source_miss_counts["aux_metadata_handle"] += int(
                    aux_metadata_handle is None
                )
            object_consume_ok = (
                table_object_lifecycle_ok
                and int(table_object.row_count) == int(read_result.object_hit_count)
                and int(table_object.column_count)
                == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
                and str(table_object.schema_hash)
                == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
                and bool(table_object.row_order_hash)
                and bool(table_object.ordered_row_hash)
                and int(table_object.payload_bytes) == 0
                and not bool(table_object.passed_to_kernel)
            )
            object_consume_ok = (
                object_consume_ok
                and int(table_object.row_count) == int(table_result.row_count)
                and str(table_object.schema_hash) == str(table_result.schema_hash)
                and str(table_object.row_order_hash) == str(table_result.row_order_hash)
                and str(table_object.ordered_row_hash)
                == str(table_result.ordered_row_hash)
                and int(table_consume_handle_field_read_count)
                == int(table_object.row_count)
                * len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
                and int(table_consume_required_handle_field_available_count)
                == int(table_object.row_count) * 3
                and int(table_consume_descriptor_ptr_field_read_count)
                == int(table_object.row_count)
                and int(table_consume_packed_weight_descriptor_field_read_count)
                == int(table_object.row_count)
                and int(table_consume_scale_metadata_handle_field_read_count)
                == int(table_object.row_count)
                and int(table_consume_aux_metadata_handle_field_read_count)
                == int(table_object.row_count)
                and int(table_consume_descriptor_ptr_field_available_count)
                == int(table_object.row_count)
                and int(table_consume_packed_weight_descriptor_field_available_count)
                == int(table_object.row_count)
                and int(table_consume_scale_metadata_handle_field_available_count)
                == int(table_object.row_count)
                and 0 <= int(table_consume_aux_metadata_handle_field_available_count)
                <= int(table_object.row_count)
            )
            table_consume_ok = bool(table_consume_ok) and bool(object_consume_ok)
            native_bridge_check = self.validate_native_typed_consumer_bridge_readonly(
                table_object
            )
            native_stub_canary = (
                self.build_native_stub_online_invocation_canary_readonly(
                    table_object,
                    native_bridge_check,
                )
            )
            kernel_side_typed_row_consumer_path = (
                self.validate_kernel_side_typed_row_consumer_path_readonly(
                    table_object
                )
            )
            wna16_adjacent_typed_slot = self.build_wna16_adjacent_typed_slot_readonly(
                table_object
            )
            table_consume_ok = bool(table_consume_ok) and bool(native_bridge_check.ok)
            table_consume_ok = bool(table_consume_ok) and bool(native_stub_canary.ok)
            table_consume_ok = (
                bool(table_consume_ok)
                and bool(kernel_side_typed_row_consumer_path.ready)
            )
            table_consume_ok = bool(table_consume_ok) and bool(
                wna16_adjacent_typed_slot.ready
            )
        elif table_result is not None:
            table_object_consumed = False
        if prep_dry_run is not None:
            prep_dry_run_mode = str(prep_dry_run.execution_mode)
            prep_dry_run_source = str(prep_dry_run.source)
            prep_dry_run_ok = bool(prep_dry_run.execution_ok)
            prep_dry_run_row_count = int(prep_dry_run.row_count)
            prep_dry_run_column_count = int(prep_dry_run.column_count)
            prep_dry_run_schema_hash = str(prep_dry_run.schema_hash)
            prep_dry_run_object_hash = str(prep_dry_run.table_object_hash)
            prep_dry_run_lifecycle_ok = bool(prep_dry_run.lifecycle_ok)
            prep_dry_run_row_handle_parity_ok_count = int(
                prep_dry_run.row_handle_parity_ok_count
            )
            prep_dry_run_descriptor_ptr_parity_ok_count = int(
                prep_dry_run.descriptor_ptr_parity_ok_count
            )
            prep_dry_run_packed_weight_descriptor_parity_ok_count = int(
                prep_dry_run.packed_weight_descriptor_parity_ok_count
            )
            prep_dry_run_scale_metadata_handle_parity_ok_count = int(
                prep_dry_run.scale_metadata_handle_parity_ok_count
            )
            prep_dry_run_aux_metadata_handle_parity_ok_count = int(
                prep_dry_run.aux_metadata_handle_parity_ok_count
            )
            prep_dry_run_row_handle_miss_count = int(
                prep_dry_run.row_handle_miss_count
            )
            prep_dry_run_handle_field_read_count = int(
                prep_dry_run.handle_field_read_count
            )
            prep_dry_run_required_handle_field_available_count = int(
                prep_dry_run.required_handle_field_available_count
            )
            prep_dry_run_optional_handle_field_available_count = int(
                prep_dry_run.optional_handle_field_available_count
            )
            prep_dry_run_descriptor_ptr_field_read_count = int(
                prep_dry_run.descriptor_ptr_field_read_count
            )
            prep_dry_run_packed_weight_descriptor_field_read_count = int(
                prep_dry_run.packed_weight_descriptor_field_read_count
            )
            prep_dry_run_scale_metadata_handle_field_read_count = int(
                prep_dry_run.scale_metadata_handle_field_read_count
            )
            prep_dry_run_aux_metadata_handle_field_read_count = int(
                prep_dry_run.aux_metadata_handle_field_read_count
            )
            prep_dry_run_descriptor_ptr_field_available_count = int(
                prep_dry_run.descriptor_ptr_field_available_count
            )
            prep_dry_run_packed_weight_descriptor_field_available_count = int(
                prep_dry_run.packed_weight_descriptor_field_available_count
            )
            prep_dry_run_scale_metadata_handle_field_available_count = int(
                prep_dry_run.scale_metadata_handle_field_available_count
            )
            prep_dry_run_aux_metadata_handle_field_available_count = int(
                prep_dry_run.aux_metadata_handle_field_available_count
            )
            prep_dry_run_passed_to_kernel = bool(prep_dry_run.passed_to_kernel)
            prep_dry_run_payload_bytes = int(prep_dry_run.payload_bytes)
            prep_bound_to_table_object = (
                table_object is not None
                and str(prep_dry_run.table_object_hash) == str(table_object.object_hash)
                and str(prep_dry_run.row_order_hash) == str(table_object.row_order_hash)
                and str(prep_dry_run.ordered_row_hash)
                == str(table_object.ordered_row_hash)
            )
            table_consume_ok = (
                bool(table_consume_ok)
                and bool(prep_dry_run.execution_ok)
                and prep_bound_to_table_object
                and int(prep_dry_run.row_count) == int(read_result.object_hit_count)
                and int(prep_dry_run.row_handle_miss_count) == 0
                and int(prep_dry_run.row_handle_parity_ok_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.descriptor_ptr_parity_ok_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.packed_weight_descriptor_parity_ok_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.scale_metadata_handle_parity_ok_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.aux_metadata_handle_parity_ok_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.handle_field_read_count)
                == int(prep_dry_run.row_count)
                * len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
                and int(prep_dry_run.required_handle_field_available_count)
                == int(prep_dry_run.row_count) * 3
                and int(prep_dry_run.descriptor_ptr_field_read_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.packed_weight_descriptor_field_read_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.scale_metadata_handle_field_read_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.aux_metadata_handle_field_read_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.descriptor_ptr_field_available_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.packed_weight_descriptor_field_available_count)
                == int(prep_dry_run.row_count)
                and int(prep_dry_run.scale_metadata_handle_field_available_count)
                == int(prep_dry_run.row_count)
                and 0 <= int(prep_dry_run.aux_metadata_handle_field_available_count)
                <= int(prep_dry_run.row_count)
                and int(prep_dry_run.payload_bytes) == 0
                and not bool(prep_dry_run.ready_credit)
                and not bool(prep_dry_run.changes_router)
                and not bool(prep_dry_run.changes_descriptor_order)
                and not bool(prep_dry_run.changes_kernel_launch_args)
                and not bool(prep_dry_run.passed_to_kernel)
            )
        shim_ok = (
            bool(read_result.read_ok)
            and int(read_result.object_hit_count) > 0
            and int(read_result.object_miss_count) == 0
            and int(read_result.stale_object_count) == 0
            and int(read_result.payload_bytes) == 0
            and table_read_ok is True
            and table_consume_ok is True
            and table_object_consumed is True
        )
        handoff_mode = None
        handoff_ready = None
        handoff_row_count = None
        handoff_column_count = None
        handoff_schema_hash = None
        handoff_required_hit_count = None
        handoff_required_miss_count = None
        handoff_optional_hit_count = None
        handoff_optional_miss_count = None
        handoff_shadow_slot: PremapKernelArgHandoffShadowSlot | None = None
        handoff_mirror: PremapKernelArgHandoffMirrorObject | None = None
        handoff_launch_schema_mirror: (
            PremapKernelArgPrelaunchLaunchSchemaMirror | None
        ) = None
        semantic_handle_adapter: (
            PremapKernelArgSemanticHandleAdapterObject | None
        ) = None
        single_field_handle_handoff_canary: (
            PremapSingleFieldHandleHandoffCanary | None
        ) = None
        kernel_side_consumer_schema_adapter: (
            PremapKernelSideConsumerSchemaAdapterObject | None
        ) = None
        kernel_side_typed_consumer_object: (
            PremapKernelSideTypedConsumerObject | None
        ) = None
        handoff_attempt: PremapKernelArgHandoffAttemptRecord | None = None
        handoff_live_toggle: PremapKernelArgHandoffLiveToggleRecord | None = None
        handoff_live_noop_integration: (
            PremapKernelArgHandoffLiveNoopIntegrationRecord | None
        ) = None
        handoff_live_consumer_adapter: (
            PremapKernelArgHandoffLiveConsumerAdapterRecord | None
        ) = None
        if (
            table_consume_source_hit_counts is not None
            and table_consume_source_miss_counts is not None
            and table_consume_row_count is not None
        ):
            handoff_mode = "readonly_kernel_arg_handoff_dry_run"
            handoff_row_count = int(table_consume_row_count)
            handoff_column_count = int(table_consume_column_count or 0)
            handoff_schema_hash = str(table_consume_schema_hash or "")
            handoff_required_hit_count = sum(
                int(table_consume_source_hit_counts.get(source, 0) or 0)
                for source in (
                    "descriptor_ptr",
                    "packed_weight_descriptor",
                    "scale_metadata_handle",
                )
            )
            handoff_required_miss_count = sum(
                int(table_consume_source_miss_counts.get(source, 0) or 0)
                for source in (
                    "descriptor_ptr",
                    "packed_weight_descriptor",
                    "scale_metadata_handle",
                )
            )
            handoff_optional_hit_count = int(
                table_consume_source_hit_counts.get("aux_metadata_handle", 0) or 0
            )
            handoff_optional_miss_count = int(
                table_consume_source_miss_counts.get("aux_metadata_handle", 0) or 0
            )
            handoff_ready = (
                table_consume_ok is True
                and handoff_column_count
                == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
                and handoff_schema_hash
                == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
                and handoff_required_hit_count == handoff_row_count * 3
                and handoff_required_miss_count == 0
                and handoff_optional_hit_count + handoff_optional_miss_count
                == handoff_row_count
                and int(table_consume_payload_bytes) == 0
                and not bool(table_consume_passed_to_kernel)
            )
            if table_object is not None:
                handoff_shadow_slot = PremapKernelArgHandoffShadowSlot(
                    mode="readonly_kernel_arg_handoff_shadow_slot",
                    table_object_hash=table_object.object_hash,
                    row_count=handoff_row_count,
                    column_count=handoff_column_count,
                    schema_hash=handoff_schema_hash,
                    row_order_hash=table_object.row_order_hash,
                    ordered_row_hash=table_object.ordered_row_hash,
                    required_source_hit_count=handoff_required_hit_count,
                    required_source_miss_count=handoff_required_miss_count,
                    optional_source_hit_count=handoff_optional_hit_count,
                    optional_source_miss_count=handoff_optional_miss_count,
                    payload_bytes=0,
                    passed_to_kernel=False,
                    changes_kernel_launch_args=False,
                )
                handoff_mirror = PremapKernelArgHandoffMirrorObject(
                    mode="readonly_kernel_arg_handoff_mirror",
                    slot_hash=handoff_shadow_slot.slot_hash,
                    table_object_hash=table_object.object_hash,
                    row_count=handoff_row_count,
                    column_count=handoff_column_count,
                    schema_hash=handoff_schema_hash,
                    row_order_hash=table_object.row_order_hash,
                    ordered_row_hash=table_object.ordered_row_hash,
                    descriptor_ptr_arg_hash=hashlib.sha256(
                        "|".join(row.descriptor_ptr for row in table_object.rows).encode(
                            "utf-8"
                        )
                    ).hexdigest(),
                    packed_weight_descriptor_arg_hash=hashlib.sha256(
                        "|".join(
                            row.packed_weight_descriptor for row in table_object.rows
                        ).encode("utf-8")
                    ).hexdigest(),
                    scale_metadata_handle_arg_hash=hashlib.sha256(
                        "|".join(
                            row.scale_metadata_handle for row in table_object.rows
                        ).encode("utf-8")
                    ).hexdigest(),
                    aux_metadata_handle_arg_hash=hashlib.sha256(
                        "|".join(
                            ""
                            if row.aux_metadata_handle is None
                            else str(row.aux_metadata_handle)
                            for row in table_object.rows
                        ).encode("utf-8")
                    ).hexdigest(),
                    required_source_hit_count=handoff_required_hit_count,
                    required_source_miss_count=handoff_required_miss_count,
                    optional_source_hit_count=handoff_optional_hit_count,
                    optional_source_miss_count=handoff_optional_miss_count,
                    payload_bytes=0,
                    passed_to_kernel=False,
                    changes_kernel_launch_args=False,
                )
                handoff_launch_schema_mirror = (
                    PremapKernelArgPrelaunchLaunchSchemaMirror(
                        mode="readonly_kernel_arg_handoff_launch_schema_mirror",
                        handoff_mirror_hash=handoff_mirror.mirror_hash,
                        slot_hash=handoff_shadow_slot.slot_hash,
                        table_object_hash=table_object.object_hash,
                        row_count=handoff_row_count,
                        column_count=handoff_column_count,
                        table_schema_hash=handoff_schema_hash,
                        launch_schema_name=(
                            PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME
                        ),
                        launch_schema_hash=(
                            PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH
                        ),
                        launch_arg_field_count=len(
                            PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS
                        ),
                        row_order_hash=table_object.row_order_hash,
                        ordered_row_hash=table_object.ordered_row_hash,
                        descriptor_ptr_arg_hash=(
                            handoff_mirror.descriptor_ptr_arg_hash
                        ),
                        packed_weight_descriptor_arg_hash=(
                            handoff_mirror.packed_weight_descriptor_arg_hash
                        ),
                        scale_metadata_handle_arg_hash=(
                            handoff_mirror.scale_metadata_handle_arg_hash
                        ),
                        aux_metadata_handle_arg_hash=(
                            handoff_mirror.aux_metadata_handle_arg_hash
                        ),
                        required_source_hit_count=handoff_required_hit_count,
                        required_source_miss_count=handoff_required_miss_count,
                        optional_source_hit_count=handoff_optional_hit_count,
                        optional_source_miss_count=handoff_optional_miss_count,
                        handle_field_read_count=int(
                            table_consume_handle_field_read_count or 0
                        ),
                        payload_bytes=0,
                        passed_to_kernel=False,
                        changes_kernel_launch_args=False,
                    )
                )
                semantic_handle_adapter = PremapKernelArgSemanticHandleAdapterObject(
                    mode="readonly_kernel_arg_semantic_handle_adapter",
                    table_object_hash=table_object.object_hash,
                    launch_schema_mirror_hash=(
                        handoff_launch_schema_mirror.launch_schema_mirror_hash
                    ),
                    row_count=handoff_row_count,
                    column_count=handoff_column_count,
                    table_schema_hash=handoff_schema_hash,
                    semantic_schema_name=(
                        PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME
                    ),
                    semantic_schema_hash=(
                        PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
                    ),
                    semantic_field_count=len(
                        PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS
                    ),
                    row_order_hash=table_object.row_order_hash,
                    ordered_row_hash=table_object.ordered_row_hash,
                    descriptor_ptr_handle_hash=(
                        handoff_mirror.descriptor_ptr_arg_hash
                    ),
                    packed_weight_descriptor_handle_hash=(
                        handoff_mirror.packed_weight_descriptor_arg_hash
                    ),
                    scale_metadata_handle_hash=(
                        handoff_mirror.scale_metadata_handle_arg_hash
                    ),
                    aux_metadata_handle_hash=(
                        handoff_mirror.aux_metadata_handle_arg_hash
                    ),
                    required_source_hit_count=handoff_required_hit_count,
                    required_source_miss_count=handoff_required_miss_count,
                    optional_source_hit_count=handoff_optional_hit_count,
                    optional_source_miss_count=handoff_optional_miss_count,
                    handle_field_read_count=int(
                        table_consume_handle_field_read_count or 0
                    ),
                    payload_bytes=0,
                    passed_to_kernel=False,
                    changes_kernel_launch_args=False,
                    live_compatible_with_current_wna16_args=False,
                )
                single_field_name = str(single_field_handle_handoff_canary_field)
                single_field_mirror_mode = (
                    premap_single_field_handle_handoff_mirror_mode(single_field_name)
                )
                single_field_values = [
                    str(getattr(row, single_field_name)) for row in table_object.rows
                ]
                single_field_hash = hashlib.sha256(
                    "|".join(single_field_values).encode("utf-8")
                ).hexdigest()
                single_field_nonzero_count = sum(
                    int(_handle_to_native_u64(value) != 0)
                    for value in single_field_values
                )
                single_field_parity_ok = (
                    single_field_hash
                    == str(
                        getattr(
                            semantic_handle_adapter,
                            _premap_semantic_adapter_hash_attr_for_field(
                                single_field_name
                            ),
                        )
                    )
                )
                single_field_semantic_hash = str(
                    getattr(
                        semantic_handle_adapter,
                        _premap_semantic_adapter_hash_attr_for_field(
                            single_field_name
                        ),
                    )
                )
                single_field_handle_handoff_canary = (
                    PremapSingleFieldHandleHandoffCanary(
                        mode="readonly_single_field_handle_handoff_canary",
                        field_name=single_field_name,
                        source="semantic_handle_table",
                        mirror_mode=single_field_mirror_mode,
                        mirror_field_name=single_field_name,
                        mirror_source="semantic_handle_table",
                        table_object_hash=table_object.object_hash,
                        semantic_adapter_hash=semantic_handle_adapter.adapter_hash,
                        row_count=handoff_row_count,
                        field_handle_count=len(single_field_values),
                        field_handle_nonzero_count=single_field_nonzero_count,
                        field_handle_zero_count=(
                            len(single_field_values) - single_field_nonzero_count
                        ),
                        field_handle_hash=single_field_hash,
                        semantic_field_hash=single_field_semantic_hash,
                        mirror_handle_hash=single_field_hash,
                        mirror_schema_hash=(
                            PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
                        ),
                        mirror_ready=bool(single_field_parity_ok)
                        and single_field_nonzero_count == len(single_field_values)
                        and len(single_field_values) == handoff_row_count,
                        parity_ok_count=(
                            handoff_row_count if single_field_parity_ok else 0
                        ),
                        parity_mismatch_count=(
                            0 if single_field_parity_ok else handoff_row_count
                        ),
                        kernel_side_typed_consumer_compatible=bool(
                            single_field_parity_ok
                        ),
                        current_wna16_arg_compatible=False,
                        live_enabled=False,
                        blocked=True,
                        block_reason="single_field_handoff_live_disabled",
                        payload_bytes=0,
                        ready_credit=False,
                        passed_to_kernel=False,
                        changes_kernel_launch_args=False,
                        live_compatible_with_current_wna16_args=False,
                    )
                )
                table_consume_ok = bool(table_consume_ok) and bool(
                    single_field_handle_handoff_canary.ready
                )
                handoff_attempt = PremapKernelArgHandoffAttemptRecord(
                    mode="readonly_kernel_arg_handoff_attempt",
                    mirror_hash=handoff_mirror.mirror_hash,
                    slot_hash=handoff_shadow_slot.slot_hash,
                    table_object_hash=table_object.object_hash,
                    row_count=handoff_row_count,
                    column_count=handoff_column_count,
                    schema_hash=handoff_schema_hash,
                    mirror_ready=handoff_mirror.ready,
                    gate_allowed=False,
                    blocked=True,
                    block_reason="kernel_arg_handoff_disabled_noop_gate",
                    payload_bytes=0,
                    passed_to_kernel=False,
                    changes_kernel_launch_args=False,
                )
                live_enabled = bool(kernel_arg_handoff_live_enabled)
                lab_gate_passed = bool(kernel_arg_handoff_lab_gate_passed)
                attempt_ready = bool(handoff_attempt.record_ready)
                live_eligible = bool(
                    live_enabled and lab_gate_passed and attempt_ready
                )
                if not live_enabled:
                    live_block_reason = "kernel_arg_handoff_live_disabled"
                elif not lab_gate_passed:
                    live_block_reason = "kernel_arg_handoff_lab_gate_not_passed"
                elif not attempt_ready:
                    live_block_reason = "kernel_arg_handoff_attempt_not_ready"
                else:
                    live_block_reason = (
                        "kernel_arg_handoff_kernel_consumer_not_connected"
                    )
                handoff_live_toggle = PremapKernelArgHandoffLiveToggleRecord(
                    mode="readonly_kernel_arg_handoff_live_toggle",
                    attempt_hash=handoff_attempt.attempt_hash,
                    table_object_hash=table_object.object_hash,
                    enabled=live_enabled,
                    lab_gate_passed=lab_gate_passed,
                    attempt_record_ready=attempt_ready,
                    live_eligible=live_eligible,
                    blocked=True,
                    block_reason=live_block_reason,
                    payload_bytes=0,
                    passed_to_kernel=False,
                    changes_kernel_launch_args=False,
                )
                live_toggle_ready = bool(handoff_live_toggle.record_ready)
                launch_schema_ready = bool(handoff_launch_schema_mirror.ready)
                integration_live_eligible = bool(
                    live_enabled
                    and lab_gate_passed
                    and live_toggle_ready
                    and launch_schema_ready
                )
                integration_consumer_connected = bool(
                    integration_live_eligible
                    and kernel_arg_handoff_consumer_connected
                )
                if not live_enabled:
                    integration_block_reason = "kernel_arg_handoff_live_disabled"
                elif not lab_gate_passed:
                    integration_block_reason = (
                        "kernel_arg_handoff_lab_gate_not_passed"
                    )
                elif not live_toggle_ready:
                    integration_block_reason = (
                        "kernel_arg_handoff_live_toggle_not_ready"
                    )
                elif not launch_schema_ready:
                    integration_block_reason = (
                        "kernel_arg_handoff_launch_schema_not_ready"
                    )
                elif integration_consumer_connected:
                    integration_block_reason = (
                        "kernel_arg_handoff_kernel_arg_pass_disabled"
                    )
                else:
                    integration_block_reason = (
                        "kernel_arg_handoff_kernel_consumer_not_connected"
                    )
                handoff_live_noop_integration = (
                    PremapKernelArgHandoffLiveNoopIntegrationRecord(
                        mode="readonly_kernel_arg_handoff_live_noop_integration",
                        live_toggle_hash=handoff_live_toggle.toggle_hash,
                        launch_schema_mirror_hash=(
                            handoff_launch_schema_mirror.launch_schema_mirror_hash
                        ),
                        table_object_hash=table_object.object_hash,
                        enabled=live_enabled,
                        lab_gate_passed=lab_gate_passed,
                        live_toggle_record_ready=live_toggle_ready,
                        launch_schema_ready=launch_schema_ready,
                        live_eligible=integration_live_eligible,
                        consumer_connected=integration_consumer_connected,
                        blocked=True,
                        block_reason=integration_block_reason,
                        payload_bytes=0,
                        passed_to_kernel=False,
                        changes_kernel_launch_args=False,
                    )
                )
                integration_ready = bool(handoff_live_noop_integration.record_ready)
                adapter_live_eligible = bool(
                    live_enabled and lab_gate_passed and integration_ready
                )
                adapter_consumer_connected = bool(
                    adapter_live_eligible
                    and kernel_arg_handoff_consumer_connected
                )
                adapter_kernel_arg_pass_live = bool(
                    adapter_consumer_connected
                    and kernel_arg_handoff_kernel_arg_pass_enabled
                )
                adapter_real_kernel_arg_handoff = bool(
                    adapter_kernel_arg_pass_live
                    and kernel_arg_handoff_real_kernel_arg_mutation_enabled
                )
                if not integration_ready:
                    adapter_block_reason = (
                        "kernel_arg_handoff_live_noop_integration_not_ready"
                    )
                elif not live_enabled:
                    adapter_block_reason = "kernel_arg_handoff_live_disabled"
                elif not lab_gate_passed:
                    adapter_block_reason = "kernel_arg_handoff_lab_gate_not_passed"
                elif adapter_real_kernel_arg_handoff:
                    adapter_block_reason = (
                        "kernel_arg_handoff_real_kernel_arg_mutation_live"
                    )
                elif adapter_kernel_arg_pass_live:
                    adapter_block_reason = "kernel_arg_handoff_kernel_arg_pass_live"
                elif adapter_consumer_connected:
                    adapter_block_reason = "kernel_arg_handoff_kernel_arg_pass_disabled"
                else:
                    adapter_block_reason = (
                        "kernel_arg_handoff_kernel_consumer_not_connected"
                    )
                adapter_blocked = not adapter_kernel_arg_pass_live
                handoff_live_consumer_adapter = (
                    PremapKernelArgHandoffLiveConsumerAdapterRecord(
                        mode="readonly_kernel_arg_handoff_live_consumer_adapter",
                        live_noop_integration_hash=(
                            handoff_live_noop_integration.integration_hash
                        ),
                        launch_schema_mirror_hash=(
                            handoff_launch_schema_mirror.launch_schema_mirror_hash
                        ),
                        table_object_hash=table_object.object_hash,
                        enabled=live_enabled,
                        lab_gate_passed=lab_gate_passed,
                        live_noop_integration_record_ready=integration_ready,
                        live_noop_integration_blocked=(
                            handoff_live_noop_integration.blocked
                        ),
                        live_noop_integration_block_reason=(
                            handoff_live_noop_integration.block_reason
                        ),
                        consumer_adapter_present=True,
                        consumer_connected=adapter_consumer_connected,
                        live_eligible=adapter_live_eligible,
                        blocked=adapter_blocked,
                        block_reason=adapter_block_reason,
                        payload_bytes=0,
                        passed_to_kernel=adapter_kernel_arg_pass_live,
                        changes_kernel_launch_args=adapter_kernel_arg_pass_live,
                        adapter_contract_live_pass=adapter_kernel_arg_pass_live,
                        real_kernel_arg_handoff=adapter_real_kernel_arg_handoff,
                    )
                )
                if not live_enabled:
                    kernel_side_block_reason = "kernel_side_consumer_live_disabled"
                elif not adapter_live_eligible:
                    kernel_side_block_reason = "kernel_side_consumer_not_eligible"
                elif not adapter_consumer_connected:
                    kernel_side_block_reason = "kernel_side_consumer_not_connected"
                elif adapter_kernel_arg_pass_live:
                    kernel_side_block_reason = (
                        "kernel_side_consumer_shadow_only_kernel_arg_pass_enabled"
                    )
                else:
                    kernel_side_block_reason = (
                        "kernel_side_consumer_kernel_arg_pass_disabled"
                    )
                kernel_side_consumer_schema_adapter = (
                    PremapKernelSideConsumerSchemaAdapterObject(
                        mode="readonly_kernel_side_consumer_schema_adapter",
                        semantic_adapter_hash=semantic_handle_adapter.adapter_hash,
                        semantic_adapter_ready=semantic_handle_adapter.ready,
                        table_object_hash=table_object.object_hash,
                        launch_schema_mirror_hash=(
                            handoff_launch_schema_mirror.launch_schema_mirror_hash
                        ),
                        row_count=handoff_row_count,
                        column_count=handoff_column_count,
                        table_schema_hash=handoff_schema_hash,
                        semantic_schema_hash=(
                            PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
                        ),
                        kernel_side_schema_name=(
                            PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME
                        ),
                        kernel_side_schema_hash=(
                            PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH
                        ),
                        kernel_side_field_count=len(
                            PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS
                        ),
                        row_order_hash=table_object.row_order_hash,
                        ordered_row_hash=table_object.ordered_row_hash,
                        required_source_hit_count=handoff_required_hit_count,
                        required_source_miss_count=handoff_required_miss_count,
                        optional_source_hit_count=handoff_optional_hit_count,
                        optional_source_miss_count=handoff_optional_miss_count,
                        handle_field_read_count=int(
                            table_consume_handle_field_read_count or 0
                        ),
                        consumer_schema_present=True,
                        consumer_connected=adapter_consumer_connected,
                        live_enabled=live_enabled,
                        live_eligible=adapter_live_eligible,
                        blocked=True,
                        block_reason=kernel_side_block_reason,
                        payload_bytes=0,
                        passed_to_kernel=False,
                        changes_kernel_launch_args=False,
                        live_compatible_with_current_wna16_args=False,
                    )
                )
                if not live_enabled:
                    typed_consumer_block_reason = (
                        "kernel_side_typed_consumer_live_disabled"
                    )
                elif not adapter_live_eligible:
                    typed_consumer_block_reason = (
                        "kernel_side_typed_consumer_not_eligible"
                    )
                elif not adapter_consumer_connected:
                    typed_consumer_block_reason = (
                        "kernel_side_typed_consumer_not_connected"
                    )
                elif adapter_kernel_arg_pass_live:
                    typed_consumer_block_reason = (
                        "kernel_side_typed_consumer_shadow_only_kernel_arg_pass_enabled"
                    )
                else:
                    typed_consumer_block_reason = (
                        "kernel_side_typed_consumer_kernel_arg_pass_disabled"
                    )
                kernel_side_typed_consumer_object = PremapKernelSideTypedConsumerObject(
                    mode="readonly_kernel_side_typed_consumer_object",
                    kernel_side_adapter_hash=(
                        kernel_side_consumer_schema_adapter.adapter_hash
                    ),
                    kernel_side_adapter_ready=(
                        kernel_side_consumer_schema_adapter.ready
                    ),
                    semantic_adapter_hash=semantic_handle_adapter.adapter_hash,
                    table_object_hash=table_object.object_hash,
                    launch_schema_mirror_hash=(
                        handoff_launch_schema_mirror.launch_schema_mirror_hash
                    ),
                    row_count=handoff_row_count,
                    column_count=handoff_column_count,
                    table_schema_hash=handoff_schema_hash,
                    semantic_schema_hash=(
                        PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
                    ),
                    kernel_side_schema_hash=(
                        PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH
                    ),
                    typed_consumer_schema_name=(
                        PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME
                    ),
                    typed_consumer_schema_hash=(
                        PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
                    ),
                    typed_consumer_field_count=len(
                        PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_FIELDS
                    ),
                    row_order_hash=table_object.row_order_hash,
                    ordered_row_hash=table_object.ordered_row_hash,
                    descriptor_ptr_handle_hash=(
                        semantic_handle_adapter.descriptor_ptr_handle_hash
                    ),
                    packed_weight_descriptor_handle_hash=(
                        semantic_handle_adapter.packed_weight_descriptor_handle_hash
                    ),
                    scale_metadata_handle_hash=(
                        semantic_handle_adapter.scale_metadata_handle_hash
                    ),
                    aux_metadata_handle_hash=(
                        semantic_handle_adapter.aux_metadata_handle_hash
                    ),
                    required_source_hit_count=handoff_required_hit_count,
                    required_source_miss_count=handoff_required_miss_count,
                    optional_source_hit_count=handoff_optional_hit_count,
                    optional_source_miss_count=handoff_optional_miss_count,
                    handle_field_read_count=int(
                        table_consume_handle_field_read_count or 0
                    ),
                    consumer_object_present=True,
                    consumer_connected=adapter_consumer_connected,
                    live_enabled=live_enabled,
                    live_eligible=adapter_live_eligible,
                    blocked=True,
                    block_reason=typed_consumer_block_reason,
                    payload_bytes=0,
                    passed_to_kernel=False,
                    changes_kernel_launch_args=False,
                    live_compatible_with_current_wna16_args=False,
                )
        return PremapDescriptorConsumerShimResult(
            execution_mode=str(execution_mode),
            object_count=int(read_result.object_hit_count),
            object_hash=read_result.object_hash,
            read_ok=bool(read_result.read_ok),
            shim_ok=bool(shim_ok),
            handle_table_row_count=handle_table_row_count,
            handle_table_column_count=handle_table_column_count,
            handle_table_schema_hash=handle_table_schema_hash,
            handle_table_read_ok=table_read_ok,
            handle_table_lifecycle_ok=table_lifecycle_ok,
            handle_table_per_row_parity_ok_count=table_parity_count,
            handle_table_row_miss_count=table_row_miss_count,
            handle_table_stale_row_count=table_stale_row_count,
            handle_table_passed_to_kernel=table_passed_to_kernel,
            handle_table_payload_bytes=handle_table_payload_bytes,
            handle_table_consume_ok=table_consume_ok,
            handle_table_consume_lifecycle_ok=table_consume_lifecycle_ok,
            handle_table_consume_row_count=table_consume_row_count,
            handle_table_consume_column_count=table_consume_column_count,
            handle_table_consume_schema_hash=table_consume_schema_hash,
            handle_table_consume_mode=table_consume_mode,
            handle_table_consume_source=table_consume_source,
            handle_table_consume_row_order_hash=table_consume_row_order_hash,
            handle_table_consume_ordered_row_hash=table_consume_ordered_row_hash,
            handle_table_consume_per_row_parity_ok_count=table_consume_parity_count,
            handle_table_consume_row_miss_count=table_consume_row_miss_count,
            handle_table_consume_stale_row_count=table_consume_stale_row_count,
            handle_table_consume_handle_field_read_count=(
                table_consume_handle_field_read_count
            ),
            handle_table_consume_required_handle_field_available_count=(
                table_consume_required_handle_field_available_count
            ),
            handle_table_consume_optional_handle_field_available_count=(
                table_consume_optional_handle_field_available_count
            ),
            handle_table_consume_descriptor_ptr_field_read_count=(
                table_consume_descriptor_ptr_field_read_count
            ),
            handle_table_consume_packed_weight_descriptor_field_read_count=(
                table_consume_packed_weight_descriptor_field_read_count
            ),
            handle_table_consume_scale_metadata_handle_field_read_count=(
                table_consume_scale_metadata_handle_field_read_count
            ),
            handle_table_consume_aux_metadata_handle_field_read_count=(
                table_consume_aux_metadata_handle_field_read_count
            ),
            handle_table_consume_descriptor_ptr_field_available_count=(
                table_consume_descriptor_ptr_field_available_count
            ),
            handle_table_consume_packed_weight_descriptor_field_available_count=(
                table_consume_packed_weight_descriptor_field_available_count
            ),
            handle_table_consume_scale_metadata_handle_field_available_count=(
                table_consume_scale_metadata_handle_field_available_count
            ),
            handle_table_consume_aux_metadata_handle_field_available_count=(
                table_consume_aux_metadata_handle_field_available_count
            ),
            handle_table_consume_source_hit_counts=table_consume_source_hit_counts,
            handle_table_consume_source_miss_counts=table_consume_source_miss_counts,
            handle_table_consume_passed_to_kernel=table_consume_passed_to_kernel,
            handle_table_consume_payload_bytes=table_consume_payload_bytes,
            kernel_arg_handoff_dry_run_mode=handoff_mode,
            kernel_arg_handoff_dry_run_ready=handoff_ready,
            kernel_arg_handoff_dry_run_row_count=handoff_row_count,
            kernel_arg_handoff_dry_run_column_count=handoff_column_count,
            kernel_arg_handoff_dry_run_schema_hash=handoff_schema_hash,
            kernel_arg_handoff_dry_run_required_source_hit_count=(
                handoff_required_hit_count
            ),
            kernel_arg_handoff_dry_run_required_source_miss_count=(
                handoff_required_miss_count
            ),
            kernel_arg_handoff_dry_run_optional_source_hit_count=(
                handoff_optional_hit_count
            ),
            kernel_arg_handoff_dry_run_optional_source_miss_count=(
                handoff_optional_miss_count
            ),
            kernel_arg_handoff_dry_run_payload_bytes=0,
            kernel_arg_handoff_dry_run_passed_to_kernel=False,
            kernel_arg_handoff_shadow_slot_mode=(
                handoff_shadow_slot.mode if handoff_shadow_slot is not None else None
            ),
            kernel_arg_handoff_shadow_slot_ready=(
                handoff_shadow_slot.ready if handoff_shadow_slot is not None else None
            ),
            kernel_arg_handoff_shadow_slot_hash=(
                handoff_shadow_slot.slot_hash
                if handoff_shadow_slot is not None
                else None
            ),
            kernel_arg_handoff_shadow_slot_table_object_hash=(
                handoff_shadow_slot.table_object_hash
                if handoff_shadow_slot is not None
                else None
            ),
            kernel_arg_handoff_shadow_slot_row_count=(
                handoff_shadow_slot.row_count
                if handoff_shadow_slot is not None
                else None
            ),
            kernel_arg_handoff_shadow_slot_column_count=(
                handoff_shadow_slot.column_count
                if handoff_shadow_slot is not None
                else None
            ),
            kernel_arg_handoff_shadow_slot_schema_hash=(
                handoff_shadow_slot.schema_hash
                if handoff_shadow_slot is not None
                else None
            ),
            kernel_arg_handoff_shadow_slot_required_source_hit_count=(
                handoff_shadow_slot.required_source_hit_count
                if handoff_shadow_slot is not None
                else None
            ),
            kernel_arg_handoff_shadow_slot_required_source_miss_count=(
                handoff_shadow_slot.required_source_miss_count
                if handoff_shadow_slot is not None
                else None
            ),
            kernel_arg_handoff_shadow_slot_optional_source_hit_count=(
                handoff_shadow_slot.optional_source_hit_count
                if handoff_shadow_slot is not None
                else None
            ),
            kernel_arg_handoff_shadow_slot_optional_source_miss_count=(
                handoff_shadow_slot.optional_source_miss_count
                if handoff_shadow_slot is not None
                else None
            ),
            kernel_arg_handoff_shadow_slot_payload_bytes=0,
            kernel_arg_handoff_shadow_slot_passed_to_kernel=False,
            kernel_arg_handoff_shadow_slot_changes_kernel_launch_args=False,
            kernel_arg_handoff_mirror_mode=(
                handoff_mirror.mode if handoff_mirror is not None else None
            ),
            kernel_arg_handoff_mirror_ready=(
                handoff_mirror.ready if handoff_mirror is not None else None
            ),
            kernel_arg_handoff_mirror_hash=(
                handoff_mirror.mirror_hash if handoff_mirror is not None else None
            ),
            kernel_arg_handoff_mirror_slot_hash=(
                handoff_mirror.slot_hash if handoff_mirror is not None else None
            ),
            kernel_arg_handoff_mirror_table_object_hash=(
                handoff_mirror.table_object_hash
                if handoff_mirror is not None
                else None
            ),
            kernel_arg_handoff_mirror_row_count=(
                handoff_mirror.row_count if handoff_mirror is not None else None
            ),
            kernel_arg_handoff_mirror_column_count=(
                handoff_mirror.column_count if handoff_mirror is not None else None
            ),
            kernel_arg_handoff_mirror_schema_hash=(
                handoff_mirror.schema_hash if handoff_mirror is not None else None
            ),
            kernel_arg_handoff_mirror_required_source_hit_count=(
                handoff_mirror.required_source_hit_count
                if handoff_mirror is not None
                else None
            ),
            kernel_arg_handoff_mirror_required_source_miss_count=(
                handoff_mirror.required_source_miss_count
                if handoff_mirror is not None
                else None
            ),
            kernel_arg_handoff_mirror_optional_source_hit_count=(
                handoff_mirror.optional_source_hit_count
                if handoff_mirror is not None
                else None
            ),
            kernel_arg_handoff_mirror_optional_source_miss_count=(
                handoff_mirror.optional_source_miss_count
                if handoff_mirror is not None
                else None
            ),
            kernel_arg_handoff_mirror_payload_bytes=(
                handoff_mirror.payload_bytes if handoff_mirror is not None else 0
            ),
            kernel_arg_handoff_mirror_passed_to_kernel=(
                handoff_mirror.passed_to_kernel if handoff_mirror is not None else False
            ),
            kernel_arg_handoff_mirror_changes_kernel_launch_args=(
                handoff_mirror.changes_kernel_launch_args
                if handoff_mirror is not None
                else False
            ),
            kernel_arg_handoff_launch_schema_mirror_mode=(
                handoff_launch_schema_mirror.mode
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_ready=(
                handoff_launch_schema_mirror.ready
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_hash=(
                handoff_launch_schema_mirror.launch_schema_mirror_hash
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash=(
                handoff_launch_schema_mirror.handoff_mirror_hash
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_slot_hash=(
                handoff_launch_schema_mirror.slot_hash
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_table_object_hash=(
                handoff_launch_schema_mirror.table_object_hash
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_row_count=(
                handoff_launch_schema_mirror.row_count
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_column_count=(
                handoff_launch_schema_mirror.column_count
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_table_schema_hash=(
                handoff_launch_schema_mirror.table_schema_hash
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_launch_schema_name=(
                handoff_launch_schema_mirror.launch_schema_name
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_launch_schema_hash=(
                handoff_launch_schema_mirror.launch_schema_hash
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count=(
                handoff_launch_schema_mirror.launch_arg_field_count
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_required_source_hit_count=(
                handoff_launch_schema_mirror.required_source_hit_count
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_required_source_miss_count=(
                handoff_launch_schema_mirror.required_source_miss_count
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count=(
                handoff_launch_schema_mirror.optional_source_hit_count
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count=(
                handoff_launch_schema_mirror.optional_source_miss_count
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_handle_field_read_count=(
                handoff_launch_schema_mirror.handle_field_read_count
                if handoff_launch_schema_mirror is not None
                else None
            ),
            kernel_arg_handoff_launch_schema_mirror_payload_bytes=(
                handoff_launch_schema_mirror.payload_bytes
                if handoff_launch_schema_mirror is not None
                else 0
            ),
            kernel_arg_handoff_launch_schema_mirror_passed_to_kernel=(
                handoff_launch_schema_mirror.passed_to_kernel
                if handoff_launch_schema_mirror is not None
                else False
            ),
            kernel_arg_handoff_launch_schema_mirror_changes_kernel_launch_args=(
                handoff_launch_schema_mirror.changes_kernel_launch_args
                if handoff_launch_schema_mirror is not None
                else False
            ),
            kernel_arg_handoff_attempt_mode=(
                handoff_attempt.mode if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_record_ready=(
                handoff_attempt.record_ready if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_hash=(
                handoff_attempt.attempt_hash if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_mirror_hash=(
                handoff_attempt.mirror_hash if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_slot_hash=(
                handoff_attempt.slot_hash if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_table_object_hash=(
                handoff_attempt.table_object_hash
                if handoff_attempt is not None
                else None
            ),
            kernel_arg_handoff_attempt_row_count=(
                handoff_attempt.row_count if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_column_count=(
                handoff_attempt.column_count if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_schema_hash=(
                handoff_attempt.schema_hash if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_mirror_ready=(
                handoff_attempt.mirror_ready if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_gate_allowed=(
                handoff_attempt.gate_allowed if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_blocked=(
                handoff_attempt.blocked if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_block_reason=(
                handoff_attempt.block_reason if handoff_attempt is not None else None
            ),
            kernel_arg_handoff_attempt_payload_bytes=(
                handoff_attempt.payload_bytes if handoff_attempt is not None else 0
            ),
            kernel_arg_handoff_attempt_passed_to_kernel=(
                handoff_attempt.passed_to_kernel
                if handoff_attempt is not None
                else False
            ),
            kernel_arg_handoff_attempt_changes_kernel_launch_args=(
                handoff_attempt.changes_kernel_launch_args
                if handoff_attempt is not None
                else False
            ),
            kernel_arg_handoff_live_toggle_mode=(
                handoff_live_toggle.mode if handoff_live_toggle is not None else None
            ),
            kernel_arg_handoff_live_toggle_record_ready=(
                handoff_live_toggle.record_ready
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_hash=(
                handoff_live_toggle.toggle_hash
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_attempt_hash=(
                handoff_live_toggle.attempt_hash
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_table_object_hash=(
                handoff_live_toggle.table_object_hash
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_enabled=(
                handoff_live_toggle.enabled
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_lab_gate_passed=(
                handoff_live_toggle.lab_gate_passed
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_attempt_record_ready=(
                handoff_live_toggle.attempt_record_ready
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_live_eligible=(
                handoff_live_toggle.live_eligible
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_blocked=(
                handoff_live_toggle.blocked
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_block_reason=(
                handoff_live_toggle.block_reason
                if handoff_live_toggle is not None
                else None
            ),
            kernel_arg_handoff_live_toggle_payload_bytes=(
                handoff_live_toggle.payload_bytes
                if handoff_live_toggle is not None
                else 0
            ),
            kernel_arg_handoff_live_toggle_passed_to_kernel=(
                handoff_live_toggle.passed_to_kernel
                if handoff_live_toggle is not None
                else False
            ),
            kernel_arg_handoff_live_toggle_changes_kernel_launch_args=(
                handoff_live_toggle.changes_kernel_launch_args
                if handoff_live_toggle is not None
                else False
            ),
            kernel_arg_handoff_live_noop_integration_mode=(
                handoff_live_noop_integration.mode
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_record_ready=(
                handoff_live_noop_integration.record_ready
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_hash=(
                handoff_live_noop_integration.integration_hash
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_live_toggle_hash=(
                handoff_live_noop_integration.live_toggle_hash
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash=(
                handoff_live_noop_integration.launch_schema_mirror_hash
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_table_object_hash=(
                handoff_live_noop_integration.table_object_hash
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_enabled=(
                handoff_live_noop_integration.enabled
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_lab_gate_passed=(
                handoff_live_noop_integration.lab_gate_passed
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_live_toggle_record_ready=(
                handoff_live_noop_integration.live_toggle_record_ready
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_launch_schema_ready=(
                handoff_live_noop_integration.launch_schema_ready
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_live_eligible=(
                handoff_live_noop_integration.live_eligible
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_consumer_connected=(
                handoff_live_noop_integration.consumer_connected
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_blocked=(
                handoff_live_noop_integration.blocked
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_block_reason=(
                handoff_live_noop_integration.block_reason
                if handoff_live_noop_integration is not None
                else None
            ),
            kernel_arg_handoff_live_noop_integration_payload_bytes=(
                handoff_live_noop_integration.payload_bytes
                if handoff_live_noop_integration is not None
                else 0
            ),
            kernel_arg_handoff_live_noop_integration_passed_to_kernel=(
                handoff_live_noop_integration.passed_to_kernel
                if handoff_live_noop_integration is not None
                else False
            ),
            kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args=(
                handoff_live_noop_integration.changes_kernel_launch_args
                if handoff_live_noop_integration is not None
                else False
            ),
            kernel_arg_handoff_live_consumer_adapter_mode=(
                handoff_live_consumer_adapter.mode
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_record_ready=(
                handoff_live_consumer_adapter.record_ready
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_hash=(
                handoff_live_consumer_adapter.adapter_hash
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash=(
                handoff_live_consumer_adapter.live_noop_integration_hash
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash=(
                handoff_live_consumer_adapter.launch_schema_mirror_hash
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_table_object_hash=(
                handoff_live_consumer_adapter.table_object_hash
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_enabled=(
                handoff_live_consumer_adapter.enabled
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_lab_gate_passed=(
                handoff_live_consumer_adapter.lab_gate_passed
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready=(
                handoff_live_consumer_adapter.live_noop_integration_record_ready
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked=(
                handoff_live_consumer_adapter.live_noop_integration_blocked
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason=(
                handoff_live_consumer_adapter.live_noop_integration_block_reason
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present=(
                handoff_live_consumer_adapter.consumer_adapter_present
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_consumer_connected=(
                handoff_live_consumer_adapter.consumer_connected
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_live_eligible=(
                handoff_live_consumer_adapter.live_eligible
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_blocked=(
                handoff_live_consumer_adapter.blocked
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_block_reason=(
                handoff_live_consumer_adapter.block_reason
                if handoff_live_consumer_adapter is not None
                else None
            ),
            kernel_arg_handoff_live_consumer_adapter_payload_bytes=(
                handoff_live_consumer_adapter.payload_bytes
                if handoff_live_consumer_adapter is not None
                else 0
            ),
            kernel_arg_handoff_live_consumer_adapter_passed_to_kernel=(
                handoff_live_consumer_adapter.passed_to_kernel
                if handoff_live_consumer_adapter is not None
                else False
            ),
            kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args=(
                handoff_live_consumer_adapter.changes_kernel_launch_args
                if handoff_live_consumer_adapter is not None
                else False
            ),
            kernel_arg_handoff_live_consumer_adapter_contract_live_pass=(
                handoff_live_consumer_adapter.adapter_contract_live_pass
                if handoff_live_consumer_adapter is not None
                else False
            ),
            kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff=(
                handoff_live_consumer_adapter.real_kernel_arg_handoff
                if handoff_live_consumer_adapter is not None
                else False
            ),
            kernel_arg_semantic_handle_adapter_mode=(
                semantic_handle_adapter.mode
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_ready=(
                semantic_handle_adapter.ready
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_hash=(
                semantic_handle_adapter.adapter_hash
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_table_object_hash=(
                semantic_handle_adapter.table_object_hash
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash=(
                semantic_handle_adapter.launch_schema_mirror_hash
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_row_count=(
                semantic_handle_adapter.row_count
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_column_count=(
                semantic_handle_adapter.column_count
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_table_schema_hash=(
                semantic_handle_adapter.table_schema_hash
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_semantic_schema_name=(
                semantic_handle_adapter.semantic_schema_name
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_semantic_schema_hash=(
                semantic_handle_adapter.semantic_schema_hash
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_semantic_field_count=(
                semantic_handle_adapter.semantic_field_count
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_required_source_hit_count=(
                semantic_handle_adapter.required_source_hit_count
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_required_source_miss_count=(
                semantic_handle_adapter.required_source_miss_count
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_optional_source_hit_count=(
                semantic_handle_adapter.optional_source_hit_count
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_optional_source_miss_count=(
                semantic_handle_adapter.optional_source_miss_count
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_handle_field_read_count=(
                semantic_handle_adapter.handle_field_read_count
                if semantic_handle_adapter is not None
                else None
            ),
            kernel_arg_semantic_handle_adapter_payload_bytes=(
                semantic_handle_adapter.payload_bytes
                if semantic_handle_adapter is not None
                else 0
            ),
            kernel_arg_semantic_handle_adapter_passed_to_kernel=(
                semantic_handle_adapter.passed_to_kernel
                if semantic_handle_adapter is not None
                else False
            ),
            kernel_arg_semantic_handle_adapter_changes_kernel_launch_args=(
                semantic_handle_adapter.changes_kernel_launch_args
                if semantic_handle_adapter is not None
                else False
            ),
            kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args=(
                semantic_handle_adapter.live_compatible_with_current_wna16_args
                if semantic_handle_adapter is not None
                else False
            ),
            single_field_handle_handoff_canary_mode=(
                single_field_handle_handoff_canary.mode
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_ready=(
                single_field_handle_handoff_canary.ready
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_hash=(
                single_field_handle_handoff_canary.canary_hash
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_field_name=(
                single_field_handle_handoff_canary.field_name
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_source=(
                single_field_handle_handoff_canary.source
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_mirror_mode=(
                single_field_handle_handoff_canary.mirror_mode
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_mirror_ready=(
                single_field_handle_handoff_canary.mirror_ready
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_mirror_field_name=(
                single_field_handle_handoff_canary.mirror_field_name
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_mirror_source=(
                single_field_handle_handoff_canary.mirror_source
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_table_object_hash=(
                single_field_handle_handoff_canary.table_object_hash
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_semantic_adapter_hash=(
                single_field_handle_handoff_canary.semantic_adapter_hash
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_row_count=(
                single_field_handle_handoff_canary.row_count
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_field_handle_count=(
                single_field_handle_handoff_canary.field_handle_count
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_field_handle_nonzero_count=(
                single_field_handle_handoff_canary.field_handle_nonzero_count
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_field_handle_zero_count=(
                single_field_handle_handoff_canary.field_handle_zero_count
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_field_handle_hash=(
                single_field_handle_handoff_canary.field_handle_hash
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_semantic_field_hash=(
                single_field_handle_handoff_canary.semantic_field_hash
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_mirror_handle_hash=(
                single_field_handle_handoff_canary.mirror_handle_hash
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_mirror_schema_hash=(
                single_field_handle_handoff_canary.mirror_schema_hash
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_parity_ok_count=(
                single_field_handle_handoff_canary.parity_ok_count
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_parity_mismatch_count=(
                single_field_handle_handoff_canary.parity_mismatch_count
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible=(
                single_field_handle_handoff_canary.kernel_side_typed_consumer_compatible
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_current_wna16_arg_compatible=(
                single_field_handle_handoff_canary.current_wna16_arg_compatible
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_live_enabled=(
                single_field_handle_handoff_canary.live_enabled
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_blocked=(
                single_field_handle_handoff_canary.blocked
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_block_reason=(
                single_field_handle_handoff_canary.block_reason
                if single_field_handle_handoff_canary is not None
                else None
            ),
            single_field_handle_handoff_canary_payload_bytes=(
                single_field_handle_handoff_canary.payload_bytes
                if single_field_handle_handoff_canary is not None
                else 0
            ),
            single_field_handle_handoff_canary_ready_credit=(
                single_field_handle_handoff_canary.ready_credit
                if single_field_handle_handoff_canary is not None
                else False
            ),
            single_field_handle_handoff_canary_passed_to_kernel=(
                single_field_handle_handoff_canary.passed_to_kernel
                if single_field_handle_handoff_canary is not None
                else False
            ),
            single_field_handle_handoff_canary_changes_kernel_launch_args=(
                single_field_handle_handoff_canary.changes_kernel_launch_args
                if single_field_handle_handoff_canary is not None
                else False
            ),
            single_field_handle_handoff_canary_live_compatible_with_current_wna16_args=(
                single_field_handle_handoff_canary.live_compatible_with_current_wna16_args
                if single_field_handle_handoff_canary is not None
                else False
            ),
            kernel_side_consumer_schema_adapter_mode=(
                kernel_side_consumer_schema_adapter.mode
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_ready=(
                kernel_side_consumer_schema_adapter.ready
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_hash=(
                kernel_side_consumer_schema_adapter.adapter_hash
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_semantic_adapter_hash=(
                kernel_side_consumer_schema_adapter.semantic_adapter_hash
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_table_object_hash=(
                kernel_side_consumer_schema_adapter.table_object_hash
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_launch_schema_mirror_hash=(
                kernel_side_consumer_schema_adapter.launch_schema_mirror_hash
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_row_count=(
                kernel_side_consumer_schema_adapter.row_count
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_column_count=(
                kernel_side_consumer_schema_adapter.column_count
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_table_schema_hash=(
                kernel_side_consumer_schema_adapter.table_schema_hash
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_semantic_schema_hash=(
                kernel_side_consumer_schema_adapter.semantic_schema_hash
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_kernel_side_schema_name=(
                kernel_side_consumer_schema_adapter.kernel_side_schema_name
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_kernel_side_schema_hash=(
                kernel_side_consumer_schema_adapter.kernel_side_schema_hash
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_kernel_side_field_count=(
                kernel_side_consumer_schema_adapter.kernel_side_field_count
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_required_source_hit_count=(
                kernel_side_consumer_schema_adapter.required_source_hit_count
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_required_source_miss_count=(
                kernel_side_consumer_schema_adapter.required_source_miss_count
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_optional_source_hit_count=(
                kernel_side_consumer_schema_adapter.optional_source_hit_count
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_optional_source_miss_count=(
                kernel_side_consumer_schema_adapter.optional_source_miss_count
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_handle_field_read_count=(
                kernel_side_consumer_schema_adapter.handle_field_read_count
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_consumer_schema_present=(
                kernel_side_consumer_schema_adapter.consumer_schema_present
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_consumer_connected=(
                kernel_side_consumer_schema_adapter.consumer_connected
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_live_enabled=(
                kernel_side_consumer_schema_adapter.live_enabled
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_live_eligible=(
                kernel_side_consumer_schema_adapter.live_eligible
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_blocked=(
                kernel_side_consumer_schema_adapter.blocked
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_block_reason=(
                kernel_side_consumer_schema_adapter.block_reason
                if kernel_side_consumer_schema_adapter is not None
                else None
            ),
            kernel_side_consumer_schema_adapter_payload_bytes=(
                kernel_side_consumer_schema_adapter.payload_bytes
                if kernel_side_consumer_schema_adapter is not None
                else 0
            ),
            kernel_side_consumer_schema_adapter_passed_to_kernel=(
                kernel_side_consumer_schema_adapter.passed_to_kernel
                if kernel_side_consumer_schema_adapter is not None
                else False
            ),
            kernel_side_consumer_schema_adapter_changes_kernel_launch_args=(
                kernel_side_consumer_schema_adapter.changes_kernel_launch_args
                if kernel_side_consumer_schema_adapter is not None
                else False
            ),
            kernel_side_consumer_schema_adapter_live_compatible_with_current_wna16_args=(
                kernel_side_consumer_schema_adapter.live_compatible_with_current_wna16_args
                if kernel_side_consumer_schema_adapter is not None
                else False
            ),
            kernel_side_typed_consumer_object_mode=(
                kernel_side_typed_consumer_object.mode
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_ready=(
                kernel_side_typed_consumer_object.ready
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_hash=(
                kernel_side_typed_consumer_object.object_hash
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_kernel_side_adapter_hash=(
                kernel_side_typed_consumer_object.kernel_side_adapter_hash
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_semantic_adapter_hash=(
                kernel_side_typed_consumer_object.semantic_adapter_hash
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_table_object_hash=(
                kernel_side_typed_consumer_object.table_object_hash
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_launch_schema_mirror_hash=(
                kernel_side_typed_consumer_object.launch_schema_mirror_hash
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_row_count=(
                kernel_side_typed_consumer_object.row_count
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_column_count=(
                kernel_side_typed_consumer_object.column_count
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_table_schema_hash=(
                kernel_side_typed_consumer_object.table_schema_hash
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_semantic_schema_hash=(
                kernel_side_typed_consumer_object.semantic_schema_hash
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_kernel_side_schema_hash=(
                kernel_side_typed_consumer_object.kernel_side_schema_hash
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_typed_consumer_schema_name=(
                kernel_side_typed_consumer_object.typed_consumer_schema_name
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_typed_consumer_schema_hash=(
                kernel_side_typed_consumer_object.typed_consumer_schema_hash
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_typed_consumer_field_count=(
                kernel_side_typed_consumer_object.typed_consumer_field_count
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_required_source_hit_count=(
                kernel_side_typed_consumer_object.required_source_hit_count
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_required_source_miss_count=(
                kernel_side_typed_consumer_object.required_source_miss_count
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_optional_source_hit_count=(
                kernel_side_typed_consumer_object.optional_source_hit_count
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_optional_source_miss_count=(
                kernel_side_typed_consumer_object.optional_source_miss_count
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_handle_field_read_count=(
                kernel_side_typed_consumer_object.handle_field_read_count
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_consumer_object_present=(
                kernel_side_typed_consumer_object.consumer_object_present
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_consumer_connected=(
                kernel_side_typed_consumer_object.consumer_connected
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_live_enabled=(
                kernel_side_typed_consumer_object.live_enabled
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_live_eligible=(
                kernel_side_typed_consumer_object.live_eligible
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_blocked=(
                kernel_side_typed_consumer_object.blocked
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_block_reason=(
                kernel_side_typed_consumer_object.block_reason
                if kernel_side_typed_consumer_object is not None
                else None
            ),
            kernel_side_typed_consumer_object_payload_bytes=(
                kernel_side_typed_consumer_object.payload_bytes
                if kernel_side_typed_consumer_object is not None
                else 0
            ),
            kernel_side_typed_consumer_object_passed_to_kernel=(
                kernel_side_typed_consumer_object.passed_to_kernel
                if kernel_side_typed_consumer_object is not None
                else False
            ),
            kernel_side_typed_consumer_object_changes_kernel_launch_args=(
                kernel_side_typed_consumer_object.changes_kernel_launch_args
                if kernel_side_typed_consumer_object is not None
                else False
            ),
            kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args=(
                kernel_side_typed_consumer_object.live_compatible_with_current_wna16_args
                if kernel_side_typed_consumer_object is not None
                else False
            ),
            native_typed_consumer_bridge_mode=(
                native_bridge_check.mode if native_bridge_check is not None else None
            ),
            native_typed_consumer_bridge_checked=(
                True if native_bridge_check is not None else None
            ),
            native_typed_consumer_bridge_ok=(
                native_bridge_check.ok if native_bridge_check is not None else None
            ),
            native_typed_consumer_bridge_input_hash=(
                native_bridge_check.input_hash
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_table_object_hash=(
                native_bridge_check.table_object_hash
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_schema_hash=(
                native_bridge_check.schema_hash
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_row_count=(
                native_bridge_check.row_count if native_bridge_check is not None else None
            ),
            native_typed_consumer_bridge_column_count=(
                native_bridge_check.column_count
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_required_handle_nonzero_count=(
                native_bridge_check.required_handle_nonzero_count
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_required_handle_zero_count=(
                native_bridge_check.required_handle_zero_count
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_optional_handle_nonzero_count=(
                native_bridge_check.optional_handle_nonzero_count
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_optional_handle_zero_count=(
                native_bridge_check.optional_handle_zero_count
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_expert_id_valid_count=(
                native_bridge_check.expert_id_valid_count
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_expert_id_invalid_count=(
                native_bridge_check.expert_id_invalid_count
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_address_key_hash_nonzero_count=(
                native_bridge_check.address_key_hash_nonzero_count
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_address_key_hash_zero_count=(
                native_bridge_check.address_key_hash_zero_count
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_failure_count=(
                len(native_bridge_check.failures)
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_failures=(
                native_bridge_check.failures
                if native_bridge_check is not None
                else None
            ),
            native_typed_consumer_bridge_payload_bytes=(
                native_bridge_check.payload_bytes
                if native_bridge_check is not None
                else 0
            ),
            native_typed_consumer_bridge_ready_credit=(
                native_bridge_check.ready_credit
                if native_bridge_check is not None
                else False
            ),
            native_typed_consumer_bridge_changes_router=(
                native_bridge_check.changes_router
                if native_bridge_check is not None
                else False
            ),
            native_typed_consumer_bridge_changes_descriptor_order=(
                native_bridge_check.changes_descriptor_order
                if native_bridge_check is not None
                else False
            ),
            native_typed_consumer_bridge_passed_to_kernel=(
                native_bridge_check.passed_to_kernel
                if native_bridge_check is not None
                else False
            ),
            native_typed_consumer_bridge_changes_kernel_launch_args=(
                native_bridge_check.changes_kernel_launch_args
                if native_bridge_check is not None
                else False
            ),
            native_stub_online_invocation_mode=(
                native_stub_canary.mode if native_stub_canary is not None else None
            ),
            native_stub_online_invocation_checked=(
                True if native_stub_canary is not None else None
            ),
            native_stub_online_invocation_ready=(
                native_stub_canary.ready if native_stub_canary is not None else None
            ),
            native_stub_online_invocation_ok=(
                native_stub_canary.ok if native_stub_canary is not None else None
            ),
            native_stub_online_invocation_native_checker_invoked=(
                native_stub_canary.native_checker_invoked
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_native_bridge_ok=(
                native_stub_canary.native_bridge_ok
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_package_hash=(
                native_stub_canary.package_hash
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_input_hash=(
                native_stub_canary.input_hash if native_stub_canary is not None else None
            ),
            native_stub_online_invocation_table_object_hash=(
                native_stub_canary.table_object_hash
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_schema_hash=(
                native_stub_canary.schema_hash
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_row_count=(
                native_stub_canary.row_count if native_stub_canary is not None else None
            ),
            native_stub_online_invocation_column_count=(
                native_stub_canary.column_count
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_required_handle_nonzero_count=(
                native_stub_canary.required_handle_nonzero_count
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_required_handle_zero_count=(
                native_stub_canary.required_handle_zero_count
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_optional_handle_nonzero_count=(
                native_stub_canary.optional_handle_nonzero_count
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_optional_handle_zero_count=(
                native_stub_canary.optional_handle_zero_count
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_expert_id_valid_count=(
                native_stub_canary.expert_id_valid_count
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_expert_id_invalid_count=(
                native_stub_canary.expert_id_invalid_count
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_address_key_hash_nonzero_count=(
                native_stub_canary.address_key_hash_nonzero_count
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_address_key_hash_zero_count=(
                native_stub_canary.address_key_hash_zero_count
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_requested=(
                native_stub_canary.invocation_requested
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_native_stub_invoked=(
                native_stub_canary.native_stub_invoked
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_blocked=(
                native_stub_canary.invocation_blocked
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_block_reason=(
                native_stub_canary.invocation_block_reason
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_failure_count=(
                len(native_stub_canary.failures)
                if native_stub_canary is not None
                else None
            ),
            native_stub_online_invocation_failures=(
                native_stub_canary.failures if native_stub_canary is not None else None
            ),
            native_stub_online_invocation_payload_bytes=(
                native_stub_canary.payload_bytes if native_stub_canary is not None else 0
            ),
            native_stub_online_invocation_ready_credit=(
                native_stub_canary.ready_credit
                if native_stub_canary is not None
                else False
            ),
            native_stub_online_invocation_changes_router=(
                native_stub_canary.changes_router
                if native_stub_canary is not None
                else False
            ),
            native_stub_online_invocation_changes_descriptor_order=(
                native_stub_canary.changes_descriptor_order
                if native_stub_canary is not None
                else False
            ),
            native_stub_online_invocation_passed_to_kernel=(
                native_stub_canary.passed_to_kernel
                if native_stub_canary is not None
                else False
            ),
            native_stub_online_invocation_changes_kernel_launch_args=(
                native_stub_canary.changes_kernel_launch_args
                if native_stub_canary is not None
                else False
            ),
            wna16_adjacent_typed_slot_name=(
                wna16_adjacent_typed_slot.name
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_mode=(
                wna16_adjacent_typed_slot.mode
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_source=(
                wna16_adjacent_typed_slot.source
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_checked=(
                wna16_adjacent_typed_slot.checked
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_ready=(
                wna16_adjacent_typed_slot.ready
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_input_hash=(
                wna16_adjacent_typed_slot.input_hash
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_table_object_hash=(
                wna16_adjacent_typed_slot.table_object_hash
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_schema_hash=(
                wna16_adjacent_typed_slot.schema_hash
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_row_count=(
                wna16_adjacent_typed_slot.row_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_row_ok_count=(
                wna16_adjacent_typed_slot.row_ok_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_error_count=(
                wna16_adjacent_typed_slot.error_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_all_handle_fields_read=(
                wna16_adjacent_typed_slot.all_handle_fields_read
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_packet_chain_depth=(
                wna16_adjacent_typed_slot.packet_chain_depth
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_field_mask=(
                wna16_adjacent_typed_slot.field_mask
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_descriptor_ptr_read_row_ok_count=(
                wna16_adjacent_typed_slot.descriptor_ptr_read_row_ok_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_packed_weight_descriptor_read_row_ok_count=(
                wna16_adjacent_typed_slot.packed_weight_descriptor_read_row_ok_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_scale_metadata_handle_read_row_ok_count=(
                wna16_adjacent_typed_slot.scale_metadata_handle_read_row_ok_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_aux_metadata_handle_read_row_ok_count=(
                wna16_adjacent_typed_slot.aux_metadata_handle_read_row_ok_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_expert_id_read_row_ok_count=(
                wna16_adjacent_typed_slot.expert_id_read_row_ok_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_address_key_hash_read_row_ok_count=(
                wna16_adjacent_typed_slot.address_key_hash_read_row_ok_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_row_metadata_read_row_ok_count=(
                wna16_adjacent_typed_slot.row_metadata_read_row_ok_count
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_row_hash_accumulator=(
                wna16_adjacent_typed_slot.row_hash_accumulator
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_field_read_hash_accumulator=(
                wna16_adjacent_typed_slot.field_read_hash_accumulator
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_row_metadata_hash_accumulator=(
                wna16_adjacent_typed_slot.row_metadata_hash_accumulator
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_failure_count=(
                len(wna16_adjacent_typed_slot.failures)
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_failures=(
                wna16_adjacent_typed_slot.failures
                if wna16_adjacent_typed_slot is not None
                else None
            ),
            wna16_adjacent_typed_slot_payload_bytes=(
                wna16_adjacent_typed_slot.payload_bytes
                if wna16_adjacent_typed_slot is not None
                else 0
            ),
            wna16_adjacent_typed_slot_passed_to_kernel=(
                wna16_adjacent_typed_slot.passed_to_kernel
                if wna16_adjacent_typed_slot is not None
                else False
            ),
            wna16_adjacent_typed_slot_changes_kernel_launch_args=(
                wna16_adjacent_typed_slot.changes_kernel_launch_args
                if wna16_adjacent_typed_slot is not None
                else False
            ),
            wna16_adjacent_typed_slot_current_wna16_arg_compatible=(
                wna16_adjacent_typed_slot.current_wna16_arg_compatible
                if wna16_adjacent_typed_slot is not None
                else False
            ),
            wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation=(
                wna16_adjacent_typed_slot.requires_wna16_arg_reinterpretation
                if wna16_adjacent_typed_slot is not None
                else False
            ),
            wna16_adjacent_typed_slot_explicit_typed_abi_slot=(
                wna16_adjacent_typed_slot.explicit_typed_abi_slot
                if wna16_adjacent_typed_slot is not None
                else True
            ),
            wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot=(
                wna16_adjacent_typed_slot.reuses_current_wna16_arg_slot
                if wna16_adjacent_typed_slot is not None
                else False
            ),
            kernel_side_typed_row_consumer_path_mode=(
                kernel_side_typed_row_consumer_path.mode
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_name=(
                kernel_side_typed_row_consumer_path.path_name
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_source=(
                kernel_side_typed_row_consumer_path.source
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_checked=(
                kernel_side_typed_row_consumer_path.checked
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_ready=(
                kernel_side_typed_row_consumer_path.ready
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_input_hash=(
                kernel_side_typed_row_consumer_path.input_hash
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_table_object_hash=(
                kernel_side_typed_row_consumer_path.table_object_hash
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_schema_hash=(
                kernel_side_typed_row_consumer_path.schema_hash
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_row_count=(
                kernel_side_typed_row_consumer_path.row_count
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_column_count=(
                kernel_side_typed_row_consumer_path.column_count
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_row_ok_count=(
                kernel_side_typed_row_consumer_path.row_ok_count
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_error_count=(
                kernel_side_typed_row_consumer_path.error_count
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_hash_accumulator=(
                kernel_side_typed_row_consumer_path.hash_accumulator
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_failure_count=(
                len(kernel_side_typed_row_consumer_path.failures)
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_failures=(
                kernel_side_typed_row_consumer_path.failures
                if kernel_side_typed_row_consumer_path is not None
                else None
            ),
            kernel_side_typed_row_consumer_path_payload_bytes=(
                kernel_side_typed_row_consumer_path.payload_bytes
                if kernel_side_typed_row_consumer_path is not None
                else 0
            ),
            kernel_side_typed_row_consumer_path_passed_to_kernel=(
                kernel_side_typed_row_consumer_path.passed_to_kernel
                if kernel_side_typed_row_consumer_path is not None
                else False
            ),
            kernel_side_typed_row_consumer_path_changes_kernel_launch_args=(
                kernel_side_typed_row_consumer_path.changes_kernel_launch_args
                if kernel_side_typed_row_consumer_path is not None
                else False
            ),
            kernel_side_typed_row_consumer_path_current_wna16_arg_compatible=(
                kernel_side_typed_row_consumer_path.current_wna16_arg_compatible
                if kernel_side_typed_row_consumer_path is not None
                else False
            ),
            handle_table_object_consumed=table_object_consumed,
            handle_table_object_hash=table_object_hash,
            handle_table_object_row_count=table_object_row_count,
            handle_table_object_lifecycle_ok=table_object_lifecycle_ok,
            handle_table_object_passed_to_kernel=table_object_passed_to_kernel,
            handle_table_object_payload_bytes=table_object_payload_bytes,
            prep_execution_dry_run_mode=prep_dry_run_mode,
            prep_execution_dry_run_source=prep_dry_run_source,
            prep_execution_dry_run_ok=prep_dry_run_ok,
            prep_execution_dry_run_row_count=prep_dry_run_row_count,
            prep_execution_dry_run_column_count=prep_dry_run_column_count,
            prep_execution_dry_run_schema_hash=prep_dry_run_schema_hash,
            prep_execution_dry_run_object_hash=prep_dry_run_object_hash,
            prep_execution_dry_run_lifecycle_ok=prep_dry_run_lifecycle_ok,
            prep_execution_dry_run_row_handle_parity_ok_count=(
                prep_dry_run_row_handle_parity_ok_count
            ),
            prep_execution_dry_run_descriptor_ptr_parity_ok_count=(
                prep_dry_run_descriptor_ptr_parity_ok_count
            ),
            prep_execution_dry_run_packed_weight_descriptor_parity_ok_count=(
                prep_dry_run_packed_weight_descriptor_parity_ok_count
            ),
            prep_execution_dry_run_scale_metadata_handle_parity_ok_count=(
                prep_dry_run_scale_metadata_handle_parity_ok_count
            ),
            prep_execution_dry_run_aux_metadata_handle_parity_ok_count=(
                prep_dry_run_aux_metadata_handle_parity_ok_count
            ),
            prep_execution_dry_run_row_handle_miss_count=(
                prep_dry_run_row_handle_miss_count
            ),
            prep_execution_dry_run_handle_field_read_count=(
                prep_dry_run_handle_field_read_count
            ),
            prep_execution_dry_run_required_handle_field_available_count=(
                prep_dry_run_required_handle_field_available_count
            ),
            prep_execution_dry_run_optional_handle_field_available_count=(
                prep_dry_run_optional_handle_field_available_count
            ),
            prep_execution_dry_run_descriptor_ptr_field_read_count=(
                prep_dry_run_descriptor_ptr_field_read_count
            ),
            prep_execution_dry_run_packed_weight_descriptor_field_read_count=(
                prep_dry_run_packed_weight_descriptor_field_read_count
            ),
            prep_execution_dry_run_scale_metadata_handle_field_read_count=(
                prep_dry_run_scale_metadata_handle_field_read_count
            ),
            prep_execution_dry_run_aux_metadata_handle_field_read_count=(
                prep_dry_run_aux_metadata_handle_field_read_count
            ),
            prep_execution_dry_run_descriptor_ptr_field_available_count=(
                prep_dry_run_descriptor_ptr_field_available_count
            ),
            prep_execution_dry_run_packed_weight_descriptor_field_available_count=(
                prep_dry_run_packed_weight_descriptor_field_available_count
            ),
            prep_execution_dry_run_scale_metadata_handle_field_available_count=(
                prep_dry_run_scale_metadata_handle_field_available_count
            ),
            prep_execution_dry_run_aux_metadata_handle_field_available_count=(
                prep_dry_run_aux_metadata_handle_field_available_count
            ),
            prep_execution_dry_run_passed_to_kernel=prep_dry_run_passed_to_kernel,
            prep_execution_dry_run_payload_bytes=prep_dry_run_payload_bytes,
            payload_bytes=0,
            ready_credit=False,
            changes_router=False,
            changes_descriptor_order=False,
            changes_kernel_launch_args=handle_table_kernel_mutation,
        )

    def execute_descriptor_address_prep_dry_run_readonly(
        self,
        table_object: PremapKernelArgShadowTableObject,
        *,
        read_result: PremapDescriptorConsumerReadResult | None = None,
        real_descriptor_handles_by_address_key: (
            dict[str, PremapRealDescriptorHandle] | None
        ) = None,
        execution_mode: str = "readonly_descriptor_address_prep_execution_dry_run",
        source: str = "kernel_arg_shadow_table_object",
    ) -> PremapDescriptorAddressPrepDryRunResult:
        """Validate a prepared descriptor/address table object for future execution.

        The returned object is the explicit no-op execution contract: it records
        table shape, schema, and identity that a future consumer could use, but
        it does not mutate launch arguments or move any payload.
        """

        expected_rows_ok = True
        if read_result is not None:
            expected_rows_ok = int(table_object.row_count) == int(
                read_result.object_hit_count
            )
        real_handles = real_descriptor_handles_by_address_key
        row_handle_parity_ok_count = 0
        descriptor_ptr_parity_ok_count = 0
        packed_weight_descriptor_parity_ok_count = 0
        scale_metadata_handle_parity_ok_count = 0
        aux_metadata_handle_parity_ok_count = 0
        row_handle_miss_count = 0
        handle_field_read_count = 0
        required_handle_field_available_count = 0
        optional_handle_field_available_count = 0
        descriptor_ptr_field_read_count = 0
        packed_weight_descriptor_field_read_count = 0
        scale_metadata_handle_field_read_count = 0
        aux_metadata_handle_field_read_count = 0
        descriptor_ptr_field_available_count = 0
        packed_weight_descriptor_field_available_count = 0
        scale_metadata_handle_field_available_count = 0
        aux_metadata_handle_field_available_count = 0
        for row in table_object.rows:
            descriptor_ptr = row.descriptor_ptr
            packed_weight_descriptor = row.packed_weight_descriptor
            scale_metadata_handle = row.scale_metadata_handle
            aux_metadata_handle = row.aux_metadata_handle
            handle_field_read_count += len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            descriptor_ptr_field_read_count += 1
            packed_weight_descriptor_field_read_count += 1
            scale_metadata_handle_field_read_count += 1
            aux_metadata_handle_field_read_count += 1
            required_handle_field_available_count += int(bool(descriptor_ptr))
            required_handle_field_available_count += int(bool(packed_weight_descriptor))
            required_handle_field_available_count += int(bool(scale_metadata_handle))
            optional_handle_field_available_count += int(aux_metadata_handle is not None)
            descriptor_ptr_field_available_count += int(bool(descriptor_ptr))
            packed_weight_descriptor_field_available_count += int(
                bool(packed_weight_descriptor)
            )
            scale_metadata_handle_field_available_count += int(
                bool(scale_metadata_handle)
            )
            aux_metadata_handle_field_available_count += int(
                aux_metadata_handle is not None
            )
            entry = self._addresses.get(row.address_key)
            real_handle = (
                real_handles.get(row.address_key) if real_handles is not None else None
            )
            consumer_object = (
                self._build_descriptor_consumer_object(
                    key=row.address_key,
                    handle=entry.handle,
                    real_handle=real_handle,
                )
                if entry is not None
                and (
                    real_handles is None
                    or (
                        real_handle is not None
                        and (
                            real_handle.address_key is None
                            or str(real_handle.address_key) == str(row.address_key)
                        )
                    )
                )
                else None
            )
            if consumer_object is None:
                row_handle_miss_count += 1
                continue
            descriptor_ptr_match = str(descriptor_ptr) == str(
                consumer_object.descriptor_ptr
            )
            packed_descriptor_match = str(packed_weight_descriptor) == str(
                consumer_object.packed_weight_descriptor
            )
            scale_metadata_match = str(scale_metadata_handle) == str(
                consumer_object.scale_metadata_handle
            )
            aux_metadata_match = aux_metadata_handle == consumer_object.aux_metadata_handle
            descriptor_ptr_parity_ok_count += int(descriptor_ptr_match)
            packed_weight_descriptor_parity_ok_count += int(packed_descriptor_match)
            scale_metadata_handle_parity_ok_count += int(scale_metadata_match)
            aux_metadata_handle_parity_ok_count += int(aux_metadata_match)
            row_handle_parity_ok_count += int(
                str(row.object_hash) == str(consumer_object.object_hash)
                and descriptor_ptr_match
                and packed_descriptor_match
                and scale_metadata_match
                and aux_metadata_match
            )
        lifecycle_ok = bool(table_object.lifecycle_ok)
        execution_ok = (
            int(table_object.row_count) > 0
            and expected_rows_ok
            and lifecycle_ok
            and row_handle_miss_count == 0
            and row_handle_parity_ok_count == int(table_object.row_count)
            and descriptor_ptr_parity_ok_count == int(table_object.row_count)
            and packed_weight_descriptor_parity_ok_count == int(table_object.row_count)
            and scale_metadata_handle_parity_ok_count == int(table_object.row_count)
            and aux_metadata_handle_parity_ok_count == int(table_object.row_count)
            and int(table_object.column_count)
            == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
            and str(table_object.schema_hash)
            == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            and int(table_object.payload_bytes) == 0
            and not bool(table_object.ready_credit)
            and not bool(table_object.changes_router)
            and not bool(table_object.changes_descriptor_order)
            and not bool(table_object.changes_kernel_launch_args)
            and not bool(table_object.passed_to_kernel)
        )
        return PremapDescriptorAddressPrepDryRunResult(
            execution_mode=str(execution_mode),
            source=str(source),
            row_count=int(table_object.row_count),
            column_count=int(table_object.column_count),
            schema_hash=str(table_object.schema_hash),
            table_object_hash=str(table_object.object_hash),
            row_order_hash=str(table_object.row_order_hash),
            ordered_row_hash=str(table_object.ordered_row_hash),
            lifecycle_ok=bool(lifecycle_ok),
            execution_ok=bool(execution_ok),
            row_handle_parity_ok_count=int(row_handle_parity_ok_count),
            descriptor_ptr_parity_ok_count=int(descriptor_ptr_parity_ok_count),
            packed_weight_descriptor_parity_ok_count=int(
                packed_weight_descriptor_parity_ok_count
            ),
            scale_metadata_handle_parity_ok_count=int(
                scale_metadata_handle_parity_ok_count
            ),
            aux_metadata_handle_parity_ok_count=int(
                aux_metadata_handle_parity_ok_count
            ),
            row_handle_miss_count=int(row_handle_miss_count),
            handle_field_read_count=int(handle_field_read_count),
            required_handle_field_available_count=int(
                required_handle_field_available_count
            ),
            optional_handle_field_available_count=int(
                optional_handle_field_available_count
            ),
            descriptor_ptr_field_read_count=int(descriptor_ptr_field_read_count),
            packed_weight_descriptor_field_read_count=int(
                packed_weight_descriptor_field_read_count
            ),
            scale_metadata_handle_field_read_count=int(
                scale_metadata_handle_field_read_count
            ),
            aux_metadata_handle_field_read_count=int(
                aux_metadata_handle_field_read_count
            ),
            descriptor_ptr_field_available_count=int(
                descriptor_ptr_field_available_count
            ),
            packed_weight_descriptor_field_available_count=int(
                packed_weight_descriptor_field_available_count
            ),
            scale_metadata_handle_field_available_count=int(
                scale_metadata_handle_field_available_count
            ),
            aux_metadata_handle_field_available_count=int(
                aux_metadata_handle_field_available_count
            ),
            payload_bytes=int(table_object.payload_bytes),
            ready_credit=bool(table_object.ready_credit),
            changes_router=bool(table_object.changes_router),
            changes_descriptor_order=bool(table_object.changes_descriptor_order),
            changes_kernel_launch_args=bool(table_object.changes_kernel_launch_args),
            passed_to_kernel=bool(table_object.passed_to_kernel),
        )

    def build_kernel_arg_shadow_table_readonly(
        self,
        address_keys: Iterable[str],
        *,
        read_result: PremapDescriptorConsumerReadResult,
        expected_object_hash_by_address_key: dict[str, str] | None = None,
        execution_mode: str = "readonly_kernel_arg_shadow_table",
        row_order_source: str = "canonical_address_key_order",
    ) -> PremapKernelArgShadowTableResult:
        """Build a no-op shadow table for future kernel argument handoff."""

        result, _ = self.build_kernel_arg_shadow_table_object_readonly(
            address_keys,
            read_result=read_result,
            expected_object_hash_by_address_key=expected_object_hash_by_address_key,
            execution_mode=execution_mode,
            row_order_source=row_order_source,
        )
        return result

    def build_kernel_arg_shadow_table_object_readonly(
        self,
        address_keys: Iterable[str],
        *,
        read_result: PremapDescriptorConsumerReadResult,
        expected_object_hash_by_address_key: dict[str, str] | None = None,
        real_descriptor_handles_by_address_key: (
            dict[str, PremapRealDescriptorHandle] | None
        ) = None,
        execution_mode: str = "readonly_kernel_arg_shadow_table",
        row_order_source: str = "canonical_address_key_order",
    ) -> tuple[PremapKernelArgShadowTableResult, PremapKernelArgShadowTableObject]:
        """Build and retain a read-only shadow table object for a consumer shim."""

        ordered_keys = [str(key) for key in address_keys]
        expected = expected_object_hash_by_address_key or {}
        real_handles = real_descriptor_handles_by_address_key
        row_order_hash = hashlib.sha256(
            "|".join(ordered_keys).encode("utf-8")
        ).hexdigest()
        row_parts: list[str] = []
        rows: list[PremapKernelArgShadowTableRow] = []
        row_miss_count = 0
        stale_row_count = 0
        per_row_parity_ok_count = 0
        for key in ordered_keys:
            object_hash = read_result.object_hash_by_address_key.get(key)
            if object_hash is None:
                row_miss_count += 1
                row_parts.append(f"{key}:<missing>")
                continue
            entry = self._addresses.get(key)
            real_handle = real_handles.get(key) if real_handles is not None else None
            consumer_object = (
                self._build_descriptor_consumer_object(
                    key=key,
                    handle=entry.handle,
                    real_handle=real_handle,
                )
                if entry is not None
                and (
                    real_handles is None
                    or (
                        real_handle is not None
                        and (
                            real_handle.address_key is None
                            or str(real_handle.address_key) == key
                        )
                    )
                )
                else None
            )
            if (
                consumer_object is None
                or str(consumer_object.object_hash) != str(object_hash)
            ):
                row_miss_count += 1
                row_parts.append(f"{key}:<missing>")
                continue
            row_parts.append(f"{key}:{object_hash}")
            rows.append(
                PremapKernelArgShadowTableRow(
                    address_key=key,
                    descriptor_ptr=str(consumer_object.descriptor_ptr),
                    packed_weight_descriptor=str(
                        consumer_object.packed_weight_descriptor
                    ),
                    scale_metadata_handle=str(consumer_object.scale_metadata_handle),
                    aux_metadata_handle=consumer_object.aux_metadata_handle,
                    object_hash=str(consumer_object.object_hash),
                    payload_bytes=0,
                    passed_to_kernel=False,
                )
            )
            if key in expected:
                if str(expected[key]) == str(object_hash):
                    per_row_parity_ok_count += 1
                else:
                    stale_row_count += 1
        ordered_row_hash = hashlib.sha256(
            "|".join(row_parts).encode("utf-8")
        ).hexdigest()
        lifecycle_ok = (
            bool(read_result.read_ok)
            and row_miss_count == 0
            and stale_row_count == 0
            and int(read_result.payload_bytes) == 0
        )
        expected_ok = not expected or per_row_parity_ok_count == len(expected)
        table_ok = (
            bool(lifecycle_ok)
            and expected_ok
            and len(ordered_keys) == int(read_result.object_hit_count)
            and len(rows) == len(ordered_keys)
        )
        result = PremapKernelArgShadowTableResult(
            execution_mode=str(execution_mode),
            row_order_source=str(row_order_source),
            row_count=len(ordered_keys),
            column_count=len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS),
            schema_hash=PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
            row_order_hash=row_order_hash,
            ordered_row_hash=ordered_row_hash,
            per_row_parity_ok_count=per_row_parity_ok_count,
            row_miss_count=row_miss_count,
            stale_row_count=stale_row_count,
            lifecycle_ok=bool(lifecycle_ok),
            table_ok=bool(table_ok),
            payload_bytes=0,
            ready_credit=False,
            changes_router=False,
            changes_descriptor_order=False,
            changes_kernel_launch_args=False,
            passed_to_kernel=False,
        )
        table_object = PremapKernelArgShadowTableObject(
            execution_mode=str(execution_mode),
            row_order_source=str(row_order_source),
            rows=tuple(rows),
            schema_hash=PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
            payload_bytes=0,
            ready_credit=False,
            changes_router=False,
            changes_descriptor_order=False,
            changes_kernel_launch_args=False,
            passed_to_kernel=False,
        )
        return result, table_object

    @staticmethod
    def _build_descriptor_consumer_object(
        *,
        key: str,
        handle: PremapAddressHandle,
        real_handle: PremapRealDescriptorHandle | None,
    ) -> PremapDescriptorConsumerObject | None:
        descriptor_ptr = (
            real_handle.descriptor_ptr
            if real_handle is not None
            else handle.descriptor_ptr
        )
        packed_descriptor = (
            real_handle.packed_weight_descriptor
            if real_handle is not None
            else handle.packed_weight_descriptor
        )
        scale_descriptor = (
            real_handle.scale_metadata_handle
            if real_handle is not None
            else handle.scale_metadata_handle
        )
        payload_bytes = int(handle.payload_bytes)
        if real_handle is not None:
            payload_bytes += int(real_handle.payload_bytes)
        if not (descriptor_ptr and packed_descriptor and scale_descriptor):
            return None
        if payload_bytes != 0:
            return None
        return PremapDescriptorConsumerObject(
            address_key=str(key),
            descriptor_ptr=str(descriptor_ptr),
            packed_weight_descriptor=str(packed_descriptor),
            scale_metadata_handle=str(scale_descriptor),
            aux_metadata_handle=(
                real_handle.aux_metadata_handle if real_handle is not None else None
            ),
            handle_hash=str(handle.handle_hash),
            real_handle_hash=(
                str(real_handle.handle_hash) if real_handle is not None else None
            ),
            payload_bytes=0,
            ready_credit=False,
            changes_router=False,
            changes_descriptor_order=False,
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
