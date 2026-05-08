# MTP Expert Prefetch Progress

## Progress Version

- Version: `v0.11-rocprof-fallback`
- Updated: 2026-05-06
- Current phase: online action shadow validated; pivoting system moat to speculative LDS tile staging

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
  the primary systems claim should move below expert prefetch / metadata
  rebuild: MTP/transition hints are used as speculative tile-staging priorities
  inside a graph-stable grouped-GEMM path
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
- Heldout online `matrix_topk` replay matches offline transition@32 baseline.
- Full MTP action replay matches the normal-envelope event simulator.
- Reviewer-safe differentiation has been tightened around LDS-level tile staging rather than broad expert prefetch.
- W7900 / RDNA3 rocWMMA hello-world smoke passes on both local gfx1100 cards.

## Micro-Architectural Direction

The current strongest originality claim is:

```text
Patchability-aware speculative LDS tile staging for exact MoE dispatch.
```

Interpretation:

```text
MTP is not a router.
MTP is not a trusted full-expert prefetcher.
MTP is a low-trust hint for ordering or staging the first grouped-GEMM tiles.
```

Important hardware boundary:

```text
LDS cannot be written by the CPU and does not persist across kernels.
Speculative LDS staging must happen inside a fused / persistent grouped-MoE
kernel or inside a graph-stable grouped-GEMM prologue that pulls descriptor/tile
state from global memory into LDS before the true commit point.
```

Proposed execution semantics:

```text
Tick:
  transition + MTP estimate hot expert/tile priorities
  grouped-GEMM prologue speculatively stages selected tile descriptors or
  first tiles in LDS

Tock:
  true router publishes authoritative metadata
  hit: consume staged LDS tile state
  miss: invalidate / overwrite LDS state and load true tile from HBM
```

This avoids overclaiming against FlashMoE / MetaShuffling / fused-MoE systems:
they already rebuild routing metadata on GPU. The differentiated question is
whether low-trust native MTP hints can profitably act below that layer, as
micro-architectural tile-stage priorities with bounded miss cost.

## LDS Tile-Staging Microbench Skeleton

Implemented P0 skeleton:

- `microbench/lds_tile_staging/lds_tile_staging_bench.hip`
- `scripts/run_lds_tile_staging_bench.py`
- `microbench/lds_tile_staging/README.md`

The benchmark is intentionally hand-written HIP rather than rocWMMA/CK. The
reason is measurement isolation: P0 needs to expose LDS bytes, staged tile
latency, validation wait, miss overwrite cost, and first-FMA timing before
integrating with a real grouped-GEMM pipeline.

Measured modes:

```text
reactive:
  wait for true metadata, then load true tile HBM -> LDS

oracle:
  stage the correct tile before validation

spec_hit:
  stage predicted tile, validate as correct

spec_miss:
  stage predicted tile, validate as wrong, overwrite LDS with true tile

mixed:
  controlled hit/miss blend
```

Default smoke config:

```text
requests=4096
experts=256
tile_elems=1024  # 4KB tile
block_threads=256
validate_iters=256
iters=100
miss_rate=0.25
```

Reports:

- GPU0 W7900: `outputs/reports/lds_tile_staging/default_gpu0.json`
- GPU1 W7900 Dual Slot: `outputs/reports/lds_tile_staging/default_gpu1.json`

Key default-smoke result:

```text
GPU0 mixed 25% miss:
  overlap_model_speedup_vs_reactive ~= 1.32x
  overlap_model_delta_vs_reactive   ~= -4431 cycles

GPU0 spec_hit:
  overlap_model_speedup_vs_reactive ~= 1.37x

GPU0 spec_miss:
  overlap_model_speedup_vs_reactive ~= 1.20x
  overwrite_cycles_p50_miss         ~= 1413 cycles

GPU1 mixed 25% miss:
  overlap_model_speedup_vs_reactive ~= 1.32x

GPU1 spec_miss:
  overlap_model_speedup_vs_reactive ~= 1.21x
```

Interpretation:

- The raw single-kernel first-FMA timing is mostly serial and should not be
  overinterpreted as true router/staging overlap.
- The benchmark therefore reports an explicit overlap model:
  `reactive = wait + true_load`, `hit = max(wait, stage)`,
  `miss = max(wait, stage) + overwrite`.
- Under that model, LDS miss overwrite remains small relative to the hidden
  staging window, which supports the premise that the miss blast radius is much
  smaller than HBM-level expert prefetch.

Next LDS microbench gates:

```text
1. sweep tile_elems, validate_iters, block_threads, and miss_rate
2. add router-interference mode that runs a competing metadata/router-like kernel
3. add rocWMMA grouped-GEMM variant for RDNA3 W7900 if the isolated prologue envelope remains positive
4. compare against a reactive grouped-GEMM mock with real WMMA-like / rocWMMA work
```

Completed sweep scripts:

- `scripts/sweep_lds_tile_staging.py`

Default two-GPU break-even sweep:

- Report: `outputs/reports/lds_tile_staging/sweep_default_2gpu.json`
- CSV: `outputs/reports/lds_tile_staging/sweep_default_2gpu.csv`
- Markdown: `outputs/reports/lds_tile_staging/sweep_default_2gpu.md`
- Plot: `outputs/reports/lds_tile_staging/sweep_default_2gpu.png`

Default grid:

```text
tile_elems = [256, 512, 1024, 2048]
validate_iters = [0, 64, 256, 1024]
miss_rate = [0.0, 0.1, 0.25, 0.5, 1.0]
block_threads = [128, 256]
devices = [GPU0, GPU1]
```

Default sweep summary:

```text
oracle:
  positive rows = 160 / 160
  speedup >= 1.1x = 129 / 160
  mean overlap-model speedup = 1.323x

spec_hit:
  positive rows = 160 / 160
  speedup >= 1.1x = 126 / 160
  mean overlap-model speedup = 1.323x

spec_miss:
  positive rows = 105 / 160
  speedup >= 1.1x = 90 / 160
  mean overlap-model speedup = 1.033x

mixed:
  positive rows = 128 / 160
  speedup >= 1.1x = 116 / 160
  mean overlap-model speedup = 1.203x
```

Interpretation:

- If there is no wait window (`validate_iters=0`) and miss rate is high, LDS
  speculation loses, as expected.
- Once there is a modest metadata/router wait window, speculative LDS staging
  has a broad positive break-even region.

Router-interference stress:

- Report: `outputs/reports/lds_tile_staging/sweep_interference_2gpu.json`
- CSV: `outputs/reports/lds_tile_staging/sweep_interference_2gpu.csv`
- Markdown: `outputs/reports/lds_tile_staging/sweep_interference_2gpu.md`
- Plot: `outputs/reports/lds_tile_staging/sweep_interference_2gpu.png`

Stress grid:

```text
tile_elems = [1024, 2048]
validate_iters = [64, 256]
miss_rate = [0.25, 0.5]
block_threads = [128, 256]
interference_iters = [0, 2, 8]
devices = [GPU0, GPU1]
```

Stress summary:

```text
mixed:
  positive rows = 47 / 48
  speedup >= 1.1x = 46 / 48
  mean overlap-model speedup = 1.370x

spec_miss:
  positive rows = 35 / 48
  speedup >= 1.1x = 26 / 48
  mean overlap-model speedup = 1.115x
```

Grouped by interference:

```text
mixed interference=0: positive=15/16, mean=1.348x
mixed interference=2: positive=16/16, mean=1.404x
mixed interference=8: positive=16/16, mean=1.357x

spec_miss interference=0: positive=11/16, mean=1.092x
spec_miss interference=2: positive=11/16, mean=1.121x
spec_miss interference=8: positive=13/16, mean=1.133x
```

This stress mode is still a synthetic concurrent HBM/ALU kernel, not a real
router. It is sufficient as a P0 guard that the envelope does not disappear
under a simple competing stream. The next gate should use a more realistic
router/metadata-builder mock before moving to rocWMMA or CK.

Same-kernel metadata-builder mock:

The LDS microbench now supports a same-kernel metadata phase via
`--metadata-tokens`. Each workgroup:

```text
1. speculatively stages a tile in LDS
2. builds synthetic expert_counts and expert_offsets in the same LDS allocation
3. validates true vs predicted expert
4. consumes staged LDS tile on hit or overwrites LDS on miss
```

This is the correct semantic model for LDS: staged state remains live only
inside the same kernel/workgroup execution window.

Metadata-builder sweep:

- Report: `outputs/reports/lds_tile_staging/sweep_metadata_builder_2gpu.json`
- CSV: `outputs/reports/lds_tile_staging/sweep_metadata_builder_2gpu.csv`
- Markdown: `outputs/reports/lds_tile_staging/sweep_metadata_builder_2gpu.md`
- Plot: `outputs/reports/lds_tile_staging/sweep_metadata_builder_2gpu.png`

Grid:

```text
tile_elems = [512, 1024]
metadata_tokens = [0, 32, 64, 128]
validate_iters = [0]
miss_rate = [0.25, 0.5, 1.0]
block_threads = [128, 256]
devices = [GPU0, GPU1]
```

Summary by metadata window:

```text
mixed metadata_tokens=0:
  positive=3/12, mean=0.880x
mixed metadata_tokens=32:
  positive=12/12, mean=1.159x
mixed metadata_tokens=64:
  positive=12/12, mean=1.149x
mixed metadata_tokens=128:
  positive=12/12, mean=1.144x

spec_miss metadata_tokens=0:
  positive=1/12, mean=0.770x
spec_miss metadata_tokens=32:
  positive=12/12, mean=1.098x
spec_miss metadata_tokens=64:
  positive=12/12, mean=1.088x
spec_miss metadata_tokens=128:
  positive=12/12, mean=1.085x
```

Interpretation:

- Without a same-kernel router/metadata window, speculative LDS staging often
  loses under miss-heavy regimes.
- Once the workgroup has even a modest metadata-builder window, both mixed and
  worst-case miss modes become consistently positive in this mock.
- This is stronger evidence for the core claim than separate-stream
  interference: the staged tile is validated and consumed/overwritten within
  the same workgroup.

The runner now reports a break-even hit-rate estimate:

```text
T_spec = p * T_hit + (1 - p) * T_miss
profitable when T_spec < T_base
p_min = (T_miss - T_base) / (T_miss - T_hit)
```

If `T_miss < T_base`, the report marks the configuration as profitable for any
positive hit rate.

Anti-artifact controls and grouped-compute mock:

The LDS bench now includes three control modes:

```text
dummy_lds_store:
  write dummy values into LDS, then load the true tile

wrong_no_consume:
  stage a wrong tile but consume the true tile from global memory

global_no_lds:
  touch the predicted global tile but do not stage it into LDS
```

It also supports `--compute-iters`, a lightweight grouped-GEMM consumer mock
that repeats FMA passes over the staged tile. This is not rocWMMA yet;
it only verifies that the staged LDS state is consumed by nontrivial compute.

Control / compute report:

- `outputs/reports/lds_tile_staging/controls_compute_gpu0.json`
- `outputs/reports/lds_tile_staging/sweep_compute_controls_2gpu.json`
- `outputs/reports/lds_tile_staging/sweep_compute_controls_2gpu.csv`

Config:

```text
tile_elems = 1024
metadata_tokens = 64
validate_iters = 0
compute_iters = [1, 4, 16]
miss_rate = [0.25, 0.5]
block_threads = 256
devices = [GPU0, GPU1]
```

Grouped by compute intensity:

```text
compute_iters=1:
  spec_hit wall ~= 0.04794 ms, overlap ~= 1.174x
  mixed    wall ~= 0.05296 ms, overlap ~= 1.116x
  spec_miss wall ~= 0.05126 ms, overlap ~= 1.030x

compute_iters=4:
  spec_hit wall ~= 0.05430 ms, overlap ~= 1.173x
  mixed    wall ~= 0.05864 ms, overlap ~= 1.117x
  spec_miss wall ~= 0.06046 ms, overlap ~= 1.035x

compute_iters=16:
  spec_hit wall ~= 0.07840 ms, overlap ~= 1.136x
  mixed    wall ~= 0.07999 ms, overlap ~= 1.089x
  spec_miss wall ~= 0.08241 ms, overlap ~= 1.013x
```

Control interpretation:

- Control modes should not use the overlap model as a profitability claim,
  because they intentionally do not consume staged LDS tile state.
- Their wall-time behavior is the anti-artifact check. In the compute mock,
  `wrong_no_consume` and `global_no_lds` do not reproduce the low-cost
  `spec_hit` path, so ordinary global cache warming is not enough to explain
  the speculative LDS hit result.
- As compute becomes heavier, first-FMA/prologue savings are diluted in total
  wall time; this is expected and means the next WMMA/rocWMMA stage should
  report both first-FMA/prologue latency and end-to-end kernel time.
- The compute mock now supports `--consumer-rows`, where each workgroup reuses
  the staged expert tile across multiple synthetic token rows. This is still
  hand-written FMA, not rocWMMA, but it is closer to grouped-GEMM tile
  reuse than a single pass over the tile.

Hardware target note:

```text
The current local GPUs are W7900 / RDNA3. The next real matrix path should be
WMMA / rocWMMA-oriented. MFMA is a CDNA-oriented follow-up and should not be
used as the primary W7900 claim.
```

Anti-artifact counters and stride/flush controls:

The LDS bench now reports explicit staged-tile outcomes:

```text
staged_tile_count
staged_tile_consumed_count
staged_tile_discarded_count
fallback_true_tile_load_count
staged_tile_consumed_fraction
staged_tile_discarded_fraction
```

It also reports LDS pressure / occupancy proxies:

```text
lds_bytes_per_block
lds_limited_blocks_per_cu
thread_limited_blocks_per_cu
occupancy_blocks_per_cu
```

New anti-artifact knobs:

```text
--tile-stride:
  spaces logical expert tiles apart in the physical tile array, increasing the
  working set and reducing accidental locality

--cache-flush-elems:
  touches a separate global buffer before the measured kernel, reducing cache
  warming artifacts
```

Stride/flush control sweep:

- Report: `outputs/reports/lds_tile_staging/sweep_antifact_stride_flush_2gpu.json`
- CSV: `outputs/reports/lds_tile_staging/sweep_antifact_stride_flush_2gpu.csv`
- Markdown: `outputs/reports/lds_tile_staging/sweep_antifact_stride_flush_2gpu.md`
- Plot: `outputs/reports/lds_tile_staging/sweep_antifact_stride_flush_2gpu.png`

Grid:

