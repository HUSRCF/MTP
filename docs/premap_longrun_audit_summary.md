# Premap Long-Run Audit Summary

This document records the tracked, lightweight evidence summary for the
read-only premap descriptor/address handle audit.  The raw `runtime_shadow.jsonl`
and generated `longrun_audit_summary.json/.md` files live under `data/traces/`
and are intentionally ignored because they are large local artifacts.

## Contract

```text
premap-only audit:
  no payload transfer
  no ready credit
  no router mutation
  no descriptor-order execution
  sampled premap_summary rows
  sampled premap_consumer_mapping rows
  read-only descriptor/address prep execution
  no kernel argument mutation
```

## Artifacts

| split | local trace directory | summary artifact |
| --- | --- | --- |
| Dolly 128 | `data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/` | `longrun_audit_summary.json` |
| Dolly 512 | `data/traces/external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit/` | `longrun_audit_summary.json` |

## Results

| metric | Dolly 128 | Dolly 512 |
| --- | ---: | ---: |
| `premap_summary_sample_period` | 32 | 64 |
| `premap_consumer_mapping_sample_period` | 32 | 64 |
| `row_count` | 20,390 | 40,684 |
| `premap_summary_count` | 10,195 | 20,342 |
| `premap_consumer_mapping_count` | 10,195 | 20,342 |
| `outcome_aggregate_count` | 0 | 0 |
| `descriptor_summary_min_count` | 0 | 0 |
| `runtime_shadow_size_mb` | 36.52 | 72.99 |
| `premap_address_resident_count_max` | 10,127 | 10,202 |
| `premap_address_resident_descriptor_bytes_max` | 41,480,192 | 41,787,392 |
| `premap_address_evicted_count` | 0 | 0 |
| `premap_address_eviction_pressure_mean` | 0.0 | 0.0 |
| `premap_address_reuse_rate_mean` | 0.9827389897 | 0.9945098118 |
| `premap_consumer_address_hit_rate` | 1.0 | 1.0 |
| `premap_consumer_descriptor_handle_hit_rate` | 1.0 | 1.0 |
| `premap_consumer_real_descriptor_handle_hit_rate` | 1.0 | 1.0 |
| `premap_consumer_lookup_after_prepare_rate` | 1.0 | 1.0 |
| `premap_consumer_real_descriptor_handle_binding_mismatch_count` | 0 | 0 |
| `premap_consumer_readonly_lookup_count` | 110,898 | 210,849 |
| `premap_consumer_readonly_handle_hit_rate` | 1.0 | 1.0 |
| `premap_consumer_readonly_handle_parity_ok_rate` | 1.0 | 1.0 |
| `premap_consumer_descriptor_prep_attempted_count` | 10,195 | 20,342 |
| `premap_consumer_descriptor_prep_executed_count` | 10,195 | 20,342 |
| `premap_consumer_descriptor_prep_lookup_count` | 110,898 | 210,849 |
| `premap_consumer_descriptor_prep_handle_count` | 110,898 | 210,849 |
| `premap_consumer_descriptor_prep_handle_hit_rate` | 1.0 | 1.0 |
| `premap_consumer_descriptor_prep_real_handle_count` | 110,898 | 210,849 |
| `premap_consumer_descriptor_prep_real_handle_miss_count` | 0 | 0 |
| `premap_consumer_descriptor_prep_real_handle_hit_rate` | 1.0 | 1.0 |
| `premap_consumer_descriptor_prep_real_handle_backed_rate` | 1.0 | 1.0 |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count` | 10,195 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count` | 110,898 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max` | 4 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min` | 4 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count` | 10,195 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count` | 0 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count` | 0 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count` | 110,898 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate` | 1.0 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate` | 1.0 | n/a |
| `premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count` | 0 | n/a |
| `premap_consumer_descriptor_prep_execution_ok_attempted_rate` | 1.0 | 1.0 |
| `premap_consumer_descriptor_prep_blocked_count` | 0 | 0 |
| `premap_consumer_error_count` | 0 | 0 |

## Interpretation

