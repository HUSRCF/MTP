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