```text
tile_elems = [1024]
metadata_tokens = [64]
validate_iters = [0]
compute_iters = [4]
miss_rate = [0.25, 0.5]
block_threads = [256]
tile_stride = [1, 4]
cache_flush_elems = [0, 1048576]
devices = [GPU0, GPU1]
include_controls = true
```

Summary:

```text
spec_hit:
  positive rows = 8 / 8
  speedup >= 1.1x = 8 / 8
  mean overlap-model speedup = 1.183x
  staged consumed fraction = 1.000

mixed:
  positive rows = 8 / 8
  speedup >= 1.1x = 8 / 8
  mean overlap-model speedup = 1.128x
  staged consumed fraction ~= 0.629
  staged discarded fraction ~= 0.371

spec_miss:
  positive rows = 8 / 8
  speedup >= 1.1x = 0 / 8
  mean overlap-model speedup = 1.043x
  staged discarded fraction = 1.000
```

Control wall-time check:

```text
spec_hit:
  mean wall delta vs reactive ~= -0.00079 ms
  staged consumed fraction = 1.000

wrong_no_consume:
  mean wall delta vs reactive ~= +0.00111 ms
  staged consumed fraction = 0.000
  staged discarded fraction = 1.000

global_no_lds:
  mean wall delta vs reactive ~= +0.00118 ms
  staged consumed fraction = 0.000
```

Interpretation:

- Stride/flush controls do not erase the `spec_hit` prologue envelope under the
  same-kernel metadata-builder mock.
- `wrong_no_consume` and `global_no_lds` do not reproduce the `spec_hit`
  wall-time path, so the hit result is less likely to be explained only by
  global cache warming.
- Control-mode overlap-model values are not used as speedup claims, because
  those modes intentionally do not consume staged LDS tile state.
- Miss paths remain lower value than hit paths. This reinforces the need for a
  hit-rate / utility gate before enabling LDS staging.

Grouped-consumer sweep:

- Report: `outputs/reports/lds_tile_staging/sweep_grouped_consumer_rows_2gpu.json`
- CSV: `outputs/reports/lds_tile_staging/sweep_grouped_consumer_rows_2gpu.csv`
- Markdown: `outputs/reports/lds_tile_staging/sweep_grouped_consumer_rows_2gpu.md`
- Plot: `outputs/reports/lds_tile_staging/sweep_grouped_consumer_rows_2gpu.png`

Grid:

```text
tile_elems = [1024]
metadata_tokens = [64]
validate_iters = [0]
compute_iters = [2]
consumer_rows = [1, 4, 8]
miss_rate = [0.25, 0.5]
block_threads = [256]
tile_stride = [4]
cache_flush_elems = [1048576]
devices = [GPU0, GPU1]
```

Summary:

```text
spec_hit:
  positive rows = 6 / 6
  speedup >= 1.1x = 6 / 6
  mean overlap-model speedup = 1.269x

mixed:
  positive rows = 6 / 6
  speedup >= 1.1x = 6 / 6
  mean overlap-model speedup = 1.156x

spec_miss:
  positive rows = 5 / 6
  speedup >= 1.1x = 0 / 6
  mean overlap-model speedup = 1.024x
```

Grouped by tile reuse:

```text
consumer_rows=1:
  spec_hit mean ~= 1.289x
  mixed mean ~= 1.151x
  spec_miss mean ~= 1.040x

consumer_rows=4:
  spec_hit mean ~= 1.280x
  mixed mean ~= 1.167x
  spec_miss mean ~= 1.003x

consumer_rows=8:
  spec_hit mean ~= 1.237x
  mixed mean ~= 1.150x
  spec_miss mean ~= 1.028x
```

Interpretation:

- The staged-hit path remains positive when the same LDS tile is consumed by
  multiple synthetic token rows.
- Mixed speculation remains positive across the row-reuse sweep, while miss-only
  paths stay marginal. That is the desired shape for a utility-gated
  low-trust hint.
- This is still not a real WMMA/rocWMMA grouped-GEMM claim. It is the last
  hand-written HIP stage before a true matrix-tile consumer.

LDS p_min runtime-policy bridge:

Runtime policy now carries an explicit on-chip staging gate:

```text
allow_lds_stage = (
    transition_ready_rate is healthy
    and lds_expected_hit_rate >= lds_p_min_hit_rate + safety_margin
    and lds_occupancy_blocks_per_cu >= min_occupancy
)
```

This gate is intentionally independent from H2D `full_fetch` admission. A tight
PCIe / H2D transfer envelope can disable MTP expert full-fetch while still
allowing kernel-internal LDS staging when the microbench p_min and occupancy
conditions are satisfied.

New fields:

```text
RuntimeSignals:
  lds_expected_hit_rate
  lds_p_min_hit_rate
  lds_occupancy_blocks_per_cu

RuntimePrefetchPolicy:
  allow_lds_stage
  lds_stage_reason
```

Unit tests:

```text
tests/test_runtime_policy.py:
  LDS missing calibration -> disabled
  expected hit rate above p_min + margin -> enabled
  expected hit rate below margin -> disabled
  low occupancy -> disabled
  H2D transfer fallback can still allow LDS stage
```

LDS stage policy evaluator:

- Script: `scripts/evaluate_lds_stage_policy.py`
- Normal grouped-consumer report:
  `outputs/reports/lds_tile_staging/lds_stage_policy_eval_grouped_consumer.json`
- Boundary report:
  `outputs/reports/lds_tile_staging/lds_stage_policy_eval_boundary.json`

The evaluator maps sweep CSV rows to tier-level eligibility:

```text
transition_top16: expected hit 0.90
transition_top17_32: expected hit 0.65
mtp_extra1_4: expected hit 0.45
mtp_extra5_8: expected hit 0.30
random_control: expected hit 0.125
```

Grouped-consumer normal envelope:

```text
mtp_extra1_4: enabled 6/6
mtp_extra5_8: enabled 6/6
random_control: enabled 5/6
mean required hit rate ~= 0.073
```

Boundary sweep without same-kernel metadata-builder window:

- Report: `outputs/reports/lds_tile_staging/sweep_lds_stage_gate_boundary_2gpu.json`
- CSV: `outputs/reports/lds_tile_staging/sweep_lds_stage_gate_boundary_2gpu.csv`

```text
mixed:
  positive rows = 3 / 6
  mean overlap-model speedup = 1.100x

p_min-gated eligibility:
  transition_top16: enabled 4/6
  transition_top17_32: enabled 4/6
  mtp_extra1_4: enabled 4/6
  mtp_extra5_8: enabled 3/6
  random_control: enabled 3/6
```

Interpretation:

- In normal same-kernel metadata windows, p_min is low and LDS stage is broadly
  eligible.
- In poor/no-window regimes, p_min gates off lower-confidence tiers. This is the
  desired bridge from microbench timing to runtime policy: LDS staging is an
  admitted action, not a default behavior.

LDS layout sweep:

The hand-written HIP bench now supports `--lds-layout`:

```text
linear:
  direct logical index -> LDS index

padded32:
  adds one padding float per 32 logical elements

xor_swizzle:
  XOR-swizzles lane positions inside each 32-element group without increasing
  storage size
```

Layout sweep artifacts:

- Report: `outputs/reports/lds_tile_staging/sweep_lds_layout_2gpu.json`
- CSV: `outputs/reports/lds_tile_staging/sweep_lds_layout_2gpu.csv`
- Markdown: `outputs/reports/lds_tile_staging/sweep_lds_layout_2gpu.md`
- Plot: `outputs/reports/lds_tile_staging/sweep_lds_layout_2gpu.png`

Grid:

```text
tile_elems = [1024]
metadata_tokens = [64]
validate_iters = [0]
compute_iters = [2]
consumer_rows = [4]
miss_rate = [0.25, 0.5]
block_threads = [256]
tile_stride = [4]
cache_flush_elems = [1048576]
lds_layout = [linear, padded32, xor_swizzle]
devices = [GPU0, GPU1]
```

Summary by layout:

```text
linear:
  spec_hit mean ~= 1.282x
  mixed mean ~= 1.155x
  spec_miss mean ~= 1.087x
  lds_bytes_per_block = 6144
  occupancy_blocks_per_cu = 8

padded32:
  spec_hit mean ~= 1.263x
  mixed mean ~= 1.178x
  spec_miss mean ~= 1.054x
  lds_bytes_per_block = 6272
  occupancy_blocks_per_cu = 8

xor_swizzle:
  spec_hit mean ~= 1.256x
  mixed mean ~= 1.160x
  spec_miss mean ~= 1.049x
  lds_bytes_per_block = 6144
  occupancy_blocks_per_cu = 8
```

Interpretation:

- All three layouts preserve a positive overlap-model envelope in this small
  W7900 sweep.
- `linear` is best for the pure hit path here; `padded32` gives slightly better
  mixed-mode mean but costs extra LDS storage.
- At `tile_elems=1024`, all layouts remain thread-limited at 8 blocks/CU rather
  than LDS-limited. Larger tiles are needed to stress the occupancy gate.

rocWMMA gfx1100 smoke:

The current local GPUs are RDNA3 / gfx1100 W7900-class devices, so the real
matrix-core path for this machine is WMMA / rocWMMA. MFMA remains a CDNA
follow-up and should not be used as the primary W7900 claim.

Implemented minimal rocWMMA smoke:

- Source: `microbench/rocwmma_smoke/rocwmma_hello.hip`
- Runner: `scripts/run_rocwmma_hello.py`
- Notes: `microbench/rocwmma_smoke/README.md`
- Report: `outputs/reports/rocwmma_smoke/rocwmma_hello_2gpu.json`

Smoke semantics:

```text
16x16x16 GEMM
input dtype: rocwmma::float16_t
accumulator dtype: float
layout: row-major A/B/C
target: --offload-arch=gfx1100
```

Two-GPU result:

```text
GPU0 AMD Radeon Pro W7900:
  ok = true
  max_abs_err = 0.0
  mean_abs_err = 0.0
  wall_ms_mean ~= 0.01019

GPU1 AMD Radeon Pro W7900 Dual Slot:
  ok = true
  max_abs_err = 0.0
  mean_abs_err = 0.0
  wall_ms_mean ~= 0.01682
```

Interpretation:

- rocWMMA headers, fragment load, `mma_sync`, and store compile and run on both
  local gfx1100 devices.
- This is only an API / numerical correctness gate. It does not yet validate
  speculative LDS staging with rocWMMA.
- Next gates are a global rocWMMA tile baseline, then an LDS-staged rocWMMA
  consumer with hit / miss / overwrite timing.

rocWMMA LDS-staged tile consumer smoke:

Implemented a second rocWMMA smoke that compares one 16x16x16 tile under three
paths:

```text
global_baseline:
  rocWMMA loads A/B directly from global memory

lds_hit:
  stage A/B into LDS, then rocWMMA loads fragments from LDS

lds_miss_overwrite:
  stage a wrong B tile into LDS, overwrite B after validation,
  then rocWMMA consumes the corrected LDS B tile
```

Artifacts:

- Source: `microbench/rocwmma_smoke/rocwmma_tile_stage.hip`
- Runner: `scripts/run_rocwmma_tile_stage.py`
- Report: `outputs/reports/rocwmma_smoke/rocwmma_tile_stage_2gpu.json`
- Reuse report: `outputs/reports/rocwmma_smoke/rocwmma_tile_stage_reuse_2gpu.json`

The smoke now treats B as the expert weight tile and supports `--consumer-rows`.
`lds_hit` stages B once into LDS, then reuses it across multiple synthetic
token rows while each row loads a separate A tile from global memory.

Two-GPU result:

```text
consumer_rows = 1 / 4 / 8
all modes max_abs_err = 0.0

GPU0 lds_hit speedup vs global:
  rows=1: 0.968x
  rows=4: 0.949x
  rows=8: 0.947x

GPU1 lds_hit speedup vs global:
  rows=1: 0.988x
  rows=4: 0.971x
  rows=8: 0.966x

GPU0 lds_miss_overwrite speedup vs global:
  rows=1: 0.902x
  rows=4: 0.898x
  rows=8: 0.889x

GPU1 lds_miss_overwrite speedup vs global:
  rows=1: 0.914x
  rows=4: 0.910x
  rows=8: 0.895x
```

Interpretation:

- rocWMMA fragments can consume LDS-staged tiles correctly on gfx1100.
- In this minimal no-overlap smoke, even B-tile reuse across 1/4/8 synthetic
  rows does not beat direct rocWMMA global loads. `lds_miss_overwrite` is slower
  still. This is expected and useful: simple LDS staging is not a default
  speedup mechanism unless a same-kernel validation window, larger grouped tile
  reuse, or scheduling overlap hides the staging cost.
- This result strengthens the contract: LDS staging must remain gated by
  expected hit rate, p_min, occupancy, and available validation/metadata window.
- Next gates are a rocWMMA tile-stage benchmark with explicit same-kernel
  validation-window timing, more realistic grouped tile shapes, and hit/miss
  p_min reporting. A rocprof pass should also confirm global/LDS traffic and
  occupancy effects before any performance claim is made.

rocWMMA same-kernel validation-window p_min sweep:

The rocWMMA tile-stage smoke now supports `--validate-iters`. The kernel uses
the same action order as the proposed staging contract:

```text
global_baseline:
  validation work -> rocWMMA loads B from global memory

lds_hit:
  stage B into LDS -> validation work -> rocWMMA consumes staged B

lds_miss_overwrite:
  stage wrong B into LDS -> validation work -> overwrite with true B
  -> rocWMMA consumes corrected B
```

The runner reports p_min per `(device, consumer_rows, validate_iters)`:

```text
T_spec = p * T_hit + (1 - p) * T_miss
profitable when T_spec < T_global
```

Artifact:

- Report: `outputs/reports/rocwmma_smoke/rocwmma_tile_stage_validate_2gpu.json`
- Policy eval: `outputs/reports/rocwmma_smoke/lds_stage_policy_eval_rocwmma_serial.json`
- Policy eval markdown: `outputs/reports/rocwmma_smoke/lds_stage_policy_eval_rocwmma_serial.md`

Grid:

```text
devices = [GPU0, GPU1]
consumer_rows = [1, 4, 8]
validate_iters = [0, 64, 256]
modes = [global_baseline, lds_hit, lds_miss_overwrite]
```

Result:

