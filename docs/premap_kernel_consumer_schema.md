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
PremapFutureKernelNativeConsumerDispatchPtrV1
PremapFutureKernelNativeConsumerArgSlotV1
PremapFutureKernelNativeConsumerViewV1
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

The dispatch-pointer envelope is one step closer to a future kernel launch
slot: it passes a compact packet containing a device pointer to
`PremapFutureKernelNativeConsumerDispatchV1`, plus ABI version, struct-size,
result-size, zero-payload, and readonly/no-kernel-pass flags.  It is still a
standalone native-consumer canary.  It must not be interpreted as permission to
pass a typed table or dispatch packet into the current WNA16 kernel.

The arg-slot envelope adds one more level of future-kernel indirection:
`PremapFutureKernelNativeConsumerArgSlotV1` points at the dispatch-pointer
packet and carries its own ABI version, packet-size, result-size,
zero-payload, and readonly/no-kernel-pass flags.  This models the compact slot
a future kernel launch could receive while preserving the same lab boundary:
the current WNA16 kernel arguments are still untouched.

The consumer-view envelope decodes that future arg slot into the row window a
future kernel-side consumer would iterate:
`PremapFutureKernelNativeConsumerViewV1` carries native params plus
`source_packet_chain_depth`, `row_offset`, `row_limit`, and `rows_per_program`.
The native stub must read all four handle fields from this view.  This still
does not pass the object to the current WNA16 kernel and still forbids payload
dereference.

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
  future_kernel_native_consumer_dispatch_ptr_abi_name: premap_future_kernel_native_consumer_dispatch_ptr_abi_v1
  future_kernel_native_consumer_dispatch_ptr_abi_struct: PremapFutureKernelNativeConsumerDispatchPtrV1
  future_kernel_native_consumer_dispatch_ptr_abi_mode: readonly_future_kernel_native_consumer_dispatch_ptr_abi
  future_kernel_native_consumer_dispatch_ptr_abi_default_enabled: false
  future_kernel_native_consumer_dispatch_ptr_abi_payload_bytes_required: 0
  future_kernel_native_consumer_dispatch_ptr_abi_passed_to_kernel_required: false
  future_kernel_native_consumer_arg_slot_abi_name: premap_future_kernel_native_consumer_arg_slot_abi_v1
  future_kernel_native_consumer_arg_slot_abi_struct: PremapFutureKernelNativeConsumerArgSlotV1
  future_kernel_native_consumer_arg_slot_abi_mode: readonly_future_kernel_native_consumer_arg_slot_abi
  future_kernel_native_consumer_arg_slot_abi_default_enabled: false
  future_kernel_native_consumer_arg_slot_abi_payload_bytes_required: 0
  future_kernel_native_consumer_arg_slot_abi_passed_to_kernel_required: false
  future_kernel_native_consumer_view_abi_name: premap_future_kernel_native_consumer_view_abi_v1
  future_kernel_native_consumer_view_abi_struct: PremapFutureKernelNativeConsumerViewV1
  future_kernel_native_consumer_view_abi_mode: readonly_future_kernel_native_consumer_view_abi
  future_kernel_native_consumer_view_abi_source: premap_future_kernel_native_consumer_arg_slot_abi_v1
  future_kernel_native_consumer_view_abi_default_enabled: false
  future_kernel_native_consumer_view_abi_payload_bytes_required: 0
  future_kernel_native_consumer_view_abi_passed_to_kernel_required: false
  future_kernel_native_consumer_view_abi_current_wna16_arg_compatible: false
  future_kernel_native_consumer_view_abi_requires_wna16_arg_reinterpretation: false
  future_kernel_native_consumer_view_abi_source_packet_chain_depth_required: 3
  future_kernel_native_consumer_abi_layout_reported: true
  future_kernel_native_consumer_launch_abi_layout_reported: true
  future_kernel_native_consumer_dispatch_abi_layout_reported: true
  future_kernel_native_consumer_dispatch_ptr_abi_layout_reported: true
  future_kernel_native_consumer_arg_slot_abi_layout_reported: true
  future_kernel_native_consumer_view_abi_layout_reported: true
