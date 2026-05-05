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
  --offload-arch gfx1100 \
  --output outputs/reports/rocwmma_smoke/rocwmma_tile_stage_reuse_2gpu.json
```