```text
all rows ok = true
all max_abs_err = 0.0
all 18 p_min rows = not_profitable_even_at_full_hit
policy evaluator:
  transition_top16 enabled = 0 / 18
  transition_top17_32 enabled = 0 / 18
  mtp_extra1_4 enabled = 0 / 18
  mtp_extra5_8 enabled = 0 / 18
  random_control enabled = 0 / 18
```

Representative rows:

```text
GPU0 rows=1 validate=0:
  global=0.01005 ms, hit=0.01050 ms, miss=0.01126 ms

GPU0 rows=4 validate=256:
  global=0.02065 ms, hit=0.02238 ms, miss=0.02349 ms

GPU1 rows=8 validate=256:
  global=0.02358 ms, hit=0.02477 ms, miss=0.02627 ms
```

Interpretation:

- rocWMMA correctness for global, staged-hit, and staged-miss-overwrite paths is
  stable under the validation-window sweep.
- A serial same-kernel validation phase does not hide the LDS staging cost.
  Even full hit-rate is not profitable in this small tile benchmark.
- This is a useful negative boundary: the next WMMA gate must model real
  overlap or pipelining, for example separate producer/validator waves,
  multiple workgroups, persistent grouped-GEMM scheduling, larger grouped tile
  shapes, or rocprof-confirmed latency hiding.
- The runtime policy implication remains conservative: `lds_stage` is disabled
  unless measured p_min is finite and the expected hit rate clears it with a
  safety margin. The runtime gate now reports `lds_p_min_not_profitable` for
  non-finite / not-profitable p_min artifacts.

rocWMMA multi-CTA / large B-pool throughput sweep:

The rocWMMA tile-stage benchmark now supports:

```text
num_cta
b_pool_tiles
tile_stride
cache_flush_elems
global_frag_reuse baseline
global_reload_per_row baseline
wall_us_per_output_tile
```

Motivation:

```text
global_frag_reuse:
  B is loaded once into a rocWMMA fragment and reused across rows.
  This is a strong baseline and LDS staging adds an extra global->LDS->fragment hop.

global_reload_per_row:
  B is reloaded for each consumer row.
  This is the scenario where sharing B through LDS can plausibly help.
```

Artifact:

- Report: `outputs/reports/rocwmma_smoke/rocwmma_tile_stage_multicta_2gpu.json`
- Strong-baseline policy eval:
  `outputs/reports/rocwmma_smoke/lds_stage_policy_eval_rocwmma_multicta_frag_reuse.json`
- Reload-baseline policy eval:
  `outputs/reports/rocwmma_smoke/lds_stage_policy_eval_rocwmma_multicta_reload.json`

Grid:

```text
devices = [GPU0, GPU1]
consumer_rows = [4, 8, 16]
num_cta = [64, 256]
b_pool_tiles = [1024]
tile_stride = [17]
cache_flush_elems = [1048576]
validate_iters = [0]
```

Summary:

```text
against global_frag_reuse:
  not_profitable_even_at_full_hit = 11 / 12
  finite p_min rows = 1 / 12
  enabled rows under default tier table = 1 / 12 for non-random tiers

against global_reload_per_row:
  not_profitable_even_at_full_hit = 7 / 12
  finite / always-profitable rows = 5 / 12
  enabled rows under default tier table = 4 / 12 for transition/MTP tiers
```

Representative profitable rows against `global_reload_per_row`:

```text
GPU0 rows=8 num_cta=256:
  p_min ~= 0.136

GPU0 rows=16 num_cta=256:
  p_min = 0.0  # profitable for any hit rate in this run

GPU1 rows=8 num_cta=256:
  p_min ~= 0.067

GPU1 rows=16 num_cta=256:
  p_min = 0.0
```

Interpretation:

- The earlier serial negative result is not solely a single-CTA artifact.
  Against the strong `global_frag_reuse` baseline, LDS staging remains mostly
  unprofitable.
- LDS staging starts to look useful only against the weaker
  `global_reload_per_row` baseline, where the baseline repeatedly reloads B.
- Therefore the safe claim is narrower: rocWMMA LDS staging may help only when
  the real grouped-GEMM path cannot already reuse the expert B tile in
  fragments/registers and when enough rows share that B tile.
- The next required gate is rocprof/counter validation. We need to confirm
  whether the actual target kernel resembles `global_frag_reuse` or
  `global_reload_per_row`, and whether the observed wins correspond to lower
  global B traffic rather than timing noise.

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

Held-out replay consistency:

```text
script:
  scripts/replay_matrix_transition_shadow.py

inputs:
  configs/eval/prefetch_shadow_512sample_mtp_extra.yaml
  outputs/artifacts/transition_matrix_512sample_calibrated.pt

output summary:
  outputs/reports/matrix_transition_shadow_replay/heldout128_summary.json

heldout split:
  samples = 128
  positions = 384..511
  joined token-layer outcomes = 455,400
  token0 outcome-only sentinel rows = 5,120

comparison:
  online matrix_top32 joined-only
  vs offline calibrated transition@32
```

Result:

```text
metric                       online joined      offline transition@32    abs diff
covered_mass_mean            0.8006447121       0.8006447554            4.32e-08
top1_ready_rate              0.9065700483       0.9065700769            2.86e-08
weighted_top1_miss_mean      0.02241862245      0.02241862193           5.24e-10
miss_mass_mean               0.1993552877       0.1993552446            4.31e-08
outcome_count                455,400            455,400                 0
```

Interpretation:

```text
online matrix_top32 == offline calibrated transition@32 on heldout replay.
The comparison must use joined-only outcomes; aggregate all-outcome metrics
include token0 outcome-only sentinels and are intentionally lower.
```

## Online Action Policy Replay

After `matrix_top32` was validated as the online transition base, the full
action-level MTP policy was replayed through the runtime shadow schema:

```text
full_fetch:
  utility-gated, up to MTP_extra4

metadata:
  raw-score high-tail, max_extra=1

premap:
  tiny descriptor budget, max_extra=1

skip:
  default fallback for remaining candidates
```

512 held-out summary-only replay:

```text
command:
  python scripts/export_runtime_shadow_jsonl.py \
    --tensor-cache outputs/reports/prefetch_shadow_512sample_mtp_extra/event_stall_tensor_cache_512sample.pt \
    --summary-only \
    --full-fetch-max-extra 4 \
    --metadata-max-extra 1 \
    --premap-max-extra 1 \
    --action-keep-fraction 0.5 \
    --metadata-score-ratio 0.95 \
    --bandwidth-gbps 6.589 \
    --layer-ms 1.0 \
    --mtp-delay-ms 2.0

summary:
  outputs/reports/action_shadow_replay_512/utility_keep50_summary.json
```

Action replay result:

```text
ready_mass_mean           = 0.8185046113
top1_ready_rate           = 0.9205775143
weighted_top1_miss_mean   = 0.0192181603

full_fetch_count          = 900,460
metadata_count            = 170,805
premap_count              = 455,400

full_fetch_later_used     = 70,268
metadata_later_used       = 12,183
premap_later_used         = 21,298

policy_mode               = default
policy_reason             = normal_envelope
ready_base_fraction       = 1.0
ready_extra_fraction      = 0.91875
```

Consistency against the event-sim normal report:

```text
report:
  outputs/reports/action_shadow_replay_512/utility_keep50_consistency.json

policy:
  transition_top32_plus_gated_utility_keep_top_0.500

result:
  ok = true
  metric_group = all
  rtol = 0.002
```

Observed differences:

```text
ready_mass_fraction       abs diff = 8.71e-05
top1_ready_rate           abs diff = 2.42e-05
weighted_top1_miss        abs diff = 5.20e-06
full_fetch_count          exact
metadata_count            exact
premap_count              exact
full_fetch_later_used     exact
metadata_later_used       exact
premap_later_used         diff = 1 count
```

Small JSONL smoke:

```text
output:
  outputs/reports/action_shadow_replay_512/utility_keep50_smoke_16.jsonl

num_eval_token_examples = 16
summary_count = 640
outcome_count = 640
full_fetch_count = 1,116
metadata_count = 178
premap_count = 640
```

Interpretation:

```text
The full action policy can be emitted through the runtime shadow schema and
matches the event simulator within tolerance on 512 held-out data.
The next runtime gate is wiring this action producer into the online vLLM
shadow path after live MTP-token sidecar/action features are available.
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

## rocWMMA / LDS Staging Microbench Status

Current LDS direction is deliberately gated by kernel-specific evidence:

```text
hand-written HIP LDS mock:
  supports a speculative staging envelope under anti-artifact controls

rocWMMA serial stage -> validate -> consume:
  rejected by p_min gate
  all tested serial configs were not_profitable_even_at_full_hit

rocWMMA multi-CTA baseline split:
  global_frag_reuse baseline:
    LDS staging is almost always rejected
    interpretation: no room when B fragment/register reuse is already strong

  global_reload_per_row baseline:
    several rows have finite or zero p_min
    representative:
      GPU0 rows=8  cta=256  p_min ~= 0.136
      GPU0 rows=16 cta=256  p_min = 0.0
      GPU1 rows=8  cta=256  p_min ~= 0.067
      GPU1 rows=16 cta=256  p_min = 0.0
    interpretation: LDS staging is conditionally viable when B-tile reload
    pressure exists
```

Safe claim:

```text
LDS staging is conditionally viable, not universally beneficial.
The next gate is classifying whether the real target grouped-GEMM path is
fragment-reuse-like or reload-per-row-like.
```

rocprof classification harness:

```text
script:
  scripts/run_rocwmma_rocprof_classification.py

smoke output:
  outputs/reports/rocwmma_smoke/rocprofv3_classification_raw_smoke/

tool status:
  rocprof-compute is not usable in the current environment because Python UI
  dependencies are missing.
  legacy rocprof works only when counters are split into HW-feasible groups.
  rocprofv3 is available and the harness supports per-metric runs to avoid
  multi-counter hangs.

current counter caveat:
  On the W7900/gfx1100 rocWMMA smoke, SQ_WAVES is non-zero but SQ_INSTS_LDS /
  SQ_INSTS_TEX_LOAD / FETCH_SIZE currently report zero under rocprof/rocprofv3.
  Therefore these counters are not yet trusted for B-reload classification.
  The harness explicitly records metric_completeness so zero-valued counter
  runs are not misread as real no-traffic evidence.

counter discovery / positive-control follow-up:
  rocprofv3-avail is now captured in reports:
    rocprofv3-avail list --agent
    rocprofv3-avail -d <device> list --pmc
    rocprofv3-avail -d <device> pmc-check <metrics>

  On GPU0, rocprofv3-avail lists the selected counters and pmc-check accepts
  SQ_WAVES / SQ_INSTS_LDS / SQ_INSTS_TEX_LOAD / FETCH_SIZE together. However,
  positive-control kernels still show only SQ_WAVES as non-zero:

    global_load_heavy:
      SQ_WAVES non-zero
      SQ_INSTS_LDS / SQ_INSTS_TEX_LOAD / FETCH_SIZE = 0

    lds_heavy:
      SQ_WAVES non-zero
      SQ_INSTS_LDS / SQ_INSTS_TEX_LOAD / FETCH_SIZE = 0

  This means the current counter path is not informative even for obvious
  global/LDS traffic. The issue is therefore not specific to rocWMMA. Until a
  trustworthy counter path is found, B-reload classification must not use these
  counter values.

  Visibility / agent-index salvage checks:
    HIP_VISIBLE_DEVICES=0 / ROCR_VISIBLE_DEVICES=0 / HSA_VISIBLE_DEVICES=0
    does not change the result.
    rocprofv3 --agent-index type-relative also does not change the result.

  Both runs still report SQ_WAVES = 2048 for 256 blocks x 256 threads on
  wave32, while the selected traffic counters remain zero. This confirms that
  the kernel filter, parser, and basic agent selection are working, but the
  traffic/LDS counter values remain unsuitable for claims.

static ISA fallback:
  scripts/inspect_hip_isa_static.py extracts .hip_fatbin, unbundles the
  gfx1100 device object, disassembles it, and counts instruction buckets such
  as global_load, lds_load, lds_store, barrier, waitcnt, and WMMA/matrix ops.

  Positive-control static smoke confirms the fallback sees the expected ISA:
    global_load_heavy: global_load present, no LDS load/store bucket
    lds_heavy: global_load plus lds_load / lds_store / barrier buckets present

  rocWMMA tile-stage static smoke also finds global_load, lds_load, lds_store,
  barrier, waitcnt, and a WMMA/matrix bucket. This is static supporting
  evidence only; it cannot replace hardware byte counters, but it is a safe
  fallback when profiler counters are non-informative.

mode-specialized rocWMMA kernels:
  The rocWMMA tile-stage benchmark no longer relies on one device kernel with a
  runtime mode switch. It now launches separate kernels:

    global_frag_reuse_kernel
    global_reload_per_row_kernel
    lds_hit_kernel
    lds_miss_overwrite_kernel

  This makes rocprof kernel filtering and static ISA inspection mode-specific.
  Host CLI semantics remain unchanged through --mode.

  GPU0 specialized smoke:
    rows=8, num_cta=64, b_pool=1024, stride=17, cache_flush=1M
    correctness: all four modes pass
    timing:
      global_frag_reuse      0.0109996 ms
      global_reload_per_row  0.0114240 ms
      lds_hit                0.0120080 ms
      lds_miss_overwrite     0.0126960 ms
    p_min status:
      vs global_frag_reuse: not_profitable_even_at_full_hit
      vs global_reload_per_row: not_profitable_even_at_full_hit

  Static ISA now separates the four symbols. The LDS modes show LDS load/store
  buckets, while global modes do not. However, static instruction counts do not
  expand runtime loops, so global_frag_reuse and global_reload_per_row can still
  look structurally similar in ISA. Reload pressure therefore still needs
  timing classification; static ISA is a structural sanity check, not a dynamic
  traffic substitute.

reload-pressure ladder:
  A two-GPU specialized ladder was run with:

    devices: GPU0 W7900, GPU1 W7900 Dual Slot
    rows: 8, 32
    num_cta: 64, 256
    b_pool_tiles: 1024, 16384
    cache_flush_elems: 0, 16M
    modes: frag, reload, distinct-reload, lds_hit, lds_miss

  Artifact:
    outputs/reports/rocwmma_smoke/rocwmma_tile_stage_specialized_ladder_2gpu.json
    outputs/reports/rocwmma_smoke/rocwmma_tile_stage_specialized_ladder_2gpu_summary.md

  Summary:
    config rows: 32
    LDS hit beats global_frag_reuse: 7 / 32
    LDS hit beats global_reload_per_row: 7 / 32
    LDS hit beats global_reload_distinct_per_row: 17 / 32

  Interpretation:
    distinct-B reload amplification can create reload pressure, and LDS hit can
    beat that distinct-reload control in some rows. However, this is not yet a
    clean default-positive LDS result: several wins depend on cache-flush /
    large-pool conditions, miss behavior remains unstable, and the direct
    global-fragment path is often still the fastest baseline. Naive LDS payload
    staging therefore remains a gated branch, not the main runtime direction.

  Current branch condition:
    If further official-like rocWMMA LB2/PGR1/CP or double-buffer tests do not
    show a robust hit-path win against a reload-heavy baseline, demote LDS
    payload staging to a negative result / optional future action.