```

This ABI is intentionally separate from the WNA16 launch argument schema.  A
successful native canary only proves typed-table readability by a future
consumer ABI; it does not authorize passing the table to the current WNA16
kernel.

The schema also carries a `required_gate_checks` block.  This block is part of
the lab preflight contract, not just documentation: the checker requires the
consumer-view envelope, row layout, handle projection, all four handle fields,
source packet chain depth of three, kernel-entry summary and kernel-entry args
row-metadata reads, zero payload bytes, no kernel pass, no kernel launch
argument mutation, and `current_wna16_arg_compatible = false`.

The native stub also reports C++/HIP layout metadata for the future native
consumer params, launch envelope, and dispatch wrapper: struct size, alignment,
and critical field offsets.  The artifact checker requires these fields so the
lab gate can catch accidental ABI drift before any real kernel argument handoff
is attempted.  The schema also pins the expected numeric layout values; a field
name match alone is not sufficient for lab acceptance.

The dispatch-pointer packet layout is pinned separately from the pointed-to
dispatch layout:

```text
PremapFutureKernelNativeConsumerDispatchPtrV1
  size = 32
  align = 8
  offset(dispatch) = 0
  offset(abi_version) = 8
  offset(dispatch_struct_size) = 12
  offset(result_struct_size) = 16
  offset(payload_bytes) = 20
  offset(flags) = 24
```

The pointed-to dispatch struct and the result struct remain pinned as
`PremapFutureKernelNativeConsumerDispatchV1` and
`PremapFutureKernelNativeConsumerDispatchResultV1`; the pointer packet only
changes how a future kernel-side consumer would receive the dispatch metadata.
It does not change payload, readiness, router, descriptor order, or the live
WNA16 launch argument contract.

The future kernel argument-slot packet is pinned one layer above the dispatch
pointer packet.  It represents the mirror object a future kernel launcher would
bind as a typed native argument bundle, while remaining disconnected from the
current WNA16 kernel arguments:

```text
PremapFutureKernelNativeConsumerArgSlotV1
  size = 32
  align = 8
  offset(dispatch_ptr) = 0
  offset(abi_version) = 8
  offset(dispatch_ptr_struct_size) = 12
  offset(result_struct_size) = 16
  offset(payload_bytes) = 20
  offset(flags) = 24
```

The future native consumer-view packet is pinned as the decoded row-window view
that a future kernel-side consumer would read after resolving the arg slot:

```text
PremapFutureKernelNativeConsumerViewV1
  size = 208
  align = 8
  params_size = 112
  params_align = 8
  result_size = 80
  result_align = 8
  offset(params) = 0
  offset(abi_version) = 112
  offset(source_packet_chain_depth) = 116
  offset(row_offset) = 120
  offset(row_limit) = 124
  offset(rows_per_program) = 128
  offset(payload_bytes) = 132
  offset(flags) = 136
```

The row adapter layout consumed through the view is pinned separately:

```text
PremapKernelSideTypedConsumerRowV1
  size = 56
  align = 8
  offset(descriptor_ptr) = 0
  offset(packed_weight_descriptor) = 8
  offset(scale_metadata_handle) = 16
  offset(aux_metadata_handle) = 24
  offset(expert_id) = 32
  offset(address_key_hash) = 40
  offset(row_index) = 48
```

The lab gate requires `source_packet_chain_depth = 3`, all four typed handle
fields readable through the view, `payload_bytes = 0`, `passed_to_kernel =
false`, and `current_wna16_arg_compatible = false`.

The compact future kernel-entry summary is pinned as the next no-op bridge.
Unlike the debug packet canary, the native kernel receives only the future
kernel-arg packet plus a summary pointer, then resolves the program-view chain
and typed rows internally:

```text
PremapFutureKernelNativeConsumerKernelEntrySummaryV1
  abi_version = 1
  packet_valid = 1
  row_count = active_rows
  row_ok_count = active_rows
  descriptor_ptr_read_ok_count = active_rows
  packed_weight_descriptor_read_ok_count = active_rows
  scale_metadata_handle_read_ok_count = active_rows
  aux_metadata_handle_read_ok_count = active_rows
  error_count = 0
  field_mask = 0xf
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
  current_wna16_arg_compatible = false
  requires_wna16_arg_reinterpretation = false
