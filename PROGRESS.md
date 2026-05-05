# MTP Expert Prefetch Progress

## Progress Version

- Version: `v0.10-rocwmma-smoke`
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