New engineering direction from review:
  The higher-ROI systems direction is now:

    MTP/transition-guided cache-aware tile ordering for exact MoE grouped dispatch.

  In this pivot, MTP/transition hints do not stage payload into LDS. They guide:
    tile visitation order
    expert-major / B-tile grouped scheduling
    hot-first ordering
    descriptor precompute / patching
    persistent grouped scheduler work assignment

  Candidate metrics:
    tile-order hit rate
    B tile reuse distance
    unique B tiles per scheduling window
    wall time under hot/cold expert ordering
    descriptor build / patch / overwrite time

  This aligns better with MetaShuffling / persistent grouped-GEMM directions
  while preserving the project's low-trust MTP prior: true router remains
  authoritative, but hint quality can influence cache-aware scheduling order.
```

Next LDS / rocWMMA steps:

```text
1. Keep trying for a trustworthy counter path only through positive controls,
   but treat the current rocprofv3 counter values as non-informative:
   - rocprofv3-avail discovery is recorded
   - positive-control kernels fail to produce non-zero LDS/global traffic
     counters beyond SQ_WAVES
   - visibility masks and --agent-index type-relative did not fix the issue

2. Use static ISA inspection plus timing-based baseline classification as the
   interim path:
   - static global/LDS instruction buckets
   - frag_reuse vs reload_per_row timing similarity
   - p_min status from the measured baseline split

3. Once counters are trustworthy, additionally report:
   kernel, wall_time, global_read_bytes, LDS traffic, occupancy,
   WMMA utilization proxy, B_reload_ratio, p_min_status

4. Only if the target path is reload-like:
   first test official-like rocWMMA LB2/PGR1/CP and a small double-buffer
   skeleton. Only move to producer-consumer / persistent grouped-GEMM if those
   hit paths beat the reload-heavy baseline.

5. If the target path is fragment-reuse-like:
   demote LDS staging from primary runtime action and focus on dispatch /
   metadata / premap scheduling instead.

6. Independent of LDS, start the no-payload pivot:
   MTP/transition-guided tile-order / cache-locality bench over the direct
   global-fragment path.
```

## Cache-Aware Tile-Order Pivot

The no-payload tile-order simulator is now implemented:

```text
module:  src/mtp_expert_prefetch/runtime/tile_order.py
script:  scripts/simulate_tile_order_cache.py
tests:   tests/test_runtime_tile_order.py
```

Supported inputs:

```text
synthetic locality traces
JSON tile-request traces
event-stall tensor caches with transition_scores / mtp_scores / target_mass
```

The first real-cache smoke used:

```text
cache:       outputs/reports/prefetch_shadow_512sample_mtp_extra/event_stall_tensor_cache_512sample.pt
examples:    512
window size: 64 token examples per layer window
topk:        target top8 experts
tiles/expert: 1
artifact:    outputs/reports/tile_order_cache/tile_order_cache_512sample_smoke.md
```

Key trace-level results:

```text
linear:
  reuse_distance_mean = 29.23
  LRU@8 = 0.391
  LRU@32 = 0.758
  tile_order_hit_rate = 0.414

B-tile/expert grouped:
  reuse_distance_mean = 20.19
  LRU@8 = 0.833
  LRU@32 = 0.833
  tile_order_hit_rate = 0.119

transition_hot_first:
  reuse_distance_mean = 25.36
  LRU@8 = 0.591
  LRU@32 = 0.798
  tile_order_hit_rate = 0.461

MTP+transition hot-first:
  reuse_distance_mean = 26.13
  LRU@8 = 0.549
  LRU@32 = 0.793
  tile_order_hit_rate = 0.489

utility_hot_first:
  reuse_distance_mean = 25.98
  LRU@8 = 0.557
  LRU@32 = 0.794
  tile_order_hit_rate = 0.491

transition_tile_grouped:
  reuse_distance_mean = 19.45
  LRU@8 = 0.833
  LRU@32 = 0.835
  tile_order_hit_rate = 0.461

MTP+transition_tile_grouped:
  reuse_distance_mean = 19.40
  LRU@8 = 0.833
  LRU@32 = 0.835
  tile_order_hit_rate = 0.489

utility_tile_grouped:
  reuse_distance_mean = 19.41
  LRU@8 = 0.833
  LRU@32 = 0.835
  tile_order_hit_rate = 0.491

oracle_cache_aware:
  reuse_distance_mean = 19.19
  LRU@8 = 0.834
  LRU@32 = 0.836
  tile_order_hit_rate = 0.983
```

Interpretation:

```text
Pure B-tile grouping maximizes small-cache locality but loses hot-first order.
Transition/MTP/utility hot-first improves tile-order hit rate while preserving
part of the locality gain over linear order.

The hybrid tile-grouped policies are the current best non-oracle candidates:
they keep the locality of B-tile grouping while ordering tile groups by
transition/MTP/utility score. `utility_tile_grouped` keeps LRU@8 near `0.833`
and raises tile-order hit rate from `0.119` to `0.491`.

This validates the pivot as a schedulability question:
  choose between locality-first and hot-first tile visitation,
  then measure the selected orders in a direct/global-fragment consumer.
```

Current claim boundary:

```text
This simulator does not claim kernel speedup. It filters tile-order policies
before HIP/rocWMMA timing. LDS payload staging remains a gated/future branch.
```

Direct/global-fragment timing smoke:

```text
bench:    microbench/tile_order_cache/tile_order_cache_bench.hip
runner:   scripts/run_tile_order_cache_bench.py
artifact: outputs/reports/tile_order_cache/tile_order_cache_bench_512sample_2gpu_tile1024_flush16m.json
input:    same 512-cache tile multiset, top8 target experts, tiles/expert=1
kernel:   direct global B-tile consume, no LDS payload staging
stress:   tile_elems=1024, cache_flush_elems=16M, tiles_per_cta=32
devices:  GPU0 W7900, GPU1 W7900 Dual Slot
```

Timing rows:

```text
GPU0:
  linear               0.2895 ms  speedup 1.000x
  utility_hot_first    0.2908 ms  speedup 0.996x
  B-tile grouped       0.2716 ms  speedup 1.066x
  utility_tile_grouped 0.2679 ms  speedup 1.081x
  oracle_cache_aware   0.2779 ms  speedup 1.042x

GPU1:
  linear               0.3054 ms  speedup 1.000x
  utility_hot_first    0.3073 ms  speedup 0.994x
  B-tile grouped       0.2769 ms  speedup 1.103x
  utility_tile_grouped 0.2779 ms  speedup 1.099x
  oracle_cache_aware   0.2719 ms  speedup 1.123x
```

Interpretation:

```text
The direct/global consumer confirms the simulator's same-hotness ablation:
utility_hot_first improves hot-order but hurts locality and does not improve
timing. Grouped policies are faster under cache-flush stress.

utility_tile_grouped keeps the same order_hit as utility_hot_first while
recovering B-tile locality. It is fastest on GPU0 and effectively tied with
B-tile grouping on GPU1, while preserving much higher hot-order signal.
```

Claim boundary:

```text
This is still a microbench, not a full grouped-GEMM kernel result. The next
gate is a stability sweep over tile_elems / tiles_per_cta / cache flush /
process repeats, then a persistent grouped scheduler prototype only if the
timing advantage is stable.
```

Stability sweep:

```text
artifact: outputs/reports/tile_order_cache/tile_order_cache_bench_512sample_stability_2gpu.json
summary:  outputs/reports/tile_order_cache/tile_order_cache_bench_512sample_stability_2gpu_summary.md
devices:  GPU0 W7900, GPU1 W7900 Dual Slot
repeat:   5 process-level runs per policy/config
tiles:    tile_elems = 512 / 1024
flush:    0 / 16M
```

Median speedup of `utility_tile_grouped` vs `linear`:

```text
GPU0 tile512  flush0:   1.058x
GPU0 tile512  flush16M: 1.079x
GPU0 tile1024 flush0:   1.106x
GPU0 tile1024 flush16M: 1.102x

GPU1 tile512  flush0:   1.188x
GPU1 tile512  flush16M: 1.036x
GPU1 tile1024 flush0:   1.129x
GPU1 tile1024 flush16M: 1.118x
```

Same-hotness ablation:

```text
utility_hot_first and utility_tile_grouped have the same tile_order_hit_rate
on this trace: 0.491.

utility_hot_first:
  LRU@8 = 0.557
  timing is near linear or worse in most configs

utility_tile_grouped:
  LRU@8 = 0.833
  median speedup vs utility_hot_first ranges from about 1.04x to 1.14x
```

Same-locality ablation:

```text
B-tile grouped and utility_tile_grouped both preserve LRU@8 ~= 0.833.

B-tile grouped:
  tile_order_hit_rate = 0.119

utility_tile_grouped:
  tile_order_hit_rate = 0.491

Timing is near B-tile grouped while preserving much higher hot-order signal.
```

Interpretation:

```text
The stable result is not "hot-first is faster"; pure hot-first is not enough.
The stable result is that utility should rank B-tile groups, while execution
keeps each B tile contiguous. This preserves cache locality and retains the
MTP/transition utility signal.
```

Runtime descriptor-order action:

```text
module:  src/mtp_expert_prefetch/runtime/descriptor_order.py
script:  scripts/simulate_descriptor_order.py
schema:  ShadowSummaryEvent descriptor_order_* fields
```

The descriptor-order action is explicitly safe:

```text
same descriptor multiset
same true router output
same candidate membership
different descriptor / tile visitation order only
```

New shadow summary fields:

```text
descriptor_order_policy
descriptor_order_build_us
descriptor_tile_multiset_hash
descriptor_order_hash
descriptor_order_metrics
```

Smoke over existing premap descriptors:

```text
input:    outputs/reports/prefetch_shadow_256sample_mtp_extra/descriptors_extra4.jsonl
artifact: outputs/reports/tile_order_cache/descriptor_order_extra4_smoke.md
descriptors: 306,249
```

Result boundary:

```text
This smoke validates runtime action semantics and hash/counter reporting.
It is not a locality claim because the current premap descriptor JSONL is
sample/layer deduplicated. It is not a token/row-level grouped-GEMM tile stream.

The locality/timing claim should remain tied to the tensor-cache tile stream
and the direct/global-fragment timing bench until a row-level runtime descriptor
stream is available.
```

Engineering implication:

```text
Python prototype order_build_us on 306k descriptors is hundreds of ms, so it is
not the intended runtime implementation. The real runtime path needs bucketed
grouping / partial sort / descriptor patching in C++ or device-side code.
The Python action is for shadow validation and counter semantics.
```

Token/row-level tile stream bridge:

```text
module:  src/mtp_expert_prefetch/runtime/tile_stream.py
script:  scripts/export_tile_stream_descriptors.py
inputs:  event-stall tensor cache
outputs: token/row-level TileRequest JSONL
```

This closes the descriptor-order input gap:

```text
tensor cache -> token/row tile stream JSONL
same JSONL -> trace-level tile-order simulator
same JSONL -> direct/global-fragment timing bench
```

512-sample smoke:

```text
input:    outputs/reports/prefetch_shadow_512sample_mtp_extra/event_stall_tensor_cache_512sample.pt
jsonl:    outputs/reports/tile_order_cache/tile_stream_512sample_top8.jsonl
summary:  outputs/reports/tile_order_cache/tile_stream_512sample_top8_summary.md
requests: 163,840
windows:  320
unique B tiles: 256
```

Replay from JSONL matches the tensor-cache export diagnostics:

```text
linear:
  LRU@8 = 0.391
  order_hit = 0.414

B-tile grouped:
  LRU@8 = 0.833
  order_hit = 0.119

utility_hot_first:
  LRU@8 = 0.557
  order_hit = 0.491

utility_tile_grouped:
  LRU@8 = 0.833
  order_hit = 0.491
```

Small GPU bench smoke from the same JSONL:

```text
artifact: outputs/reports/tile_order_cache/tile_stream_512sample_top8_bench_smoke.json
device:   GPU0
policies: linear vs utility_tile_grouped
tile_elems: 256
iters: 5
result: utility_tile_grouped speedup_median_vs_linear ~= 1.005x
```

Boundary:

```text
This is a row-level stream bridge and semantic replay check, not a new
performance claim. The stronger timing evidence remains the prior stability
sweep. The important engineering step is that runtime descriptor_order and
the GPU timing bench can now consume the same row-level tile descriptor format.
```

Descriptor-order shadow summary over token/row streams:

```text
module:  order_tile_request_stream(...)
schema:  ShadowSummaryEvent descriptor_tile_request_count / unique_b_tiles /
         same_multiset / order_changed
script:  scripts/simulate_tile_stream_descriptor_order.py
```

512-sample row-stream shadow smoke:

```text
artifact: outputs/reports/tile_order_cache/tile_stream_descriptor_order_512sample_top8.md
shadow:   outputs/reports/tile_order_cache/tile_stream_descriptor_order_512sample_top8.shadow.jsonl
```

Key rows:

```text
linear:
  build_us median ~= 7.8ms
  LRU@8 = 0.391
  order_hit = 0.414
  same_multiset = true
  order_changed = false

utility_tile_grouped:
  build_us median ~= 82.6ms in Python
  LRU@8 = 0.833
  order_hit = 0.491
  same_multiset = true
  order_changed = true
```

Order-build overhead Pareto:

```text
script:  scripts/summarize_tile_order_overhead_pareto.py
artifact: outputs/reports/tile_order_cache/tile_stream_top8_overhead_pareto_stability.md
```

Current conclusion:

```text
The Python prototype is far too expensive for runtime descriptor ordering:
order_build_us is tens of milliseconds on the 163k-row stream, while measured
kernel savings in the direct/global-fragment bench are tens of microseconds.

