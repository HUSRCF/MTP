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

## Run

```bash
python scripts/run_rocwmma_hello.py \
  --device 0 \
  --device 1 \
  --offload-arch gfx1100 \
  --output outputs/reports/rocwmma_smoke/rocwmma_hello_2gpu.json
```
