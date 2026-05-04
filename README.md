# MTP Expert Prefetch

Research code for using MTP hidden states to predict future MoE expert demand, then driving expert prefetch / cache scheduling for offloaded inference.

The intended first target is `Qwen3.6-35B-A3B-GPTQ-Int4`: keep the quantized backbone frozen, use BF16 MTP / predictor modules, collect routing traces, and evaluate predictive expert loading before moving runtime changes into llama.cpp or another inference engine.

## Project Layout

```text
configs/                  Experiment configs grouped by task.
data/                     Local datasets and generated routing traces.
docs/                     Design notes, experiment logs, and paper-facing notes.
scripts/                  Thin entry-point scripts for one-off operations.
src/mtp_expert_prefetch/  Reusable Python package.
tests/                    Unit and smoke tests.
outputs/                  Local run outputs, checkpoints, reports, and figures.
third_party/              External code snapshots or patches, kept explicit.
```

## Main Workflow

1. Fetch text material into `data/raw/`.
2. Run the frozen model and collect hidden/router/MTP traces into `data/traces/`.
3. Train BF16 future-expert predictors from traces.
4. Evaluate prediction quality and cache-simulator latency proxies.
5. Port the validated prefetch policy into the runtime prototype.

Example smoke material:

```bash
python scripts/fetch_text_material.py configs/data/aya_dataset_smoke.yaml
```

For Qwen3.6 tracing, use an isolated environment if your base environment is
shared with vLLM or other packages:

```bash
python -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install --upgrade 'git+https://github.com/huggingface/transformers.git'
python scripts/trace_router_mtp.py configs/trace/router_mtp_trace_aya_dataset.yaml
```

## Design Principles

- Keep heavyweight model weights outside git.
- Keep reusable logic under `src/`; keep `scripts/` as thin wrappers.
- Make every experiment reproducible from a config file.
- Separate trace collection, predictor training, cache simulation, and runtime integration.