This does not invalidate descriptor_order as a runtime action. It fixes the
next implementation requirement: real runtime ordering must use bucketed
group-by-tile / partial sort / precomputed group order in C++ or device-side
code. The Python path is only for shadow semantics and offline analysis.
```

Bucketed descriptor-order builder:

```text
policies:
  utility_tile_grouped_bucket
  utility_tile_grouped_top16
  utility_tile_grouped_top32

microbench:
  microbench/tile_order_cache/descriptor_order_builder_bench.cpp
script:
  scripts/run_descriptor_order_builder_bench.py
```

Python bucket prototype on the 163,840-row stream:

```text
utility_tile_grouped:        ~= 90.6ms
utility_tile_grouped_bucket: ~= 54.7ms
utility_tile_grouped_top16:  ~= 56.6ms
utility_tile_grouped_top32:  ~= 56.7ms
```

This preserves the useful ordering metrics:

```text
utility_tile_grouped_bucket:
  LRU@8 = 0.833
  order_hit = 0.491
  same_multiset = true
```

C++ preallocated bucket builder:

```text
artifact: outputs/reports/tile_order_cache/descriptor_order_builder_cpp_512sample_top8.md

utility_tile_grouped_bucket:
  total build_us median ~= 2.02ms for 163,840 rows / 320 windows
  normalized ~= 6.30us per window
  Python prototype ~= 55ms

utility_tile_grouped_top16/top32:
  total build_us median ~= 2.32ms / 2.36ms
```

Net overhead against the current direct/global-fragment timing bench:

```text
artifact: outputs/reports/tile_order_cache/descriptor_order_builder_cpp_overhead_pareto_smoke.md

utility_tile_grouped_bucket:
  kernel_saved_us ~= 27.5us
  cpp_build_us ~= 2015us
  net_saved_us ~= -1988us
```

Current interpretation:

```text
C++ bucketed grouping proves the algorithmic direction is much better than
Python object sorting, but still not profitable against the current tiny
direct/global-fragment bench envelope.

The per-window cost is now single-digit microseconds, so the remaining question
is whether the real runtime granularity/kernel saved envelope is per large
batch/layer, per window, or can reuse cached permutations. Descriptor_order
should remain shadow/precomputed until a net-positive implementation is shown.
```

Descriptor-order permutation cache replay:

```text
script:   scripts/analyze_descriptor_order_cache_replay.py
artifact: outputs/reports/tile_order_cache/descriptor_order_cache_replay_512sample_top8.md
```

Strict cache keys:

```text
exact_multiset:
  hit_rate = 0.0
  unique_keys = 320 / 320 windows

tile_set:
  hit_rate = 0.0
  unique_keys = 320 / 320 windows
```

Interpretation:

```text
Full permutation cache and same-active-set group-order cache do not repeat on
this 512-sample row stream. They cannot amortize descriptor-order build cost.
```

Heuristic key:

```text
layer_only:
  hit_rate = 0.875
  unique_keys = 40
  reuse_count = 8 per layer
  amortized builder ~= 0.79-0.92us/window before lookup/apply
```

Boundary:

```text
layer_only is not a same-multiset permutation cache. It is only a heuristic
layer-prior group-order cache. It preserves execution correctness because it
can still order the current descriptor multiset, but it may lose the utility
ranking value and must be evaluated as a separate policy.
```

Descriptor-order cache hit-path microbench:

```text
script:   scripts/run_descriptor_order_cache_hit_bench.py
artifact: outputs/reports/tile_order_cache/descriptor_order_cache_hit_bench_512sample_top8.md
```

CPU lookup path:

```text
exact_multiset warm lookup:
  ~= 8.85us over 320 keys, ~= 27.6ns/key

tile_set warm lookup:
  ~= 9.18us over 320 keys, ~= 28.7ns/key

layer_only warm lookup:
  ~= 2.13us over 320 keys, ~= 6.7ns/key
```

Current conclusion:

```text
Lookup cost is small. The blocker is reuse, not lookup. Strict safe cache keys
do not repeat in this trace; only heuristic layer-level reuse repeats.
Next gate is to evaluate layer-prior / cached group-order policies directly
against reuse/order-hit/timing, instead of treating them as exact permutation
caches.
```

Layer-prior tile-group ordering:

```text
core functions:
  src/mtp_expert_prefetch/runtime/tile_order.py

scripts:
  scripts/build_layer_prior_tile_order.py
  scripts/evaluate_layer_prior_tile_order.py

artifacts:
  outputs/reports/tile_order_cache/tile_stream_512sample_top8_calibration.jsonl
  outputs/reports/tile_order_cache/tile_stream_512sample_top8_heldout.jsonl
  outputs/reports/tile_order_cache/layer_prior_frequency_384calib.json
  outputs/reports/tile_order_cache/layer_prior_utility_384calib.json
  outputs/reports/tile_order_cache/layer_prior_weighted_utility_384calib.json
  outputs/reports/tile_order_cache/layer_prior_tile_order_heldout.md
```

Split:

```text
calibration:
  384 examples
  122,880 token-row TileRequest records
  240 windows

heldout:
  128 examples
  40,960 token-row TileRequest records
  80 windows
```

Heldout trace-level result:

```text
linear:
  LRU@8 = 0.4437
  order_hit = 0.4641

B-tile grouped:
  LRU@8 = 0.8439
  order_hit = 0.1234

utility_tile_grouped_bucket:
  LRU@8 = 0.8441
  order_hit = 0.5375

layer_prior_frequency:
  LRU@8 = 0.8442
  order_hit = 0.5766

layer_prior_utility:
  LRU@8 = 0.8442
  order_hit = 0.5234
```

Interpretation:

```text
Exact descriptor permutation caching is not viable on this trace, but a
calibrated per-layer group-order prior is a real policy.

Frequency prior is currently the strongest heldout layer-prior variant:
it preserves B-tile locality and improves hot group order beyond dynamic
utility_tile_grouped on this split.

The policy remains safe: it preserves the current descriptor multiset and only
changes tile-group visitation order. It is not an expert predictor and does
not alter true router membership.
```

Heldout direct/global-fragment timing sweep:

```text
artifact:
  outputs/reports/tile_order_cache/layer_prior_tile_order_heldout_bench_sweep.json

tiny/no-flush envelope:
  tile_elems=256, cache_flush=0
  linear remains fastest on this bench shape.
  Do not claim timing benefit here.

larger tile envelope:
  tile_elems=1024, cache_flush=0
  B-tile grouped speedup ~= 1.16x on both W7900 devices.
  layer_prior_frequency speedup ~= 1.15x on both W7900 devices.
  utility_tile_grouped_bucket speedup ~= 1.14x on both W7900 devices.

cache-pressure envelope:
  tile_elems=1024, cache_flush=16M
  B-tile grouped speedup ~= 1.05-1.11x.
  layer_prior_frequency speedup ~= 1.03-1.07x.
```

Current descriptor-order conclusion:

```text
layer_prior_frequency is the best runtime-feasible descriptor-order candidate
so far: it has no exact multiset-cache dependency, uses a small per-layer prior,
preserves locality, and improves hot group order.

Dynamic utility_tile_grouped remains a diagnostic/upper policy because dynamic
build cost is still too high for the current timing envelope.

Next gate:
  implement a C++/two-level layer-prior builder path and online shadow counters
  for descriptor_order_policy=layer_prior_frequency.
```

C++ two-level layer-prior builder:

```text
code:
  microbench/tile_order_cache/descriptor_order_builder_bench.cpp
  scripts/run_descriptor_order_builder_bench.py

mode:
  layer_prior_plan

representation:
  present/counts/offsets
  filtered group_order from prior_order[layer]
  optional top-H current-utility override
  no full materialized descriptor reorder in the plan mode
```

Heldout builder result:

```text
artifact:
  outputs/reports/tile_order_cache/layer_prior_descriptor_order_builder_heldout.md

utility_tile_grouped_bucket:
  ~= 365.5us total
  ~= 4.57us/window
  LRU@8 = 0.8441
  order_hit = 0.5375

layer_prior_frequency:
  ~= 332.8us total
  ~= 4.16us/window
  LRU@8 = 0.8442
  order_hit = 0.5766

layer_prior_utility:
  ~= 317.9us total
  ~= 3.97us/window
  LRU@8 = 0.8442
  order_hit = 0.5234
```

Materialization control:

```text
artifact:
  outputs/reports/tile_order_cache/layer_prior_descriptor_order_builder_materialized_heldout.md

layer_prior_frequency plan:
  ~= 315.2us total
  ~= 3.94us/window

layer_prior_frequency materialized:
  ~= 347.9us total
  ~= 4.35us/window
```

Interpretation:

```text
The two-level representation is the right runtime shape: materializing a full
reordered descriptor array is measurably slower.

However, the current CPU-side builder is still too expensive for the tiny
direct/global-fragment timing envelope.
```

Overhead Pareto:

```text
artifact:
  outputs/reports/tile_order_cache/layer_prior_tile_order_overhead_pareto_heldout.md

tile_elems=1024, no flush:
  layer_prior_frequency kernel_saved_us ~= 8us per heldout stream
  layer_prior_frequency build_us ~= 333us per heldout stream
  net_saved_us remains negative

tile_elems=1024, cache_flush=16M:
  kernel_saved_us ~= 4-10us depending on device
  build_us remains ~= 333us
  net_saved_us remains negative
```

Current descriptor-order boundary:

```text
layer_prior_frequency is still the best semantic policy for descriptor_order:
it preserves B-tile locality and improves order_hit on heldout.

But it is not yet a per-window CPU critical-path action under the current
direct/global-fragment microbench envelope.

Use it next as:
  online shadow metric/policy,
  precomputed descriptor group order,
  or a candidate for a lower-overhead integrated grouped-kernel path.
```

Descriptor-order online shadow counters:

```text
code:
  src/mtp_expert_prefetch/runtime/shadow_log.py
  src/mtp_expert_prefetch/runtime/online_shadow.py
  src/mtp_expert_prefetch/runtime/shadow_controller.py
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py

new flattened summary fields:
  descriptor_order_prior_id
  descriptor_order_prior_hash
  descriptor_order_lru_at_8
  descriptor_order_lru_at_16
  descriptor_order_hit_rate
  descriptor_reuse_distance_mean
  descriptor_unique_tiles_per_window_mean

aggregate fields:
  descriptor_order_lru_at_8_mean
  descriptor_order_lru_at_16_mean
  descriptor_order_hit_rate_mean
  descriptor_reuse_distance_mean
  descriptor_unique_tiles_per_window_mean
```

Runtime hook boundary:

```text
write_active_runtime_shadow_descriptor_order_summary(...)

This writes descriptor_order counters through the active RuntimeShadowController.
It does not cache router masks for outcome join because descriptor_order is an
order-only action over the current descriptor multiset.
```

Smoke:

```text
script:
  scripts/simulate_tile_stream_descriptor_order.py

artifact:
  outputs/reports/tile_order_cache/layer_prior_descriptor_order_shadow_smoke.jsonl

records:
  linear
  b_tile_grouped
  layer_prior_frequency

layer_prior_frequency shadow fields:
  descriptor_order_prior_hash = 0371...
  descriptor_order_lru_at_8 = 0.8442
  descriptor_order_hit_rate = 0.5766
  descriptor_reuse_distance_mean = 20.5402
```

Current next gate:

```text
Attach a real vLLM/runtime producer that builds current-router token-row tile
requests, calls descriptor_order_policy=layer_prior_frequency, and writes only
the shadow counters. Do not change grouped-GEMM execution order yet.
```

Online vLLM descriptor-order producer:

```text
code:
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py

runtime_shadow options:
  emit_descriptor_order_summaries
  descriptor_order_prior_path
  descriptor_order_prior_id
  descriptor_order_tiles_per_expert
  descriptor_order_cache_sizes
  descriptor_order_top_k
  descriptor_order_top_utility_override

behavior:
  after a true-router top-k call, expand the current layer's token/top-k rows
  into a current-router TileRequest stream;
  apply the calibrated layer_prior_frequency order;
  write a descriptor_order_shadow summary with prior hash, multiset/order hash,
  LRU/order-hit/reuse metrics, and overhead fields.

boundary:
  this is shadow-only;
  it does not alter grouped-GEMM execution order;
  it does not write ready masks;
  it does not participate in action-summary/outcome joining.

fallback:
  missing prior or missing layer order is a no-op, not a runtime failure.
```

Current next gate:

```text
Run an online vLLM shadow-only smoke with the calibrated layer-prior artifact,
then compare online descriptor_order LRU/order-hit/reuse metrics with the 512
heldout tensor-cache replay before enabling any real descriptor visitation
order changes.
```

Online vLLM descriptor-order smoke results:

```text
code/config changes:
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py
    - vLLM trace now supports trace.start_sample.
    - descriptor-order TileRequest streams can use
      descriptor_order_token_window_size=64, matching the tensor-cache
      heldout convention of 64 token examples x top8 = 512 tile requests.
  scripts/replay_vllm_descriptor_order_shadow.py
    - rebuilds token/row TileRequest streams from sample_*.pt vLLM traces;
    - applies the same layer-prior/order metrics as heldout replay;
    - can run an internal vLLM calibration/heldout split.

real vLLM shadow-only runs:
  smoke8:
    configs/trace/router_mtp_trace_aya_dataset_gptq_vllm_descriptor_order_shadow_smoke8.yaml
    data/traces/aya_dataset_smoke_gptq_vllm_descriptor_order_shadow_smoke8/

  smoke32:
    configs/trace/router_mtp_trace_aya_dataset_gptq_vllm_descriptor_order_shadow_smoke32.yaml
    data/traces/aya_dataset_smoke_gptq_vllm_descriptor_order_shadow_smoke32/

  heldout with vLLM-calibrated prior:
    configs/trace/router_mtp_trace_aya_dataset_gptq_vllm_descriptor_order_shadow_smoke32_heldout_vllm_prior.yaml
    data/traces/aya_dataset_smoke_gptq_vllm_descriptor_order_shadow_smoke32_heldout_vllm_prior/

  smoke64:
    configs/trace/router_mtp_trace_aya_dataset_gptq_vllm_descriptor_order_shadow_smoke64.yaml
    data/traces/aya_dataset_smoke_gptq_vllm_descriptor_order_shadow_smoke64/
