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
- anti-artifact controls:
  - `dummy_lds_store`: write dummy values into LDS, then load the true tile;
  - `wrong_no_consume`: stage a wrong tile but do not consume it;
  - `global_no_lds`: touch the predicted global tile without staging it into LDS.

The benchmark records per-block cycle counters around the LDS prologue and also
reports HIP event wall time. `validate_iters` is a synthetic true-router /
metadata wait window. It is not a router benchmark; it simply creates a window
where speculative HBM->LDS staging can be hidden before the commit point.

`--metadata-tokens` replaces the pure spin wait with a same-kernel metadata
builder mock that constructs expert counts and offsets in LDS before validation.
`--compute-iters` repeats the FMA pass over the staged tile.
`--consumer-rows` makes each workgroup consume the same staged expert tile for
multiple synthetic token rows, acting as a lightweight grouped-GEMM tile-reuse
mock. It is not rocWMMA yet.
`--tile-stride` spaces logical experts apart in the physical tile array, creating
a larger strided working set. `--cache-flush-elems` touches a separate power-of-two
global buffer before each measured kernel to reduce cache-warming artifacts.

The JSON report includes staged-tile outcome counters:

- `staged_tile_count`
- `staged_tile_consumed_count`
- `staged_tile_discarded_count`
- `fallback_true_tile_load_count`
- consumed / discarded fractions

It also reports `lds_bytes_per_block`, `occupancy_blocks_per_cu`, and related
LDS/thread-limited occupancy proxies so tile-staging gains can be interpreted
against LDS pressure.

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
  --metadata-tokens 64 \
  --compute-iters 4 \
  --output outputs/reports/lds_tile_staging/spec_miss.json
```

To run controls:

```bash
python scripts/run_lds_tile_staging_bench.py \
  --device 0 \
  --include-controls \
  --metadata-tokens 64 \
  --compute-iters 4 \
  --output outputs/reports/lds_tile_staging/controls.json
```

Use `--device 1` for the second ROCm-visible GPU.

## Why Not rocWMMA First?

rocWMMA/CK are the right follow-up once the LDS-staging envelope is positive.
For P0, a hand-written HIP kernel is better because it exposes the exact
variables we need to isolate: LDS bytes, overwrite penalty, hit/miss behavior,
and first-FMA latency. A rocWMMA version should be added after this microbench
shows that the prologue-level effect is worth integrating into a real GEMM
pipeline.

Hardware note:

```text
The current local target is W7900 / RDNA3, so the matrix path should be
WMMA / rocWMMA-oriented. MFMA is a CDNA-oriented follow-up and should not be
used as the main W7900 validation claim.
```

## Interpreting Controls

The overlap model is meaningful for `reactive`, `oracle`, `spec_hit`,
`spec_miss`, and `mixed`. It is intentionally not a profitability model for
the anti-artifact controls, because those controls do not consume the staged LDS
tile as the real speculative path does. Use control-mode wall time and sink
checksums to detect whether the observed effect could be explained by ordinary
global cache warming, dummy LDS writes, or measurement imbalance.

For example, `wrong_no_consume` and `global_no_lds` may show favorable synthetic
overlap-model values because they do not pay the same LDS-consumption or miss
overwrite path. That is not a speedup claim. The relevant anti-artifact question
is whether their wall time and staged-consumed counters reproduce the `spec_hit`
path. They should not.
