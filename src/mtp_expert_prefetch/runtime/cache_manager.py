from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import asdict, dataclass, field

from mtp_expert_prefetch.runtime.premap import PremapAddressRecord, PremapPreparedPlan

PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH = hashlib.sha256(
    "|".join(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS).encode("utf-8")
).hexdigest()


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

    def execute_descriptor_consumer_shim_readonly(
        self,
        read_result: PremapDescriptorConsumerReadResult,
        *,
        kernel_arg_shadow_table_result: PremapKernelArgShadowTableResult | None = None,
        kernel_arg_shadow_table_object: PremapKernelArgShadowTableObject | None = None,
        descriptor_address_prep_dry_run_result: (
            PremapDescriptorAddressPrepDryRunResult | None
        ) = None,
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