The premap-only long-run audit scales from 128 to 512 samples for the
read-only prelaunch handle/source-class contract, with stable sampled row
volume and no handle/parity failures.  The Dolly128-derived 12,288 capacity
gate remains sufficient for same-source 512 validation: no premap address
evictions are observed, resident descriptor bytes remain modest, and
consumer lookup-after-prepare stays at 1.0.

The 512 artifact predates the kernel-arg shadow table, live-noop integration,
live-consumer-adapter envelope, semantic handle adapter, kernel-side schema
adapter, and typed consumer object.  It is valid scale evidence for premap
address reuse and read-only real-handle parity, but it must not be used as a
strict lab gate for kernel-side consumer integration.  The current lab-default
precondition is the refreshed Dolly128 typed-consumer-object gate:

```text
data/traces/
  external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate_typed_consumer_object_128.json
```

The committed runtime gate YAML keeps its legacy filename:

```text
configs/runtime/
  premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml
```

Its contract and evidence now require the stricter typed-consumer-object
precondition above.

The Dolly128 and Dolly512 rows therefore come from different audit stages; their
premap address/handle counters are comparable, but their kernel-arg/live-adapter
gate fields are not directly comparable.

This is not a payload-prefetch or endpoint-latency claim.  It validates only the
read-only descriptor/address preparation and consumer-handle mapping contract
needed before wiring a real cache-manager consumer.  Descriptor prep execution
here means resolving resident metadata handles into a read-only prep object; it
does not mutate vLLM tensors or kernel arguments.  The refreshed 128-sample gate
also validates a readonly kernel-argument shadow table, launch-schema mirror,
semantic handle adapter, kernel-side consumer schema adapter, and typed consumer
object.  These are table-shape, schema-hash, field-read, and row-parity dry runs
only; they are not a vLLM kernel patch.

## Machine Gate

Use the gate checker before treating a long-run premap audit as valid evidence:

```bash
PYTHONPATH=src:. python scripts/check_premap_longrun_audit_gate.py \
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate_typed_consumer_object_128.json \
  --max-capacity 12288 \
  --min-reuse-rate 0.98 \
  --require-readonly-consumer \
  --require-descriptor-prep \
  --require-real-descriptor-prep \
  --require-kernel-arg-shadow-table \
  --require-consumer-shim-table-read \
  --require-consumer-shim-table-consume \
  --require-consumer-shim-table-object \
  --require-consumer-shim-prep-execution \
  --require-kernel-arg-handoff-attempt \
  --require-kernel-arg-handoff-live-toggle \
  --require-kernel-arg-handoff-launch-schema-mirror \
  --require-kernel-arg-handoff-live-noop-integration \
  --require-kernel-arg-handoff-live-consumer-adapter \
  --require-kernel-arg-semantic-handle-adapter \
  --require-kernel-side-consumer-schema-adapter \
  --require-kernel-side-typed-consumer-object
```

The gate requires:

```text
only premap_summary + premap_consumer_mapping rows
matching sampled row counts
premap payload bytes = 0
address evictions = 0
eviction pressure mean = 0
resident count <= capacity
reuse rate >= threshold
consumer address / descriptor / real-handle hit rates = 1.0
lookup-after-prepare rate = 1.0
binding mismatch count = 0
readonly consumer hit/parity rates = 1.0
descriptor prep attempted = premap_consumer_mapping_count
descriptor prep executed = attempted
descriptor prep handle count = lookup count
descriptor prep handle hit / execution-ok rates = 1.0
descriptor prep missing/block counts = 0
descriptor prep descriptor_ptr / packed_weight / scale_metadata counts = lookup count
descriptor prep real-handle count = lookup count
descriptor prep real-handle miss count = 0
descriptor prep real-handle hit/backed rates = 1.0
kernel arg shadow table executed count = descriptor prep executed count
kernel arg shadow table row count = descriptor prep lookup count
kernel arg shadow table per-row parity count = row count
kernel arg shadow table ok/lifecycle rates = 1.0
kernel arg shadow table payload/ready/router/order/kernel/passed violations = 0
consumer shim table read/consume checked count = premap_consumer_mapping_count
consumer shim table consume row count = descriptor prep lookup count
consumer shim required source hit count = 3 x row count
consumer shim optional source hit + miss count = row count
kernel arg handoff dry-run / shadow-slot / mirror records are ready
kernel arg handoff attempt is blocked by disabled no-op gate
live toggle / live-noop / live-consumer-adapter records are blocked
launch schema mirror hash and field-count match the gate contract
semantic handle adapter hash and field-count match the gate contract
kernel-side consumer schema adapter is present but disconnected
kernel-side typed consumer object is present but disconnected
kernel-side typed consumer object payload/passed/kernel-arg violations = 0
payload / router / descriptor_order / ready-credit violation counts = 0
consumer error count = 0
```