```

Key reports:

```text
outputs/reports/tile_order_cache/vllm_descriptor_order_shadow_smoke8_replay.md
outputs/reports/tile_order_cache/vllm_descriptor_order_shadow_smoke32_replay.md
outputs/reports/tile_order_cache/vllm_descriptor_order_shadow_smoke32_heldout_vllm_prior_replay.md
outputs/reports/tile_order_cache/vllm_smoke32_layer_prior_frequency_24calib.json
outputs/reports/tile_order_cache/vllm_descriptor_order_shadow_smoke64_replay.md
outputs/reports/tile_order_cache/vllm_smoke64_layer_prior_frequency_48calib.json
```

Online producer validation:

```text
smoke32, old tensor-cache prior:
  descriptor summaries = 1280
  online mean LRU@8 / LRU@16 = 0.9358 / 0.9374
  online mean order_hit = 0.3505
  online mean reuse_mean = 0.4423
  decision_us mean = 2724.9
  candidate_construction_us mean = 1564.5
  descriptor_order_build_us mean = 237.0

heldout-only, vLLM-calibrated prior:
  descriptor summaries = 320
  online mean LRU@8 / LRU@16 = 0.9454 / 0.9455
  online mean order_hit = 0.9012
  online mean reuse_mean = 0.4569
  decision_us mean = 3027.5
  candidate_construction_us mean = 1767.4
  descriptor_order_build_us mean = 242.4
```

512-window replay validation:

```text
smoke32 with old tensor-cache layer_prior_frequency:
  requests = 1,002,880
  windows = 1,960

  linear:
    LRU@8 / LRU@16 = 0.7143 / 0.9397
    reuse_mean = 8.9340
    order_hit = 0.7536

  utility_tile_grouped_bucket:
    LRU@8 / LRU@16 = 0.9434 / 0.9457
    reuse_mean = 2.3124
    order_hit = 0.5763

  old layer_prior_frequency:
    LRU@8 / LRU@16 = 0.9433 / 0.9441
    reuse_mean = 2.3945
    order_hit = 0.3037

This means the tensor-cache calibrated prior does not transfer cleanly to the
current vLLM/GPTQ router trace. The hook is valid, but the prior artifact is
backend/trace dependent.

vLLM internal 24/8 calibration split:
  vLLM-calibrated layer_prior_frequency on heldout samples 24-31:
    LRU@8 / LRU@16 = 0.9494 / 0.9526
    reuse_mean = 2.2661
    order_hit = 0.9016

  dynamic utility_tile_grouped_bucket on the same heldout:
    LRU@8 / LRU@16 = 0.9495 / 0.9531
    reuse_mean = 2.1984
    order_hit = 0.6350

smoke64 scale check:
  requests = 1,844,160
  windows = 3,640

  old tensor-cache layer_prior_frequency:
    LRU@8 / LRU@16 = 0.9404 / 0.9413
    reuse_mean = 2.5393
    order_hit = 0.2977

  utility_tile_grouped_bucket:
    LRU@8 / LRU@16 = 0.9405 / 0.9426
    reuse_mean = 2.4463
    order_hit = 0.5608

  vLLM internal 48/16 calibration split:
    vLLM-calibrated layer_prior_frequency on heldout samples 48-63:
      LRU@8 / LRU@16 = 0.9368 / 0.9378
      reuse_mean = 3.2646
      order_hit = 0.8689

    utility_tile_grouped_bucket on the same heldout:
      LRU@8 / LRU@16 = 0.9368 / 0.9381
      reuse_mean = 3.1584
      order_hit = 0.5207
```

Conclusion:

```text
The real vLLM shadow-only descriptor_order producer is wired and observable.

The online counters now use token-window semantics compatible with heldout
tile streams, and overhead fields are populated.

A layer-prior descriptor_order policy must be calibrated on the same router
trace/backend family. Reusing the tensor-cache prior on GPTQ/vLLM preserves
locality but loses group-order hit. Recalibrating on vLLM traces restores strong
heldout order_hit while keeping the same safety boundary:
same current true-router multiset, order-only changes, no ready-mask effects.

Next gate:
  lower descriptor_order overhead via a two-level C++/runtime builder
  or keep descriptor_order as a shadow/precomputed action until the order-build
  path is below the measured kernel saved envelope.
```

C++ builder overhead on real vLLM streams:

```text
scripts:
  scripts/replay_vllm_descriptor_order_shadow.py
    now supports --output-jsonl for exporting the vLLM TileRequest stream.

  scripts/run_descriptor_order_builder_bench.py
    consumes the same vLLM JSONL stream and measures C++ builder cost.

artifacts:
  outputs/reports/tile_order_cache/vllm_smoke64_tile_stream_top8.jsonl
  outputs/reports/tile_order_cache/vllm_smoke64_descriptor_order_builder_bench.md
  outputs/reports/tile_order_cache/vllm_smoke32_heldout_tile_stream_top8.jsonl
  outputs/reports/tile_order_cache/vllm_smoke32_heldout_descriptor_order_builder_bench.md
```

Results:

```text
smoke64 full stream:
  requests = 1,844,160
  layer_prior_frequency plan:
    cpp_build_us_median = 8,821.9 total
    cpp_us/window = 2.42
    python_build_us ~= 468,474
    LRU@8 / LRU@16 = 0.9404 / 0.9423
    order_hit = 0.8854

  layer_prior_frequency materialized:
    cpp_build_us_median = 10,366.6 total
    cpp_us/window = 2.85

smoke32 heldout-only stream:
  requests = 283,520
  windows = 560
  layer_prior_frequency plan:
    cpp_build_us_median = 1,233.1 total
    cpp_us/window = 2.20
    python_build_us ~= 51,605
    LRU@8 / LRU@16 = 0.9494 / 0.9526
    order_hit = 0.9016

  layer_prior_frequency materialized:
    cpp_build_us_median = 1,470.8 total
    cpp_us/window = 2.63
```

Updated overhead conclusion:

```text
The Python online descriptor_order producer is still too expensive for the
decode critical path.

However, the C++ two-level layer_prior_plan is now in the low-microsecond
per-window range on real vLLM TileRequest streams. This revives descriptor_order
as a runtime-feasible action if the grouped-kernel consumer can use a
two-level group-order plan directly, avoiding full Python materialization.

Next implementation gate:
  replace the Python shadow producer's object-level TileRequest ordering with
  a lower-overhead plan builder or expose a runtime C++ builder path for
  descriptor_order summaries.
```

Follow-up overhead reduction:

```text
runtime change:
  common online path now uses tensor/rank-map layer_prior_plan when:
    tiles_per_expert = 1
    top_utility_override = 0

  runtime_shadow option:
    descriptor_order_metrics_mode: compact

compact mode:
  keeps LRU@K, order_hit, unique tile stats, run length, hashes, request count
  skips full reuse-distance distribution

TRY/AWQ 1-sample online smoke after compact mode:
  summaries = 40
  outcomes = 5,080

  LRU@8 mean = 0.8593
  LRU@16 mean = 0.8593
  order_hit mean = 0.6203
  reuse_distance = skipped in compact mode

  candidate_construction_us mean = 4.16
  descriptor_order_build_us mean = 495.38
  decision_us mean = 1,452.38
  counter_update_us mean = 952.84

previous full-metric online smoke:
  descriptor_order_build_us mean = 881.75
  decision_us mean = 3,402.53
  counter_update_us mean = 2,516.30

interpretation:
  tensor/rank-map planning reduces the plan-build cost, and compact metrics
  remove a large part of online shadow overhead while preserving the primary
  locality/order observability. Full reuse-distance accounting should remain
  an offline replay diagnostic or sampled debug mode.
```

AWQ compact descriptor_order scale-up:

```text
configs:
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_smoke8.yaml
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_smoke32.yaml

environment:
  TRY conda env
  HIP_VISIBLE_DEVICES=0 for smoke8
  HIP_VISIBLE_DEVICES=1 for smoke32

outputs:
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_smoke8/runtime_shadow.jsonl
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_smoke32/runtime_shadow.jsonl
```

Correctness / scale:

```text
smoke8:
  samples = 8
  token count range = 35..127
  outcomes = 29,760 = sum(num_tokens) * 40
  descriptor_order summaries = 320 = 8 * 40
  runtime_shadow size = 22MB

smoke32:
  samples = 32
  token count range = 35..127
  outcomes = 125,360 = sum(num_tokens) * 40
  descriptor_order summaries = 1,280 = 32 * 40
  runtime_shadow size = 90MB
```

Compact overhead distribution:

```text
smoke8:
  candidate_construction_us:
    mean 4.72 / p50 4.39 / p90 5.29 / p95 5.85 / p99 8.16 / max 21.03
  descriptor_order_build_us:
    mean 478.73 / p50 478.08 / p90 564.33 / p95 585.59 / p99 630.44 / max 744.96
  decision_us:
    mean 1248.67 / p50 1360.25 / p90 1575.90 / p95 1626.91 / p99 1710.56 / max 2190.96
  counter_update_us:
    mean 765.22 / p50 833.06 / p90 1011.52 / p95 1037.89 / p99 1100.92 / max 1441.13

smoke32:
  candidate_construction_us:
    mean 4.13 / p50 4.12 / p90 4.46 / p95 4.60 / p99 5.18 / max 19.41
  descriptor_order_build_us:
    mean 452.57 / p50 448.48 / p90 527.73 / p95 558.32 / p99 616.71 / max 893.86
  decision_us:
    mean 1210.03 / p50 1253.86 / p90 1485.60 / p95 1535.35 / p99 1687.79 / max 2287.63
  counter_update_us:
    mean 753.33 / p50 825.15 / p90 970.96 / p95 992.39 / p99 1091.56 / max 1411.27
```

Compact locality/order distribution:

```text
smoke8:
  LRU@8 mean 0.8153 / p50 0.8258 / p95 0.8937 / p99 0.9120
  LRU@16 mean 0.8153 / p50 0.8258 / p95 0.8937 / p99 0.9120
  order_hit mean 0.4670 / p50 0.5000 / p95 0.7500 / p99 0.8125
  unique_tiles_total mean 97.03 / p50 93.5 / p95 156.0 / p99 185.0

smoke32:
  LRU@8 mean 0.8143 / p50 0.8235 / p95 0.8760 / p99 0.8978
  LRU@16 mean 0.8143 / p50 0.8237 / p95 0.8760 / p99 0.8978
  order_hit mean 0.4137 / p50 0.4375 / p95 0.7500 / p99 0.8125
  unique_tiles_total mean 102.83 / p50 98.0 / p95 161.0 / p99 191.4
```

Scale-up conclusion:

```text
AWQ online compact descriptor_order shadow is stable at 8/32 sample scale.
Summary/outcome counts match manifest token counts exactly, and same_multiset /
order_changed are true for every descriptor_order summary.

Overhead is stable but still too high for a synchronous critical-path runtime
action: p95 decision_us is ~1.54ms and p99 is ~1.69ms on smoke32. This is
acceptable for online shadow observability, not yet for production descriptor
visitation changes.

Next gate:
  compare no-shadow vs compact-shadow end-to-end wall time/TPOT, then add an
  even cheaper metrics_mode=none for long online runs where only hashes/counts
  and build_us are needed.
```

AWQ no-shadow vs compact-shadow end-to-end comparison:

```text
environment:
  conda env: TRY
  gpu: HIP_VISIBLE_DEVICES=1
  model: qwen3_6_35b_a3b_awq_4bit
  recorder: enabled in both no-shadow and compact-shadow
  max_tokens: 1

configs added:
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_no_shadow_smoke8.yaml
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_no_shadow_smoke32.yaml

instrumentation added:
  output_dir/performance_summary.json now records:
    llm_init_wall_seconds
    generate_wall_seconds
    trace_write_wall_seconds
    total_trace_wall_seconds
    generate_seconds_per_requested_output_token
    end_to_end_seconds_per_requested_output_token
```

Raw external wall-time:

```text
8 samples:
  no_shadow       74.08s
  compact_shadow  91.06s

32 samples repeat1:
  no_shadow       66.04s
  compact_shadow  72.97s

32 samples repeat2, reverse order:
  compact_shadow  69.89s
  no_shadow       80.62s

32 samples repeat3, with performance_summary:
  no_shadow       63.99s
  compact_shadow  69.88s
```

Interpretation:

```text
Raw external wall time is too noisy for small AWQ runs because vLLM engine
construction and AWQ safetensors loading dominate the run (~43-56s). Repeat2
even reverses the raw ordering, so raw wall-time alone is not a reliable
shadow overhead estimate.
```

Instrumented 32-sample path-level timing:

```text
no_shadow:
  total_trace_wall_seconds = 60.83
  llm_init_wall_seconds    = 48.98
  generate_wall_seconds    = 3.76
  trace_write_wall_seconds = 0.93
  generate_s/output_token  = 0.118

compact_shadow:
  total_trace_wall_seconds = 66.72
  llm_init_wall_seconds    = 49.02
  generate_wall_seconds    = 9.56
  trace_write_wall_seconds = 0.90
  generate_s/output_token  = 0.299

delta:
  total_trace_wall_seconds = +5.90s
  generate_wall_seconds    = +5.80s
  generate_s/output_token  = +0.181s
  llm_init_wall_seconds    = +0.03s
```

Compact-shadow internal overhead, current 32-sample run:

```text
descriptor summaries = 1,280
outcomes             = 125,360
same_multiset        = 1,280 / 1,280
order_changed        = 1,280 / 1,280

candidate_construction_us:
  mean = 3.88, p95 = 4.32, p99 = 4.70

descriptor_order_build_us:
  mean = 413.94, p95 = 505.27, p99 = 558.97

decision_us:
  mean = 1,113.30, p95 = 1,428.99, p99 = 1,536.26

counter_update_us:
  mean = 695.49, p95 = 943.77, p99 = 989.08

LRU@8 mean      = 0.8143
LRU@16 mean     = 0.8143
order_hit mean  = 0.4137
```

Current conclusion:

```text
AWQ compact descriptor-order shadow has stable observability metrics and valid
same-multiset/order-changed semantics at 32 samples.

However, compact shadow still adds measurable generate-path overhead in Python:
~5.8s over 32 samples, or ~181ms per generated token in this tracing setup.
The cost is dominated by Python descriptor-order metric/counter work, not model
loading and not candidate construction.

Therefore compact mode remains suitable for diagnostic online shadow, but not
for a synchronous production critical path. The next optimization target is a
metrics_mode=none / minimal scalar mode, then a C++/two-level counter path if
we need lower-overhead long online runs.
```

Descriptor-order `metrics_mode=none`:

```text
implementation:
  src/mtp_expert_prefetch/runtime/descriptor_order.py
    supports metrics_mode=none in _evaluate_ordered_tile_id_windows(...)

