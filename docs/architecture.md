# Architecture

## Goal

Use MTP hidden states as a lookahead signal for future MoE routing. The predictor should estimate which experts will be needed in the next few decoding steps, so a runtime can prefetch those experts into VRAM before they block generation.

## Components

### Frozen Backbone

The target model is loaded in quantized form where possible. The backbone is not trained in the first phase.

Expected precision split:

- INT4: MoE expert weights.
- BF16: routers, attention, shared experts, MTP modules, embeddings, and predictor modules.

### Trace Collector

Runs representative text through the frozen model and stores:

- input token ids and sequence metadata;
- selected top-k experts per token and layer;
- optional router logits or scores;
- optional hidden states or projected hidden states;
- optional MTP outputs and shape metadata.

For the first trace pass, prefer `CohereForAI/aya_dataset` over the full
`CohereForAI/aya_collection`: it is human-curated and small enough for quick
iteration. The collection is useful later when we need broader multilingual and
task coverage.

### Future Expert Predictor

Consumes current hidden or MTP future hidden states and predicts future expert sets:

```text
P(expert | layer, future_step, hidden)
```

The primary target is multi-label top-k expert prediction, not token prediction.

### Cache Simulator

Tests whether predictions reduce blocking expert loads under controlled memory budgets. This should run before implementing runtime prefetch.

### Runtime Prototype

Implements expert residency, prefetch scheduling, and eviction. llama.cpp is a good first target after the PyTorch trace/training loop is validated.