```

Its native layout is also pinned:

```text
future_kernel_native_consumer_kernel_entry_summary_struct_size = 104
future_kernel_native_consumer_kernel_entry_summary_struct_align = 8
future_kernel_native_consumer_kernel_entry_summary_offset_abi_version = 0
future_kernel_native_consumer_kernel_entry_summary_offset_packet_valid = 4
future_kernel_native_consumer_kernel_entry_summary_offset_row_count = 8
future_kernel_native_consumer_kernel_entry_summary_offset_row_ok_count = 12
future_kernel_native_consumer_kernel_entry_summary_offset_descriptor_ptr_read_ok_count = 16
future_kernel_native_consumer_kernel_entry_summary_offset_packed_weight_descriptor_read_ok_count = 20
future_kernel_native_consumer_kernel_entry_summary_offset_scale_metadata_handle_read_ok_count = 24
future_kernel_native_consumer_kernel_entry_summary_offset_aux_metadata_handle_read_ok_count = 28
future_kernel_native_consumer_kernel_entry_summary_offset_expert_id_read_ok_count = 32
future_kernel_native_consumer_kernel_entry_summary_offset_address_key_hash_read_ok_count = 36
future_kernel_native_consumer_kernel_entry_summary_offset_row_metadata_read_ok_count = 40
future_kernel_native_consumer_kernel_entry_summary_offset_error_count = 44
future_kernel_native_consumer_kernel_entry_summary_offset_field_mask = 48
future_kernel_native_consumer_kernel_entry_summary_offset_payload_bytes = 52
future_kernel_native_consumer_kernel_entry_summary_offset_passed_to_kernel = 56
future_kernel_native_consumer_kernel_entry_summary_offset_changes_kernel_launch_args = 60
future_kernel_native_consumer_kernel_entry_summary_offset_current_wna16_arg_compatible = 64
future_kernel_native_consumer_kernel_entry_summary_offset_requires_wna16_arg_reinterpretation = 68
future_kernel_native_consumer_kernel_entry_summary_offset_reserved = 72
future_kernel_native_consumer_kernel_entry_summary_offset_row_hash_accumulator = 80
future_kernel_native_consumer_kernel_entry_summary_offset_field_read_hash_accumulator = 88
future_kernel_native_consumer_kernel_entry_summary_offset_row_metadata_hash_accumulator = 96
```

This summary is still diagnostic-only: it validates that a compact future
kernel entry can consume the typed handle table, but it is not passed to the
current WNA16 fused-MoE kernel and does not authorize payload movement.

The next envelope is the single-argument future kernel entry ABI:

```text
PremapFutureKernelNativeConsumerKernelEntryArgsV1
  size = 40
  align = 8
  offset(kernel_arg_packet) = 0
  offset(summary) = 8
  offset(abi_version) = 16
  offset(kernel_arg_packet_struct_size) = 20
  offset(summary_struct_size) = 24
  offset(payload_bytes) = 28
  offset(flags) = 32
```

The native stub launches a separate canary kernel that receives only this
single entry-args object.  The object points at the future kernel-arg packet
and the compact summary buffer, then the kernel resolves the typed rows through
the same packet chain.  This is closer to a future kernel launch ABI than the
two-argument diagnostic entry, but it still forbids payload dereference and is
not connected to the current WNA16 fused-MoE kernel argument list.

The window-sweep checker also follows each child canary's native stub artifact
and validates the consumer-view layout relationship:

```text
offset(params) = 0
offset(abi_version) = params_size
source_packet_chain_depth / row_offset / row_limit / rows_per_program /
payload_bytes / flags are contiguous 32-bit fields
offset(flags) + 4 <= size
size and result_size respect their reported alignments
typed row handle fields use the pinned 64-bit row adapter offsets
```

This keeps the online prelaunch canary tied to the future kernel-side ABI
packet shape, not only to JSON summary field names.

## Artifact Checker Path Contract

The online native-stub canary runner writes the exact strict preflight artifacts
that belong to that runner:

```text
preflight_output_json
preflight_status_output_json
```

`scripts/check_premap_online_native_stub_canary_artifacts.py` follows those
runner-recorded paths by default.  This is the preferred lab workflow because
the runner, its final no-defer preflight, and its summary/status artifact must
be checked as one evidence bundle.

Explicit `--preflight-json` and `--status-json` are still available for manual
cross-checks, but they should only be used when intentionally comparing against
non-runner-recorded artifacts.  Passing a generic preflight/status filename for
a specialized runner can produce a real mismatch even when the runner itself is
valid.

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
12. `MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI`
13. `MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI`

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
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json

artifact check:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_hard_hashchain_preflight_32tables.json

lab preflight:
  outputs/reports/premap_lab_preflight_default_with_online_merged_summary_fields.json

online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_passed_count = 31 / 31
final_preflight_passed = true
artifact_check_passed = true
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
default_kernel_consumer_dispatch_abi_mode =
  readonly_future_kernel_native_consumer_dispatch_abi
default_kernel_consumer_dispatch_abi_row_assignment_formula =
  row_offset + program_id * rows_per_program + lane_id
default_kernel_consumer_dispatch_abi_current_wna16_arg_compatible = false
default_kernel_consumer_dispatch_ptr_abi_name =
  premap_future_kernel_native_consumer_dispatch_ptr_abi_v1
default_kernel_consumer_dispatch_ptr_abi_mode =
  readonly_future_kernel_native_consumer_dispatch_ptr_abi
default_kernel_consumer_dispatch_ptr_abi_current_wna16_arg_compatible = false
default_kernel_consumer_online_merged_multiprogram_source_count = 32
default_kernel_consumer_online_merged_multiprogram_row_count = 1841
default_kernel_consumer_online_merged_multiprogram_dispatch_row_offset = 0
default_kernel_consumer_online_merged_multiprogram_dispatch_row_limit = 1841
default_kernel_consumer_online_merged_multiprogram_dispatch_active_rows = 1841
default_kernel_consumer_online_merged_multiprogram_hashchain_equal = true
default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked = true
payload_bytes_required = 0
passed_to_kernel_required = false
changes_kernel_launch_args_required = false
```