Before treating any runtime YAML as a lab entrypoint, also run the preflight:

```bash
PYTHONPATH=src:. python scripts/run_premap_lab_preflight.py \
  --output-json /tmp/premap_lab_preflight.json
```

The preflight checks that default long-run trace configs still reference the
readonly lab gate, that the typed-consumer-object gate and selfcheck evidence
are `passed=true` with empty `failures`, and that any trace with
live/pass/mutation/single-field handoff flags is explicitly marked as a canary:

```text
premap_risky_trace_canary = true
premap_risky_trace_canary_scope = non-empty string
referenced runtime gate has canary = true and lab_default = false
```

## Live Handoff Canary Modes

The lab default keeps all live kernel-argument handoff paths disabled.  Two
explicit canary modes exist only to validate the next no-op boundary before a
real kernel handoff:

```text
premap_kernel_arg_handoff_live_enabled = true
premap_kernel_arg_handoff_live_consumer_connected = false
```

This validates a live-enabled but disconnected adapter.  The checker must be
called with:

```bash
PYTHONPATH=src:. python scripts/check_premap_longrun_audit_gate.py ... \
  --require-kernel-arg-handoff-live-toggle \
  --require-kernel-arg-handoff-live-noop-integration \
  --require-kernel-arg-handoff-launch-schema-mirror \
  --require-kernel-arg-handoff-live-consumer-adapter \
  --allow-enabled-blocked-live-toggle
```

The next canary connects the prelaunch consumer adapter to the shadow mirror,
but still blocks the actual kernel argument pass:

```text
premap_kernel_arg_handoff_live_enabled = true
premap_kernel_arg_handoff_live_consumer_connected = true
block_reason = kernel_arg_handoff_kernel_arg_pass_disabled
```

Its checker invocation must additionally include:

```bash
  --allow-connected-blocked-consumer-adapter
```

The committed connected-canary gate also records both required `allow_*`
checker flags under `gate.check`; this state is intentionally not the lab
default.

Even in this connected canary, the contract remains no-op:

```text
payload_bytes = 0
ready_credit = false
passed_to_kernel = false
changes_kernel_launch_args = false
```

GPU1 AWQ/vLLM connected-canary smoke:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary.yaml

gate:
  configs/runtime/
    premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_blocked_canary.yaml

run-local copy used for this smoke:
  tmp/live_adapter_connected_canary_smoke/
    trace_live_connected_blocked_consumer_adapter_canary.yaml

artifact:
  /tmp/mtp_connected_adapter_canary_smoke/
    performance_summary.json
    connected_blocked_gate_check.json

committed-config artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary/
      performance_summary.json
      connected_blocked_gate_check.json

passed = true
failures = []

live_noop_integration_checked = 640
live_noop_integration_consumer_connected = 640
live_noop_integration_blocked = 640
live_noop_integration_block_reason =
  kernel_arg_handoff_kernel_arg_pass_disabled
live_noop_integration_payload_bytes = 0
live_noop_integration_passed_to_kernel = 0
live_noop_integration_changes_kernel_launch_args = 0
live_noop_integration_ready_credit = false
live_noop_integration_kernel_arg_violation = 0

live_consumer_adapter_checked = 640
live_consumer_adapter_consumer_connected = 640
live_consumer_adapter_blocked = 640
live_consumer_adapter_block_reason =
  kernel_arg_handoff_kernel_arg_pass_disabled
