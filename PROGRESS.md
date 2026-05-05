# MTP Expert Prefetch Progress

## Progress Version

- Version: `v0.7-online-matrix-transition-shadow`
- Updated: 2026-05-05
- Current phase: online matrix_topk transition shadow validation

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

## Novelty / Prior-Art Guard

Independent novelty check result, 2026-05-05:

```text
Do not claim:
  first MoE expert prefetch
  first speculative/draft/MTP-assisted expert prefetch
  new cross-layer expert prediction
  new cache scheduling framework

Closest-overlap areas:
  ProMoE / MoE-Infinity style expert prefetch and offload
  FATE / pre-attention / internal-state expert prediction
  SP-MoE / MoE-SpeQ style speculative or draft-token expert prefetch
  Speculating Experts style representation-based future expert speculation
  SpecMD-style cache policy benchmarks

Safe positioning:
  native MTP signals are evaluated as low-trust future expert-map hints
  true router remains authoritative
  native MTP router/hidden predictors are negative baselines on Qwen3.6-A3B
  MTP token prior is useful only as novel-extra candidate expansion beyond
  a protected same-layer transition baseline
  utility/action admission determines whether hints become full_fetch,
  metadata, premap, or skip
```

Required baselines for paper-level claims:

```text
load-on-demand / no prefetch
LRU / LFU / least-stale cache policies
transition_top32 only
frequency / popularity-only
ProMoE-style learned predictor
FATE-style cross-layer or gate-input predictor
DuoServe-style layer predictor
MTP token-prior / hidden-router-only / full-hidden variants
SP-MoE or MoE-SpeQ-style speculative token baseline under matched budget
oracle next-token experts and oracle queue/lead-time upper bound
utility/action policy ablations
```

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
- vLLM online runtime shadow joins action summaries and true-router outcomes.
- Online `matrix_topk` transition summaries are wired with calibrated transition artifacts.

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

Runtime hardening counters:

```text
join_status:
  joined
  outcome_only
  summary_only_timeout

controller_stats:
  written_summary_count
  joined_outcome_count
  outcome_only_count
  summary_only_timeout_count
  duplicate_summary_count
  duplicate_outcome_count
  evicted_summary_count
  pending_summary_count
```

The pending summary cache is bounded by `max_pending`. Evicted summaries and
summary-only timeouts are explicitly counted, so online shadow replay can
separate policy misses from logging/join failures.

vLLM shadow-only runtime wiring:

```text
trace.runtime_shadow.enabled = true
  creates OnlineShadowLogger + RuntimeShadowController
  passes the controller as VllmRouterRecorder.shadow_outcome_sink
  sets the same controller as the active summary hook during llm.generate(...)
```

Summary-side hook:

```text
write_active_runtime_shadow_action_summary(...)
  no-op when runtime shadow is disabled
  otherwise calls RuntimeShadowController.write_action_summary(...)
```

Recorder-side hook:

```text
VllmRouterRecorder.record_topk(...)
  writes true-router ShadowOutcomeEvent through the same controller
```

This is still shadow-only. It only records JSONL events and does not trigger
prefetch, cache mutation, scheduler mutation, router changes, or logit changes.
Smoke config:

```text
configs/trace/router_mtp_trace_aya_dataset_awq_vllm_shadow_smoke.yaml
```

Smoke run, GPU1 W7900 Dual Slot:

```text
command:
  HIP_VISIBLE_DEVICES=1 python scripts/trace_router_mtp_vllm.py \
    configs/trace/router_mtp_trace_aya_dataset_awq_vllm_shadow_smoke.yaml

outputs:
  data/traces/aya_dataset_smoke_awq_vllm_shadow_smoke/manifest.jsonl
  data/traces/aya_dataset_smoke_awq_vllm_shadow_smoke/runtime_shadow.jsonl

runtime_shadow rows:
  outcomes = 5,080
  summaries = 0
  join_status = outcome_only
```

This validates the recorder-side online outcome path under an actual vLLM run.
Summary-side action decisions are wired through
`write_active_runtime_shadow_action_summary(...)`; they will appear as joined
records once the runtime policy hook calls the summary side during serving.

Transition-only summary producer:

```text
trace.runtime_shadow.emit_transition_summaries = true
  writes transition_only_shadow summaries for token t+1 / same layer
  source = token t true routed top-k from the recorder
  no MTP action policy
  no real prefetch
```

Clean smoke run with `runtime_shadow.overwrite = true`, GPU1:

```text
runtime_shadow rows = 10,120
summary_count = 5,040
outcome_count = 5,080
joined_outcome_count = 5,040
outcome_only_count = 40
summary_only_timeout_count = 0
```

Interpretation:

```text
40 outcome_only rows = token 0 for each of 40 layers
5,040 joined rows = token 1..126 for each of 40 layers
```

This validates online shadow_event_id alignment for previous-token same-layer
summary production. The current summary is intentionally a minimal transition
sanity hook, not the final trained transition_top32 + MTP action policy.

Transition summary modes:

```text
previous_topk:
  copies token t true top-k as token t+1 shadow base
  purpose = event_id / token-offset / layer-offset sentinel

matrix_topk:
  loads transition_matrix [delta, layer, in_expert, out_expert]
  applies previous-token same-layer top-k/weights
  writes top transition candidates as token t+1 shadow base
  purpose = real online transition_topK summary path
```

`previous_topk` remains the offset sentinel. `matrix_topk` is now backed by a
calibrated transition matrix artifact and is the formal online
`transition_topK` summary path.

Calibrated matrix artifact:

```text
path:
  outputs/artifacts/transition_matrix_512sample_calibrated.pt

metadata:
  outputs/artifacts/transition_matrix_512sample_calibrated.json

shape:
  transition_matrix = [1, 40, 256, 256]
  frequency_scores  = [1, 1, 40, 256]

split:
  train samples   = 384
  heldout samples = 128
  train token examples = 35,223

semantics:
  delta=1 means token t -> token t+1 same-layer transition
  previous-token top-k weights are renormalized before matrix lookup
  stable tie-break is score descending, expert_id ascending
```

Matrix smoke config:

```text
configs/trace/router_mtp_trace_aya_dataset_awq_vllm_matrix_shadow_smoke.yaml
```

Smoke run, GPU1 W7900 Dual Slot:

```text
command:
  HIP_VISIBLE_DEVICES=1 python scripts/trace_router_mtp_vllm.py \
    configs/trace/router_mtp_trace_aya_dataset_awq_vllm_matrix_shadow_smoke.yaml

runtime_shadow rows = 10,120
summary_count = 5,040
outcome_count = 5,080
joined_outcome_count = 5,040
outcome_only_count = 40
summary_only_timeout_count = 0
```

Online matrix_top32 smoke metrics on the 1-sample trace:

```text
covered_mass_mean = 0.8515
top1_ready_rate = 0.9384
weighted_top1_miss_mean = 0.01635
```

Interpretation:

```text
token0 outcome_only remains the expected sentinel
token1..126 x 40 layers are joined
matrix_topk has passed the real vLLM online summary/outcome join check
```

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
