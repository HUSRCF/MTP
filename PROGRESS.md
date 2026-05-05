# MTP Expert Prefetch Progress

## Progress Version

- Version: `v0.6-runtime-shadow-replay`
- Updated: 2026-05-05
- Current phase: 512-sample scale-up validation for action-level runtime policy

## Runtime Policy Contract

The current runtime MVP policy is:

```text
transition_top32 protected base
+ full_fetch: up to MTP_extra4, utility gate
+ metadata: up to MTP_extra1, raw-score high-tail, high-overlap/idle only
+ premap: independent tiny descriptor budget
+ skip: default fallback
```

Safety boundaries:

- True router remains authoritative.
- Predictions never change logits or executed routed experts.
- Only `full_fetch` enters ready-before-demand and stall proxy.
- `metadata` and `premap` are setup-preparation actions only.
- MTP extras must be novel additions and cannot replace `transition_top32`.

## Passed Gates

- vLLM router recorder labels are trusted.
- Same-token router hidden oracle passed.
- MTP token path alignment passed after `prefc` concat fix.
- Native MTP router-only predictor is frozen as a negative baseline.
- MTP-token prior is promoted only as extra-budget candidate expansion.
- Utility-gated `full_fetch` beats fixed extraK on issued-byte efficiency.
- Action-level counters report `full_fetch` / `metadata` / `premap` / `skip`.
- Metadata and premap are tracked with separate setup-prep accounting.
- Transfer-capacity fallback gate is implemented in runtime policy.
- Runtime shadow schema records gate outcome and policy overhead fields.
- Runtime shadow replay exporter writes action-level summary/outcome JSONL from tensor caches.

## Current Scale-Up

512-sample configs are committed in:

- `configs/data/aya_dataset_512.yaml`
- `configs/trace/router_mtp_trace_aya_dataset_autoround_512sample.yaml`
- `configs/trace/router_mtp_trace_aya_dataset_awq_vllm_512sample.yaml`
- `configs/eval/prefetch_shadow_512sample_mtp_extra.yaml`

Active chain:

1. AutoRound 512 trace on GPU0.
2. vLLM AWQ router-recorder 512 trace on GPU1.
3. Merge AutoRound MTP and vLLM router labels.
4. Rebuild fixed MTP token top-M sidecar.
5. Run 512-sample tensor-cache event/action validation.
6. Sweep broader bandwidth / layer-time / MTP-delay envelope.

## Primary 512 Validation Questions

- Does `transition_top32 + up to MTP_extra4 + utility gate` keep its Pareto advantage?
- Do action-level later-used rates preserve ordering: `full_fetch > metadata > premap`?
- Does metadata max1 remain high-overlap/opportunistic rather than default-expanded?
- Does premap remain positive only as tiny/idle descriptor prep?
- Are 512-scale results consistent with 256-sample conclusions?

## Latest 512-Sample Results

Artifacts:

- Tensor cache: `outputs/reports/prefetch_shadow_512sample_mtp_extra/event_stall_tensor_cache_512sample.pt`
- Baseline action report: `outputs/reports/prefetch_shadow_512sample_mtp_extra/event_stall_action_policy_512_baseline.json`
- Normal Pareto report: `outputs/reports/prefetch_shadow_512sample_mtp_extra/event_stall_action_pareto_512_normal.json`
- Stress report: `outputs/reports/prefetch_shadow_512sample_mtp_extra/event_stall_action_stress_512_bw2_layer025_delay8.json`
- Compact summary: `outputs/reports/prefetch_shadow_512sample_mtp_extra/action_sweep_512_compact.md`

Normal envelope (`6.589 GB/s`, `1.0 ms/layer`, `2.0 ms MTP delay`, `cap160`):

```text
transition@32: ready_mass=0.8006, top1=0.9065, weighted_miss=0.0224
fixed extra4: ready_mass=0.8245, top1=0.9234, stall_reduction=10.69%
fixed extra8: ready_mass=0.8362, top1=0.9293, stall_reduction=16.33%
score keep50: ready_mass=0.8174, top1=0.9199, stall_reduction=7.10%
utility keep50: ready_mass=0.8184, top1=0.9206, stall_reduction=7.61%
```

Normal-envelope action results:

```text
utility keep50 metadata later-used = 12183
utility keep50 premap later-used   = 21299
score keep50 metadata later-used   = 8734
score keep50 premap later-used     = 20631
```

Stress envelope (`2 GB/s`, `0.25 ms/layer`, `8.0 ms MTP delay`, `cap160`):

```text
transition@32: ready_mass=0.5485, top1=0.7069, weighted_miss=0.0713
MTP extra ready fraction = 0.0
fixed/gated MTP full-fetch stall reduction = 0.0
```

Interpretation:

- 512-sample normal-envelope results are consistent with and stronger than the 256-sample direction.
- Utility-gated full-fetch remains the best default gate among score/utility gates.
- Fixed extra4/extra8 remain aggressive upper baselines, not default runtime behavior.
- In the severe transfer-insufficient regime, MTP full-fetch correctly has no ready-before-demand value; runtime should fall back to transition-only plus optional metadata/premap shadow/prep.

## Runtime Fallback Gate

The runtime policy now explicitly disables MTP `full_fetch` when any primary
capacity gate fails:

```text
transition_ready_rate < 0.90
=> fallback reason: transition_not_ready

mtp_ready_fraction < 0.05
=> fallback reason: mtp_not_ready

bandwidth_gbps * layer_ms < 2.0
=> fallback reason: transfer_envelope_tight
```

Fallback behavior:

```text
full_fetch max_extra = 0
metadata max_extra = 0
allow_full_mtp_fetch = false
allow_mtp_metadata = false
allow_mtp_premap = true
```

