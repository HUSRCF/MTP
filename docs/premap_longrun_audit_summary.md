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
| `premap_consumer_error_count` | 0 | 0 |

## Interpretation

The premap-only long-run audit scales from 128 to 512 samples with stable sampled
row volume and no handle/parity failures.  The Dolly128-derived 12,288 capacity
gate remains sufficient for same-source 512 validation: no premap address
evictions are observed, resident descriptor bytes remain modest, and
consumer lookup-after-prepare stays at 1.0.

This is not a payload-prefetch or endpoint-latency claim.  It validates only the
read-only descriptor/address preparation and consumer-handle mapping contract
needed before wiring a real cache-manager consumer.

## Machine Gate

Use the gate checker before treating a long-run premap audit as valid evidence:

```bash
python scripts/check_premap_longrun_audit_gate.py \
  data/traces/external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_summary.json
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
consumer error count = 0
```

Current local 512 gate output:

```text
passed = true
max_capacity = 12288
min_reuse_rate = 0.98
row_count = 40684
premap_summary_count = 20342
premap_consumer_mapping_count = 20342
premap_address_resident_count_max = 10202
premap_address_reuse_rate_mean = 0.9945098118
premap_address_eviction_pressure_mean = 0.0
premap_consumer_address_hit_rate = 1.0
premap_consumer_real_descriptor_handle_hit_rate = 1.0
```