The `default_kernel_consumer_dispatch_abi_*` and
`default_kernel_consumer_dispatch_ptr_abi_*` summary keys are compact aliases
for the future-native dispatch ABI fields.  They must not be read as current
WNA16 launch-argument compatibility. The
`default_kernel_consumer_online_merged_multiprogram_*` fields summarize the
required online-merged full-table runner evidence: 32 real online prelaunch
exports merged into a 1841-row native stream. Tail-window artifacts are
supporting diagnostics only and are not accepted as the required default lab
gate evidence.
The unprefixed `payload_bytes_required`, `passed_to_kernel_required`, and
`changes_kernel_launch_args_required` entries in this compact block are the
lab-summary contract aliases for the default gate's zero-payload/no-kernel-arg
requirements.

The compact summary can be checked without rerunning the full preflight:

```bash
python scripts/check_premap_lab_preflight_summary.py \
  outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.json \
  --output-json \
  outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.check.json
```

The checker requires:

```text
passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
payload_bytes_required = 0
passed_to_kernel_required = false
changes_kernel_launch_args_required = false
default_kernel_consumer_online_merged_multiprogram_source_count >= 32
default_kernel_consumer_online_merged_multiprogram_dispatch_active_rows =
  default_kernel_consumer_online_merged_multiprogram_row_count
default_kernel_consumer_online_merged_multiprogram_hashchain_equal = true
default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked = true
default_kernel_consumer_online_merged_multiprogram_no_payload = true
default_kernel_consumer_online_merged_multiprogram_passed_to_kernel = false
default_kernel_consumer_online_merged_multiprogram_changes_kernel_launch_args = false
all gate/schema/evidence SHA256 summary fields are present
```

Tests cover multi-program dispatch windows (`grid_x > 1`) with both zero and
nonzero `row_offset`, so the future row assignment formula is validated beyond
the single-program tail-window case.

## Future Kernel-Arg Packet ABI

The latest native-consumer bridge adds one more explicit ABI layer:

```text
PremapFutureKernelNativeConsumerKernelArgPacketV1
```

This packet is a compact future-kernel argument object.  It contains a pointer
to `PremapFutureKernelNativeConsumerProgramViewPtrV1` plus ABI version,
dependent struct sizes, `payload_bytes`, and readonly/no-kernel flags.  A
future standalone native consumer can receive this packet and walk the typed
handle table through:

```text
kernel_arg_packet
  -> program_view_ptr
  -> program_view
  -> consumer_view
  -> typed descriptor/address rows
```

The packet is intentionally not compatible with the current WNA16 fused-MoE
kernel argument list:

```text
future_kernel_native_consumer_kernel_arg_packet_payload_bytes = 0
future_kernel_native_consumer_kernel_arg_packet_passed_to_kernel = false
future_kernel_native_consumer_kernel_arg_packet_changes_kernel_launch_args = false
future_kernel_native_consumer_kernel_arg_packet_current_wna16_arg_compatible = false
future_kernel_native_consumer_kernel_arg_packet_requires_wna16_arg_reinterpretation = false
```

