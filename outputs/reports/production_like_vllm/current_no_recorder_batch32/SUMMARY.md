# Production-like vLLM Batch32 Decode Baseline

Date: 2026-06-11

Scope:
- Model: `configs/model/qwen3_6_35b_a3b_awq_4bit.yaml` derivatives
- Dataset split: external prompt Dolly, 32 samples, gen64
- GPU: GPU1 W7900 dual-slot
- Purpose: separate true vLLM batched decode throughput from recorder/shadow harness throughput.

## Results

| mode | router recorder | return routed experts | samples | output tokens | generate_s | TPOT_s | aggregate tok/s | tok/s/seq |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| recorder_harness_8 | on | n/a | 8 | 512 | 38.337 | 0.074877 | 13.36 | 1.67 |
| batch32_return_routed | off | on | 32 | 2048 | 8.020 | 0.003916 | 255.36 | 7.98 |
| batch32_no_route_capture | off | off | 32 | 2048 | 7.253 | 0.003541 | 282.38 | 8.82 |
| batch32_no_route_capture_graph | off | off | 32 | 2048 | 13.276 | 0.006482 | 154.26 | 4.82 |
| telemetry_ladder_production_batch | off | off | 32 | 2048 | 7.265 | 0.003548 | 281.88 | 8.81 |

## Interpretation

The earlier `production_like` telemetry ladder mode is a low-observability audit harness, but it still uses the router recorder path. In that path each prompt is generated separately, so GPU utilization is low and TPOT is not representative of production batched serving.

The no-recorder batch32 path submits all 32 prompts in one `llm.generate` call and is the appropriate production-like throughput baseline. Disabling routed-expert return removes additional trace-side D2H/CPU overhead and improves aggregate throughput by about 10.6% over `batch32_return_routed`.

The graph/compile path (`enforce_eager=false`) is not profitable for this current setup. It spends about 423.6s in engine init/compile and its measured generate throughput is slower than eager. The short-term production path should keep `enforce_eager=true`.

`scripts/run_awq_telemetry_ladder.py` now has an explicit `production_batch` mode that disables runtime shadow, router recorder, and routed-expert return, while keeping batch32 eager serving. This is the default entrypoint for production-like TPOT comparisons.

## Backend Notes

The run still uses `enforce_eager=true`; CUDAGraph/torch.compile are disabled. vLLM logs also show ROCm custom paged attention falls back to Triton because this Qwen3/Mamba hybrid uses a non-power-of-two/stride-padded attention block size (`1056` tokens). This is not a simple environment-variable issue.

## Artifact Paths

- Recorder harness:
  `outputs/reports/awq_telemetry_ladder/gpu1_current_production_like_smoke8_20260611/production_like/repeat_00/performance_summary.json`
- Batch32 with routed experts:
  `data/traces/external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_production_no_recorder_eager/performance_summary.json`
- Batch32 without routed experts:
  `data/traces/external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_production_no_recorder_no_route_capture_eager/performance_summary.json`
- Batch32 without routed experts, graph/compile:
  `data/traces/external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_production_no_recorder_graph/performance_summary.json`
- Scripted telemetry-ladder production batch:
  `outputs/reports/awq_telemetry_ladder/gpu1_current_production_batch32_20260611/production_batch/repeat_00/performance_summary.json`

Next gate:
- Move live handoff/typed-slot benchmarks onto the no-recorder batched path before making any TPOT claim.
- Keep recorder/shadow runs as semantic evidence only, not production throughput evidence.
