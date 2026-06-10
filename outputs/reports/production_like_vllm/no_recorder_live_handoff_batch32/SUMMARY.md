# No-Recorder Live Handoff Batch32 Smoke

Date: 2026-06-11

Scope:
- Model: Qwen3.6-35B-A3B AWQ 4-bit
- GPU: GPU1 W7900
- Split: Dolly 32 samples, gen64
- Path: true vLLM batched `llm.generate([...])`, router recorder off, runtime shadow off

## Result

| mode | repeats | mean generate_s | median generate_s | mean aggregate tok/s | median aggregate tok/s |
|---|---:|---:|---:|---:|---:|
| `production_batch` | 3 | 7.284 | 7.279 | 281.18 | 281.37 |
| `production_batch_premap_live_future_wna16_typed_slot_envelope_counter_off` | 3 | 7.230 | 7.238 | 283.26 | 282.97 |

Mean throughput delta: `+0.74%`.

Median throughput delta: `+0.57%`.

## Semantic Counter Smoke

`production_batch_premap_live_future_wna16_typed_slot_envelope_detailed` ran on the same 32-sample split with no router recorder and no runtime shadow.

Nonzero live counters:

```text
package_seen_count = 5120
package_pass_through_count = 5120
package_producer_future_wna16_typed_slot_envelope_count = 2560
single_field_replacement_live_passed_to_kernel_count = 5120
```

This proves the no-recorder live package is constructed and consumed in the WNA16 wrapper path.

## Boundary

This is a production-compatible positive signal for the pass-through live envelope boundary.

It is not yet evidence that prepared descriptor/address handles improve WNA16 latency, because the current benchmark still passes original WNA16 compute arguments through the typed-slot envelope.

## Artifacts

- Repeat-3 A/B:
  `outputs/reports/awq_telemetry_ladder/gpu1_production_batch_live_envelope_repeat3_20260611/`
- Detailed counter smoke:
  `outputs/reports/awq_telemetry_ladder/gpu1_production_batch_live_envelope_detailed_smoke32_20260611/`
