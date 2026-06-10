# No-Recorder Prepared-Table Batch32 Boundary

Date: 2026-06-11

Scope:

```text
GPU1 AWQ/Dolly 32-sample gen64
batch32 vLLM path
runtime_shadow.enabled = false
router recorder = false
record_topk = false
```

## Results

Pass-through future typed-slot envelope:

```text
output root:
outputs/reports/awq_telemetry_ladder/
  gpu1_production_batch_live_envelope_repeat3_20260611/

production_batch mean generate_s:
  7.283710

production_batch_premap_live_future_wna16_typed_slot_envelope_counter_off
mean generate_s:
  7.230100

mean aggregate throughput:
  production_batch = 281.18 tok/s
  live envelope    = 283.26 tok/s

mean throughput delta:
  +0.74%
```

Prepared table with independent future typed-slot kernel canary:

```text
output root:
outputs/reports/awq_telemetry_ladder/
  gpu1_production_batch_prepared_typed_slot_smoke32_20260611/

production_batch:
  generate_s = 7.244
  TPOT = 0.003537

production_batch_premap_live_future_wna16_typed_slot_kernel_variant_counter_off:
  generate_s = 165.188
  TPOT = 0.080658

production_batch_premap_live_future_wna16_typed_slot_kernel_variant_detailed:
  generate_s = 164.019
  TPOT = 0.080087
  future_typed_slot_kernel_variant_launch_count = 5120
  wrapper_prepared_columns_hit_count = 5120
  producer_materialization_count = 2560
  native_row_fill_row_count = 302583
```

Prepared table with original WNA16 alias adapter:

```text
output root:
outputs/reports/awq_telemetry_ladder/
  gpu1_production_batch_prepared_alias_smoke32_20260611/

production_batch:
  generate_s = 7.266
  TPOT = 0.003548

production_batch_premap_live_prepared_alias_adapter_counter_off:
  generate_s = 158.451
  TPOT = 0.077368

production_batch_premap_live_prepared_alias_adapter_detailed:
  generate_s = 159.730
  TPOT = 0.077993
  package_pass_through_count = 5120
  prepared_table_hit_count = 5120
  single_field_live_passed_to_kernel_count = 5120
```

Prelaunch mapping/address-manager attribution only:

```text
output root:
outputs/reports/awq_telemetry_ladder/
  gpu1_production_batch_mapping_only_retry3_20260611/

same-environment production_batch baseline:
  output root:
  outputs/reports/awq_telemetry_ladder/
    gpu1_production_batch_baseline_for_mapping_only_20260611/
  generate_s = 7.219
  TPOT = 0.003525

production_batch_premap_prelaunch_mapping_only_counter_off:
  generate_s = 41.961
  TPOT = 0.020489
  runtime_shadow.enabled = false
  router recorder = false
  consumer mapping rows = false
  real handles = false
  descriptor prep = off
  live kernel-arg handoff = false

slowdown vs same-environment production_batch:
  5.81x
```

## Interpretation

```text
The pass-through typed-slot envelope can participate in the true no-recorder
batch path and remains close to production_batch.

Prepared-table paths are not production-compatible yet.  The prepared alias
adapter still calls the original optimized WNA16 kernel, but it is about as slow
as the independent future typed-slot kernel canary.  Therefore the dominant
cost is before the WNA16 compute kernel:

- CPU extraction of expert_ids / num_tokens_post_padded
- address-manager lookup
- real-handle resolution
- semantic prepared row construction
- typed-column staging / row fill

The mapping-only attribution run shows that even before real-handle resolution
or table staging, re-entering Python prelaunch expert extraction and
address-manager mapping is already not production-compatible.

The next implementation gate is not another WNA16 kernel variant.  The
prepared-table construction and typed-slot staging must move into a lower-level
producer/native adapter that avoids per-launch Python participation, or the
table content must be produced and retained before per-launch WNA16 invocation.
```