The schema pins the packet layout:

```text
future_kernel_native_consumer_kernel_arg_packet_struct_size = 32
future_kernel_native_consumer_kernel_arg_packet_struct_align = 8
future_kernel_native_consumer_kernel_arg_packet_program_view_ptr_struct_size = 32
future_kernel_native_consumer_kernel_arg_packet_result_struct_size = 64
future_kernel_native_consumer_kernel_arg_packet_offset_program_view_ptr = 0
future_kernel_native_consumer_kernel_arg_packet_offset_abi_version = 8
future_kernel_native_consumer_kernel_arg_packet_offset_program_view_ptr_struct_size = 12
future_kernel_native_consumer_kernel_arg_packet_offset_result_struct_size = 16
future_kernel_native_consumer_kernel_arg_packet_offset_payload_bytes = 20
future_kernel_native_consumer_kernel_arg_packet_offset_flags = 24
```

The next readonly wrapper is `PremapFutureKernelNativeConsumerKernelEntryArgsV1`.
It carries a pointer to the kernel-arg packet, a pointer to the entry summary,
and no payload/kernel launch mutation.  The schema pins its layout separately:

```text
future_kernel_native_consumer_kernel_entry_args_struct_size = 40
future_kernel_native_consumer_kernel_entry_args_struct_align = 8
future_kernel_native_consumer_kernel_entry_args_kernel_arg_packet_struct_size = 32
future_kernel_native_consumer_kernel_entry_args_summary_struct_size = 104
future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet = 0
future_kernel_native_consumer_kernel_entry_args_offset_summary = 8
future_kernel_native_consumer_kernel_entry_args_offset_abi_version = 16
future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet_struct_size = 20
future_kernel_native_consumer_kernel_entry_args_offset_summary_struct_size = 24
future_kernel_native_consumer_kernel_entry_args_offset_payload_bytes = 28
future_kernel_native_consumer_kernel_entry_args_offset_flags = 32
```

The strict lab gate now requires both packet layers explicitly:

```text
require_child_program_view_ptr_abi = true
require_child_kernel_arg_packet_abi = true
require_child_kernel_entry_args_abi = true
```

When `require_child_kernel_arg_packet_abi` is false, the static checker remains
compatible with older artifacts that did not emit packet fields.  When it is
true, the checker requires packet source, row count, row-ok count, field masks,
and the no-payload/no-kernel/no-WNA16-reinterpretation safety bits.

The packet checker also requires explicit per-row field-read evidence for the
future consumer handles:

```text
future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_*
future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_*
future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_*
future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_*
```

These counters prove that the compact packet path reaches the same typed
descriptor/address handle columns as the arg-slot and consumer-view paths.  They
remain readonly evidence only: no payload is dereferenced and no current WNA16
kernel argument is changed.

The compact lab preflight also gates the entry-args read path itself:

```text
future_kernel_native_consumer_kernel_entry_args_field_read_path =
  kernel_entry_args_to_kernel_arg_packet_to_program_view_rows
future_kernel_native_consumer_kernel_entry_args_packet_chain_depth = 5
future_kernel_native_consumer_kernel_entry_args_summary_row_count =
  future_kernel_native_consumer_kernel_entry_args_summary_row_ok_count
future_kernel_native_consumer_kernel_entry_args_summary_*_read_row_ok_count =
  future_kernel_native_consumer_kernel_entry_args_summary_row_count
future_kernel_native_consumer_kernel_entry_args_summary_error_count = 0
future_kernel_native_consumer_kernel_entry_args_summary_field_mask = 15
```

This makes the default lab preflight reject a future kernel-entry object that
only reports the correct layout but does not actually traverse the packet chain
and read all typed handle fields plus row metadata.

## Next Gates

1. Keep the current readonly dispatch ABI as the default lab preflight
   condition.
2. Keep the pointer-backed program-view and kernel-arg packet ABIs as stricter
   standalone native-consumer bridges.  They model future kernel argument
   objects, but remain outside the current WNA16 fused-MoE launch.
3. Build a real WNA16-adjacent consumer path only by adding an explicit typed
   ABI slot to a future native consumer or standalone adapter. Do not reinterpret
   the typed table as the current WNA16 argument list.
4. Only after that compatible consumer path passes should a single-field live
   handoff canary be considered, default disabled, starting with metadata/scale
   handles rather than payload pointers.
