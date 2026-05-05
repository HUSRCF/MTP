# Differentiation And Moat Analysis

This document frames **Tick-Tock Residency with Native MTP Hints** from a strict
reviewer perspective. The goal is to avoid overclaiming in the crowded MoE
prefetch/offloading literature while preserving the real system moat.

## 1. Core Differentiation Table

| Work type | Representative work | Prediction source / cost | Routing authority | Scheduling abstraction | Our differentiation |
| --- | --- | --- | --- | --- | --- |
| External predictor / trace predictor | ProMoE, DuoServe-style systems | Learned predictors over activations or offline traces; nontrivial predictor path | Often used as a high-trust predictor for likely expert usage | Prefetch/cache experts before demand | We do not try to replace the router or learn the whole expert map. `transition_top32` is the protected online base; native MTP is treated as a low-trust semantic hint that may only append novel experts. |
| Cross-layer / hidden-state expert prediction | FATE, cross-layer gate, pre-attention predictors | Neighbor-layer hidden/gate inputs; medium online cost | Medium trust; can influence cache/prefetch aggressively | Layer-wise prefetch and shallow-favoring cache | Our negative result matters: native MTP router/hidden predictors are not promoted. The useful signal is MTP predicted-token prior as semantic novelty beyond transition, not a hidden-state full-space generator. |
| Speculative decoding / draft-model expert prefetch | SP-MoE, MoE-SpeQ-like designs | Draft model, speculative tree, or future-token path | High trust in speculative branch; often tied to verification scheduling | Runtime governor over speculative expert set | Native MTP is never allowed to route or execute experts. It only produces prefetch/premap hints; true router remains authoritative. A miss only wastes or downgrades preparation work, not model correctness. |
| Traditional expert cache/offload | MoE-Infinity, SpecMD-style policies | Frequency, recency, local statistics, future-info baselines | Router decides; cache is reactive | Page/cache residency and eviction | We add an online low-trust semantic novelty source and an action-level admission contract: `full_fetch`, `metadata`, `premap`, or `skip`. The value is not just cache hit rate, but ready-before-demand utility per issued byte. |
| Static graph compiler | MIGraphX / TensorRT-like compilation | No token-level route predictor; compiler optimizes stable graph | Not intended for per-token dynamic routing patch | AOT or compile-time graph lowering | We avoid putting token-level MoE route patching in a graph compiler hot path. The intended system path is HIP Graph replay plus fixed-size descriptor buffers. |

## 2. Core Moat A: RSEP Decomposition

### Reviewer-safe claim

The useful MTP signal is not "MTP predicts expert routing." Our current results
support a narrower decomposition:

```text
future expert demand ~= transition inertia union semantic novelty
```

where:

```text
transition inertia:
  previous-token same-layer transition_top32
  strong online baseline
  protected base pool

semantic novelty:
  native MTP predicted-token prior
  only admits novel experts not already in transition_top32
  filtered by utility/action gate
```

### What not to claim

Do not claim that native MTP hidden states or native MTP router outputs are
accurate future expert generators. They were tested and frozen as negative
baselines. The useful signal is the token-prior path, not direct MTP router
top-k prediction.

### Current empirical boundary

The runtime policy should be written as:

```text
transition_top32 protected base
+ full_fetch: up to MTP_extra4 through utility gate
+ metadata: max1 raw-score high-tail under high-overlap / idle window
+ premap: max1 tiny idle descriptor preparation
+ fallback: transition-only when transfer capacity is insufficient
```

This is a low-trust, action-level use of MTP hints.

## 3. Core Moat B: Tick-Tock Action Admission

The system-level contribution is not simply "more prefetch candidates." The
claim should be about controlled action admission under a transfer deadline.

```text
Tick:
  before true demand, form protected transition candidates and optional MTP
  semantic extras.

Tock:
  when true router results arrive, count which preparation actions were useful
  and perform supplemental fetch only for true misses.
```

Action semantics are intentionally separated:

```text
full_fetch:
  may count as ready-before-demand if completed
  primary stall-reduction action

metadata:
  never counts as ready expert weights
  only reduces future setup latency if later used
  should be high-score and high-overlap only

premap:
  never counts as ready expert weights
  descriptor/address preparation only
  should be idle/tiny-budget controlled, not primarily score-driven

skip:
  default for low-utility or unsafe candidates
```

This structure is a "blast-radius" control: prediction errors cannot change
executed experts or logits.

## 4. Core Moat C: Topology-Static, Metadata-Dynamic Dispatch

This is the deepest systems hypothesis and should be described carefully.

### Motivation

For large-batch or long prefill MoE, the active expert set can approach the full
expert set. In that regime, predicting a small absolute subset of experts is not
the main problem. The remaining bottleneck may shift toward:

```text
dynamic dispatch metadata construction
token sorting / offsets
pointer or descriptor preparation
host-side launch overhead
queue timing under PCIe / ROCm
```

