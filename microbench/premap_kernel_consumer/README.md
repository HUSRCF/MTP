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
table header:

```text
c1384d55958c9aa78b07b4ee3e9094f835ec1ca4c61bd7e9613c01ceb8275e98
```
