# Speculative LDS Tile-Staging Microbench

This microbench isolates the first systems question behind the current moat:

```text
Can low-trust transition/MTP hints reduce grouped-GEMM prologue latency by
staging likely tiles into LDS before true routing metadata is committed?
```

It intentionally does **not** depend on Qwen/vLLM, rocWMMA, CK, or a real MoE
kernel yet. The P0 goal is to measure the cost envelope for:

- reactive true routing: wait for true metadata, then load the true tile from HBM into LDS;
- oracle staging: stage the correct tile into LDS before the validation point;
- speculative hit: stage the predicted tile, validate it as correct, then compute;
- speculative miss: stage the predicted tile, validate it as wrong, overwrite LDS with the true tile, then compute;
- mixed speculation: a controlled miss-rate blend of hit and miss.

The benchmark records per-block cycle counters around the LDS prologue and also
reports HIP event wall time. `validate_iters` is a synthetic true-router /
metadata wait window. It is not a router benchmark; it simply creates a window
where speculative HBM->LDS staging can be hidden before the commit point.

Important boundary:

```text
LDS cannot be written by the CPU and does not persist across kernels.
This benchmark stages LDS state inside the HIP kernel prologue.
```

## Build And Run

```bash
python scripts/run_lds_tile_staging_bench.py --device 0 --output outputs/reports/lds_tile_staging/smoke.json
```

To run a single mode:

```bash
python scripts/run_lds_tile_staging_bench.py \
  --device 0 \
  --mode spec_miss \
  --requests 4096 \
  --tile-elems 1024 \
  --validate-iters 256 \
  --output outputs/reports/lds_tile_staging/spec_miss.json
```

Use `--device 1` for the second ROCm-visible GPU.

## Why Not rocWMMA First?

rocWMMA/CK are the right follow-up once the LDS-staging envelope is positive.
For P0, a hand-written HIP kernel is better because it exposes the exact
variables we need to isolate: LDS bytes, overwrite penalty, hit/miss behavior,
and first-FMA latency. A rocWMMA version should be added after this microbench
shows that the prologue-level effect is worth integrating into a real GEMM
pipeline.