live_consumer_adapter_payload_bytes = 0
live_consumer_adapter_passed_to_kernel = 0
live_consumer_adapter_changes_kernel_launch_args = 0
live_consumer_adapter_ready_credit = false
live_consumer_adapter_kernel_arg_violation = 0
```

Do not use either canary mode as a runtime-performance or payload-prefetch
claim.  They validate only that the future prelaunch consumer can observe the
prepared handle table and remain safely blocked.

Current local 128 typed-consumer-object lab gate output.  For readability, the
kernel-arg and kernel-side names below omit the common
`premap_consumer_descriptor_prep_consumer_shim_` prefix used in
`performance_summary.json`:

```text
passed = true
max_capacity = 12288
min_reuse_rate = 0.98
row_count = 20390
premap_summary_count = 10195
premap_consumer_mapping_count = 10195
premap_address_resident_count_max = 10127
premap_address_reuse_rate_mean = 0.9827389897
premap_address_eviction_pressure_mean = 0.0
premap_consumer_address_hit_rate = 1.0
premap_consumer_real_descriptor_handle_hit_rate = 1.0
premap_consumer_readonly_lookup_count = 110898
premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_handle_parity_ok_rate = 1.0
premap_consumer_descriptor_prep_attempted_count = 10195
premap_consumer_descriptor_prep_executed_count = 10195
premap_consumer_descriptor_prep_lookup_count = 110898
premap_consumer_descriptor_prep_handle_count = 110898
premap_consumer_descriptor_prep_handle_hit_rate = 1.0
premap_consumer_descriptor_prep_real_handle_count = 110898
premap_consumer_descriptor_prep_real_handle_miss_count = 0
premap_consumer_descriptor_prep_real_handle_hit_rate = 1.0
premap_consumer_descriptor_prep_real_handle_backed_rate = 1.0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count = 10195
premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count = 110898
premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max = 4
premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min = 4
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash = a02928d41970cdf1630dc2a743589ab18068454ac47341a34c4583fd40a5f294
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count = 10195
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count = 0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count = 0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count = 110898
premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate = 1.0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate = 1.0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count = 0
premap_consumer_descriptor_prep_execution_ok_attempted_rate = 1.0
premap_consumer_descriptor_prep_blocked_count = 0
kernel_arg_handoff_dry_run_checked_count = 10195
kernel_arg_handoff_shadow_slot_checked_count = 10195
kernel_arg_handoff_mirror_checked_count = 10195
kernel_arg_handoff_attempt_checked_count = 10195
kernel_arg_handoff_attempt_blocked_count = 10195
kernel_arg_handoff_live_toggle_checked_count = 10195
kernel_arg_handoff_live_toggle_enabled_count = 0
kernel_arg_handoff_live_noop_integration_checked_count = 10195
kernel_arg_handoff_live_noop_integration_consumer_connected_count = 0
kernel_arg_handoff_live_consumer_adapter_checked_count = 10195
kernel_arg_handoff_live_consumer_adapter_consumer_connected_count = 0
kernel_arg_semantic_handle_adapter_checked_count = 10195
kernel_side_consumer_schema_adapter_checked_count = 10195
kernel_side_consumer_schema_adapter_consumer_connected_count = 0
kernel_side_typed_consumer_object_checked_count = 10195
kernel_side_typed_consumer_object_ready_count = 10195
kernel_side_typed_consumer_object_consumer_connected_count = 0
kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args_count = 0
kernel_side_typed_consumer_object_passed_to_kernel_count = 0
kernel_side_typed_consumer_object_kernel_arg_violation_count = 0
```

Current-code strict smoke:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke/
      performance_summary.json
      longrun_audit_gate_live_consumer_adapter.json

performance summary flag:
  runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled = false

checker result:
  passed = true
  failures = []
  live_noop_integration_checked = 640
  live_noop_integration_consumer_connected = 0
  live_noop_integration_blocked = 640
  live_noop_integration_changes_kernel_launch_args = 0
  live_consumer_adapter_checked = 640
  live_consumer_adapter_consumer_connected = 0
  live_consumer_adapter_blocked = 640
  live_consumer_adapter_changes_kernel_launch_args = 0
  live_consumer_adapter_kernel_arg_violation = 0
```

This 8-sample run is only a current-code sanity check for the default-disabled
live-adapter envelope.  The lab-default scale gate remains the refreshed
Dolly128 artifact.
