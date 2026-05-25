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

The premap-only long-run audit scales from 128 to 512 samples with stable sampled
row volume and no handle/parity failures.  The Dolly128-derived 12,288 capacity
gate remains sufficient for same-source 512 validation: no premap address
evictions are observed, resident descriptor bytes remain modest, and
consumer lookup-after-prepare stays at 1.0.

This is not a payload-prefetch or endpoint-latency claim.  It validates only the
read-only descriptor/address preparation and consumer-handle mapping contract
needed before wiring a real cache-manager consumer.  Descriptor prep execution
here means resolving resident metadata handles into a read-only prep object; it
does not mutate vLLM tensors or kernel arguments.  The refreshed 128-sample gate
also validates a readonly kernel-argument shadow table: this is a table-shape
and row-parity dry run only, not a vLLM kernel patch.

## Machine Gate

Use the gate checker before treating a long-run premap audit as valid evidence:

```bash
python scripts/check_premap_longrun_audit_gate.py \
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_summary.json \
  --max-capacity 12288 \
  --min-reuse-rate 0.98 \
  --require-readonly-consumer \
  --require-descriptor-prep \
  --require-real-descriptor-prep \
  --require-kernel-arg-shadow-table
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
payload / router / descriptor_order / ready-credit violation counts = 0
consumer error count = 0
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
python scripts/check_premap_longrun_audit_gate.py ... \
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

Even in this connected canary, the contract remains no-op:

```text
payload_bytes = 0
ready_credit = false
passed_to_kernel = false
changes_kernel_launch_args = false
```

Do not use either canary mode as a runtime-performance or payload-prefetch
claim.  They validate only that the future prelaunch consumer can observe the
prepared handle table and remain safely blocked.

Current local 128 kernel-arg-shadow-table gate output:

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
```
