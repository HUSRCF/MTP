# Premap Typed Consumer Stub

This directory contains a standalone HIP/C++ stub for the future premap native
consumer ABI.  It is not linked into vLLM and does not replace the AWQ WNA16
fused-MoE kernel.

The native path is split into two explicit pieces:

- `premap_typed_consumer_abi_v1.h` defines the struct-of-arrays table ABI.
- `premap_typed_consumer_adapter_v1.h` defines the row-view adapter that a
  future kernel-side consumer would call to load `descriptor_ptr`,
  `packed_weight_descriptor`, `scale_metadata_handle`, and
  `aux_metadata_handle`.
- `PremapKernelSideTypedConsumerLaunchEnvelopeV1` is the explicit canary
  envelope for a future kernel consumer.  It carries the table, expected schema
  hashes, row/order hashes, and readonly flags.  It is only used when the
  `MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE` macro is enabled.
- `PremapFutureKernelSideConsumerArgsV1` is the closer-to-real future kernel
  argument object.  It wraps the launch envelope plus a field mask and
  single-field mirror selector so an independent native stub can consume the
  same argument shape a future kernel slot would receive.  It is still not the
  current WNA16 kernel argument list and is never passed to the real fused-MoE
  kernel.

This separation is deliberate: the adapter is the compatibility point for a
future kernel-side consumer, not an attempt to reinterpret the current WNA16
kernel argument list.

The stub reads a typed descriptor/address table with these row fields:

- `descriptor_ptr`
- `packed_weight_descriptor`
- `scale_metadata_handle`
- `aux_metadata_handle` (optional; zero handles are valid)

Debug behavior is compiled one macro at a time through
`scripts/run_premap_typed_consumer_stub.py --macro ...`. Payload dereference and
kernel-arg passing macros are forbidden for this readonly stub.

The schema-check macro validates the typed consumer schema hash carried in the
table header. The runner injects this hash from the Python runtime schema
constant when compiling the stub:

```text
c1384d55958c9aa78b07b4ee3e9094f835ec1ca4c61bd7e9613c01ceb8275e98
```

Use `--omit-aux-pointer` to exercise the native null-pointer ABI for the
optional `aux_metadata_handle` column.

`MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD` is the
one-field handoff canary. It loads `scale_metadata_handle` through
`PremapKernelSideTypedConsumerRowV1` and compares that row-view value against
the ABI table column for the same row. The check proves the native consumer can
read the scale-metadata mirror through the future typed row ABI, while still
reporting `payload_bytes=0`, `passed_to_kernel=false`, and
`changes_kernel_launch_args=false`.

`MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD`,
`MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD`, and
`MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD` provide the same
one-field mirror check for `descriptor_ptr`, `packed_weight_descriptor`, and
`aux_metadata_handle` respectively. The descriptor pointer mirror compares the
address value only; it still does not dereference payload. Only one mirror macro
may be enabled in a single stub build so each canary remains attributable to a
single field.

`MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH` is the next readonly
compatibility canary. It routes each ABI row through
`premap_typed_consumer_kernel_side_consume_row_v1`, which is the explicit native
adapter entry point a future kernel-side consumer would call.  The check reads
the row-view schema, validates required handles and lifetime metadata, and
emits a path hash. It still reports `payload_bytes=0`,
`passed_to_kernel=false`, and `changes_kernel_launch_args=false`; it is not a
WNA16 kernel argument replacement.

`MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI` is the
table/envelope-level future-kernel canary. It consumes
`PremapKernelSideTypedConsumerLaunchEnvelopeV1` through
`premap_typed_consumer_kernel_side_compatible_consume_row_v1`, validates the
schema, readonly flags, row count/order hashes, and all required handle columns,
and reports `current_wna16_arg_compatible=false`. This is the minimal ABI stub
for a future kernel-side consumer; it still does not reinterpret the typed table
as an existing WNA16 launch argument, dereference payload, or pass anything to
the real fused-MoE kernel.

`MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS` is the current
closest-to-kernel canary. It launches a separate native HIP checker that accepts
`PremapFutureKernelSideConsumerArgsV1` as a future kernel parameter structure
and iterates the typed table through that object. When combined with one
single-field mirror macro, the checker validates that the selected field is
read through the future args object with row parity. The online canary now runs
this future-args path for all four mirror fields: `scale_metadata_handle`,
`descriptor_ptr`, `packed_weight_descriptor`, and `aux_metadata_handle`. The
output continues to require `payload_bytes=0`, `passed_to_kernel=false`,
`changes_kernel_launch_args=false`, and `current_wna16_arg_compatible=false`.

Runtime manager bridge:

```text
PremapKernelArgShadowTableObject.to_native_typed_consumer_input_dict()
```

exports the readonly prepared table into the `--input-json` shape consumed by
this stub. The bridge converts semantic handle tokens into deterministic u64
identities for native validation; it still performs no payload dereference and
does not mutate any vLLM/WNA16 kernel launch arguments.
