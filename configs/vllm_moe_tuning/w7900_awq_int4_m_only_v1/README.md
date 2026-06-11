# W7900 AWQ/WNA16 M-only MoE Config Overlay

This directory is a repo-local `VLLM_TUNED_CONFIG_FOLDER` overlay for the
vLLM fused-MoE config lookup:

```bash
VLLM_TUNED_CONFIG_FOLDER="$(git rev-parse --show-toplevel)/configs/vllm_moe_tuning/w7900_awq_int4_m_only_v1"
```

It exists to make the W7900 AWQ/WNA16 config lookup reproducible without
editing the conda environment or vLLM site-packages.

Scope: this overlay has only been validated for the W7900 AWQ/WNA16 path
(`E=256,N=512,dtype=int4_w4a16`).  It should not be reused for non-WNA16 MoE
kernel paths without a separate A/B run.

Two aliases are included because different lookup paths have reported different
device-name normalizations:

- `AMD_Radeon_PRO_W7900_Dual_Slot_`
- `AMD_Radeon_PRO_W7900`

The JSON files intentionally override only M-side launch/configuration fields:

- `BLOCK_SIZE_M`
- `GROUP_SIZE_M`
- `SPLIT_K`
- `num_warps`
- `num_stages`

They intentionally do not set `BLOCK_SIZE_N`, `BLOCK_SIZE_K`, or
`matrix_instr_nonkdim`; vLLM should keep its dynamic W1/W2 N/K choices.

Current status: negative evidence.  GPU1 AWQ/Dolly heldout128 gen64 repeat-3
confirmed the overlay is loaded, but it was slower than the latest reuse-LLM
production-batch baseline.  Do not enable this overlay by default for
production-like benchmark claims.
