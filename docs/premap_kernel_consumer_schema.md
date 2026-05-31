# Premap Kernel Consumer Schema

This artifact defines the typed descriptor/address object that a future native
consumer may read before the AWQ WNA16 fused-MoE launch. It is intentionally not
the current WNA16 kernel argument list, and it must not be represented by
pretending a Python tuple or tensor is a valid WNA16 kernel arg.

Machine-readable schema:

`configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml`

Native ABI header:

`microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h`

Native consumer adapter header:

`microbench/premap_kernel_consumer/premap_typed_consumer_adapter_v1.h`

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

The current lab gate has also advanced through readonly launch and dispatch
ABI envelopes:

```cpp
PremapFutureKernelNativeConsumerParamsV1
PremapFutureKernelNativeConsumerLaunchV1
PremapFutureKernelNativeConsumerDispatchV1
```

The dispatch envelope is still a future-consumer ABI, not a current WNA16
kernel argument. It validates the row window a future kernel would receive:

- `grid_x`, `block_x`, and `shared_mem_bytes`;
- `row_offset`, `row_limit`, and active row coverage;
- `rows_per_program == block_x`;
- row assignment formula
  `row_offset + program_id * rows_per_program + lane_id`;
- minimal launch cover and inactive lane accounting;
- a `program_iteration_hash` over the launch geometry and tail-program shape.

The machine-readable schema records the ABI binding explicitly:

```yaml
native_consumer_abi:
  abi_name: premap_kernel_side_typed_consumer_abi_v1
  cpp_header: microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h
  cpp_struct: PremapKernelSideTypedConsumerAbiV1
  handle_column_count: 4
  payload_bytes_allowed: false
  kernel_arg_pass_allowed: false
  adapter_name: premap_kernel_side_typed_consumer_adapter_v1
  adapter_header: microbench/premap_kernel_consumer/premap_typed_consumer_adapter_v1.h
  adapter_row_struct: PremapKernelSideTypedConsumerRowV1
  adapter_payload_deref_allowed: false
  adapter_kernel_arg_pass_allowed: false
  launch_envelope_name: premap_kernel_side_typed_consumer_launch_envelope_v1
  launch_envelope_struct: PremapKernelSideTypedConsumerLaunchEnvelopeV1
  launch_envelope_default_enabled: false
  launch_envelope_payload_bytes_required: 0
  launch_envelope_passed_to_kernel_required: false
  future_kernel_native_consumer_dispatch_abi_name: premap_future_kernel_native_consumer_dispatch_abi_v1
  future_kernel_native_consumer_dispatch_abi_struct: PremapFutureKernelNativeConsumerDispatchV1
  future_kernel_native_consumer_dispatch_abi_mode: readonly_future_kernel_native_consumer_dispatch_abi
  future_kernel_native_consumer_dispatch_abi_default_enabled: false
  future_kernel_native_consumer_dispatch_abi_payload_bytes_required: 0
  future_kernel_native_consumer_dispatch_abi_passed_to_kernel_required: false
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
7. `MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD`
8. `MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD`
9. `MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE`
10. `MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME`
11. `MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR`

`CHECK_POINTER_VISIBILITY` is the coarse legacy visibility check for required
handle columns. The per-field macros are the preferred ladder for future
canaries because they let the native checker enable descriptor, packed-weight,
scale-metadata, and optional aux-metadata validation independently.
The mirror macros are one-field-at-a-time checks that compare a row-view value
loaded through `PremapKernelSideTypedConsumerRowV1` with the same row in the ABI
table column. They validate the future typed consumer row-read path without
payload dereference or current WNA16 kernel-argument handoff.
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

## Current Evidence

Current post-review evidence:

```text
runner:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_window_tail4_32input.json

artifact check:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input.json

lab preflight:
  outputs/reports/premap_lab_preflight_post_review_latest_status.json

online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_passed_count = 31 / 31
tail_window_size = 4
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

The artifact checker now cross-checks runtime and strict deferred evidence
counts against the full preflight evidence scan.  It also binds the strict
default deferred evidence labels to the labels recorded in the status artifact,
so a preflight file cannot pass by preserving only the same deferred count while
changing which evidence was deferred.  The lab preflight rejects both
artifact-only evidence deferral and runner+artifact double deferral in the
normal lab path.

The compact lab preflight summary also mirrors the future dispatch ABI schema
without exposing a live kernel path:

```text
default_kernel_consumer_schema_row_field_names =
  descriptor_ptr, packed_weight_descriptor, scale_metadata_handle, aux_metadata_handle
default_kernel_consumer_schema_row_metadata_names =
  layer_id, expert_id, address_key_hash, row_order_hash, ordered_row_hash
default_kernel_consumer_dispatch_abi_name =
  premap_future_kernel_native_consumer_dispatch_abi_v1
default_kernel_consumer_dispatch_abi_current_wna16_arg_compatible = false
payload_bytes_required = 0
passed_to_kernel_required = false
changes_kernel_launch_args_required = false
```

The `default_kernel_consumer_dispatch_abi_*` summary keys are compact aliases
for the future-native dispatch ABI fields.  They must not be read as current
WNA16 launch-argument compatibility.

Tests cover multi-program dispatch windows (`grid_x > 1`) with both zero and
nonzero `row_offset`, so the future row assignment formula is validated beyond
the single-program tail-window case.

## Next Gates

1. Keep the current readonly dispatch ABI as the default lab preflight
   condition.
2. Build a real WNA16-adjacent consumer path only by adding an explicit typed
   ABI slot to a future native consumer or standalone adapter. Do not reinterpret
   the typed table as the current WNA16 argument list.
3. Only after that compatible consumer path passes should a single-field live
   handoff canary be considered, default disabled, starting with metadata/scale
   handles rather than payload pointers.