### Safe academic claim

```text
We use low-trust MTP hints to pre-materialize a topology-static dispatch
skeleton. Prediction errors do not invalidate the graph; they only increase
metadata patching or overwrite work. The true router remains authoritative, and
the system falls back to full metadata overwrite or eager dispatch when patching
is not profitable.
```

### Intended execution abstraction

The graph topology stays fixed. Dynamic MoE state is represented by fixed-size
metadata buffers:

```text
token_counts[num_experts]
expert_offsets[num_experts]
expert pointer / descriptor arrays
sorted token indices
workspace pointers
optional node enable masks
```

Inactive experts use zero counts rather than changing graph topology.

The execution flow is:

```text
Tick:
  transition + MTP estimate hot expert distribution
  pre-allocate workspace
  optionally pre-fill descriptor buffers
  optionally bind stable graph nodes to descriptor buffers

Tock:
  true router produces authoritative metadata
  compare speculative metadata against true metadata

small delta:
  patch descriptor buffer
  hipGraphLaunch

large delta:
  overwrite full descriptor buffer
  hipGraphLaunch or eager fallback
```

### Important correction

Do not claim `O(missing experts)`. A route miss may change many token-expert
assignments even if the active expert set barely changes.

Use:

```text
O(delta metadata)
```

where delta metadata includes changed expert counts, offsets, sorted indices,
and token-expert assignments.

## 5. ROCm / HIP Graph Boundary

### Do not put token-level routing patching in MIGraphX

MIGraphX is a graph compiler / inference engine. It is appropriate for stable
subgraphs or ahead-of-time graph lowering, not per-token MoE route patching in a
microsecond-scale hot path.

### Intended hot path

```text
HIP Graph:
  replay a fixed dispatch skeleton
  reduce CPU launch overhead
  optionally update node params or point nodes at stable descriptor buffers

Descriptor buffer:
  carries dynamic MoE metadata
  can be patched or overwritten without graph recapture

Custom HIP / CK / Triton grouped MoE kernels:
  consume token counts, offsets, and sorted token indices
```

The most robust design is to keep HIP Graph node parameters stable and put
dynamic state behind descriptor buffers. This reduces dependence on expensive or
beta graph-update APIs.

## 6. Microbenchmark Plan And Break-Even Gate

This systems claim must be validated by microbenchmarks before it becomes a
paper-level contribution.

### Required microbenchmarks

```text
1. eager dummy grouped-MoE dispatch latency
2. HIP graph launch latency
3. descriptor buffer overwrite + graph launch latency
4. hipGraphExecNodeSetParams cost
5. hipGraphNodeSetEnabled cost
6. hipGraphExecUpdate cost
7. speculative metadata patch vs full metadata overwrite penalty
8. optional overlap with compute stream and H2D metadata copies
```

### Break-even equation

Define:

```text
saved_us = eager_dispatch_us - graph_launch_us

cost_patch =
  validation_us
  + speculative_patch_us
  + (1 - partial_hit_rate) * miss_overwrite_us
```

The skeleton path is profitable only if:

```text
cost_patch < saved_us
```

or, with action costs:

```text
net_gain_us =
  saved_dispatch_us
  + saved_setup_us
  - validation_us
  - patch_us
  - overwrite_penalty_us
  - extra_metadata_copy_us
```

The paper should report the measured break-even region rather than assume graph
patching is always profitable.

## 7. Claim Boundaries

### Safe claims

```text
Native MTP hints are useful only as low-trust semantic novelty signals.
The transition baseline remains protected and authoritative as the base pool.
True router remains authoritative for expert execution.
Prediction errors cannot change logits or routed expert execution.
The action policy converts hints into full_fetch / metadata / premap / skip.
Topology-static dispatch can make route misses metadata work rather than graph
recompile work, subject to microbenchmarked break-even.
```

### Unsafe claims

```text
First MoE expert prefetch system.
First speculative/MTP expert prefetch system.
MTP directly predicts expert routing accurately.
MTP replaces the router.
Miss cost is O(missing experts).
Zero-overhead dispatch without microbench evidence.
MIGraphX can patch token-level MoE routes in the hot path.
```

## 8. Required Baselines For Paper Claims

The prior-art risk is high. At minimum, paper claims need:

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
oracle next-token experts
oracle queue / lead-time upper bound
utility/action policy ablations
HIP Graph metadata patch microbenchmarks
```

## 9. Recommended Paper Positioning

The strongest positioning is:

```text
We do not propose a new router.
We do not trust MTP enough to execute predicted experts.
Instead, we characterize native MTP as a low-trust future expert-map hint and
show how to safely exploit only the residual semantic novelty beyond a strong
transition baseline.

At runtime, hints are admitted into action levels with explicit cost and
deadline semantics. A separate topology-static dispatch skeleton study evaluates
whether the same hints can reduce metadata and dispatch overhead without ever
requiring graph recompilation or changing model outputs.
```