This maps the 512-sample severe stress result into a concrete runtime gate:
when MTP extras cannot become ready before demand, full expert prefetch is
disabled rather than adding transfer pressure.

## Runtime Shadow Logging

Shadow summary events now carry policy and overhead fields needed for online
shadow validation:

```text
policy_reason
allow_full_mtp_fetch
allow_mtp_metadata
allow_mtp_premap
transition_ready_rate
mtp_ready_fraction
bandwidth_gbps
layer_ms
candidate_construction_us
admission_decision_us
counter_update_us
logging_us
```

These fields are intended to support the next gate:

```text
offline event sim ≈ online shadow replay
```

## Runtime Shadow Replay

The runtime shadow contract can now be exported as JSONL from cached evaluation
tensors:

```text
scripts/export_runtime_shadow_jsonl.py
```

The exporter uses the same runtime policy fallback gate and canonical admission
helpers as the simulator, then writes per-token/layer:

```text
summary event:
  policy mode / reason / allow flags
  full_fetch / metadata / premap / skip counts and bytes
  transfer envelope fields

outcome event:
  true routed top-k ids/weights
  full_fetch used
  metadata later-used
  premap later-used
  skip would-have-used
  ready mass / miss mass / weighted top1 miss
```

Smoke checks:

```text
normal envelope:
  policy_mode = default
  full_fetch / metadata / premap all active

severe stress envelope:
  policy_mode = fallback
  full_fetch = 0
  metadata = 0
  premap remains allowed
```

This is the bridge for the next validation gate:

```text
offline event sim ≈ runtime shadow JSONL replay
```

512-sample summary-only replay:

```text
normal envelope, GPU1:
  policy_mode = default
  ready_mass = 0.8187
  top1_ready = 0.9207
  weighted_top1_miss = 0.0192
  full_fetch_count = 900,460
  metadata_count = 170,805
  premap_count = 455,400
  action_admission_overhead = 0.094 us/token-layer
  aggregate_counter_overhead = 0.448 us/token-layer
  total_shadow_decision_overhead = 0.542 us/token-layer

severe stress envelope, GPU1:
  policy_mode = fallback
  reason = transition_not_ready
  full_fetch_count = 0
  metadata_count = 0
  premap_count = 455,400
  ready_mass = 0.8006
  top1_ready = 0.9066
  weighted_top1_miss = 0.0224
```

The full JSONL path is intended for small debug samples. Scale validation should
use `--summary-only`, which aggregates the same action/outcome semantics with
vectorized tensors and avoids multi-hundred-MB partial logs.

Online runtime logging bridge:

```text
OnlineShadowLogger
  writes the same summary/outcome JSONL schema from a serving/runtime path
  after action decision and true-router outcome are available

check_shadow_replay_consistency.py
  compares online/offline shadow aggregates against event-sim policies
```

Consistency checks:

```text
normal envelope:
  metric_group = all
  result = pass
  ready/action counters align with event sim within rtol=0.002

severe stress envelope:
  metric_group = ready
  result = pass
  action counters intentionally differ because runtime fallback suppresses
  MTP full_fetch/metadata while the event sim stress report still records
  requested-but-late actions.
```

vLLM recorder hook:

```text
VllmRouterRecorder.shadow_outcome_sink
  optional, default None
  writes true-router ShadowOutcomeEvent skeletons per token/layer
  does not make action decisions
  does not modify routing, logits, scheduling, cache, or prefetch behavior
```

This is the first shadow-only runtime hook point. A complete online integration
still needs the action-decision side to write matching `ShadowSummaryEvent`
records before true-router outcomes are joined.

Action summary adapter:

```text
build_shadow_summary_from_decisions(...)
OnlineShadowLogger.write_action_summary(...)
```

The adapter converts canonical `AdmissionDecisionMasks` into a
`ShadowSummaryEvent` with:

```text
full_fetch / metadata / premap / skip counts
action bytes
reason_counts
action_reason_counts
policy envelope fields
overhead fields
```

Offline shadow replay now uses the same adapter for small JSONL summary events,
so future online summary hooks and offline replay share one summary-construction
path.

Joined online shadow controller:

```text
RuntimeShadowController
  writes action summaries through OnlineShadowLogger.write_action_summary(...)
  caches action masks by shadow_event_id
  implements the vLLM recorder outcome sink protocol
  enriches true-router outcomes with later-used / ready metrics
```

The controller is still shadow-only:

```text
no real prefetch
no cache mutation
no scheduler mutation
no router/logit changes
```

Outcome join semantics:

```text
summary side:
  stores full_fetch / metadata / premap / skip masks
  optionally stores queue/cache-aware ready_mask

outcome side:
  joins by request_id:sequence_id:token_index:layer
  full_fetch_used_count = full_fetch action ∩ true_topk
  metadata_later_used_count = metadata action ∩ true_topk
  premap_later_used_count = premap action ∩ true_topk
  skip_would_have_used_count = skip action ∩ true_topk
  covered_mass / top1_ready come only from ready_mask
```

If no matching summary is pending, the controller writes the recorder's
outcome-only skeleton unchanged. This keeps outcome-only vLLM logging safe while
allowing full action/outcome joining when both sides are wired.

## Current Default Evaluation Settings

```text
transition_topk = 32
mtp_topk = 64
default full_fetch max_extra = 4
high-budget max_extra = 8
metadata max_extra = 1
metadata score ratio = 0.95
premap max_extra = 1
admission capacity per layer = 160
calibrated H2D bandwidth = 6.589 GB/s
layer time = 1.0 ms
MTP delay = 2.0 ms
action cost overlap = 0.90
```