semantics:
  keeps:
    descriptor_count
    tile_multiset_hash
    order_hash
    order_build_us
    request_count
    window_count
    unique_tiles_total

  skips heavy metrics:
    LRU@K
    tile_order_hit_rate
    reuse_distance
    consecutive run stats
    first_tiles payload

configs:
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_smoke8.yaml
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_smoke32.yaml
```

AWQ none-mode smoke8:

```text
command:
  HIP_VISIBLE_DEVICES=1 VLLM_ENABLE_V1_MULTIPROCESSING=0 \
    conda run -n TRY python scripts/trace_router_mtp_vllm.py \
    configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_smoke8.yaml

output:
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_none_smoke8/runtime_shadow.jsonl
  outputs/reports/awq_shadow_overhead/metrics_mode_none_smoke8.md

runtime_shadow rows = 30,080
outcomes            = 29,760
descriptor summaries = 320
same_multiset       = 320 / 320
order_changed       = 320 / 320
metrics_mode        = none

none-mode metrics:
  LRU@8 emitted       = 0 rows
  order_hit emitted   = 0 rows
  unique_b_tiles mean = 97.03

overhead comparison against compact smoke8:
  compact decision_us p50/p95/p99 = 1216.5 / 1516.9 / 1647.0
  none    decision_us p50/p95/p99 =  743.0 /  917.9 /  993.5

  compact counter_update_us p50/p95/p99 = 752.7 / 983.3 / 1060.8
  none    counter_update_us p50/p95/p99 = 304.6 / 423.2 /  431.5
```

Conclusion:

```text
metrics_mode=none behaves as intended: it preserves descriptor-order audit
semantics via hashes/counts/build_us while removing LRU/order-hit heavy
observability.

This reduces Python shadow overhead substantially:
  decision p50 drops by ~39%
  counter_update p50 drops by ~60%

None-mode is now the preferred long-run online shadow setting when locality
metrics are not needed on every sample. Compact remains the diagnostic mode for
periodic LRU/order-hit validation.
```

AWQ none-mode smoke32:

```text
output:
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_none_smoke32/runtime_shadow.jsonl
  outputs/reports/awq_shadow_overhead/metrics_mode_none_smoke32.md

runtime_shadow rows = 126,640
outcomes            = 125,360
descriptor summaries = 1,280
same_multiset       = 1,280 / 1,280
order_changed       = 1,280 / 1,280
metrics_mode        = none
```

32-sample path-level timing:

```text
no_shadow:
  total_trace_wall_seconds = 60.83
  llm_init_wall_seconds    = 48.98
  generate_wall_seconds    = 3.76
  generate_s/output_token  = 0.118

compact_shadow:
  total_trace_wall_seconds = 66.72
  llm_init_wall_seconds    = 49.02
  generate_wall_seconds    = 9.56
  generate_s/output_token  = 0.299

none_shadow:
  total_trace_wall_seconds = 65.05
  llm_init_wall_seconds    = 48.54
  generate_wall_seconds    = 8.48
  generate_s/output_token  = 0.265

deltas vs no_shadow:
  compact generate +5.80s, total +5.90s
  none    generate +4.72s, total +4.22s
```

32-sample descriptor-order overhead:

```text
compact:
  decision_us p50/p95/p99        = 1203.3 / 1429.0 / 1536.3
  counter_update_us p50/p95/p99  =  800.7 /  943.8 /  989.1
  descriptor_build_us p50/p95/p99 = 412.1 / 505.3 / 559.0
  LRU@8/order_hit rows           = 1280 / 1280

none:
  decision_us p50/p95/p99        =  712.2 /  847.8 /  928.3
  counter_update_us p50/p95/p99  =  315.5 /  355.8 /  394.4
  descriptor_build_us p50/p95/p99 = 405.6 / 494.9 / 549.5
  LRU@8/order_hit rows           = 0 / 0
```

Interpretation:

```text
metrics_mode=none scales cleanly from 8 to 32 samples: summary/outcome counts
remain aligned and p99 overhead does not worsen.

None mode reduces descriptor-order shadow CPU overhead versus compact:
  decision_us p50 drops from ~1203us to ~712us
  counter_update_us p50 drops from ~801us to ~316us

However, no-shadow vs none-shadow path-level timing still shows a measurable
generate-path cost (+4.72s over 32 samples). That remaining cost is mostly the
synchronous summary/controller/logging path, not LRU/order-hit metric
computation and not model loading.

Next optimization target:
  async/batched logger path or flat scalar buffer for none-mode summaries.
```

Runtime shadow summary/outcome attribution:

```text
implementation:
  RuntimeShadowController now supports:
    emit_summaries: bool = true
    emit_outcomes: bool = true

  This keeps default behavior unchanged while allowing controlled attribution:
    outcome_only  = emit_summaries=false, emit_outcomes=true
    summary_only  = emit_summaries=true,  emit_outcomes=false
    both          = emit_summaries=true,  emit_outcomes=true

configs:
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_shadow_outcome_only_smoke32.yaml
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_summary_only_smoke32.yaml

tests:
  RuntimeShadowController suppress-summary and suppress-outcome behavior is
  covered in tests/test_runtime_online_shadow.py.
```

AWQ 32-sample attribution:

```text
report:
  outputs/reports/awq_shadow_overhead/summary_outcome_attribution32.md

path-level generate time:
  no_shadow     = 3.76s
  outcome_only  = 7.50s  (+3.74s)
  summary_only  = 6.03s  (+2.27s)
  none_both     = 8.48s  (+4.72s)
  compact_both  = 9.56s  (+5.80s)

rows written:
  outcome_only:
    outcomes = 125,360
    summaries = 0

  summary_only:
    outcomes = 0
    descriptor summaries = 1,280

  none_both:
    outcomes = 125,360
    descriptor summaries = 1,280
```

Descriptor summary overhead, none mode:

```text
summary_only:
  decision_us p50/p95/p99 = 702.5 / 833.9 / 872.5
  counter_update_us p50/p95/p99 = 315.1 / 353.5 / 376.7
  descriptor_build_us p50/p95/p99 = 401.0 / 485.0 / 522.7

none_both:
  decision_us p50/p95/p99 = 712.2 / 847.8 / 928.3
  counter_update_us p50/p95/p99 = 315.5 / 355.8 / 394.4
  descriptor_build_us p50/p95/p99 = 405.6 / 494.9 / 549.5
```

Interpretation:

```text
The remaining none-shadow overhead is split across two synchronous Python paths:

1. outcome logging/controller path:
   outcome_only writes 125k outcome rows and accounts for most of the
   no-shadow gap (+3.74s generate).

2. descriptor summary path:
   summary_only writes only 1,280 descriptor summaries but still costs +2.27s,
   driven by Python summary construction, hash/order build, JSONL write, and
   controller/logger overhead.

none_both remains expensive because it still emits both outcome rows and
descriptor summaries synchronously.
```

Next gate:

```text
P0:
  add outcome_logging_mode = full | aggregate | off
  and make aggregate/off the default for long-run descriptor-order audit.

P0:
  add a batched/flat scalar writer for descriptor summaries:
    fixed schema rows
    no nested descriptor_order_metrics payload in none mode
    batch flush instead of flush_every=1 for long runs

P1:
  async writer / ring buffer once flat schema proves beneficial.
```

Runtime online descriptor-order fast producer:

```text
implementation:
  src/mtp_expert_prefetch/runtime/descriptor_order.py
    adds build_layer_prior_plan_report_from_router_topk(...)
    compact/two-level layer_prior_plan-style report builder
    avoids Python object-level TileRequest materialization in online shadow

  src/mtp_expert_prefetch/tracing/vllm_router_trace.py
    descriptor_order summary producer now calls the compact plan builder
    candidate_construction_us measures only tensor detach/copy overhead

  tests:
    tests/test_runtime_layer_prior_order.py verifies compact plan report hashes
    and metrics match the original TileRequest stream implementation.
```

AWQ/vLLM descriptor_order smoke environment:

```text
working env:
  conda env: TRY
  python: /home/husrcf/anaconda3/envs/TRY/bin/python
  torch: 2.11.0+rocm7.2
  transformers: 5.6.2
  vllm: 0.19.2rc1.dev213+g9558f4390

failed env notes:
  base is contaminated by in-progress flash-attn/kernel development.
  MCP imports vLLM after fixing libzstd search path, but current vLLM build
  rejects the original qwen3_5_moe AWQ architecture.
  AIAA has no vLLM installed.

command:
  HIP_VISIBLE_DEVICES=1 VLLM_ENABLE_V1_MULTIPROCESSING=0 \
    conda run -n TRY python scripts/trace_router_mtp_vllm.py \
    configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_smoke.yaml

outputs:
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_smoke/manifest.jsonl
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_smoke/runtime_shadow.jsonl
```

Online smoke result, 1 sample:

```text
manifest rows = 1
runtime_shadow rows = 5,120
  outcomes = 5,080
  descriptor_order summaries = 40

descriptor_order metrics across 40 layers:
  LRU@8 mean = 0.8593
  LRU@16 mean = 0.8593
  order_hit mean = 0.6203
  reuse_distance mean = 4.1123
  windows/layer = 2
  tile requests/layer = 1,016

fast-producer overhead:
  candidate_construction_us mean = 4.47
  descriptor_order_build_us mean = 881.75
  decision_us mean = 3,402.53

interpretation:
  object-level TileRequest construction is removed from the online producer.
  candidate construction is now low microseconds, but descriptor_order metric
  computation remains the dominant online shadow cost. This is acceptable for
  shadow validation; a real runtime action should use compact counters or the
  C++ two-level plan builder path rather than full Python metric evaluation.
```

Runtime shadow outcome logging modes:

```text
implementation:
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py
    adds shadow_outcome_logging_mode = full / aggregate / off
    aggregate writes one outcome_aggregate record per sample/layer router call
    off skips per-token outcome event construction entirely

  src/mtp_expert_prefetch/runtime/shadow_log.py
    adds ShadowOutcomeAggregateEvent and aggregate_shadow_events counters

  configs:
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_outcome_aggregate_smoke32.yaml
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_outcome_off_smoke32.yaml
```

AWQ 32-sample result:

```text
mode                         generate_s  TPOT_s   rows     summary  outcome  aggregate
no_shadow                    3.762       0.1176   0        0        0        0
none + full outcomes         8.478       0.2649   126640   1280     125360   0
none + aggregate outcomes    4.855       0.1517   2560     1280     0        1280
none + outcomes off          4.722       0.1476   1280     1280     0        0
```

Interpretation:

```text
per-token full outcome JSONL is the main remaining shadow overhead.
aggregate reduces rows by ~49x vs full-outcome none mode and cuts generate
overhead from +4.72s to +1.09s over no-shadow.

off is the lower bound for descriptor-order audit-only shadow: it keeps only
summary/hash/count/build_us rows and cuts generate overhead to +0.96s.

Descriptor summary internal overhead is almost unchanged across outcome modes,
so the next bottleneck is the descriptor summary path itself, not LRU/order-hit
or per-token outcome logging.
```

Descriptor-order count-only summary mode:

```text
implementation:
  src/mtp_expert_prefetch/runtime/descriptor_order.py
    adds descriptor_order_metrics_mode=count_only
    skips layer-prior ordering, tile_multiset_hash, and order_hash
    keeps request_count/window_count/unique_tiles_total/prior metadata only

  configs:
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_outcome_aggregate_smoke32.yaml
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_outcome_off_smoke32.yaml

  pyproject.toml:
    pytest default collection is restricted to tests/
    third_party/GPTQModel is no longer collected by plain pytest -q
```

AWQ 32-sample count-only result:

```text
mode                         generate_s  TPOT_s   rows   decision_p50  build_p50  counter_p50
no_shadow                    3.762       0.1176   0      -             -          -
none + aggregate outcomes    4.855       0.1517   2560   695.7us       390.9us    315.0us
none + outcomes off          4.722       0.1476   1280   701.0us       398.0us    318.1us
count_only + aggregate       4.065       0.1270   2560   74.4us        56.9us     14.2us
count_only + off             3.875       0.1211   1280   82.3us        67.7us     12.9us
```

Interpretation:

```text
count_only confirms that hash/order construction dominated the remaining
descriptor summary cost.

aggregate audit overhead drops from ~29% over no-shadow to ~8%:
  4.065 / 3.762 - 1 = 8.1%

off + count_only is a near-lower-bound audit path:
  3.875 / 3.762 - 1 = 3.0%

Next bottleneck is now JSONL/controller overhead, so the next gate is
jsonl_batched or flat/batched writer rather than further metric pruning.
```

Runtime shadow JSONL batched writer:

```text
implementation:
  src/mtp_expert_prefetch/runtime/online_shadow.py
    adds writer_mode = sync_jsonl / jsonl_batched
    jsonl_batched stores event objects in memory and serializes/writes them
    during flush/close instead of per row in the generate path

  configs:
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_outcome_aggregate_batched_smoke32.yaml
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_outcome_off_batched_smoke32.yaml
```

AWQ 32-sample writer result:

```text
mode                         writer         generate_s  TPOT_s   rows
no_shadow                    -              3.762       0.1176   0
count_only + aggregate       sync_jsonl     4.065       0.1270   2560
count_only + aggregate       jsonl_batched  4.021       0.1256   2560
count_only + off             sync_jsonl     3.875       0.1211   1280
count_only + off             jsonl_batched  3.939       0.1231   1280
```

Interpretation:

```text
jsonl_batched is replay-correct and slightly helps the aggregate audit path:
  aggregate overhead drops from ~8.1% to ~6.9% over no-shadow.

It does not improve the off path in this 32-sample run, so per-row file flush
is no longer the main bottleneck after count_only. Remaining overhead is likely
dominated by recorder/controller event construction and tensor CPU copy/detach.

Default recommendation:
  count_only + aggregate + jsonl_batched for long-run audit
  count_only + off + sync_jsonl as the descriptor-only lower-bound check
