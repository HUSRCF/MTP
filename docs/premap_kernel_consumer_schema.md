# Premap Kernel Consumer Schema

This artifact defines the typed descriptor/address object that a future native
consumer may read before the AWQ WNA16 fused-MoE launch. It is intentionally not
the current WNA16 kernel argument list, and it must not be represented by
pretending a Python tuple or tensor is a valid WNA16 kernel arg.

Machine-readable schema:

`configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml`

Native ABI header:

`microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h`

## Boundary

Current status is `readonly_shadow_only`.

Allowed:

- build a typed descriptor/address table object;
- read row fields from a consumer shim or native stub;
- verify row count, schema hash, row ordering hash, field parity, and lifetime;
- compile native debug consumers behind explicit macros.

Forbidden in the lab default gate:

- payload dereference or H2D payload movement;
- ready-credit accounting;
- router mutation;
- descriptor-order execution;
- passing the typed object to the real WNA16 fused-MoE kernel;
- mutating existing kernel launch arguments.

## Row ABI

The future native consumer reads a struct-of-arrays table in vLLM prelaunch
`sorted_token_ids` order. Required fields are address-level handles, not payload
contents:

| field | ABI dtype | shape | required | lifetime | ownership |
| --- | --- | --- | --- | --- | --- |
| `descriptor_ptr` | `uint64` | `[row_count]` | yes | model load epoch | model weight device |
| `packed_weight_descriptor` | `uint64` | `[row_count]` | yes | model load epoch | model weight device |
| `scale_metadata_handle` | `uint64` | `[row_count]` | yes | model load epoch | model weight device |
| `aux_metadata_handle` | `uint64` | `[row_count]` | no, null/zero allowed | model load epoch | model weight device |

Row metadata includes `layer_id`, `expert_id`, `address_key_hash`,
`row_order_hash`, and `ordered_row_hash`. The metadata lets the consumer verify
that the table matches the prelaunch descriptor/address resolution boundary
without passing any new kernel args.

The native canary consumes the table through:

```cpp
PremapKernelSideTypedConsumerAbiV1
```

The machine-readable schema records the ABI binding explicitly:

```yaml
native_consumer_abi:
  abi_name: premap_kernel_side_typed_consumer_abi_v1
  cpp_header: microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h
  cpp_struct: PremapKernelSideTypedConsumerAbiV1
  handle_column_count: 4
  payload_bytes_allowed: false
  kernel_arg_pass_allowed: false
```

This ABI is intentionally separate from the WNA16 launch argument schema.  A
successful native canary only proves typed-table readability by a future
consumer ABI; it does not authorize passing the table to the current WNA16
kernel.

## Macro Ladder

Native debug support must be injected one flag at a time:

1. `MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA`
2. `MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION`
3. `MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY`
4. `MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR`
5. `MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR`
6. `MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE`
7. `MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE`
8. `MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME`
9. `MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR`

`CHECK_POINTER_VISIBILITY` is the coarse legacy visibility check for required
handle columns. The per-field macros are the preferred ladder for future
canaries because they let the native checker enable descriptor, packed-weight,
scale-metadata, and optional aux-metadata validation independently.
`CHECK_AUX_METADATA_HANDLE` is intentionally stricter than the base ABI: it
requires the optional aux pointer to be present and non-zero, so it should only
be used in canaries where the exported table is expected to carry aux metadata.

The following flags are reserved for future canaries and are forbidden in the
lab default gate:

- `MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF`
- `MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS`

`MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA` checks the typed schema hash carried by
the native table. The runner injects these words from the project runtime schema
constant at compile time rather than relying on a hardcoded stub-local value.
For schema v1, the split hash words are:

```text
hi = c1384d55958c9aa7
lo = 613c01ceb8275e98
```

The optional `aux_metadata_handle` column may be absent at the JSON bridge
boundary. The runner can either materialize it as zero handles or run the native
stub with a null aux pointer. The stub must not reject zero/null optional aux
handles and must not dereference them.

`PremapKernelArgShadowTableObject.to_native_typed_consumer_input_dict()` exports
the runtime prepared table into the JSON shape accepted by the native stub. This
bridge hashes semantic string handles into deterministic non-zero u64 handle
identities for native row-iteration checks. It remains a no-payload identity
bridge, not a live WNA16 kernel argument handoff.

## Next Gates

1. Build a small HIP/C++ native stub that consumes this table and validates
   schema/layout/row iteration without touching the real WNA16 kernel.
2. Feed the prelaunch shim typed object into that stub under the existing lab
   gate.
3. Only after native-stub parity passes should a single-field replacement canary
   be considered, default disabled, starting with metadata/scale handles rather
   than payload pointers.
