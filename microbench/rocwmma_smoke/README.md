# rocWMMA Smoke Tests

This directory contains the smallest ROCm / rocWMMA validation needed before
connecting speculative LDS staging to a true matrix-core consumer on W7900.

Current target:

```text
GPU: AMD W7900 / W7900 Dual Slot
ISA: gfx1100 / RDNA3
Matrix path: WMMA / rocWMMA
```

The first smoke is intentionally tiny:

```text
16x16x16 GEMM
input dtype: rocwmma::float16_t
accumulator dtype: float
layout: row-major A/B/C
```

It only verifies:

- rocWMMA headers and API compile for `gfx1100`;
- fragment load / `mma_sync` / store run on both local GPUs;
- output agrees with a CPU reference.

It does **not** yet test speculative LDS staging. That comes next:

```text
global rocWMMA baseline
-> LDS-staged rocWMMA consumer
-> hit/miss/overwrite timing
```

The second smoke starts that path with a single rocWMMA tile:

```text
global_baseline:
  rocWMMA loads A/B directly from global memory

lds_hit:
  stage the B/expert tile into LDS, then rocWMMA reuses it across
  one or more synthetic token rows

lds_miss_overwrite:
  stage the wrong B tile into LDS, overwrite B after validation,
  then rocWMMA consumes the corrected LDS B tile
```

This proves the fragment can consume LDS-staged B tiles on gfx1100. It is not
yet a speedup claim: without a same-kernel validation window or enough grouped
tile reuse, LDS staging is expected to add overhead relative to a direct global
load.

## Run

```bash
python scripts/run_rocwmma_hello.py \
  --device 0 \
  --device 1 \
  --offload-arch gfx1100 \
  --output outputs/reports/rocwmma_smoke/rocwmma_hello_2gpu.json
```

```bash
python scripts/run_rocwmma_tile_stage.py \
  --device 0 \
  --device 1 \
  --consumer-rows 1 \
  --consumer-rows 4 \
  --consumer-rows 8 \
  --validate-iters 0 \
  --validate-iters 64 \
  --validate-iters 256 \
  --offload-arch gfx1100 \
  --output outputs/reports/rocwmma_smoke/rocwmma_tile_stage_validate_2gpu.json
```

The validation sweep currently reports a conservative boundary: all rows are
numerically correct, but the serial same-kernel validation phase does not hide
LDS staging cost. The next performance gate should test real overlap or
pipelining, not just longer serial validation work.

## rocprof Counter Guard

The profiling harness deliberately treats unsupported or zero-only counter
results as non-informative. On the current W7900 / gfx1100 setup, rocprofv3 can
report non-zero `SQ_WAVES`, but the selected LDS/global traffic counters have
returned zero even for positive-control kernels with obvious global and LDS
traffic.

Run the positive controls before using counters for B-reload classification:

```bash
python scripts/run_rocprof_positive_controls.py \
  --device 0 \
  --metric SQ_WAVES \
  --metric SQ_INSTS_LDS \
  --metric SQ_INSTS_TEX_LOAD \
  --metric FETCH_SIZE \
  --blocks 256 \
  --threads 256 \
  --elems 4194304 \
  --inner-iters 64 \
  --warmup 0 \
  --iters 1 \
  --output-dir outputs/reports/rocwmma_smoke/rocprof_positive_controls_smoke
```

If the positive controls are also non-informative, do not compute a hardware
`B_reload_ratio` from those counters. Use static ISA inspection plus timing
classification as the interim fallback:

```bash
python scripts/inspect_hip_isa_static.py \
  --binary microbench/rocwmma_smoke/build/rocwmma_tile_stage \
  --kernel-regex rocwmma_tile_stage \
  --output-dir outputs/reports/rocwmma_smoke/static_isa_rocwmma_tile_stage_smoke
```

Static inspection is supporting evidence only. It can show that the target
kernel contains global loads, LDS loads/stores, barriers, and WMMA/matrix ops,
but it cannot replace trustworthy hardware byte counters.
