# Premap Typed Consumer Stub

This directory contains a standalone HIP/C++ stub for the future premap native
consumer ABI.  It is not linked into vLLM and does not replace the AWQ WNA16
fused-MoE kernel.

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

Runtime manager bridge:

```text
PremapKernelArgShadowTableObject.to_native_typed_consumer_input_dict()
```

exports the readonly prepared table into the `--input-json` shape consumed by
this stub. The bridge converts semantic handle tokens into deterministic u64
identities for native validation; it still performs no payload dereference and
does not mutate any vLLM/WNA16 kernel launch arguments.