```

Runtime shadow minimal descriptor-summary events:

```text
implementation:
  src/mtp_expert_prefetch/runtime/shadow_log.py
    adds ShadowDescriptorSummaryMinEvent with a fixed scalar schema
    keeps descriptor policy/prior id/hash, request/window/unique-tile counts,
    and timing scalars only

  src/mtp_expert_prefetch/runtime/online_shadow.py
  src/mtp_expert_prefetch/runtime/shadow_controller.py
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py
    add descriptor_order_event_mode = summary / minimal
    minimal writes descriptor_summary_min records instead of full summary rows

  configs:
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_minimal_aggregate_batched_smoke32.yaml
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_minimal_off_batched_smoke32.yaml
```

AWQ 32-sample minimal-event result:

```text
mode                         generate_s  TPOT_s   rows   summary  min   aggregate
no_shadow                    3.762       0.1176   0      0        0     0
count_only + aggregate batch 4.021       0.1256   2560   1280     0     1280
count_only + off batch       3.939       0.1231   1280   1280     0     0
minimal + aggregate batch    3.866       0.1208   2560   0        1280  1280
minimal + off batch          3.797       0.1187   1280   0        1280  0
```

Interpretation:

```text
minimal descriptor-summary events move the hot path from full policy summary
objects to fixed scalar telemetry records.

aggregate audit overhead drops to ~2.8% over no-shadow:
  3.866 / 3.762 - 1 = 2.8%

descriptor-only lower-bound overhead drops to ~0.9% over no-shadow:
  3.797 / 3.762 - 1 = 0.9%

This confirms the next efficient long-run audit path is:
  descriptor_order_metrics_mode=count_only
  descriptor_order_event_mode=minimal
  outcome_logging_mode=aggregate
  writer_mode=jsonl_batched

Descriptor min events are intentionally audit-minimal:
they do not carry same_multiset/order_hash/LRU/order_hit fields. Periodic
none/compact runs remain necessary for semantic and locality diagnostics.
```

Review fix:

```text
aggregate_shadow_events now separates full descriptor summaries from
descriptor_summary_min events.

Build/count/timing means use all descriptor summary events, but LRU/order_hit
and reuse metrics are averaged only over events that actually carry those
fields. This prevents mixed full+minimal logs from diluting diagnostic metrics.
```

Runtime shadow long-run audit:

```text
configs:
  router_mtp_trace_aya_dataset_awq_vllm_no_shadow_128sample.yaml
  router_mtp_trace_aya_dataset_awq_vllm_no_shadow_512sample.yaml
  router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_minimal_aggregate_batched_128sample.yaml
  router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_minimal_aggregate_batched_512sample.yaml

report:
  outputs/reports/runtime_shadow_longrun_audit.md
```

AWQ long-run result:

```text
mode                 samples  generate_s  TPOT_s   overhead  rows
no_shadow            32       3.762       0.1176   -         0
minimal+aggregate    32       3.866       0.1208   +2.78%    2,560
no_shadow            128      13.560      0.1059   -         0
minimal+aggregate    128      14.597      0.1140   +7.65%    10,240
no_shadow            512      54.507      0.1065   -         0
minimal+aggregate    512      57.878      0.1130   +6.19%    40,960
```

Online scalar stability:

```text
samples  descriptor_build_us_mean  decision_us_mean  unique_tiles_mean
32       50.637                    66.722            102.830
128      51.060                    67.156             99.499
512      50.279                    66.358             98.860
```

Offline replay consistency:

```text
128 layer_prior_frequency:
  LRU@8 0.821650, LRU@16 0.821655, reuse_mean 21.5797, order_hit 0.413485

512 layer_prior_frequency:
  LRU@8 0.822214, LRU@16 0.822215, reuse_mean 21.4121, order_hit 0.440311
```

Interpretation:

```text
minimal+aggregate scales linearly in row count and stays single-digit overhead
at 128/512 samples. The 512-sample run is lower overhead than 128, so there is
no evidence of scale-driven overhead growth in this envelope.

Offline replay confirms the layer-prior descriptor-order structure remains
stable: it preserves B-tile locality at B-grouped levels while keeping order_hit
far above plain B-tile grouping.
```

Descriptor consumer micro-runtime MVP:

```text
implementation:
  scripts/run_descriptor_consumer_micro_runtime.py

input:
  online AWQ vLLM trace directory
  layer_prior_frequency prior

semantics:
  rebuild current-router token/row TileRequest stream
  keep the same descriptor/tile multiset
  compare no_order vs layer_prior_frequency
  feed both orders into the same HIP tile consumer
  report checksum deltas, LRU/order_hit, and wall-time

reports:
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w512_sweep.json
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w512_sweep_gpu1.json
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_summary.md
```

AWQ 128 trace, first 512 complete windows:

```text
selected requests: 261,808
unique B tiles: 256
no_order:
  LRU@8 0.172321, order_hit 0.222656
layer_prior_frequency:
  LRU@8 0.710735, order_hit 0.382324
checksum delta vs no_order: 0 for all measured rows
```

Execution-facing HIP consumer result:

```text
GPU0 speedup layer_prior vs no_order:
  tile_elems 256:  0.992x / 1.000x with 16M flush
  tile_elems 512:  1.092x / 1.037x with 16M flush
  tile_elems 1024: 1.096x / 1.081x with 16M flush
  tile_elems 2048: 1.065x / 1.056x with 16M flush

GPU1 speedup layer_prior vs no_order:
  tile_elems 256:  0.972x / 1.012x with 16M flush
  tile_elems 512:  1.143x / 1.053x with 16M flush
  tile_elems 1024: 1.090x / 1.093x with 16M flush
  tile_elems 2048: 1.069x / 1.070x with 16M flush
```

Interpretation:

```text
The descriptor-order execution MVP passes the same-multiset consumer gate.
Layer-prior ordering improves the same HIP consumer for tile_elems >= 512 on
both GPUs, while 256-element tiles are too small/noisy and should remain gated
or treated as no-op.

This is not yet a vLLM kernel patch. It is the bridge result showing that the
online trace descriptor-order signal can translate into execution-side timing
under a controlled descriptor consumer.
```

Descriptor consumer stability + net-overhead gate:

```text
implementation:
  scripts/run_descriptor_consumer_micro_runtime.py

new accounting:
  host Python order_build_us
  order_export_us
  C++ layer_prior_plan build_us
  C++ layer_prior_materialized build_us
  consumer_saved_us
  net_saved_us after Python/C++ build

reports:
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w512_stability_r20.json
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w1024_stability_r10.json
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_all_smoke_r3.json
```

AWQ 128 trace stability:

```text
512 windows / 261,808 requests / repeat=20:
  layer_prior raw consumer speedup min/mean/max:
    1.031x / 1.068x / 1.108x
  consumer_saved_us min/mean/max:
    8.36 / 27.19 / 40.86
  checksum delta max:
    0
  locality:
    no_order LRU@8 0.1723, order_hit 0.2227
    layer_prior LRU@8 0.7107, order_hit 0.3823

1024 windows / 523,448 requests / repeat=10:
  layer_prior raw consumer speedup min/mean/max:
    1.057x / 1.090x / 1.162x
  consumer_saved_us min/mean/max:
    29.96 / 65.19 / 94.00
  checksum delta max:
    0
  locality:
    no_order LRU@8 0.2324, order_hit 0.2611
    layer_prior LRU@8 0.7433, order_hit 0.3663

all windows / 7,360 windows / 3,761,600 requests / repeat=3 smoke:
  layer_prior raw consumer speedup min/mean/max:
    1.112x / 1.132x / 1.155x
  consumer_saved_us min/mean/max:
    690.99 / 853.70 / 1035.24
  checksum delta max:
    0
  locality:
    no_order LRU@8 0.3699, order_hit 0.3509
    layer_prior LRU@8 0.8217, order_hit 0.4135
```

Net-overhead result:

```text
Raw descriptor visitation order is consistently positive in the controlled HIP
consumer, but dynamic per-invocation order construction is not net-positive.

Best observed C++ layer_prior_plan net_saved_us remains negative:
  512-window sweep:  max net_saved_us_after_cpp_plan_build ~= -3.14 ms
  1024-window sweep: max net_saved_us_after_cpp_plan_build ~= -6.22 ms
  all-window smoke:  max net_saved_us_after_cpp_plan_build ~= -33.96 ms

Therefore the execution gate is:
  enable real descriptor-order execution only when the layer-prior plan is
  precomputed, reused, or consumed through a two-level descriptor representation.

Disable:
  dynamic per-invocation full order rebuild/materialization on the decode
  critical path.
```

C++ builder robustness:

```text
The micro-runtime now infers the C++ builder tile domain from the observed
stream:
  num_tiles = max(tile_id) + 1

This avoids treating non-256 tile domains as builder failures. The C++ builder
mode execution is also recorded with returncode/stdout/stderr and ok=false on
failure, so optional builder accounting no longer destroys the raw consumer
benchmark result.

Smoke:
  descriptor_consumer_micro_runtime_builder_smoke.json
  selected windows: 4
  C++ layer_prior_plan ok=true, returncode=0
  C++ layer_prior_materialized ok=true, returncode=0

Regression tests:
  tests/test_descriptor_consumer_micro_runtime.py
  covers observed num_tiles inference, net_saved_us formulas, and skipping net
  accounting when the descriptor multiset does not match.
```

Interpretation:

```text
The descriptor-order execution bridge now passes the same-multiset correctness
gate and the raw consumer timing gate across 512/1024/all-window AWQ traces.

It does not yet pass the dynamic-builder net-benefit gate. The next real
runtime MVP should patch a descriptor consumer to use precomputed/reused
layer_prior group plans or a two-level group_order + group_offsets path, with
fallback to original order.

This remains more mature than speculative LDS payload staging, but it is still
one step before a vLLM fused-MoE kernel patch.
```

Two-level descriptor consumer MVP:

```text
implementation:
  microbench/tile_order_cache/tile_order_cache_bench.hip
  scripts/run_descriptor_consumer_micro_runtime.py

new input mode:
  materialized:
    tile_ids[]

  two-level group plan:
    group_tile_ids[]
    group_counts[]
    group_offsets[]

semantics:
  same current-router descriptor multiset
  no router/membership/logit change
  consume group plan directly instead of materializing reordered tile_ids
```

First one-CTA-per-group result:

```text
The first group-plan consumer was semantically correct but often slower,
because launching one CTA per active B-tile group created too much scheduling
overhead.
```

Chunked group-plan fix:

```text
The group-plan kernel now consumes multiple groups per CTA, using tiles_per_cta
as groups_per_cta in group-plan mode.
```

AWQ 128 trace, first 512 windows, tile_elems=1024, no flush, groups_per_cta sweep:

```text
GPU0 two-level layer_prior speedup vs no_order:
  groups_per_cta=4:  1.236x
  groups_per_cta=8:  1.159x
  groups_per_cta=16: 1.113x
  groups_per_cta=32: 1.072x
  groups_per_cta=64: 0.983x

GPU1 two-level layer_prior speedup vs no_order:
  groups_per_cta=4:  1.246x
  groups_per_cta=8:  1.171x
  groups_per_cta=16: 1.107x
  groups_per_cta=32: 1.077x
  groups_per_cta=64: 0.993x
```

512-window mixed tile-size result with groups_per_cta=32:

```text
two-level group-plan consumer is positive for many 512/1024-tile cases, but
turns negative for 2048-tile cases. Therefore group-plan execution needs its
own runtime gate:

  enable two-level consumer only when:
    same_multiset = true
    tile_elems in measured positive envelope
    groups_per_cta in measured positive envelope, currently 4 or 8 for 1024
    descriptor plan is precomputed/reused or built inside the consumer path

  keep fallback:
    materialized layer_prior order or original no_order
```

Net-overhead boundary remains:

```text
The two-level consumer removes materialized ordered tile-id input from the
kernel path, but the current Python/C++ host plan build is still not
net-positive as a per-invocation critical-path action. The next runtime patch
should pass precomputed layer-prior group plans or build the group plan inside
the existing descriptor producer/consumer without a full host-side rebuild.
```

Two-level gate table + producer stats:

```text
implementation:
  scripts/summarize_descriptor_consumer_gate_table.py
  src/mtp_expert_prefetch/runtime/descriptor_order.py
  src/mtp_expert_prefetch/runtime/shadow_log.py
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py

gate report:
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w512_two_level_gate_table.json
  outputs/reports/tile_order_cache/descriptor_consumer_two_level_gate_table_summary.md

runtime shadow fields:
  descriptor_order_execution_mode
  descriptor_group_plan_groups_per_cta
  descriptor_group_plan_group_count
  descriptor_group_plan_avg_group_size
  descriptor_group_plan_p95_group_size
  descriptor_group_plan_max_group_size
  descriptor_group_plan_cta_count
```

Gate table result on AWQ 128 trace, first 512 windows, tile_elems=1024:

```text
group-plan stats:
  group_count: 75,733
  window_count: 512
  avg_group_size: 3.46
  p95_group_size: 10
  max_group_size: 63
  avg_groups_per_window: 147.92
  p95_groups_per_window: 173
  max_groups_per_window: 189

gate rows:
  allowed: 16 / 20

GPU0:
  groups_per_cta=4:
    no_flush 1.302x, 16M_flush 1.487x
  groups_per_cta=8:
    no_flush 1.154x, 16M_flush 1.212x
  groups_per_cta=16:
    no_flush 1.133x, 16M_flush 1.077x
  groups_per_cta=32:
    no_flush 1.061x, 16M_flush 1.032x
  groups_per_cta=64:
    no_flush 0.975x, 16M_flush 0.999x

GPU1:
  groups_per_cta=4:
    no_flush 1.269x, 16M_flush 1.590x
  groups_per_cta=8:
    no_flush 1.144x, 16M_flush 1.338x
  groups_per_cta=16:
    no_flush 1.088x, 16M_flush 1.047x
  groups_per_cta=32:
    no_flush 1.041x, 16M_flush 1.026x
  groups_per_cta=64:
    no_flush 0.979x, 16M_flush 0.984x
```

Updated gate:

```text
Recommended initial runtime gate:
  descriptor_order_execution_mode = two_level_group_plan
  tile_elems = 1024
  groups_per_cta in {4, 8}
  same_multiset = true
  checksum/parity gate passes

Allowed but lower-priority diagnostic envelope:
  groups_per_cta in {16, 32}

Disable:
  groups_per_cta >= 64
  unmeasured tile_elems/device/kernel variants
```

Producer-side status:

```text
The runtime descriptor-order producer now computes and emits two-level group
plan stats in both full summary and minimal telemetry modes. This lets online
shadow runs audit whether a request/layer falls into the measured profitable
group-plan envelope without changing real execution order.

The attempted fresh smoke config generated trace .pt files but did not produce
runtime_shadow.jsonl in that path, so online field validation is currently
covered by focused recorder/controller tests rather than a new end-to-end trace
run. The next end-to-end AWQ shadow run should use the known writer path and
verify these fields in runtime_shadow.jsonl before vLLM kernel patching.
```
