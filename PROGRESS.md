# MTP Expert Prefetch Progress

## Progress Version

- Version: `v0.44-runner-recorded-lab-closure`
- Updated: 2026-06-02
- Current phase: premap descriptor/address prep now has a typed
  kernel-side consumer object, a launch-shaped future native ABI, and a
  dispatch-shaped readonly native consumer ABI.  The default lab gate remains
  live-disabled, zero-payload, and not passed to the current WNA16 kernel.
  The latest hardening requires the online canary artifact checker to see the
  full preflight runtime/strict evidence scan and forbids the normal lab
  preflight from deferring both runner and artifact evidence at the same time.
  Review follow-up now covers the strict preflight rows/type and deferred-label
  count mismatch branches, and the lab preflight summary now exposes the
  future dispatch ABI schema fields directly while keeping
  `current_wna16_arg_compatible=false`.  A new future-native arg-slot ABI
  canary now models the compact parameter slot a future kernel could receive,
  while still keeping payload and WNA16 kernel-arg pass disabled.  The latest
  compact status fields now
  bind `artifact_check_passed` to the independent artifact evidence row and
  bind `final_preflight_passed` to both final status and no-defer closure.
  The latest required lab evidence now runs the future-native arg-slot ABI over
  a merged table built from 32 real online vLLM prelaunch typed-consumer
  exports, so the multi-program packet chain is validated on online handle
  distributions rather than only on a standalone synthetic table.  The same
  online-merged canary is now reproducible through a dedicated runner script
  instead of relying on a hand-materialized artifact.  The lab preflight status
  now explicitly marks that the dispatch/dispatch-pointer/arg-slot
  handle-projection hash covers all four typed handle fields, and the strict
  preflight now fails if that all-field projection check is not satisfied.
  The online-merged arg-slot runner evidence is now also checked to target the
  default GPU1 lab device, accepting either physical `device=1` or logical
  `device=0` under `HIP_VISIBLE_DEVICES=1`.  The compact preflight status now
  also exposes the future kernel-args and compatible-consumer-path row/safety
  fields so the next kernel-side ABI step is visible without opening the full
  runner JSON.  Future kernel-args mirror coverage is now also visible in the
  same compact status and reaches all four typed handle fields in the default
  lab artifact.  That full-field future-kernel-args coverage is now a strict
  lab preflight requirement.  The future kernel-args compatible consumer path
  is also now visible as an explicit required lab contract field.  The
  one-step lab closure runner now additionally requires the native artifact
  checker to consume the preflight/status paths recorded by the native runner
  itself, so explicit manual paths can no longer satisfy the default lab
  closure accidentally.  The latest lab gate now also requires child
  future-native arg-slot artifacts to expose an all-field typed handle mask
  (`field_mask=15`, `required_field_mask=7`) across native, launch, dispatch,
  dispatch-pointer, and arg-slot consumer layers.

## Latest Update: Future Native Arg-Slot Field-Mask Gate

The online-merged future-native arg-slot gate now verifies that the native
consumer path is not only row/window/hash correct, but also exposes the full
typed handle schema expected by a future kernel-side consumer:

```text
future_kernel_native_*_field_mask = 15
future_kernel_native_*_required_field_mask = 7
```

This is enforced for native consumer, launch consumer, dispatch consumer,
dispatch-pointer consumer, and arg-slot consumer summaries.  The window sweep
checker now requires child artifacts to carry these masks, and the all-field
window sweep plus one-step lab gate verify now surface
`require_child_field_masks=true`.

Validation:

```text
python -m pytest tests -q
  912 passed, 2 warnings

python scripts/run_premap_lab_gate_verify.py
  passed = true

python scripts/check_premap_lab_gate_verify.py \
  --output-json outputs/reports/premap_lab_gate_verify.check.json
  passed = true
```

The lab gate remains no-op with respect to the real vLLM/WNA16 path:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

The lab closure/verify orchestrators now also set subprocess `PYTHONPATH`
explicitly to `repo:repo/src:$PYTHONPATH`, so the gate no longer depends on a
manually configured shell environment for child script imports.

The compact `run_premap_lab_preflight.py --summary-only` status now also
flattens the same five consumer-layer masks:

```text
default_kernel_consumer_native_field_mask = 15
default_kernel_consumer_launch_field_mask = 15
default_kernel_consumer_dispatch_field_mask = 15
default_kernel_consumer_dispatch_ptr_field_mask = 15
default_kernel_consumer_arg_slot_field_mask = 15
```

`scripts/run_premap_lab_preflight.py` now bootstraps `repo` and `repo/src` on
`sys.path`, so the compact status entrypoint can be invoked directly without an
external `PYTHONPATH`.

## Latest Update: Optional Tail-Window Closure Probe

The lab closure runner can now optionally refresh and validate a row-window
future-native arg-slot canary:

```text
scripts/run_premap_lab_gate_closure.py --run-tail-window-probe --tail-window-size 512
```

This is deliberately a side probe, not a replacement for the default full-table
lab gate.  It keeps the same merged online prelaunch typed-consumer table
resident, but asks the future native dispatch/dispatch-pointer/arg-slot ABI to
consume only the tail row window:

```text
outputs/reports/premap_lab_gate_closure_tail_window512.json

passed = true
arg_slot_tail_window_runner.tail_window_size = 512
arg_slot_tail_window_runner.merged_row_count = 1841
arg_slot_tail_window_runner.dispatch_row_offset = 1329
arg_slot_tail_window_runner.dispatch_row_limit = 1841
arg_slot_tail_window_runner.dispatch_active_rows = 512
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

The closure artifact can now be checked without rerunning native/GPU canaries:

```text
scripts/check_premap_lab_gate_closure.py

outputs/reports/premap_lab_gate_closure.check.json
  passed = true

outputs/reports/premap_lab_gate_closure_tail_window512.check.json
  passed = true
  require_tail_window_probe = true
```

A one-step verify runner now refreshes both closures and checks both artifacts:

```text
scripts/run_premap_lab_gate_verify.py

outputs/reports/premap_lab_gate_verify.json

passed = true
steps =
  default_closure
  default_closure_check
  tail_window_closure
  tail_window_closure_check
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

The verify runner now also inspects the generated statuses directly, so a
subcommand returning zero is not enough if its artifact reports failed checks,
payload bytes, kernel handoff, or a tail-window checker that did not actually
require the tail-window contract.

This pushes the future kernel-side typed-consumer path closer to real
CTA/program row-slice consumption while preserving the current safety boundary:
no payload dereference or transfer, no ready credit, no router/order mutation,
and no current WNA16 kernel-argument pass.

## Latest Update: Runner-Recorded Lab Closure Contract

The canonical lab closure runner now enforces the evidence path contract that
the native artifact checker must use paths recorded by the native runner:

```text
scripts/run_premap_lab_gate_closure.py

requires_runner_recorded_artifact_paths = true
native_artifact_check.preflight_json_source = runner_recorded
native_artifact_check.status_json_source = runner_recorded
```

The latest closure artifact passes under the default strict contract:

```text
outputs/reports/premap_lab_gate_closure.json

passed = true
failures = []
selected_source_count = 32
merged_row_count = 1841
dispatch_active_rows = 1841
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

This prevents a manual `--preflight-json` / `--status-json` override from
silently satisfying the lab closure.  Manual explicit paths remain available
only through an explicit override flag for debugging, not as the default lab
precondition.  The safety boundary is unchanged: no payload dereference or
transfer, no ready credit, no router/order mutation, and no current WNA16
kernel-argument pass.

## Latest Update: GPU1-target online-merged arg-slot runner gate

The default lab preflight now rejects online-merged future-native arg-slot
runner evidence that does not target the GPU1 lab device:

```text
online_merged_multiprogram_arg_slot_runner_device_not_gpu1
```

The check deliberately accepts both forms used in local runs:

```text
device = 1
or
device = 0 with HIP_VISIBLE_DEVICES=1
```

The optional online-merged one-field mirror runner artifacts were refreshed
with explicit `--device 1` and current all-handle projection metadata:

```text
outputs/reports/premap_kernel_consumer/
  online_merged_future_native_arg_slot_32tables_descriptor_ptr_canary_runner.json
  online_merged_future_native_arg_slot_32tables_packed_weight_canary_runner.json
  online_merged_future_native_arg_slot_32tables_aux_metadata_canary_runner.json

device = 1
merged_row_count = 1841
handle_projection_all_handle_fields_checked = true
handle_projection_field_names =
  [descriptor_ptr, packed_weight_descriptor, scale_metadata_handle,
   aux_metadata_handle]
```

The default preflight artifact remains green:

```text
outputs/reports/premap_lab_preflight_default_with_projection_coverage.json

passed = true
default_optional_evidence_passed = true
default_kernel_consumer_arg_slot_online_merged_optional_mirror_field_coverage =
  [aux_metadata_handle, descriptor_ptr, packed_weight_descriptor]
default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_checked = true
```

This is still a lab-gate/evidence hardening step only.  The safety boundary is
unchanged: no payload dereference or transfer, no ready credit, no router/order
mutation, and no WNA16 kernel-argument pass.

The same compact artifact now also exposes the future kernel-args path:

```text
default_kernel_consumer_dispatch_runner_future_kernel_args_checked = true
default_kernel_consumer_dispatch_runner_future_kernel_args_row_count = 174
default_kernel_consumer_dispatch_runner_future_kernel_args_row_ok_count = 174
default_kernel_consumer_dispatch_runner_future_kernel_args_payload_bytes = 0
default_kernel_consumer_dispatch_runner_future_kernel_args_passed_to_kernel = false
default_kernel_consumer_dispatch_runner_future_kernel_args_current_wna16_arg_compatible = false

default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_checked = true
default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_required = true
default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_row_count = 174
default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_row_ok_count = 174
default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_payload_bytes = 0
default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_passed_to_kernel = false
default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_current_wna16_arg_compatible = false

default_kernel_consumer_dispatch_runner_future_kernel_args_mirror_field_coverage =
  [scale_metadata_handle]
default_kernel_consumer_dispatch_runner_future_kernel_args_optional_mirror_field_coverage =
  [aux_metadata_handle, descriptor_ptr, packed_weight_descriptor]
default_kernel_consumer_dispatch_runner_future_kernel_args_total_mirror_field_coverage =
  [aux_metadata_handle, descriptor_ptr, packed_weight_descriptor,
   scale_metadata_handle]
default_kernel_consumer_dispatch_runner_future_kernel_args_total_full_field_mirror_coverage = true
default_kernel_consumer_dispatch_runner_future_kernel_args_total_mirror_coverage_required = true
```

The strict preflight now rejects missing future-kernel-args full-field coverage
via:

```text
default_kernel_consumer_future_kernel_args_total_mirror_coverage_incomplete
```

This promotes the future kernel-args path from a visible compact status into a
real lab precondition for the next kernel-side compatible consumer step.  It
still does not make the path compatible with the current WNA16 kernel args and
does not pass any typed object to the current kernel.

## Latest Update: Explicit All-Handle Projection Coverage

The default lab preflight now exposes and enforces the full handle-projection
coverage of the future-native arg-slot path instead of relying on the reader to
infer it from the hashchain fields:

```text
outputs/reports/premap_lab_preflight_default_with_projection_coverage.json

default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal = true
default_kernel_consumer_dispatch_runner_handle_projection_field_names =
  [descriptor_ptr, packed_weight_descriptor, scale_metadata_handle,
   aux_metadata_handle]
default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_schema_covered = true
default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_checked = true
default_kernel_consumer_arg_slot_online_total_full_field_mirror_coverage = true
default_kernel_consumer_arg_slot_total_full_field_mirror_coverage = true
```

This does not change the safety boundary: the arg-slot path still only reads a
future typed ABI object, does not dereference payload, and is not passed to the
current WNA16 kernel.  The new status field makes the gate clearer, and the
strict no-defer preflight now rejects missing coverage via:

```text
default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_unchecked
```

Single-field mirror canaries cover one field at a time, while the projection
hash validates that the native consumer row path reads the full typed handle
row.

The online-merged runner report now carries the same self-description directly:

```text
outputs/reports/premap_kernel_consumer/
  online_merged_future_native_arg_slot_canary_runner_latest.json

device = 1
selected_source_count = 32
merged_row_count = 1841
handle_projection_hashchain_equal = true
handle_projection_all_handle_fields_checked = true
handle_projection_field_names =
  [descriptor_ptr, packed_weight_descriptor, scale_metadata_handle,
   aux_metadata_handle]
```

The default lab preflight required-evidence validator now also checks these
runner-level fields directly, so a runner report with a missing or false
all-field projection marker is rejected before it can satisfy the lab gate.

## Latest Update: Reproducible Online-Merged Arg-Slot Runner

The online-merged arg-slot canary now has a one-step evidence runner, and the
default lab preflight now checks that runner as required evidence:

```text
scripts/run_premap_online_merged_native_arg_slot_canary.py
```

It consumes the existing online prelaunch native-stub runner artifact, merges
the exported typed-consumer input tables, runs the future native arg-slot HIP
stub, and emits a compact runner report:

```text
outputs/reports/premap_kernel_consumer/
  online_merged_future_native_arg_slot_canary_runner_latest.json
```

The latest GPU1 run used 32 online vLLM prelaunch typed input tables:

```text
selected_source_count = 32
merged_row_count = 1841
block_threads = 256
expected_program_count = 8

future_kernel_native_dispatch_consumer_row_ok_count = 1841 / 1841
future_kernel_native_dispatch_ptr_consumer_row_ok_count = 1841 / 1841
future_kernel_native_arg_slot_consumer_row_ok_count = 1841 / 1841

future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator =
  9748c8c92c02281b
future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator =
  9748c8c92c02281b
future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator =
  9748c8c92c02281b
```

The runner preserves the lab safety boundary:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
not_a_single_vllm_launch_table = true
```

The first post-commit canary used `*_latest` runner and `*_latest` stub paths;
that proved the native arg-slot path works, but the full lab gate expects the
latest runner artifact to point at the canonical stub evidence path.  The
canonical evidence was refreshed and the full no-defer lab gate now closes:

```text
canonical runner:
  outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_canary_runner_latest.json

canonical stub:
  outputs/reports/premap_kernel_consumer/
    typed_consumer_stub_gpu1_online_merged_future_native_arg_slot_32tables_canary.json

canonical merged input:
  outputs/reports/premap_kernel_consumer/
    online_merged_prelaunch_typed_consumer_input_arg_slot_32tables.json

full no-defer preflight:
  python scripts/run_premap_lab_preflight.py
    --output-json
      outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.full.json
  passed

summary-only preflight:
  outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.json
  passed

compact checker:
  outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.check.json
  passed
```

The online native-stub artifact checker must be run with the preflight/status
paths recorded by the runner, not the generic default filenames.  The current
matching set also passes:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json

preflight:
  outputs/reports/
    premap_lab_preflight_online_prelaunch_native_stub_canary_hard_hashchain_preflight_32tables.json

status:
  outputs/reports/
    premap_lab_preflight_status_online_prelaunch_native_stub_canary_hard_hashchain_preflight_32tables.json

artifact checker:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_current.json
  passed
```

## 2026-06-02 - Runner-recorded artifact checker paths

The native prelaunch artifact checker now defaults to the preflight/status
paths recorded by the runner artifact:

```text
runner.preflight_output_json
runner.preflight_status_output_json
```

Explicit `--preflight-json` and `--status-json` still work for manual
cross-checks, but the default CLI path now follows the runner's own final
strict preflight artifacts.  This prevents the common failure mode where the
checker is pointed at generic preflight/status filenames that do not correspond
to the runner under review.

Validation:

```text
python scripts/check_premap_online_native_stub_canary_artifacts.py \
  --runner-json \
    outputs/reports/premap_kernel_consumer/
      online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json \
  --output-json \
    outputs/reports/premap_kernel_consumer/
      online_prelaunch_native_stub_canary_artifact_check_runner_recorded_current.json

result:
  passed = true
  preflight_json_source = runner_recorded
  status_json_source = runner_recorded

pytest tests/test_check_premap_online_native_stub_canary_artifacts.py -q:
  59 passed

pytest tests/test_check_premap_online_native_stub_canary_artifacts.py \
       tests/test_run_premap_online_native_stub_canary.py \
       tests/test_run_premap_lab_preflight.py -q:
  167 passed

pytest tests -q:
  869 passed, 2 warnings
```

## 2026-06-02 - Lab gate closure runner

Added a single orchestration entrypoint for the readonly premap lab gate:

```text
scripts/run_premap_lab_gate_closure.py
```

It runs the canonical closure sequence without enabling payload movement or
current WNA16 kernel argument handoff:

```text
1. refresh online-merged future native arg-slot runner evidence
2. run full no-defer lab preflight
3. run summary-only lab preflight
4. run compact preflight summary checker
5. run native prelaunch artifact checker using runner-recorded paths
```

The closure report keeps the same safety boundary:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

Validation:

```text
python scripts/run_premap_lab_gate_closure.py \
  --output-json outputs/reports/premap_lab_gate_closure.json

result:
  passed = true
  arg_slot_runner.passed = true
  full_preflight.passed = true
  summary_preflight.passed = true
  summary_check.passed = true
  native_artifact_check.passed = true
  native_artifact_check.preflight_json_source = runner_recorded
  native_artifact_check.status_json_source = runner_recorded

pytest tests/test_run_premap_lab_gate_closure.py -q:
  2 passed

pytest tests/test_run_premap_lab_gate_closure.py \
       tests/test_check_premap_online_native_stub_canary_artifacts.py \
       tests/test_check_premap_lab_preflight_summary.py \
       tests/test_run_premap_lab_preflight.py -q:
  158 passed

pytest tests -q:
  871 passed, 2 warnings
```

The same runner now also supports dispatch row-window canaries.  The latest
tail-window run keeps the full merged table resident but asks the future
dispatch/dispatch-pointer/arg-slot ABI to consume only the last active window:

```text
outputs/reports/premap_kernel_consumer/
  online_merged_future_native_arg_slot_tail_window49_canary_runner.json

merged_row_count = 1841
dispatch_row_offset = 1792
dispatch_row_limit = 1841
dispatch_active_rows = 49
dispatch_expected_program_count = 1

future_kernel_native_dispatch_consumer_row_ok_count = 49 / 49
future_kernel_native_dispatch_ptr_consumer_row_ok_count = 49 / 49
future_kernel_native_arg_slot_consumer_row_ok_count = 49 / 49
```

This validates the row-window semantics a real future launch would use while
still keeping the current WNA16 kernel arguments untouched.

Focused validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_online_merged_native_arg_slot_canary.py \
         tests/test_materialize_premap_online_merged_typed_consumer_input.py -q

10 passed
```

Default lab preflight after promoting the runner artifact to required evidence:

```text
outputs/reports/premap_lab_preflight_default_after_runner_required_gate.json

passed = true
required_evidence = 18 / 18
optional_evidence = 13 / 13
```

Full validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

851 passed, 2 warnings
```

## Latest Update: Online-Merged Future Native Arg-Slot Canary

The lab gate now requires an online-merged multi-program ABI canary:

```text
future_kernel_native_arg_slot_online_merged_multiprogram_canary_json:
  outputs/reports/premap_kernel_consumer/
    typed_consumer_stub_gpu1_online_merged_future_native_arg_slot_32tables_canary.json
```

It is generated from a merged typed-consumer input:

```text
outputs/reports/premap_kernel_consumer/
  online_merged_prelaunch_typed_consumer_input_arg_slot_32tables.json

source_count = 32 real online prelaunch typed input tables
row_count = 1841
block_threads = 256
expected_program_count = 8
```

The merged input is explicitly marked as diagnostic:

```text
source = merged_vllm_prelaunch_typed_consumer_inputs
not_a_single_vllm_launch_table = true
payload_bytes = 0
ready_credit = false
passed_to_kernel = false
changes_kernel_launch_args = false
```

GPU1 native stub result:

```text
future_kernel_native_dispatch_consumer_row_ok_count = 1841 / 1841
future_kernel_native_dispatch_ptr_consumer_row_ok_count = 1841 / 1841
future_kernel_native_arg_slot_consumer_row_ok_count = 1841 / 1841

grid_x = 8
block_x = 256
launch_threads = 2048
full_program_count = 7
last_program_active_rows = 49
inactive_lane_count = 207

future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator =
  9748c8c92c02281b
future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator =
  9748c8c92c02281b
future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator =
  9748c8c92c02281b
```

Default lab preflight now accepts this as required evidence together with the
reproducible runner evidence:

```text
outputs/reports/premap_lab_preflight_default_after_runner_required_gate.json

passed = true
required_evidence = 18 / 18
optional_evidence = 13 / 13
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_materialize_premap_online_merged_typed_consumer_input.py \
         tests/test_run_premap_lab_preflight.py -q

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

843 passed, 2 warnings
```

## Latest Update: Future Native Handle-Projection Packet Chain

The future native dispatch, dispatch-pointer packet, and arg-slot packet now
also report an ABI-independent full-row handle projection hash:

```text
future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator
future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator
future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator
```

Unlike the path-specific `hash_accumulator`, this projection hashes only the
typed handle row view:

```text
descriptor_ptr
packed_weight_descriptor
scale_metadata_handle
aux_metadata_handle
address_key_hash
expert_id
row_index
```

The artifact checker still only requires the normal row hashes to be present
and valid, because those include packet-wrapper metadata and may differ by ABI
path.  It now requires the handle-projection hashes and the single-field mirror
hashes to match across the dispatch -> dispatch_ptr -> arg_slot chain.

GPU1 standalone native-stub smoke:

```text
outputs/reports/premap_kernel_consumer/
  typed_consumer_stub_gpu1_future_native_arg_slot_handle_projection_smoke.json

row_count = 16
future_kernel_native_dispatch_consumer_row_ok_count = 16
future_kernel_native_dispatch_ptr_consumer_row_ok_count = 16
future_kernel_native_arg_slot_consumer_row_ok_count = 16

future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator =
  9eac876e3b41938b
future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator =
  9eac876e3b41938b
future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator =
  9eac876e3b41938b

payload_bytes = 0
passed_to_kernel = false
current_wna16_arg_compatible = false
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_check_premap_online_native_stub_canary_artifacts.py \
         tests/test_run_premap_lab_preflight.py \
         tests/test_premap_typed_consumer_stub.py -q

159 passed
```

Boundary remains unchanged: this is still independent native-stub and online
artifact evidence only.  The current WNA16 fused-MoE kernel does not consume
this packet chain, no payload is moved, and no kernel launch argument is passed
or mutated.

## Latest Update: Future Native Arg-Slot ABI Canary

## Latest Update: Future Native Packet-Chain Visibility Gate

The future native typed-consumer path now reports and requires explicit
packet-chain visibility for the two launch-shaped native packets that are
closest to a future kernel argument handoff:

```text
future_kernel_native_dispatch_ptr_consumer_packet_visible = true
future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible = true
future_kernel_native_dispatch_ptr_consumer_packet_chain_depth = 2

future_kernel_native_arg_slot_consumer_slot_visible = true
future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible = true
future_kernel_native_arg_slot_consumer_dispatch_packet_visible = true
future_kernel_native_arg_slot_consumer_packet_chain_depth = 3
```

These fields are emitted by the native HIP stub and required by both the lab
preflight checker and the online native-stub artifact checker.  New negative
tests reject invisible dispatch-ptr and arg-slot packet-chain evidence.

GPU1 canary:

```text
outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_arg_slot_packet_chain_visibility_canary.json

row_count = 32
future_kernel_native_dispatch_ptr_consumer_row_ok_count = 32
future_kernel_native_arg_slot_consumer_row_ok_count = 32
future_kernel_native_arg_slot_consumer_single_field_mirror_field_name =
  scale_metadata_handle
future_kernel_native_arg_slot_consumer_payload_bytes = 0
future_kernel_native_arg_slot_consumer_passed_to_kernel = false
future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible = false
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_premap_typed_consumer_stub.py \
         tests/test_run_premap_lab_preflight.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py -q

146 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

817 passed, 2 warnings
```

Boundary remains unchanged: this is still readonly/native-stub evidence only.
It does not move payload, does not mark ready credit, does not pass or mutate
the current WNA16 kernel arguments, and does not claim latency improvement.

## Latest Update: Contract-Conditioned Lab Preflight Summary

## Latest Update: Standalone Future Arg-Slot Native Canary Refresh

The independent native typed-consumer stub was rerun on GPU1 with the full
future-native arg-slot guard chain:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA
MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION
MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY
MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR
MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR
MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE
MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE
MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME
MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR
MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI
MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI
MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI
MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI
MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI
MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD
```

Artifact:

```text
outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_arg_slot_full_guard_scale_canary_latest.json

ok = true
future_kernel_native_arg_slot_consumer_checked = true
future_kernel_native_arg_slot_consumer_row_count = 1024
future_kernel_native_arg_slot_consumer_row_ok_count = 1024
future_kernel_native_arg_slot_consumer_error_count = 0
future_kernel_native_arg_slot_consumer_payload_bytes = 0
future_kernel_native_arg_slot_consumer_passed_to_kernel = false
future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible = false
future_kernel_native_dispatch_consumer_launch_geometry_checked = true
future_kernel_native_dispatch_consumer_launch_minimal_cover = true
```

The schema checker was also rerun:

```text
outputs/reports/premap_kernel_consumer/typed_consumer_schema_check_latest.json
passed = true
failures = []
rows = 4
```

Boundary is unchanged.  This is an independent native typed-consumer canary that
reads the future arg-slot ABI shape; it still does not pass the slot to the
current WNA16 fused-MoE kernel, does not move payload, and does not claim a
runtime performance result.

The lab preflight summary now reports requirement fields from the observed
default gate contract instead of reusing hard-coded defaults.  This keeps
negative contract tests readable: if a test gate intentionally flips
`kernel_side_typed_row_consumer_path_required` or
`native_typed_consumer_bridge_passed_to_kernel_required`, or the dispatch
full-table / dispatch-ptr contract flags, the summary mirrors that observed
contract while the contract checker still fails the gate.
If a contract key is missing, the summary reports that requirement as `null`
instead of silently substituting the default value; this makes broken contract
artifacts easier to read from the compact preflight status alone.
The contract parser now also rejects non-mapping `contract` payloads with a
structured `contract_type_mismatch` failure instead of raising an uncaught
`AttributeError`.  Contract values with the wrong shape, such as string
`"true"` for a boolean field, are shown as `null` in the compact summary while
the contract checker still reports the exact mismatch.

The online arg-slot full-field coverage hard-fail is also conditioned on the
observed default gate contract:

```text
future_kernel_native_arg_slot_online_total_mirror_coverage_required = true
  -> final no-defer preflight requires all four online mirror fields

future_kernel_native_arg_slot_online_total_mirror_coverage_required = false
  -> contract mismatch fails the gate, but the coverage-specific hard-fail is
     not emitted as a second, misleading failure
```

Current default preflight remains strict:

```text
output = outputs/reports/premap_lab_preflight_status_contract_summary_observed.json
passed = true
failures = []

kernel_side_typed_row_consumer_path_required = true
native_typed_consumer_bridge_required = true
default_kernel_consumer_dispatch_full_table_required = true
default_kernel_consumer_dispatch_ptr_required = true
passed_to_kernel_required = false
default_kernel_consumer_arg_slot_online_total_mirror_coverage_required = true
default_kernel_consumer_arg_slot_online_total_full_field_mirror_coverage = true
default_contract_observed_available = true
```

Validation:

```text
pytest tests/test_run_premap_lab_preflight.py -q
  65 passed

pytest tests -q
  785 passed, 2 warnings
```

Boundary is unchanged: this is a lab gate reporting/checking hardening only.
No payload is moved, no kernel launch argument is changed, and the future typed
consumer ABI is still not passed to the current WNA16 fused-MoE kernel.

The standalone native typed-consumer path now has one more future-kernel ABI
layer:

```cpp
PremapFutureKernelNativeConsumerArgSlotV1
```

This arg-slot packet points at `PremapFutureKernelNativeConsumerDispatchPtrV1`,
which points at dispatch metadata and then the typed descriptor/address table.
The canary validates ABI version, struct sizes, readonly flags, row iteration,
and single-field mirror parity through this packet chain.

Standalone smoke:

```text
typed_consumer_stub_future_arg_slot_smoke.json:
  passed = true
  future_kernel_native_arg_slot_consumer_checked = true
  future_kernel_native_arg_slot_consumer_row_count = 17
  future_kernel_native_arg_slot_consumer_row_ok_count = 17
  future_kernel_native_arg_slot_consumer_error_count = 0
  future_kernel_native_arg_slot_consumer_single_field_mirror_field_name =
    scale_metadata_handle
  future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count = 17
  future_kernel_native_arg_slot_consumer_payload_bytes = 0
  future_kernel_native_arg_slot_consumer_passed_to_kernel = false
  future_kernel_native_arg_slot_consumer_changes_kernel_launch_args = false
  future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible = false
```

Validation:

```text
pytest tests/test_premap_typed_consumer_stub.py \
  tests/test_run_premap_online_native_stub_canary.py \
  tests/test_check_premap_online_native_stub_canary_artifacts.py -q
  67 passed

pytest tests -q
  768 passed, 2 warnings
```

Boundary is unchanged: the arg-slot ABI is still an independent native canary.
It does not pass the slot to the current WNA16 fused-MoE kernel, does not move
payload, and does not claim WNA16 kernel-argument compatibility.

## Latest Update: Online Runner Status Semantics

The default lab compact status now exposes the 32-input online native runner
gate with stricter flat-field semantics.  In particular:

```text
default_kernel_consumer_dispatch_runner_artifact_check_passed:
  derived from the independent artifact evidence row
  requires present + valid JSON + passed=true + failures=[]

default_kernel_consumer_dispatch_runner_final_preflight_passed:
  requires the embedded final preflight status to pass
  requires final strict default deferred_count = 0
  requires final runtime deferred_count = 0
```

Current default compact status:

```text
premap_lab_preflight_status_default_after_online_32input_dispatch_ptr_required.json:
  passed = true
  online_input_count = 32
  online_extra_input_count = 31
  online_extra_input_passed_count = 31
  artifact_evidence_passed = true
  artifact_check_passed = true
  artifact_check_min_online_inputs = 32
  artifact_check_final_deferred_count = 0
  final_preflight_passed = true
  final_strict_default_gate_evidence_deferred_count = 0
  final_runtime_gate_evidence_deferred_count = 0
```

Validation:

```text
pytest tests/test_run_premap_lab_preflight.py -q
  54 passed

pytest tests -q
  766 passed, 2 warnings
```

Boundary is unchanged: the default lab gate validates readonly online typed
consumer evidence only.  It still does not pass typed tables to the current
WNA16 fused-MoE kernel, does not move payload, and does not claim current
WNA16 kernel-argument compatibility.

## Latest Update: Lab Preflight Dispatch Schema Summary

The default lab preflight status summary now carries the typed schema and
future dispatch ABI fields directly, so a compact preflight artifact can be used
as the lab entrypoint without expanding the full schema checker payload.

```text
premap_lab_preflight_status_dispatch_program_iteration_32required_contract_check_summary_fields.json:
  passed = true
  default_kernel_consumer_schema_name =
    fused_moe_awq_wna16_kernel_side_typed_consumer_object_v1
  default_kernel_consumer_schema_row_field_names =
    descriptor_ptr, packed_weight_descriptor, scale_metadata_handle, aux_metadata_handle
  default_kernel_consumer_schema_row_metadata_names =
    layer_id, expert_id, address_key_hash, row_order_hash, ordered_row_hash
  default_kernel_consumer_dispatch_abi_name =
    premap_future_kernel_native_consumer_dispatch_abi_v1
  default_kernel_consumer_dispatch_abi_struct =
    PremapFutureKernelNativeConsumerDispatchV1
  default_kernel_consumer_dispatch_abi_mode =
    readonly_future_kernel_native_consumer_dispatch_abi
  default_kernel_consumer_dispatch_abi_row_assignment_formula =
    row_offset + program_id * rows_per_program + lane_id
  default_kernel_consumer_dispatch_abi_current_wna16_arg_compatible = false
  payload_bytes_required = 0
  passed_to_kernel_required = false
  changes_kernel_launch_args_required = false
```

Validation:

```text
pytest tests/test_run_premap_lab_preflight.py \
  tests/test_premap_kernel_consumer_schema.py \
  tests/test_check_premap_online_native_stub_canary_artifacts.py -q
  81 passed

pytest tests -q
  747 passed, 2 warnings
```

Boundary: the summary exposes a readonly future dispatch ABI contract only. It
does not indicate a live WNA16 argument mutation path.

## Latest Update: Review Closure for Dispatch Evidence Gate

The post-hardening code review found no blocker and one low-severity coverage
gap.  The missing regression tests are now covered:

```text
preflight_strict_default_gate_evidence_rows_missing:
  covered by non-list rows regression

preflight_strict_default_gate_evidence_deferred_labels_count_mismatch:
  covered by deferred_count != deferred label count regression
```

Validation:

```text
pytest tests/test_check_premap_online_native_stub_canary_artifacts.py -q
  29 passed

pytest tests -q
  747 passed, 2 warnings
```

The stricter checker still accepts the real dispatch-window online canary and
default lab status:

```text
online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input_post_review_test_patch.json:
  passed = true
  failures = []
  min_online_inputs = 32
  runner_online_prelaunch_input_check_count = 32
  require_all_field_mirror_stubs = true
  future_native_dispatch rows = 174 / 174

schema_check_post_review_test_patch.json:
  passed = true
  failures = []
  schema = fused_moe_awq_wna16_kernel_side_typed_consumer_object_v1
```

Boundary remains unchanged: this is still readonly future-native typed ABI
evidence.  It is not a live WNA16 kernel-argument pass, does not dereference
payload, and does not claim compatibility with the current WNA16 fused-MoE
argument list.

## Latest Update: Dispatch ABI Gate Hardening

The dispatch-shaped future-native ABI gate is now stricter about the evidence
chain used before any lab integration:

```text
artifact checker:
  requires preflight.runtime_gate_evidence_scan
  requires preflight.strict_gate_evidence_checks.default_readonly_gate
  requires both deferred_count values to be present and consistent
  requires strict default deferred evidence labels to match status labels
  covers multi-program dispatch windows with both zero and nonzero row offsets

lab preflight:
  rejects defer_online_prelaunch_artifact_evidence without runner defer
  rejects runner+artifact double defer in normal lab preflight
```

The real dispatch-window 32-input online canary remains valid under the new
checks:

```text
online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input.json:
  passed = true
  failures = []
  require_all_field_mirror_stubs = true
  min_online_inputs = 32
```

The default post-review lab preflight also remains clean:

```text
premap_lab_preflight_post_review_latest_status.json:
  passed = true
  deferred_online_prelaunch_runner_evidence = false
  deferred_online_prelaunch_artifact_evidence = false
  runtime_gate_evidence_deferred_count = 0
  strict_default_gate_evidence_deferred_count = 0
  payload_bytes_required = 0
  passed_to_kernel_required = false
  changes_kernel_launch_args_required = false
```

Validation:

```text
pytest tests/test_check_premap_online_native_stub_canary_artifacts.py \
  tests/test_run_premap_lab_preflight.py -q
  70 passed

pytest tests -q
  745 passed, 2 warnings
```

Boundary: this remains a readonly future-kernel consumer path.  It validates
the future dispatch ABI/evidence chain, but it still does not pass typed tables
to the current WNA16 fused-MoE kernel, does not dereference payload, and does
not claim WNA16 kernel-argument compatibility.

## Previous Update: Four-Field Online Future Native Launch ABI Gate

## Latest Update: Four-Field Online Future Native Launch ABI Gate

The launch-shaped future-native ABI is now wired into the online prelaunch
native-stub runner and the default lab preflight gate.  The runner uses the
existing GPU1 Dolly-128 AWQ online prelaunch export and checks 16 exported
typed-table inputs against the independent native stub suite.  The launch ABI
now checks the base launch consumer plus descriptor, packed-weight, scale, and
aux-metadata mirrors.

Evidence:

```text
online_prelaunch_native_stub_canary_runner_future_native_launch_abi_16_128export.json:
  passed = true
  failures = []
  runner_online_prelaunch_input_check_count = 16
  runner_online_prelaunch_input_extra_check_count = 15
  runner_online_prelaunch_input_extra_check_passed_count = 15

online_prelaunch_native_stub_canary_artifact_check_future_native_launch_abi_16_128export.json:
  passed = true
  failures = []
  require_all_field_mirror_stubs = true
  runner_future_kernel_native_consumer_stub_row_count = 174
  runner_future_kernel_native_consumer_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_descriptor_ptr_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_packed_weight_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_aux_metadata_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_launch_stub_row_count = 174
  runner_future_kernel_native_consumer_launch_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_count = 174
  runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_launch_packed_weight_stub_row_count = 174
  runner_future_kernel_native_consumer_launch_packed_weight_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_count = 174
  runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_ok_count = 174
  stage1_deferred_count = 1
  final_deferred_count = 0
  status_deferred_count = 0
```

The default lab preflight now points
`native_typed_consumer_online_prelaunch_canary_runner_json` at that launch ABI
runner artifact and validates the launch-consumer summary:

```text
premap_lab_preflight_status_future_native_launch_abi_16_128export.json:
  passed = true
  required_evidence = 11 / 11
  optional_evidence = 4 / 4
  runtime_gate_evidence_deferred_count = 0
  payload_bytes_required = 0
  passed_to_kernel_required = false
  changes_kernel_launch_args_required = false
```

Validation:

```text
pytest tests/test_run_premap_lab_preflight.py \
  tests/test_run_premap_online_native_stub_canary.py \
  tests/test_check_premap_online_native_stub_canary_artifacts.py -q
  53 passed

pytest tests -q
  706 passed, 2 warnings
```

Boundary: this is still a readonly, live-disabled future-kernel ABI gate.  It
does not pass the typed table to the current WNA16 fused-MoE kernel, does not
dereference payload, and does not claim current WNA16 kernel-argument
compatibility.

## Previous Update: Future Native Launch ABI Stub

The typed premap consumer now has a more kernel-like native ABI layer:

```text
PremapFutureKernelNativeConsumerParamsV1
  -> PremapFutureKernelNativeConsumerLaunchV1
  -> typed_consumer_future_native_launch_kernel
```

This is still an independent native consumer stub, not a WNA16 kernel-arg
mutation.  It keeps the lab safety boundary explicit:

```text
payload_bytes = 0
payload_deref_allowed = false
passed_to_kernel = false
kernel_arg_pass_allowed = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

GPU1 canary on the exported Dolly-128 AWQ prelaunch typed-table input:

```text
typed_consumer_stub_gpu1_future_native_launch_consumer_scale_mirror_canary.json:
  passed = true
  row_count = 174
  row_ok_count = 174
  future_kernel_native_consumer_checked = true
  future_kernel_native_consumer_row_ok_count = 174
  future_kernel_native_launch_consumer_checked = true
  future_kernel_native_launch_consumer_row_ok_count = 174
  future_kernel_native_launch_consumer_single_field_mirror_checked = true
  future_kernel_native_launch_consumer_single_field_mirror_field_name =
    scale_metadata_handle
  future_kernel_native_launch_consumer_single_field_mirror_row_ok_count = 174
```

The schema artifact was updated with the launch ABI fields and passes the
schema checker:

```text
typed_consumer_schema_check_future_native_launch_abi.json:
  passed = true
  failures = []
  macro_count = 22
```

Boundary: this is a future-kernel-argument shape check only.  It does not make
the current WNA16 fused-MoE kernel consume the typed table yet.

## Previous Update: Future Native ABI Online Runner Gate

The future-native consumer ABI is now part of the online prelaunch native-stub
runner and artifact checker.  The runner still uses an exported online
prelaunch typed-table input; it does not reroute any live WNA16 kernel argument
and does not dereference payload.  It now validates:

```text
native_stub_future_kernel_native_consumer_abi:
  single_field = scale_metadata_handle

native_stub_future_kernel_native_consumer_descriptor_ptr_mirror:
  single_field = descriptor_ptr

native_stub_future_kernel_native_consumer_packed_weight_mirror:
  single_field = packed_weight_descriptor

native_stub_future_kernel_native_consumer_aux_metadata_mirror:
  single_field = aux_metadata_handle
```

Online runner evidence using the existing GPU1 16-input / Dolly-128 exported
online prelaunch trace slice:

```text
online_prelaunch_native_stub_canary_runner_future_native_consumer_abi_16_128export.json:
  passed = true
  failures = []
  runner_online_prelaunch_input_check_count = 16
  runner_online_prelaunch_input_extra_check_count = 15
  runner_online_prelaunch_input_extra_check_passed_count = 15
  future_kernel_native_consumer_stub_summary:
    row_count = 174
    row_ok_count = 174
    future_kernel_native_consumer_checked = true
    future_kernel_native_consumer_error_count = 0
    single_field = scale_metadata_handle
    single_field_row_ok_count = 174
  future_kernel_native_consumer_descriptor_ptr_stub_summary:
    row_ok_count = 174
    single_field = descriptor_ptr
  future_kernel_native_consumer_packed_weight_stub_summary:
    row_ok_count = 174
    single_field = packed_weight_descriptor
  future_kernel_native_consumer_aux_metadata_stub_summary:
    row_ok_count = 174
    single_field = aux_metadata_handle
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
  current_wna16_arg_compatible = false
```

Strict lab preflight now uses that 16-input future-native runner as the
required online-prelaunch evidence:

```text
premap_lab_preflight_status_future_native_consumer_abi_16_128export.json:
  passed = true
  required_evidence = 11 / 11
  optional_evidence = 4 / 4
  native_typed_consumer_online_prelaunch_canary_runner_json =
    online_prelaunch_native_stub_canary_runner_future_native_consumer_abi_16_128export.json
```

Earlier smoke evidence using the GPU1 1-sample prelaunch export:

```text
online_prelaunch_native_stub_canary_runner_future_native_consumer_abi_1_default_export.json:
  passed = true
  failures = []
  runner_online_prelaunch_input_check_count = 1
  future_kernel_native_consumer_stub_summary:
    row_count = 204
    row_ok_count = 204
    future_kernel_native_consumer_checked = true
    future_kernel_native_consumer_error_count = 0
    single_field = scale_metadata_handle
    single_field_row_ok_count = 204
  future_kernel_native_consumer_descriptor_ptr_stub_summary:
    row_ok_count = 204
    single_field = descriptor_ptr
  future_kernel_native_consumer_packed_weight_stub_summary:
    row_ok_count = 204
    single_field = packed_weight_descriptor
  future_kernel_native_consumer_aux_metadata_stub_summary:
    row_ok_count = 204
    single_field = aux_metadata_handle
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
  current_wna16_arg_compatible = false
```

Artifact checker evidence for the promoted 16-input gate:

```text
online_prelaunch_native_stub_canary_artifact_check_future_native_consumer_abi_16_128export.json:
  passed = true
  failures = []
  require_all_field_mirror_stubs = true
  runner_online_prelaunch_input_check_count = 16
  runner_online_prelaunch_input_extra_check_count = 15
  runner_online_prelaunch_input_extra_check_passed_count = 15
  runner_future_kernel_native_consumer_stub_row_count = 174
  runner_future_kernel_native_consumer_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_descriptor_ptr_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_packed_weight_stub_row_ok_count = 174
  runner_future_kernel_native_consumer_aux_metadata_stub_row_ok_count = 174
  stage1_deferred_count = 1
  final_deferred_count = 0
  status_deferred_count = 0
```

Validation:

```text
pytest tests/test_premap_typed_consumer_stub.py \
  tests/test_premap_kernel_consumer_schema.py \
  tests/test_run_premap_lab_preflight.py \
  tests/test_run_premap_online_native_stub_canary.py \
  tests/test_check_premap_online_native_stub_canary_artifacts.py -q
  78 passed

pytest tests/test_run_premap_lab_preflight.py \
  tests/test_run_premap_online_native_stub_canary.py \
  tests/test_check_premap_online_native_stub_canary_artifacts.py -q
  53 passed

pytest tests -q
  704 passed, 2 warnings
```

This promotes the standalone future-native ABI canary into an online
prelaunch artifact gate.  It remains readonly and live-disabled: no payload,
no ready credit, no kernel-argument pass, and no compatibility claim with the
current WNA16 argument list.

## Latest Update: Future-Args Compatible Consumer Path Gate

The next canary layer after `future_kernel_consumer_args` is now implemented
and enforced by the lab preflight.  It does not reinterpret the typed table as
an existing WNA16 argument; it builds a future argument envelope and then routes
that envelope through an independent compatible-consumer path:

```text
future_kernel_args_compatible_consumer_path:
  name = premap_future_kernel_args_compatible_consumer_path_v1
  mode = readonly_future_kernel_args_to_compatible_consumer_path
  source = premap_future_kernel_side_consumer_args_v1
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
  current_wna16_arg_compatible = false
```

Evidence:

```text
typed_consumer_stub_gpu1_future_kernel_args_compatible_path_canary.json:
  passed = true
  row_count = 174
  row_ok_count = 174
  future_kernel_consumer_args_checked = true
  future_kernel_consumer_args_row_ok_count = 174
  future_kernel_args_compatible_consumer_path_checked = true
  future_kernel_args_compatible_consumer_path_row_ok_count = 174
  future_kernel_args_compatible_consumer_path_error_count = 0
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
  current_wna16_arg_compatible = false

online_prelaunch_native_stub_canary_artifact_check_future_args_compatible_path_16_128export.json:
  passed = true
  min_online_inputs = 16
  runner_online_prelaunch_input_check_count = 16
  runner_online_prelaunch_input_extra_check_passed_count = 15
  runner_future_kernel_args_compatible_path_stub_row_count = 174
  runner_future_kernel_args_compatible_path_stub_row_ok_count = 174

premap_lab_preflight_status_future_args_compatible_path_16_128export.json:
  passed = true
  default_contract_passed = true
  default_kernel_consumer_schema_passed = true
  required_evidence = 11 / 11
  optional_evidence = 4 / 4

pytest tests/test_premap_typed_consumer_stub.py \
  tests/test_run_premap_online_native_stub_canary.py \
  tests/test_check_premap_online_native_stub_canary_artifacts.py \
  tests/test_run_premap_lab_preflight.py -q
  67 passed
```

This promotes the future-argument-to-compatible-consumer boundary into the lab
default preflight gate.  It is still a readonly native stub/ABI canary only:
no payload dereference, no ready credit, no current WNA16 kernel argument
mutation, and no kernel launch argument change.

## Latest Update: Future Native Consumer ABI Stub

The next independent native ABI layer is now in place.  Instead of routing
through the current WNA16 argument list, the stub constructs a standalone
future-kernel-shaped parameter object:

```text
future_kernel_native_consumer_abi:
  name = premap_future_kernel_native_consumer_abi_v1
  struct = PremapFutureKernelNativeConsumerParamsV1
  mode = readonly_future_kernel_native_consumer_abi
  source = premap_typed_handle_table_soa_fields
  fields =
    descriptor_ptr
    packed_weight_descriptor
    scale_metadata_handle
    aux_metadata_handle
    expert_id
    address_key_hash
    row_count / column_count / lifetime_epoch
    row_order_hash / ordered_row_hash
    field_mask / single_field_mirror_kind
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
  current_wna16_arg_compatible = false
```

This ABI reads the same typed handle table in a shape closer to a future kernel
argument structure, but it remains an independent HIP/native stub.  It is not
passed into the live WNA16 fused-MoE kernel.

GPU1 canary evidence on the online-exported 128-sample prelaunch table:

```text
typed_consumer_stub_gpu1_future_native_consumer_scale_mirror_canary.json:
  passed = true
  future_kernel_native_consumer_row_count = 174
  future_kernel_native_consumer_row_ok_count = 174
  single_field = scale_metadata_handle
  single_field_row_ok_count = 174

typed_consumer_stub_gpu1_future_native_consumer_packed_weight_mirror_canary.json:
  passed = true
  future_kernel_native_consumer_row_ok_count = 174
  single_field = packed_weight_descriptor
  single_field_row_ok_count = 174

typed_consumer_stub_gpu1_future_native_consumer_descriptor_ptr_mirror_canary.json:
  passed = true
  future_kernel_native_consumer_row_ok_count = 174
  single_field = descriptor_ptr
  single_field_row_ok_count = 174

typed_consumer_stub_gpu1_future_native_consumer_aux_metadata_mirror_canary.json:
  passed = true
  future_kernel_native_consumer_row_ok_count = 174
  single_field = aux_metadata_handle
  single_field_row_ok_count = 174
```

For all four field canaries:

```text
future_kernel_native_consumer_error_count = 0
future_kernel_native_consumer_single_field_mirror_error_count = 0
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

Validation:

```text
pytest tests/test_premap_kernel_consumer_schema.py \
  tests/test_premap_typed_consumer_stub.py \
  tests/test_run_premap_lab_preflight.py -q
  59 passed

premap_lab_preflight_status_future_native_consumer_abi_canary.json:
  passed = true
  default_contract_passed = true
  default_kernel_consumer_schema_passed = true
  required_evidence = 11 / 11
  optional_evidence = 4 / 4
```

The next gate is to wire this native ABI stub into the online prelaunch runner
and artifact checker in the same way as the future-args compatible path, while
keeping it default-disabled and still outside the live WNA16 kernel launch.

## Latest Update: Future Kernel Args Lab Preflight Gate

The future kernel-side consumer argument object is now part of the default lab
preflight gate instead of a loose side canary:

```text
future_kernel_consumer_args:
  name = premap_future_kernel_side_consumer_args_v1
  mode = readonly_future_kernel_consumer_args
  source = premap_kernel_side_typed_consumer_launch_envelope_v1
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
  current_wna16_arg_compatible = false
  single_field_mirror_required = true
  single_field_mirror_field = scale_metadata_handle
```

The default lab gate now points at the online runner artifact that contains
`future_kernel_args_stub_summary`, and `run_premap_lab_preflight.py` validates
that summary plus the per-input `native_stub_future_kernel_consumer_args`
outputs.  This proves the online-exported typed table can be wrapped in the
future kernel-argument shape and consumed by the native stub while keeping the
current WNA16 kernel untouched.

Validation:

```text
premap_lab_preflight_future_kernel_args_gate.json:
  passed = true
  failures = []
  required_evidence = 11 / 11
  future_kernel_consumer_args_required = true

pytest tests/test_run_premap_lab_preflight.py -q
  33 passed

pytest tests -q
  700 passed, 2 warnings
```

Second-field canary on GPU1:

```text
typed_consumer_stub_gpu1_future_kernel_args_packed_weight_mirror_canary.json:
  passed = true
  row_count = 174
  row_ok_count = 174
  future_kernel_consumer_args_checked = true
  future_kernel_consumer_args_row_ok_count = 174
  future_kernel_consumer_args_single_field_mirror_field_name =
    packed_weight_descriptor
  future_kernel_consumer_args_single_field_mirror_row_ok_count = 174
  future_kernel_consumer_args_single_field_mirror_error_count = 0
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
```

This is still a readonly ABI/native-stub gate.  It does not authorize live
kernel-argument mutation or payload dereference.

## Latest Update: Online Typed Row Consumer Prelaunch Gate

The vLLM prelaunch readonly consumer shim now emits and aggregates a stricter
typed row consumer path:

```text
kernel_side_typed_row_consumer_path:
  mode = readonly_typed_row_consumer_path
  path_name = premap_kernel_side_typed_consumer_path_v1
  source = vllm_prelaunch_prepared_handle_table
  schema_hash = premap_descriptor_consumer_handle_table_v1
  column_count = 4
  row_ok_count = row_count
  error_count = 0
  failure_count = 0
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
  current_wna16_arg_compatible = false
```

This is one boundary closer to the future kernel consumer than the native-stub
package canary: it validates row-by-row typed-table traversal in the online
prelaunch path, but still does not invoke the live WNA16 kernel with any new
argument and does not move payload.

Validation:

```text
pytest tests/test_check_premap_longrun_audit_gate.py \
  tests/test_runtime_shadow_log.py tests/test_vllm_router_shadow_sink.py -q
  168 passed

pytest tests -q
  693 passed, 2 warnings
```

Online smoke evidence:

```text
trace:
  data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary/

gate:
  longrun_audit_gate_typed_row_consumer_path_smoke.json
  passed = true

typed row consumer path:
  checked_count = 640
  ready_count = 640
  row_count = 9794
  row_ok_count = 9794
  error_count = 0
  failure_count = 0
  payload_bytes = 0
  passed_to_kernel_count = 0
  kernel_arg_violation_count = 0
  current_wna16_arg_compatible_count = 0
```

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

## Latest Update: Single-Field Handle Handoff Canary Lab Gate

The typed premap/prelaunch path now has a stricter lab-default precondition:

```text
single_field_handle_handoff_canary:
  mode = readonly_single_field_handle_handoff_canary
  field = scale_metadata_handle
  source = semantic_handle_table
  mirror_mode = readonly_scale_metadata_handle_mirror
  mirror_field = scale_metadata_handle
  mirror_source = semantic_handle_table
  mirror_schema = fused_moe_awq_wna16_kernel_side_typed_consumer_object_v1
  kernel_side_typed_consumer_compatible = true
  current_wna16_arg_compatible = false
  live_enabled = false
  block_reason = single_field_handoff_live_disabled
  payload_bytes = 0
  ready_credit = false
  passed_to_kernel = false
  changes_kernel_launch_args = false
  live_compatible_with_current_wna16_args = false
```

This is the first one-field-at-a-time handoff canary.  It is explicitly a
readonly `scale_metadata_handle` mirror for the future typed kernel-side
consumer schema.  It does not replace a live kernel argument and does not treat
prepared handle tuples as current WNA16-compatible tensor args.

New 128-sample GPU1 strict audit evidence:

```text
trace:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/

runtime_shadow rows:
  premap_summary = 10,195
  premap_consumer_mapping = 10,195

strict checker:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate_single_field_canary.json

single-field canary:
  checked_count = 10,195
  ready_count = 10,195
  row_count = 110,898
  field_handle_count = 110,898
  field_handle_nonzero_count = 110,898
  field_handle_zero_count = 0
  parity_ok_count = 110,898
  parity_mismatch_count = 0
  mirror_mode = readonly_scale_metadata_handle_mirror
  mirror_ready_count = checked_count
  mirror_field = scale_metadata_handle
  mirror_source = semantic_handle_table
  kernel_side_typed_consumer_compatible_count = checked_count
  current_wna16_arg_compatible_count = 0
  live_enabled_count = 0
  blocked_count = 10,195
  payload_bytes = 0
  ready_credit_count = 0
  passed_to_kernel_count = 0
  kernel_arg_violation_count = 0
  live_compatible_with_current_wna16_args_count = 0
```

The default lab gate artifact now includes:

```text
configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml

contract:
  single_field_handle_handoff_canary_required = true
  single_field_handle_handoff_canary_field = scale_metadata_handle
  single_field_handle_handoff_canary_mirror_mode =
    readonly_scale_metadata_handle_mirror
  single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible =
    true
  single_field_handle_handoff_canary_current_wna16_arg_compatible = false

evidence:
  strict_single_field_handle_handoff_canary_128_gate_json =
    data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate_single_field_canary.json
```

`scripts/run_premap_lab_preflight.py` now requires and validates that evidence
as part of the default lab gate.  The actual lab preflight passes with the
updated mirror contract:

```text
/tmp/premap_lab_preflight_one_field_canary.json
  passed = true
  required_evidence = 10 / 10 present and passed
```

Validation:

```text
pytest tests/test_runtime_premap.py tests/test_runtime_shadow_log.py \
  tests/test_vllm_router_shadow_sink.py \
  tests/test_check_premap_longrun_audit_gate.py \
  tests/test_run_premap_lab_preflight.py -q
  219 passed

pytest tests -q
  679 passed, 2 warnings
```

Next gate:

```text
Implement a real kernel-side compatible consumer schema/path before any live
field replacement.  The current WNA16 launch must remain untouched until the
native consumer path can read the typed table through an ABI that is not a
tuple/tensor disguise.
```

## Previous Update: ROCm Upstream FlashAttention Decoder Adapter

The custom ROCm FlashAttention 2.x package is installed in the TRY env and can
be imported by vLLM.  Environment variables alone do not make vLLM choose this
package for decoder attention; vLLM must receive an explicit
`attention_config.backend: FLASH_ATTN`, and its decoder ABI must be adapted.

New configs:

```text
configs/model/qwen3_6_35b_a3b_awq_4bit_fa_probe.yaml
configs/model/qwen3_6_35b_a3b_awq_4bit_fa_force.yaml
configs/trace/router_mtp_trace_smoke_text_awq_vllm_gpu1_decode_independent_prompt_smoke1_gen16_fa_force.yaml
configs/trace/router_mtp_trace_smoke_text_awq_vllm_gpu1_decode_independent_prompt_smoke8_gen64_fa_force.yaml
```

`vllm.attention_config` is now passed through to `LLM(...)`.  With
`attention_config.backend: FLASH_ATTN`, vLLM logs:

```text
Using FLASH_ATTN backend (selected via --attention-backend).
Using FlashAttention version None
```

The upstream ROCm FA2 package does not implement the same decoder ABI as vLLM's
native FlashAttention backend:

```text
varlen + block_table:
  fails because AMD Triton FA2 varlen_fwd does not support block_table.

flash_attn_with_kvcache:
  executes, but does not match the current vLLM paged-KV semantics for this
  Qwen3.6 AWQ path and produced bad text in smoke.
```

The current repo-local adapter therefore resolves vLLM paged-KV metadata into a
dense varlen K/V stream and calls standard `flash_attn_varlen_func`.  This is a
correctness adapter only; it materializes K/V and is not a performance path.

Evidence:

```text
1-sample gen16 forced decoder FA:
  output matches the base ROCM_ATTN smoke text exactly.

8-sample gen64 forced decoder FA:
  backend = FLASH_ATTN
  generated text is coherent across all 8 prompts.
  exact text match vs base = 4 / 8
  matching first-80-character prefix = 5 / 8
  generate wall time:
    base ROCM_ATTN: 37.97s
    forced FA correctness adapter: 112.28s
```

This proves that vLLM decoder paged-KV metadata can be mapped into an upstream
ROCm FA2 decoder call in a semantically valid way.  It does not prove a runtime
speedup.  A performance-capable backend would need a native paged varlen ABI or
a direct FA decoder path that consumes vLLM's block table without materializing
K/V.

Decision:

```text
ROCm upstream FA2 decoder adapter:
  status = diagnostic / correctness-only
  reason = semantic bridge works, but the current adapter materializes paged KV
           and is much slower than vLLM's ROCM_ATTN path.

Do not use this branch for the main runtime performance claim.
Do not continue tuning it unless a native paged-KV/block_table FA ABI becomes
available.
```

Next mainline experiment focus:

```text
Return to the MTP prefetch / premap path.

P0:
  keep the typed premap descriptor/address preparation gate as the lab
  precondition.

P0:
  connect the prepared descriptor/address object to the vLLM prelaunch consumer
  in readonly mode:
    payload_bytes = 0
    ready_credit = 0
    changes_kernel_launch_args = false
    kernel_arg_pass = false

P1:
  run production-like action replay / controlled manager evidence under the
  existing bounded-cache and capacity gates, not attention-backend experiments.

P1:
  only after native typed consumer compatibility is proven, consider one
  field-at-a-time descriptor/address handoff canaries.
```

Validation:

```text
pytest tests -q
  670 passed, 2 warnings
```

## Typed Kernel-Side Premap Consumer Gates

The future native consumer ABI is now documented and machine-checked:

```text
schema:
  configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml
doc:
  docs/premap_kernel_consumer_schema.md
checker:
  scripts/check_premap_kernel_consumer_schema.py
```

The schema explicitly models `descriptor_ptr`,
`packed_weight_descriptor`, `scale_metadata_handle`, `aux_metadata_handle`,
and row metadata as a readonly struct-of-arrays table.  It is not treated as
the existing WNA16 kernel arg list.  Debug support is macro-gated one feature
at a time; payload dereference and kernel-arg passing macros are forbidden in
the lab-default gate.

Native stub evidence:

```text
stub:
  microbench/premap_kernel_consumer/premap_typed_consumer_stub.hip
runner:
  scripts/run_premap_typed_consumer_stub.py
schema hash:
  c1384d55958c9aa78b07b4ee3e9094f835ec1ca4c61bd7e9613c01ceb8275e98
gpu1 smoke:
  rows = 4096
  macros =
    MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA
    MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION
    MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY
    MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME
    MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR
  row_ok_count = 4096
  error_count = 0
  typed_schema_hash_hi = c1384d55958c9aa7
  typed_schema_hash_lo = 613c01ceb8275e98
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
gpu1 missing-aux input bridge:
  rows = 4
  aux_metadata_handle omitted from JSON input
  native table run with aux pointer omitted / nullptr
  row_ok_count = 4
  error_count = 0
gpu1 manager-table bridge:
  source = ControlledPremapAddressManager.build_kernel_arg_shadow_table_object_readonly
  exported via PremapKernelArgShadowTableObject.to_native_typed_consumer_input_dict()
  rows = 2
  native table run with aux pointer omitted / nullptr
  row_ok_count = 2
  error_count = 0
  payload_bytes = 0
  passed_to_kernel = false
```

This only proves that a native HIP consumer can read the future typed ABI shape.
The stub also supports a binary-prefix input bridge generated from JSON fields,
and the runtime manager can now export a prepared shadow table object into that
same native input shape.  This is the first bridge from the Python runtime
prepared table to a native consumer stub, but it is still disconnected from the
live vLLM prelaunch hook and does not replace the WNA16 kernel.

The HIP stub schema hash is injected by `scripts/run_premap_typed_consumer_stub.py`
from the project runtime schema constant instead of being hardcoded in the stub.
The lab preflight now requires the default readonly gate to explicitly reference
the typed schema artifact instead of silently falling back to a default path.
The schema checker enforces artifact identity, compile guard, exact row-field
order, metadata shape/source/dtype, optional `aux_metadata_handle` nullability,
and forbidden macro defaults.

The default lab gate now requires a readonly typed kernel-side consumer object:

```text
mode = readonly_kernel_side_typed_consumer_object
consumer_connected = false
live_enabled = false
live_eligible = false
payload_bytes = 0
passed_to_kernel = 0
changes_kernel_launch_args = 0
```

Two explicit canary branches are documented separately:

```text
connected-but-blocked canary:
  consumer_connected = true
  live_enabled = true
  block_reason = kernel_side_typed_consumer_kernel_arg_pass_disabled

live-kernel-pass negative canary:
  runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled = true
  live adapter records current WNA16 tensor-arg incompatibility
  typed object remains readonly and not passed to kernel

real-kernel-arg-mutation negative canary:
  runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled = true
  requires --allow-incompatible-real-kernel-arg-mutation-canary
  remains excluded from lab-default gates until a compatible typed kernel schema exists

prepared-table candidate dry-run canary:
  may resolve candidate fields from prepared handles for parity/type diagnostics
  remains dry-run only and is guarded as a canary, not a lab-default gate
```

These canaries use `min_reuse_rate = 0.0` because they are 1-sample contract
checks, not capacity/reuse/performance gates.  The default 128-sample lab gate
retains the stricter long-run reuse/capacity checks.

Default lab-gate refresh:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml
output:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
manifest rows = 128
runtime_shadow rows = 20,390
gate:
  longrun_audit_gate_typed_consumer_object_128.json
  passed = true
  failures = []
typed consumer:
  checked = 10,195
  typed_object_ready = 10,195
  passed_to_kernel = 0
  kernel_arg_violation = 0
  live_compatible_with_current_wna16_args = 0
runtime flags:
  kernel_arg_pass_enabled = false
  real_kernel_arg_mutation_enabled = false
manager:
  premap_address_reuse_rate_mean = 0.982739
  premap_address_eviction_pressure_mean = 0.0
  resident_count_max = 10,127
```

This refresh confirms the non-canary default path remains stable after the
live/pass/mutation canaries were tightened.

Online native typed-consumer bridge gate:

```text
gate:
  longrun_audit_gate_live_connected_readonly.json
  passed = true
  failures = []
checker:
  --require-native-typed-consumer-bridge
native bridge:
  mode = readonly_native_typed_consumer_bridge_check
  checked / ok = 10,195 / 10,195
  row_count = 110,898
  column_count_min/max = 4 / 4
  required_handle_nonzero = 332,694
  required_handle_zero = 0
  optional_handle_nonzero = 110,898
  optional_handle_zero = 0
  expert_id_valid = 110,898
  expert_id_invalid = 0
  address_key_hash_nonzero = 110,898
  failure_count = 0
  payload_bytes = 0
  passed_to_kernel = 0
  kernel_arg_violation = 0
```

This promotes the native bridge from offline stub evidence to an online
prelaunch-consumer contract.  The runtime shim now converts the prepared
readonly handle table into the future native-consumer input shape and validates
row/field parity at the online boundary.  The current WNA16 fused-MoE launch is
still unchanged: no payload is moved, no ready credit is granted, and no kernel
argument is passed or mutated.

The lab preflight is now also a typed-evidence gate, not just a path/schema
check.  `scripts/run_premap_lab_preflight.py` requires the default readonly
runtime gate to reference both:

```text
strict_kernel_side_typed_consumer_object_128_gate_json
strict_kernel_side_typed_consumer_object_128_selfcheck_json
strict_native_typed_consumer_bridge_128_gate_json
native_typed_consumer_bridge_smoke_json
```

and verifies that both JSON artifacts are parseable objects with:

```text
passed = true
failures = []
```

## Consumer-view layout is now an explicit lab-gate requirement

The premap lab gate now requires child window-sweep checks to prove the
future native consumer-view ABI layout, not only the presence of consumer-view
row fields.

Both strict checker outputs now expose:

```text
require_child_consumer_view_layout = true
```

and the top-level lab gate rejects artifacts where either:

```text
window_sweep_check.require_child_consumer_view_layout != true
all_field_window_sweep_check.require_child_consumer_view_layout != true
```

This keeps the current handoff at the same safety boundary:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

Verification:

```text
python scripts/run_premap_lab_gate_verify.py \
  --output-json outputs/reports/premap_lab_gate_verify.json

passed = true
window_sweep_check.require_child_consumer_view_layout = true
all_field_window_sweep_check.require_child_consumer_view_layout = true

python scripts/check_premap_lab_gate_verify.py \
  outputs/reports/premap_lab_gate_verify.json \
  --output-json outputs/reports/premap_lab_gate_verify.check.json

passed = true
failures = []

python -m pytest \
  tests/test_check_premap_online_merged_native_arg_slot_window_sweep.py \
  tests/test_check_premap_online_merged_native_arg_slot_all_field_window_sweep.py \
  tests/test_run_premap_lab_gate_verify.py \
  tests/test_check_premap_lab_gate_verify.py -q

35 passed

python -m pytest tests -q

929 passed, 2 warnings
```

Malformed evidence paths fail closed (`missing_evidence_path`, `missing_file`,
`not_file`, `read_failed`, `invalid_json`, `json_not_object`, `not_passed`, or
`failures_not_empty`).  This makes the typed-consumer-object lab gate a single
machine precondition rather than a pair of manually ordered commands.

The premap kernel-arg handoff path now includes a live-disabled kernel-side
consumer schema adapter:

```text
prepared descriptor/address table
-> kernel-arg shadow table
-> kernel-arg mirror
-> prelaunch launch-schema mirror
-> typed semantic handle adapter
-> kernel-side consumer schema adapter
```

The semantic handle adapter proves the prepared handle table has typed
descriptor/address fields.  The kernel-side adapter is one boundary closer to
the future consumer: it gives that consumer a stable schema name/hash/field
count and explicit liveness flags, but keeps the runtime no-op:

```text
mode = readonly_kernel_side_consumer_schema_adapter
kernel-side schema name/hash/field count match
semantic adapter hash present
table object hash and launch-schema mirror hash present
required source hits = row_count * 3
optional source hits + misses = row_count
handle field reads = row_count * 4
consumer_schema_present = true
consumer_connected = false
live_enabled = false
live_eligible = false
blocked = true
block_reason = kernel_side_consumer_live_disabled
payload_bytes = 0
passed_to_kernel = 0
changes_kernel_launch_args = 0
live_compatible_with_current_wna16_args = 0
```

The checker now supports:

```bash
--require-kernel-side-consumer-schema-adapter
```

and the config loader can require:

```yaml
kernel_side_consumer_schema_adapter_required: true
```

This is still a live-disabled schema gate.  It does not pass any new argument
to the current fused-MoE/AWQ kernel.

Validation:

```text
pytest tests/test_runtime_shadow_log.py \
       tests/test_check_premap_longrun_audit_gate.py \
       tests/test_vllm_premap_capacity_gate.py -q
163 passed

pytest tests -q
603 passed, 2 warnings
```

## Previous Update: Typed Semantic Handle Adapter Dry-Run Gate

The premap kernel-arg handoff path includes a typed semantic handle adapter:

```text
prepared descriptor/address table
-> kernel-arg shadow table
-> kernel-arg mirror
-> prelaunch launch-schema mirror
-> typed semantic handle adapter
```

This adapter is explicitly a future kernel-side schema contract, not a live
WNA16 tensor-argument replacement.  The checker requires:

```text
mode = readonly_kernel_arg_semantic_handle_adapter
semantic schema name/hash/field count match
table object hash and launch-schema mirror hash present
required source hits = row_count * 3
optional source hits + misses = row_count
handle field reads = row_count * 4
payload_bytes = 0
passed_to_kernel = 0
changes_kernel_launch_args = 0
live_compatible_with_current_wna16_args = 0
```

The gate is also dependency-strict: if semantic adapter fields appear, the
prelaunch launch-schema mirror must also be present.  This prevents a semantic
handle table from being interpreted outside the launch-boundary schema it is
meant to describe.

Validation:

```text
GPU1 128-sample strict audit:
  longrun_audit_gate_semantic_handle_adapter.json
  passed = true
  failures = []

semantic adapter checked / ready = 10,195 / 10,195
row_count = 110,898
required_source_miss_count = 0
payload_bytes / passed_to_kernel / kernel_arg_violation = 0 / 0 / 0
live_compatible_with_current_wna16_args_count = 0

pytest tests -q
597 passed, 2 warnings
```

The lab-default readonly gate artifact now requires
`require_kernel_arg_semantic_handle_adapter=true`, and its evidence paths point
to the strict 128-sample semantic-adapter gate JSON.  Runtime shadow aggregation
also has explicit zero-default coverage so older non-semantic events cannot be
misread as ready semantic adapter records.

## Previous Update: Experimental Kernel-Arg Pass Live Path

The premap kernel-arg handoff path now has a minimal live-pass envelope at the
prelaunch consumer-adapter layer:

```text
prepared descriptor/address table
-> kernel-arg shadow table
-> kernel-arg mirror
-> prelaunch launch-schema mirror
-> live toggle
-> live no-op integration
-> live consumer adapter
-> experimental kernel_arg_pass live state
```

The live pass remains default-disabled.  It is accepted only when all of the
following are true:

```text
premap_kernel_arg_handoff_live_enabled = true
premap_kernel_arg_handoff_live_consumer_connected = true
premap_kernel_arg_handoff_kernel_arg_pass_enabled = true
gate.check.allow_kernel_arg_handoff_live_kernel_arg_pass = true
```

Under that explicit gate, the adapter can report:

```text
block_reason = kernel_arg_handoff_kernel_arg_pass_live
blocked = false
passed_to_kernel = true
changes_kernel_launch_args = true
payload_bytes = 0
```

The default lab gate and connected-blocked canary still require:

```text
premap_kernel_arg_handoff_kernel_arg_pass_enabled = false
payload_bytes / passed_to_kernel / changes_kernel_launch_args = 0 / 0 / 0
```

This is a code/schema/checker gate only at this point.  It does not claim a
validated endpoint performance win or payload prefetch.  Any real lab run that
uses the live pass must use the explicit checker allow flag:

```bash
--allow-kernel-arg-handoff-live-kernel-arg-pass
```

Validation:

```text
pytest tests/test_runtime_premap.py \
       tests/test_vllm_premap_capacity_gate.py \
       tests/test_check_premap_longrun_audit_gate.py -q
136 passed

pytest tests -q
574 passed, 2 warnings
```

## Previous Update: Kernel-Arg Connected-Adapter Canary

The premap descriptor/address prep path now has one more strict long-run
lab gate after the 128-sample live-noop gate:

```text
prepared descriptor/address table
-> kernel-arg shadow table
-> kernel-arg mirror
-> prelaunch launch-schema mirror
-> live toggle
-> live no-op integration
-> live consumer adapter envelope
```

The `readonly_kernel_arg_handoff_live_consumer_adapter` record is now required
by the lab-default readonly gate artifact.  A fresh GPU1 128-sample strict audit
passed with:

```text
premap summaries / consumer mappings = 10,195 / 10,195
adapter checked / ready / lab_gate_passed = 10,195 / 10,195 / 10,195
adapter present / blocked = 10,195 / 10,195
consumer_connected / live_eligible = 0 / 0
payload_bytes / passed_to_kernel / kernel_arg_violation = 0 / 0 / 0
```

This is a readiness / safety contract only.  It does not move payload, does not
grant ready credit, does not change router outputs, and does not mutate kernel
launch arguments.

On top of this lab-default disconnected adapter gate, there is now a canary-only
connected adapter state.  It requires both:

```text
premap_kernel_arg_handoff_live_enabled = true
premap_kernel_arg_handoff_live_consumer_connected = true
```

and must remain blocked with:

```text
block_reason = kernel_arg_handoff_kernel_arg_pass_disabled
payload_bytes / passed_to_kernel / changes_kernel_launch_args = 0 / 0 / 0
```

Evidence:

```text
data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
  performance_summary.json
  longrun_audit_gate_live_consumer_adapter.json

configs/runtime/
  premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml
```

Validation:

```text
pytest tests -q
535 passed, 2 warnings
```

Follow-up hardening:

```text
runtime gate loader now has explicit canary tests for:
  default-disabled live consumer adapter
  live-enabled but consumer-disconnected adapter
  rejection if a gate claims consumer_connected=true

live adapter changes_kernel_launch_args is now a first-class aggregate
metric, not only a checker alias:
  changes_kernel_launch_args_count
  kernel_arg_violation_count
both are checked to stay zero under the lab gate.
```

Live-enabled blocked canary:

```text
temporary GPU1 smoke:
  config/gate: tmp/live_adapter_canary_smoke/
  output: /tmp/mtp_live_adapter_canary_smoke/
  samples / max_tokens = 1 / 16
  checker flag: --allow-enabled-blocked-live-toggle

result:
  passed = true
  adapter checked = 640
  adapter enabled / live_eligible = 640 / 640
  consumer_connected / blocked = 0 / 640
  payload_bytes / passed_to_kernel / changes_kernel_launch_args = 0 / 0 / 0

Interpretation:
  This is a canary for the live-enabled but consumer-disconnected branch.
  It is not the lab-default gate and still does not connect a kernel consumer
  or mutate launch arguments.
  Only the runtime trace is 1-sample; the temporary gate metadata is copied from
  the 128-sample lab-gate template and is not a recalibrated canary artifact.
```

Refreshed default-disabled strict smoke:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke/
      performance_summary.json
      longrun_audit_gate_live_consumer_adapter.json

performance summary flag:
  runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled = false

checker result:
  passed = true
  failures = []
  live_noop_integration_checked = 640
  live_noop_integration_consumer_connected = 0
  live_noop_integration_blocked = 640
  live_noop_integration_changes_kernel_launch_args = 0
  live_consumer_adapter_checked = 640
  live_consumer_adapter_consumer_connected = 0
  live_consumer_adapter_blocked = 640
  live_consumer_adapter_changes_kernel_launch_args = 0
  live_consumer_adapter_kernel_arg_violation = 0
```

This 8-sample run is a quick current-code sanity gate.  The lab-default scale
gate remains the refreshed Dolly128 artifact; the Dolly512 artifact remains
legacy read-only handle/source-class scale evidence until rerun with the current
kernel-arg/live-adapter envelope.

A 32-sample strict-smoke config and gate artifact are now available as an
intermediate current-envelope check:

```text
configs/trace/
  router_mtp_trace_external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke.yaml

data/traces/
  external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke/
    performance_summary.json
    longrun_audit_gate_live_consumer_adapter.json
```

Here `current-envelope` means the current code path plus the current
runtime-shadow contract.  It inherits the 8-sample strict-smoke contract, keeps
`premap_kernel_arg_handoff_kernel_arg_pass_enabled = false`, and is intended to
bridge quick smoke and the 128-sample lab gate.  It is not a replacement for the
lab-default Dolly128 gate.

32-sample checker result:

```text
passed = true
failures = []
runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled = false
runtime_shadow_premap_kernel_arg_handoff_live_enabled = false
runtime_shadow_premap_kernel_arg_handoff_live_consumer_connected = false

decision_summary_count = 2560
premap_summary_count = 2560

live_noop_integration_checked = 2560
live_noop_integration_consumer_connected = 0
live_noop_integration_blocked = 2560
live_noop_integration_changes_kernel_launch_args = 0

live_consumer_adapter_checked = 2560
live_consumer_adapter_consumer_connected = 0
live_consumer_adapter_blocked = 2560
live_consumer_adapter_changes_kernel_launch_args = 0
live_consumer_adapter_kernel_arg_violation = 0
```

The strict checker now also rejects any performance summary or gate metric set
that explicitly reports:

```text
runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled = true
```

This prevents kernel-argument pass-through opt-in from being treated as a valid
readonly lab gate by accident.  The current checked 8/32 artifacts explicitly
keep the flag false; the refreshed 128 artifact does not carry the flag and is
accepted by the checker default as false.  All three pass the hardened checker.

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
- Descriptor-order minimal telemetry runs as a long-run online audit path with
  single-digit overhead on AWQ/vLLM.
- Layer-prior two-level group-plan execution passes the independent HIP
  consumer gate under measured tile/group configurations.
- Current AWQ coarse bottleneck evidence is locked with file/directory SHA256
  manifests, including superseded-artifact indexing for polluted or stale runs.
- AWQ/vLLM MoE source timing now reaches the package-level `fused_experts`
  entry used by WNA16.  The current GPU1 diagnostic shows that
  `quant_method.apply - fused_experts_outer` is small, while the large
  remaining MoE apply residual is inside `fused_experts` wrapper/launch/glue,
  not in the AWQ apply shell.
- Premap descriptor/address prep now emits and validates stage coverage of the
  no-op kernel-arg envelope through launch-schema mirror, live toggle,
  live-noop-integration, and live consumer adapter.  The adapter record is
  default-disabled, consumer-disconnected, zero-payload, and never passed to
  the kernel.  GPU1 Dolly 128-sample strict long-run validates 10195/10195
  checked+ready adapter records with no payload or kernel-arg violations, and
  this gate is promoted into the lab default precondition:
  `data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate_live_consumer_adapter.json`.

## Prefetch Cache-Manager Replay

The event queue cache-lab shim is now ready-time aware:

```text
prefetch hit := virtual H2D completion time <= token/layer demand deadline
```

This replaces the earlier event-queue residency-only assumption for
`queue_model=event`.  The old residency-only protected-score sweep remains a
diagnostic artifact, but it should not be used as the claim gate for deadline
or ready-before-demand behavior.

Current ready-time Dolly heldout128/prefix127 evidence:

```text
artifact:
  outputs/reports/prefetch_action_replay/
    event_queue_sweep_protected_score_ready_v1/
  outputs/reports/prefetch_action_replay/
    event_queue_ready_sensitivity_summary.md

config:
  cache_capacity = 10240
  measured copy = GPU1 p95, batch8, pinned H2D
  queue_model = event_driven_ready_time_batch_queue
  queue_policy = drop
  queue_admission_policy = protected_score
  queue_event_interval_us = 50
  max_inflight = 32 / 33 / 34 / 36 / 40 / 48 / 64
  deadline_us = 0 / 5000 / 15000 / 30000 / 60000

result:
  first_positive_any:
    max_inflight = 32
    deadline_us = 30000
    net_saved_ms_vs_transition = +1.828
    extra_issued_vs_transition = 0

  first_positive_mtp_extra_issued = {}
```

Sensitivity follow-up:

```text
sweeps:
  measured_copy:      copy_scale=1.0,  event_interval_us=50
  copy_scale_0_5:     copy_scale=0.5,  event_interval_us=50
  copy_scale_0_25:    copy_scale=0.25, event_interval_us=50
  lookahead500:       copy_scale=1.0,  event_interval_us=500

summary:
  positive_any_count = 3 / 4
  positive_mtp_extra_issued_count = 0 / 4

best extra-issued cells:
  measured_copy:   net=-353.505 ms, extra_issued=378
  copy_scale_0_5:  net=-179.803 ms, extra_issued=378
  copy_scale_0_25: net=-103.465 ms, extra_issued=378
  lookahead500:    net=-247.455 ms, extra_issued=378
```

Interpretation:

```text
When prefetches must actually complete before the demand deadline, the previous
residency-only first-positive point at max_inflight=33 no longer holds.

There is a small net-positive cell at max_inflight=32/deadline=30000us, but it
does not issue any extra payload beyond transition_top32.  It is therefore
tracked as same-issued admission/order behavior, not as MTP-extra full_fetch
evidence.

Current conclusion:
  protected-baseline + MTP extra-issued full_fetch does not pass the ready-time
  event queue gate under the measured-copy sweep, 2x/4x faster-copy what-ifs, or
  the larger event-interval/lookahead sweep.

Next gate:
  full_fetch extras should remain disabled/fallback by default under the
  ready-time manager gate.  The next prefetch branch should prioritize
  low-risk metadata/premap or a stricter admission model that proves a positive
  MTP-extra-issued cell before any full_fetch runtime claim.
```

Metadata/premap downgrade summary:

```text
artifact:
  outputs/reports/prefetch_action_replay/metadata_premap_gate_summary.md

inputs:
  AYA heldout512 combined claim gate
  Dolly heldout128 prefix127 combined claim gate

result:
  rows = 8
  metadata_positive_count = 0
  premap_positive_count = 4

normal envelope:
  AYA premap net setup:
    score_keep50   +37.219 ms
    utility_keep50 +48.808 ms
  Dolly premap net setup:
    score_keep50   +13.939 ms
    utility_keep50 +18.954 ms

stress envelope:
  metadata and premap are negative for both AYA and Dolly.
```

Interpretation:

```text
metadata/premap remain lower-risk than full_fetch because they do not move full
expert payloads, but they are not default-enable actions.

metadata does not pass the current setup proxy in any AYA/Dolly row.
premap has a positive normal-envelope proxy but fails stress.  The next
low-risk action branch should therefore be premap-only, normal-envelope gated,
and stress-fallback aware.
```

Premap-only GPU sweep:

```text
artifact:
  outputs/reports/prefetch_action_replay/
    premap_only_gate_dolly128_prefix127_gpu1_summary.md
  outputs/reports/prefetch_action_replay/
    premap_only_gate_aya256_gpu1_summary.md

Dolly heldout128 prefix127:
  device = cuda:1
  premap_budget_max_extra = 1
  metadata_budget_max_extra = 0
  full_fetch_ready_threshold = 999.0

result:
  premap first positive overlap = 0.5
  premap best overlap = 0.95
  premap best net setup proxy ~= +70.0 ms
  metadata remains disabled / zero

AYA heldout256:
  device = cuda:1
  premap_budget_max_extra = 1
  metadata_budget_max_extra = 0
  full_fetch_ready_threshold = 999.0

result:
  premap first positive overlap = 0.5
  premap best overlap = 0.95
  premap best net setup proxy ~= +94.9 ms
  metadata remains disabled / zero
```

Blocked follow-up:

```text
artifact:
  outputs/reports/prefetch_action_replay/premap_only_gate_gpu_blockers.md

AYA heldout512 premap-only GPU sweep failed on both cuda:0 and cuda:1 with a
ROCm/HSA hardware exception during GPU tensor execution.  This is treated as an
environment/scale blocker, not as a negative AYA premap result.
```

Premap read-only consumer mapping:

```text
runtime gate:
  configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml

smoke artifact:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/

mode:
  premap_policy = premap_only_with_consumer_mapping_noop
  premap_consumer_mapping_mode = noop_assertion
  premap_consumer_resolve_real_handles = true
  premap_consumer_require_readonly_gate = true

result:
  premap_consumer_mapping events = 20480
  readonly gate passed rows      = 20480 / 20480
  missing source-class rows      = 0
  performance_summary fields     = present under runtime_shadow_aggregate_*

real prelaunch handle source classification:
  packed_weight hits    = 190215
  scale_metadata hits   = 190215
  aux_metadata hits     = 190215
  packed_weight misses  = 0
  scale_metadata misses = 0
  aux_metadata misses   = 0
  miss_reason_counts    = {}

no-op contract:
  payload bytes          = 0
  router changes         = 0
  descriptor-order edits = 0
  ready credit           = 0
```

Interpretation:

```text
The premap-only branch now reaches a read-only vLLM/AWQ consumer contract:
  (layer_id, expert_id)
    -> address_key
    -> premap descriptor/address handle
    -> actual packed-weight / scale / aux-metadata runtime handle hash

This is still no-op assertion only.  It does not move payload, does not issue
ready credit, does not change routing, and does not change descriptor order.
The source-class and miss-reason counters make failures auditable before any
future runtime consumer uses these handles.
```

128-sample long-run audit:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/

gate:
  scripts/check_premap_longrun_audit_gate.py
  max_capacity = 12288
  min_reuse_rate = 0.98

result:
  passed = true
  row_count = 20390
  premap_summary = 10195
  premap_consumer_mapping = 10195
  resident_count_max = 10127
  reuse_rate_mean = 0.982739
  evicted_count = 0

real prelaunch handle source classification:
  real_handle hits = 110898
  real_handle misses = 0
  packed_weight hits = 110898
  scale_metadata hits = 110898
  aux_metadata hits = 110898
  packed_weight / scale_metadata / aux_metadata misses = 0 / 0 / 0
  resolver_disabled / consumer_layer_missing / expert_map_miss / no_handle_parts = 0 / 0 / 0 / 0
```

Interpretation:

```text
The premap read-only consumer contract scales from the 8-sample smoke to the
128-sample long-run audit under sampled consumer mapping.  The runtime can
resolve every sampled prelaunch packed-weight, scale-metadata, and aux-metadata
handle class without payload transfer or router/order side effects.
```

512-sample long-run audit:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit/

gate:
  scripts/check_premap_longrun_audit_gate.py
  max_capacity = 12288
  min_reuse_rate = 0.98

result:
  passed = true
  row_count = 40684
  premap_summary = 20342
  premap_consumer_mapping = 20342
  resident_count_max = 10202
  reuse_rate_mean = 0.994510
  evicted_count = 0

real prelaunch handle source classification:
  real_handle hits = 210849
  real_handle misses = 0
  packed_weight hits = 210849
  scale_metadata hits = 210849
  aux_metadata hits = 210849
  packed_weight / scale_metadata / aux_metadata misses = 0 / 0 / 0
  resolver_disabled / consumer_layer_missing / expert_map_miss / no_handle_parts = 0 / 0 / 0 / 0
```

Interpretation:

```text
The same read-only prelaunch handle/source-class contract passes at the
512-sample scale.  The Dolly128-derived 12288-address capacity gate remains
sufficient on the 512 split, with no eviction pressure and complete prelaunch
source-class handle resolution for every sampled consumer mapping.

This 512 artifact predates the kernel-arg shadow table / live-noop /
live-consumer-adapter envelope.  It is valid scale evidence for premap address
reuse and readonly real-handle parity, but it is not a strict live-adapter lab
gate artifact.  The strict kernel-arg-shadow/live-adapter lab precondition is
currently the refreshed Dolly128 gate:

  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
      longrun_audit_gate_live_consumer_adapter.json

The Dolly128 and Dolly512 artifacts are therefore different audit stages:
premap address/handle counters are comparable, but kernel-arg/live-adapter gate
fields are not directly comparable across those two artifacts.
```

Consumer shim prepared-table dry-run:

```text
implemented:
  consumer shim now explicitly consumes the prepared kernel-arg shadow table
  object in read-only mode

contract:
  handle table is read by the shim
  row count / column count / schema hash / row-order hash are audited
  per-row handle parity is checked
  lifecycle / miss / stale counters are recorded
  payload bytes remain 0
  ready credit remains false
  router / descriptor-order / kernel-launch args remain unchanged
  passed_to_kernel remains false

smoke evidence:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/
      consumer_shim_table_consume_summary.json

result:
  consume_checked_count = 20480
  consume_ok_rate = 1.0
  consume_lifecycle_ok_rate = 1.0
  consume_row_count = 190215
  consume_per_row_parity_ok_count = 190215
  consume_row_miss_count = 0
  consume_stale_row_count = 0
  consume_payload_bytes = 0
  consume_passed_to_kernel_count = 0
```

Kernel-arg handoff shadow / mirror / attempt gate:

```text
implemented:
  consumer shim builds a future kernel-argument shadow table
  shim consumes the prepared table object in read-only mode
  shim builds a kernel-arg handoff mirror
  shim builds a readonly kernel-arg handoff attempt record

contract:
  mode = readonly_kernel_arg_handoff_attempt
  block_reason = kernel_arg_handoff_disabled_noop_gate
  gate_allowed = false
  blocked = true
  mirror_ready = true
  record_ready = true
  payload bytes remain 0
  passed_to_kernel remains false
  kernel launch args remain unchanged
  ready credit remains false
  router / descriptor-order remain unchanged

strict smoke evidence:
  artifact:
    data/traces/
      external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke/

  checker:
    scripts/check_premap_longrun_audit_gate.py
      --require-readonly-consumer
      --require-descriptor-prep
      --require-real-descriptor-prep
      --require-kernel-arg-shadow-table
      --require-consumer-shim-table-read
      --require-consumer-shim-table-consume
      --require-consumer-shim-table-object
      --require-consumer-shim-prep-execution
      --require-kernel-arg-handoff-attempt

  result:
    passed = true
    premap_summary = 640
    consumer_shim_executed = 640
    handle_table_consume_ok_rate = 1.0
    handle_table_object_consumed_rate = 1.0
    prep_execution_dry_run_ok_rate = 1.0
    kernel_arg_handoff_shadow_slot_ready_count = 640
    kernel_arg_handoff_mirror_ready_count = 640
    kernel_arg_handoff_attempt_record_ready_count = 640
    kernel_arg_handoff_attempt_blocked_count = 640
    kernel_arg_handoff_attempt_gate_allowed_count = 0
    kernel_arg_handoff_attempt_payload_bytes = 0
    kernel_arg_handoff_attempt_passed_to_kernel_count = 0
    kernel_arg_handoff_attempt_kernel_arg_violation_count = 0
    row_count = 1280
    prepared handle rows = 6965

128-sample long-run evidence:
  artifact:
    data/traces/
      external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/

  gate output:
    longrun_audit_gate_handoff_attempt.json

  checker:
    max_capacity = 12288
    min_reuse_rate = 0.98
    --require-readonly-consumer
    --require-descriptor-prep
    --require-real-descriptor-prep
    --require-kernel-arg-shadow-table
    --require-consumer-shim-table-read
    --require-consumer-shim-table-consume
    --require-consumer-shim-table-object
    --require-consumer-shim-prep-execution

  result:
    passed = true
    premap_summary = 10195
    consumer_shim_executed = 10195
    resident_count_max = 10127
    reuse_rate_mean = 0.982739
    eviction_pressure_mean = 0.0
    real_handle_miss_count = 0
    handle_table_consume_ok_rate = 1.0
    handle_table_consume_row_count = 110898
    handle_table_consume_per_row_parity_ok_count = 110898
    handle_table_consume_row_miss_count = 0
    handle_table_consume_stale_row_count = 0
    handle_table_object_consumed_rate = 1.0
    prep_execution_dry_run_ok_rate = 1.0
    kernel_arg_handoff_shadow_slot_ready_count = 10195
    kernel_arg_handoff_mirror_ready_count = 10195
    kernel_arg_handoff_attempt_record_ready_count = 10195
    kernel_arg_handoff_attempt_blocked_count = 10195
    kernel_arg_handoff_attempt_gate_allowed_count = 0
    kernel_arg_handoff_attempt_payload_bytes = 0
    kernel_arg_handoff_attempt_passed_to_kernel_count = 0
    kernel_arg_handoff_attempt_kernel_arg_violation_count = 0
```

Interpretation:

```text
Premap is now represented as a real descriptor/address preparation object that
can be read by the prelaunch consumer shim and packaged into the same shape a
future fused-MoE/AWQ kernel-argument handoff would consume.

The current gate deliberately stops at an audited handoff attempt record.  It
does not pass the package to the kernel, does not move payload, and does not
grant ready-before-demand credit.  This is a kernel-arg handoff no-op safety
gate, not a performance or endpoint-runtime claim.
```

## Evidence Lock

Current coarse bottleneck baseline:

```text
outputs/reports/awq_telemetry_ladder/current_coarse_bottleneck_baseline_2026-05-17.md
```

Evidence manifest:

```text
outputs/reports/awq_telemetry_ladder/current_coarse_bottleneck_evidence_manifest_2026-05-17.md
outputs/reports/awq_telemetry_ladder/current_coarse_bottleneck_evidence_manifest_2026-05-17.json
```

The manifest records SHA256 hashes for report files and recursive tree digests
for active artifact directories.  This baseline's generated entry set does not
include the manifest itself, and the generator excludes output manifest paths
from directory hashing to avoid self-referential digest drift.  Evidence
boundaries remain:

```text
coarse bottleneck attribution only
diagnostic modes are not production-equivalent runtime candidates
local curated smoke_text prompts are prompt-source sanity evidence only
Dolly external prompt-source repeat-3 is a completed/hash-locked attribution
evidence point, not a standalone strong distribution-level or speedup claim
```

Latest external prompt-source gate:

```text
source:
  Databricks Dolly 15k, 128 materialized prompts

GPU1 repeat-3:
  artifact:
    outputs/reports/awq_telemetry_ladder/
      gpu1_external_prompt_gate_dolly_128_gen64_repeat3_core/
  production_like median TPOT:       0.063120 s/token
  attention_total_only median TPOT:  0.069878 s/token
  median delta:                     +10.71%
  p95 / p99 delta:                  +20.21% / +18.13%
  final gate:                       false, median_not_improved

GPU0 single-run sanity:
  artifact:
    outputs/reports/awq_telemetry_ladder/
      gpu0_external_prompt_gate_dolly_128_gen64_core/
  production_like TPOT:              0.067339 s/token
  attention_total_only TPOT:         0.070923 s/token
  delta:                            +5.32%

interpretation:
  The external prompt source reproduces the boundary that
  attention_total_only is attribution-only and not a runtime candidate.
```

Utilization sidecar status:

```text
scripts:
  scripts/sample_rocm_smi.py
  scripts/summarize_rocm_smi_jsonl.py
  scripts/run_with_rocm_smi.py

GPU1 Dolly production_like ladder:
  max_samples=8:   TPOT 0.067407 s/token
  max_samples=32:  TPOT 0.065378 s/token
  max_samples=64:  TPOT 0.064841 s/token

process-bound rocm-smi 8-sample:
  artifact:
    outputs/reports/awq_telemetry_ladder/
      gpu1_dolly_utilization_ladder_production_like_8_rocm_bound/
  GPU use mean / p50 / p95:  51.0% / 58.0% / 77.0%
  VRAM p50 / p95:            49.0% / 98.0%

approximate 32-sample overlap rocm-smi:
  GPU use mean / p50 / p95:  51.5% / 60.0% / 76.0%
  VRAM p50:                  98.0%

interpretation:
  Low observed compute utilization is not a simple idle-GPU failure mode.
  The GPU is active but not compute-saturated, consistent with mixed decode
  bottlenecks: small-kernel launch/engine gaps, memory/KV behavior, and MoE
  fragmentation.  A decode-only marker is still needed for precise generate-only
  utilization.
```

## AWQ/vLLM Performance Attribution

Production-like performance reports must keep runtime-shadow top-k row writing
disabled (`runtime_shadow.record_router_topk=false`).  This is distinct from
capturing internal top-k tensors for local assertions.  Earlier
`select_experts` hotspots were dominated by trace row recording overhead, not
by the production routing path.

Current GPU1 8-sample diagnostic direction, within this source-split taxonomy:

```text
select_experts:
  no longer a primary production bottleneck once record_topk is disabled

shared expert:
  Qwen2MoeMLP source split is active
  shared_direct residual is reduced to a bounded wrapper/glue remainder

quant_method.apply:
  package-level fused_experts outer wrapper is active
  quant_method.apply - fused_experts_outer is small
  fused_experts_outer - inner source parts is the largest remaining
  measured MoE apply residual in this diagnostic
```

Latest artifact:

```text
outputs/reports/awq_telemetry_ladder/
  gpu1_source_split_fused_outer_fixed_smoke8/
```

Key decode sums from that run:

```text
quant_method.apply                         1599.84 ms
apply_source_fused_experts_outer           1573.44 ms
quant_method.apply - fused_experts_outer     26.40 ms
fused_experts_outer - inner source parts    785.18 ms
shared_direct_layer                         573.36 ms
shared_direct source parts                  415.37 ms
shared_direct residual                      157.99 ms
```

Next performance gate:

```text
split fused_experts internal wrapper/launch/glue:
  workspace/config/prep
  prepare_expert_assignment
  dispatch_fused_moe_kernel host enqueue
  WNA16 launch setup / event gap
  activation / combine
  post-dispatch residual

pass condition:
  explain the current ~785 ms fused_experts_outer-minus-source-parts residual
  into named substages without re-enabling record_topk row logging
```

Follow-up split:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_source_split_impl_total_smoke8/

new events:
  apply_source_impl_total
  apply_source_quantize_hidden
  apply_source_prepare_assignment
  apply_source_quantize_intermediate

GPU1, AWQ, 8 samples, 64 output tokens, diagnostic_light:
  quant_method.apply                              1240.41 ms
  apply_source_fused_experts_outer                1209.54 ms
  apply_source_impl_total                         1100.21 ms
  quant_method.apply - fused_experts_outer          30.87 ms
  fused_experts_outer - impl_total                 109.34 ms
  impl_total - inner source parts                  156.97 ms
  fused_experts_outer - inner source parts         266.31 ms

  source W1 enqueue - WNA16 launch parts            41.17 ms
  source W2 enqueue - WNA16 launch parts            35.55 ms
```

Interpretation:

```text
The earlier ~785 ms residual was partly a taxonomy gap.  Explicit impl-total,
quantize, and prepare-assignment regions reduce the remaining fused_experts
outer-minus-source residual to ~266 ms in this run.

The remaining measured gaps split into:
  package-level fused_experts wrapper/outer overhead
  fused_experts_impl body regions still not attributed to named source parts
  W1/W2 dispatch enqueue overhead beyond the WNA16 invoke/enqueue hooks

This is still diagnostic timing only; event volume and copied source wrappers
make it unsuitable for production TPOT claims.
```

Outer-wrapper split:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_source_split_outer_impl_detail_smoke8/

new events:
  apply_source_outer_quant_config
  apply_source_outer_inplace_assert
  apply_source_outer_dispatch_select
  apply_source_outer_impl_call

GPU1, AWQ, 8 samples, 64 output tokens, diagnostic_light:
  quant_method.apply                              1348.11 ms
  apply_source_fused_experts_outer                1317.65 ms
  apply_source_outer parts sum                    1263.62 ms
  apply_source_impl_total                         1149.32 ms

  quant_method.apply - fused_experts_outer          30.46 ms
  fused_experts_outer - outer parts                 54.02 ms
  outer impl-call - impl_total                     112.15 ms
  impl_total - inner source parts                  165.19 ms
  fused_experts_outer - inner source parts         333.52 ms

  source W1 enqueue - WNA16 launch parts            42.25 ms
  source W2 enqueue - WNA16 launch parts            36.90 ms
```

Interpretation:

```text
The outer wrapper itself is now mostly named: quant-config defaulting,
inplace assert, dispatch-function selection, and impl-call timing explain most
of the package-level fused_experts wrapper.

The remaining named residual now sits in two places:
  outer impl-call minus impl_total
  impl_total minus inner source parts

The W1/W2 enqueue-vs-launch gap remains visible but smaller than those two
residual buckets.  This run adds more diagnostic events than the previous split,
so absolute generate/TPOT numbers are not comparable to production-like runs.
```

Telemetry-overhead calibration:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_source_timing_emit_split_smoke8/

result:
  source_full emit split:
    apply_source_emit_overhead                 148.85 ms
    outer_impl_call - impl_total               124.87 ms

  earlier full-source residuals:
    impl_total - inner source parts            ~151.95 ms
    outer_impl_call - impl_total               ~124.87 ms

  dispatch gap comparison:
    source_none W1/W2 gap                      23.55 ms / 17.58 ms
    source_full_emit_split W1/W2 gap           20.43 ms / 17.38 ms

interpretation:
  the large impl-inner residual is the same scale as measured source-event
  emission overhead, and the outer impl-call gap is smaller than the measured
  emit overhead.  These residuals are therefore treated as diagnostic
  boundary/emission artifacts, not production optimization targets.

  The W1/W2 launch/glue gaps remain real but small after calibration.

policy:
  source_full / copied dispatch source splits are structural-debug only.
  Production performance tables must use record_topk=false and avoid
  emit-heavy source timing.
```

Attention and engine low-intrusion ladder:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_low_intrusion_next_8sample_decode/

GPU1, AWQ, 8 samples, 64 output tokens:
  production_like TPOT              0.07217 s
  attention_total_only TPOT         0.07830 s  (+8.49%)
  shared_expert_light TPOT          0.08391 s  (+16.26%)
  engine_light TPOT                 0.07086 s  (-1.82%, variance / not a speed claim)

engine_light breakdown:
  engine llm.generate call                 36.28 s
  engine execute_model                     36.02 s
  engine model_forward                     35.41 s
  execute_model - model_forward             0.61 s
  llm.generate - execute_model              0.26 s
  sample_tokens                             0.13 s
  logits_processor_forward                  0.05 s
  sampler_forward                           0.04 s

interpretation:
  engine/logits/sampler residual is not the dominant bottleneck in this
  setting.  The runtime is still model-forward dominated.

attention_total_only:
  remains useful for coarse diagnostic attribution, but overhead varies and
  it is not a production TPOT claim.

shared_expert_light:
  diagnostic-only because it adds large overhead, but it points to shared
  expert direct layer / output gate as real named targets.
```

Shared expert production-like A/B:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_gate_prod_ab_8sample_decode/

GPU1, AWQ, 8 samples, 64 output tokens, telemetry-minimal:
  production_like TPOT                   0.07117 s
  production_like_force_shared_aux       0.07232 s  (+1.61%)
  shared_gate_fused_minimal              0.07380 s  (+3.70%)

interpretation:
  forcing the shared expert auxiliary stream does not show a gain in this
  8-sample smoke.
  the current fused shared output-gate postprocess path also does not show a
  gain in this 8-sample smoke.
  Therefore the shared-expert opportunity is not solved by these two switches;
  the next valid target is the shared direct layer/body or a lower-level
  shared-expert execution change, not more output-gate postprocess tuning.
```

Shared output-gate minimal postprocess A/B:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_gate_minimal_ab_8sample_decode/

GPU1, AWQ, 8 samples, 64 output tokens, telemetry-minimal:
  production_like TPOT                   0.07424 s
  shared_gate_inplace_minimal            0.07126 s  (-4.01%)
  shared_gate_fused_minimal              0.07582 s  (+2.13%)

interpretation:
  inplace sigmoid/mul postprocess shows a positive 8-sample smoke signal,
  while the current Triton fused gate remains negative in this code state.

  This is not yet a stable endpoint claim.  The next gate is 32/128-sample
  telemetry-minimal validation for shared_gate_inplace_minimal.  Do not enable
  it by default before the larger split confirms TPOT and output parity.
```

32-sample follow-up:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_gate_inplace_minimal_32sample_decode/

GPU1, AWQ, 32 samples, 64 output tokens, telemetry-minimal:
  production_like TPOT                   0.07374 s
  shared_gate_inplace_minimal            0.07425 s  (+0.68%)

interpretation:
  the 8-sample inplace positive signal does not hold at 32 samples.
  Shared output-gate postprocess changes should remain diagnostic-only for now;
  they are not a stable endpoint optimization.
```

Implementation correction:

```text
The first shared_gate_inplace_minimal mode was discovered to be a no-op for the
inplace postprocess: with source timing disabled and fused disabled,
SharedExperts.apply returned to the original path before the custom postprocess
could run.  The old 8/32-sample inplace results above are therefore retained
only as invalidated/no-op evidence and not as an optimization result.

Fix:
  custom shared gate postprocess is now decoupled from source timing.
  shared_gate_inplace_minimal and shared_gate_fused_minimal run the custom
  Qwen2MoeMLP postprocess path without emitting source timing rows.
  MULTI_STREAM_OVERLAPPED orders no longer silently bypass custom gate modes;
  custom gate modes fall back to a direct custom Qwen2MoeMLP path when the
  shared expert module is the supported Qwen2MoeMLP shape, and otherwise fall
  back to the original vLLM path.
  Qwen2MoeMLP custom helpers now accept projection/gate outputs returned either
  as tensors or as tuple-like vLLM projection outputs.
  fused_triton raises a typed unsupported-path exception for narrow-kernel
  semantic precondition failures and falls back to the default semantic path
  instead of hard failing.
```

Fixed shared output-gate minimal A/B:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_gate_minimal_ab_fixed_8sample_decode/

GPU1, AWQ, 8 samples, 64 output tokens, telemetry-minimal:
  production_like TPOT                   0.07091 s
  shared_gate_inplace_minimal            0.07191 s  (+1.40%)
  shared_gate_fused_minimal              0.07490 s  (+5.63%)

interpretation:
  once the custom gate postprocess actually executes, both inplace and fused
  variants are negative in the 8-sample smoke.  Shared output-gate postprocess
  should remain diagnostic/negative evidence, not a runtime optimization branch.
```

Attention / GDN production-like A/B:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_attention_gdn_prod_ab_8sample_decode/

GPU1, AWQ, 8 samples, 64 output tokens, telemetry-minimal:
  production_like TPOT                         0.07319 s
  production_like_no_packed_recurrent         0.07715 s  (+5.41%)

interpretation:
  disabling the packed recurrent decode path is slower in this smoke.
  Keep the packed recurrent path enabled; it is not the current negative
  optimization point.
```

Shared body coarse attribution:

```text
artifacts:
  outputs/reports/awq_telemetry_ladder/
    gpu1_decoder_shared_body_light_8sample_decode/
    gpu1_decoder_shared_body_light_32sample_decode/
    gpu1_decoder_shared_body_light_128sample_decode/

mode:
  decoder_shared_body_light
  record_topk = false
  decoder component timing enabled
  moe_source_timing_mode = shared_body
  moe_substage_logging_mode = aggregate

overhead vs production_like:
  8 samples:    TPOT 0.07477 -> 0.07693 s  (+2.89%)
  32 samples:   TPOT 0.07434 -> 0.07837 s  (+5.42%)
  latest 128x64 rerun:
    TPOT 0.07349 -> 0.07709 s  (+4.90%)

latest 128x64 coarse decode sums:
  requested output tokens                 8192
  generate total                         631.530 s
  decoder layer total                    589.043 s
  attention                              183.101 s
  MLP/MoE                                316.122 s
  MoE apply                              178.204 s
  MLP/MoE - MoE apply                    137.918 s
  outside attention+MLP residual          89.821 s
  shared expert direct layer              62.265 s

integrity:
  descriptor/shared-body events scale to 128 samples without missing
  aggregate rows.  The only emitted MoE substage in shared_body mode is
  experts_shared_direct_layer.
  The latest rerun supersedes the earlier stale decode_breakdown values in this
  artifact directory.
```

Interpretation:

```text
decoder_shared_body_light is the current preferred coarse shared-expert
diagnostic path.  It avoids the high-overhead per-substage Python hooks and
keeps the shared direct body as a single named bucket.

The 128-sample run confirms that shared direct body remains a real, named
MLP/MoE component, but the mode still adds non-trivial overhead and must not be
used as a production TPOT claim.

Next valid directions:
  keep coarse decoder/MLP/MoE/shared-body attribution for longer diagnostics
  or add a much lower-level, few-region shared direct body split.
  Do not return to Python per-substage shared hooks.
```

Shared body few-region attribution:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_decoder_shared_body_regions_light_8sample_decode/

mode:
  decoder_shared_body_regions_light
  moe_source_timing_mode = shared_body_regions
  emitted MoE body buckets:
    experts_shared_direct_layer
    experts_shared_body_core
    experts_shared_body_gate_proj
    experts_shared_body_gate_apply
    experts_shared_body_gate_fused when fused gate is active

GPU1, AWQ, 8 samples, 64 output tokens:
  production_like TPOT                       0.08352 s
  decoder_shared_body_regions_light TPOT     0.09052 s  (+8.38%)

decode sums:
  shared direct layer                         639.168 ms
  shared body core                            265.547 ms
  shared body gate projection                 160.885 ms
  shared body gate apply                       50.702 ms
  shared body region parts sum                477.134 ms
  shared direct minus body regions            162.033 ms
```

Interpretation:

```text
The few-region split avoids child-module Python hooks and gives a named
breakdown of the shared direct body.  It is still diagnostic-only because it
adds measurable overhead, but it is much more actionable than per-substage
shared source timing.

The largest named shared direct component in this smoke is the core
gate-up/activation/down body, followed by the output gate projection.
The remaining direct-minus-body-region residual is now bounded at ~162 ms in
this 8-sample run.
```

Shared body telemetry ladder:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_body_telemetry_ladder_8sample_decode/

GPU1, AWQ, 8 samples, 64 output tokens:
  production_like TPOT                    0.08100 s
  shared_body_total_only TPOT             0.08184 s  (+1.03%)
  decoder_shared_body_regions_light TPOT  0.08886 s  (+9.70%)
  shared_body_regions_no_write TPOT       0.08610 s  (+6.30%)
```

Shared body total-only scale validation:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_body_total_only_32sample_decode/

GPU1, AWQ, 32 samples, 256 requested output tokens total:
  production_like TPOT         0.08035 s
  shared_body_total_only TPOT  0.08180 s  (+1.80%)
  shared direct layer sum      1787.909 ms
  shared direct p50 / p95      1393.916 / 1474.442 us

artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_body_total_only_128sample_decode/

GPU1, AWQ, 128 samples, 1024 requested output tokens total:
  production_like TPOT         0.07703 s
  shared_body_total_only TPOT  0.07906 s  (+2.63%)
  shared direct layer sum      6900.918 ms
  shared direct p50 / p95      1350.263 / 1445.613 us
```

Interpretation:

```text
shared_body_total_only is a low-intrusion way to track the coarse shared direct
layer cost.  The 32/128-sample scale runs stay in the low-single-digit overhead
range and do not show scale drift, so shared_body_total_only is acceptable for
low-intrusion diagnostic coarse attribution.  It is not a production TPOT claim.

The few-region split remains diagnostic-only.  Disabling aggregate writes
reduces overhead by only ~3.4 percentage points, so most of the overhead comes
from entering the region timing path itself rather than JSONL flushing.

Use shared_body_regions only for small attribution runs.  Do not use it as a
production TPOT share, and do not keep adding Python region hooks unless a
specific named bucket is required.
```

Shared body coarse 128x64 decode attribution:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_decoder_shared_body_light_128sample_decode/

GPU1, AWQ, 128 samples, 64 output tokens/sample:
  production_like TPOT              0.07349 s
  decoder_shared_body_light TPOT    0.07709 s  (+4.90%)
  requested output tokens           8192

decode decoder layer total          589.043 s  (93.27% generate)
decode MLP/MoE block                316.122 s  (50.06%)
decode attention                    183.101 s  (28.99%)
decode MoE layer apply              178.204 s  (28.22%)
decode MLP/MoE - MoE apply          137.918 s  (21.84%)
decode outside attention+MLP        89.821 s   (14.22%)
shared expert direct layer          62.265 s   (9.86%)
generate minus decoder layer        42.487 s   (6.73%)
```

Shared direct total-only cross-check:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_body_total_only_128sample_gen64_decode/

same GPU1/AWQ 128x64 split:
  shared_body_total_only TPOT             0.07563 s
  overhead vs external production_like    +2.91%
  shared expert direct layer              61.959 s
  shared direct p50 / p95                 12179.084 / 13771.811 us
```

Interpretation:

```text
decoder_shared_body_light gives a useful full-length coarse attribution table
without returning to region-level hooks.  Its 128x64 overhead is ~4.9%, so this
is still a diagnostic attribution run, not a production TPOT claim.

The lower-overhead shared_body_total_only cross-check gives nearly the same
shared direct total as decoder_shared_body_light (61.96 s vs 62.26 s), so the
shared direct layer remains a stable named coarse bucket under the long decode
split.  Its overhead uses the production_like baseline from the companion
`gpu1_decoder_shared_body_light_128sample_decode` artifact; the total-only
artifact itself was run as a single-mode cross-check.

The largest actionable coarse blocks remain MLP/MoE total, attention, and MoE
apply.  shared_body_total_only remains the lower-overhead way to track only the
shared direct layer; decoder_shared_body_light is for full coarse breakdown.
```

Shared stream production-like A/B:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_stream_ab_32sample_gen64_decode/

GPU1, AWQ, 32 samples, 64 output tokens/sample, telemetry-minimal:
  production_like TPOT                    0.071917 s
  force_shared_aux TPOT                   0.075152 s  (+4.50%)
  disable_shared_stream TPOT              0.072240 s  (+0.45%)
```

Interpretation:

```text
Forcing the shared expert aux-stream path is slower in this smoke.  Disabling
the shared stream is approximately neutral to slightly slower, so shared-stream
overlap is not currently a clear P0 optimization lever in this single-pass
32-sample run.  Keep the default shared stream policy for now; a global shared
stream policy decision would require a multi-repeat / split sweep.
```

Attention total-only 128x64 validation:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_attention_total_only_128sample_gen64_decode/

GPU1, AWQ, 128 samples, 64 output tokens/sample:
  production_like TPOT             0.071420 s
  attention_total_only TPOT        0.075752 s  (+6.07%)
  requested output tokens          8192

decode decoder layer total         577.764 s  (93.10% generate)
decode attention                   182.239 s  (29.37%)
decode MLP/MoE block               304.434 s  (49.06%)
decode MoE layer apply             176.253 s  (28.40%)
decode MLP/MoE - MoE apply         128.181 s  (20.66%)
decode outside attention+MLP       91.091 s   (14.68%)
generate minus decoder layer       42.800 s   (6.90%)
```

Interpretation:

```text
Under the current `num_tokens` phase heuristic, attention_total_only shows that
attention is a large secondary coarse block on the long decode split, around
29% of generate in this diagnostic run.

The mode still adds ~6% TPOT overhead at 128x64, so it should be used for
coarse attribution only.  Do not use it as production TPOT evidence, and do not
return to per-handoff attention hooks unless a small debug run needs them.
```

Engine-light 128x64 residual split:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_engine_light_128sample_gen64_decode/

GPU1, AWQ, 128 samples, 64 output tokens/sample:
  production_like TPOT             0.070425 s
  engine_light TPOT                0.072832 s  (+3.42%)
  requested output tokens          8192

engine llm.generate call           596.636 s
engine execute_model               592.291 s
engine model_forward               582.386 s
execute_model - model_forward        9.905 s  (1.66% generate)
llm.generate - execute_model         4.345 s  (0.73%)
prepare_inputs                       4.482 s  (0.75%)
attention_metadata                   1.833 s  (0.31%)
sample_tokens                        2.297 s  (0.39%)
logits_processor_forward             0.451 s  (0.08%)
sampler_forward                      0.693 s  (0.12%)
sampler_sample                       0.234 s  (0.04%)
```

Interpretation:

```text
engine_light is diagnostic-only, but it shows that engine/scheduler/sampling
residual is not the current dominant bottleneck under this 128x64 split.
The large blocks remain model-forward decoder work rather than sampler or
outer engine bookkeeping.
```

Diagnostic coarse-breakdown smoke:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_diagnostic_coarse_breakdown_8sample_gen64_decode/

mode:
  diagnostic_coarse_breakdown
  record_router_topk = false
  decoder layer/component timing = on
  decoder_component_logging_mode = rows
  MoE substage timing = on
  engine timing = on
  decoder_source_timing_mode = off
  moe_source_timing_mode = shared_body
  moe_substage_logging_mode = aggregate
  WNA16 event timing = off
  outcomes / descriptor summaries / transition summaries = off

GPU1, AWQ, 8 samples, 64 output tokens/sample:
  production_like TPOT              0.073619 s
  diagnostic_coarse_breakdown TPOT  0.080887 s  (+9.87%)
  requested output tokens           512

diagnostic coarse sums:
  generate total                    41.414 s
  decoder layer total               38.976 s  (94.11% generate)
  attention                         12.106 s  (29.23%)
  MLP/MoE                           20.901 s  (50.47%)
  MoE apply                         11.769 s  (28.42%)
  MLP/MoE - MoE apply                9.133 s  (22.05%)
  outside attention+MLP              5.968 s  (14.41%)
  shared expert direct layer         4.130 s  (9.97%)
  execute_model - model_forward      0.737 s  (1.78%)
  generate - execute_model           0.343 s  (0.83%)
  sample_tokens                      0.171 s
```

32-sample scale check:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_diagnostic_coarse_breakdown_32sample_gen64_decode/

GPU1, AWQ, 32 samples, 64 output tokens/sample:
  production_like TPOT              0.073838 s
  diagnostic_coarse_breakdown TPOT  0.079042 s  (+7.05%)
  requested output tokens           2048

diagnostic coarse sums:
  generate total                    161.878 s
  decoder layer total               152.156 s  (93.99% generate)
  attention                          46.674 s  (28.83%)
  MLP/MoE                            80.926 s  (49.99%)
  MoE apply                          45.894 s  (28.35%)
  MLP/MoE - MoE apply                35.033 s  (21.64%)
  outside attention+MLP              24.555 s  (15.17%)
  shared expert direct layer         15.783 s  (9.75%)
  execute_model - model_forward       3.413 s  (2.11%)
  generate - execute_model            1.194 s  (0.74%)
  sample_tokens                       0.619 s

runtime shadow volume:
  total rows                         361,056
  decoder_component_timing rows      163,840
  moe_substage_aggregate rows          2,560

derived summary artifact:
  real_bottleneck_summary.json
  real_bottleneck_summary.md
```

Interpretation:

```text
diagnostic_coarse_breakdown is a convenience diagnostic mode that puts the
current coarse hierarchy into one artifact.  It is useful for quick topology
checks, but it still writes decoder component rows and adds measurable overhead:
about +9.9% TPOT at 8 samples and +7.1% at 32 samples.

The summary artifact is generated by scripts/summarize_awq_real_bottlenecks.py
and is intended as a reusable coarse bottleneck table.  It keeps
diagnostic_coarse_breakdown separate from production_like so the diagnostic
overhead is visible instead of hidden inside the endpoint baseline.

Summary-script guardrails:
  if results_json does not identify a diagnostic mode, the summary now reports
  diagnostic_unknown instead of guessing diagnostic_light.  The CLI also
  accepts --diagnostic-mode when a standalone breakdown needs an explicit label.
  Legacy diagnostic_light_* JSON fields are retained only as aliases of the
  active diagnostic mode, and the alias target is recorded in
  diagnostic_light_fields_legacy_alias_of.

Low-intrusion coarse baseline artifact:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_low_intrusion_coarse_baseline_128sample_gen64/

inputs:
  attention_total_only 128x64 breakdown
  shared_body_total_only 128x64 breakdown
  engine_light 128x64 breakdown
  diagnostic_coarse_breakdown 32x64 breakdown for a single-artifact comparison

summary:
  real_bottleneck_summary.json
  real_bottleneck_summary.md

low-intrusion coarse rows:
  attention_total_only attention              182.239 s  (29.37% of source generate)
  attention_total_only MLP/MoE                304.434 s  (49.06%)
  attention_total_only MoE apply              176.253 s  (28.40%)
  shared_body_total_only shared direct         61.959 s  (10.00%)
  shared_body_total_only MoE apply            180.943 s  (29.20%)
  engine_light execute_model - model_forward    9.905 s  (1.66%)
  engine_light generate - execute_model         4.345 s  (0.73%)
  engine_light sample_tokens                    2.297 s  (0.38%)
```

Interpretation:

```text
This is the current preferred Amdahl-priority table.  It combines separate
low-intrusion diagnostic artifacts, so each share is relative to that source
artifact's generate time.  It is more appropriate for prioritization than the
single diagnostic_coarse_breakdown table, but it is still not a single-run
endpoint TPOT claim.

Current priority from this table:
  MLP/MoE and MoE apply remain the largest optimization direction.
  attention is a large secondary block.
  shared direct is a stable mid-sized bucket around 10%.
  engine/sampler residual is small in this split.
```

Do not use this mode as the official endpoint TPOT baseline.  For formal
performance claims, keep using production_like for endpoint timing and the
single-purpose low-intrusion diagnostic modes for attribution:
  shared_body_total_only
  attention_total_only
  engine_light
```

Verification for the shared-body / attention / engine diagnostic tranche:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest \
  tests/test_vllm_router_shadow_sink.py \
  tests/test_run_awq_telemetry_ladder_modes.py \
  tests/test_analyze_awq_decode_breakdown.py \
  tests/test_summarize_awq_real_bottlenecks.py -q

result:
  86 passed for the broader telemetry/analyzer/summary tranche
```

Tail-latency repeat helper:

```text
files:
  scripts/summarize_telemetry_ladder_repeats.py
  tests/test_summarize_telemetry_ladder_repeats.py
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py

trace addition:
  vLLM router trace writes sample_timing.jsonl.  Paths that can isolate one
  generated sample emit scope=sample rows with generate_elapsed_us /
  requested_output_tokens.  Batched chunks are labeled scope=chunk for audit
  only and are not used as per-sample p95/p99 evidence.

summary addition:
  repeat summaries now report sample_timing_count, sample_p50, sample_p95,
  sample_p99 when sample_timing.jsonl is present.
  final_gate_pass is a statistical gate over matching context, repeat count,
  median TPOT improvement, tail sample count, and p95/p99 tail regression.  It
  can be configured to require external parity evidence via --require-parity;
  the helper never infers output/logit parity from timing rows.  The default
  min_tail_samples is 30 so one-sample smokes cannot accidentally pass a
  tail-latency gate.

sample artifacts regenerated:
  outputs/reports/awq_telemetry_ladder/
    gpu1_sample_timing_smoke1_gen1/repeat_summary.{json,md}
    gpu1_shared_disable_stream_repeat3_32sample_gen64/repeat_summary.{json,md}

current behavior:
  gpu1_sample_timing_smoke1_gen1 exposes sample p50/p95/p99 from its single
  sample_timing row, but it is below the default tail-sample gate.
  gpu1_shared_disable_stream_repeat3_32sample_gen64 remains tail-latency
  unavailable because it predates sample_timing.jsonl.
  Having sample_p50/p95/p99 values does not mean a candidate passed the gate:
  final_gate_reason must still be checked for insufficient_tail_samples,
  missing_sample_timing, tail_latency_regression, median_not_improved, or an
  explicitly required parity failure.
  Multiple gate conditions can fail at once; final_gate_reason reports the
  first failed condition by priority, while the per-condition booleans
  (median_gate_pass, tail_latency_gate_pass, repeat_count_gate_pass, etc.)
  carry the full decision state.

verification:
  /home/husrcf/anaconda3/envs/TRY/bin/python -m pytest \
    tests/test_summarize_telemetry_ladder_repeats.py \
    tests/test_run_awq_telemetry_ladder_modes.py \
    tests/test_summarize_awq_real_bottlenecks.py -q

result:
  59 passed
```

Independent heldout prompt config:

```text
file:
  configs/trace/
    router_mtp_trace_aya_dataset_awq_vllm_gpu1_decode_independent_heldout128_gen64_base.yaml

split:
  data = configs/data/aya_dataset_512.yaml
  split_id = aya_dataset_512_indices_384_511_independent_heldout128_gen64
  split_source = data/traces/aya_dataset_512_autoround/manifest.jsonl
  expected sample range = 384..511
  start_sample = 384
  max_samples = 128
  max_tokens = 64

purpose:
  provide a second heldout prompt split for GPU1 AWQ decode validation and
  for run_awq_telemetry_ladder.py --base-config runs.  This is a config /
  reproducibility artifact only; it does not by itself establish a performance
  result.

defaults:
  record_router_topk = false
  decoder / MoE / engine / WNA16 timing hooks = off
  outcome logging = off
  descriptor-order execution = disabled

runner guard:
  run_awq_telemetry_ladder.py no longer overwrites start_sample / max_samples /
  max_tokens with CLI defaults.  If those CLI arguments are omitted, the base
  config split is preserved; explicit CLI values still override the base
  config.  This prevents the independent heldout config from silently falling
  back to the older 128/8/8 ladder defaults.
  The ladder writer also validates split metadata when present:
    expected_sample_start / expected_sample_end must match the effective
    start_sample / max_samples range
    split_source must match token_source_manifest after path normalization
    against cwd, repo root, and base_config.parent candidate anchors
    split_source_resolved_match is chosen from the matching candidates by
    preferring an existing path, so results metadata points at the real manifest
    when it is available
  summary.md records the effective resolved split values rather than raw
  optional CLI values.
  results.json rows also persist effective_start_sample, effective_max_samples,
  effective_max_tokens, effective_sample_end, split_override_active,
  split_metadata_validated, split_id, split_source, token_source_manifest, and
  expected sample range.
  A non-GPU config-generation smoke writes:
    outputs/reports/awq_telemetry_ladder/
      independent_heldout_config_smoke/trace_configs/production_like/repeat_00.yaml
  and confirms the generated ladder config keeps start_sample=384,
  max_samples=128, max_tokens=64 with record_router_topk=false and timing hooks
  disabled.

verification:
  /home/husrcf/anaconda3/envs/TRY/bin/python -m pytest \
    tests/test_run_awq_telemetry_ladder_modes.py \
    tests/test_summarize_telemetry_ladder_repeats.py \
    tests/test_summarize_awq_real_bottlenecks.py -q

result:
  59 passed
```

Independent heldout production-like run:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_independent_heldout128_gen64_production_like/

command:
  /home/husrcf/anaconda3/envs/TRY/bin/python \
    scripts/run_awq_telemetry_ladder.py \
    --base-config configs/trace/router_mtp_trace_aya_dataset_awq_vllm_gpu1_decode_independent_heldout128_gen64_base.yaml \
    --output-root outputs/reports/awq_telemetry_ladder/gpu1_independent_heldout128_gen64_production_like \
    --modes production_like \
    --gpu 1 \
    --conda-env TRY

result:
  returncode = 0
  effective split = samples 384..511
  requested output tokens = 8192
  split_override_active = false
  metadata_checks_passed = true
  split_source_resolved_match =
    /home/husrcf/Code/ProtBind/MTP/data/traces/aya_dataset_512_autoround/manifest.jsonl

endpoint:
  generate_wall_seconds = 488.8477
  TPOT = 0.059674 s/token

sample_timing:
  sample_timing_count = 128
  sample_p50 = 0.061404 s/token
  sample_p95 = 0.062807 s/token
  sample_p99 = 0.063873 s/token

interpretation:
  This establishes the independent heldout production-like baseline and a
  p95/p99-capable tail-latency artifact.  It is a baseline artifact only, not
  an optimization result.
```

Independent heldout attention total-only run:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_independent_heldout128_gen64_attention_total_only/

result:
  returncode = 0
  effective split = samples 384..511
  requested output tokens = 8192
  split_override_active = false
  metadata_checks_passed = true

endpoint:
  TPOT = 0.063529 s/token
  overhead vs independent production_like baseline = +6.46%

diagnostic decode sums:
  generate total                    520.428 s
  decoder layer total               483.162 s  (92.84% generate)
  attention                         165.602 s  (31.82%)
  MLP/MoE                           235.290 s  (45.21%)
  MoE apply                         120.078 s  (23.07%)
  MLP/MoE - MoE apply               115.212 s  (22.14%)
  outside attention+MLP              82.270 s  (15.81%)
  generate minus decoder layer       37.265 s  (7.16%)

interpretation:
  On this independent heldout artifact, attention_total_only observes
  attention as a large secondary block.  The mode adds measurable overhead and
  remains diagnostic-only.  It is not an endpoint performance claim or a
  repeat/tail gate pass.
```

Independent heldout shared-body total-only run:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_independent_heldout128_gen64_shared_body_total_only/

result:
  returncode = 0
  effective split = samples 384..511
  requested output tokens = 8192
  split_override_active = false
  metadata_checks_passed = true

endpoint:
  TPOT = 0.062232 s/token
  overhead vs independent production_like baseline = +4.29%

diagnostic decode sums:
  generate total                    509.802 s
  decoder layer total               475.685 s  (93.31% generate)
  MoE apply                         120.151 s  (23.57%)
  shared expert direct layer         54.925 s  (10.77%)
  generate minus decoder layer       34.117 s  (6.69%)

shared direct per-layer timing:
  p50 = 11049.494 us
  p95 = 11351.120 us
  p99 = 11551.896 us

interpretation:
  On this single independent heldout artifact, shared_body_total_only observes
  shared direct as a named coarse bucket around 10% of generate.  The p50/p95/p99
  values are diagnostic distribution summaries for this run only; they are not
  used as pass/fail tail gates without repeat evidence and the minimum sample
  gate.  This is attribution evidence only; the mode still adds diagnostic
  overhead.
```

Independent heldout engine-light run:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_independent_heldout128_gen64_engine_light/

result:
  returncode = 0
  effective split = samples 384..511
  requested output tokens = 8192
  split_override_active = false
  metadata_checks_passed = true

endpoint:
  TPOT = 0.063193 s/token
  overhead vs independent production_like baseline = +5.90%

sample_timing:
  sample_timing_count = 128
  sample_p50 = 0.062476 s/token
  sample_p95 = 0.075054 s/token
  sample_p99 = 0.084154 s/token

engine diagnostic sums:
  generate total                    517.679 s
  execute_model                     513.715 s  (99.23% generate)
  model_forward                     505.033 s  (97.56%)
  execute_model - model_forward       8.682 s  (1.68%)
  llm.generate - execute_model        3.964 s  (0.77%)
  logits processor                    0.415 s  (0.08%)
  sample_tokens                       1.900 s  (0.37%)
  sampler forward                     0.600 s  (0.12%)
  sampler sample                      0.192 s  (0.04%)
  decoder layer total               481.570 s  (93.03%)
  MoE apply                         121.972 s  (23.56%)

interpretation:
  On this diagnostic artifact, engine/scheduler/sampler rows are small relative
  to model_forward and decoder-layer timing.  The mode is attribution-only and
  adds overhead; it is not a production TPOT claim.
```

Independent heldout GPU0 production-like baseline:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu0_independent_heldout128_gen64_production_like/

result:
  returncode = 0
  effective split = samples 384..511
  requested output tokens = 8192
  split_override_active = false
  metadata_checks_passed = true

endpoint:
  generate_wall_seconds = 540.6852
  TPOT = 0.066002 s/token

sample_timing:
  sample_timing_count = 128
  sample_p50 = 0.067951 s/token
  sample_p95 = 0.068884 s/token
  sample_p99 = 0.069672 s/token

cross-GPU note:
  GPU0 production_like TPOT is about 10.6% slower than the GPU1 independent
  production_like baseline on this split (0.066002 vs 0.059674 s/token).
  This is a device/baseline observation, not an optimization result.
```

Independent heldout coarse bottleneck summary:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_independent_heldout128_gen64_coarse_summary/

inputs:
  production_like:
    gpu1_independent_heldout128_gen64_production_like/
  attention_total_only:
    gpu1_independent_heldout128_gen64_attention_total_only/
  shared_body_total_only:
    gpu1_independent_heldout128_gen64_shared_body_total_only/
  engine_light:
    gpu1_independent_heldout128_gen64_engine_light/

low-intrusion coarse table:
  attention_total_only:
    attention        165.602 s  (31.82% of that artifact generate)
    MLP/MoE          235.290 s  (45.21%)
    MoE apply        120.078 s  (23.07%)

  shared_body_total_only:
    shared direct     54.925 s  (10.77% of that artifact generate)
    MoE apply        120.151 s  (23.57%)

  engine_light:
    execute_model - model_forward   8.682 s  (1.68%)
    generate - execute_model        3.964 s  (0.77%)
    sample_tokens                   1.900 s  (0.37%)

interpretation:
  This summary combines separate diagnostic artifacts.  Shares are computed
  against each artifact's own generate time and should not be treated as one
  simultaneous run.  The production_like artifact is included only as context
  alignment and is not used as the denominator for the low-intrusion diagnostic
  percentages.

  This heldout setup artifact suggests MLP/MoE first and attention second,
  with shared direct as a named sub-bucket and engine/sampler residual small in
  this run.  This has not reached a repeat/gate-level conclusion for choosing
  a default optimization strategy.
```

Cross-GPU attention-total heldout check:

```text
summary artifact:
  outputs/reports/awq_telemetry_ladder/
    cross_gpu_independent_heldout_attention_summary.md

GPU0 artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu0_independent_heldout128_gen64_attention_total_only/

GPU0 result:
  TPOT = 0.069817 s/token
  overhead vs GPU0 production_like baseline = +5.78%
  sample_timing_count = 128
  sample_p50 = 0.070762 s/token
  sample_p95 = 0.083141 s/token
  sample_p99 = 0.083640 s/token

GPU0 diagnostic decode sums:
  generate total                    571.940 s
  decoder layer total               530.129 s  (92.69% generate)
  attention                         180.586 s  (31.57%)
  MLP/MoE                           259.738 s  (45.41%)
  MoE apply                         132.977 s  (23.25%)

GPU1 attention_total_only comparison:
  TPOT = 0.063529 s/token
  overhead vs GPU1 production_like baseline = +6.46%
  sample p50/p95/p99 are included in the summary artifact
  attention = 31.82%
  MLP/MoE = 45.21%
  MoE apply = 23.07%

interpretation:
  On this independent heldout split, the coarse attention/MLP-MoE/MoE-apply
  hierarchy is similar on both W7900 devices.  This is a single-run
  cross-device directional consistency signal for the bottleneck map, not an
  optimization result and not a repeat-level gate.
```

GPU1 independent heldout repeat-3 core modes:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_independent_heldout128_gen64_repeat3_core_modes/

summary:
  outputs/reports/awq_telemetry_ladder/
    gpu1_independent_heldout128_gen64_repeat3_core_modes/repeat_summary.md

scope:
  split = samples 384..511
  max_tokens = 64
  requested output tokens per repeat = 8192
  repeats = 3
  device = GPU1 W7900

median TPOT:
  production_like          0.065109 s/token
  attention_total_only     0.067021 s/token  (+2.94% median)
  shared_body_total_only   0.071201 s/token  (+9.36% median)

sample timing, 384 rows per mode:
  production_like:
    p50/p95/p99 = 0.067166 / 0.068847 / 0.070033 s/token
  attention_total_only:
    p50/p95/p99 = 0.070106 / 0.080686 / 0.083266 s/token
    p95/p99 delta vs production_like = +17.20% / +18.90%
  shared_body_total_only:
    p50/p95/p99 = 0.069610 / 0.087635 / 0.157121 s/token
    p95/p99 delta vs production_like = +27.29% / +124.35%

gate result:
  attention_total_only final_gate_pass = false
  shared_body_total_only final_gate_pass = false
  final_gate_reason = median_not_improved
  tail_latency_gate_pass = false for both modes

interpretation:
  Repeat-3 confirms that attention_total_only is a useful low-intrusion
  attribution mode but still has measurable endpoint and tail overhead.
  shared_body_total_only is much noisier in tail latency and remains
  diagnostic-only.  These repeat results supersede single-run overhead numbers
  for gating decisions.
```

GPU0 sidecar descriptor-consumer micro-runtime while GPU1 repeat was running:

```text
artifacts:
  outputs/reports/tile_order_cache/gpu0_sidecar_descriptor_consumer_quick_check.md
  outputs/reports/tile_order_cache/gpu0_sidecar_descriptor_consumer_cta_sweep.md

input trace:
  data/traces/aya_dataset_128_awq_vllm_descriptor_order_shadow_count_only_minimal_aggregate_batched/

scope:
  selected windows = 128
  selected requests = 65,536
  unique tiles = 256
  device = GPU0
  tile_elems = 1024
  flush = 0

quick check:
  tiles/CTA=4:
    layer_prior_frequency speedup = 1.0505x
    layer_prior_frequency_two_level speedup = 1.0354x
  tiles/CTA=8:
    layer_prior_frequency speedup = 1.0779x
    layer_prior_frequency_two_level speedup = 0.8797x

CTA sweep:
  two-level speedup:
    tiles/CTA=1   1.5093x
    tiles/CTA=2   1.1677x
    tiles/CTA=16  0.7775x
    tiles/CTA=32  0.7383x
  materialized layer_prior speedup:
    tiles/CTA=16  1.0695x
    tiles/CTA=32  1.1098x

group-plan stats:
  groups = 18,266
  avg group size = 3.588
  p95 group size = 11
  max group size = 62
  avg groups/window = 142.703

interpretation:
  The sidecar did not load the AWQ/vLLM model and is safe as a lightweight GPU0
  micro-runtime check, but it should not overlap with GPU1 repeat runs when
  repeat stability is the priority.  The result reinforces that
  two-level execution needs a narrow groups_per_cta gate; small groups_per_cta
  can be positive, while larger groups_per_cta can regress.  Net saved time
  remains negative once current host-side plan/materialization cost is included,
  so this is still gated micro-runtime evidence rather than a runtime win.
```

Independent prompt-source smoke_text AWQ/vLLM check:

```text
config:
  configs/trace/
    router_mtp_trace_smoke_text_awq_vllm_gpu1_decode_independent_prompt_smoke8_gen64_base.yaml

data:
  configs/data/smoke_text_8.yaml

artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_smoke_text_independent_prompt_smoke8_gen64_core_v3/

scope:
  source = inline smoke_text_8 prompts
  samples = 8
  max_tokens = 64
  requested output tokens = 512
  device = GPU1 W7900
  modes = production_like, attention_total_only

endpoint:
  production_like TPOT        0.067123 s/token
  attention_total_only TPOT   0.067270 s/token  (+0.22%)

attention_total_only coarse breakdown:
  attention     11.063 s  (32.12% of diagnostic generate)
  MLP/MoE       15.864 s  (46.06%)
  MoE apply      8.076 s  (23.45%)
```

Interpretation:

```text
This is an independent prompt-source smoke, not a strong lab gate.  It uses
only 8 inline prompts, so it should not replace the AYA heldout repeat-3 gate.
It does, however, reproduce the same coarse hierarchy direction:
  MLP/MoE largest
  attention second
  MoE apply around the low-20% range

The first smoke_text run used the shared two-prompt smoke data source and only
covered 2 samples; it is retained only as a sanity check.  The intermediate v2
run used 8 prompts but was produced before splitting the data file, so it is
also superseded for reproducibility.  The current v3 artifact's trace configs
point directly at configs/data/smoke_text_8.yaml, while the original
smoke_text.yaml keeps its quick 2-sample semantics.
```

## Prefetch Action Replay Refocus

The prefetch line is now refocused on production-like action replay rather
than descriptor-order / direct_topk / WNA16 runtime branches.

Claim boundary:

```text
MTP/transition utility is a low-trust future-expert hint.
It is evaluated only as an admission signal on top of a protected
transition_top32 baseline.

This is replay / local stall-proxy evidence, not endpoint TPOT evidence and
not a real DMA/cache-manager implementation.
```

Primary report:

```text
outputs/reports/prefetch_action_replay/prefetch_claim_gate.md
```

AYA512 normal-envelope replay:

```text
artifact:
  outputs/reports/prefetch_action_replay/
    aya512_production_like_action_replay_normal.json
    aya512_production_like_action_replay_normal_pareto.md
    aya512_production_like_action_replay_normal_claim_gate.md

configuration:
  bandwidth_gbps = 6.589
  action_cost_overlap_factor = 0.8

baseline transition_top32:
  ready mass       0.8006
  top1 hit         0.9065
  weighted miss    0.0224

normal positive signal:
  utility_keep50:
    stall_reduction_vs_transition = 7.61%
    extra issued bytes            = 1.486 TB
    saved supplemental fetches    = 69,528
    used / extra byte             = 0.077

  score_keep50:
    stall_reduction_vs_transition = 7.10%
    extra issued bytes            = 1.277 TB
    saved supplemental fetches    = 64,908
    used / extra byte             = 0.084

fixed-extra tradeoff:
  extra1/2/4/8 produces 3.96% / 6.71% / 10.69% / 16.33% stall-proxy reduction,
  but byte efficiency monotonically drops from 0.080 to 0.041 used/extra byte.
```

Action-level interpretation:

```text
normal utility_keep50:
  full_fetch count = 900,460
  metadata count   = 558,399
  premap count     = 708,823
  metadata net ms  = -569.94
  premap net ms    = +48.81

normal score_keep50:
  full_fetch count = 773,820
  metadata count   = 935,694
  premap count     = 637,273
  metadata net ms  = -904.55
  premap net ms    = +37.22

Interpretation:
  gated full_fetch supports a positive local stall/readiness proxy in the
  normal envelope.
  premap has a small positive setup proxy under overlap.
  metadata is negative under the current byte/cost model and should remain
  secondary or diagnostic unless the saved-us/overlap model changes.
```

AYA512 severe-stress replay:

```text
artifact:
  outputs/reports/prefetch_action_replay/
    aya512_production_like_action_replay_stress.json
    aya512_production_like_action_replay_stress_pareto.md
    aya512_production_like_action_replay_stress_claim_gate.md

configuration:
  bandwidth_gbps = 3.0
  action_cost_overlap_factor = 0.0
  downgrade_full_fetch_ready_threshold = 1.10

stress result:
  score_keep50:
    full_fetch count = 0
    stall reduction  = 0.00%
    metadata net ms  = -35,077.82
    premap net ms    = -753.64

  utility_keep50:
    full_fetch count = 0
    stall reduction  = 0.00%
    metadata net ms  = -29,917.05
    premap net ms    = -825.79
```

Interpretation:

```text
The stress gate behaves correctly:
  speculative full_fetch is disabled,
  transition_top32 readiness is preserved,
  no local stall-proxy gain is claimed under the stress envelope,
  metadata/premap are net-negative without overlap and should not be default
  runtime actions in this envelope.
```

Current prefetch claim gate:

```text
status = partial pass across AYA512 + Dolly prefix127

supported:
  across both prompt sources, normal-envelope MTP extras improve local
  stall/readiness proxy over transition_top32.
  across both prompt sources, severe-stress fallback shuts down full_fetch
  instead of forcing speculative payload fetch.

not yet supported:
  endpoint TPOT improvement
  real DMA/cache-manager benefit
  metadata default enablement
  premap default enablement under stress

current endpoint boundary:
  Amdahl mapping is complete as an upper-bound estimate only.
  It is not measured endpoint TPOT and does not assume a real cache manager.
```

Dolly/external prompt replay follow-up:

```text
artifact:
  outputs/reports/prefetch_action_replay/next_dolly_action_replay_plan.md

status:
  superseded by completed Dolly prefix127 replay evidence.

result:
  Dolly prefix127 now has merged true-router + MTP candidate manifests,
  MTP token top-M sidecar, prefc-fixed manifest, tensor-cache artifact, and
  normal/stress action replay reports.

next gate:
  move to the controlled real prefetch lab harness:
    outputs/reports/prefetch_action_replay/real_prefetch_lab_experiment_plan.md
```

Curated local 32-prompt prompt-source smoke:

```text
config:
  configs/trace/
    router_mtp_trace_smoke_text_awq_vllm_gpu1_decode_independent_prompt_smoke32_gen64_base.yaml

data:
  configs/data/smoke_text_32.yaml

artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_smoke_text_independent_prompt_smoke32_gen64_core/

repeat-3 artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_smoke_text_independent_prompt_smoke32_gen64_repeat3_core/

scope:
  source = locally curated inline prompts
  samples = 32
  max_tokens = 64
  requested output tokens = 2,048
  device = GPU1 W7900
  modes = production_like, attention_total_only

endpoint:
  GPU1 single-run production_like TPOT        0.066393 s/token
  GPU1 single-run attention_total_only TPOT   0.072234 s/token  (+8.80%)

  GPU1 repeat-3 production_like median        0.069836 s/token
  GPU1 repeat-3 attention_total_only median   0.069860 s/token  (+0.03%)
  GPU1 repeat-3 attention_total_only p95/p99 delta vs production_like = +13.22% / -3.27%

  GPU0 production_like TPOT        0.065958 s/token
  GPU0 attention_total_only TPOT   0.069304 s/token  (+5.07%)
  GPU0 attention_total_only p95/p99 delta vs production_like = +20.17% / +23.45%

GPU1 repeat-3 attention_total_only repeat_00 coarse breakdown:
  attention     46.099 s  (31.61% of diagnostic generate)
  MLP/MoE       65.946 s  (45.22%)
  MoE apply     33.411 s  (22.91%)

GPU0 attention_total_only coarse breakdown, clean rerun2:
  attention     45.108 s  (31.78% of diagnostic generate)
  MLP/MoE       64.101 s  (45.16%)
  MoE apply     32.610 s  (22.98%)
```

Interpretation:

```text
This 32-prompt run is stronger than smoke_text_8 for sample count but is still a
local curated prompt sanity split, not an external heldout dataset.  It supports
the same coarse hierarchy:
  MLP/MoE largest
  attention second
  MoE apply around 23%

It also reinforces the telemetry boundary:
  attention_total_only is attribution-only, not production-equivalent.
  On GPU1 repeat-3, median overhead is near zero but p95 still regresses,
  so the final gate remains closed.  The first GPU0 run was contaminated by
  display/interactive GPU0 use and is superseded by
  gpu0_smoke_text_independent_prompt_smoke32_gen64_core_rerun2_clean/.
```

## Descriptor-Order Runtime Gate

The current closest-to-runtime branch is same-multiset descriptor/tile
visitation ordering:

```text
true router outcome
-> current-router descriptor/tile stream
-> layer_prior_frequency two-level group plan
-> same multiset, same checksum, changed visitation order
```

The measured first runtime envelope is intentionally gated:

```text
execution_mode = two_level_group_plan
tile_elems in {512, 1024, 2048}
groups_per_cta in {4, 8}
groups_per_cta in {16, 32} remains diagnostic-only
groups_per_cta >= 64 is disabled
devices = {GPU0, GPU1}
```

The runtime adapter is now explicit and local:

- `DescriptorOrderRuntimeGate` loads
  `configs/runtime/descriptor_order_two_level_gate.yaml`.
- `build_noop_descriptor_order_assertion()` maps current-router top-k tensors
  to a group-plan report without mutating router tensors or changing vLLM
  execution.
- The gate closes if required correctness evidence is missing.  The low-cost
  `count_only` report is telemetry only; callers must pass explicit
  `same_multiset` and `checksum_delta` evidence from a no-op assertion or
  consumer parity check before the runtime gate can allow execution.
- Reason priority is envelope-first after execution-mode mismatch:
  unsupported tile/group/device settings are rejected before correctness
  details are interpreted.

This is the intended boundary for the next vLLM/HIP patch.  The project should
not silently edit conda `site-packages`; real integration should use an
explicit local fork, overlay, or monkey-patch entrypoint that first runs this
no-op assertion path and returns the original top-k tensors unchanged.

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

rocWMMA LDS-staged tile consumer smoke:

Implemented a second rocWMMA smoke that compares one 16x16x16 tile under three
paths:

```text
global_baseline:
  rocWMMA loads A/B directly from global memory

lds_hit:
  stage A/B into LDS, then rocWMMA loads fragments from LDS

lds_miss_overwrite:
  stage a wrong B tile into LDS, overwrite B after validation,
  then rocWMMA consumes the corrected LDS B tile
```

Artifacts:

- Source: `microbench/rocwmma_smoke/rocwmma_tile_stage.hip`
- Runner: `scripts/run_rocwmma_tile_stage.py`
- Report: `outputs/reports/rocwmma_smoke/rocwmma_tile_stage_2gpu.json`
- Reuse report: `outputs/reports/rocwmma_smoke/rocwmma_tile_stage_reuse_2gpu.json`

The smoke now treats B as the expert weight tile and supports `--consumer-rows`.
`lds_hit` stages B once into LDS, then reuses it across multiple synthetic
token rows while each row loads a separate A tile from global memory.

Two-GPU result:

```text
consumer_rows = 1 / 4 / 8
all modes max_abs_err = 0.0

GPU0 lds_hit speedup vs global:
  rows=1: 0.968x
  rows=4: 0.949x
  rows=8: 0.947x

GPU1 lds_hit speedup vs global:
  rows=1: 0.988x
  rows=4: 0.971x
  rows=8: 0.966x

GPU0 lds_miss_overwrite speedup vs global:
  rows=1: 0.902x
  rows=4: 0.898x
  rows=8: 0.889x

GPU1 lds_miss_overwrite speedup vs global:
  rows=1: 0.914x
  rows=4: 0.910x
  rows=8: 0.895x
```

Interpretation:

- rocWMMA fragments can consume LDS-staged tiles correctly on gfx1100.
- In this minimal no-overlap smoke, even B-tile reuse across 1/4/8 synthetic
  rows does not beat direct rocWMMA global loads. `lds_miss_overwrite` is slower
  still. This is expected and useful: simple LDS staging is not a default
  speedup mechanism unless a same-kernel validation window, larger grouped tile
  reuse, or scheduling overlap hides the staging cost.
- This result strengthens the contract: LDS staging must remain gated by
  expected hit rate, p_min, occupancy, and available validation/metadata window.
- Next gates are a rocWMMA tile-stage benchmark with explicit same-kernel
  validation-window timing, more realistic grouped tile shapes, and hit/miss
  p_min reporting. A rocprof pass should also confirm global/LDS traffic and
  occupancy effects before any performance claim is made.

rocWMMA same-kernel validation-window p_min sweep:

The rocWMMA tile-stage smoke now supports `--validate-iters`. The kernel uses
the same action order as the proposed staging contract:

```text
global_baseline:
  validation work -> rocWMMA loads B from global memory

lds_hit:
  stage B into LDS -> validation work -> rocWMMA consumes staged B

lds_miss_overwrite:
  stage wrong B into LDS -> validation work -> overwrite with true B
  -> rocWMMA consumes corrected B
```

The runner reports p_min per `(device, consumer_rows, validate_iters)`:

```text
T_spec = p * T_hit + (1 - p) * T_miss
profitable when T_spec < T_global
```

Artifact:

- Report: `outputs/reports/rocwmma_smoke/rocwmma_tile_stage_validate_2gpu.json`
- Policy eval: `outputs/reports/rocwmma_smoke/lds_stage_policy_eval_rocwmma_serial.json`
- Policy eval markdown: `outputs/reports/rocwmma_smoke/lds_stage_policy_eval_rocwmma_serial.md`

Grid:

```text
devices = [GPU0, GPU1]
consumer_rows = [1, 4, 8]
validate_iters = [0, 64, 256]
modes = [global_baseline, lds_hit, lds_miss_overwrite]
```

Result:

```text
all rows ok = true
all max_abs_err = 0.0
all 18 p_min rows = not_profitable_even_at_full_hit
policy evaluator:
  transition_top16 enabled = 0 / 18
  transition_top17_32 enabled = 0 / 18
  mtp_extra1_4 enabled = 0 / 18
  mtp_extra5_8 enabled = 0 / 18
  random_control enabled = 0 / 18
```

Representative rows:

```text
GPU0 rows=1 validate=0:
  global=0.01005 ms, hit=0.01050 ms, miss=0.01126 ms

GPU0 rows=4 validate=256:
  global=0.02065 ms, hit=0.02238 ms, miss=0.02349 ms

GPU1 rows=8 validate=256:
  global=0.02358 ms, hit=0.02477 ms, miss=0.02627 ms
```

Interpretation:

- rocWMMA correctness for global, staged-hit, and staged-miss-overwrite paths is
  stable under the validation-window sweep.
- A serial same-kernel validation phase does not hide the LDS staging cost.
  Even full hit-rate is not profitable in this small tile benchmark.
- This is a useful negative boundary: the next WMMA gate must model real
  overlap or pipelining, for example separate producer/validator waves,
  multiple workgroups, persistent grouped-GEMM scheduling, larger grouped tile
  shapes, or rocprof-confirmed latency hiding.
- The runtime policy implication remains conservative: `lds_stage` is disabled
  unless measured p_min is finite and the expected hit rate clears it with a
  safety margin. The runtime gate now reports `lds_p_min_not_profitable` for
  non-finite / not-profitable p_min artifacts.

rocWMMA multi-CTA / large B-pool throughput sweep:

The rocWMMA tile-stage benchmark now supports:

```text
num_cta
b_pool_tiles
tile_stride
cache_flush_elems
global_frag_reuse baseline
global_reload_per_row baseline
wall_us_per_output_tile
```

Motivation:

```text
global_frag_reuse:
  B is loaded once into a rocWMMA fragment and reused across rows.
  This is a strong baseline and LDS staging adds an extra global->LDS->fragment hop.

global_reload_per_row:
  B is reloaded for each consumer row.
  This is the scenario where sharing B through LDS can plausibly help.
```

Artifact:

- Report: `outputs/reports/rocwmma_smoke/rocwmma_tile_stage_multicta_2gpu.json`
- Strong-baseline policy eval:
  `outputs/reports/rocwmma_smoke/lds_stage_policy_eval_rocwmma_multicta_frag_reuse.json`
- Reload-baseline policy eval:
  `outputs/reports/rocwmma_smoke/lds_stage_policy_eval_rocwmma_multicta_reload.json`

Grid:

```text
devices = [GPU0, GPU1]
consumer_rows = [4, 8, 16]
num_cta = [64, 256]
b_pool_tiles = [1024]
tile_stride = [17]
cache_flush_elems = [1048576]
validate_iters = [0]
```

Summary:

```text
against global_frag_reuse:
  not_profitable_even_at_full_hit = 11 / 12
  finite p_min rows = 1 / 12
  enabled rows under default tier table = 1 / 12 for non-random tiers

against global_reload_per_row:
  not_profitable_even_at_full_hit = 7 / 12
  finite / always-profitable rows = 5 / 12
  enabled rows under default tier table = 4 / 12 for transition/MTP tiers
```

Representative profitable rows against `global_reload_per_row`:

```text
GPU0 rows=8 num_cta=256:
  p_min ~= 0.136

GPU0 rows=16 num_cta=256:
  p_min = 0.0  # profitable for any hit rate in this run

GPU1 rows=8 num_cta=256:
  p_min ~= 0.067

GPU1 rows=16 num_cta=256:
  p_min = 0.0
```

Interpretation:

- The earlier serial negative result is not solely a single-CTA artifact.
  Against the strong `global_frag_reuse` baseline, LDS staging remains mostly
  unprofitable.
- LDS staging starts to look useful only against the weaker
  `global_reload_per_row` baseline, where the baseline repeatedly reloads B.
- Therefore the safe claim is narrower: rocWMMA LDS staging may help only when
  the real grouped-GEMM path cannot already reuse the expert B tile in
  fragments/registers and when enough rows share that B tile.
- The next required gate is rocprof/counter validation. We need to confirm
  whether the actual target kernel resembles `global_frag_reuse` or
  `global_reload_per_row`, and whether the observed wins correspond to lower
  global B traffic rather than timing noise.

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

## rocWMMA / LDS Staging Microbench Status

Current LDS direction is deliberately gated by kernel-specific evidence:

```text
hand-written HIP LDS mock:
  supports a speculative staging envelope under anti-artifact controls

rocWMMA serial stage -> validate -> consume:
  rejected by p_min gate
  all tested serial configs were not_profitable_even_at_full_hit

rocWMMA multi-CTA baseline split:
  global_frag_reuse baseline:
    LDS staging is almost always rejected
    interpretation: no room when B fragment/register reuse is already strong

  global_reload_per_row baseline:
    several rows have finite or zero p_min
    representative:
      GPU0 rows=8  cta=256  p_min ~= 0.136
      GPU0 rows=16 cta=256  p_min = 0.0
      GPU1 rows=8  cta=256  p_min ~= 0.067
      GPU1 rows=16 cta=256  p_min = 0.0
    interpretation: LDS staging is conditionally viable when B-tile reload
    pressure exists
```

Safe claim:

```text
LDS staging is conditionally viable, not universally beneficial.
The next gate is classifying whether the real target grouped-GEMM path is
fragment-reuse-like or reload-per-row-like.
```

rocprof classification harness:

```text
script:
  scripts/run_rocwmma_rocprof_classification.py

smoke output:
  outputs/reports/rocwmma_smoke/rocprofv3_classification_raw_smoke/

tool status:
  rocprof-compute is not usable in the current environment because Python UI
  dependencies are missing.
  legacy rocprof works only when counters are split into HW-feasible groups.
  rocprofv3 is available and the harness supports per-metric runs to avoid
  multi-counter hangs.

current counter caveat:
  On the W7900/gfx1100 rocWMMA smoke, SQ_WAVES is non-zero but SQ_INSTS_LDS /
  SQ_INSTS_TEX_LOAD / FETCH_SIZE currently report zero under rocprof/rocprofv3.
  Therefore these counters are not yet trusted for B-reload classification.
  The harness explicitly records metric_completeness so zero-valued counter
  runs are not misread as real no-traffic evidence.

counter discovery / positive-control follow-up:
  rocprofv3-avail is now captured in reports:
    rocprofv3-avail list --agent
    rocprofv3-avail -d <device> list --pmc
    rocprofv3-avail -d <device> pmc-check <metrics>

  On GPU0, rocprofv3-avail lists the selected counters and pmc-check accepts
  SQ_WAVES / SQ_INSTS_LDS / SQ_INSTS_TEX_LOAD / FETCH_SIZE together. However,
  positive-control kernels still show only SQ_WAVES as non-zero:

    global_load_heavy:
      SQ_WAVES non-zero
      SQ_INSTS_LDS / SQ_INSTS_TEX_LOAD / FETCH_SIZE = 0

    lds_heavy:
      SQ_WAVES non-zero
      SQ_INSTS_LDS / SQ_INSTS_TEX_LOAD / FETCH_SIZE = 0

  This means the current counter path is not informative even for obvious
  global/LDS traffic. The issue is therefore not specific to rocWMMA. Until a
  trustworthy counter path is found, B-reload classification must not use these
  counter values.

  Visibility / agent-index salvage checks:
    HIP_VISIBLE_DEVICES=0 / ROCR_VISIBLE_DEVICES=0 / HSA_VISIBLE_DEVICES=0
    does not change the result.
    rocprofv3 --agent-index type-relative also does not change the result.

  Both runs still report SQ_WAVES = 2048 for 256 blocks x 256 threads on
  wave32, while the selected traffic counters remain zero. This confirms that
  the kernel filter, parser, and basic agent selection are working, but the
  traffic/LDS counter values remain unsuitable for claims.

static ISA fallback:
  scripts/inspect_hip_isa_static.py extracts .hip_fatbin, unbundles the
  gfx1100 device object, disassembles it, and counts instruction buckets such
  as global_load, lds_load, lds_store, barrier, waitcnt, and WMMA/matrix ops.

  Positive-control static smoke confirms the fallback sees the expected ISA:
    global_load_heavy: global_load present, no LDS load/store bucket
    lds_heavy: global_load plus lds_load / lds_store / barrier buckets present

  rocWMMA tile-stage static smoke also finds global_load, lds_load, lds_store,
  barrier, waitcnt, and a WMMA/matrix bucket. This is static supporting
  evidence only; it cannot replace hardware byte counters, but it is a safe
  fallback when profiler counters are non-informative.

mode-specialized rocWMMA kernels:
  The rocWMMA tile-stage benchmark no longer relies on one device kernel with a
  runtime mode switch. It now launches separate kernels:

    global_frag_reuse_kernel
    global_reload_per_row_kernel
    lds_hit_kernel
    lds_miss_overwrite_kernel

  This makes rocprof kernel filtering and static ISA inspection mode-specific.
  Host CLI semantics remain unchanged through --mode.

  GPU0 specialized smoke:
    rows=8, num_cta=64, b_pool=1024, stride=17, cache_flush=1M
    correctness: all four modes pass
    timing:
      global_frag_reuse      0.0109996 ms
      global_reload_per_row  0.0114240 ms
      lds_hit                0.0120080 ms
      lds_miss_overwrite     0.0126960 ms
    p_min status:
      vs global_frag_reuse: not_profitable_even_at_full_hit
      vs global_reload_per_row: not_profitable_even_at_full_hit

  Static ISA now separates the four symbols. The LDS modes show LDS load/store
  buckets, while global modes do not. However, static instruction counts do not
  expand runtime loops, so global_frag_reuse and global_reload_per_row can still
  look structurally similar in ISA. Reload pressure therefore still needs
  timing classification; static ISA is a structural sanity check, not a dynamic
  traffic substitute.

reload-pressure ladder:
  A two-GPU specialized ladder was run with:

    devices: GPU0 W7900, GPU1 W7900 Dual Slot
    rows: 8, 32
    num_cta: 64, 256
    b_pool_tiles: 1024, 16384
    cache_flush_elems: 0, 16M
    modes: frag, reload, distinct-reload, lds_hit, lds_miss

  Artifact:
    outputs/reports/rocwmma_smoke/rocwmma_tile_stage_specialized_ladder_2gpu.json
    outputs/reports/rocwmma_smoke/rocwmma_tile_stage_specialized_ladder_2gpu_summary.md

  Summary:
    config rows: 32
    LDS hit beats global_frag_reuse: 7 / 32
    LDS hit beats global_reload_per_row: 7 / 32
    LDS hit beats global_reload_distinct_per_row: 17 / 32

  Interpretation:
    distinct-B reload amplification can create reload pressure, and LDS hit can
    beat that distinct-reload control in some rows. However, this is not yet a
    clean default-positive LDS result: several wins depend on cache-flush /
    large-pool conditions, miss behavior remains unstable, and the direct
    global-fragment path is often still the fastest baseline. Naive LDS payload
    staging therefore remains a gated branch, not the main runtime direction.

  Current branch condition:
    If further official-like rocWMMA LB2/PGR1/CP or double-buffer tests do not
    show a robust hit-path win against a reload-heavy baseline, demote LDS
    payload staging to a negative result / optional future action.

New engineering direction from review:
  The higher-ROI systems direction is now:

    MTP/transition-guided cache-aware tile ordering for exact MoE grouped dispatch.

  In this pivot, MTP/transition hints do not stage payload into LDS. They guide:
    tile visitation order
    expert-major / B-tile grouped scheduling
    hot-first ordering
    descriptor precompute / patching
    persistent grouped scheduler work assignment

  Candidate metrics:
    tile-order hit rate
    B tile reuse distance
    unique B tiles per scheduling window
    wall time under hot/cold expert ordering
    descriptor build / patch / overwrite time

  This aligns better with MetaShuffling / persistent grouped-GEMM directions
  while preserving the project's low-trust MTP prior: true router remains
  authoritative, but hint quality can influence cache-aware scheduling order.
```

Next LDS / rocWMMA steps:

```text
1. Keep trying for a trustworthy counter path only through positive controls,
   but treat the current rocprofv3 counter values as non-informative:
   - rocprofv3-avail discovery is recorded
   - positive-control kernels fail to produce non-zero LDS/global traffic
     counters beyond SQ_WAVES
   - visibility masks and --agent-index type-relative did not fix the issue

2. Use static ISA inspection plus timing-based baseline classification as the
   interim path:
   - static global/LDS instruction buckets
   - frag_reuse vs reload_per_row timing similarity
   - p_min status from the measured baseline split

3. Once counters are trustworthy, additionally report:
   kernel, wall_time, global_read_bytes, LDS traffic, occupancy,
   WMMA utilization proxy, B_reload_ratio, p_min_status

4. Only if the target path is reload-like:
   first test official-like rocWMMA LB2/PGR1/CP and a small double-buffer
   skeleton. Only move to producer-consumer / persistent grouped-GEMM if those
   hit paths beat the reload-heavy baseline.

5. If the target path is fragment-reuse-like:
   demote LDS staging from primary runtime action and focus on dispatch /
   metadata / premap scheduling instead.

6. Independent of LDS, start the no-payload pivot:
   MTP/transition-guided tile-order / cache-locality bench over the direct
   global-fragment path.
```

## Cache-Aware Tile-Order Pivot

The no-payload tile-order simulator is now implemented:

```text
module:  src/mtp_expert_prefetch/runtime/tile_order.py
script:  scripts/simulate_tile_order_cache.py
tests:   tests/test_runtime_tile_order.py
```

Supported inputs:

```text
synthetic locality traces
JSON tile-request traces
event-stall tensor caches with transition_scores / mtp_scores / target_mass
```

The first real-cache smoke used:

```text
cache:       outputs/reports/prefetch_shadow_512sample_mtp_extra/event_stall_tensor_cache_512sample.pt
examples:    512
window size: 64 token examples per layer window
topk:        target top8 experts
tiles/expert: 1
artifact:    outputs/reports/tile_order_cache/tile_order_cache_512sample_smoke.md
```

Key trace-level results:

```text
linear:
  reuse_distance_mean = 29.23
  LRU@8 = 0.391
  LRU@32 = 0.758
  tile_order_hit_rate = 0.414

B-tile/expert grouped:
  reuse_distance_mean = 20.19
  LRU@8 = 0.833
  LRU@32 = 0.833
  tile_order_hit_rate = 0.119

transition_hot_first:
  reuse_distance_mean = 25.36
  LRU@8 = 0.591
  LRU@32 = 0.798
  tile_order_hit_rate = 0.461

MTP+transition hot-first:
  reuse_distance_mean = 26.13
  LRU@8 = 0.549
  LRU@32 = 0.793
  tile_order_hit_rate = 0.489

utility_hot_first:
  reuse_distance_mean = 25.98
  LRU@8 = 0.557
  LRU@32 = 0.794
  tile_order_hit_rate = 0.491

transition_tile_grouped:
  reuse_distance_mean = 19.45
  LRU@8 = 0.833
  LRU@32 = 0.835
  tile_order_hit_rate = 0.461

MTP+transition_tile_grouped:
  reuse_distance_mean = 19.40
  LRU@8 = 0.833
  LRU@32 = 0.835
  tile_order_hit_rate = 0.489

utility_tile_grouped:
  reuse_distance_mean = 19.41
  LRU@8 = 0.833
  LRU@32 = 0.835
  tile_order_hit_rate = 0.491

oracle_cache_aware:
  reuse_distance_mean = 19.19
  LRU@8 = 0.834
  LRU@32 = 0.836
  tile_order_hit_rate = 0.983
```

Interpretation:

```text
Pure B-tile grouping maximizes small-cache locality but loses hot-first order.
Transition/MTP/utility hot-first improves tile-order hit rate while preserving
part of the locality gain over linear order.

The hybrid tile-grouped policies are the current best non-oracle candidates:
they keep the locality of B-tile grouping while ordering tile groups by
transition/MTP/utility score. `utility_tile_grouped` keeps LRU@8 near `0.833`
and raises tile-order hit rate from `0.119` to `0.491`.

This validates the pivot as a schedulability question:
  choose between locality-first and hot-first tile visitation,
  then measure the selected orders in a direct/global-fragment consumer.
```

Current claim boundary:

```text
This simulator does not claim kernel speedup. It filters tile-order policies
before HIP/rocWMMA timing. LDS payload staging remains a gated/future branch.
```

Direct/global-fragment timing smoke:

```text
bench:    microbench/tile_order_cache/tile_order_cache_bench.hip
runner:   scripts/run_tile_order_cache_bench.py
artifact: outputs/reports/tile_order_cache/tile_order_cache_bench_512sample_2gpu_tile1024_flush16m.json
input:    same 512-cache tile multiset, top8 target experts, tiles/expert=1
kernel:   direct global B-tile consume, no LDS payload staging
stress:   tile_elems=1024, cache_flush_elems=16M, tiles_per_cta=32
devices:  GPU0 W7900, GPU1 W7900 Dual Slot
```

Timing rows:

```text
GPU0:
  linear               0.2895 ms  speedup 1.000x
  utility_hot_first    0.2908 ms  speedup 0.996x
  B-tile grouped       0.2716 ms  speedup 1.066x
  utility_tile_grouped 0.2679 ms  speedup 1.081x
  oracle_cache_aware   0.2779 ms  speedup 1.042x

GPU1:
  linear               0.3054 ms  speedup 1.000x
  utility_hot_first    0.3073 ms  speedup 0.994x
  B-tile grouped       0.2769 ms  speedup 1.103x
  utility_tile_grouped 0.2779 ms  speedup 1.099x
  oracle_cache_aware   0.2719 ms  speedup 1.123x
```

Interpretation:

```text
The direct/global consumer confirms the simulator's same-hotness ablation:
utility_hot_first improves hot-order but hurts locality and does not improve
timing. Grouped policies are faster under cache-flush stress.

utility_tile_grouped keeps the same order_hit as utility_hot_first while
recovering B-tile locality. It is fastest on GPU0 and effectively tied with
B-tile grouping on GPU1, while preserving much higher hot-order signal.
```

Claim boundary:

```text
This is still a microbench, not a full grouped-GEMM kernel result. The next
gate is a stability sweep over tile_elems / tiles_per_cta / cache flush /
process repeats, then a persistent grouped scheduler prototype only if the
timing advantage is stable.
```

Stability sweep:

```text
artifact: outputs/reports/tile_order_cache/tile_order_cache_bench_512sample_stability_2gpu.json
summary:  outputs/reports/tile_order_cache/tile_order_cache_bench_512sample_stability_2gpu_summary.md
devices:  GPU0 W7900, GPU1 W7900 Dual Slot
repeat:   5 process-level runs per policy/config
tiles:    tile_elems = 512 / 1024
flush:    0 / 16M
```

Median speedup of `utility_tile_grouped` vs `linear`:

```text
GPU0 tile512  flush0:   1.058x
GPU0 tile512  flush16M: 1.079x
GPU0 tile1024 flush0:   1.106x
GPU0 tile1024 flush16M: 1.102x

GPU1 tile512  flush0:   1.188x
GPU1 tile512  flush16M: 1.036x
GPU1 tile1024 flush0:   1.129x
GPU1 tile1024 flush16M: 1.118x
```

Same-hotness ablation:

```text
utility_hot_first and utility_tile_grouped have the same tile_order_hit_rate
on this trace: 0.491.

utility_hot_first:
  LRU@8 = 0.557
  timing is near linear or worse in most configs

utility_tile_grouped:
  LRU@8 = 0.833
  median speedup vs utility_hot_first ranges from about 1.04x to 1.14x
```

Same-locality ablation:

```text
B-tile grouped and utility_tile_grouped both preserve LRU@8 ~= 0.833.

B-tile grouped:
  tile_order_hit_rate = 0.119

utility_tile_grouped:
  tile_order_hit_rate = 0.491

Timing is near B-tile grouped while preserving much higher hot-order signal.
```

Interpretation:

```text
The stable result is not "hot-first is faster"; pure hot-first is not enough.
The stable result is that utility should rank B-tile groups, while execution
keeps each B tile contiguous. This preserves cache locality and retains the
MTP/transition utility signal.
```

Runtime descriptor-order action:

```text
module:  src/mtp_expert_prefetch/runtime/descriptor_order.py
script:  scripts/simulate_descriptor_order.py
schema:  ShadowSummaryEvent descriptor_order_* fields
```

The descriptor-order action is explicitly safe:

```text
same descriptor multiset
same true router output
same candidate membership
different descriptor / tile visitation order only
```

New shadow summary fields:

```text
descriptor_order_policy
descriptor_order_build_us
descriptor_tile_multiset_hash
descriptor_order_hash
descriptor_order_metrics
```

Smoke over existing premap descriptors:

```text
input:    outputs/reports/prefetch_shadow_256sample_mtp_extra/descriptors_extra4.jsonl
artifact: outputs/reports/tile_order_cache/descriptor_order_extra4_smoke.md
descriptors: 306,249
```

Result boundary:

```text
This smoke validates runtime action semantics and hash/counter reporting.
It is not a locality claim because the current premap descriptor JSONL is
sample/layer deduplicated. It is not a token/row-level grouped-GEMM tile stream.

The locality/timing claim should remain tied to the tensor-cache tile stream
and the direct/global-fragment timing bench until a row-level runtime descriptor
stream is available.
```

Engineering implication:

```text
Python prototype order_build_us on 306k descriptors is hundreds of ms, so it is
not the intended runtime implementation. The real runtime path needs bucketed
grouping / partial sort / descriptor patching in C++ or device-side code.
The Python action is for shadow validation and counter semantics.
```

Token/row-level tile stream bridge:

```text
module:  src/mtp_expert_prefetch/runtime/tile_stream.py
script:  scripts/export_tile_stream_descriptors.py
inputs:  event-stall tensor cache
outputs: token/row-level TileRequest JSONL
```

This closes the descriptor-order input gap:

```text
tensor cache -> token/row tile stream JSONL
same JSONL -> trace-level tile-order simulator
same JSONL -> direct/global-fragment timing bench
```

512-sample smoke:

```text
input:    outputs/reports/prefetch_shadow_512sample_mtp_extra/event_stall_tensor_cache_512sample.pt
jsonl:    outputs/reports/tile_order_cache/tile_stream_512sample_top8.jsonl
summary:  outputs/reports/tile_order_cache/tile_stream_512sample_top8_summary.md
requests: 163,840
windows:  320
unique B tiles: 256
```

Replay from JSONL matches the tensor-cache export diagnostics:

```text
linear:
  LRU@8 = 0.391
  order_hit = 0.414

B-tile grouped:
  LRU@8 = 0.833
  order_hit = 0.119

utility_hot_first:
  LRU@8 = 0.557
  order_hit = 0.491

utility_tile_grouped:
  LRU@8 = 0.833
  order_hit = 0.491
```

Small GPU bench smoke from the same JSONL:

```text
artifact: outputs/reports/tile_order_cache/tile_stream_512sample_top8_bench_smoke.json
device:   GPU0
policies: linear vs utility_tile_grouped
tile_elems: 256
iters: 5
result: utility_tile_grouped speedup_median_vs_linear ~= 1.005x
```

Boundary:

```text
This is a row-level stream bridge and semantic replay check, not a new
performance claim. The stronger timing evidence remains the prior stability
sweep. The important engineering step is that runtime descriptor_order and
the GPU timing bench can now consume the same row-level tile descriptor format.
```

Descriptor-order shadow summary over token/row streams:

```text
module:  order_tile_request_stream(...)
schema:  ShadowSummaryEvent descriptor_tile_request_count / unique_b_tiles /
         same_multiset / order_changed
script:  scripts/simulate_tile_stream_descriptor_order.py
```

512-sample row-stream shadow smoke:

```text
artifact: outputs/reports/tile_order_cache/tile_stream_descriptor_order_512sample_top8.md
shadow:   outputs/reports/tile_order_cache/tile_stream_descriptor_order_512sample_top8.shadow.jsonl
```

Key rows:

```text
linear:
  build_us median ~= 7.8ms
  LRU@8 = 0.391
  order_hit = 0.414
  same_multiset = true
  order_changed = false

utility_tile_grouped:
  build_us median ~= 82.6ms in Python
  LRU@8 = 0.833
  order_hit = 0.491
  same_multiset = true
  order_changed = true
```

Order-build overhead Pareto:

```text
script:  scripts/summarize_tile_order_overhead_pareto.py
artifact: outputs/reports/tile_order_cache/tile_stream_top8_overhead_pareto_stability.md
```

Current conclusion:

```text
The Python prototype is far too expensive for runtime descriptor ordering:
order_build_us is tens of milliseconds on the 163k-row stream, while measured
kernel savings in the direct/global-fragment bench are tens of microseconds.

This does not invalidate descriptor_order as a runtime action. It fixes the
next implementation requirement: real runtime ordering must use bucketed
group-by-tile / partial sort / precomputed group order in C++ or device-side
code. The Python path is only for shadow semantics and offline analysis.
```

Bucketed descriptor-order builder:

```text
policies:
  utility_tile_grouped_bucket
  utility_tile_grouped_top16
  utility_tile_grouped_top32

microbench:
  microbench/tile_order_cache/descriptor_order_builder_bench.cpp
script:
  scripts/run_descriptor_order_builder_bench.py
```

Python bucket prototype on the 163,840-row stream:

```text
utility_tile_grouped:        ~= 90.6ms
utility_tile_grouped_bucket: ~= 54.7ms
utility_tile_grouped_top16:  ~= 56.6ms
utility_tile_grouped_top32:  ~= 56.7ms
```

This preserves the useful ordering metrics:

```text
utility_tile_grouped_bucket:
  LRU@8 = 0.833
  order_hit = 0.491
  same_multiset = true
```

C++ preallocated bucket builder:

```text
artifact: outputs/reports/tile_order_cache/descriptor_order_builder_cpp_512sample_top8.md

utility_tile_grouped_bucket:
  total build_us median ~= 2.02ms for 163,840 rows / 320 windows
  normalized ~= 6.30us per window
  Python prototype ~= 55ms

utility_tile_grouped_top16/top32:
  total build_us median ~= 2.32ms / 2.36ms
```

Net overhead against the current direct/global-fragment timing bench:

```text
artifact: outputs/reports/tile_order_cache/descriptor_order_builder_cpp_overhead_pareto_smoke.md

utility_tile_grouped_bucket:
  kernel_saved_us ~= 27.5us
  cpp_build_us ~= 2015us
  net_saved_us ~= -1988us
```

Current interpretation:

```text
C++ bucketed grouping proves the algorithmic direction is much better than
Python object sorting, but still not profitable against the current tiny
direct/global-fragment bench envelope.

The per-window cost is now single-digit microseconds, so the remaining question
is whether the real runtime granularity/kernel saved envelope is per large
batch/layer, per window, or can reuse cached permutations. Descriptor_order
should remain shadow/precomputed until a net-positive implementation is shown.
```

Descriptor-order permutation cache replay:

```text
script:   scripts/analyze_descriptor_order_cache_replay.py
artifact: outputs/reports/tile_order_cache/descriptor_order_cache_replay_512sample_top8.md
```

Strict cache keys:

```text
exact_multiset:
  hit_rate = 0.0
  unique_keys = 320 / 320 windows

tile_set:
  hit_rate = 0.0
  unique_keys = 320 / 320 windows
```

Interpretation:

```text
Full permutation cache and same-active-set group-order cache do not repeat on
this 512-sample row stream. They cannot amortize descriptor-order build cost.
```

Heuristic key:

```text
layer_only:
  hit_rate = 0.875
  unique_keys = 40
  reuse_count = 8 per layer
  amortized builder ~= 0.79-0.92us/window before lookup/apply
```

Boundary:

```text
layer_only is not a same-multiset permutation cache. It is only a heuristic
layer-prior group-order cache. It preserves execution correctness because it
can still order the current descriptor multiset, but it may lose the utility
ranking value and must be evaluated as a separate policy.
```

Descriptor-order cache hit-path microbench:

```text
script:   scripts/run_descriptor_order_cache_hit_bench.py
artifact: outputs/reports/tile_order_cache/descriptor_order_cache_hit_bench_512sample_top8.md
```

CPU lookup path:

```text
exact_multiset warm lookup:
  ~= 8.85us over 320 keys, ~= 27.6ns/key

tile_set warm lookup:
  ~= 9.18us over 320 keys, ~= 28.7ns/key

layer_only warm lookup:
  ~= 2.13us over 320 keys, ~= 6.7ns/key
```

Current conclusion:

```text
Lookup cost is small. The blocker is reuse, not lookup. Strict safe cache keys
do not repeat in this trace; only heuristic layer-level reuse repeats.
Next gate is to evaluate layer-prior / cached group-order policies directly
against reuse/order-hit/timing, instead of treating them as exact permutation
caches.
```

Layer-prior tile-group ordering:

```text
core functions:
  src/mtp_expert_prefetch/runtime/tile_order.py

scripts:
  scripts/build_layer_prior_tile_order.py
  scripts/evaluate_layer_prior_tile_order.py

artifacts:
  outputs/reports/tile_order_cache/tile_stream_512sample_top8_calibration.jsonl
  outputs/reports/tile_order_cache/tile_stream_512sample_top8_heldout.jsonl
  outputs/reports/tile_order_cache/layer_prior_frequency_384calib.json
  outputs/reports/tile_order_cache/layer_prior_utility_384calib.json
  outputs/reports/tile_order_cache/layer_prior_weighted_utility_384calib.json
  outputs/reports/tile_order_cache/layer_prior_tile_order_heldout.md
```

Split:

```text
calibration:
  384 examples
  122,880 token-row TileRequest records
  240 windows

heldout:
  128 examples
  40,960 token-row TileRequest records
  80 windows
```

Heldout trace-level result:

```text
linear:
  LRU@8 = 0.4437
  order_hit = 0.4641

B-tile grouped:
  LRU@8 = 0.8439
  order_hit = 0.1234

utility_tile_grouped_bucket:
  LRU@8 = 0.8441
  order_hit = 0.5375

layer_prior_frequency:
  LRU@8 = 0.8442
  order_hit = 0.5766

layer_prior_utility:
  LRU@8 = 0.8442
  order_hit = 0.5234
```

Interpretation:

```text
Exact descriptor permutation caching is not viable on this trace, but a
calibrated per-layer group-order prior is a real policy.

Frequency prior is currently the strongest heldout layer-prior variant:
it preserves B-tile locality and improves hot group order beyond dynamic
utility_tile_grouped on this split.

The policy remains safe: it preserves the current descriptor multiset and only
changes tile-group visitation order. It is not an expert predictor and does
not alter true router membership.
```

Heldout direct/global-fragment timing sweep:

```text
artifact:
  outputs/reports/tile_order_cache/layer_prior_tile_order_heldout_bench_sweep.json

tiny/no-flush envelope:
  tile_elems=256, cache_flush=0
  linear remains fastest on this bench shape.
  Do not claim timing benefit here.

larger tile envelope:
  tile_elems=1024, cache_flush=0
  B-tile grouped speedup ~= 1.16x on both W7900 devices.
  layer_prior_frequency speedup ~= 1.15x on both W7900 devices.
  utility_tile_grouped_bucket speedup ~= 1.14x on both W7900 devices.

cache-pressure envelope:
  tile_elems=1024, cache_flush=16M
  B-tile grouped speedup ~= 1.05-1.11x.
  layer_prior_frequency speedup ~= 1.03-1.07x.
```

Current descriptor-order conclusion:

```text
layer_prior_frequency is the best runtime-feasible descriptor-order candidate
so far: it has no exact multiset-cache dependency, uses a small per-layer prior,
preserves locality, and improves hot group order.

Dynamic utility_tile_grouped remains a diagnostic/upper policy because dynamic
build cost is still too high for the current timing envelope.

Next gate:
  implement a C++/two-level layer-prior builder path and online shadow counters
  for descriptor_order_policy=layer_prior_frequency.
```

C++ two-level layer-prior builder:

```text
code:
  microbench/tile_order_cache/descriptor_order_builder_bench.cpp
  scripts/run_descriptor_order_builder_bench.py

mode:
  layer_prior_plan

representation:
  present/counts/offsets
  filtered group_order from prior_order[layer]
  optional top-H current-utility override
  no full materialized descriptor reorder in the plan mode
```

Heldout builder result:

```text
artifact:
  outputs/reports/tile_order_cache/layer_prior_descriptor_order_builder_heldout.md

utility_tile_grouped_bucket:
  ~= 365.5us total
  ~= 4.57us/window
  LRU@8 = 0.8441
  order_hit = 0.5375

layer_prior_frequency:
  ~= 332.8us total
  ~= 4.16us/window
  LRU@8 = 0.8442
  order_hit = 0.5766

layer_prior_utility:
  ~= 317.9us total
  ~= 3.97us/window
  LRU@8 = 0.8442
  order_hit = 0.5234
```

Materialization control:

```text
artifact:
  outputs/reports/tile_order_cache/layer_prior_descriptor_order_builder_materialized_heldout.md

layer_prior_frequency plan:
  ~= 315.2us total
  ~= 3.94us/window

layer_prior_frequency materialized:
  ~= 347.9us total
  ~= 4.35us/window
```

Interpretation:

```text
The two-level representation is the right runtime shape: materializing a full
reordered descriptor array is measurably slower.

However, the current CPU-side builder is still too expensive for the tiny
direct/global-fragment timing envelope.
```

Overhead Pareto:

```text
artifact:
  outputs/reports/tile_order_cache/layer_prior_tile_order_overhead_pareto_heldout.md

tile_elems=1024, no flush:
  layer_prior_frequency kernel_saved_us ~= 8us per heldout stream
  layer_prior_frequency build_us ~= 333us per heldout stream
  net_saved_us remains negative

tile_elems=1024, cache_flush=16M:
  kernel_saved_us ~= 4-10us depending on device
  build_us remains ~= 333us
  net_saved_us remains negative
```

Current descriptor-order boundary:

```text
layer_prior_frequency is still the best semantic policy for descriptor_order:
it preserves B-tile locality and improves order_hit on heldout.

But it is not yet a per-window CPU critical-path action under the current
direct/global-fragment microbench envelope.

Use it next as:
  online shadow metric/policy,
  precomputed descriptor group order,
  or a candidate for a lower-overhead integrated grouped-kernel path.
```

Descriptor-order online shadow counters:

```text
code:
  src/mtp_expert_prefetch/runtime/shadow_log.py
  src/mtp_expert_prefetch/runtime/online_shadow.py
  src/mtp_expert_prefetch/runtime/shadow_controller.py
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py

new flattened summary fields:
  descriptor_order_prior_id
  descriptor_order_prior_hash
  descriptor_order_lru_at_8
  descriptor_order_lru_at_16
  descriptor_order_hit_rate
  descriptor_reuse_distance_mean
  descriptor_unique_tiles_per_window_mean

aggregate fields:
  descriptor_order_lru_at_8_mean
  descriptor_order_lru_at_16_mean
  descriptor_order_hit_rate_mean
  descriptor_reuse_distance_mean
  descriptor_unique_tiles_per_window_mean
```

Runtime hook boundary:

```text
write_active_runtime_shadow_descriptor_order_summary(...)

This writes descriptor_order counters through the active RuntimeShadowController.
It does not cache router masks for outcome join because descriptor_order is an
order-only action over the current descriptor multiset.
```

Smoke:

```text
script:
  scripts/simulate_tile_stream_descriptor_order.py

artifact:
  outputs/reports/tile_order_cache/layer_prior_descriptor_order_shadow_smoke.jsonl

records:
  linear
  b_tile_grouped
  layer_prior_frequency

layer_prior_frequency shadow fields:
  descriptor_order_prior_hash = 0371...
  descriptor_order_lru_at_8 = 0.8442
  descriptor_order_hit_rate = 0.5766
  descriptor_reuse_distance_mean = 20.5402
```

Current next gate:

```text
Attach a real vLLM/runtime producer that builds current-router token-row tile
requests, calls descriptor_order_policy=layer_prior_frequency, and writes only
the shadow counters. Do not change grouped-GEMM execution order yet.
```

Online vLLM descriptor-order producer:

```text
code:
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py

runtime_shadow options:
  emit_descriptor_order_summaries
  descriptor_order_prior_path
  descriptor_order_prior_id
  descriptor_order_tiles_per_expert
  descriptor_order_cache_sizes
  descriptor_order_top_k
  descriptor_order_top_utility_override

behavior:
  after a true-router top-k call, expand the current layer's token/top-k rows
  into a current-router TileRequest stream;
  apply the calibrated layer_prior_frequency order;
  write a descriptor_order_shadow summary with prior hash, multiset/order hash,
  LRU/order-hit/reuse metrics, and overhead fields.

boundary:
  this is shadow-only;
  it does not alter grouped-GEMM execution order;
  it does not write ready masks;
  it does not participate in action-summary/outcome joining.

fallback:
  missing prior or missing layer order is a no-op, not a runtime failure.
```

Current next gate:

```text
Run an online vLLM shadow-only smoke with the calibrated layer-prior artifact,
then compare online descriptor_order LRU/order-hit/reuse metrics with the 512
heldout tensor-cache replay before enabling any real descriptor visitation
order changes.
```

Online vLLM descriptor-order smoke results:

```text
code/config changes:
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py
    - vLLM trace now supports trace.start_sample.
    - descriptor-order TileRequest streams can use
      descriptor_order_token_window_size=64, matching the tensor-cache
      heldout convention of 64 token examples x top8 = 512 tile requests.
  scripts/replay_vllm_descriptor_order_shadow.py
    - rebuilds token/row TileRequest streams from sample_*.pt vLLM traces;
    - applies the same layer-prior/order metrics as heldout replay;
    - can run an internal vLLM calibration/heldout split.

real vLLM shadow-only runs:
  smoke8:
    configs/trace/router_mtp_trace_aya_dataset_gptq_vllm_descriptor_order_shadow_smoke8.yaml
    data/traces/aya_dataset_smoke_gptq_vllm_descriptor_order_shadow_smoke8/

  smoke32:
    configs/trace/router_mtp_trace_aya_dataset_gptq_vllm_descriptor_order_shadow_smoke32.yaml
    data/traces/aya_dataset_smoke_gptq_vllm_descriptor_order_shadow_smoke32/

  heldout with vLLM-calibrated prior:
    configs/trace/router_mtp_trace_aya_dataset_gptq_vllm_descriptor_order_shadow_smoke32_heldout_vllm_prior.yaml
    data/traces/aya_dataset_smoke_gptq_vllm_descriptor_order_shadow_smoke32_heldout_vllm_prior/

  smoke64:
    configs/trace/router_mtp_trace_aya_dataset_gptq_vllm_descriptor_order_shadow_smoke64.yaml
    data/traces/aya_dataset_smoke_gptq_vllm_descriptor_order_shadow_smoke64/
```

Key reports:

```text
outputs/reports/tile_order_cache/vllm_descriptor_order_shadow_smoke8_replay.md
outputs/reports/tile_order_cache/vllm_descriptor_order_shadow_smoke32_replay.md
outputs/reports/tile_order_cache/vllm_descriptor_order_shadow_smoke32_heldout_vllm_prior_replay.md
outputs/reports/tile_order_cache/vllm_smoke32_layer_prior_frequency_24calib.json
outputs/reports/tile_order_cache/vllm_descriptor_order_shadow_smoke64_replay.md
outputs/reports/tile_order_cache/vllm_smoke64_layer_prior_frequency_48calib.json
```

Online producer validation:

```text
smoke32, old tensor-cache prior:
  descriptor summaries = 1280
  online mean LRU@8 / LRU@16 = 0.9358 / 0.9374
  online mean order_hit = 0.3505
  online mean reuse_mean = 0.4423
  decision_us mean = 2724.9
  candidate_construction_us mean = 1564.5
  descriptor_order_build_us mean = 237.0

heldout-only, vLLM-calibrated prior:
  descriptor summaries = 320
  online mean LRU@8 / LRU@16 = 0.9454 / 0.9455
  online mean order_hit = 0.9012
  online mean reuse_mean = 0.4569
  decision_us mean = 3027.5
  candidate_construction_us mean = 1767.4
  descriptor_order_build_us mean = 242.4
```

512-window replay validation:

```text
smoke32 with old tensor-cache layer_prior_frequency:
  requests = 1,002,880
  windows = 1,960

  linear:
    LRU@8 / LRU@16 = 0.7143 / 0.9397
    reuse_mean = 8.9340
    order_hit = 0.7536

  utility_tile_grouped_bucket:
    LRU@8 / LRU@16 = 0.9434 / 0.9457
    reuse_mean = 2.3124
    order_hit = 0.5763

  old layer_prior_frequency:
    LRU@8 / LRU@16 = 0.9433 / 0.9441
    reuse_mean = 2.3945
    order_hit = 0.3037

This means the tensor-cache calibrated prior does not transfer cleanly to the
current vLLM/GPTQ router trace. The hook is valid, but the prior artifact is
backend/trace dependent.

vLLM internal 24/8 calibration split:
  vLLM-calibrated layer_prior_frequency on heldout samples 24-31:
    LRU@8 / LRU@16 = 0.9494 / 0.9526
    reuse_mean = 2.2661
    order_hit = 0.9016

  dynamic utility_tile_grouped_bucket on the same heldout:
    LRU@8 / LRU@16 = 0.9495 / 0.9531
    reuse_mean = 2.1984
    order_hit = 0.6350

smoke64 scale check:
  requests = 1,844,160
  windows = 3,640

  old tensor-cache layer_prior_frequency:
    LRU@8 / LRU@16 = 0.9404 / 0.9413
    reuse_mean = 2.5393
    order_hit = 0.2977

  utility_tile_grouped_bucket:
    LRU@8 / LRU@16 = 0.9405 / 0.9426
    reuse_mean = 2.4463
    order_hit = 0.5608

  vLLM internal 48/16 calibration split:
    vLLM-calibrated layer_prior_frequency on heldout samples 48-63:
      LRU@8 / LRU@16 = 0.9368 / 0.9378
      reuse_mean = 3.2646
      order_hit = 0.8689

    utility_tile_grouped_bucket on the same heldout:
      LRU@8 / LRU@16 = 0.9368 / 0.9381
      reuse_mean = 3.1584
      order_hit = 0.5207
```

Conclusion:

```text
The real vLLM shadow-only descriptor_order producer is wired and observable.

The online counters now use token-window semantics compatible with heldout
tile streams, and overhead fields are populated.

A layer-prior descriptor_order policy must be calibrated on the same router
trace/backend family. Reusing the tensor-cache prior on GPTQ/vLLM preserves
locality but loses group-order hit. Recalibrating on vLLM traces restores strong
heldout order_hit while keeping the same safety boundary:
same current true-router multiset, order-only changes, no ready-mask effects.

Next gate:
  lower descriptor_order overhead via a two-level C++/runtime builder
  or keep descriptor_order as a shadow/precomputed action until the order-build
  path is below the measured kernel saved envelope.
```

C++ builder overhead on real vLLM streams:

```text
scripts:
  scripts/replay_vllm_descriptor_order_shadow.py
    now supports --output-jsonl for exporting the vLLM TileRequest stream.

  scripts/run_descriptor_order_builder_bench.py
    consumes the same vLLM JSONL stream and measures C++ builder cost.

artifacts:
  outputs/reports/tile_order_cache/vllm_smoke64_tile_stream_top8.jsonl
  outputs/reports/tile_order_cache/vllm_smoke64_descriptor_order_builder_bench.md
  outputs/reports/tile_order_cache/vllm_smoke32_heldout_tile_stream_top8.jsonl
  outputs/reports/tile_order_cache/vllm_smoke32_heldout_descriptor_order_builder_bench.md
```

Results:

```text
smoke64 full stream:
  requests = 1,844,160
  layer_prior_frequency plan:
    cpp_build_us_median = 8,821.9 total
    cpp_us/window = 2.42
    python_build_us ~= 468,474
    LRU@8 / LRU@16 = 0.9404 / 0.9423
    order_hit = 0.8854

  layer_prior_frequency materialized:
    cpp_build_us_median = 10,366.6 total
    cpp_us/window = 2.85

smoke32 heldout-only stream:
  requests = 283,520
  windows = 560
  layer_prior_frequency plan:
    cpp_build_us_median = 1,233.1 total
    cpp_us/window = 2.20
    python_build_us ~= 51,605
    LRU@8 / LRU@16 = 0.9494 / 0.9526
    order_hit = 0.9016

  layer_prior_frequency materialized:
    cpp_build_us_median = 1,470.8 total
    cpp_us/window = 2.63
```

Updated overhead conclusion:

```text
The Python online descriptor_order producer is still too expensive for the
decode critical path.

However, the C++ two-level layer_prior_plan is now in the low-microsecond
per-window range on real vLLM TileRequest streams. This revives descriptor_order
as a runtime-feasible action if the grouped-kernel consumer can use a
two-level group-order plan directly, avoiding full Python materialization.

Next implementation gate:
  replace the Python shadow producer's object-level TileRequest ordering with
  a lower-overhead plan builder or expose a runtime C++ builder path for
  descriptor_order summaries.
```

Follow-up overhead reduction:

```text
runtime change:
  common online path now uses tensor/rank-map layer_prior_plan when:
    tiles_per_expert = 1
    top_utility_override = 0

  runtime_shadow option:
    descriptor_order_metrics_mode: compact

compact mode:
  keeps LRU@K, order_hit, unique tile stats, run length, hashes, request count
  skips full reuse-distance distribution

TRY/AWQ 1-sample online smoke after compact mode:
  summaries = 40
  outcomes = 5,080

  LRU@8 mean = 0.8593
  LRU@16 mean = 0.8593
  order_hit mean = 0.6203
  reuse_distance = skipped in compact mode

  candidate_construction_us mean = 4.16
  descriptor_order_build_us mean = 495.38
  decision_us mean = 1,452.38
  counter_update_us mean = 952.84

previous full-metric online smoke:
  descriptor_order_build_us mean = 881.75
  decision_us mean = 3,402.53
  counter_update_us mean = 2,516.30

interpretation:
  tensor/rank-map planning reduces the plan-build cost, and compact metrics
  remove a large part of online shadow overhead while preserving the primary
  locality/order observability. Full reuse-distance accounting should remain
  an offline replay diagnostic or sampled debug mode.
```

AWQ compact descriptor_order scale-up:

```text
configs:
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_smoke8.yaml
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_smoke32.yaml

environment:
  TRY conda env
  HIP_VISIBLE_DEVICES=0 for smoke8
  HIP_VISIBLE_DEVICES=1 for smoke32

outputs:
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_smoke8/runtime_shadow.jsonl
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_smoke32/runtime_shadow.jsonl
```

Correctness / scale:

```text
smoke8:
  samples = 8
  token count range = 35..127
  outcomes = 29,760 = sum(num_tokens) * 40
  descriptor_order summaries = 320 = 8 * 40
  runtime_shadow size = 22MB

smoke32:
  samples = 32
  token count range = 35..127
  outcomes = 125,360 = sum(num_tokens) * 40
  descriptor_order summaries = 1,280 = 32 * 40
  runtime_shadow size = 90MB
```

Compact overhead distribution:

```text
smoke8:
  candidate_construction_us:
    mean 4.72 / p50 4.39 / p90 5.29 / p95 5.85 / p99 8.16 / max 21.03
  descriptor_order_build_us:
    mean 478.73 / p50 478.08 / p90 564.33 / p95 585.59 / p99 630.44 / max 744.96
  decision_us:
    mean 1248.67 / p50 1360.25 / p90 1575.90 / p95 1626.91 / p99 1710.56 / max 2190.96
  counter_update_us:
    mean 765.22 / p50 833.06 / p90 1011.52 / p95 1037.89 / p99 1100.92 / max 1441.13

smoke32:
  candidate_construction_us:
    mean 4.13 / p50 4.12 / p90 4.46 / p95 4.60 / p99 5.18 / max 19.41
  descriptor_order_build_us:
    mean 452.57 / p50 448.48 / p90 527.73 / p95 558.32 / p99 616.71 / max 893.86
  decision_us:
    mean 1210.03 / p50 1253.86 / p90 1485.60 / p95 1535.35 / p99 1687.79 / max 2287.63
  counter_update_us:
    mean 753.33 / p50 825.15 / p90 970.96 / p95 992.39 / p99 1091.56 / max 1411.27
```

Compact locality/order distribution:

```text
smoke8:
  LRU@8 mean 0.8153 / p50 0.8258 / p95 0.8937 / p99 0.9120
  LRU@16 mean 0.8153 / p50 0.8258 / p95 0.8937 / p99 0.9120
  order_hit mean 0.4670 / p50 0.5000 / p95 0.7500 / p99 0.8125
  unique_tiles_total mean 97.03 / p50 93.5 / p95 156.0 / p99 185.0

smoke32:
  LRU@8 mean 0.8143 / p50 0.8235 / p95 0.8760 / p99 0.8978
  LRU@16 mean 0.8143 / p50 0.8237 / p95 0.8760 / p99 0.8978
  order_hit mean 0.4137 / p50 0.4375 / p95 0.7500 / p99 0.8125
  unique_tiles_total mean 102.83 / p50 98.0 / p95 161.0 / p99 191.4
```

Scale-up conclusion:

```text
AWQ online compact descriptor_order shadow is stable at 8/32 sample scale.
Summary/outcome counts match manifest token counts exactly, and same_multiset /
order_changed are true for every descriptor_order summary.

Overhead is stable but still too high for a synchronous critical-path runtime
action: p95 decision_us is ~1.54ms and p99 is ~1.69ms on smoke32. This is
acceptable for online shadow observability, not yet for production descriptor
visitation changes.

Next gate:
  compare no-shadow vs compact-shadow end-to-end wall time/TPOT, then add an
  even cheaper metrics_mode=none for long online runs where only hashes/counts
  and build_us are needed.
```

AWQ no-shadow vs compact-shadow end-to-end comparison:

```text
environment:
  conda env: TRY
  gpu: HIP_VISIBLE_DEVICES=1
  model: qwen3_6_35b_a3b_awq_4bit
  recorder: enabled in both no-shadow and compact-shadow
  max_tokens: 1

configs added:
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_no_shadow_smoke8.yaml
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_no_shadow_smoke32.yaml

instrumentation added:
  output_dir/performance_summary.json now records:
    llm_init_wall_seconds
    generate_wall_seconds
    trace_write_wall_seconds
    total_trace_wall_seconds
    generate_seconds_per_requested_output_token
    end_to_end_seconds_per_requested_output_token
```

Raw external wall-time:

```text
8 samples:
  no_shadow       74.08s
  compact_shadow  91.06s

32 samples repeat1:
  no_shadow       66.04s
  compact_shadow  72.97s

32 samples repeat2, reverse order:
  compact_shadow  69.89s
  no_shadow       80.62s

32 samples repeat3, with performance_summary:
  no_shadow       63.99s
  compact_shadow  69.88s
```

Interpretation:

```text
Raw external wall time is too noisy for small AWQ runs because vLLM engine
construction and AWQ safetensors loading dominate the run (~43-56s). Repeat2
even reverses the raw ordering, so raw wall-time alone is not a reliable
shadow overhead estimate.
```

Instrumented 32-sample path-level timing:

```text
no_shadow:
  total_trace_wall_seconds = 60.83
  llm_init_wall_seconds    = 48.98
  generate_wall_seconds    = 3.76
  trace_write_wall_seconds = 0.93
  generate_s/output_token  = 0.118

compact_shadow:
  total_trace_wall_seconds = 66.72
  llm_init_wall_seconds    = 49.02
  generate_wall_seconds    = 9.56
  trace_write_wall_seconds = 0.90
  generate_s/output_token  = 0.299

delta:
  total_trace_wall_seconds = +5.90s
  generate_wall_seconds    = +5.80s
  generate_s/output_token  = +0.181s
  llm_init_wall_seconds    = +0.03s
```

Compact-shadow internal overhead, current 32-sample run:

```text
descriptor summaries = 1,280
outcomes             = 125,360
same_multiset        = 1,280 / 1,280
order_changed        = 1,280 / 1,280

candidate_construction_us:
  mean = 3.88, p95 = 4.32, p99 = 4.70

descriptor_order_build_us:
  mean = 413.94, p95 = 505.27, p99 = 558.97

decision_us:
  mean = 1,113.30, p95 = 1,428.99, p99 = 1,536.26

counter_update_us:
  mean = 695.49, p95 = 943.77, p99 = 989.08

LRU@8 mean      = 0.8143
LRU@16 mean     = 0.8143
order_hit mean  = 0.4137
```

Current conclusion:

```text
AWQ compact descriptor-order shadow has stable observability metrics and valid
same-multiset/order-changed semantics at 32 samples.

However, compact shadow still adds measurable generate-path overhead in Python:
~5.8s over 32 samples, or ~181ms per generated token in this tracing setup.
The cost is dominated by Python descriptor-order metric/counter work, not model
loading and not candidate construction.

Therefore compact mode remains suitable for diagnostic online shadow, but not
for a synchronous production critical path. The next optimization target is a
metrics_mode=none / minimal scalar mode, then a C++/two-level counter path if
we need lower-overhead long online runs.
```

Descriptor-order `metrics_mode=none`:

```text
implementation:
  src/mtp_expert_prefetch/runtime/descriptor_order.py
    supports metrics_mode=none in _evaluate_ordered_tile_id_windows(...)

semantics:
  keeps:
    descriptor_count
    tile_multiset_hash
    order_hash
    order_build_us
    request_count
    window_count
    unique_tiles_total

  skips heavy metrics:
    LRU@K
    tile_order_hit_rate
    reuse_distance
    consecutive run stats
    first_tiles payload

configs:
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_smoke8.yaml
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_smoke32.yaml
```

AWQ none-mode smoke8:

```text
command:
  HIP_VISIBLE_DEVICES=1 VLLM_ENABLE_V1_MULTIPROCESSING=0 \
    conda run -n TRY python scripts/trace_router_mtp_vllm.py \
    configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_smoke8.yaml

output:
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_none_smoke8/runtime_shadow.jsonl
  outputs/reports/awq_shadow_overhead/metrics_mode_none_smoke8.md

runtime_shadow rows = 30,080
outcomes            = 29,760
descriptor summaries = 320
same_multiset       = 320 / 320
order_changed       = 320 / 320
metrics_mode        = none

none-mode metrics:
  LRU@8 emitted       = 0 rows
  order_hit emitted   = 0 rows
  unique_b_tiles mean = 97.03

overhead comparison against compact smoke8:
  compact decision_us p50/p95/p99 = 1216.5 / 1516.9 / 1647.0
  none    decision_us p50/p95/p99 =  743.0 /  917.9 /  993.5

  compact counter_update_us p50/p95/p99 = 752.7 / 983.3 / 1060.8
  none    counter_update_us p50/p95/p99 = 304.6 / 423.2 /  431.5
```

Conclusion:

```text
metrics_mode=none behaves as intended: it preserves descriptor-order audit
semantics via hashes/counts/build_us while removing LRU/order-hit heavy
observability.

This reduces Python shadow overhead substantially:
  decision p50 drops by ~39%
  counter_update p50 drops by ~60%

None-mode is now the preferred long-run online shadow setting when locality
metrics are not needed on every sample. Compact remains the diagnostic mode for
periodic LRU/order-hit validation.
```

AWQ none-mode smoke32:

```text
output:
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_none_smoke32/runtime_shadow.jsonl
  outputs/reports/awq_shadow_overhead/metrics_mode_none_smoke32.md

runtime_shadow rows = 126,640
outcomes            = 125,360
descriptor summaries = 1,280
same_multiset       = 1,280 / 1,280
order_changed       = 1,280 / 1,280
metrics_mode        = none
```

32-sample path-level timing:

```text
no_shadow:
  total_trace_wall_seconds = 60.83
  llm_init_wall_seconds    = 48.98
  generate_wall_seconds    = 3.76
  generate_s/output_token  = 0.118

compact_shadow:
  total_trace_wall_seconds = 66.72
  llm_init_wall_seconds    = 49.02
  generate_wall_seconds    = 9.56
  generate_s/output_token  = 0.299

none_shadow:
  total_trace_wall_seconds = 65.05
  llm_init_wall_seconds    = 48.54
  generate_wall_seconds    = 8.48
  generate_s/output_token  = 0.265

deltas vs no_shadow:
  compact generate +5.80s, total +5.90s
  none    generate +4.72s, total +4.22s
```

32-sample descriptor-order overhead:

```text
compact:
  decision_us p50/p95/p99        = 1203.3 / 1429.0 / 1536.3
  counter_update_us p50/p95/p99  =  800.7 /  943.8 /  989.1
  descriptor_build_us p50/p95/p99 = 412.1 / 505.3 / 559.0
  LRU@8/order_hit rows           = 1280 / 1280

none:
  decision_us p50/p95/p99        =  712.2 /  847.8 /  928.3
  counter_update_us p50/p95/p99  =  315.5 /  355.8 /  394.4
  descriptor_build_us p50/p95/p99 = 405.6 / 494.9 / 549.5
  LRU@8/order_hit rows           = 0 / 0
```

Interpretation:

```text
metrics_mode=none scales cleanly from 8 to 32 samples: summary/outcome counts
remain aligned and p99 overhead does not worsen.

None mode reduces descriptor-order shadow CPU overhead versus compact:
  decision_us p50 drops from ~1203us to ~712us
  counter_update_us p50 drops from ~801us to ~316us

However, no-shadow vs none-shadow path-level timing still shows a measurable
generate-path cost (+4.72s over 32 samples). That remaining cost is mostly the
synchronous summary/controller/logging path, not LRU/order-hit metric
computation and not model loading.

Next optimization target:
  async/batched logger path or flat scalar buffer for none-mode summaries.
```

Runtime shadow summary/outcome attribution:

```text
implementation:
  RuntimeShadowController now supports:
    emit_summaries: bool = true
    emit_outcomes: bool = true

  This keeps default behavior unchanged while allowing controlled attribution:
    outcome_only  = emit_summaries=false, emit_outcomes=true
    summary_only  = emit_summaries=true,  emit_outcomes=false
    both          = emit_summaries=true,  emit_outcomes=true

configs:
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_shadow_outcome_only_smoke32.yaml
  configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_summary_only_smoke32.yaml

tests:
  RuntimeShadowController suppress-summary and suppress-outcome behavior is
  covered in tests/test_runtime_online_shadow.py.
```

AWQ 32-sample attribution:

```text
report:
  outputs/reports/awq_shadow_overhead/summary_outcome_attribution32.md

path-level generate time:
  no_shadow     = 3.76s
  outcome_only  = 7.50s  (+3.74s)
  summary_only  = 6.03s  (+2.27s)
  none_both     = 8.48s  (+4.72s)
  compact_both  = 9.56s  (+5.80s)

rows written:
  outcome_only:
    outcomes = 125,360
    summaries = 0

  summary_only:
    outcomes = 0
    descriptor summaries = 1,280

  none_both:
    outcomes = 125,360
    descriptor summaries = 1,280
```

Descriptor summary overhead, none mode:

```text
summary_only:
  decision_us p50/p95/p99 = 702.5 / 833.9 / 872.5
  counter_update_us p50/p95/p99 = 315.1 / 353.5 / 376.7
  descriptor_build_us p50/p95/p99 = 401.0 / 485.0 / 522.7

none_both:
  decision_us p50/p95/p99 = 712.2 / 847.8 / 928.3
  counter_update_us p50/p95/p99 = 315.5 / 355.8 / 394.4
  descriptor_build_us p50/p95/p99 = 405.6 / 494.9 / 549.5
```

Interpretation:

```text
The remaining none-shadow overhead is split across two synchronous Python paths:

1. outcome logging/controller path:
   outcome_only writes 125k outcome rows and accounts for most of the
   no-shadow gap (+3.74s generate).

2. descriptor summary path:
   summary_only writes only 1,280 descriptor summaries but still costs +2.27s,
   driven by Python summary construction, hash/order build, JSONL write, and
   controller/logger overhead.

none_both remains expensive because it still emits both outcome rows and
descriptor summaries synchronously.
```

Next gate:

```text
P0:
  add outcome_logging_mode = full | aggregate | off
  and make aggregate/off the default for long-run descriptor-order audit.

P0:
  add a batched/flat scalar writer for descriptor summaries:
    fixed schema rows
    no nested descriptor_order_metrics payload in none mode
    batch flush instead of flush_every=1 for long runs

P1:
  async writer / ring buffer once flat schema proves beneficial.
```

Runtime online descriptor-order fast producer:

```text
implementation:
  src/mtp_expert_prefetch/runtime/descriptor_order.py
    adds build_layer_prior_plan_report_from_router_topk(...)
    compact/two-level layer_prior_plan-style report builder
    avoids Python object-level TileRequest materialization in online shadow

  src/mtp_expert_prefetch/tracing/vllm_router_trace.py
    descriptor_order summary producer now calls the compact plan builder
    candidate_construction_us measures only tensor detach/copy overhead

  tests:
    tests/test_runtime_layer_prior_order.py verifies compact plan report hashes
    and metrics match the original TileRequest stream implementation.
```

AWQ/vLLM descriptor_order smoke environment:

```text
working env:
  conda env: TRY
  python: /home/husrcf/anaconda3/envs/TRY/bin/python
  torch: 2.11.0+rocm7.2
  transformers: 5.6.2
  vllm: 0.19.2rc1.dev213+g9558f4390

failed env notes:
  base is contaminated by in-progress flash-attn/kernel development.
  MCP imports vLLM after fixing libzstd search path, but current vLLM build
  rejects the original qwen3_5_moe AWQ architecture.
  AIAA has no vLLM installed.

command:
  HIP_VISIBLE_DEVICES=1 VLLM_ENABLE_V1_MULTIPROCESSING=0 \
    conda run -n TRY python scripts/trace_router_mtp_vllm.py \
    configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_smoke.yaml

outputs:
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_smoke/manifest.jsonl
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_smoke/runtime_shadow.jsonl
```

Online smoke result, 1 sample:

```text
manifest rows = 1
runtime_shadow rows = 5,120
  outcomes = 5,080
  descriptor_order summaries = 40

descriptor_order metrics across 40 layers:
  LRU@8 mean = 0.8593
  LRU@16 mean = 0.8593
  order_hit mean = 0.6203
  reuse_distance mean = 4.1123
  windows/layer = 2
  tile requests/layer = 1,016

fast-producer overhead:
  candidate_construction_us mean = 4.47
  descriptor_order_build_us mean = 881.75
  decision_us mean = 3,402.53

interpretation:
  object-level TileRequest construction is removed from the online producer.
  candidate construction is now low microseconds, but descriptor_order metric
  computation remains the dominant online shadow cost. This is acceptable for
  shadow validation; a real runtime action should use compact counters or the
  C++ two-level plan builder path rather than full Python metric evaluation.
```

Runtime shadow outcome logging modes:

```text
implementation:
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py
    adds shadow_outcome_logging_mode = full / aggregate / off
    aggregate writes one outcome_aggregate record per sample/layer router call
    off skips per-token outcome event construction entirely

  src/mtp_expert_prefetch/runtime/shadow_log.py
    adds ShadowOutcomeAggregateEvent and aggregate_shadow_events counters

  configs:
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_outcome_aggregate_smoke32.yaml
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_none_outcome_off_smoke32.yaml
```

AWQ 32-sample result:

```text
mode                         generate_s  TPOT_s   rows     summary  outcome  aggregate
no_shadow                    3.762       0.1176   0        0        0        0
none + full outcomes         8.478       0.2649   126640   1280     125360   0
none + aggregate outcomes    4.855       0.1517   2560     1280     0        1280
none + outcomes off          4.722       0.1476   1280     1280     0        0
```

Interpretation:

```text
per-token full outcome JSONL is the main remaining shadow overhead.
aggregate reduces rows by ~49x vs full-outcome none mode and cuts generate
overhead from +4.72s to +1.09s over no-shadow.

off is the lower bound for descriptor-order audit-only shadow: it keeps only
summary/hash/count/build_us rows and cuts generate overhead to +0.96s.

Descriptor summary internal overhead is almost unchanged across outcome modes,
so the next bottleneck is the descriptor summary path itself, not LRU/order-hit
or per-token outcome logging.
```

Descriptor-order count-only summary mode:

```text
implementation:
  src/mtp_expert_prefetch/runtime/descriptor_order.py
    adds descriptor_order_metrics_mode=count_only
    skips layer-prior ordering, tile_multiset_hash, and order_hash
    keeps request_count/window_count/unique_tiles_total/prior metadata only

  configs:
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_outcome_aggregate_smoke32.yaml
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_outcome_off_smoke32.yaml

  pyproject.toml:
    pytest default collection is restricted to tests/
    third_party/GPTQModel is no longer collected by plain pytest -q
```

AWQ 32-sample count-only result:

```text
mode                         generate_s  TPOT_s   rows   decision_p50  build_p50  counter_p50
no_shadow                    3.762       0.1176   0      -             -          -
none + aggregate outcomes    4.855       0.1517   2560   695.7us       390.9us    315.0us
none + outcomes off          4.722       0.1476   1280   701.0us       398.0us    318.1us
count_only + aggregate       4.065       0.1270   2560   74.4us        56.9us     14.2us
count_only + off             3.875       0.1211   1280   82.3us        67.7us     12.9us
```

Interpretation:

```text
count_only confirms that hash/order construction dominated the remaining
descriptor summary cost.

aggregate audit overhead drops from ~29% over no-shadow to ~8%:
  4.065 / 3.762 - 1 = 8.1%

off + count_only is a near-lower-bound audit path:
  3.875 / 3.762 - 1 = 3.0%

Next bottleneck is now JSONL/controller overhead, so the next gate is
jsonl_batched or flat/batched writer rather than further metric pruning.
```

Runtime shadow JSONL batched writer:

```text
implementation:
  src/mtp_expert_prefetch/runtime/online_shadow.py
    adds writer_mode = sync_jsonl / jsonl_batched
    jsonl_batched stores event objects in memory and serializes/writes them
    during flush/close instead of per row in the generate path

  configs:
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_outcome_aggregate_batched_smoke32.yaml
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_outcome_off_batched_smoke32.yaml
```

AWQ 32-sample writer result:

```text
mode                         writer         generate_s  TPOT_s   rows
no_shadow                    -              3.762       0.1176   0
count_only + aggregate       sync_jsonl     4.065       0.1270   2560
count_only + aggregate       jsonl_batched  4.021       0.1256   2560
count_only + off             sync_jsonl     3.875       0.1211   1280
count_only + off             jsonl_batched  3.939       0.1231   1280
```

Interpretation:

```text
jsonl_batched is replay-correct and slightly helps the aggregate audit path:
  aggregate overhead drops from ~8.1% to ~6.9% over no-shadow.

It does not improve the off path in this 32-sample run, so per-row file flush
is no longer the main bottleneck after count_only. Remaining overhead is likely
dominated by recorder/controller event construction and tensor CPU copy/detach.

Default recommendation:
  count_only + aggregate + jsonl_batched for long-run audit
  count_only + off + sync_jsonl as the descriptor-only lower-bound check
```

Runtime shadow minimal descriptor-summary events:

```text
implementation:
  src/mtp_expert_prefetch/runtime/shadow_log.py
    adds ShadowDescriptorSummaryMinEvent with a fixed scalar schema
    keeps descriptor policy/prior id/hash, request/window/unique-tile counts,
    and timing scalars only

  src/mtp_expert_prefetch/runtime/online_shadow.py
  src/mtp_expert_prefetch/runtime/shadow_controller.py
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py
    add descriptor_order_event_mode = summary / minimal
    minimal writes descriptor_summary_min records instead of full summary rows

  configs:
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_minimal_aggregate_batched_smoke32.yaml
    router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_minimal_off_batched_smoke32.yaml
```

AWQ 32-sample minimal-event result:

```text
mode                         generate_s  TPOT_s   rows   summary  min   aggregate
no_shadow                    3.762       0.1176   0      0        0     0
count_only + aggregate batch 4.021       0.1256   2560   1280     0     1280
count_only + off batch       3.939       0.1231   1280   1280     0     0
minimal + aggregate batch    3.866       0.1208   2560   0        1280  1280
minimal + off batch          3.797       0.1187   1280   0        1280  0
```

Interpretation:

```text
minimal descriptor-summary events move the hot path from full policy summary
objects to fixed scalar telemetry records.

aggregate audit overhead drops to ~2.8% over no-shadow:
  3.866 / 3.762 - 1 = 2.8%

descriptor-only lower-bound overhead drops to ~0.9% over no-shadow:
  3.797 / 3.762 - 1 = 0.9%

This confirms the next efficient long-run audit path is:
  descriptor_order_metrics_mode=count_only
  descriptor_order_event_mode=minimal
  outcome_logging_mode=aggregate
  writer_mode=jsonl_batched

Descriptor min events are intentionally audit-minimal:
they do not carry same_multiset/order_hash/LRU/order_hit fields. Periodic
none/compact runs remain necessary for semantic and locality diagnostics.
```

Review fix:

```text
aggregate_shadow_events now separates full descriptor summaries from
descriptor_summary_min events.

Build/count/timing means use all descriptor summary events, but LRU/order_hit
and reuse metrics are averaged only over events that actually carry those
fields. This prevents mixed full+minimal logs from diluting diagnostic metrics.
```

Runtime shadow long-run audit:

```text
configs:
  router_mtp_trace_aya_dataset_awq_vllm_no_shadow_128sample.yaml
  router_mtp_trace_aya_dataset_awq_vllm_no_shadow_512sample.yaml
  router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_minimal_aggregate_batched_128sample.yaml
  router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_shadow_count_only_minimal_aggregate_batched_512sample.yaml

report:
  outputs/reports/runtime_shadow_longrun_audit.md
```

AWQ long-run result:

```text
mode                 samples  generate_s  TPOT_s   overhead  rows
no_shadow            32       3.762       0.1176   -         0
minimal+aggregate    32       3.866       0.1208   +2.78%    2,560
no_shadow            128      13.560      0.1059   -         0
minimal+aggregate    128      14.597      0.1140   +7.65%    10,240
no_shadow            512      54.507      0.1065   -         0
minimal+aggregate    512      57.878      0.1130   +6.19%    40,960
```

Online scalar stability:

```text
samples  descriptor_build_us_mean  decision_us_mean  unique_tiles_mean
32       50.637                    66.722            102.830
128      51.060                    67.156             99.499
512      50.279                    66.358             98.860
```

Offline replay consistency:

```text
128 layer_prior_frequency:
  LRU@8 0.821650, LRU@16 0.821655, reuse_mean 21.5797, order_hit 0.413485

512 layer_prior_frequency:
  LRU@8 0.822214, LRU@16 0.822215, reuse_mean 21.4121, order_hit 0.440311
```

Interpretation:

```text
minimal+aggregate scales linearly in row count and stays single-digit overhead
at 128/512 samples. The 512-sample run is lower overhead than 128, so there is
no evidence of scale-driven overhead growth in this envelope.

Offline replay confirms the layer-prior descriptor-order structure remains
stable: it preserves B-tile locality at B-grouped levels while keeping order_hit
far above plain B-tile grouping.
```

Descriptor consumer micro-runtime MVP:

```text
implementation:
  scripts/run_descriptor_consumer_micro_runtime.py

input:
  online AWQ vLLM trace directory
  layer_prior_frequency prior

semantics:
  rebuild current-router token/row TileRequest stream
  keep the same descriptor/tile multiset
  compare no_order vs layer_prior_frequency
  feed both orders into the same HIP tile consumer
  report checksum deltas, LRU/order_hit, and wall-time

reports:
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w512_sweep.json
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w512_sweep_gpu1.json
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_summary.md
```

AWQ 128 trace, first 512 complete windows:

```text
selected requests: 261,808
unique B tiles: 256
no_order:
  LRU@8 0.172321, order_hit 0.222656
layer_prior_frequency:
  LRU@8 0.710735, order_hit 0.382324
checksum delta vs no_order: 0 for all measured rows
```

Execution-facing HIP consumer result:

```text
GPU0 speedup layer_prior vs no_order:
  tile_elems 256:  0.992x / 1.000x with 16M flush
  tile_elems 512:  1.092x / 1.037x with 16M flush
  tile_elems 1024: 1.096x / 1.081x with 16M flush
  tile_elems 2048: 1.065x / 1.056x with 16M flush

GPU1 speedup layer_prior vs no_order:
  tile_elems 256:  0.972x / 1.012x with 16M flush
  tile_elems 512:  1.143x / 1.053x with 16M flush
  tile_elems 1024: 1.090x / 1.093x with 16M flush
  tile_elems 2048: 1.069x / 1.070x with 16M flush
```

Interpretation:

```text
The descriptor-order execution MVP passes the same-multiset consumer gate.
Layer-prior ordering improves the same HIP consumer for tile_elems >= 512 on
both GPUs, while 256-element tiles are too small/noisy and should remain gated
or treated as no-op.

This is not yet a vLLM kernel patch. It is the bridge result showing that the
online trace descriptor-order signal can translate into execution-side timing
under a controlled descriptor consumer.
```

Descriptor consumer stability + net-overhead gate:

```text
implementation:
  scripts/run_descriptor_consumer_micro_runtime.py

new accounting:
  host Python order_build_us
  order_export_us
  C++ layer_prior_plan build_us
  C++ layer_prior_materialized build_us
  consumer_saved_us
  net_saved_us after Python/C++ build

reports:
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w512_stability_r20.json
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w1024_stability_r10.json
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_all_smoke_r3.json
```

AWQ 128 trace stability:

```text
512 windows / 261,808 requests / repeat=20:
  layer_prior raw consumer speedup min/mean/max:
    1.031x / 1.068x / 1.108x
  consumer_saved_us min/mean/max:
    8.36 / 27.19 / 40.86
  checksum delta max:
    0
  locality:
    no_order LRU@8 0.1723, order_hit 0.2227
    layer_prior LRU@8 0.7107, order_hit 0.3823

1024 windows / 523,448 requests / repeat=10:
  layer_prior raw consumer speedup min/mean/max:
    1.057x / 1.090x / 1.162x
  consumer_saved_us min/mean/max:
    29.96 / 65.19 / 94.00
  checksum delta max:
    0
  locality:
    no_order LRU@8 0.2324, order_hit 0.2611
    layer_prior LRU@8 0.7433, order_hit 0.3663

all windows / 7,360 windows / 3,761,600 requests / repeat=3 smoke:
  layer_prior raw consumer speedup min/mean/max:
    1.112x / 1.132x / 1.155x
  consumer_saved_us min/mean/max:
    690.99 / 853.70 / 1035.24
  checksum delta max:
    0
  locality:
    no_order LRU@8 0.3699, order_hit 0.3509
    layer_prior LRU@8 0.8217, order_hit 0.4135
```

Net-overhead result:

```text
Raw descriptor visitation order is consistently positive in the controlled HIP
consumer, but dynamic per-invocation order construction is not net-positive.

Best observed C++ layer_prior_plan net_saved_us remains negative:
  512-window sweep:  max net_saved_us_after_cpp_plan_build ~= -3.14 ms
  1024-window sweep: max net_saved_us_after_cpp_plan_build ~= -6.22 ms
  all-window smoke:  max net_saved_us_after_cpp_plan_build ~= -33.96 ms

Therefore the execution gate is:
  enable real descriptor-order execution only when the layer-prior plan is
  precomputed, reused, or consumed through a two-level descriptor representation.

Disable:
  dynamic per-invocation full order rebuild/materialization on the decode
  critical path.
```

C++ builder robustness:

```text
The micro-runtime now infers the C++ builder tile domain from the observed
stream:
  num_tiles = max(tile_id) + 1

This avoids treating non-256 tile domains as builder failures. The C++ builder
mode execution is also recorded with returncode/stdout/stderr and ok=false on
failure, so optional builder accounting no longer destroys the raw consumer
benchmark result.

Smoke:
  descriptor_consumer_micro_runtime_builder_smoke.json
  selected windows: 4
  C++ layer_prior_plan ok=true, returncode=0
  C++ layer_prior_materialized ok=true, returncode=0

Regression tests:
  tests/test_descriptor_consumer_micro_runtime.py
  covers observed num_tiles inference, net_saved_us formulas, and skipping net
  accounting when the descriptor multiset does not match.
```

Interpretation:

```text
The descriptor-order execution bridge now passes the same-multiset correctness
gate and the raw consumer timing gate across 512/1024/all-window AWQ traces.

It does not yet pass the dynamic-builder net-benefit gate. The next real
runtime MVP should patch a descriptor consumer to use precomputed/reused
layer_prior group plans or a two-level group_order + group_offsets path, with
fallback to original order.

This remains more mature than speculative LDS payload staging, but it is still
one step before a vLLM fused-MoE kernel patch.
```

Two-level descriptor consumer MVP:

```text
implementation:
  microbench/tile_order_cache/tile_order_cache_bench.hip
  scripts/run_descriptor_consumer_micro_runtime.py

new input mode:
  materialized:
    tile_ids[]

  two-level group plan:
    group_tile_ids[]
    group_counts[]
    group_offsets[]

semantics:
  same current-router descriptor multiset
  no router/membership/logit change
  consume group plan directly instead of materializing reordered tile_ids
```

First one-CTA-per-group result:

```text
The first group-plan consumer was semantically correct but often slower,
because launching one CTA per active B-tile group created too much scheduling
overhead.
```

Chunked group-plan fix:

```text
The group-plan kernel now consumes multiple groups per CTA, using tiles_per_cta
as groups_per_cta in group-plan mode.
```

AWQ 128 trace, first 512 windows, tile_elems=1024, no flush, groups_per_cta sweep:

```text
GPU0 two-level layer_prior speedup vs no_order:
  groups_per_cta=4:  1.236x
  groups_per_cta=8:  1.159x
  groups_per_cta=16: 1.113x
  groups_per_cta=32: 1.072x
  groups_per_cta=64: 0.983x

GPU1 two-level layer_prior speedup vs no_order:
  groups_per_cta=4:  1.246x
  groups_per_cta=8:  1.171x
  groups_per_cta=16: 1.107x
  groups_per_cta=32: 1.077x
  groups_per_cta=64: 0.993x
```

512-window mixed tile-size result with groups_per_cta=32:

```text
two-level group-plan consumer is positive for many 512/1024-tile cases, but
turns negative for 2048-tile cases. Therefore group-plan execution needs its
own runtime gate:

  enable two-level consumer only when:
    same_multiset = true
    tile_elems in measured positive envelope
    groups_per_cta in measured positive envelope, currently 4 or 8 for 1024
    descriptor plan is precomputed/reused or built inside the consumer path

  keep fallback:
    materialized layer_prior order or original no_order
```

Net-overhead boundary remains:

```text
The two-level consumer removes materialized ordered tile-id input from the
kernel path, but the current Python/C++ host plan build is still not
net-positive as a per-invocation critical-path action. The next runtime patch
should pass precomputed layer-prior group plans or build the group plan inside
the existing descriptor producer/consumer without a full host-side rebuild.
```

Two-level gate table + producer stats:

```text
implementation:
  scripts/summarize_descriptor_consumer_gate_table.py
  src/mtp_expert_prefetch/runtime/descriptor_order.py
  src/mtp_expert_prefetch/runtime/shadow_log.py
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py

gate report:
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_w512_two_level_gate_table.json
  outputs/reports/tile_order_cache/descriptor_consumer_two_level_gate_table_summary.md

runtime shadow fields:
  descriptor_order_execution_mode
  descriptor_group_plan_groups_per_cta
  descriptor_group_plan_group_count
  descriptor_group_plan_avg_group_size
  descriptor_group_plan_p95_group_size
  descriptor_group_plan_max_group_size
  descriptor_group_plan_cta_count
```

Gate table result on AWQ 128 trace, first 512 windows, tile_elems=1024:

```text
group-plan stats:
  group_count: 75,733
  window_count: 512
  avg_group_size: 3.46
  p95_group_size: 10
  max_group_size: 63
  avg_groups_per_window: 147.92
  p95_groups_per_window: 173
  max_groups_per_window: 189

gate rows:
  allowed: 16 / 20

GPU0:
  groups_per_cta=4:
    no_flush 1.302x, 16M_flush 1.487x
  groups_per_cta=8:
    no_flush 1.154x, 16M_flush 1.212x
  groups_per_cta=16:
    no_flush 1.133x, 16M_flush 1.077x
  groups_per_cta=32:
    no_flush 1.061x, 16M_flush 1.032x
  groups_per_cta=64:
    no_flush 0.975x, 16M_flush 0.999x

GPU1:
  groups_per_cta=4:
    no_flush 1.269x, 16M_flush 1.590x
  groups_per_cta=8:
    no_flush 1.144x, 16M_flush 1.338x
  groups_per_cta=16:
    no_flush 1.088x, 16M_flush 1.047x
  groups_per_cta=32:
    no_flush 1.041x, 16M_flush 1.026x
  groups_per_cta=64:
    no_flush 0.979x, 16M_flush 0.984x
```

Updated gate:

```text
Recommended initial runtime gate:
  descriptor_order_execution_mode = two_level_group_plan
  tile_elems = 1024
  groups_per_cta in {4, 8}
  same_multiset = true
  checksum/parity gate passes

Allowed but lower-priority diagnostic envelope:
  groups_per_cta in {16, 32}

Disable:
  groups_per_cta >= 64
  unmeasured tile_elems/device/kernel variants
```

Producer-side status:

The runtime descriptor-order producer now computes and emits two-level group
plan stats in both full summary and minimal telemetry modes. This lets online
shadow runs audit whether a request/layer falls into the measured profitable
group-plan envelope without changing real execution order.

Bugfix: the generic `scripts/trace_router_mtp.py` entry point now dispatches
`model.backend: vllm` configs to `trace_router_mtp_vllm()` before entering the
Transformers tracing path. The previous behavior ignored the vLLM backend and
could generate only `.pt` router traces without `runtime_shadow.jsonl`.

End-to-end validation through the generic entry now writes runtime shadow output
for the AWQ vLLM descriptor-order smoke:

```text
runtime_shadow.jsonl rows: 2,560
descriptor_summary_min rows: 1,280
outcome_aggregate rows: 1,280

sample descriptor fields:
  descriptor_order_execution_mode: two_level_group_plan
  descriptor_order_policy: layer_prior_frequency
  descriptor_order_prior_id: layer_prior_frequency_384calib
  descriptor_group_plan_groups_per_cta: 8
  descriptor_group_plan_group_count: 173
  descriptor_group_plan_avg_group_size: 5.87
  descriptor_group_plan_p95_group_size: 27.4
  descriptor_group_plan_max_group_size: 56
  descriptor_group_plan_cta_count: 22
```

Regression coverage:
`tests/test_trace_backend_dispatch.py` verifies that vLLM backend configs route
through the vLLM trace function from the generic entry point.

Expanded two-level runtime gate:

```text
implementation:
  scripts/check_descriptor_order_group_plan_consistency.py
  configs/runtime/descriptor_order_two_level_gate.yaml

gate reports:
  outputs/reports/tile_order_cache/descriptor_consumer_micro_runtime_awq128_two_level_gate_table_tile_sweep.json
  outputs/reports/tile_order_cache/descriptor_consumer_two_level_gate_table_tile_sweep_summary.md

sweep:
  tile_elems: 512 / 1024 / 2048
  groups_per_cta: 4 / 8 / 16 / 32 / 64
  cache_flush_elems: 0 / 16M
  devices: GPU0 / GPU1

gate result:
  rows: 60
  allowed: 47
  checksum_delta: 0 for all allowed rows

conservative first runtime gate:
  descriptor_order_execution_mode = two_level_group_plan
  tile_elems in {512, 1024, 2048}
  groups_per_cta in {4, 8}
  devices in {0, 1}
  same_multiset = true
  checksum/parity gate passes

diagnostic only:
  groups_per_cta in {16, 32}

disable:
  groups_per_cta >= 64
  unmeasured tile_elems/device/kernel variants
```

Online producer consistency check:

```text
report:
  outputs/reports/tile_order_cache/descriptor_order_group_plan_online_consistency_smoke32.md

input:
  data/traces/aya_dataset_smoke_awq_vllm_descriptor_order_shadow_count_only_minimal_aggregate_batched_smoke32/runtime_shadow.jsonl

descriptor events: 1,280
missing required group-plan fields: 0
execution modes: {two_level_group_plan: 1,280}
groups_per_cta: {8: 1,280}

producer stats:
  descriptor_tile_request_count mean: 783.5
  descriptor_unique_b_tiles mean: 102.83
  descriptor_group_plan_group_count mean: 140.66
  descriptor_group_plan_avg_group_size mean: 5.75
  descriptor_group_plan_p95_group_size mean: 23.65
  descriptor_group_plan_max_group_size max: 63
  descriptor_group_plan_cta_count mean: 18.02
  descriptor_order_build_us mean: 52.21

gate projection for observed groups_per_cta=8:
  tile_elems 512:  4/4 allowed
  tile_elems 1024: 4/4 allowed
  tile_elems 2048: 4/4 allowed
```

## 2026-05-11: Direct-topk runtime path demoted to diagnostic evidence

We tested whether bypassing the vLLM/AWQ expert-assignment producer launch is
profitable by itself. The `direct_topk_identity` variant preserves the original
top-k slot order (`chosen = logical_pid_m`) and does not use layer-prior
ordering, `prior_rank`, or a layer allowlist.

Scope: this is the current patched `diagnostic_off` trace path through the
project recorder/patch entrypoint, not an unmodified production vLLM path.

Implementation coverage:

```text
W1: top_k=8 fixed direct-topk identity kernel
W2: top_k=1 generic direct-topk identity kernel
invalid / mapped -1 expert slots: zero-filled in the original top-k slot
```

Correctness result on GPU1 AWQ heldout128/gen8 `diagnostic_off`:

```text
generated_text match: 128 / 128
router_topk match:    128 / 128
router_weights match: 128 / 128
runtime_shadow rows:  0
```

Because runtime shadow writeout is disabled in this benchmark, the W1/W2
coverage statement comes from implementation/launch-path coverage rather than
JSONL event counts.

Performance result:

```text
no_order TPOT:             0.0710665390 s/output token
direct_topk_identity TPOT: 0.0751786907 s/output token
speedup vs no_order:       0.9453x
```

Evidence artifact:

```text
outputs/reports/tile_order_cache/direct_topk_identity_negative_gate_awq_w7900_gpu1.md
```

Conclusion:

`direct_topk_identity` preserves output/router parity in this smoke, but is
performance negative. Under GPU1 W7900 AWQ heldout128/gen8 `diagnostic_off`,
the current direct-topk consumer replacement does not provide a TPOT win.
Direct-topk execution is therefore demoted from the runtime-win path to
shadow/diagnostic use or kernel-level negative evidence for this configuration.

Next direction:

```text
Keep:
  online shadow / minimal telemetry
  descriptor-order diagnostics
  two-level group-plan micro-runtime evidence

Do not default-enable:
  direct_topk_identity
  direct_topk_layer_prior
  post-hoc tensor reorder

If revisited:
  require a new kernel design with measured TPOT win under diagnostic_off
  and W1/W2 correctness parity.
```

## 2026-05-11: W7900 AWQ WNA16 config sweep

Motivation:

The AWQ vLLM runs warn that no optimized MoE config exists for:

```text
E=256,N=512,device_name=AMD_Radeon_PRO_W7900_Dual_Slot_,dtype=int4_w4a16.json
```

Implementation:

```text
script:
  scripts/run_wna16_config_sweep.py

mechanism:
  uses VLLM_TUNED_CONFIG_FOLDER
  does not modify site-packages

artifact:
  outputs/reports/wna16_config_sweep/awq_w7900_gpu1/summary_all.md
```

First-pass sweep:

```text
GPU: 1
mode: no_order
split: heldout start=128
max_samples: 32
max_tokens: 8
runtime shadow: diagnostic/off baseline config
```

Results:

```text
baseline_no_tuned_config: TPOT 0.072071, 1.0000x
bm16_g1_w4_s2:            TPOT 0.073352, 0.9825x
r8060s_full_bn16_k64:     TPOT 0.076495, 0.9422x
bm16_g1_w2_s2:            TPOT 0.078705, 0.9157x
bm32_g4_w2_s2:            TPOT 0.081149, 0.8881x
bm32_g1_w2_s2:            TPOT 0.082928, 0.8691x
bm16_g1_w1_s2:            TPOT 0.098227, 0.7337x
```

Conclusion:

No candidate beat the default missing-config path in this short sweep. The
default vLLM WNA16 heuristic is already stronger than these simple tuned-config
overrides on W7900/AWQ decode. In particular, writing a config file that fixes
`BLOCK_SIZE_N/K` can hurt because W1 (`top_k=8`) and W2 (`top_k=1`) benefit from
different projection-specific N/K choices.

Next tuning direction:

```text
Prefer:
  patchable runtime override that leaves BLOCK_SIZE_N/K projection-specific
  or a microbench/auto-tuner that times W1 and W2 separately

Avoid:
  one static JSON config that forces the same BLOCK_SIZE_N/K for both W1 and W2
```

## 2026-05-11: WNA16 runtime override with dynamic N/K preserved

Motivation:

Static tuned JSON can accidentally lock `BLOCK_SIZE_N/K` across W1/W2.  The
new path patches the local WNA16 invoke wrapper instead:

```text
runtime_shadow.wna16_config_override:
  allowed keys:
    BLOCK_SIZE_M
    GROUP_SIZE_M
    SPLIT_K
    num_warps
    num_stages

  rejected keys:
    BLOCK_SIZE_N
    BLOCK_SIZE_K
```

Safety changes:

```text
Do not override N/K.
Keep any W1/W2 dynamic N/K already selected by vLLM.
Fail fast if an override config contains unsupported keys.
Apply only to W7900/AWQ decode-like WNA16 shapes:
  A_M <= wna16_config_override_max_tokens
  top_k in {1, 8}
  A_M * top_k == 8
  WNA16 quant path
  block_shape is present
```

Important negative finding:

Unconditional runtime override caused HIP illegal memory access even for
`bm16_g1_default`.  This indicates that decode tuning must not touch prefill or
other non-target small/large-M shapes.

Strict decode-guard smoke:

```text
artifact:
  outputs/reports/wna16_runtime_override_sweep/awq_w7900_gpu1_decode_guard_32_strict/summary.md

GPU: 1
split: heldout start=128
max_samples: 32
max_tokens: 8

baseline_no_tuned_config: TPOT 0.072558, 1.0000x
bm16_g1_w2_s2:            TPOT 0.072078, 1.0067x
```

Conclusion:

The strict decode-only runtime override is now safe enough for controlled
experiments and preserves vLLM dynamic W1/W2 N/K selection.  The best observed
candidate is only a weak positive smoke-level signal (~0.7% TPOT), not a
performance claim.  It requires repeat/128-512 sample validation and W1/W2
attribution before becoming a real tuning result.

Next tuning direction:

```text
P0:
  W1/W2 separated microbench/autotune
  decode/prefill separated timing attribution
  repeated 32/128/512 validation for bm16_g1_w2_s2

Stop:
  if repeat runs fail to show >2-3% stable decode improvement
  or any candidate triggers illegal memory access twice
```

## 2026-05-11: W1/W2 separated WNA16 runtime override smoke

Implementation:

```text
hook:
  runtime_shadow.wna16_config_override_target_top_k

driver:
  scripts/run_wna16_w1w2_autotune.py

semantics:
  W1 bucket -> target_top_k = 8
  W2 bucket -> target_top_k = 1
```

Smoke artifact:

```text
outputs/reports/wna16_w1w2_autotune/awq_w7900_gpu1_smoke8/summary.md
```

Results:

```text
GPU: 1
split: heldout start=128
max_samples: 8
max_tokens: 8
candidate: bm16_g1_w2_s2

W1 target_top_k=8:
  baseline TPOT 0.077128
  candidate TPOT 0.074793
  speedup 1.0312x

W2 target_top_k=1:
  baseline TPOT 0.074715
  candidate TPOT 0.075063
  speedup 0.9954x
```

Conclusion:

The weak global `bm16_g1_w2_s2` signal is not uniform across WNA16 projections.
The signal appears W1-only in the smoke run, while W2 slightly regresses.  This
supports the W1/W2-separated autotune direction and argues against expanding
global runtime overrides.

Next:

```text
Validate W1-only bm16_g1_w2_s2 on 32/128 samples.
Sweep a small W1-only candidate set before touching W2.
Keep W2 at baseline unless a separate W2 candidate passes repeat validation.
```

Follow-up 32-sample W1-only validation:

```text
artifact:
  outputs/reports/wna16_w1w2_autotune/awq_w7900_gpu1_w1_32/summary.md

W1 target_top_k=8:
  baseline TPOT 0.070923
  bm16_g1_w2_s2 TPOT 0.072682
  speedup 0.9758x
```

Conclusion:

The W1-only 8-sample positive signal does not survive the 32-sample validation.
`bm16_g1_w2_s2` is therefore not a stable WNA16 runtime override candidate.  The
W1/W2-separated autotune framework remains useful, but this specific candidate
should be frozen as failed rather than promoted.

## 2026-05-11: WNA16 W1 kernel timing attribution

Implementation:

```text
event:
  wna16_kernel_timing

fields:
  wna16_bucket = w1 / w2 / other
  wna16_num_tokens
  wna16_top_k
  wna16_config_override_applied
  WNA16 config M/N/K/GROUP/SPLIT/warps/stages
  host invoke elapsed_us
  optional GPU event elapsed_us

scripts:
  scripts/run_wna16_config_sweep.py --emit-kernel-timing
  scripts/run_wna16_w1w2_autotune.py --emit-kernel-timing
  scripts/analyze_wna16_kernel_cost.py --runtime-only
```

GPU-event diagnostic smoke:

```text
artifact:
  outputs/reports/wna16_w1w2_autotune/awq_w7900_gpu1_w1_gpu_event_smoke4/

GPU: 1
max_samples: 4
bucket: W1 target_top_k=8
candidate: bm16_g1_w2_s2

baseline W1 GPU p50/p95:
  135.05us / 148.63us

candidate W1 GPU p50/p95:
  126.24us / 146.16us

baseline W2 GPU p50/p95:
  79.71us / 96.45us

candidate W2 GPU p50/p95:
  80.49us / 93.94us
```

Interpretation:

`bm16_g1_w2_s2` can improve the W1 kernel bucket in a synchronized diagnostic
run, but this did not survive the 32-sample end-to-end TPOT validation.  The
kernel-level signal is therefore useful for screening candidates, not sufficient
for a runtime performance claim.

Next:

```text
Use GPU-event W1/W2 timing as a first-stage candidate filter.
Then validate survivors with telemetry-off TPOT on 32/128 samples.
Do not promote any candidate from kernel p50 alone.
```

## 2026-05-11: W1-only WNA16 candidate pool screen

Candidate pool:

```text
BLOCK_SIZE_M=16
GROUP_SIZE_M=1
SPLIT_K=1
num_warps in {1, 2, 4}
num_stages in {2, 3}
target_top_k=8  # W1 only
```

GPU-event screen:

```text
artifact:
  outputs/reports/wna16_w1w2_autotune/awq_w7900_gpu1_w1_candidate_pool_gpu_event_smoke4/w1_timing_summary.md

rule:
  W1 GPU p50 speedup >= 1.03x
  W1 GPU p95 speedup >= 1.00x
  override rows must cover all target-bucket GPU rows
```

Results:

```text
baseline_no_tuned_config:
  W1 GPU p50/p95 = 136.724us / 153.443us

bm16_g1_w1_s2:
  314.118us / 329.788us -> fail

bm16_g1_w1_s3:
  583.650us / 601.540us -> fail

bm16_g1_w2_s2:
  126.036us / 147.906us -> survivor
  p50 speedup 1.0848x
  p95 speedup 1.0374x

bm16_g1_w2_s3:
  152.946us / 174.056us -> fail

bm16_g1_w4_s2:
  138.047us / 152.997us -> fail

bm16_g1_w4_s3:
  143.697us / 163.197us -> fail
```

Telemetry-off TPOT validation of survivor:

```text
artifact:
  outputs/reports/wna16_w1w2_autotune/awq_w7900_gpu1_w1_survivor_tpot32/summary.md

W1 target_top_k=8, max_samples=32:
  baseline TPOT 0.073200
  bm16_g1_w2_s2 TPOT 0.073327
  speedup 0.9983x
```

Conclusion:

The W1 GPU-event screen identifies `bm16_g1_w2_s2` as the only kernel-level
survivor, but it does not improve telemetry-off end-to-end TPOT at 32 samples.
Therefore no WNA16 runtime override candidate currently qualifies for runtime
promotion.  The kernel timing infrastructure remains useful for diagnosing
where time is spent, but WNA16 config tuning should be frozen unless a new
candidate class or a true W1/W2 microkernel benchmark is added.

## 2026-05-12: AWQ MoE residual attribution

Goal:

```text
Explain experts_total - quant_method.apply and the remaining quant_method.apply
residual under a production-like diagnostic posture:
  record_router_topk = false
  WNA16 GPU-event timing = off for primary attribution
```

Implementation:

```text
Added MoE substage timing for:
  experts_shared_stream_sync
  experts_maybe_dispatch
  experts_maybe_combine
  experts_shared_determine_order
  experts_shared_apply_skipped
  experts_shared_direct_layer
  experts_shared_aux_stream_layer_wait
  apply_config_lookup
  apply_resize_cache_{w1_output,activation,w2_output,other}

The active MoE context now uses token-based push/reset in new wrappers, while
the legacy set_active_moe_assignment_context API remains by-reference for tests
and direct recorder utilities.
```

Primary evidence:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_residual_split_smoke8/
  diagnostic_light_decode_breakdown.{json,md}

GPU1, AWQ, 8 samples, 64 output tokens, diagnostic_light:
  generate                       4851.471 ms
  decoder layer                  3829.267 ms
  MLP/MoE block                  2033.110 ms
  quant_method.apply              961.444 ms
  experts_total                  2005.274 ms
  experts_total - quant_apply    1043.830 ms
  measured non-apply parts        656.823 ms
  experts_total residual          387.007 ms

Key non-apply contributors:
  shared no-overlap               462.546 ms
  shared direct layer             410.742 ms
  shared no-overlap inner sum     419.733 ms
  shared no-overlap residual       42.813 ms
  select_experts                  147.348 ms
  prepare_expert_assignment        83.172 ms
```

Quant apply residual:

```text
quant_method.apply                961.444 ms
measured quant-apply parts         627.393 ms
quant-apply residual              334.051 ms

Measured parts include:
  W1 host dispatch                248.684 ms
  W2 host dispatch                205.304 ms
  activation                       28.148 ms
  moe_sum                          38.220 ms
  config lookup                    14.812 ms
  quantize hidden/intermediate       9.054 ms
  prepare_expert_assignment        83.172 ms
```

Diagnostic-only WNA16 GPU-event cross-check:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_residual_split_smoke8/
  diagnostic_full_decode_breakdown.{json,md}

diagnostic_full enables synchronized GPU events and record_topk, so it is not a
production TPOT claim.  It is retained only to estimate WNA16 host-vs-GPU gaps.
```

Rejected path:

```text
Global torch.empty / torch.empty_like monkey-patching was tested and rejected.
It can perturb vLLM initialization/device placement, so allocation timing must
not be collected through a global torch allocation hook.
```

Conclusion:

```text
The apparent select_experts bottleneck was mostly record_topk/tracing pollution.
With record_router_topk=false, the dominant MoE-side non-apply cost is the
shared expert path, especially the shared direct layer.

The remaining quant_method.apply residual is still substantial, but should be
investigated through source-level fused_experts_impl instrumentation or a local
vLLM overlay, not a global torch allocation hook.
```

## 2026-05-12: AWQ shared/apply source-level split

Goal:

```text
Move beyond wrapper-level residual attribution by splitting:
  1. shared expert direct layer into W1 / activation / W2 / output-combine /
     child-other / residual;
  2. quant_method.apply inside fused_experts_impl into pre-dispatch,
     workspace allocation, W1/W2 enqueue regions, activation, combine/scatter,
     and post-dispatch.
```

Implementation:

```text
SharedExpert.apply now has a diagnostic source-split path that installs
temporary leaf-module hooks while preserving the original forward result.

fused_experts_impl is wrapped by a diagnostic source-level copy that emits
apply_source_* regions around the same vLLM operations.

Nested wrapper timings are still emitted, but analyzer reports source parts and
older measured parts as separate decompositions.  They must not be summed
together.
```

Primary evidence:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_source_split_smoke8/
  diagnostic_light_decode_breakdown.{json,md}

GPU1, AWQ, 8 samples, 64 output tokens, diagnostic_light:
  generate                         5684.718 ms
  decoder layer                    4081.945 ms
  attention                        1185.552 ms
  MLP/MoE block                    2338.800 ms
  experts_total                    2313.167 ms
  quant_method.apply               1036.613 ms
  experts_total - quant_apply      1276.554 ms
```

Shared expert source split:

```text
shared no-overlap                  713.861 ms
shared direct layer                674.736 ms
shared source parts sum            374.570 ms
shared residual                    300.167 ms

source parts:
  shared W1/gate-up                100.898 ms
  shared activation                 46.384 ms
  shared W2/down                    90.659 ms
  shared child-other               136.628 ms
```

Quant apply source split:

```text
quant_method.apply                1036.613 ms
old measured parts sum             602.905 ms
old measured residual              433.709 ms
source parts sum                   783.005 ms
source residual                    253.609 ms

source regions:
  pre-dispatch                      55.877 ms
  workspace allocation              55.891 ms
  W1 enqueue                       249.750 ms
  activation                        49.577 ms
  W2 enqueue                       215.471 ms
  combine/scatter                   64.234 ms
```

Interpretation:

```text
Source-level instrumentation explains more of quant_method.apply than the
previous wrapper-level decomposition, reducing the residual from ~434 ms to
~254 ms in this diagnostic run.

The shared expert direct layer remains only partially explained.  The large
child-other and residual terms mean the next shared-expert step is to inspect
actual leaf module names / structure before claiming W1/activation/W2 are the
dominant shared costs.
```

Boundary:

```text
This run is diagnostic attribution only, not a production TPOT claim.
Temporary shared-expert forward hooks and the copied fused_experts_impl wrapper
add measurement overhead and are version-sensitive.  Performance claims must
continue to use telemetry-off or production-like paths with record_topk disabled.
```

Follow-up hardening:

```text
The copied fused_experts_impl diagnostic wrapper now installs only when the
upstream vLLM function signature exactly matches the expected parameter list;
otherwise the original implementation is left untouched.

experts_shared_child_other rows now carry the leaf module name in
moe_substage_status, allowing the next diagnostic pass to identify which shared
expert leaves are still unclassified.
```

Leaf-name validation:

```text
artifact before classification:
  outputs/reports/awq_telemetry_ladder/gpu1_source_split_leafnames_smoke8/

The only child-other shared leaf was:
  experts_shared_child_other:leaf:expert_gate = 2560

Qwen shared expert uses expert_gate as an output gate:
  sigmoid(expert_gate(x)) * out

Therefore expert_gate / shared_expert_gate are classified as
experts_shared_output_combine rather than W1/gate-up.
```

Validation after classification:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
  gpu1_source_split_expert_gate_classified_smoke8/

GPU1, AWQ, 8 samples, 64 output tokens, diagnostic_light:
  experts_shared_child_other           null
  experts_shared_output_combine        164.015 ms
  shared direct source parts sum       449.263 ms
  shared direct minus source parts     355.241 ms
  shared direct layer                  804.504 ms

The child-other bucket is now closed for this model/version.  The remaining
shared direct residual is no longer a leaf-name classification issue; it likely
comes from wrapper/functional overhead, non-leaf work, or hook instrumentation
overhead and should be treated as diagnostic residual.
```

Qwen2MoeMLP source fast path:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
  gpu1_source_split_qwen2_direct_smoke8/

For the Qwen2MoeMLP shared expert structure, the diagnostic source split now
executes the same forward stages directly:
  gate_up_proj -> act_fn -> down_proj -> sigmoid(expert_gate(x)) * out

GPU1, AWQ, 8 samples, 64 output tokens, diagnostic_light:
  shared direct layer                  610.621 ms
  shared W1/gate-up                    110.594 ms
  shared activation                     58.961 ms
  shared W2/down                       112.373 ms
  shared output/combine                214.623 ms
  shared child-other                   null
  shared direct source parts sum       496.550 ms
  shared direct minus source parts     114.071 ms

Compared with the generic leaf-hook path, the Qwen2-specific source path reduces
the shared direct residual from ~355 ms to ~114 ms.  This confirms that most of
the earlier residual was instrumentation / leaf-hook attribution mismatch, not
unclassified model compute.
```

Safety hardening:

```text
The Qwen2 source path is gated by:
  class name == Qwen2MoeMLP
  class module == vllm.model_executor.models.qwen2_moe
  gate_up_proj / act_fn / down_proj are callable
  expert_gate is None or callable
  bound forward signature == (x)

If the gate fails, tracing falls back to the generic leaf-hook diagnostic path.
Actual execution exceptions still propagate; this avoids silently masking a
real upstream semantic change.
```

### Source Timing Telemetry Ladder Calibration

Before further splitting the remaining fused experts attribution gaps, we added
an explicit source timing ladder:

```text
runtime_shadow.moe_source_timing_mode:
  off
  outer
  outer_impl
  outer_impl_enqueue
  full
```

Implementation notes:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_source_timing_ladder_smoke8/

The ladder keeps record_router_topk=false and emits decoder-layer / MoE timing,
while controlling how much copied fused_experts source timing is enabled.
Unknown moe_source_timing_mode now raises an explicit ValueError instead of
silently falling back to full timing.
run_awq_telemetry_ladder.py now prepends PYTHONPATH=src instead of overwriting
an existing PYTHONPATH, and avoids nested conda run when already inside the
requested environment.
```

GPU1, AWQ, 8 samples, 64 output tokens:

| mode | TPOT (s) | generate (s) | quant_apply (ms) | outer (ms) | impl (ms) | outer-impl (ms) | impl-inner (ms) | W1 gap (ms) | W2 gap (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| source_none | 0.101681 | 6.508 | 1112.910 | 0.000 | 0.000 | n/a | n/a | n/a | n/a |
| source_outer | 0.106450 | 6.813 | 1220.606 | 1187.561 | 0.000 | n/a | n/a | n/a | n/a |
| source_outer_impl | 0.100815 | 6.452 | 1169.148 | 1138.227 | 983.367 | 154.859 | n/a | n/a | n/a |
| source_outer_impl_enqueue | 0.118381 | 7.576 | 1392.335 | 1356.364 | 1155.043 | 201.321 | 536.345 | 58.133 | 45.009 |
| source_full | 0.109562 | 7.012 | 1402.959 | 1369.977 | 1192.610 | 177.367 | 168.648 | 46.034 | 40.217 |

Interpretation:

```text
source_none is the calibration baseline for diagnostic_light without copied
fused_experts source regions.
source_outer adds about +4.7% TPOT vs source_none in this single 8-sample run.
source_outer_impl is within run noise of source_none, suggesting impl_total-only
is not obviously more expensive than the baseline at this scale.
source_outer_impl_enqueue is the heaviest mode (+16.4% TPOT vs source_none), so
that mode should not be used for performance shares.
source_full is also diagnostic-only (+7.8% TPOT vs source_none), but its
impl-inner residual (~169 ms) is much more credible than the enqueue-only mode's
~536 ms artifact.
```

Boundary:

```text
These are diagnostic attribution runs, not production TPOT claims.  The next
165 ms / 112 ms / 79 ms split should use the ladder-calibrated view:
  - treat source_outer_impl_enqueue as contaminated by instrumentation overhead;
  - use source_full to name buckets;
  - use source_none / source_outer / source_outer_impl to estimate observation
    overhead before making any optimization claim.
```

### Source Residual Emit/Entry Split

After the ladder calibration, source_full was rerun with explicit source event
write-overhead and impl-entry-overhead telemetry.

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
  gpu1_source_timing_emit_split_smoke8/source_full/repeat_00/
```

GPU1, AWQ, 8 samples, 64 output tokens, source_full:

```text
quant_method.apply                         1199.373 ms
fused_experts_outer                        1171.623 ms
outer_impl_call                            1121.178 ms
impl_entry_overhead                           2.781 ms
impl_total                                  996.305 ms
source_emit_overhead                        148.850 ms

outer_impl_call - impl_total                124.873 ms
named overhead (entry + emit)               151.631 ms
unclassified after named overhead           -26.758 ms

impl_total - inner source parts             151.948 ms
impl residual after emit adjustment           3.098 ms
```

W1/W2 launch/glue split:

```text
W1 source enqueue                           258.010 ms
W1 dispatch host                            241.304 ms
W1 source enqueue - dispatch host            16.706 ms
W1 dispatch host - launch parts              20.432 ms
W1 source enqueue - launch parts             37.139 ms

W2 source enqueue                           217.042 ms
W2 dispatch host                            202.013 ms
W2 source enqueue - dispatch host            15.030 ms
W2 dispatch host - launch parts              17.385 ms
W2 source enqueue - launch parts             32.414 ms
```

Interpretation:

```text
The previous ~165 ms impl_total-minus-inner-source residual is almost entirely
source event write overhead in full source timing mode.  After subtracting
measured emit overhead, the residual is only ~3 ms.

The previous ~112 ms outer_impl_call-minus-impl_total boundary is also explained
by measured entry/emit overhead within diagnostic noise; it should not be
treated as production runtime overhead.

The W1/W2 source enqueue gap decomposes into two smaller pieces:
  source wrapper -> dispatch host: ~15-17 ms
  dispatch host -> launch parts:   ~17-20 ms

Therefore the next real source-level target is not the apparent 165/112 ms
residual; those are diagnostic artifacts.  Remaining launch/glue work is
closer to tens of milliseconds in this 8-sample diagnostic and should be
validated with lower-overhead telemetry before optimization.
```

### Low-Overhead Dispatch/Launch Gap Check

The same traces were re-analyzed to compare low-overhead `source_none` against
the full source diagnostic.

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
  gpu1_source_timing_emit_split_smoke8/
  low_overhead_dispatch_gap_compare.json
```

Low-overhead source_none:

```text
quant_method.apply                         1112.910 ms
W1 dispatch host                            280.443 ms
W1 launch setup                               4.465 ms
W1 launch enqueue                           252.433 ms
W1 dispatch host - launch parts              23.545 ms

W2 dispatch host                            232.327 ms
W2 launch setup                               4.088 ms
W2 launch enqueue                           210.656 ms
W2 dispatch host - launch parts              17.583 ms
```

Interpretation:

```text
Under low-overhead source_none, W1/W2 dispatch-vs-launch residual is only
~23.5 ms / ~17.6 ms across the full 8-sample run.  This is the cleaner estimate
for launch/glue work than copied-source diagnostics.
```

### Copied Dispatch Source Split Attempt

To inspect the residual structurally, the WNA16 branch of
`dispatch_fused_moe_kernel` was copied behind source timing mode and split into:

```text
pre_invoke
cuda_decision
invoke_call
```

The smoke ran successfully, but the copied dispatch source split is too heavy
for performance attribution:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
  gpu1_dispatch_source_split_smoke8/source_full/repeat_00/

quant_method.apply                         2132.329 ms
source_emit_overhead                        778.482 ms
impl residual after emit adjustment           1.835 ms

W1 dispatch host                            358.396 ms
  pre_invoke                                  5.933 ms
  cuda_decision                               4.041 ms
  invoke_call                               259.582 ms
  dispatch host - source parts               88.842 ms

W2 dispatch host                            310.596 ms
  pre_invoke                                  4.352 ms
  cuda_decision                               3.301 ms
  invoke_call                               220.065 ms
  dispatch host - source parts               82.878 ms
```

Boundary:

```text
This copied-dispatch split is a structure check only.  Its event emission
overhead is far too high for performance shares.  For performance attribution,
use source_none dispatch-host-minus-launch-parts (~23.5 ms / ~17.6 ms) as the
current low-overhead estimate.
```

### Decoder Source Split

After excluding the false fused-experts residuals, the next large target was
the decoder non-MoE / attention residual.  A diagnostic decoder source split was
added behind:

```text
runtime_shadow.decoder_source_timing_mode: qwen3_next | qwen3_5
```

The copied decoder forward path is now explicitly mode-gated:
`qwen3_next` only runs on `Qwen3NextDecoderLayer`, and `qwen3_5` only runs on
`Qwen3_5DecoderLayer`.  This avoids silently applying a copied forward body to
an unsupported decoder class.  It records:

```text
decoder_input_layernorm
decoder_linear_attention
decoder_full_attention
decoder_post_attention_layernorm
decoder_mlp_call
```

Artifact:

```text
outputs/reports/awq_telemetry_ladder/
gpu1_decoder_source_split_smoke8_v2/decoder_source/repeat_00/
```

GPU1, AWQ, 8 samples, 64 output tokens, decoder_source:

```text
decoder layer total                   4740.916 ms
source parts sum                      4644.950 ms
decoder layer - source parts            95.966 ms

input RMSNorm                          284.909 ms
linear attention                      1007.605 ms
full attention                         492.230 ms
post-attention RMSNorm                 278.689 ms
MLP/MoE call                          2581.517 ms

MoE layer apply                       1115.112 ms
experts_total                         2512.084 ms
quant_method.apply                    1115.112 ms
```

Interpretation:

```text
The decoder source split closes the decoder layer attribution: only ~96 ms of
the decoder layer remains outside named source buckets in this diagnostic run.

The largest remaining layer-level costs are:
  1. MLP/MoE call (~2.58 s)
  2. attention total (~1.50 s: linear ~1.01 s + full ~0.49 s)
  3. RMSNorm total (~0.56 s)

This confirms that further work should target shared expert / MLP internals and
attention internals rather than the false fused_experts source residuals.
```

Boundary:

```text
This is diagnostic host-wall attribution.  It intentionally duplicates the
decoder forward structure and coexists with existing attention/mlp component
wrappers, so nested rows are not additive with production timing claims.
```

### Attention Leaf Source Split

The decoder source split identified attention as a real remaining layer-level
target.  A diagnostic attention-leaf hook was added for full and linear
attention modules.  The analyzer now preserves unknown decoder component names
instead of silently merging them into `other`, and records
`decoder_unknown_component_counts` as an integrity guard.

Artifact:

```text
outputs/reports/awq_telemetry_ladder/
gpu1_attention_leaf_split_smoke8_v2/decoder_source/repeat_00/
```

GPU1, AWQ, 8 samples, 64 output tokens, decoder_source:

```text
generate                              6360.391 ms
decoder layer total                   5151.259 ms
source parts sum                      5062.221 ms
decoder layer - source parts            89.038 ms

source attention total                1569.876 ms
  linear attention                    1063.746 ms
  full attention                       506.130 ms

attention leaf parts sum               714.243 ms
  linear leaf parts                    392.591 ms
    input proj                          98.214 ms
    ba proj                             75.807 ms
    core                               127.195 ms
    out proj                            91.374 ms
  full leaf parts                      321.653 ms
    qkv proj                            33.261 ms
    q/k norm                           112.330 ms
    core                               144.093 ms
    o proj                              31.969 ms

source attention - leaf parts          855.632 ms
unknown decoder component names              0
```

Interpretation:

```text
The attention leaf split shows that named leaf modules explain ~714 ms of
~1570 ms source-attention time.  The remaining ~856 ms is still inside attention
wrapper/core glue or functional/custom-op regions that are not represented as
leaf `nn.Module` calls.

The largest named attention leaves are:
  1. full attention core (~144 ms)
  2. linear attention core (~127 ms)
  3. full attention q/k norm (~112 ms)
  4. linear input/out/ba projections (~265 ms combined)

Next target:
split the remaining attention wrapper/core residual, especially linear
attention core/glue and full-attention core/KV-cache path, without copying more
large forward bodies into the production-like timing path.
```

Boundary:

```text
This is diagnostic-only nested timing.  Leaf module timings are nested inside
`decoder_linear_attention` / `decoder_full_attention` and should not be added to
decoder source totals for production TPOT claims.
```

Follow-up source-method split:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
  gpu1_attention_leaf_split_smoke8_v4/decoder_source/repeat_00/

changes:
  attention leaf/source hooks are now lazily registered only when the copied
  decoder source path is actually enabled, avoiding leaf-hook registration in
  production-like/off processes.

  linear attention internal methods are timed:
    attention_linear_core_total
    attention_linear_core_decode_non_spec
    attention_linear_layout_unpack

GPU1, AWQ, 8 samples, 64 output tokens, decoder_source:
  linear attention source-method nested sum  678.594 ms
  linear core total                          350.866 ms
  linear core decode_non_spec                327.728 ms

  linear input projection                    100.603 ms
  linear ba projection                        79.108 ms
  linear norm                                181.317 ms
  linear output projection                    95.139 ms

  full attention core                        142.339 ms
  full q/k norm                              117.008 ms
  full qkv projection                         34.036 ms
  full output projection                      32.415 ms
```

Interpretation:

```text
The GDN linear-attention decode fast path is now explicitly identified:
`_forward_core_decode_non_spec` explains most of the linear core source-method
time.  The source-method rows are nested diagnostic counters: `_forward_core`
contains `_forward_core_decode_non_spec`, so their sum is not an additive
attention cost.  The remaining attention cost is split between projection/norm
leaves, full-attention core, and wrapper/custom-op glue.

This run has visible diagnostic outliers in attention sums, so the result should
be used for target localization, not stable percentage claims.  Stable claims
still require a low-intrusion mode or repeated runs.
```

Low-intrusion attention-only mode:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
  gpu1_attention_source_low_intrusion_smoke8/attention_source/repeat_00/

mode:
  runtime_shadow.decoder_source_timing_mode: attention_leaf

semantics:
  does not use copied decoder forward
  uses existing attention wrapper to lazily register attention leaf/source hooks
  keeps record_router_topk=false
```

Key decode source-method result:

```text
linear core total                       348.615 ms
linear core decode_non_spec             325.473 ms
linear input projection                 100.015 ms
linear ba projection                     77.286 ms
linear norm                             180.491 ms
linear output projection                 94.619 ms

full attention core                     142.141 ms
full q/k norm                           113.711 ms
full qkv projection                      33.924 ms
full output projection                   32.741 ms
```

Overhead check:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_attention_source_overhead_smoke8/

GPU1, AWQ, 8 samples, 64 output tokens:
  production_like TPOT      0.078406 s/token
  attention_source TPOT     0.104117 s/token
  relative overhead         +32.8%
```

Interpretation:

```text
The attention-only mode confirms the same target without copying the full
decoder forward: Qwen3.5 linear attention decode spends a substantial named
portion in the GDN non-spec decode core plus norm/projection leaves.

However, this mode still installs Python hooks on attention internals and has a
large measured TPOT perturbation in the overhead check.  It is therefore
diagnostic-only and should not be used as production TPOT evidence.
```

Shared expert diagnostic-light split:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_diagnostic_light_smoke8/diagnostic_light/repeat_00/

mode:
  record_router_topk=false
  moe_source_timing_mode=off
  attention source hooks disabled

GPU1, AWQ, 8 samples, 64 output tokens:
  production_like TPOT from paired overhead run  0.078406 s/token
  diagnostic_light TPOT                         0.101511 s/token

  shared direct layer                           609.232 ms
  shared W1/gate-up                             104.497 ms
  shared activation                              52.702 ms
  shared W2/down                                 98.958 ms
  shared output/combine                         186.364 ms
  shared direct source parts sum                442.521 ms
  shared direct minus source parts              166.711 ms
```

Interpretation:

```text
Shared expert remains a concrete MoE-side target under record_topk=false.
The largest named source part is output/combine, not W1/W2.  The direct-layer
wrapper/glue residual is still visible, but the whole diagnostic_light mode has
large TPOT perturbation and should be used for attribution only, not production
speed claims.
```

Shared output/combine source split:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_output_gate_split_smoke8/diagnostic_light/repeat_00/

change:
  Qwen2MoeMLP shared output/combine is split into:
    experts_shared_output_gate
    experts_shared_output_sigmoid_mul

GPU1, AWQ, 8 samples, 64 output tokens:
  shared direct layer                     619.278 ms
  shared W1/gate-up                       102.551 ms
  shared activation                        52.446 ms
  shared W2/down                           97.746 ms
  shared output gate                      140.985 ms
  shared output sigmoid/mul                44.930 ms
  shared output detailed parts sum        185.914 ms
  shared direct source parts sum          438.657 ms
  shared direct minus source parts        180.621 ms
```

Interpretation:

```text
The previous shared output/combine bucket is mostly the shared expert gate
linear layer, not the sigmoid/multiply.  Shared W1/W2 remain visible but are
not the largest named shared source part.  The remaining direct-layer residual
is still diagnostic wrapper/glue until a lower-intrusion source split or
operator-level timing confirms it.
```

ROCm shared expert forced aux-stream diagnostic:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_force_aux_smoke8_v2/

change:
  runtime_shadow.shared_experts_force_aux_stream=true
  forces SharedExpertsOrder.MULTI_STREAM_OVERLAPPED on ROCm when the vLLM aux
  stream exists and token count is below the existing vLLM shared-expert stream
  threshold.  Default is false.

GPU1, AWQ, 8 samples, 64 output tokens:
  baseline diagnostic_light TPOT          0.097104 s/token
  force aux diagnostic_light TPOT         0.095681 s/token
  generated_text match                    8 / 8

baseline:
  shared no-overlap                       639.391 ms
  shared direct layer                     604.560 ms
  shared output gate                      138.554 ms
  shared output sigmoid/mul                44.030 ms

force aux:
  shared no-overlap                        42.691 ms
  shared overlap                          606.151 ms
  shared aux-stream layer+wait            550.300 ms
  shared stream sync                       48.900 ms
```

Interpretation:

```text
The first forced-aux ROCm smoke is correctness-safe at generated-text level and
shows a small diagnostic TPOT improvement, but internal MoE timing shifts rather
than cleanly shrinking.  This is not yet a performance claim.  The next gate is
multi-repeat telemetry-off/minimal benchmarking plus stronger parity before
considering any runtime default.
```

Safety review update:

```text
The force-aux diagnostic now preserves vLLM's native safety guards:
  reject when _disable_shared_experts_overlap is true
  reject when native order is MK_INTERNAL_OVERLAPPED
  require aux stream to exist
  require token count within the existing vLLM threshold

The first pre-safety-gate 3-repeat run showed a stable positive diagnostic
signal, but it is retained only as direction evidence because it bypassed those
native guards.
```

Safe-force smoke:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_force_aux_safe_smoke8/

GPU1, AWQ, 8 samples, 64 output tokens:
  baseline diagnostic_light TPOT          0.102060 s/token
  safe force-aux diagnostic TPOT          0.092789 s/token
  generated_text match                    8 / 8

baseline:
  shared no-overlap                       669.612 ms
  shared direct layer                     633.678 ms
  shared output gate                      144.216 ms
  shared output sigmoid/mul                45.075 ms

safe force aux:
  shared no-overlap                        44.127 ms
  shared overlap                          599.399 ms
  shared aux-stream layer+wait            541.920 ms
  shared stream sync                       48.599 ms
```

Interpretation:

```text
The safe-force path confirms that ROCm has an executable shared-expert aux
stream path under the current AWQ smoke conditions, despite vLLM's default
CUDA-only platform gate.  This remains diagnostic-only: the TPOT result is a
single-run signal under diagnostic_light, and the official gate requires
multi-repeat safe-force results plus stronger parity under telemetry-minimal or
telemetry-off settings.
```

Safe-force repeat check:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_force_aux_safe_repeats_smoke8/

GPU1, AWQ, 8 samples, 64 output tokens, diagnostic_light:
  repeat 0:
    baseline TPOT   0.098106 s/token
    force aux TPOT  0.093080 s/token
    speedup         1.0540x
    generated_text  8 / 8 match

  repeat 1:
    baseline TPOT   0.098759 s/token
    force aux TPOT  0.092083 s/token
    speedup         1.0725x
    generated_text  8 / 8 match

  repeat 2:
    baseline TPOT   0.099203 s/token
    force aux TPOT  0.095805 s/token
    speedup         1.0355x
    generated_text  8 / 8 match

  median speedup    1.0610x
```

Interpretation:

```text
After restoring vLLM's native safety guards, forced ROCm shared-expert aux
stream still shows a stable positive diagnostic_light signal on GPU1 smoke8.
This is now a credible performance lead, but still not a production claim:
diagnostic_light contains timing/logging overhead, and correctness evidence is
currently generated-text parity only.

Next gate:
  telemetry-minimal/off benchmark
  stronger output/logit parity if available
  larger 32/128-sample split
  explicit fallback/reject evidence for native overlap-disabled and
  MK_INTERNAL_OVERLAPPED conditions
```

Production-like force-aux check:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_shared_force_aux_production_like_repeats_smoke8/

GPU1, AWQ, 8 samples, 64 output tokens, production_like:
  repeat 0:
    baseline TPOT   0.075082 s/token
    force aux TPOT  0.082147 s/token
    speedup         0.9140x
    generated_text  8 / 8 match

  repeat 1:
    baseline TPOT   0.077960 s/token
    force aux TPOT  0.082584 s/token
    speedup         0.9440x
    generated_text  8 / 8 match

  repeat 2:
    baseline TPOT   0.076849 s/token
    force aux TPOT  0.083245 s/token
    speedup         0.9232x
    generated_text  8 / 8 match

  median speedup    0.9306x
```

Conclusion:

```text
Force-shared-aux is correctness-safe at generated-text level in the smoke, but
it is performance-negative under production_like timing.  The earlier
diagnostic_light positive signal was not sufficient for a runtime claim and is
likely measurement/scheduling-context dependent.

Default:
  shared_experts_force_aux_stream=false

Status:
  diagnostic / negative evidence only

Next performance focus:
  do not pursue forced aux-stream as a runtime win on this AWQ/W7900 setting;
  return to larger production-like bottlenecks such as attention/GDN core,
  shared expert gate linear cost, and engine residual.
```

Attention/GDN low-intrusion source-method check:

```text
code:
  added telemetry mode:
    attention_core_light

  runtime behavior:
    decoder_source_timing_mode=attention_core
    records only linear-attention/GDN source methods:
      attention_linear_core_total
      attention_linear_core_decode_non_spec
      attention_linear_layout_unpack

    it does not register full-attention leaf hooks in fresh runs
    and registered leaf hooks are runtime-gated off under attention_core.

artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_attention_core_light_fixed_smoke8/

GPU1, AWQ, 8 samples, 64 output tokens:
  production_like:
    TPOT       0.072913 s/token
    generate  37.331 s

  attention_core_light:
    TPOT       0.094191 s/token
    generate  48.226 s
    overhead   +29.2%

  attention_core_light decode source sums:
    attention total                         11352.3 ms
    attention_linear_core_total              2890.1 ms
    attention_linear_core_decode_non_spec    2680.0 ms
    attention_linear_source_method_nested    5570.1 ms

  event sanity:
    previous buggy core-light event rows:
      decoder_component_timing = 97040
      included full-attention leaf rows

    fixed core-light event rows:
      decoder_component_timing = 71440
      no attention_full_* leaf rows emitted
```

Interpretation:

```text
attention_core_light successfully narrows the diagnostic path to GDN/linear
attention source methods and avoids full-attention leaf-hook pollution.

However, it still adds large TPOT overhead, so it remains diagnostic-only and
must not be used for production performance claims.

The strongest current attention-side target is the linear/GDN core method
itself, especially attention_linear_core_total and
attention_linear_core_decode_non_spec, but the next optimization pass needs a
lower-overhead kernel/operator-level measurement rather than Python method
wrapping.
```

Real-bottleneck summary report:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_attention_core_light_fixed_smoke8/real_bottlenecks.{json,md}

Telemetry contract:
  production_like:
    TPOT/generate baseline only; no diagnostic attribution.

  diagnostic_light:
    coarse decoder/MoE/shared-expert attribution;
    not a production TPOT claim.

  attention_core_light:
    linear/GDN source-method attribution only;
    diagnostic-only due to method-wrapper overhead.

TPOT:
  production_like       0.072913 s/token
  diagnostic_light      0.093705 s/token  (+28.52%)
  attention_core_light  0.094191 s/token  (+29.18%)

diagnostic_light bottlenecks:
  decoder layer              45793.8 ms  95.45% diagnostic generate
  attention                  10920.9 ms  22.76%
  MLP/MoE                    29110.9 ms  60.68%
  MoE apply                  14008.6 ms  29.20%
  shared expert direct        7731.3 ms  16.11%
  shared expert output gate   1259.5 ms   2.63%
  engine residual             2183.4 ms   4.55%

attention_core_light:
  attention total                         11352.3 ms
  linear core total                        2890.1 ms
  linear core decode non-spec              2680.0 ms
  linear source method nested sum          5570.1 ms

Important:
  attention source-method rows are nested diagnostic counters.
  Do not add them together or treat them as production timing shares.
```

Updated priority:

```text
P0:
  shared expert gate linear:
    output gate is a named source component and should be investigated as a
    low-overhead fused/combined linear opportunity, not through aux-stream force.

P0:
  engine residual:
    needs lower-level vLLM engine/sampler/logits breakdown under production-like
    or minimally intrusive timing.

P1:
  attention/GDN core:
    current Python method wrapper localizes the target but is too intrusive;
    next measurement should move to lower-overhead operator/kernel-level timing.

Deprioritized:
  descriptor_order/direct_topk/forced shared aux as default runtime wins:
    all have useful safety/negative evidence, but current production-like
    performance evidence does not support default enablement.
```
## AWQ Real Bottleneck Refocus

Status: 2026-05-12, GPU1 AWQ/vLLM decode diagnostics.

The descriptor-order / direct-topk line is now bounded:

```text
descriptor_order:
  correctness-safe and useful as shadow / diagnostic evidence

direct_topk:
  correctness-safe, but not a robust default runtime win

WNA16-only tuning:
  locally useful, but Amdahl-limited for end-to-end TPOT
```

The current performance work has therefore moved back to the larger realistic
latency targets:

```text
1. attention / GDN core
2. shared expert gate linear / shared direct layer
3. engine / scheduler / sampling / logits residual
```

Current consolidated artifact:

- `outputs/reports/awq_telemetry_ladder/gpu1_attention_core_light_fixed_smoke8/real_bottlenecks.json`
- `outputs/reports/awq_telemetry_ladder/gpu1_attention_core_light_fixed_smoke8/real_bottlenecks.md`

Telemetry contract:

```text
production_like:
  TPOT/generate baseline only; no attribution

diagnostic_light:
  coarse decoder/MoE/shared attribution; not a production TPOT claim.
  This may include coarse `experts_shared_*` timing, but not shared-expert
  source split.

attention_core_light:
  linear/GDN source-method attribution only; diagnostic-only due to wrapper overhead

decoder_layer_only:
  low-intrusion decoder total timing; no component/MoE substage rows

shared_expert_light:
  shared-expert substage/source split only. It has no decoder component timing,
  no generic MoE substages, and no copied `apply_source_*` fused-experts split.
  This is the next entry point for shared W1 / activation / shared W2 /
  output gate attribution.
```

Key evidence from the consolidated report:

```text
production_like TPOT:
  0.072913 s/token

diagnostic_light TPOT:
  0.093705 s/token
  +28.52% overhead vs production_like

attention_core_light TPOT:
  0.094191 s/token
  +29.18% overhead vs production_like

decoder_layer_only:
  decoder layer = 38653.766 ms
  engine residual = 2482.547 ms
  engine residual share = 6.03%
```

Diagnostic-light bottlenecks, with the diagnostic-overhead caveat:

```text
attention:
  10920.885 ms
  22.76% of diagnostic generate

MLP/MoE:
  29110.857 ms
  60.68% of diagnostic generate

MoE apply:
  14008.596 ms
  29.20% of diagnostic generate

shared expert direct:
  7731.285 ms
  16.11% of diagnostic generate

shared expert output gate:
  1259.454 ms
  2.63% of diagnostic generate
```

Attention-core diagnostic evidence:

```text
attention total:
  11352.312 ms

linear/GDN core total:
  2890.054 ms

linear/GDN decode non-spec:
  2680.032 ms

linear source method nested sum:
  5570.086 ms
```

Important boundary:

```text
attention_core_light rows are nested diagnostic counters.
Do not add them together.
Do not treat them as production timing shares.
```

The previously observed fused-expert source residuals were calibrated away as
diagnostic artifacts:

```text
impl_total - inner source parts:
  explained by source event emission overhead

outer_impl_call - impl_total:
  explained by entry / event boundary overhead

W1/W2 dispatch gap:
  real but small; not the P0 optimization target
```

Shared-expert-light smoke:

- `outputs/reports/awq_telemetry_ladder/gpu1_shared_expert_light_smoke8/`
- `outputs/reports/awq_telemetry_ladder/gpu1_shared_expert_light_smoke8/shared_expert_light/repeat_00/decode_breakdown.md`

```text
production_like:
  TPOT = 0.074150 s/token

shared_expert_light:
  TPOT = 0.092216 s/token
  overhead ~= 24.36%
  diagnostic-only

shared direct layer:
  634.145 ms
  10.745% of diagnostic generate

shared W1/gate-up:
  106.066 ms
  1.797% of diagnostic generate

shared activation:
  53.740 ms
  0.911% of diagnostic generate

shared W2/down:
  99.918 ms
  1.693% of diagnostic generate

shared output gate:
  145.011 ms
  2.457% of diagnostic generate

shared output sigmoid/mul:
  45.386 ms
  0.769% of diagnostic generate

shared direct source parts sum:
  450.120 ms

shared direct minus source parts:
  184.024 ms
```

Interpretation:

```text
shared_expert_light successfully names the shared expert compute pieces, but
it has substantial diagnostic overhead and should not be used for production
TPOT claims.

The largest named shared pieces in this smoke are the shared output gate and
the shared W1/W2 projections. The remaining shared direct residual still needs
lower-intrusion attribution before optimization work.
```

Filtered shared-expert-light smoke:

- `outputs/reports/awq_telemetry_ladder/gpu1_shared_expert_filtered_smoke8/`
- `outputs/reports/awq_telemetry_ladder/gpu1_shared_expert_filtered_smoke8/shared_expert_light/repeat_00/decode_breakdown.md`

Implementation change:

```text
moe_source_timing_mode=shared:
  emits only `experts_shared_*` substage rows
  filters out generic MoE substages such as select/dispatch/quant_method.apply
  keeps copied `apply_source_*` fused-experts split disabled
```

Evidence:

```text
production_like:
  TPOT = 0.076544 s/token

shared_expert_light filtered:
  TPOT = 0.084007 s/token
  overhead ~= 9.75%

line_count:
  38400

moe_substage_timing rows:
  33280

previous unfiltered shared_expert_light:
  TPOT = 0.092216 s/token
  line_count = 99840
  moe_substage_timing rows = 94720
```

Filtered shared source decode attribution:

```text
shared direct layer:
  622.069 ms

shared W1/gate-up:
  100.698 ms

shared activation:
  51.842 ms

shared W2/down:
  96.012 ms

shared output gate:
  139.873 ms

shared output sigmoid/mul:
  44.794 ms

shared direct source parts sum:
  433.219 ms

shared direct minus source parts:
  188.850 ms
```

Interpretation:

```text
Filtering generic MoE substages makes shared_expert_light a much lower
intrusion diagnostic path, reducing the observed TPOT overhead from roughly
24% to roughly 10% on this smoke. It remains diagnostic-only, but is now a
practical entry point for shared W1/W2/gate attribution.
```

Engine-light smoke:

- `outputs/reports/awq_telemetry_ladder/gpu1_engine_light_smoke8/`
- `outputs/reports/awq_telemetry_ladder/gpu1_engine_light_smoke8/engine_light/repeat_00/decode_breakdown.md`

Implementation:

```text
engine_light:
  emit_decoder_layer_timing=true
  emit_engine_timing=true
  emit_decoder_component_timing=false
  emit_moe_substage_timing=false
  decoder_source_timing_mode=off
  moe_source_timing_mode=off
```

Evidence:

```text
production_like:
  TPOT = 0.070999 s/token

engine_light:
  TPOT = 0.072208 s/token
  overhead ~= 1.70%
  line_count = 5768
  engine_substage_timing rows = 648
```

Engine-light attribution:

```text
generate:
  4621.336 ms

decoder layer:
  3592.244 ms
  77.732% of engine_light generate

generate - decoder layer:
  1029.092 ms

engine execute_model:
  4541.431 ms

engine model_forward:
  4428.495 ms

engine logits processor:
  27.907 ms

engine sample_tokens:
  33.252 ms

engine sampler forward:
  4.943 ms

engine sampler sample:
  1.626 ms

engine bookkeeping sync:
  2.188 ms

engine prepare_inputs:
  39.438 ms

engine preprocess:
  0.643 ms
```

Interpretation:

```text
engine_light has low enough overhead for coarse engine attribution.
Logits processing, sampling, and bookkeeping are small in this smoke and do
not explain the full generate-minus-decoder-layer residual. Most remaining
time is either model-forward wrapper / scheduler-side time outside the layer
hooks, or other vLLM engine work not yet split below execute_model.

The engine rows are nested: execute_model contains model_forward and logits;
sample_tokens contains sampler/bookkeeping. Do not add them as independent
shares.
```

Current next gates:

```text
P0:
  split shared expert direct/gate path with low-intrusion hooks:
    shared W1/gate projection
    activation
    shared W2/down projection
    output gate/combine
    wrapper residual

  Implementation note:
    use `moe_source_timing_mode=shared` / telemetry ladder mode
    `shared_expert_light`. Shared expert source split is now explicitly gated
    off for production_like, decoder_layer_only, and diagnostic_light. Generic
    MoE substage rows are filtered out in `shared_expert_light` to reduce
    diagnostic overhead.

P0:
  split attention/GDN core into production-adjacent source buckets:
    qkv / input projection
    linear/GDN core
    layout unpack
    output projection
    wrapper residual

P0:
  split engine residual below decoder layer:
    logits / lm_head
    sampling
    scheduler / engine loop
    output processing
    CPU-GPU synchronization

P1:
  only after the larger buckets are explained, revisit WNA16 and direct_topk as
  local MoE-path micro-optimizations.
```

Validation commands:

```bash
conda run -n TRY pytest tests/test_run_awq_telemetry_ladder_modes.py \
  tests/test_summarize_awq_real_bottlenecks.py -q

python -m py_compile src/mtp_expert_prefetch/tracing/vllm_router_trace.py \
  scripts/run_awq_telemetry_ladder.py \
  scripts/summarize_awq_real_bottlenecks.py
```

### 2026-05-12: Deep engine residual split

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_engine_light_deep_smoke8/
```

Configuration:

```text
GPU: 1
samples: 8
requested output tokens: 64
modes:
  production_like
  engine_light
```

End-to-end overhead check:

```text
production_like:
  generate_wall_seconds = 4.603129
  TPOT = 0.071924 s

engine_light:
  generate_wall_seconds = 4.453092
  TPOT = 0.069580 s
```

The deep engine timing path does not introduce a visible positive overhead in
this smoke. Treat the result as diagnostic attribution, not a production TPOT
claim.

Breakdown:

```text
generate total / engine llm.generate call:
  4453.092 ms

engine execute_model:
  4378.441 ms

engine model_forward:
  4267.750 ms

execute_model - model_forward:
  110.691 ms

generate - execute_model:
  74.650 ms

engine logits processor:
  26.851 ms

engine sample_tokens:
  31.361 ms

engine sampler forward:
  4.549 ms

engine sampler sample:
  1.433 ms

engine bookkeeping sync:
  1.958 ms

engine prepare_inputs:
  37.998 ms

engine attention metadata:
  18.736 ms

engine update_states:
  9.867 ms
```

The analyzer now emits these engine residuals as first-class table rows:

```text
engine execute_model minus model_forward:
  110.691 ms

engine llm.generate minus execute_model:
  74.650 ms
```

Interpretation:

```text
generate - execute_model is small in this smoke.
execute_model - model_forward is also modest and mostly explained by
prepare_inputs, attention metadata, logits processor, sample_tokens, and
update/bookkeeping scale work.

Sampler and logits are not the large residual:
  logits processor is ~0.60% of generate
  sample_tokens is ~0.70% of generate
  sampler forward + sampler sample is ~0.13% of generate

The remaining large unoptimized mass is inside model_forward / decoder layers,
not scheduler/output processing.
```

Boundary:

```text
engine_* rows are nested host-wall counters.
execute_model contains model_forward/logits/sample-side engine work.
sample_tokens contains sampler/bookkeeping.
Do not add nested engine rows as independent shares.
```

Current implication:

```text
Do not prioritize sampler/output processing as the next performance target.
Continue with model_forward-internal buckets:
  attention/GDN core
  shared expert direct/gate path
  decoder residual / non-MoE layer work
```

### 2026-05-13: model-forward internal next-target smoke

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_core_shared_next_smoke8/
```

Configuration:

```text
GPU: 1
samples: 8
requested output tokens: 64
modes:
  production_like
  diagnostic_light
  attention_core_light
  shared_expert_light
```

TPOT:

```text
production_like:
  0.076353 s/token

diagnostic_light:
  0.088418 s/token
  overhead vs production_like: +15.80%

attention_core_light:
  0.086636 s/token
  overhead vs production_like: +13.47%

shared_expert_light:
  0.085681 s/token
  overhead vs production_like: +12.22%
```

Diagnostic-light decode attribution:

```text
decoder layer:
  4491.666 ms
  79.38% of diagnostic generate

attention:
  1340.151 ms
  23.68% of diagnostic generate

MLP/MoE:
  2525.432 ms
  44.63% of diagnostic generate

MoE apply:
  1399.732 ms
  24.74% of diagnostic generate

decoder outside attention+MLP residual:
  626.083 ms
```

Attention-core diagnostic:

```text
attention total:
  1334.079 ms

linear/GDN core total:
  345.389 ms

linear/GDN core decode non-spec:
  320.826 ms

linear source-method nested sum:
  666.215 ms
```

Boundary:

```text
attention_core_light is diagnostic-only. The method-wrapper overhead is too
large for production TPOT claims, but it localizes the linear/GDN core as a
real model-forward-internal target.
```

Shared-expert diagnostic:

```text
shared no-overlap:
  711.050 ms

shared direct layer:
  663.110 ms

shared direct source parts sum:
  461.496 ms

shared direct minus source parts:
  201.614 ms

shared W1/gate-up:
  108.224 ms

shared activation:
  55.689 ms

shared W2/down:
  101.865 ms

shared output gate:
  148.815 ms

shared output sigmoid/mul:
  46.903 ms
```

Interpretation:

```text
The largest named shared-expert sub-bucket is the output gate path, followed by
shared W1/W2. The remaining shared direct residual is still diagnostic and may
include wrapper/source-boundary overhead.
```

### 2026-05-13: shared auxiliary stream negative smoke

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_shared_aux_stream_smoke8/
```

Production-like TPOT:

```text
production_like:
  0.071803 s/token

production_like_force_shared_aux:
  0.075800 s/token
  overhead vs production_like: +5.57%
```

Diagnostic-light TPOT:

```text
diagnostic_light:
  0.084741 s/token

diagnostic_light_force_shared_aux:
  0.088096 s/token
  overhead vs diagnostic_light: +3.96%
```

Diagnostic interpretation:

```text
Forcing the shared expert auxiliary stream is not a profitable default.
The forced path increases shared stream synchronization cost and does not
produce a net production-like TPOT improvement in this GPU1 smoke.
```

Current implication:

```text
Do not pursue forced shared-aux stream as the default shared-expert
optimization.

Next shared-expert targets should be lower-level:
  shared output gate
  shared W1/W2 direct path
  direct-layer residual / wrapper overhead
```

Tooling update:

```text
scripts/summarize_awq_real_bottlenecks.py now accepts:
  --shared-expert-breakdown

This keeps shared_expert_light source-split fields in the consolidated
real_bottlenecks report instead of leaving shared gate/W1/W2 blank when the
coarse diagnostic_light run does not emit source-level shared expert rows.
```

Regenerated summary:

```text
outputs/reports/awq_telemetry_ladder/gpu1_core_shared_next_smoke8/real_bottlenecks.md
```

Current summary highlights:

```text
shared direct layer:
  663.110 ms

shared direct source parts:
  461.496 ms

shared direct minus source parts:
  201.614 ms

shared W1/gate-up:
  108.224 ms

shared activation:
  55.689 ms

shared W2/down:
  101.865 ms

shared output gate:
  148.815 ms

shared output sigmoid/mul:
  46.903 ms
```

Validation:

```bash
conda run -n TRY pytest -q
# 225 passed, 2 warnings
```

Validation:

```bash
conda run -n TRY pytest -q
# 225 passed, 2 warnings

conda run -n TRY python scripts/run_awq_telemetry_ladder.py \
  --output-root outputs/reports/awq_telemetry_ladder/gpu1_engine_light_deep_smoke8 \
  --modes production_like engine_light \
  --max-samples 8 --max-tokens 8 --start-sample 128 \
  --gpu 1 --conda-env TRY

conda run -n TRY python scripts/analyze_awq_decode_breakdown.py \
  outputs/reports/awq_telemetry_ladder/gpu1_engine_light_deep_smoke8/engine_light/repeat_00 \
  --output-json outputs/reports/awq_telemetry_ladder/gpu1_engine_light_deep_smoke8/engine_light/repeat_00/decode_breakdown.json \
  --output-md outputs/reports/awq_telemetry_ladder/gpu1_engine_light_deep_smoke8/engine_light/repeat_00/decode_breakdown.md
```

### 2026-05-13: shared output gate diagnostic upper-bound ablation

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_shared_gate_ablation_smoke8/
```

Modes:

```text
production_like:
  telemetry-minimal baseline

shared_expert_light:
  shared expert source split enabled

shared_gate_ablation:
  diagnostic-only source split with shared expert output gate forced to unity
```

TPOT:

```text
production_like:
  0.068122 s/token

shared_expert_light:
  0.079932 s/token

shared_gate_ablation:
  0.077354 s/token
  improvement vs shared_expert_light: ~3.2%
```

Shared expert source split:

```text
shared_expert_light:
  shared direct layer:              622.840 ms
  shared direct source parts:       433.773 ms
  shared direct minus source parts: 189.067 ms
  shared W1 / gate-up:              101.579 ms
  shared activation:                 51.636 ms
  shared W2 / down:                  96.312 ms
  shared output gate:               139.889 ms
  shared output sigmoid/mul:         44.357 ms

shared_gate_ablation:
  shared direct layer:              425.505 ms
  shared output gate:                 0.774 ms
  shared output sigmoid/mul:          0.509 ms
```

Interpretation:

```text
The shared output gate is a real cost center in the shared expert path.
Skipping it gives an upper-bound diagnostic reduction inside the source-split
wrapper, but it changes model semantics and is not a valid runtime
optimization.

The deployable direction is therefore not "skip the gate"; it is either:
  fuse/streamline the expert_gate linear + sigmoid/mul path, or
  move on to the next real bottleneck if fusion is not feasible.
```

Current boundary:

```text
shared_gate_ablation is diagnostic-only.
It must not be used for correctness or performance claims beyond showing the
upper-bound cost of the shared output gate.
```

### 2026-05-13: shared gate in-place postprocess diagnostic

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_shared_gate_inplace_smoke8/
```

Modes:

```text
production_like
shared_expert_light
shared_gate_inplace
```

`shared_gate_inplace` keeps the expert gate enabled and only changes the
postprocess from:

```python
out = torch.sigmoid(gate_out) * out
```

to:

```python
gate_out.sigmoid_()
out.mul_(gate_out)
```

TPOT:

```text
production_like:
  0.070866 s/token

shared_expert_light:
  0.079278 s/token

shared_gate_inplace:
  0.079338 s/token
```

Decode shared source split:

```text
shared_expert_light:
  shared direct layer:        624.193 ms
  shared output gate:         139.400 ms
  shared output sigmoid/mul:   45.400 ms

shared_gate_inplace:
  shared direct layer:        611.629 ms
  shared output gate:         139.684 ms
  shared output sigmoid/mul:   35.174 ms
```

Interpretation:

```text
In-place gate postprocess removes roughly 10 ms from the decode
sigmoid/multiply substage in this source-split diagnostic, but it does not
improve TPOT and does not address the dominant shared output gate linear.

Therefore the shared gate path should not be pursued through Python-level
postprocess tweaks.  Any deployable shared-gate improvement would need a lower
level fused expert_gate linear + sigmoid/mul implementation, or the work should
move to the next real bottleneck such as attention/GDN core.
```

### 2026-05-13: attention/GDN core deep split

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_attention_core_deep_smoke8/
```

Mode update:

```text
attention_core_deep:
  decoder_source_timing_mode=attention_core_deep
  record_router_topk=false
  moe_source_timing_mode=off
```

This diagnostic mode keeps the existing attention core method timing and adds
GDN decode fast-path leaf timings for:

```text
attention_linear_core_conv_update
attention_linear_core_recurrent
```

TPOT:

```text
production_like:
  0.071586 s/token

attention_core_light:
  0.084753 s/token
  overhead vs production_like: +18.39%

attention_core_deep:
  0.085537 s/token
  overhead vs production_like: +19.49%
  overhead vs attention_core_light: +0.93%
```

Decode GDN/linear attention core:

```text
attention_core_light:
  attention_linear_core_total:           345.484 ms
  attention_linear_core_decode_non_spec: 321.888 ms

attention_core_deep:
  attention_linear_core_total:           374.856 ms
  attention_linear_core_decode_non_spec: 360.640 ms
  attention_linear_core_conv_update:     132.684 ms
  attention_linear_core_recurrent:       121.216 ms
```

Interpretation:

```text
attention_core_deep is diagnostic-only but low incremental overhead over
attention_core_light.  The GDN decode fast path is split between convolution
state update and recurrent gated-delta rule; neither is the sole dominant leaf.

The next attention-side work should inspect kernel/source options for both
causal_conv1d_update and fused_recurrent_gated_delta_rule_packed_decode rather
than assuming a single core kernel bottleneck.
```

### 2026-05-13: packed recurrent production-like toggle

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_packed_recurrent_toggle_smoke8/
```

Scope note:

```text
This older smoke and the newer
outputs/reports/awq_telemetry_ladder/gpu1_attention_gdn_prod_ab_8sample_decode/
both agree on the direction: disabling packed recurrent decode is slower.
The exact regression percentage differs across code/config snapshots
(+16.10% here, +5.41% in the newer telemetry-minimal run), so use them as
consistent negative evidence for disabling the packed path rather than a
single stable percentage.
```

Modes:

```text
production_like:
  default VLLM_ENABLE_FLA_PACKED_RECURRENT_DECODE=1

production_like_no_packed_recurrent:
  VLLM_ENABLE_FLA_PACKED_RECURRENT_DECODE=0
```

TPOT:

```text
production_like:
  0.072446 s/token

production_like_no_packed_recurrent:
  0.084108 s/token
  overhead vs production_like: +16.10%
```

Interpretation:

```text
The packed recurrent decode fast path is required for this AWQ/GPU1 setting.
Disabling it is clearly negative under production-like telemetry.

Therefore the recurrent side should not be optimized by falling back to the
generic path.  Any future recurrent optimization must tune or specialize the
existing packed recurrent Triton kernel.
```

### 2026-05-13: GDN recurrent and conv-update launch-meta microbench

Artifacts:

```text
outputs/reports/awq_telemetry_ladder/gdn_recurrent_microbench_gpu1_smoke.json
outputs/reports/awq_telemetry_ladder/gdn_conv_update_microbench_gpu1_smoke.json
```

Shape:

```text
batch=8
GDN heads: H=16, HV=32
K=128, V=128
conv dim=8192, kernel width=4
dtype=bf16, state_dtype=fp32
GPU=1
```

Packed recurrent sweep:

```text
vLLM default:
  BV=32, num_warps=1, num_stages=3
  median: 52.042 us
  mean:   53.366 us
  p90:    58.321 us

best observed:
  BV=64, num_warps=4, num_stages=3
  median: 51.901 us
  mean:   53.006 us
  p90:    55.561 us
```

Conv-update sweep:

```text
vLLM default:
  BLOCK_N=256, num_warps=1, num_stages=2
  median: 38.575 us
  mean:   40.812 us
  p90:    47.700 us

best observed:
  BLOCK_N=256, num_warps=1, num_stages=2
  median: 38.575 us
  mean:   40.812 us
  p90:    47.700 us
```

Interpretation:

```text
The current vLLM launch meta is already near-optimal for both GDN decode leaf
kernels under the tested AWQ/GPU1 shape.  The packed recurrent best median is
only ~0.27% faster than the default, and the conv-update default is the best
observed candidate.

This rules out simple Triton launch-meta tuning as the next high-ROI path for
attention/GDN.  Further performance work should move up a level: attention/GDN
dataflow, kernel fusion opportunities, or engine/logits/output residuals.
```

### 2026-05-13: engine/logits/sampler residual refresh

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_engine_residual_refresh_smoke8/
```

Modes:

```text
production_like
engine_light
```

TPOT:

```text
production_like:
  0.074534 s/token

engine_light:
  0.075862 s/token
  overhead vs production_like: +1.78%
```

Engine-light breakdown:

```text
generate total:                         4855.190 ms
engine llm.generate call:               4855.190 ms
engine execute_model:                   4773.734 ms
engine model_forward:                   4650.602 ms

engine execute_model - model_forward:    123.132 ms  (2.536% generate)
engine llm.generate - execute_model:      81.456 ms  (1.678% generate)

engine update_states:                    11.789 ms
engine attention metadata:               21.437 ms
engine logits processor:                 26.102 ms
engine sample_tokens:                    34.606 ms
engine sampler forward:                   5.627 ms
engine sampler sample:                    1.891 ms
engine bookkeeping sync:                  2.847 ms

decode decoder layer total:            3788.145 ms  (78.023% generate)
decode MoE layer apply:                1176.606 ms  (24.234% generate)
```

Interpretation:

```text
The engine/logits/sampler residual is not the current primary bottleneck under
low-intrusion engine timing.  The gap outside model_forward is small:
execute_model-model_forward is ~2.5% of generate and generate-execute_model is
~1.7%.

Logits processing and sampling are both sub-1% in this smoke.  Further endpoint
work should focus inside model_forward, especially decoder-layer attention/GDN
and shared expert paths, not scheduler/sampler/output processing.
```

### 2026-05-13: shared expert output-gate fusion microbench

Artifact:

```text
outputs/reports/awq_telemetry_ladder/shared_gate_fused_microbench_gpu1_smoke.json
```

Diagnostic target:

```text
baseline:
  gate = sigmoid(hidden @ shared_expert_gate_weight)
  out = out * gate

fused:
  one Triton program per token computes gate projection,
  sigmoid, and output multiply for hidden_size=2048
```

GPU1 best-by-batch:

```text
batch=1:
  baseline best: 146.720 us
  fused best:     28.740 us
  speedup:        5.11x

batch=2:
  baseline best: 149.900 us
  fused best:     17.940 us
  speedup:        8.36x

batch=4:
  baseline best: 157.740 us
  fused best:     18.420 us
  speedup:        8.56x

batch=8:
  baseline best: 148.620 us
  fused best:     28.760 us
  speedup:        5.17x

batch=16:
  baseline best: 157.820 us
  fused best:     18.140 us
  speedup:        8.70x

batch=32:
  baseline best: 153.940 us
  fused best:     18.020 us
  speedup:        8.54x
```

Correctness:

```text
max_abs_diff <= 0.015625 across the sweep
```

Interpretation:

```text
This is the first strong local positive signal after the GDN leaf-kernel meta
sweeps.  The shared expert output gate is a real model-forward cost, and its
current decomposition uses a small dense gate projection plus separate sigmoid
/ multiply work.  A narrow fused kernel avoids that launch/dataflow overhead for
decode-sized batches.

This is still a standalone microbench, not a vLLM runtime speedup claim.  The
next gate is a runtime smoke that replaces only the shared output gate
postprocess with the fused semantic-equivalent path and compares correctness
plus TPOT against production_like/shared_expert_light.
```

### 2026-05-13: shared fused output-gate runtime smoke

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_shared_gate_fused_smoke8/
```

Modes:

```text
production_like
shared_expert_light
shared_gate_fused
```

TPOT:

```text
production_like:
  0.069995 s/token

shared_expert_light:
  0.077736 s/token

shared_gate_fused:
  0.078370 s/token
```

Source breakdown:

```text
shared_expert_light:
  decode MoE layer apply:             1094.989 ms
  shared direct layer:                 606.586 ms
  shared output gate:                  135.647 ms
  shared output sigmoid/mul:            43.341 ms
  shared direct source parts sum:      419.234 ms

shared_gate_fused:
  decode MoE layer apply:             1073.591 ms
  shared direct layer:                 543.881 ms
  shared output fused gate:            149.156 ms
  shared direct source parts sum:      385.075 ms
```

Interpretation:

```text
The fused gate runtime path is semantically connected and locally reduces the
measured shared direct layer and MoE apply source buckets.  However, the
diagnostic TPOT does not improve; shared_gate_fused is slightly slower than
shared_expert_light in this smoke.

Therefore the current fused gate patch is a local source-level positive signal,
not an endpoint performance win.  It should remain diagnostic until a
telemetry-minimal or production-like integration proves TPOT improvement.
```

### 2026-05-13: shared fused output-gate telemetry-minimal A/B

Artifacts:

```text
outputs/reports/awq_telemetry_ladder/gpu1_shared_gate_fused_minimal_smoke8/
outputs/reports/awq_telemetry_ladder/gpu1_shared_gate_fused_minimal_32sample/
outputs/reports/awq_telemetry_ladder/gpu1_shared_gate_fused_minimal_smoke8_repeats/
```

Scope note:

```text
These are older runtime-smoke artifacts from the first fused-gate patch.
The newer telemetry-minimal A/B at
outputs/reports/awq_telemetry_ladder/gpu1_shared_gate_prod_ab_8sample_decode/
is the current smoke for this code state and shows no gain for
shared_gate_fused_minimal.  Treat the older positive 8-sample result as an
unstable signal, not as the current conclusion.
```

8-sample single run:

```text
production_like:
  0.073101 s/token

shared_gate_fused_minimal:
  0.069743 s/token
  speedup vs production_like: ~4.59%
```

32-sample single run:

```text
production_like:
  0.069369 s/token

shared_gate_fused_minimal:
  0.070306 s/token
  regression vs production_like: ~1.35%
```

8-sample 3-repeat summary:

```text
production_like:
  TPOT values: [0.069953, 0.073003, 0.073433]
  median: 0.073003
  mean:   0.072130

shared_gate_fused_minimal:
  TPOT values: [0.075161, 0.071907, 0.070506]
  median: 0.071907
  mean:   0.072525
```

Interpretation:

```text
The fused shared output gate is not yet a stable endpoint win.  It has a strong
standalone microbench signal and reduces local source buckets under diagnostic
timing, but TPOT is noisy: the 8-sample single run is positive, 32-sample is
negative, and 8-sample repeats are mixed.

Keep the patch as an experimental/diagnostic mode.  Do not enable it by default
or claim runtime speedup without a larger, telemetry-minimal heldout run showing
stable TPOT improvement.
```

### 2026-05-13: attention/GDN dataflow refresh

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_attention_dataflow_refresh_smoke8/
```

Modes:

```text
production_like
attention_source
attention_core_deep
```

TPOT:

```text
production_like:
  0.073138 s/token

attention_source:
  0.094080 s/token
  overhead vs production_like: +28.63%

attention_core_deep:
  0.085687 s/token
  overhead vs production_like: +17.16%
```

Attention source breakdown:

```text
decode attention total:        1631.217 ms
decode MoE layer apply:        1398.622 ms
outside attention+MLP:          607.579 ms

linear input proj:              102.243 ms
linear BA proj:                  80.195 ms
linear norm:                    184.135 ms
linear core total:              355.110 ms
linear core decode non-spec:    332.070 ms
linear out proj:                 96.610 ms

full attention core:            148.140 ms
full qk norm:                   115.407 ms
full qkv proj:                   34.632 ms
full o proj:                     33.451 ms
```

Attention core deep breakdown:

```text
decode attention total:        1346.798 ms
decode MoE layer apply:        1347.171 ms

linear core total:              373.734 ms
linear core decode non-spec:    359.330 ms
conv update:                    131.525 ms
packed recurrent:               120.823 ms
```

Interpretation:

```text
The attention/GDN path is a broader dataflow cost, not a single leaf-kernel
meta-tuning target.  Conv update and packed recurrent are material leaf costs,
but both launch-meta sweeps showed little/no simple tuning headroom.  The
surrounding linear-attention projection/norm/out-proj path is also substantial.

Next attention-side work should inspect semantic-preserving fusion/dataflow
opportunities around GDN projections/norm/core handoff, or validate whether
full-attention qk_norm/core contributes a separate optimization target.  Do not
claim production shares from attention_source directly; its hook overhead is
diagnostic-only.
```

### 2026-05-15: low-intrusion attention core handoff telemetry

Implemented `attention_core_handoff_light` as a lower-intrusion alternative to
`attention_source` / `attention_core_deep`.

Captured buckets:

```text
attention_linear_handoff_linear_proj_total
attention_linear_handoff_norm
attention_linear_handoff_core_total
attention_linear_handoff_core_decode_non_spec
attention_linear_handoff_conv_update
attention_linear_handoff_recurrent
attention_linear_handoff_core_post_layout
attention_linear_handoff_out_proj
```

Analyzer-derived bucket:

```text
attention_linear_handoff_core_prep_layout
  = core_decode_non_spec - conv_update - recurrent
```

Safety/interpretation:

```text
core_prep_layout and core_post_layout are nested residual diagnostics, not
independent additive costs.  The analyzer now reports negative-residual anomaly
flags for both derived buckets.
```

Validation:

```text
python -m py_compile scripts/analyze_awq_decode_breakdown.py \
  scripts/run_awq_telemetry_ladder.py \
  src/mtp_expert_prefetch/tracing/vllm_router_trace.py

python -m pytest tests/test_analyze_awq_decode_breakdown.py \
  tests/test_run_awq_telemetry_ladder_modes.py -q
  -> 20 passed

python -m pytest -q
  -> 233 passed, 2 warnings
```

GPU smoke status:

```text
TRY env:
  blocked before model execution by vLLM C extension ABI mismatch:
  vllm._C undefined symbol and torch.ops._C.silu_and_mul not registered.

MTP env:
  vLLM C op check passes, but vLLM import is blocked by zstandard C API
  mismatch through transformers/torchao/torch.distributed.checkpoint.

Both failures occur in production_like before the new attention mode runs, so
they are environment blockers rather than evidence against
attention_core_handoff_light.
```

Retry after permission update:

```text
Added an explicit smoke-only fallback gate:
  MTP_PATCH_MISSING_VLLM_ACTIVATION_OPS=1
  or runtime_shadow.patch_missing_vllm_activation_ops=true

Fallbacks currently cover:
  torch.ops._C.silu_and_mul
  torch.ops._C.gelu_and_mul
  torch.ops._moe_C.topk_softmax
  torch.ops._moe_C.topk_sigmoid

Manifest marks such runs with:
  runtime_shadow_patch_missing_vllm_activation_ops
  runtime_shadow_patched_missing_vllm_activation_ops
  trace_fallback_mode=vllm_activation_and_topk_ops
```

The fallback moved TRY past model construction and router top-k, but the next
missing op is:

```text
torch.ops._moe_C.moe_align_block_size
```

Stop line:

```text
Do not keep expanding Python fallbacks to cover moe_align_block_size or WNA16
dispatch.  At that point the smoke would no longer validate the real AWQ/vLLM
path.  Restore a working vLLM/MoE C extension environment before collecting the
attention_core_handoff_light GPU table.
```

Environment repair:

```text
TRY env vLLM was rebuilt from a fresh /tmp clone against the active
torch 2.12.0+rocm7.2 environment.

Build source:
  /tmp/vllm_try_rebuild

Build/install env:
  TMPDIR=/tmp/vllm_rebuild_tmp
  TORCH_EXTENSIONS_DIR=/tmp/torch_extensions_try_vllm
  MAX_JOBS=128
  VLLM_TARGET_DEVICE=rocm
  PYTORCH_ROCM_ARCH=gfx1100
```

Installed vLLM:

```text
vllm 0.21.1rc1.dev3+g95cfe102a.rocm720
```

Post-rebuild ABI/op check passes:

```text
import vllm._C ok
import vllm._rocm_C ok
import vllm._moe_C ok
torch.ops._C.silu_and_mul = true
torch.ops._C.gelu_and_mul = true
torch.ops._moe_C.topk_softmax = true
torch.ops._moe_C.topk_sigmoid = true
torch.ops._moe_C.moe_align_block_size = true
```

Compatibility fixes for vLLM 0.21.1:

```text
MoERunner._forward_impl and _apply_quant_method now accept input_ids.
BaseRouter.select_experts / _compute_routing also accept input_ids.

The trace wrappers now:
  - accept *extra_args / **extra_kwargs where vLLM signatures drifted
  - convert a first optional positional input_ids into a signature-filtered kwarg
  - preserve remaining optional positional args
  - use quant_method / _quant_method fallback
  - short-circuit the no-recorder/no-extra hot path
```

Validation:

```text
python -m pytest -q
  -> 233 passed, 2 warnings

GPU1 AWQ smoke:
  scripts/run_awq_telemetry_ladder.py
    --modes production_like attention_core_handoff_light
    --max-samples 1 --max-tokens 1 --start-sample 128

production_like:
  returncode = 0

attention_core_handoff_light:
  returncode = 0
  runtime_shadow.jsonl lines = 1430
```

Interpretation:

```text
The TRY environment blocker is resolved for real AWQ/vLLM smoke runs.
The earlier Python activation/top-k fallback is no longer needed for this path
and remains smoke-only diagnostic machinery.

The current 1-sample / 1-token run is an environment and hook sanity check,
not a performance table.  The next performance step is a GPU1 8-sample decode
run with attention_core_handoff_light and the standard analyzer.
```

GPU1 8-sample attention handoff decode table:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_attention_core_handoff_light_8sample_decode/

config:
  max_samples = 8
  max_tokens = 64
  start_sample = 128
  GPU = 1
  modes = production_like, attention_core_handoff_light
```

Run status:

```text
production_like:
  returncode = 0
  requested_output_token_count = 512
  generate_wall_seconds = 40.3548
  TPOT = 0.07882 s/output token

attention_core_handoff_light:
  returncode = 0
  runtime_shadow.jsonl lines = 777520
  requested_output_token_count = 512
  generate_wall_seconds = 51.7077
  TPOT = 0.10099 s/output token
  overhead vs production_like = 28.13%
```

Analyzer artifacts:

```text
attention_core_handoff_light_breakdown.json
attention_core_handoff_light_breakdown.md
```

Decode attribution from the handoff run:

```text
generate total                         51.708 s  100.0%
decode decoder layer total             48.836 s   94.4%
decode attention                       15.975 s   30.9%
decode MLP/MoE block                   27.329 s   52.9%
decode MoE layer apply                 16.139 s   31.2%
decode outside attention+MLP residual   5.533 s   10.7%
generate minus decode decoder layer     2.871 s    5.6%
```

Low-intrusion attention handoff buckets:

```text
linear_proj_total        1.542 s   2.98% generate
norm                     1.567 s   3.03%
core_prep_layout         1.528 s   2.95%
conv_update              1.182 s   2.29%
recurrent                1.113 s   2.15%
core_post_layout         0.134 s   0.26%
out_proj                 0.838 s   1.62%
```

Boundary:

```text
attention_core_handoff_light is diagnostic-only and writes a large shadow log.
The +28% TPOT overhead is instrumentation overhead, not model runtime behavior.

This mode intentionally does not enable source-level fused_experts split or
WNA16 GPU-event timing, so zero WNA16 GPU-event rows in this artifact are a
configuration boundary, not evidence that WNA16 is absent.
```

Attention handoff aggregate logger:

```text
Implementation:
  - Added decoder_component_logging_mode.
  - rows: existing per-event decoder_component_timing behavior.
  - attention_handoff_aggregate: aggregate attention_linear_handoff_* buckets
    into per request/layer/phase decoder_component_aggregate rows.
  - Analyzer now maps decoder_component_aggregate sum_us back into the same
    decode_attention_linear_handoff_* sums_us fields.

Scope:
  - Aggregate mode is sample/layer/phase telemetry, not token-level telemetry.
  - Non-handoff decoder components still emit normal decoder_component_timing rows.
```

GPU1 8-sample attention aggregate ladder:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_attention_handoff_aggregate_8sample_decode/

config:
  max_samples = 8
  max_tokens = 64
  start_sample = 128
  GPU = 1
  modes = production_like, attention_total_only, attention_core_handoff_aggregate
```

Run status:

```text
production_like:
  returncode = 0
  generate_wall_seconds = 35.2852
  TPOT = 0.06892 s/output token
  runtime_shadow rows = 0

attention_total_only:
  returncode = 0
  generate_wall_seconds = 37.3278
  TPOT = 0.07291 s/output token
  overhead vs production_like = 5.79%
  runtime_shadow rows = 81920

attention_core_handoff_aggregate:
  returncode = 0
  generate_wall_seconds = 40.2618
  TPOT = 0.07864 s/output token
  overhead vs production_like = 14.10%
  runtime_shadow rows = 82400
  decoder_component_aggregate rows = 480
  aggregated handoff component events = 122160
```

Analyzer artifacts:

```text
attention_core_handoff_aggregate_breakdown.json
attention_core_handoff_aggregate_breakdown.md
```

Aggregate decode attribution:

```text
generate total                         40.262 s  100.0%
decode decoder layer total             38.018 s   94.4%
decode attention                       13.146 s   32.7%
decode MLP/MoE block                   19.141 s   47.5%
decode MoE layer apply                 11.001 s   27.3%
decode outside attention+MLP residual   5.730 s   14.2%
generate minus decode decoder layer     2.244 s    5.6%
```

Aggregate attention handoff buckets:

```text
linear_proj_total        1.516 s   3.77% generate
norm                     1.537 s   3.82%
core_prep_layout         0.844 s   2.10%
conv_update              1.163 s   2.89%
recurrent                1.103 s   2.74%
core_post_layout         0.104 s   0.26%
out_proj                 0.815 s   2.02%
```

Boundary:

```text
Aggregate mode cuts the full attention handoff diagnostic overhead roughly in
half: +14.1% TPOT vs +28.1% for full rows on a comparable 8-sample GPU1 run.
It is still diagnostic attribution, not a production performance claim.

The remaining overhead is dominated by decoder layer/component summary rows and
attention wrapper timing, not by per-handoff JSONL firehose.
```

Validation:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest -q
237 passed, 2 warnings
```

Attention handoff counter/no-write attribution:

```text
Implementation:
  - Added attention_handoff_aggregate_no_write:
    aggregate with the existing dict payload path, then drop aggregate rows at
    flush. Non-handoff decoder_component_timing rows remain enabled.
  - Added attention_handoff_counter_only:
    fixed component-id arrays for attention_linear_handoff_* sums/counts, then
    flush the same decoder_component_aggregate schema.
  - Added attention_handoff_counter_only_no_write:
    fixed-array aggregation with aggregate rows dropped at flush.
  - Unknown future attention_linear_handoff_* components no longer disappear:
    counter_only writes them as decoder_component_timing fallback rows, while
    counter_only_no_write drops them to preserve the no-write ablation semantics.
```

GPU1 8-sample counter/no-write ladder:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/
    gpu1_attention_counter_8sample_decode/

config:
  max_samples = 8
  max_tokens = 64
  start_sample = 128
  GPU = 1
```

Run status:

```text
production_like:
  generate = 37.411 s
  TPOT = 0.07307
  overhead = 0.00%
  rows = 0

attention_total_only:
  generate = 37.851 s
  TPOT = 0.07393
  overhead = +1.18%
  rows = 81920

attention_core_handoff_aggregate:
  generate = 41.056 s
  TPOT = 0.08019
  overhead = +9.74%
  rows = 82400
  decoder_component_aggregate rows = 480
  aggregated handoff component events = 122160

attention_core_handoff_aggregate_no_write:
  generate = 39.822 s
  TPOT = 0.07778
  overhead = +6.45%
  rows = 81920

attention_core_handoff_counter_only:
  generate = 41.165 s
  TPOT = 0.08040
  overhead = +10.03%
  rows = 82400
  decoder_component_aggregate rows = 480
  aggregated handoff component events = 122160

attention_core_handoff_counter_only_no_write:
  generate = 39.904 s
  TPOT = 0.07794
  overhead = +6.66%
  rows = 81920
```

Analyzer artifacts:

```text
attention_core_handoff_counter_only_breakdown.json
attention_core_handoff_counter_only_breakdown.md
```

Interpretation:

```text
counter_only does not materially beat dict aggregate in this Python hook path.
aggregate vs no_write differs by about 3.3 percentage points, so JSONL flush of
the aggregate rows is not the dominant cost.

The main remaining attention handoff overhead is per-call Python wrapper /
recorder entry and handoff timing itself.  To reduce overhead further, the
next step should move aggregation closer to the wrapper boundary or sample
attention handoff diagnostics, rather than adding more handoff subevents.
```

Validation:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest -q
243 passed, 2 warnings
```

Attention timing policy after overhead attribution:

```text
production_like:
  TPOT/generate performance baseline.

attention_total_only:
  low-intrusion coarse diagnostic mode.
  Current GPU1 8-sample overhead is about +1.18%.
  This is the only attention timing mode suitable for routine diagnostic ladders.

attention_core_handoff_aggregate:
  diagnostic-only internal attribution.
  Current GPU1 8-sample overhead is about +9.74%.

attention_core_handoff_*_no_write:
  cost attribution only.
  It shows that aggregate JSONL write is not the main bottleneck.

full-row handoff / handoff counter experiments:
  debug-only; do not use for long runs or performance claims.
```

Hard conclusion:

```text
Attention handoff-level instrumentation is dominated by per-call Python wrapper,
recorder, and timing overhead.

Further work should not optimize dict-vs-counter aggregation or add more handoff
subevents.  If attention internals still need attribution, use coarser
source-level regions such as:

  attention_forward
  linear projections
  core attention
  output projection

The event count target should be samples × layers × 3-5 regions, not per-handoff
call counts.
```

## 2026-05-15 shared-expert native stream disable A/B

Question:

```text
After excluding custom shared gate postprocess as a negative path, test whether
vLLM's native shared-experts auxiliary stream is actually beneficial for the
current AWQ/W7900 decode workload.
```

Patch hygiene:

```text
scripts/run_awq_telemetry_ladder.py now supports mode-level unset_env.

production_like and production_like_force_shared_aux explicitly remove:
  VLLM_DISABLE_SHARED_EXPERTS_STREAM

production_like_disable_shared_stream explicitly sets:
  VLLM_DISABLE_SHARED_EXPERTS_STREAM=1

This avoids contaminating the baseline if the parent shell already has the
disable flag set.
```

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_shared_stream_disable_ab_repeats_8sample_decode/
```

Config:

```text
GPU = 1
max_samples = 8
max_tokens = 64
start_sample = 128
repeats = 3
record_router_topk = false
source timing = off
shadow summaries/outcomes = off
```

Results:

```text
production_like TPOT:
  repeat0 = 0.074559
  repeat1 = 0.074309
  repeat2 = 0.074071
  mean    = 0.074313

production_like_disable_shared_stream TPOT:
  repeat0 = 0.068383
  repeat1 = 0.071360
  repeat2 = 0.071741
  mean    = 0.070495

mean delta:
  -5.14% TPOT vs production_like
```

Interpretation:

```text
This is an 8-sample production-like smoke signal for disabling the native
shared expert auxiliary stream on GPU1 AWQ decode.

It is not evidence for the custom shared gate / fused gate patches; those remain
negative or diagnostic-only.  This A/B only tests vLLM's native shared-experts
stream policy through the upstream environment flag.
```

Boundary:

```text
The signal is repeat-stable at 8 samples but still needs 32/128-sample
confirmation before being treated as a runtime default.

If confirmed, the next optimization target is the shared direct body / model
forward dataflow around native stream scheduling, not Python-level gate
postprocess fusion.
```

Validation:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest tests/test_run_awq_telemetry_ladder_modes.py -q
18 passed
```

Follow-up 32-sample gate:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_shared_stream_disable_ab_32sample_decode/

production_like:
  TPOT = 0.070881
  generate = 145.165 s

production_like_disable_shared_stream:
  TPOT = 0.072027
  generate = 147.512 s

delta:
  +1.62% TPOT vs production_like
```

Updated conclusion:

```text
The 8-sample positive signal does not survive the 32-sample validation.

Disabling vLLM's native shared-experts stream should not become a default
runtime optimization.  Keep it as a conditional diagnostic knob only.

The shared direct body / model-forward dataflow line should move away from
Python-level gate postprocess and single-knob stream toggles, and toward broader
model-forward attribution or lower-level shared expert kernel/body changes.
```

Validation after env-hygiene test updates:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest tests/test_run_awq_telemetry_ladder_modes.py -q
20 passed
```

## 2026-05-15 engine/model-forward residual 32-sample check

Question:

```text
After shared-stream disable failed the 32-sample gate, check whether the next
large target is outside model_forward, e.g. scheduler / engine loop / logits /
sampler / output processing.
```

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_engine_light_32sample_decode/
```

Run status:

```text
production_like:
  TPOT = 0.070179
  generate = 143.726 s

engine_light:
  TPOT = 0.073184
  generate = 149.882 s
  overhead = +4.28% vs production_like
```

Engine-light breakdown:

```text
generate total:
  149.882 s

engine_execute_model:
  148.821 s

engine_model_forward:
  146.361 s

engine_execute_model - engine_model_forward:
  2.460 s
  1.64% of generate

engine_generate_call - engine_execute_model:
  1.061 s
  0.71% of generate

logits processor:
  0.130 s

sample_tokens:
  0.560 s

sampler forward:
  0.170 s

attention metadata:
  0.461 s

prepare_inputs:
  1.110 s
```

Decoder closure:

```text
decode decoder_layer sum:
  140.393 s

prefill decoder_layer sum:
  3.142 s

all decoder_layer sum:
  143.535 s

model_forward - all decoder_layer:
  2.826 s
  1.89% of generate
```

Interpretation:

```text
The high-level engine/output/sampler residual is small in this 32-sample run.

Most time is still inside model_forward and specifically inside decoder layers.
This argues against spending P0 effort on scheduler/output/sampler for this AWQ
decode configuration.

The next useful low-intrusion direction is not more engine timing; it is a
coarse model_forward/decoder-internal split that avoids handoff/source-event
pollution:

  decoder attention total
  decoder MLP/MoE total
  shared expert direct body
  quant apply total
  residual norms / layer scales

Use production_like for endpoint TPOT and keep engine_light as diagnostic-only.
```

## 2026-05-15 decoder-internal coarse attribution attempt

Goal:

```text
Return to decoder-internal coarse attribution after ruling out scheduler/sampler
as P0 targets.

Desired buckets:
  attention total
  MLP/MoE total
  shared expert direct body
  quant apply total
  norm / layer-scale residual

Avoid:
  attention handoff events
  WNA16 GPU-event sync
  record_topk
  full source timing
```

Attempt 1: `decoder_coarse_light`

```text
mode:
  decoder_source_timing_mode = qwen3_5
  moe_source_timing_mode = shared

artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_decoder_coarse_light_8sample_decode/

result:
  production_like TPOT = 0.072568
  decoder_coarse_light TPOT = 0.096243
  overhead = +32.6%
```

Conclusion:

```text
Rejected as too intrusive.

Even though it is coarser than attention handoff, the qwen3_5 decoder source
path still enters source-copy / decoder-source reconstruction and is not a
low-intrusion routine attribution mode.
```

Attempt 2: `decoder_component_light`

```text
mode:
  decoder_source_timing_mode = off
  decoder_component_logging_mode = rows
  moe_source_timing_mode = shared
  record_router_topk = false
  WNA16 timing = off

artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_decoder_component_light_8sample_decode/

result:
  production_like TPOT = 0.074709
  decoder_component_light TPOT = 0.086738
  overhead = +16.1%
```

Coarse diagnostic buckets from decoder_component_light:

```text
generate:
  44.410 s

decode decoder layer:
  42.189 s

decode attention:
  11.578 s

decode MLP/MoE:
  24.215 s

decode MoE apply:
  11.344 s

decode MLP/MoE - MoE apply:
  12.871 s

decode outside attention+MLP residual:
  6.396 s

shared expert direct layer:
  6.572 s

shared W1:
  0.983 s

shared W2:
  0.922 s

shared activation:
  0.490 s

shared output gate:
  1.378 s

shared sigmoid/mul:
  0.443 s

shared direct minus source parts:
  2.356 s
```

Interpretation:

```text
decoder_component_light avoids qwen3_5 source-copy and attention handoff, but
still emits many per-layer/per-token MoE shared substage rows.  Its +16.1%
overhead is too high for long-run attribution.

The useful finding is directional:
  MLP/MoE remains larger than attention.
  shared direct body is a sizeable chunk.
  MLP/MoE residual outside measured MoE apply is still large.

Next gate:
  replace row-level shared MoE substages with aggregate counters or sampled
  short diagnostics before running 32/128 samples.
```

Validation:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest tests/test_run_awq_telemetry_ladder_modes.py -q
23 passed
```

## 2026-05-16 shared MoE substage aggregate/sampled attribution

Goal:

```text
Reduce the decoder_component_light overhead by replacing row-level shared MoE
substage rows with aggregate and sampled aggregate telemetry.
```

Implementation:

```text
VllmRouterRecorder:
  shadow_moe_substage_logging_mode:
    rows
    aggregate
    sampled_aggregate
    shared_sampled_aggregate

  shadow_moe_substage_sample_period:
    default 1

Aggregate event:
  event_type = moe_substage_aggregate
  token_index = -1
  key = request / sequence / layer / phase / num_tokens

Sampled aggregate fields:
  raw_sum_us      = sampled raw elapsed sum
  sum_us          = period-scaled time estimate
  count           = sampled event count
  estimated_count = period-scaled count estimate
  status_counts / estimated_status_counts
  sample_period

Analyzer:
  uses sum_us for time estimates
  uses estimated_count / estimated_status_counts for integrity counters
```

Code review:

```text
Spark review found no blockers.
Follow-up fixes:
  sampling now only applies to sampled_aggregate / shared_sampled_aggregate
  analyzer no longer treats sampled count as the true event count
  shared_sampled_aggregate has a two-substage regression test
```

Validation:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest \
  tests/test_vllm_router_shadow_sink.py::test_moe_substage_aggregate_flushes_per_layer_phase_bucket \
  tests/test_vllm_router_shadow_sink.py::test_moe_substage_sampled_aggregate_scales_decode_samples \
  tests/test_analyze_awq_decode_breakdown.py::test_decode_breakdown_reads_moe_substage_aggregate \
  tests/test_analyze_awq_decode_breakdown.py::test_decode_breakdown_reads_sampled_moe_substage_aggregate_counts \
  tests/test_run_awq_telemetry_ladder_modes.py::test_decoder_component_sampled_light_samples_shared_moe_substages -q
5 passed

/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest \
  tests/test_vllm_router_shadow_sink.py -k 'shared_sampled_aggregate or sampled_aggregate_scales' -q
3 passed
```

GPU1 AWQ decode results:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_decoder_component_sampled_light_8sample_decode/

8 samples:
  production_like TPOT = 0.077507
  sampled_light TPOT   = 0.082622
  overhead             = +6.60%
  runtime_shadow rows  = 82,560

artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_decoder_component_sampled_light_32sample_decode/

32 samples:
  production_like TPOT = 0.076577
  sampled_light TPOT   = 0.084727
  overhead             = +10.64%
  runtime_shadow rows  = 330,240

artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_decoder_component_sampled_light_128sample_decode/

128 samples:
  production_like TPOT = 0.074642
  sampled_light TPOT   = 0.084793
  overhead             = +13.60%
  runtime_shadow rows  = 1,297,760
```

128-sample sampled attribution:

```text
generate:
  694.623 s

decode decoder layer:
  647.309 s

decode attention:
  192.478 s

decode MLP/MoE:
  358.791 s

decode MoE apply:
  189.989 s

decode MLP/MoE - MoE apply:
  168.802 s

outside attention+MLP residual:
  96.040 s

shared expert direct layer:
  100.740 s

shared W1:
  16.562 s

shared W2:
  15.160 s

shared activation:
  8.168 s

shared output gate:
  23.038 s

shared sigmoid/mul:
  7.359 s

shared direct minus source parts:
  30.454 s
```

Conclusion:

```text
Aggregate/sampled telemetry reduces log volume and is useful for short
diagnostic attribution, but it is still not a production-like timing path.

The 8/32/128 sampled overhead is roughly +6.6% / +10.6% / +13.6%.
This confirms that the remaining overhead is dominated by per-substage timing
entry/exit and Python wrapper cost, not JSONL row volume.

Use production_like for endpoint performance claims.
Use decoder_component_sampled_light only for bounded diagnostic attribution.
The stable direction remains:
  MLP/MoE > attention as the larger decoder block
  shared expert direct/output-gate path is a real MoE-side target
  further shared substage detail needs lower-level or coarser source timing,
  not more Python per-call telemetry.
```

## 2026-05-16 shared direct body coarse attribution

Motivation:

```text
Do not keep expanding shared substage Python hooks.
Move to a lower-intrusion coarse mode that preserves:
  decoder layer total
  attention total
  MLP/MoE total
  MoE apply total
  shared direct body total

and drops:
  shared W1 / W2 / activation / output-gate per-substage Python events
```

Implementation:

```text
new mode:
  moe_source_timing_mode = shared_body

aliases:
  shared_direct
  shared_coarse

filter:
  only experts_shared_direct_layer is allowed
  experts_shared_w1 / w2 / activation / output_gate are filtered out

execution:
  when source_timing_enabled is false, the shared direct body calls
  self._layer(shared_experts_input) instead of _run_shared_layer_with_source_split
```

Validation:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest \
  tests/test_vllm_router_shadow_sink.py::test_moe_substage_shared_body_mode_only_records_direct_layer \
  tests/test_vllm_router_shadow_sink.py::test_moe_substage_shared_body_aliases_only_record_direct_layer \
  tests/test_run_awq_telemetry_ladder_modes.py::test_decoder_shared_body_light_records_only_coarse_shared_body -q
4 passed

Spark review:
  no blocker
  confirmed shared_body does not re-enable W1/W2/activation/output-gate source split
```

GPU1 AWQ decode results:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_decoder_shared_body_light_8sample_decode/

8 samples:
  production_like TPOT      = 0.074768
  decoder_shared_body TPOT  = 0.076927
  overhead                  = +2.89%
  runtime_shadow rows       = 82,560

artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_decoder_shared_body_light_32sample_decode/

32 samples:
  production_like TPOT      = 0.074339
  decoder_shared_body TPOT  = 0.078369
  overhead                  = +5.42%
  runtime_shadow rows       = 330,240
```

32-sample coarse attribution:

```text
generate:
  160.500 s

decode decoder layer:
  149.576 s

decode attention:
  46.134 s

decode MLP/MoE:
  80.508 s

decode MoE apply:
  45.727 s

decode MLP/MoE - MoE apply:
  34.781 s

outside attention+MLP residual:
  22.934 s

shared expert direct layer:
  15.611 s
```

Conclusion:

```text
decoder_shared_body_light is the preferred coarse diagnostic mode over
decoder_component_sampled_light.

It preserves the main decoder/MoE attribution buckets while avoiding shared
substage source split.  Its 8/32 overhead is +2.9% / +5.4%, versus
sampled-substage +6.6% / +10.6% / +13.6%.

Use:
  decoder_shared_body_light for low-intrusion coarse attribution.

Avoid:
  shared W1/W2/activation/output-gate Python substage hooks except for small
  bounded debug runs.

Next useful direction:
  if more detail is needed, instrument fewer lower-level body regions inside
  the shared direct implementation, not per-substage Python wrapper hooks.
```

## 2026-05-16 shared expert production-like variant gate

Goal:

```text
Evaluate shared-direct optimization candidates under a production-like endpoint
TPOT口径, without decoder/source timing or shared region hooks.

This checks whether the previously identified shared-direct coarse bucket has a
low-risk runtime knob before doing deeper source-level optimization.
```

Artifact:

```text
outputs/reports/awq_telemetry_ladder/gpu1_shared_production_variants_128sample_gen64/
```

Run:

```text
GPU: 1
samples: 128
max_tokens: 64
start_sample: 128
modes:
  production_like
  production_like_force_shared_aux
  production_like_disable_shared_stream
  shared_gate_inplace_minimal
  shared_gate_fused_minimal
```

Results:

| mode | TPOT_s | generate_s | overhead_vs_prod |
|---|---:|---:|---:|
| production_like | 0.071041 | 581.968 | +0.00% |
| production_like_force_shared_aux | 0.073246 | 600.030 | +3.10% |
| production_like_disable_shared_stream | 0.070338 | 576.207 | -0.99% |
| shared_gate_inplace_minimal | 0.073730 | 603.996 | +3.79% |
| shared_gate_fused_minimal | 0.073289 | 600.387 | +3.16% |

Interpretation:

```text
Shared output-gate postprocess variants are not profitable:
  inplace:      +3.79% TPOT
  fused_triton: +3.16% TPOT

Forcing the aux-stream shared path is also negative:
  force_aux:    +3.10% TPOT

Disabling the shared-experts stream is the only positive signal:
  disable_stream: -0.99% TPOT
```

Conclusion:

```text
Do not pursue shared gate postprocess fusion as a runtime speedup path based on
this AWQ/W7900 artifact.

The only remaining shared-direct knob worth a small follow-up is stream policy:
disable_shared_stream shows a small positive signal in the single-pass
128-sample artifact, but it needs repeat / split validation before becoming a
default.

In the separate low-intrusion coarse baseline for this AWQ/W7900 setup,
shared direct was observed as a stable coarse bucket near 10% of generate time:

  outputs/reports/awq_telemetry_ladder/gpu1_low_intrusion_coarse_baseline_128sample_gen64/

The low-risk postprocess variants in this artifact do not convert that bucket
into endpoint speedup.
```

Validation gap:

```text
This production-like variant run reports endpoint timing only.  It does not yet
provide a formal generated-text / logits parity table for each variant.

Before enabling any shared-stream policy by default, require:
  1. repeat >= 3 on the same split,
  2. independent heldout prompt split,
  3. median TPOT improvement > 1% with no p95 / p99 regression,
  4. generated-text hash parity or an explicit tolerated-difference report,
  5. unchanged routing / model configuration metadata.

Until that gate passes:
  production_like_disable_shared_stream is a small positive signal only,
  not a default runtime optimization.

Current status:
  this artifact does not satisfy the default-enablement gate.  It is only a
  precursor observation for deciding whether a more expensive validation run is
  worthwhile.

Implementation gap:
  this ladder currently reports endpoint TPOT / generate wall time.  A helper
  still needs to extract per-sample or per-step p95 / p99 latency from raw trace
  artifacts before the p95 / p99 gate can be checked automatically.
```

Single-pass artifact reproduction command:

```bash
/home/husrcf/anaconda3/bin/conda run -n TRY \
  python scripts/run_awq_telemetry_ladder.py \
  --base-config configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_attr_no_order_gpu1_decode_heldout128_gen8_diagnostic_off.yaml \
  --output-root outputs/reports/awq_telemetry_ladder/gpu1_shared_production_variants_128sample_gen64 \
  --max-samples 128 \
  --max-tokens 64 \
  --start-sample 128 \
  --gpu 1 \
  --modes production_like production_like_force_shared_aux production_like_disable_shared_stream shared_gate_inplace_minimal shared_gate_fused_minimal \
  --continue-on-error
```

Fast same-split repeat smoke:

```bash
/home/husrcf/anaconda3/bin/conda run -n TRY \
  python scripts/run_awq_telemetry_ladder.py \
  --base-config configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_attr_no_order_gpu1_decode_heldout128_gen8_diagnostic_off.yaml \
  --output-root outputs/reports/awq_telemetry_ladder/gpu1_shared_disable_stream_repeat3_32sample_gen64 \
  --max-samples 32 \
  --max-tokens 64 \
  --start-sample 128 \
  --gpu 1 \
  --repeats 3 \
  --modes production_like production_like_disable_shared_stream \
  --continue-on-error
```

This 32-sample repeat is only a quick smoke for variance.  It later measured a
neutral / slightly slower median delta (+0.26%), so it is not sufficient as the
final validation gate.

Full same-split repeat validation template:

```bash
/home/husrcf/anaconda3/bin/conda run -n TRY \
  python scripts/run_awq_telemetry_ladder.py \
  --base-config configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_attr_no_order_gpu1_decode_heldout128_gen8_diagnostic_off.yaml \
  --output-root outputs/reports/awq_telemetry_ladder/gpu1_shared_disable_stream_repeat3_128sample_gen64 \
  --max-samples 128 \
  --max-tokens 64 \
  --start-sample 128 \
  --gpu 1 \
  --repeats 3 \
  --modes production_like production_like_disable_shared_stream \
  --continue-on-error
```

Alternate-offset smoke template:

```bash
/home/husrcf/anaconda3/bin/conda run -n TRY \
  python scripts/run_awq_telemetry_ladder.py \
  --base-config configs/trace/router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_attr_no_order_gpu1_decode_heldout128_gen8_diagnostic_off.yaml \
  --output-root outputs/reports/awq_telemetry_ladder/gpu1_shared_disable_stream_repeat3_32sample_gen64_altstart256 \
  --max-samples 32 \
  --max-tokens 64 \
  --start-sample 256 \
  --gpu 1 \
  --repeats 3 \
  --modes production_like production_like_disable_shared_stream \
  --continue-on-error
```

The alternate-offset template changes only the dataset offset inside the same
configured dataset source.  It is not a replacement for an independently
curated heldout prompt split.

Default-enablement checklist:

```text
[partial] same-source repeat:
  fast 32-sample repeat smoke completed; full 128-sample repeat template exists
  but has not been executed.

[not covered] independent heldout prompt split:
  source-offset smoke is exploratory only and does not satisfy this gate.
  A separate heldout prompt config / prompt file still needs to be created and
  referenced explicitly in a validation command.

[not covered] p95 / p99 regression:
  needs a helper to extract per-sample or per-step latency distributions from
  raw trace artifacts.

[not covered] output parity:
  needs generated-text hash or tolerated-difference reporting for each
  shared-stream variant.

[partial] routing / model config unchanged:
  current artifacts record runtime_shadow and model-path metadata, but the final
  gate summary must explicitly list model path / model hash, base config path or
  hash, runtime_shadow option hash, and any environment overrides.
```

Fast same-split repeat smoke result:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_shared_disable_stream_repeat3_32sample_gen64/

repeat summary:
  outputs/reports/awq_telemetry_ladder/gpu1_shared_disable_stream_repeat3_32sample_gen64/repeat_summary.json
  outputs/reports/awq_telemetry_ladder/gpu1_shared_disable_stream_repeat3_32sample_gen64/repeat_summary.md

production_like TPOT:
  repeat0: 0.071752
  repeat1: 0.072255
  repeat2: 0.073346
  median:  0.072255
  mean:    0.072451

production_like_disable_shared_stream TPOT:
  repeat0: 0.072083
  repeat1: 0.072825
  repeat2: 0.072443
  median:  0.072443
  mean:    0.072450

median delta:
  +0.26% vs production_like
```

Interpretation:

```text
The 32-sample repeat smoke does not reproduce the single-pass 128-sample
disable_stream positive signal.  Its median is slightly slower and its mean is
essentially identical to baseline.

Current evidence is therefore conflicting and sample-sensitive:
  128-sample single pass: disable_stream shows a small positive signal
  32-sample repeat smoke: disable_stream is neutral / slightly slower

This is enough to keep disable_stream out of the default runtime path, but not
enough to claim it is universally negative.  The current operational stance is:
  keep default vLLM shared-stream behavior for runtime
  use shared_body_total_only for coarse attribution
  keep shared gate / force-aux / disable-stream variants as diagnostic evidence
  until full repeat + independent heldout + parity gates are available
```

Helper:

```text
scripts/summarize_telemetry_ladder_repeats.py

reports:
  per-mode TPOT values / median / mean / min / max / stdev
  sample_timing_count / sample_p50 / sample_p95 / sample_p99 when
    sample_timing.jsonl is present
  candidate median_delta_vs_baseline
  candidate mean_delta_vs_baseline
  candidate p95_delta / p99_delta when both baseline and candidate have
    sample_timing.jsonl
  median_gate_pass
  final_gate_pass for the statistical gate; if --require-parity is set, the
    gate also requires externally supplied parity evidence via --parity-available
  excluded_failed_rows
  invalid_rows for invalid_mode / missing_returncode / invalid_returncode /
    missing_tpot-or-nonfinite-tpot / missing_context_field /
    invalid_context_value / invalid_sample_timing_json
  context_consistent for sample_count / requested_output_token_count
  repeat_count_gate_pass

explicit non-goal:
  it does not infer p95 / p99 latency from endpoint TPOT.
  tail-latency fields come only from explicit scope=sample rows in
    sample_timing.jsonl.
```

Trace support for future tail-latency gates:

```text
src/mtp_expert_prefetch/tracing/vllm_router_trace.py now writes:
  sample_timing.jsonl

sample-mode rows:
  scope = sample
  sample_idx
  record_id
  input_tokens
  requested_output_tokens
  generate_elapsed_us
  trace_write_elapsed_us
  status

chunk-mode rows:
  scope = chunk
  chunk_start
  sample_indices
  sample_count
  requested_output_tokens
  generate_elapsed_us
  status

The repeat helper only uses exact scope=sample rows for p50/p95/p99. Chunk rows
are retained for audit but are not converted into per-sample tail latency.
```

GPU1 sample-timing smoke:

```text
artifact:
  outputs/reports/awq_telemetry_ladder/gpu1_sample_timing_smoke1_gen1/

run:
  max_samples = 1
  max_tokens = 1
  mode = production_like

sample_timing.jsonl:
  scope: sample
  sample_idx: 128
  requested_output_tokens: 1
  generate_elapsed_us: 190064.302
  trace_write_elapsed_us: 541.148

repeat summary:
  sample_timing_count = 1
  sample_p50 = sample_p95 = sample_p99 = 0.190064 s/token
```

Validation:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest \
  tests/test_summarize_telemetry_ladder_repeats.py -q
13 passed

/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest \
  tests/test_summarize_telemetry_ladder_repeats.py \
  tests/test_run_awq_telemetry_ladder_modes.py \
  tests/test_summarize_awq_real_bottlenecks.py -q
49 passed
```

## 2026-05-17: Dolly Prefetch Action Replay Input Smoke

Goal:

```text
Replicate the AYA512 production-like prefetch action replay on an external
Dolly prompt split before strengthening the MTP admission claim.
```

Current status:

```text
AYA512 replay:
  normal envelope: complete
  stress envelope: complete
  claim gate: partial pass

Dolly128 replay:
  prefix127 normal + stress replay complete
  sample_000001 input-generation smoke passed end-to-end
```

Key finding:

```text
AWQ/vLLM true-router trace-build configs must keep:

  trace.runtime_shadow.record_router_topk = true

The vLLM hook records select_experts top-k into the trace payload only when this
flag is enabled.  This is acceptable for offline trace construction, but these
configs must not be used as production-like TPOT benchmarks.  Performance
benchmark configs should keep record_router_topk=false.
```

Artifacts:

```text
AutoRound/native-MTP smoke:
  data/traces/external_prompt_gate_dolly_128_autoround_smoke_sample1/manifest.jsonl

AWQ/vLLM true-router smoke:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_smoke_sample1/manifest.jsonl
  router_topk modules: 40
  router_weights modules: 40
  router_call_meta rows: 40

Merged trace:
  data/traces/external_prompt_gate_dolly_128_merged_mtp_vllm_smoke_sample1/manifest.jsonl

MTP token sidecar:
  data/traces/mtp_token_topm_external_prompt_gate_dolly_128_prefc_fixed_smoke_sample1/manifest.jsonl

Prefc-fixed merged trace:
  data/traces/external_prompt_gate_dolly_128_merged_mtp_vllm_prefc_fixed_smoke_sample1/manifest.jsonl

Tensor-cache probe:
  outputs/reports/prefetch_action_replay/dolly128_smoke_sample1_tensor_cache_build_probe.json
  outputs/reports/prefetch_shadow_dolly_128_mtp_extra_smoke_sample1/event_stall_tensor_cache_dolly128_smoke_sample1.pt
```

Smoke result:

```text
simulate_prefetch_event_stalls.py:
  ok = true
  num_eval_token_examples = 22
  num_layers = 40
  transition_topk = 32
  tensor cache written
```

Boundary:

```text
sample_000000 is not valid replay evidence because the prompt consumed the
max_model_len=128 budget and produced an empty AWQ/vLLM router payload.
sample_000001 is the current valid smoke for the external-prompt input chain.
```

Next:

```text
Done for the prefix127 split.  See the Dolly Prefix127 Production-Like Action
Replay section below for the full evidence chain.
```

## 2026-05-17: Dolly Prefix127 Production-Like Action Replay

Status:

```text
complete for prefix127 split
```

Input construction:

```text
Full AutoRound/native-MTP trace:
  data/traces/external_prompt_gate_dolly_128_autoround/manifest.jsonl
  rows = 128

Full AWQ/vLLM true-router trace:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode/manifest.jsonl
  rows = 128
  non-empty router_topk = 128 / 128
  router modules per sample = 40

Filtered replay split:
  original source_sample_idx=12 excluded due AutoRound/AWQ token-prefix divergence
  filtered sample_idx values are renumbered after exclusion
  retained samples = 127 / 128

Prefix127 manifests:
  data/traces/external_prompt_gate_dolly_128_autoround_prefix127/manifest.jsonl
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_prefix127/manifest.jsonl

Merged + prefc-fixed inputs:
  data/traces/external_prompt_gate_dolly_128_prefix127_merged_mtp_vllm/manifest.jsonl
  data/traces/mtp_token_topm_external_prompt_gate_dolly_128_prefix127_prefc_fixed/manifest.jsonl
  data/traces/external_prompt_gate_dolly_128_prefix127_merged_mtp_vllm_prefc_fixed/manifest.jsonl
```

Tensor cache:

```text
outputs/reports/prefetch_shadow_dolly_128_prefix127_mtp_extra/event_stall_tensor_cache_dolly128_prefix127.pt

num_eval_token_examples = 3217
num_layers = 40
token_layer_count = 128,680
```

Normal envelope:

```text
report:
  outputs/reports/prefetch_action_replay/dolly128_prefix127_production_like_action_replay_normal.json

summary:
  outputs/reports/prefetch_action_replay/dolly128_prefix127_production_like_action_replay_normal_claim_gate.md

bandwidth_gbps = 6.589
action_cost_overlap_factor = 0.8
admission_capacity_per_layer = 160

transition_ready:
  ready_mass = 0.7155
  top1_hit = 0.8347
  weighted_top1_miss = 0.0403

utility_keep50:
  stall_reduction = 7.20%
  extra_issued = 0.408 TB
  saved_fetches = 24,912
  used_per_extra_byte = 0.101
  full_fetch = 247,242
  metadata = 164,953
  premap = 210,502
  metadata_net_ms = -147.11
  premap_net_ms = 18.95
```

Stress envelope:

```text
report:
  outputs/reports/prefetch_action_replay/dolly128_prefix127_production_like_action_replay_stress.json

summary:
  outputs/reports/prefetch_action_replay/dolly128_prefix127_production_like_action_replay_stress_claim_gate.md

bandwidth_gbps = 3.0
action_cost_overlap_factor = 0.0
downgrade_full_fetch_ready_threshold = 1.10

utility_keep50:
  stall_reduction = 0.00%
  extra_issued = 0.000 TB
  full_fetch = 0
  metadata = 413,238
  premap = 209,203
  metadata_net_ms = -8342.26
  premap_net_ms = -240.49
```

Interpretation:

```text
Dolly prefix127 reproduces the AYA qualitative claim gate:
  normal envelope: gated MTP extras improve local stall/readiness proxy.
  stress envelope: full_fetch shuts down completely and transition_top32 is preserved.

This upgrades the claim from AYA-only to partial pass across AYA512 and an
external Dolly prompt split.

Still not supported:
  endpoint TPOT speedup
  real DMA/cache-manager benefit
  metadata default enablement
  premap default enablement under stress
```

## 2026-05-17: Prefetch Amdahl Upper-Bound Mapping

Artifact:

```text
outputs/reports/prefetch_action_replay/aya512_dolly_prefix127_amdahl_upper_bound.md
outputs/reports/prefetch_action_replay/aya512_dolly_prefix127_amdahl_upper_bound.json
```

Tool:

```text
scripts/map_prefetch_amdahl.py
tests/test_map_prefetch_amdahl.py
```

Component shares:

```text
source:
  outputs/reports/awq_telemetry_ladder/gpu1_low_intrusion_coarse_baseline_128sample_gen64/real_bottleneck_summary.json

MoE apply share = 28.40%
MLP/MoE share  = 49.06%
```

Conservative MoE-apply endpoint upper bound:

```text
AYA512 utility_keep50:
  local stall reduction = 7.61%
  endpoint saved share  = 2.16%
  endpoint speedup upper = 2.21%

Dolly prefix127 utility_keep50:
  local stall reduction = 7.20%
  endpoint saved share  = 2.05%
  endpoint speedup upper = 2.09%
```

Boundary:

```text
This is not endpoint TPOT evidence.  It maps replay-local stall-proxy reduction
onto measured component shares to bound the best possible endpoint effect.

Use MoE-apply mapping as the conservative upper bound.  MLP/MoE mapping is an
optimistic ceiling and should not be used as a direct runtime claim.
```

Validation:

```text
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest \
  tests/test_map_prefetch_amdahl.py \
  tests/test_summarize_prefetch_claim_gate.py \
  tests/test_build_evidence_manifest.py \
  tests/test_prefetch_pareto_summary.py -q

9 passed
```

## 2026-05-18: Prefetch Cache Lab Replay

Goal:

```text
Move from action-level stall proxy to a controlled cache/fetch-manager lab
replay before considering a real runtime prefetch manager.
```

Implementation:

```text
scripts/run_prefetch_cache_lab.py
scripts/summarize_prefetch_cache_lab.py
tests/test_prefetch_cache_lab.py
tests/test_summarize_prefetch_cache_lab.py
```

Boundary:

```text
bounded-cache lab replay only
not endpoint TPOT
not a real vLLM cache-manager implementation
```

Core model:

```text
cache key:
  (layer, expert)

demand stream:
  target_mass > 0 from existing event-stall tensor cache

cache manager:
  bounded LRU over expert payloads

costs:
  demand miss -> demand_stall_us
  prefetch issue -> prefetch_dma_us
  optional manager / lookup / decision costs
```

Artifacts:

```text
outputs/reports/prefetch_action_replay/dolly128_prefix127_cache_lab_normal.json
outputs/reports/prefetch_action_replay/dolly128_prefix127_cache_lab_normal_capacity10240.json
outputs/reports/prefetch_action_replay/dolly128_prefix127_cache_lab_stress_capacity10240.json
outputs/reports/prefetch_action_replay/aya512_cache_lab_normal_capacity2048.json
outputs/reports/prefetch_action_replay/aya512_cache_lab_normal_capacity10240.json
outputs/reports/prefetch_action_replay/aya512_cache_lab_stress_capacity10240.json
outputs/reports/prefetch_action_replay/aya512_dolly_prefix127_cache_lab_summary.md
```

Key result:

```text
capacity=2048:
  Dolly utility_keep50 net_saved_ms_vs_transition = -16,840
  AYA utility_keep50 net_saved_ms_vs_transition   = -50,953
  interpretation: cache pollution / evict-before-use dominates

capacity=10240:
  Dolly utility_keep50 net_saved_ms_vs_transition = +352
  AYA utility_keep50 net_saved_ms_vs_transition   = +546
  interpretation: when payload residency is large enough, gated MTP extras
  become net-positive vs transition_top32 in this lab replay

stress fallback, capacity=10240:
  Dolly / AYA utility_keep50 net_saved_ms_vs_transition = 0
  interpretation: gated policies collapse to transition_top32 and do not issue
  extra full_fetch payloads under stress fallback
```

Conclusion:

```text
Real prefetch/cache-manager work is now capacity-gated.
The action replay positive signal survives a bounded-cache lab only in the
large-residency envelope.  It fails under smaller capacity because unused
prefetches are evicted before use.

Next gate:
  sweep cache capacity / manager overhead / overlap to identify the smallest
  robust positive residency envelope before any vLLM runtime cache-manager
  prototype.
```

## Production-like prefetch action replay v2

Update:

```text
Fixed replay audit hashes:
  demand_stream_hash now covers current-demand rows only
    columns = token, layer, expert

  true_router_stream_hash now covers the full true-router stream
    columns = token, future_window, layer, expert

The two hashes are no longer aliased.
```

Implementation:

```text
scripts/run_prefetch_cache_lab.py
scripts/summarize_prefetch_cache_lab.py
tests/test_prefetch_cache_lab.py
tests/test_summarize_prefetch_cache_lab.py
```

Artifacts:

```text
outputs/reports/prefetch_action_replay/production_like_aya512_normal_v2.json
outputs/reports/prefetch_action_replay/production_like_aya512_stress_v2.json
outputs/reports/prefetch_action_replay/production_like_dolly128_prefix127_normal_v2.json
outputs/reports/prefetch_action_replay/production_like_dolly128_prefix127_stress_v2.json
outputs/reports/prefetch_action_replay/production_like_action_replay_summary_v2.md
outputs/reports/prefetch_action_replay/production_like_action_replay_summary_v2.csv
outputs/reports/prefetch_action_replay/production_like_action_replay_summary_v2.json
```

Key result, capacity=10240:

```text
AYA heldout512 normal:
  transition_top32_plus_utility_keep50 net_saved_ms_vs_transition = +545.910
  transition_top32_plus_score_keep50   net_saved_ms_vs_transition = +573.055

Dolly heldout128 prefix127 normal:
  transition_top32_plus_utility_keep50 net_saved_ms_vs_transition = +351.836
  transition_top32_plus_score_keep50   net_saved_ms_vs_transition = +383.439

Stress fallback:
  AYA / Dolly gated policies collapse to transition_top32
  net_saved_ms_vs_transition = 0
```

Boundary:

```text
bounded-cache lab replay only
not endpoint TPOT
not a real vLLM cache-manager implementation
```

Conclusion:

```text
The prefetch main line remains viable in the large-residency normal envelope:
gated MTP/score extras beat transition_top32 on both AYA and Dolly replay.

Under stress fallback, gated extras are shut down and do not damage the
transition baseline.

Next gate:
  capacity / overlap / manager-overhead sweep plus Amdahl mapping from local
  stall proxy to endpoint upper bound.
```

Capacity sweep v2:

```text
artifact:
  outputs/reports/prefetch_action_replay/capacity_sweep_v2/summary.md
  outputs/reports/prefetch_action_replay/capacity_sweep_v2/summary.csv
  outputs/reports/prefetch_action_replay/capacity_sweep_v2/summary.json

capacities:
  2048 / 4096 / 8192 / 10240 / 16384

AYA heldout512 utility_keep50 net_saved_ms_vs_transition:
  2048:  -50,953.472
  4096:  -11,831.519
  8192:     -107.529
  10240:    +545.910
  16384:    +545.910

Dolly heldout128 prefix127 utility_keep50 net_saved_ms_vs_transition:
  2048:  -16,840.217
  4096:   -4,186.528
  8192:     +186.761
  10240:    +351.836
  16384:    +351.836

interpretation:
  The cache-manager replay is residency-gated. Dolly turns positive by
  capacity=8192; AYA needs capacity=10240 for a clear positive margin.
  capacity=10240 and 16384 are identical in these traces, indicating the
  replay has reached the relevant working-set residency plateau.
```

Current prefetch claim boundary:

```text
supported:
  In a large-residency bounded-cache replay, gated MTP/score extras improve
  local demand-stall cost vs transition_top32 on both AYA and Dolly.

not supported:
  small-residency runtime cache benefit
  endpoint TPOT improvement
  real vLLM cache-manager deployment

next gate:
  overlap / manager-overhead sensitivity around capacity 8192 and 10240,
  then map the robust local stall-proxy gain through measured MoE shares.
```

Overlap sensitivity v2:

```text
artifact:
  outputs/reports/prefetch_action_replay/overlap_sweep_v2/summary.md
  outputs/reports/prefetch_action_replay/overlap_sweep_v2/summary.csv
  outputs/reports/prefetch_action_replay/overlap_sweep_v2/summary.json

capacities:
  8192 / 10240

overlap_factor:
  0.0 / 0.5 / 0.8 / 0.9
```

Utility keep50 net_saved_ms_vs_transition:

```text
AYA heldout512, capacity=8192:
  overlap 0.0: -3348.331
  overlap 0.5: -1322.830
  overlap 0.8:  -107.529
  overlap 0.9:  +297.571

AYA heldout512, capacity=10240:
  overlap 0.0:    -2.003
  overlap 0.5:  +340.442
  overlap 0.8:  +545.910
  overlap 0.9:  +614.399

Dolly heldout128 prefix127, capacity=8192:
  overlap 0.0:  -676.878
  overlap 0.5:  -137.104
  overlap 0.8:  +186.761
  overlap 0.9:  +294.716

Dolly heldout128 prefix127, capacity=10240:
  overlap 0.0:   -11.770
  overlap 0.5:  +215.484
  overlap 0.8:  +351.836
  overlap 0.9:  +397.287
```

Interpretation:

```text
The positive signal is overlap-sensitive but not solely an overlap=0.8 artifact.

At capacity=10240, both AYA and Dolly turn positive by overlap=0.5 and are near
break-even at overlap=0.0.  At capacity=8192, Dolly turns positive by
overlap=0.8, while AYA needs a more aggressive overlap=0.9.

Current robust normal-envelope point:
  capacity=10240
  overlap_factor>=0.5

Current borderline point:
  capacity=8192
  overlap_factor depends on dataset and should not be used as the default
  positive claim.
```

Manager-overhead sensitivity v2:

```text
artifact:
  outputs/reports/prefetch_action_replay/manager_sweep_v2/summary.md
  outputs/reports/prefetch_action_replay/manager_sweep_v2/summary.csv
  outputs/reports/prefetch_action_replay/manager_sweep_v2/summary.json

fixed envelope:
  capacity=10240
  overlap_factor=0.5

manager_us_per_issue:
  0 / 1 / 5 / 10 / 50
```

Utility keep50 net_saved_ms_vs_transition:

```text
AYA heldout512:
  manager 0 us:  +340.442
  manager 1 us:  +337.707
  manager 5 us:  +326.767
  manager 10 us: +313.092
  manager 50 us: +203.692

Dolly heldout128 prefix127:
  manager 0 us:  +215.484
  manager 1 us:  +213.669
  manager 5 us:  +206.409
  manager 10 us: +197.334
  manager 50 us: +124.734
```

Interpretation:

```text
At the robust residency point, the replay remains positive even with
50 us manager overhead per issued fetch.  This suggests the current positive
normal-envelope result is not hypersensitive to small CPU/bookkeeping overheads,
provided payload residency and overlap are sufficient.

This still does not prove endpoint TPOT benefit or a real runtime cache manager.
```

Bandwidth sensitivity v2:

```text
artifact:
  outputs/reports/prefetch_action_replay/bandwidth_sweep_v2/summary.md
  outputs/reports/prefetch_action_replay/bandwidth_sweep_v2/summary.csv
  outputs/reports/prefetch_action_replay/bandwidth_sweep_v2/summary.json

fixed envelope:
  capacity=10240
  overlap_factor=0.5
  manager_us_per_issue=50

bandwidth_gbps:
  3.0 / 6.589 / 12.0
```

Utility keep50 net_saved_ms_vs_transition:

```text
AYA heldout512:
  3.0 GB/s:    +610.975
  6.589 GB/s:  +203.692
  12.0 GB/s:    +50.181

Dolly heldout128 prefix127:
  3.0 GB/s:    +382.525
  6.589 GB/s:  +124.734
  12.0 GB/s:    +27.569
```

Interpretation:

```text
The robust-envelope replay remains positive under slower and faster bandwidth
assumptions even with 50 us manager overhead per issued fetch.

The absolute margin shrinks as bandwidth increases, because demand misses are
cheaper and the prefetch opportunity envelope narrows.  This should be reported
as a bounded-cache local stall-proxy result, not as an endpoint speedup claim.
```

Cache-lab Amdahl upper-bound v2:

```text
artifact:
  outputs/reports/prefetch_action_replay/production_like_cache_lab_amdahl_v2.md
  outputs/reports/prefetch_action_replay/production_like_cache_lab_amdahl_v2.csv
  outputs/reports/prefetch_action_replay/production_like_cache_lab_amdahl_v2.json

shares:
  MoE apply = 28.40%
  MLP/MoE   = 49.06%
```

Conservative MoE-apply mapped upper bound:

```text
AYA heldout512 normal:
  utility_keep50 local demand-stall reduction = 40.52%
  MoE-apply endpoint saved-share upper bound  = 11.51%
  MoE-apply endpoint speedup upper bound      = 13.01%

Dolly heldout128 prefix127 normal:
  utility_keep50 local demand-stall reduction = 30.56%
  MoE-apply endpoint saved-share upper bound  = 8.68%
  MoE-apply endpoint speedup upper bound      = 9.51%

Stress fallback:
  local demand-stall reduction = 0
  endpoint upper bound         = 0
```

Boundary:

```text
This is an upper-bound translation of a replay-local demand-DMA stall proxy.
It is not endpoint TPOT evidence and does not prove that real vLLM execution
can realize these savings.  The practical claim remains bounded-cache replay
benefit under a favorable residency/overlap envelope.
```

Machine-readable gate summary:

```text
script:
  scripts/summarize_prefetch_cache_lab_gate.py

tests:
  tests/test_summarize_prefetch_cache_lab_gate.py

artifact:
  outputs/reports/prefetch_action_replay/prefetch_cache_lab_gate_v2.md
  outputs/reports/prefetch_action_replay/prefetch_cache_lab_gate_v2.json
```

Gate result:

```text
first positive capacity:
  AYA heldout512:                 10240
  Dolly heldout128 prefix127:      8192

first positive overlap at capacity=10240:
  AYA heldout512:                 0.5
  Dolly heldout128 prefix127:     0.5

manager_sensitivity at capacity=10240, overlap=0.5:
  all tested manager costs remain positive up to 50 us/issue

bandwidth_sensitivity at capacity=10240, overlap=0.5, manager=50 us/issue:
  all tested bandwidths remain positive across 3.0 / 6.589 / 12.0 GB/s
```

Evidence manifest:

```text
outputs/reports/prefetch_action_replay/prefetch_cache_lab_v2_evidence_manifest.md
outputs/reports/prefetch_action_replay/prefetch_cache_lab_v2_evidence_manifest.json
```

Manifest entries:

```text
production_like summary
capacity_sweep_v2 directory
overlap_sweep_v2 directory
manager_sweep_v2 directory
bandwidth_sweep_v2 directory
gate summary
Amdahl upper-bound mapping
controlled_manager_v1 summary
controlled_manager_prototype smoke summary
real_prefetch_lab_experiment_plan
measured_copy_bench
measured_copy_manager summary
measured_copy_queue_sweep_dolly summary
```

Runtime gate contract:

```text
module:
  src/mtp_expert_prefetch/runtime/cache_lab_gate.py

config:
  configs/runtime/prefetch_cache_lab_gate_v2.yaml

tests:
  tests/test_cache_lab_gate.py
```

Default contract:

```text
min_payload_capacity: 10240
min_overlap_factor: 0.5
max_manager_us_per_issue: 50.0
min_bandwidth_gbps: 3.0
max_bandwidth_gbps: 12.0
require_stress_fallback_clear: true
```

Interpretation:

```text
This is an admission envelope for controlled cache-manager prototypes.  It is
not the older per-layer candidate budget used by RuntimeSignals.effective_capacity.

The gate allows MTP full_fetch only inside the replay-supported large-residency,
moderate-overlap envelope.  Outside that envelope, full_fetch should fallback
to transition-only / metadata-premap shadow behavior.
```

Replay integration smoke:

```text
script:
  scripts/run_prefetch_cache_lab.py --cache-lab-gate-config \
    configs/runtime/prefetch_cache_lab_gate_v2.yaml

artifacts:
  outputs/reports/prefetch_action_replay/cache_lab_gate_smoke_allowed.json
  outputs/reports/prefetch_action_replay/cache_lab_gate_smoke_capacity_blocked.json

allowed smoke:
  reason = cache_lab_envelope_allowed
  utility_keep50 remains different from transition_top32
  utility_keep50 net_saved_us_vs_transition = +376.04

capacity-blocked smoke:
  reason = payload_capacity_below_gate
  utility_keep50 collapses to transition_top32
  utility_keep50 net_saved_us_vs_transition = 0
```

Controlled cache-manager prototype:

```text
module:
  src/mtp_expert_prefetch/runtime/cache_manager.py

summary script:
  scripts/summarize_cache_manager_prototype.py

tests:
  tests/test_cache_manager.py
  tests/test_summarize_cache_manager_prototype.py

artifacts:
  outputs/reports/prefetch_action_replay/cache_manager_prototype_smoke_allowed.json
  outputs/reports/prefetch_action_replay/cache_manager_prototype_smoke_capacity_blocked.json
  outputs/reports/prefetch_action_replay/cache_manager_prototype_summary.md
  outputs/reports/prefetch_action_replay/cache_manager_prototype_summary.json
```

Prototype contract:

```text
The controlled manager owns bounded global LRU residency, demand hit/miss
accounting, prefetch issue/use accounting, and unused-prefetch eviction
counters.  The replay path now exercises this manager instead of a local
OrderedDict cache shim.

This is still a lab cache-manager replay/prototype.  It is not endpoint TPOT
and not a real vLLM cache-manager implementation.
```

Prototype smoke summary:

```text
allowed:
  reason = cache_lab_envelope_allowed
  capacity = 10240
  overlap = 0.5
  manager_us_per_issue = 50
  bandwidth_gbps = 6.589
  utility_keep50 issued / used / unused = 2613 / 2305 / 308
  utility_keep50 net_saved_us_vs_transition = +376.043

capacity-blocked:
  reason = payload_capacity_below_gate
  capacity = 8192
  overlap = 0.8
  utility_keep50 collapses to transition_top32
  utility_keep50 stress_shutdown_count = 3520
  utility_keep50 net_saved_us_vs_transition = 0
```

Validation:

```text
python -m pytest tests -q
346 passed, 2 warnings
```

Review fixes:

```text
scripts/summarize_cache_manager_prototype.py now derives the transition
baseline from config.transition_topk instead of hard-coding transition_top32.

The candidate row is matched exactly as:
  transition_top{topk}{policy_suffix}

Duplicate exact candidate rows raise an error, and missing gate decisions are
reported as gate_decision_missing instead of being mistaken for a blocked gate.
```

Replay contract tests:

```text
apply_cache_lab_gate_to_policies() is now a tested helper instead of being
embedded only inside main().

The regression test verifies:
  blocked gate -> score/utility candidates collapse to transition
  oracle_used remains unchanged
  shutdown_count records the removed extra payloads
  replay_policy row counters match cache_manager_snapshot counters
```

Manager-backed production-like replay v1:

```text
artifacts:
  outputs/reports/prefetch_action_replay/controlled_manager_aya512_normal_v1.json
  outputs/reports/prefetch_action_replay/controlled_manager_aya512_stress_v1.json
  outputs/reports/prefetch_action_replay/controlled_manager_dolly128_prefix127_normal_v1.json
  outputs/reports/prefetch_action_replay/controlled_manager_dolly128_prefix127_stress_v1.json
  outputs/reports/prefetch_action_replay/controlled_manager_v1_summary.md
  outputs/reports/prefetch_action_replay/controlled_manager_v1_summary.json
  outputs/reports/prefetch_action_replay/controlled_manager_v1_summary.csv

common envelope:
  capacity = 10240
  overlap_factor = 0.5
  manager_us_per_issue = 50
  bandwidth_gbps = 6.589
  gate = configs/runtime/prefetch_cache_lab_gate_v2.yaml
```

Result:

```text
AYA heldout512 normal:
  transition_top32_plus_utility_keep50 net_saved_ms_vs_transition = +203.692
  transition_top32_plus_score_keep50   net_saved_ms_vs_transition = +213.570

Dolly heldout128 prefix127 normal:
  transition_top32_plus_utility_keep50 net_saved_ms_vs_transition = +124.734
  transition_top32_plus_score_keep50   net_saved_ms_vs_transition = +135.191

AYA stress:
  gated score/utility policies collapse to transition_top32
  net_saved_ms_vs_transition = 0

Dolly stress:
  gated score/utility policies collapse to transition_top32
  net_saved_ms_vs_transition = 0
```

Interpretation:

```text
This pins the main AYA/Dolly production-like cache-lab reports to the current
ControlledExpertCacheManager implementation.  It preserves the earlier
bounded-cache conclusion: normal envelope is positive at the robust capacity,
and stress fallback shuts down MTP full_fetch extras.

This remains lab replay evidence, not endpoint TPOT and not a real vLLM cache
manager.
```

Measured-copy controlled-manager shim v1:

```text
copy microbench:
  scripts/benchmark_expert_transfer.py

artifact:
  outputs/reports/prefetch_action_replay/measured_copy_gpu1_expert_transfer_v1.json

device:
  GPU1 / AMD Radeon PRO W7900 Dual Slot

payload:
  expert_bytes = 1,650,000
  pinned H2D copy, uint8 contiguous payload

selected replay envelope:
  measured_copy_stat = p95
  measured_copy_experts = 8
  measured_copy_us_per_issue = 1828.442
  measured_copy_effective_gbps = 0.902
  max_inflight_prefetches = 8
  queue_wait_us_per_overflow = 1828.442
```

Measured-copy replay artifacts:

```text
outputs/reports/prefetch_action_replay/measured_copy_manager_aya512_normal_v1.json
outputs/reports/prefetch_action_replay/measured_copy_manager_aya512_stress_v1.json
outputs/reports/prefetch_action_replay/measured_copy_manager_dolly128_prefix127_normal_v1.json
outputs/reports/prefetch_action_replay/measured_copy_manager_dolly128_prefix127_stress_v1.json
outputs/reports/prefetch_action_replay/measured_copy_manager_v1_summary.md
outputs/reports/prefetch_action_replay/measured_copy_manager_v1_summary.json
outputs/reports/prefetch_action_replay/measured_copy_manager_v1_summary.csv
```

Result:

```text
AYA heldout512 normal:
  utility_keep50 net_saved_ms_vs_transition = +1992.471
  utility_keep50 queue_wait_ms = 2225.214
  utility_keep50 queue_pressure = 0.197

Dolly heldout128 prefix127 normal:
  utility_keep50 net_saved_ms_vs_transition = +1105.965
  utility_keep50 queue_wait_ms = 2492.167
  utility_keep50 queue_pressure = 0.231

AYA / Dolly stress:
  gated score/utility policies collapse to transition_top32
  net_saved_ms_vs_transition = 0
```

Interpretation:

```text
The measured H2D copy envelope is much slower than the prior analytic
6.589 GB/s assumption, but the same measured copy cost also applies to demand
misses.  Under this replay model, the normal-envelope MTP utility candidate
remains positive and stress fallback remains net-neutral.

The new queue-pressure counters show a real implementation risk:
issue bursts create multi-second aggregate queue_wait_ms in replay.  A real
fetch manager must therefore support batching, in-flight limits, and queue
backpressure rather than relying on average bandwidth alone.

This is still a controlled replay/shim result.  It does not prove endpoint
TPOT or a production vLLM DMA/cache manager.
```

Measured-copy queue sensitivity:

```text
artifact:
  outputs/reports/prefetch_action_replay/measured_copy_queue_sweep_dolly_v1_summary.md
  outputs/reports/prefetch_action_replay/measured_copy_queue_sweep_dolly_v1_summary.json
  outputs/reports/prefetch_action_replay/measured_copy_queue_sweep_dolly_v1_summary.csv

dataset:
  Dolly heldout128 prefix127

fixed envelope:
  capacity = 10240
  overlap_factor = 0.5
  manager_us_per_issue = 50
  measured_copy_us_per_issue = 1828.442
```

Utility keep50 vs transition:

```text
max_inflight = 0  (queue disabled): +1482.624 ms
max_inflight = 4:                  +923.121 ms
max_inflight = 8:                 +1105.965 ms
max_inflight = 16:                +1217.500 ms
max_inflight = 32:                +1224.814 ms
```

Queue interpretation:

```text
The queue model is a per-token-layer burst-overflow approximation, not a real
async DMA scheduler simulation.

Even the stricter max_inflight=4 setting remains positive for Dolly in this
measured-copy replay.  However, the aggregate queue_wait_ms is large, so the
next runtime shim must explicitly test batching/coalescing/backpressure.
```

Queue-aware batching/backpressure shim:

```text
artifact:
  outputs/reports/prefetch_action_replay/queue_aware_manager_dolly_v1_summary.md
  outputs/reports/prefetch_action_replay/queue_aware_manager_dolly_v1_summary.json
  outputs/reports/prefetch_action_replay/queue_aware_manager_dolly_v1_summary.csv

dataset:
  Dolly heldout128 prefix127

fixed envelope:
  capacity = 10240
  overlap_factor = 0.5
  manager_us_per_issue = 50
  measured_copy_us_per_batch = 14627.537
  measured_copy_batch_size = 8
  max_inflight_prefetches = 8
```

Utility keep50 vs transition:

```text
token_layer batching + wait:
  net_saved_ms_vs_transition = -947891.123

token_layer batching + drop:
  net_saved_ms_vs_transition = -1422.150

global batching + wait:
  net_saved_ms_vs_transition = -943166.429

global batching + drop:
  net_saved_ms_vs_transition = +238.075
```

Interpretation:

```text
Token/layer-local batching is not sufficient: under the wait policy, burst
overflow wait dominates even when DMA batching is globally coalesced.

Within this Dolly queue-aware sweep, the only positive variant is global
batching + drop backpressure.  That is useful evidence for a stricter runtime
contract, but it is not an unconditional full_fetch win.  It means the manager
needs cross-window coalescing and explicit admission/backpressure that can drop
overflow extras instead of preserving every requested prefetch.

This remains a queue approximation over the issue/demand stream, not a real
async DMA scheduler or endpoint TPOT result.
```

Event-driven queue-manager shim:

```text
implementation:
  scripts/run_prefetch_cache_lab.py --queue-model event

artifact:
  outputs/reports/prefetch_action_replay/event_queue_manager_dolly_v1_summary.md
  outputs/reports/prefetch_action_replay/event_queue_manager_dolly_v1_summary.json
  outputs/reports/prefetch_action_replay/event_queue_manager_dolly_v1_summary.csv

dataset:
  Dolly heldout128 prefix127

fixed envelope:
  capacity = 10240
  measured_copy_us_per_batch = 14627.537
  measured_copy_batch_size = 8
  queue_batch_size = 8
  queue_event_interval_us = 50
  queue_deadline_us = 500
```

Utility keep50 vs transition:

```text
event queue + wait:
  net_saved_ms_vs_transition = +1482.624
  queue_service_ms = 10775.009
  queue_total_span_ms = 10775.009
  queue_max_delay_ms = 9512.039

event queue + drop, prefix admission:
  net_saved_ms_vs_transition = -1285.790
  queue_service_ms = 2631.128
  queue_total_span_ms = 6083.578
  queue_max_delay_ms = 2033.494

event queue + drop, score admission:
  score_keep50 net_saved_ms_vs_transition = +2625.240
  utility_keep50 net_saved_ms_vs_transition = +1953.681
  utility queue_service_ms = 4481.512
  utility queue_total_span_ms = 5607.628
  utility queue_max_delay_ms = 3754.158

event queue + drop, protected-score admission:
  score_keep50 net_saved_ms_vs_transition = 0.000
  utility_keep50 net_saved_ms_vs_transition = 0.000

event queue + drop, protected-score admission, max_inflight=40:
  score_keep50 net_saved_ms_vs_transition = +1612.222
  utility_keep50 net_saved_ms_vs_transition = +1482.624

protected-score budget sweep:
  artifact:
    outputs/reports/prefetch_action_replay/event_queue_sweep_protected_score_v1/summary.md
    outputs/reports/prefetch_action_replay/event_queue_sweep_protected_score_v1/sweep.json
    outputs/reports/prefetch_action_replay/event_queue_sweep_protected_score_v1/summary.csv

  sweep:
    max_inflight = 32..40
    deadline_us = 0 / 100 / 250 / 500 / 1000

  first positive score_keep50:
    max_inflight = 33
    deadline_us = 0
    net_saved_ms_vs_transition = +317.533

  first positive utility_keep50:
    max_inflight = 33
    deadline_us = 0
    net_saved_ms_vs_transition = +374.472
```

Interpretation:

```text
The event-driven queue removes the unrealistic aggregate overflow wait from the
wait policy and makes measured-copy service time explicit.  Under this logical
arrival/deadline envelope, utility_keep50 remains positive in wait mode.

However, max queue delay is large, so wait mode is still not a production
runtime claim.  Blunt prefix drop is negative because per-burst backpressure
drops too many useful prefetches.  Score-aware drop restores positive net
savings in this Dolly event-queue replay, which makes admission quality a
first-class manager requirement: the manager should drop low-score extras,
not simply preserve a prefix of each token/layer burst.

The protected-score control is also important: with `max_inflight=8` below the
transition_top32 baseline width, preserving the transition prefix consumes the
entire per-window issue budget and collapses MTP extras back to transition.
Therefore the positive score-admission result should be read as "high-value
MTP extras can replace transition tail under queue pressure", not as
"transition_top32 is fully protected and extras are added for free".

When the issue budget is widened to `max_inflight=40`, protected-score restores
the same positive net as the event wait replay because transition_top32 plus up
to 8 extras fit inside the per-window budget.  This gives a concrete runtime
gate: protected baseline + MTP extras requires queue capacity above the
transition baseline width; below that, the manager must choose between
transition-tail replacement and strict baseline protection.

The local budget sweep was the old residency-only event-shim view: the first
positive protected baseline point appeared at `max_inflight=33`, i.e.
transition_top32 plus one extra slot.  Here `max_inflight` was a per
token/layer burst cap, not a system-wide DMA concurrency limit.

This residency-only result is superseded for deadline/ready-before-demand
claims by the newer ready-time event queue.  In the ready-time queue, a prefetch
hit requires virtual H2D completion no later than the demand deadline, and the
MTP-extra-issued cells do not pass the tested copy/lookahead sweeps.

This is still a virtual event-driven service shim over the issue/demand
stream.  It uses global queue coalescing and is not a real DMA scheduler or
endpoint TPOT result.
```

### Premap-only runtime/shadow contract

Implemented a dedicated `premap_summary` runtime shadow event for descriptor /
address preparation:

```text
premap_summary:
  records descriptor/address prep counts, bytes, hashes, and build_us
  records zero payload bytes
  records zero full_fetch / metadata side effects
  records no router mutation
  records no descriptor_order execution / visitation change
  gives no ready-before-demand credit
```

This separates premap audit semantics from both full payload transfer and
descriptor_order execution.  The logger/controller can now write premap-only
summary rows from `ExpertPrefetchDescriptor` lists, with deterministic
descriptor/address hashes and aggregate violation counters for payload,
router-change, descriptor-order-change, and ready-credit mistakes.

Validation:

```bash
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest tests -q
```

Result:

```text
380 passed, 2 warnings
```

Boundary:

```text
This is a shadow/audit contract only.
It does not move expert payloads, does not change true router outputs, and does
not execute descriptor_order.
```

Smoke artifact:

```text
outputs/reports/prefetch_action_replay/premap_only_shadow_contract_smoke/README.md
outputs/reports/prefetch_action_replay/premap_only_shadow_contract_smoke/contract_verification.md
```

Result:

```text
premap_summary_count = 40
premap_summary_descriptor_count = 2611
premap_summary_actual_bytes = 10,694,656
premap_summary_payload_bytes = 0
premap_summary_payload_violation_count = 0
premap_summary_full_fetch_violation_count = 0
premap_summary_metadata_violation_count = 0
premap_summary_router_change_violation_count = 0
premap_summary_descriptor_order_change_violation_count = 0
premap_summary_ready_credit_violation_count = 0
descriptor_order_summary_count = 0
full_fetch_count = 0
metadata_count = 0
outcome_count = 0
```

The reusable verifier is:

```text
scripts/summarize_premap_shadow_contract.py
```

It reads `runtime_shadow.jsonl` and fails the contract if the artifact contains
payload transfer, router mutation, descriptor_order execution, ready-credit
side effects, or any non-premap event class.

### vLLM current-router premap shadow producer

Wired the premap-only contract into the vLLM router recorder as an explicit
shadow producer:

```text
runtime_shadow.emit_premap_summaries = true
```

The new hook converts the current true-router top-k for each observed layer into
deduplicated `ExpertPrefetchDescriptor` rows and emits one `premap_summary`
audit event.  It works with `outcome_logging_mode=off`, so it can validate the
descriptor/address producer without writing per-token outcomes.

Safety boundary:

```text
current-router top-k remains authoritative
no payload transfer
no full_fetch / metadata action
no ready-before-demand credit
no descriptor_order execution
invalid / OOB expert ids are filtered from the premap descriptor set
```

This is a vLLM producer-contract validation path, not a future-MTP prefetch
performance claim.  The source is recorded as:

```text
current_router_topk_premap_shadow
```

Validation:

```bash
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest tests/test_vllm_router_shadow_sink.py -q
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest tests -q
```

Result:

```text
42 passed
386 passed, 2 warnings
```

Real AWQ/vLLM smoke:

```bash
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/trace_router_mtp_vllm.py \
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_shadow_smoke_sample1.yaml

/home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/summarize_premap_shadow_contract.py \
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_shadow_smoke_sample1/runtime_shadow.jsonl \
  --output-json data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_shadow_smoke_sample1/premap_contract_summary.json \
  --output-md data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_shadow_smoke_sample1/premap_contract_summary.md
```

Result:

```text
event_types = ["premap_summary"]
premap_summary_count = 40
premap_summary_descriptor_count = 2490
premap_summary_actual_bytes = 10,199,040
premap_summary_payload_bytes = 0
premap_summary_payload_violation_count = 0
premap_summary_full_fetch_violation_count = 0
premap_summary_metadata_violation_count = 0
premap_summary_router_change_violation_count = 0
premap_summary_descriptor_order_change_violation_count = 0
premap_summary_ready_credit_violation_count = 0
forbidden_event_total = 0
non_premap_event_total = 0
contract ok = true
```

8-sample AWQ/vLLM scale smoke:

```bash
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/trace_router_mtp_vllm.py \
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_shadow_smoke8.yaml
```

Verifier result:

```text
event_types = ["premap_summary"]
premap_summary_count = 320
premap_summary_descriptor_count = 33818
premap_summary_actual_bytes = 138,518,528
premap_summary_build_us_mean = 232.140 us
premap_summary_payload_bytes = 0
premap_summary_payload_violation_count = 0
premap_summary_full_fetch_violation_count = 0
premap_summary_metadata_violation_count = 0
premap_summary_router_change_violation_count = 0
premap_summary_descriptor_order_change_violation_count = 0
premap_summary_ready_credit_violation_count = 0
forbidden_event_total = 0
contract ok = true
```

Transition-derived premap action smoke:

```bash
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/trace_router_mtp_vllm.py \
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_transition_premap_shadow_smoke_sample1.yaml
```

This mode emits future-token premap audit rows from the previous-token
transition candidates:

```text
emit_transition_premap_summaries = true
transition_summary_mode = previous_topk
premap_policy = transition_premap_only
premap_source = previous_token_transition_premap_shadow
```

Verifier result:

```text
event_types = ["premap_summary"]
premap_summary_count = 880
premap_summary_descriptor_count = 7040
premap_summary_actual_bytes = 28,835,840
premap_summary_build_us_mean = 48.149 us
premap_summary_payload_bytes = 0
premap_summary_payload_violation_count = 0
premap_summary_full_fetch_violation_count = 0
premap_summary_metadata_violation_count = 0
premap_summary_router_change_violation_count = 0
premap_summary_descriptor_order_change_violation_count = 0
premap_summary_ready_credit_violation_count = 0
forbidden_event_total = 0
non_premap_event_total = 0
contract ok = true
```

This is still shadow-only.  It validates that transition-derived premap
descriptor/address preparation can be produced on the real AWQ/vLLM router path
without outcome rows, payload movement, ready-credit, router mutation, or
descriptor_order execution.

Calibrated matrix-topk transition premap smoke:

```bash
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/trace_router_mtp_vllm.py \
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_matrix_premap_shadow_smoke_sample1.yaml
```

This mode uses the calibrated transition artifact:

```text
transition_summary_mode = matrix_topk
transition_topk_count = 32
transition_matrix_path = outputs/artifacts/transition_matrix_512sample_calibrated.pt
premap_policy = transition_matrix_top32_premap_only
transition_premap_source = matrix_topk_transition_premap_shadow
```

Verifier result:

```text
event_types = ["premap_summary"]
premap_summary_count = 880
premap_summary_descriptor_count = 28160
premap_summary_unique_experts_mean = 32.0
premap_summary_actual_bytes = 115,343,360
premap_summary_build_us_mean = 217.234 us
premap_summary_payload_bytes = 0
premap_summary_payload_violation_count = 0
premap_summary_full_fetch_violation_count = 0
premap_summary_metadata_violation_count = 0
premap_summary_router_change_violation_count = 0
premap_summary_descriptor_order_change_violation_count = 0
premap_summary_ready_credit_violation_count = 0
forbidden_event_total = 0
non_premap_event_total = 0
contract ok = true
```

This is the closest current vLLM shadow path to the protected transition
baseline: it emits transition@32 descriptor/address premap audit rows from the
real router stream while preserving the no-payload/no-ready-credit contract.

Premap prepared-plan / address-manager shim:

```text
runtime.premap now builds a PremapPreparedPlan:
  ExpertPrefetchDescriptor[]
  -> PremapAddressRecord[]
  -> deterministic descriptor slots
  -> deterministic address keys
  -> descriptor_hash / address_hash

runtime.cache_manager now includes ControlledPremapAddressManager:
  consumes PremapPreparedPlan
  tracks address residency / reuse / eviction
  tracks cumulative prepared_descriptor_actual_bytes
  tracks current resident_descriptor_bytes
  keeps payload_bytes = 0
```

`build_premap_shadow_summary` now derives counts, bytes, descriptor hash, and
address hash from `PremapPreparedPlan` instead of local summary-only hashing.
This connects premap summaries to an explicit descriptor/address preparation
object and a cache-manager-style shim while preserving the same safety contract:

```text
no full payload transfer
no ready credit
no router mutation
no descriptor_order execution
```

Review hardening:

```text
address_key remains address-level:
  expert_weight_descriptor:s{sample}:l{layer}:e{expert}

address_hash is plan-level:
  includes descriptor slot, address key, priority, and source
  so same address reuse does not hide different premap plan semantics

ControlledPremapAddressManager snapshot separates:
  prepared_descriptor_actual_bytes  # cumulative preparation work
  resident_descriptor_bytes         # current descriptor/address residency
  reused address entries refresh descriptor_bytes on later plans
```

Validation:

```bash
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest tests -q
```

Result:

```text
392 passed, 2 warnings
```

Real AWQ/vLLM current-router smoke after prepared-plan hookup:

```bash
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/trace_router_mtp_vllm.py \
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_shadow_smoke_sample1.yaml

/home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/summarize_premap_shadow_contract.py \
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_shadow_smoke_sample1/runtime_shadow.jsonl \
  --output-json data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_shadow_smoke_sample1/premap_contract_summary.json \
  --output-md data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_shadow_smoke_sample1/premap_contract_summary.md
```

Verifier result:

```text
event_types = ["premap_summary"]
premap_summary_count = 40
premap_summary_descriptor_count = 2490
premap_summary_actual_bytes = 10,199,040
premap_summary_build_us_mean = 276.280 us
premap_summary_payload_bytes = 0
premap_summary_payload_violation_count = 0
premap_summary_full_fetch_violation_count = 0
premap_summary_metadata_violation_count = 0
premap_summary_router_change_violation_count = 0
premap_summary_descriptor_order_change_violation_count = 0
premap_summary_ready_credit_violation_count = 0
forbidden_event_total = 0
non_premap_event_total = 0
contract ok = true
```

The build time now includes constructing the explicit prepared-plan records and
their address hashes.  This is therefore a stricter premap preparation smoke
than the earlier summary-only hash path.

Premap address-manager replay shim:

```text
runtime.premap_replay:
  load_premap_descriptor_jsonl
  group_premap_descriptors_by_sample_layer
  replay_premap_address_manager
  preserves first-seen event order for LRU-sensitive replay

scripts/replay_premap_address_manager.py:
  descriptor JSONL -> PremapPreparedPlan events -> ControlledPremapAddressManager
  reports address reuse, resident descriptor bytes, eviction pressure
```

Smoke replay artifact:

```bash
/home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/replay_premap_address_manager.py \
  outputs/reports/prefetch_action_replay/premap_only_shadow_contract_smoke/descriptors.jsonl \
  --capacity 0 32 128 512 2048 unbounded \
  --descriptor-bytes 4096 \
  --output-json outputs/reports/prefetch_action_replay/premap_address_manager_replay_smoke/summary.json \
  --output-md outputs/reports/prefetch_action_replay/premap_address_manager_replay_smoke/summary.md
```

Result:

```text
events = 40
descriptors = 2,611
payload_bytes = 0
unbounded resident_descriptor_bytes = 10,694,656
unbounded resident_address_count = 2,611
```

256-sample replay artifact:

```bash
/home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/replay_premap_address_manager.py \
  outputs/reports/prefetch_shadow_256sample_mtp_extra/descriptors.jsonl \
  --capacity 0 256 1024 4096 8192 16384 unbounded \
  --descriptor-bytes 4096 \
  --output-json outputs/reports/prefetch_action_replay/premap_address_manager_replay_256sample/summary.json \
  --output-md outputs/reports/prefetch_action_replay/premap_address_manager_replay_256sample/summary.md
```

Key rows:

```text
events = 2,560
descriptors = 348,543
prepared_descriptor_actual_bytes = 1,427,632,128
payload_bytes = 0

capacity 8192:
  reuse_rate = 0.948219
  reused_address_count = 330,495
  resident_descriptor_bytes = 33,554,432
  eviction_pressure = 0.546099

capacity 16384:
  reuse_rate = 0.971731
  reused_address_count = 338,690
  resident_address_count = 9,853
  resident_descriptor_bytes = 40,357,888
  eviction_pressure = 0.0
```

Interpretation:

```text
Premap descriptor/address preparation has strong layer/expert address reuse in
the 256-sample artifact once the address manager has enough capacity.  The
resident descriptor/address footprint is tens of MB, not full expert payload
GB-scale transfer.  This supports keeping premap as a descriptor/address
preparation path before considering any full payload manager.

The replay preserves descriptor event order instead of sorting sample/layer
groups, because LRU reuse and eviction pressure are order-sensitive.
```

Optional vLLM online premap address-manager counters:

```text
runtime_shadow:
  emit_premap_address_manager_counters: true
  premap_address_manager_capacity: 16384
```

The recorder keeps a `ControlledPremapAddressManager` and writes minimal
manager counters into the existing `premap_summary` row:

```text
premap_address_manager_capacity
premap_address_new_count
premap_address_reused_count
premap_address_evicted_count
premap_address_resident_count
premap_address_resident_descriptor_bytes
premap_address_reuse_rate
premap_address_eviction_pressure
premap_address_prepared_descriptor_actual_bytes
```

The aggregate verifier treats `premap_address_new/reused/evicted_count` as
monotonic manager snapshots and sums per-row deltas. This avoids over-counting
cumulative snapshots while still handling a new request/manager reset.

This is optional and disabled by default. It remains premap-only:

```text
payload_bytes = 0
full_fetch_count = 0
metadata_count = 0
ready_credit = false
changes_router = false
changes_descriptor_order = false
```

GPU1 AWQ sample1 smoke:

```bash
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/trace_router_mtp_vllm.py \
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_shadow_smoke_sample1.yaml

/home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/summarize_premap_shadow_contract.py \
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_shadow_smoke_sample1/runtime_shadow.jsonl \
  --output-json data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_shadow_smoke_sample1/premap_contract_summary.json \
  --output-md data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_shadow_smoke_sample1/premap_contract_summary.md
```

Verifier result:

```text
event_types = ["premap_summary"]
premap_summary_count = 40
premap_summary_descriptor_count = 2490
premap_summary_actual_bytes = 10,199,040
premap_summary_build_us_mean = 300.358 us
counter_update_us_mean = 1128.743 us
premap_address_manager_count = 40
premap_address_new_count = 2490
premap_address_reused_count = 0
premap_address_evicted_count = 0
premap_address_resident_count_max = 2490
premap_address_resident_descriptor_bytes_max = 10,199,040
premap_summary_payload_bytes = 0
forbidden_event_total = 0
non_premap_event_total = 0
contract ok = true
```

This sample1 current-router smoke has no cross-event address reuse, which is
expected. The larger 256-sample offline replay above is the current evidence
for high premap address reuse under sufficient address-manager capacity.

Validation:

```bash
/home/husrcf/anaconda3/envs/TRY/bin/python -m pytest tests -q
```

Result:

```text
399 passed, 2 warnings
```

GPU1 AWQ 8-sample online premap-address manager smoke:

```bash
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/trace_router_mtp_vllm.py \
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_shadow_smoke8.yaml

/home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/summarize_premap_shadow_contract.py \
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_shadow_smoke8/runtime_shadow.jsonl \
  --output-json data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_shadow_smoke8/premap_contract_summary.json \
  --output-md data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_shadow_smoke8/premap_contract_summary.md
```

Result:

```text
event_types = ["premap_summary"]
premap_summary_count = 320
premap_summary_descriptor_count = 33818
premap_summary_actual_bytes = 138,518,528
premap_summary_build_us_mean = 225.263 us
counter_update_us_mean = 1129.011 us
premap_address_manager_count = 320
premap_address_new_count = 8488
premap_address_reused_count = 25330
premap_address_evicted_count = 0
premap_address_resident_count_max = 8488
premap_address_resident_descriptor_bytes_max = 34,766,848
premap_summary_payload_bytes = 0
forbidden_event_total = 0
non_premap_event_total = 0
contract ok = true
```

Interpretation:

```text
Online current-router premap/address shadow counters now show cross-sample
address reuse on the real AWQ vLLM path while preserving the premap-only
contract: no payload movement, no ready credit, no router change, and no
descriptor-order execution.
```

Next diagnostic config:

```text
configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_diag8.yaml
```

This keeps premap manager counters enabled and adds the low-intrusion online
fields requested for the next smoke:

```text
outcome_logging_mode = aggregate
descriptor_order_event_mode = minimal
descriptor_order_metrics_mode = count_only
emit_decoder_layer_timing = true
emit_decoder_component_timing = false
```

The mixed-event diagnostic should be summarized with aggregate shadow analysis,
not the strict premap-only verifier, because it intentionally emits outcome,
descriptor-order, and decoder-layer timing rows in addition to premap summaries.

GPU1 AWQ 8-sample mixed diagnostic smoke:

```bash
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/trace_router_mtp_vllm.py \
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_diag8.yaml
```

Result:

```text
runtime_shadow rows = 1,280
event_counts:
  decoder_layer_timing = 320
  descriptor_summary_min = 320
  outcome_aggregate = 320
  premap_summary = 320

premap:
  descriptor_count = 33,818
  actual_bytes = 138,518,528
  payload_bytes = 0
  address_new = 8,488
  address_reused = 25,330
  address_evicted = 0
  resident_descriptor_bytes_max = 34,766,848

descriptor_order:
  policy = layer_prior_frequency
  execution_mode = two_level_group_plan
  metrics_mode = count_only
  gate_allow = 320 / 320
  build_us_mean = 54.823
```

Mixed-summary verifier:

```bash
env PYTHONPATH=src \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/summarize_runtime_shadow_mixed_diag.py \
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_diag8/runtime_shadow.jsonl \
  --strict \
  --output-json data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_diag8/mixed_shadow_summary.json \
  --output-md data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_premap_manager_diag8/mixed_shadow_summary.md
```

This validates that outcome aggregate, descriptor-order minimal/count-only,
decoder layer timing, and premap manager counters can coexist in one online
shadow file.  Because this config used `max_tokens=1`, all decoder layer timing
rows are phase-tagged as prefill by the current `num_tokens` heuristic; this is
a diagnostic tag, not a protocol-level phase guarantee.

True gen64/decode diagnostic config:

```text
configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_manager_diag.yaml
```

Run:

```bash
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/trace_router_mtp_vllm.py \
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_manager_diag.yaml
```

Mixed-summary verifier:

```bash
env PYTHONPATH=src \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/summarize_runtime_shadow_mixed_diag.py \
  data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_manager_diag/runtime_shadow.jsonl \
  --strict \
  --require-decode-phase \
  --output-json data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_manager_diag/mixed_shadow_summary.json \
  --output-md data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_manager_diag/mixed_shadow_summary.md
```

Result:

```text
runtime_shadow rows = 102,400
event_counts:
  decoder_layer_timing = 20,480
  descriptor_layer_timing = 20,480
  descriptor_summary_min = 20,480
  outcome_aggregate = 20,480
  premap_summary = 20,480

Note: `descriptor_layer_timing` was emitted by the run above through the
existing default descriptor-layer timing path.  The config has since been made
explicit with `emit_descriptor_layer_timing: false` for future runs; the mixed
summary strict checker allows old artifacts with descriptor-layer timing only
when its count matches `decoder_layer_timing`.

decoder layer timing:
  decode rows = 20,160
  decode elapsed_us p50 / p95 / p99 = 3091.191 / 3514.783 / 3701.171
  prefill rows = 320
  prefill has first-token/JIT outliers, including layer0 sample0 max = 342,299.943 us

outcome aggregate:
  top_k = 8
  routed_expert_count sum = 190,215
  routed_expert_count p50 / p95 / p99 = 8 / 8 / 81

premap/address manager:
  descriptor_count = 190,215
  actual_bytes = 779,120,640
  payload_bytes = 0
  address_new = 8,939
  address_reused = 181,276
  address_evicted = 0
  resident_descriptor_bytes_max = 36,614,144
  reuse_rate p50 / p95 / p99 = 0.916 / 0.951 / 0.953
  premap_build_us p50 / p95 / p99 = 22.874 / 27.122 / 154.928

descriptor_order:
  policy = layer_prior_frequency
  execution_mode = two_level_group_plan
  metrics_mode = count_only
  gate_allow = 20,480 / 20,480
  build_us p50 / p95 / p99 = 34.546 / 45.718 / 55.807
```

Interpretation:

```text
The online premap/address path now scales from sample/layer smoke to true
decode-token/layer events while keeping payload movement disabled.  The current
address manager capacity is sufficient for this 8-sample gen64 run:
resident descriptors stay around 36.6MB and no address eviction occurs.

This is telemetry/evidence for premap descriptor/address preparation only.
It is not a full_fetch payload-transfer result and it does not alter router,
descriptor order execution, or vLLM kernels.

Scale-up mixed diagnostics:

```text
configs/trace/router_mtp_trace_external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_premap_manager_diag.yaml
configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_premap_manager_diag.yaml
```

Both runs pass:

```bash
env PYTHONPATH=src \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/summarize_runtime_shadow_mixed_diag.py <runtime_shadow.jsonl> \
  --strict \
  --require-decode-phase \
  --output-json <mixed_shadow_summary.json> \
  --output-md <mixed_shadow_summary.md>
```

Scale comparison:

| samples | rows | event count each | decode p50/p95/p99 us | premap reuse p50/p95/p99 | resident MB max | premap build p50/p95/p99 us | descriptor build p50/p95/p99 us | new/reused/evicted |
| ---: | ---: | ---: | --- | --- | ---: | --- | --- | --- |
| 8 | 102,400 | 20,480 | 3091.2 / 3514.8 / 3701.2 | 0.916 / 0.951 / 0.953 | 34.9 | 22.9 / 27.1 / 154.9 | 34.5 / 45.7 / 55.8 | 8,939 / 181,276 / 0 |
| 32 | 327,680 | 81,920 | 3562.9 / 3953.9 / 5328.8 | 0.975 / 0.986 / 0.987 | 38.6 | 25.6 / 30.8 / 165.6 | 37.8 / 52.9 / 62.6 | 9,886 / 752,041 / 0 |
| 128 | 1,304,960 | 326,240 | 3676.9 / 6044.4 / 11363.7 | 0.993 / 0.997 / 0.997 | 39.6 | 25.7 / 41.1 / 179.4 | 38.3 / 58.4 / 106.8 | 10,127 / 3,045,065 / 0 |

Interpretation:

```text
Premap address reuse strengthens with scale and saturates under the current
16,384-entry address capacity.  Resident descriptor/address footprint remains
bounded at about 40MB, with zero evictions through the 128-sample gen64 run.

Premap descriptor construction stays low in the median, while manager counter
updates remain the heavier online shadow cost. Descriptor-order count_only build
time is stable in p50/p95, with a larger p99 tail at 128 samples.

Decoder timing rows are useful for diagnostic distribution tracking, but these
mixed runs are not production timing claims: they still include online shadow,
runtime logging, first-shape JIT/warmup outliers, and the current num-token
phase heuristic.
```

Premap address capacity sensitivity:

The capacity sweep is replayed from the same 128-sample vLLM gen64 trace
contract, not from the older sample/layer descriptor artifact.  The replay
reconstructs one current-router premap event per `router_call_meta` entry and
one address descriptor per unique routed expert in that token/layer event.

```bash
env PYTHONPATH=src \
  /home/husrcf/anaconda3/envs/TRY/bin/python \
  scripts/replay_vllm_trace_premap_address_capacity.py \
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_premap_manager_diag/manifest.jsonl \
  --capacity 4096 8192 12288 16384 unbounded \
  --fast-address-only \
  --output-json outputs/reports/prefetch_action_replay/premap_address_capacity_vllm_trace_dolly128_gen64_gpu1/sensitivity.json \
  --output-md outputs/reports/prefetch_action_replay/premap_address_capacity_vllm_trace_dolly128_gen64_gpu1/sensitivity.md
```

Sanity:

```text
8-sample fast replay at capacity=16384 exactly matches the online mixed summary:
  descriptor_count = 190,215
  new/reused/evicted = 8,939 / 181,276 / 0
  resident_descriptor_bytes = 36,614,144
```

128-sample result:

| capacity | events | descriptors | reuse_rate | resident_addr | resident_MB | max_resident_MB | evicted | eviction_pressure | payload_bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4096 | 326,240 | 3,055,192 | 0.826910 | 4096 | 16.000 | 16.000 | 524,727 | 0.992254 | 0 |
| 8192 | 326,240 | 3,055,192 | 0.981336 | 8192 | 32.000 | 32.000 | 48,831 | 0.856339 | 0 |
| 12288 | 326,240 | 3,055,192 | 0.996685 | 10,127 | 39.559 | 39.559 | 0 | 0.000000 | 0 |
| 16384 | 326,240 | 3,055,192 | 0.996685 | 10,127 | 39.559 | 39.559 | 0 | 0.000000 | 0 |
| unbounded | 326,240 | 3,055,192 | 0.996685 | 10,127 | 39.559 | 39.559 | 0 | 0.000000 | 0 |

Interpretation:

```text
The minimum no-eviction address budget for this Dolly128 gen64 current-router
premap stream is 12,288 address entries.  The active address universe is only
10,127 layer/expert pairs, corresponding to about 39.6MB of descriptor/address
metadata at 4096 bytes per prepared descriptor.

8,192 entries already achieves high reuse (98.1%) but still evicts 48,831
addresses, so it is a low-footprint/evicting budget, not the no-eviction gate.
4,096 entries is too small for the long-run audit stream.
```

Premap address capacity gate artifact:

```text
configs/runtime/premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml
```

The artifact records:

```text
recommended_capacity_entries = 12288
active_address_count = 10127
recommended_resident_descriptor_mb = 39.559
low_footprint_capacity_entries = 8192
low_footprint_risk = evicting
payload_bytes_required = 0
address_key_scope = layer_expert
```

The 32/128 gen64 mixed diagnostic configs now reference this artifact:

```text
premap_address_capacity_gate_path:
  configs/runtime/premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml
```

`trace_router_mtp_vllm.py` resolves the artifact at config load time and fills:

```text
premap_address_manager_capacity = 12288
premap_address_capacity_gate_id =
  premap_address_capacity_dolly128_gen64_awq_w7900_gpu1
```

This removes hand-written capacity literals from the runtime shadow configs and
keeps the online premap-address manager budget tied to the evidence artifact.

Gate-resolved online smoke:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_premap_manager_gate_smoke.yaml

performance_summary:
  runtime_shadow_premap_address_manager_capacity = 12288
  runtime_shadow_premap_address_capacity_gate_id =
    premap_address_capacity_dolly128_gen64_awq_w7900_gpu1
  runtime_shadow_premap_address_capacity_gate_path =
    configs/runtime/premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml
```

Strict mixed summary for the same smoke:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_premap_manager_gate_smoke/
    mixed_shadow_summary.json

rows = 327,680
event counts:
  decoder_layer_timing   = 81,920
  descriptor_summary_min = 81,920
  outcome_aggregate      = 81,920
  premap_summary         = 81,920

premap:
  descriptor_count = 761,927
  payload_bytes = 0
  new / reused / evicted = 9,886 / 752,041 / 0
  resident_descriptor_bytes_max = 40,493,056
```

Interpretation:

```text
The 12,288-entry gate artifact is now parsed by the online runtime path and
recorded in performance_summary.  The 32-sample smoke stays below the gate
budget with zero evictions, confirming that the runtime summary is using the
artifact-derived capacity rather than a hand-written inline capacity.
```

Default long-run audit config:

```text
configs/trace/
  router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml
```

This config carries the premap address-manager counters into the default
long-run audit path:

```text
writer_mode = jsonl_batched
record_router_topk = true
outcome_logging_mode = aggregate
emit_premap_summaries = true
emit_premap_address_manager_counters = true
premap_address_capacity_gate_path =
  configs/runtime/premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml
descriptor_order_event_mode = minimal
descriptor_order_metrics_mode = count_only
```

`record_router_topk=true` is intentional here: current-router premap summaries
need the true top-k stream in order to build address descriptors.  This config
is therefore a low-overhead audit/telemetry path, not a production-like TPOT
baseline.  Production-like latency baselines should keep top-k row recording
and premap audit summaries disabled.

Heavy timing remains off in the default audit config:

```text
emit_decoder_layer_timing = false
emit_decoder_component_timing = false
emit_moe_substage_timing = false
emit_engine_timing = false
emit_wna16_kernel_timing = false
decoder_source_timing_mode = off
moe_source_timing_mode = off
```

The strict mixed diagnostic configs keep decoder timing enabled when latency
distribution evidence is needed; the default long-run audit config is for
low-overhead online telemetry and premap-address manager stability.
```

Long-run audit scale check:

```text
configs:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

summaries:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_summary.json
  data/traces/
    external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_summary.json
```

Both runs use the same Dolly128-derived artifact gate:

```text
runtime_shadow_premap_address_manager_capacity = 12288
runtime_shadow_premap_address_capacity_gate_id =
  premap_address_capacity_dolly128_gen64_awq_w7900_gpu1
```

Boundary:

```text
The 512-sample run is a same-source scale-validation check.  It intentionally
reuses the Dolly128-derived gate to test whether the existing budget remains
stable at larger audit scale.  It is not a 512-sample gate recalibration.
```

| samples | rows | descriptor_summary_min | outcome_aggregate | premap_summary | premap descriptors | new | reused | evicted | max resident addresses | max resident MB | reuse p50 | reuse p95 | reuse p99 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 978,720 | 326,240 | 326,240 | 326,240 | 3,055,192 | 10,127 | 3,045,065 | 0 | 10,127 | 39.559 | 0.9934 | 0.9965 | 0.9967 |
| 512 | 3,905,640 | 1,301,880 | 1,301,880 | 1,301,880 | 12,226,516 | 10,202 | 12,216,314 | 0 | 10,202 | 39.852 | 0.9983 | 0.9991 | 0.9992 |

Timing counters in the low-overhead audit path:

| samples | premap_build_us p50/p95/p99 | counter_update_us p50/p95/p99 | descriptor_order_build_us p50/p95/p99 |
|---:|---:|---:|---:|
| 128 | 25.990 / 66.377 / 184.795 | 1306.169 / 5220.444 / 5979.729 | 38.043 / 106.435 / 119.971 |
| 512 | 25.419 / 61.100 / 186.642 | 1302.730 / 4661.279 / 5984.788 | 37.477 / 80.557 / 115.277 |

Interpretation:

```text
The premap address-manager counters are stable from 128 to 512 samples under
the default long-run audit config.  The 12,288-entry gate remains sufficient:
512 samples increase the active address universe only slightly from 10,127 to
10,202 entries, with zero evictions and no payload bytes.

Reuse improves with longer runs because the layer/expert address universe is
almost saturated after the early stream.  Premap build and descriptor-order
count_only build remain stable in p50/p95/p99.  The heavier per-event
counter_update_us is still the main audit overhead component, but it does not
grow with scale in the 128 -> 512 check.
```

Capacity replay validation on the long-run audit traces:

```text
artifacts:
  outputs/reports/prefetch_action_replay/
    premap_address_capacity_vllm_trace_dolly128_gen64_longrun_validation/
    sensitivity.json
  outputs/reports/prefetch_action_replay/
    premap_address_capacity_vllm_trace_dolly512_gen64_gpu1_validation/
    sensitivity.json
```

| samples | capacity | reuse_rate | max resident addresses | max resident MB | evicted | payload bytes |
|---:|---:|---:|---:|---:|---:|---:|
| 128 | 8192 | 0.981336 | 8192 | 32.000 | 48,831 | 0 |
| 128 | 10240 | 0.996685 | 10,127 | 39.559 | 0 | 0 |
| 128 | 12288 | 0.996685 | 10,127 | 39.559 | 0 | 0 |
| 512 | 4096 | 0.825279 | 4096 | 16.000 | 2,132,134 | 0 |
| 512 | 8192 | 0.983184 | 8192 | 32.000 | 197,406 | 0 |
| 512 | 10240 | 0.999166 | 10,202 | 39.852 | 0 | 0 |
| 512 | 12288 | 0.999166 | 10,202 | 39.852 | 0 | 0 |

Interpretation:

```text
The same-source long-run traces show that 10,240 entries are already enough for
zero eviction on both Dolly128 and Dolly512 gen64 audit streams.  The current
default gate remains at 12,288 entries intentionally: it is a conservative
Dolly128-derived artifact budget with roughly 20% slack over the observed
10,202-entry Dolly512 active address universe.

Do not treat this as a cross-distribution recalibration.  It is a same-source
capacity validation showing that the selected 12,288-entry default is safe and
that 8,192 remains an evicting low-footprint budget.
```

## Premap consumer mapping no-op gate

Implemented a no-op fused-MoE/AWQ consumer mapping assertion for the premap
address path.

Runtime contract:

```text
BaseRouter/current-router premap summary
  -> ControlledPremapAddressManager prepares descriptor/address handles

fused-MoE/AWQ _prepare_expert_assignment consumer handle
  -> map (layer_id, expert_id) to the same premap address key
  -> record resident hit/miss + parity
  -> do not modify tensors
  -> do not move payload bytes
  -> do not change router or descriptor_order execution
  -> do not credit readiness
```

New event:

```text
event_type = premap_consumer_mapping
premap_consumer_mapping_mode = noop_assertion
premap_consumer_mapping_source = fused_moe_prepare_expert_assignment
premap_consumer_address_hit_count / miss_count
premap_consumer_all_hit
premap_consumer_parity_ok
premap_consumer_payload_bytes = 0
premap_consumer_changes_router = false
premap_consumer_changes_descriptor_order = false
premap_consumer_ready_credit = false
```

AWQ/vLLM GPU1 smoke:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/
```

Summary:

| metric | value |
|---|---:|
| runtime_shadow rows | 102,400 |
| descriptor_summary_min | 20,480 |
| outcome_aggregate | 20,480 |
| premap_summary | 20,480 |
| premap_consumer_mapping | 20,480 |
| premap_consumer_address_hit_count | 190,215 |
| premap_consumer_address_miss_count | 0 |
| premap_consumer_address_hit_rate | 1.0 |
| premap_consumer_all_hit_rate | 1.0 |
| premap_consumer_parity_ok_rate | 1.0 |
| premap_consumer_error_count | 0 |
| premap_consumer_payload_violation_count | 0 |
| premap_consumer_router_change_violation_count | 0 |
| premap_consumer_descriptor_order_change_violation_count | 0 |
| premap_consumer_ready_credit_violation_count | 0 |
| premap_address_resident_count_max | 8,939 |
| premap_address_evicted_count | 0 |

The performance summary records:

```text
runtime_shadow_emit_premap_consumer_mapping = true
runtime_shadow_premap_consumer_mapping_mode = noop_assertion
runtime_shadow_premap_consumer_mapping_source =
  fused_moe_prepare_expert_assignment
runtime_shadow_premap_address_manager_capacity = 12288
runtime_shadow_premap_address_capacity_gate_id =
  premap_address_capacity_dolly128_gen64_awq_w7900_gpu1
```

Interpretation:

```text
The real fused-MoE/AWQ consumer handle now maps cleanly onto the current
premap address-key contract.  In the 8-sample smoke, every consumer-side
(layer, expert) key was already resident in the controlled premap address
manager, and the consumer key set matched the latest current-router premap
producer key set for each layer.

This is a mapping/parity gate only.  It does not claim payload readiness,
latency improvement, or endpoint TPOT gain.
```

## Premap descriptor/address handle-object gate

Extended the premap consumer mapping from an address-key assertion to a
descriptor/address handle-object assertion.

Runtime handle contract:

```text
address_key
  -> PremapAddressHandle
       descriptor_ptr
       packed_weight_descriptor
       scale_metadata_handle
       descriptor_bytes
       payload_bytes = 0
```

The handle is deliberately metadata-only:

```text
no payload transfer
no ready credit
no router mutation
no descriptor_order execution
no kernel argument mutation
```

## Native stub online invocation canary gate

The premap consumer path now has a live-disabled native-stub invocation canary.
The prelaunch shim builds the typed handle-table package that a future native
consumer would receive and runs the in-process native typed bridge checker on
that exact table, but still blocks the actual native stub launch.

Strict GPU1 AWQ/vLLM 128-sample gate:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate_native_stub_online_invocation_canary.json

passed = true
failures = []
native_stub_online_invocation_checked = 10,195
native_stub_online_invocation_ready = 10,195
native_stub_online_invocation_ok = 10,195
native_checker_invoked = 10,195
native_bridge_ok = 10,195
native_stub_invoked = 0
blocked = 10,195
block_reason = native_stub_live_disabled

row_count = 110,898
column_count_min/max = 4 / 4
required_handle_nonzero_count = 332,694
required_handle_zero_count = 0
optional_handle_nonzero_count = 110,898
expert_id_invalid_count = 0
address_key_hash_zero_count = 0
failure_count = 0

payload_bytes = 0
ready_credit_count = 0
changes_router_count = 0
changes_descriptor_order_count = 0
passed_to_kernel_count = 0
kernel_arg_violation_count = 0
```

Review fixes included in this gate:

```text
1. The table object hash and native bridge metadata now include ready_credit,
   changes_router, and changes_descriptor_order, so the canary independently
   preserves the no-op boundary.

2. The canary recomputes the current table input hash and rejects stale native
   bridge checks that do not match the current table object/schema/row layout.

3. The default lab preflight now performs content-level checks for the native
   bridge and native-stub evidence JSONs instead of accepting any passed JSON.
   It verifies mode, counts, payload=0, ready/router/order no-op counts,
   native_stub_invoked=0, blocked count, and block reason.
```

The default lab readonly gate now requires:

```text
require_native_stub_online_invocation_canary = true
mode = readonly_native_stub_online_invocation_canary
block_reason = native_stub_live_disabled
native_stub_invoked = 0
payload_bytes = 0
ready_credit = false
changes_router = false
changes_descriptor_order = false
passed_to_kernel = false
changes_kernel_launch_args = false
```

This is still a live-disabled canary, not a real kernel handoff.  It validates
that the online prelaunch path can construct and check the future native
consumer package without mutating the real WNA16 launch.

## Native typed consumer stub canary

The default lab preflight now also requires a real HIP/C++ typed consumer stub
canary.  This is separate from the online prelaunch shim: it feeds a prepared
native bridge input into the standalone native consumer stub under explicit
debug macros, while still forbidding payload dereference and kernel-arg pass.

Evidence:

```text
stub:
  microbench/premap_kernel_consumer/premap_typed_consumer_stub.hip

runner:
  scripts/run_premap_typed_consumer_stub.py

input:
  outputs/reports/premap_kernel_consumer/native_bridge_input_latest.json

artifact:
  outputs/reports/premap_kernel_consumer/
    typed_consumer_stub_gpu1_from_native_bridge_input_canary.json

ok = true
row_count = 2
row_ok_count = 2
error_count = 0
column_count = 4
input_source = binary_prefix
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
expected_schema_hash =
  c1384d55958c9aa78b07b4ee3e9094f835ec1ca4c61bd7e9613c01ceb8275e98
```

Compiled macro ladder:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA = true
MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION = true
MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY = true
MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME = true
MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR = true

MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF = forbidden
MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS = forbidden
```

The lab preflight now performs content-level checks on this stub artifact:

```text
native_typed_consumer_stub_canary_required = true
stub input_json == native_typed_consumer_bridge_input_json
stub row_count == native bridge input _meta.row_count
stub column_count == native bridge input _meta.column_count
native bridge input _meta.schema_hash == handle-table schema hash
native bridge input row-field lengths == stub row_count
ok = true
row_ok_count == row_count
error_count = 0
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
all required debug macros enabled
forbidden payload/kernel-arg macros absent
```

This establishes a lower-level native typed-consumer canary, but it remains
disconnected from the live WNA16 fused-MoE kernel and from the online prelaunch
kernel argument path.

### 2026-05-26: Single-field kernel-arg replacement live gate remains default-disabled

The next kernel-argument handoff layer is now wired as an explicit gate:

```text
single-field dry-run:
  construct a candidate replacement for one future kernel argument field
  compare runtime identity signature
  do not pass it to the kernel

single-field live replacement:
  exists as a runtime/config/checker flag
  defaults to disabled
  requires an explicit checker allow flag before any live canary can pass
```

The default-disabled gate is now enforced by checker counters, not only by
configuration:

```text
if dry_run_enabled and live_enabled == false:
  live_disabled_count == dry_run_candidate_count
  live_candidate_count == 0
  live_replaced_count == 0
  live_parity_ok_count == 0
  live_parity_mismatch_count == 0
  live_passed_to_kernel_count == 0
  live_payload_bytes == 0
```

1-sample AWQ canary:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_single_field_replacement_dry_run_canary.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_single_field_replacement_dry_run_canary/
    single_field_replacement_dry_run_gate_check.json

passed = true
failures = []
dry_run_enabled = true
live_enabled = false
field = B_scale
dry_run_candidate_count = 1,280
dry_run_parity_ok_count = 1,280
dry_run_passed_to_kernel_count = 0
live_disabled_count = 1,280
live_candidate_count = 0
live_replaced_count = 0
live_passed_to_kernel_count = 0
live_payload_bytes = 0
```

This advances the handoff stack to the next boundary while preserving the lab
precondition:

```text
future live replacement is representable and explicitly gated
default lab/audit runs cannot accidentally replace a kernel argument field
payload transfer remains 0
kernel argument mutation remains disabled unless explicitly allowed
```

### 2026-05-26: Explicit single-field live replacement canary passed

After the default-disabled gate, a 1-sample explicit live canary was run with
the checker allow flag enabled.  This is still an identity replacement of the
same runtime `B_scale` object, so it validates the handoff source transition and
counters without introducing payload movement or semantic handle replacement.

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_single_field_replacement_live_canary.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_single_field_replacement_live_canary/
    single_field_replacement_live_gate_check.json

checker:
  --allow-single-field-replacement-live

passed = true
failures = []
dry_run_enabled = true
live_enabled = true
field = B_scale
dry_run_candidate_count = 1,280
dry_run_parity_ok_count = 1,280
dry_run_passed_to_kernel_count = 0
live_disabled_count = 0
live_candidate_count = 1,280
live_replaced_count = 1,280
live_parity_ok_count = 1,280
live_passed_to_kernel_count = 1,280
live_payload_bytes = 0
```

Boundary:

```text
the live canary requires explicit checker allow
the replacement candidate is runtime-identity equal to the original field
payload transfer remains 0
this is not yet semantic descriptor/address handle replacement
```

### 2026-05-26: 128-sample strict single-field live replacement gate passed

The explicit single-field live canary was scaled from the 1-sample smoke to the
128-sample strict lab gate.  This keeps the same conservative boundary as the
smoke: the live field replacement is an identity replacement of the original
runtime `B_scale` object, not a semantic descriptor/address handle swap.

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_single_field_replacement_live_strict.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_single_field_replacement_live_strict/
    single_field_replacement_live_gate_check.json

checker:
  --allow-single-field-replacement-live

passed = true
failures = []
row_count = 20,390
premap_summary_count = 10,195
premap_consumer_mapping_count = 10,195

package_seen_count = 20,390
package_pass_through_count = 20,390
package_layer_mismatch_count = 0
package_block_reason_mismatch_count = 0

dry_run_enabled = true
live_enabled = true
dry_run_candidate_count = 20,390
dry_run_parity_ok_count = 20,390
dry_run_passed_to_kernel_count = 0

live_disabled_count = 0
live_candidate_count = 20,390
live_replaced_count = 20,390
live_parity_ok_count = 20,390
live_passed_to_kernel_count = 20,390
live_payload_bytes = 0

premap_address_resident_count_max = 10,127
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_eviction_pressure_mean = 0.0
```

Interpretation:

```text
the single-field live handoff layer is stable under the 128-sample strict gate
the replacement remains runtime-identity equivalent to the original field
the path still moves no payload and makes no endpoint-performance claim
next gate is semantic descriptor/address handle candidate sourcing before any
non-identity field replacement
```

## Kernel-arg live-pass canary smoke

The kernel-argument handoff path now has an explicit experimental live-pass
canary.  This is not the default lab gate and not a payload/ready/runtime
performance claim.  It only verifies that the prelaunch consumer adapter can
accept the mirrored kernel-argument package under an explicit gate contract.

New canary artifacts:

```text
trace config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_kernel_arg_pass_canary.yaml

readonly gate:
  configs/runtime/
    premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_kernel_arg_pass_canary.yaml

runtime output:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_kernel_arg_pass_canary/
      performance_summary.json
      kernel_arg_pass_gate_check.json
      kernel_arg_pass_default_reject_check.json
```

Explicit live-pass checker:

```text
checker flags:
  --require-kernel-arg-handoff-live-toggle
  --require-kernel-arg-handoff-launch-schema-mirror
  --require-kernel-arg-handoff-live-noop-integration
  --require-kernel-arg-handoff-live-consumer-adapter
  --allow-enabled-blocked-live-toggle
  --allow-connected-blocked-consumer-adapter
  --allow-kernel-arg-handoff-live-kernel-arg-pass

passed = true
failures = []
premap_summary_count = 640
premap_consumer_mapping_count = 640

live_consumer_adapter_checked = 640
live_consumer_adapter_blocked = 0
live_consumer_adapter_block_reason =
  kernel_arg_handoff_kernel_arg_pass_live
live_consumer_adapter_passed_to_kernel_count = 640
live_consumer_adapter_changes_kernel_launch_args_count = 640
live_consumer_adapter_contract_live_pass_count = 640
live_consumer_adapter_real_kernel_arg_handoff_count = 0
live_consumer_adapter_payload_bytes = 0

live_noop_integration_block_reason =
  kernel_arg_handoff_kernel_arg_pass_disabled
live_noop_integration_passed_to_kernel_count = 0
consumer_shim_table_consume_passed_to_kernel_count = 0
premap_summary_payload_bytes = 0
premap_consumer_ready_credit_violation_count = 0
```

Default strict checker still fails closed without the live-pass allow flag:

```text
passed = false
failures include:
  kernel_arg_handoff_kernel_arg_pass_enabled_true
  consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_mismatch
  consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked_count_mismatch
  consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count_mismatch
  consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count_mismatch
  consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass_count_mismatch
```

Validation:

```text
pytest tests/test_runtime_premap.py \
       tests/test_vllm_premap_capacity_gate.py \
       tests/test_check_premap_longrun_audit_gate.py -q

138 passed
```

8-sample live-pass canary:

```text
trace config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_kernel_arg_pass_canary.yaml

runtime output:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_kernel_arg_pass_canary/
      performance_summary.json
      kernel_arg_pass_gate_check.json

checker with explicit live-pass allow:
  passed = true
  failures = []

runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled = true
premap_summary_count = 640
premap_consumer_mapping_count = 640

live_consumer_adapter_checked = 640
live_consumer_adapter_blocked = 0
live_consumer_adapter_passed_to_kernel_count = 640
live_consumer_adapter_changes_kernel_launch_args_count = 640
live_consumer_adapter_contract_live_pass_count = 640
live_consumer_adapter_real_kernel_arg_handoff_count = 0
live_consumer_adapter_payload_bytes = 0

live_noop_integration_passed_to_kernel_count = 0
consumer_shim_table_consume_passed_to_kernel_count = 0
premap_summary_payload_bytes = 0
premap_consumer_ready_credit_violation_count = 0
```

Boundary:

```text
This is an adapter/mirror live-pass envelope.  The explicit
`contract_live_pass_count` records that the prelaunch adapter accepted the
mirrored package, while `real_kernel_arg_handoff_count = 0` records that this
is still not a real fused-MoE/AWQ launch-argument mutation.

It still does not move payload, grant ready credit, mutate router outputs, run
descriptor_order execution, or pass a new argument package into the real fused
MoE/AWQ kernel launch.
```

## 2026-05-25 - 128-Sample Launch-Schema Mirror Gate Promoted

The kernel-arg handoff mirror is now checked against an explicit future launch
schema mirror under the 128-sample Dolly AWQ GPU1 lab-default audit.

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

gate artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate.json

gate config:
  configs/runtime/
    premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml
```

Result:

```text
passed = true
failures = []
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_resident_count_max = 10,127
premap_address_eviction_pressure_mean = 0.0

kernel_arg_handoff_launch_schema_mirror_checked = 10,195
kernel_arg_handoff_launch_schema_mirror_ready = 10,195
kernel_arg_handoff_launch_schema_mirror_row_count = 110,898
kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count = 91,755

launch_schema_name =
  fused_moe_awq_wna16_prelaunch_descriptor_address_v1
launch_schema_hash =
  576c83df9f825786d494ae3fe1f2286fcbae1afc876b243e748bae8e5b804984

payload_bytes = 0
passed_to_kernel_count = 0
kernel_arg_violation_count = 0
```

The lab precondition now requires:

```text
readonly consumer
real descriptor prep
kernel-arg shadow table
consumer shim table read/consume/object
prep execution dry-run
kernel-arg handoff attempt
kernel-arg live toggle
kernel-arg launch-schema mirror
```

This still does not pass kernel args, move payload, grant ready credit, mutate the
router, or change descriptor order.  It only validates that the prepared handle
table can be mirrored into the schema shape a future fused-MoE/AWQ prelaunch
consumer would receive.

Follow-up reproducibility fix:

```text
scripts/check_premap_longrun_audit_gate.py now accepts the generated
longrun_audit_gate.json as an input artifact, not only raw performance_summary.json.

The backfill path is restricted to gate reports that already say:
  passed = true
  failures = []

Failed gate reports are not backfilled, so the strict checker cannot turn a
failed artifact into a passing artifact by adding derived counters.
```

The fused-MoE/AWQ consumer mapping now resolves the resident
`PremapAddressHandle` object for each `(layer_id, expert_id)` key and records a
handle hash parity check against the latest current-router premap summary.

GPU1 AWQ/vLLM smoke artifact:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/
```

Summary:

| metric | value |
|---|---:|
| runtime_shadow rows | 102,400 |
| premap_consumer_mapping | 20,480 |
| premap_consumer_address_hit_count | 190,215 |
| premap_consumer_address_miss_count | 0 |
| premap_consumer_address_hit_rate | 1.0 |
| premap_consumer_descriptor_handle_hit_count | 190,215 |
| premap_consumer_descriptor_handle_miss_count | 0 |
| premap_consumer_descriptor_handle_hit_rate | 1.0 |
| premap_consumer_parity_ok_rate | 1.0 |
| premap_consumer_descriptor_handle_parity_ok_rate | 1.0 |
| premap_consumer_error_count | 0 |
| premap_consumer_payload_violation_count | 0 |
| premap_consumer_router_change_violation_count | 0 |
| premap_consumer_descriptor_order_change_violation_count | 0 |
| premap_consumer_ready_credit_violation_count | 0 |
| premap_address_resident_count_max | 8,939 |
| premap_address_evicted_count | 0 |

Interpretation:

```text
The real fused-MoE/AWQ consumer-side mapping can now resolve stable
descriptor/address handle objects from the controlled premap address manager.
The resolved handle set has exact parity with the latest current-router premap
producer summary, and all handles remain metadata-only with payload_bytes=0.

This advances the no-op mapping gate from key presence to usable handle
resolution.  It is still not a payload-readiness claim and not an endpoint
performance claim.
```

## Premap prepare-before-consumer ordering gate

Added a lightweight ordering audit to the premap consumer mapping event.

New consumer fields:

```text
premap_consumer_expected_prepare_plan_count
premap_consumer_observed_prepare_plan_count
premap_consumer_expected_prepare_record_count
premap_consumer_observed_prepare_record_count
premap_consumer_lookup_after_prepare
```

Semantics:

```text
current-router premap producer:
  records the manager prepare-plan / prepare-record counters after preparing
  the layer's descriptor/address handles

fused-MoE/AWQ consumer mapping:
  reads the manager counters at lookup time
  requires observed >= expected for both plan and record counters
  folds lookup_after_prepare into premap_consumer_parity_ok
```

This closes a small but important audit gap:

```text
handle_hit/parity now means:
  the consumer resolved the expected descriptor/address handle set
  and the lookup happened after the corresponding premap preparation point

It does not mean:
  payload is ready
  H2D transfer happened
  vLLM kernel arguments were changed
  endpoint latency improved
```

Validation:

```text
focused:
  82 passed

full:
  417 passed, 2 warnings

GPU1 AWQ/vLLM smoke:
  runtime_shadow_aggregate_premap_consumer_mapping_count = 20480
  runtime_shadow_aggregate_premap_consumer_address_hit_rate = 1.0
  runtime_shadow_aggregate_premap_consumer_descriptor_handle_hit_rate = 1.0
  runtime_shadow_aggregate_premap_consumer_parity_ok_rate = 1.0
  runtime_shadow_aggregate_premap_consumer_descriptor_handle_parity_ok_rate = 1.0
  runtime_shadow_aggregate_premap_consumer_lookup_after_prepare_rate = 1.0
  runtime_shadow_aggregate_premap_consumer_error_count = 0
  runtime_shadow_aggregate_premap_consumer_payload_violation_count = 0
  runtime_shadow_aggregate_premap_consumer_router_change_violation_count = 0
  runtime_shadow_aggregate_premap_consumer_descriptor_order_change_violation_count = 0
  runtime_shadow_aggregate_premap_consumer_ready_credit_violation_count = 0
```

## Premap real vLLM/AWQ descriptor-handle no-op gate

Extended the premap consumer mapping smoke with an optional real-handle resolver:

```text
premap_consumer_resolve_real_handles = true
```

At the fused-MoE/AWQ consumer handle, the audit path now tries to resolve the
actual routed-expert tensor handles on the live vLLM layer without mutating them:

```text
CompressedTensorsWNA16 path:
  w13_weight_packed
  w2_weight_packed
  w13_weight_scale
  w2_weight_scale

AutoGPTQ/WNA16-compatible path:
  w13_qweight / w2_qweight
  w13_scales / w2_scales
  optional qzeros/g_idx handles when present
```

The handle hash is built from metadata only:

```text
expert id / local expert id
attribute name
shape / dtype / device
per-expert tensor data_ptr
```

It does not copy tensor payload, does not dereference or move expert weights,
and does not change vLLM kernel arguments.

GPU1 AWQ/vLLM smoke:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/

runtime_shadow_aggregate_premap_consumer_mapping_count = 20480
runtime_shadow_aggregate_premap_consumer_address_hit_rate = 1.0
runtime_shadow_aggregate_premap_consumer_descriptor_handle_hit_rate = 1.0
runtime_shadow_aggregate_premap_consumer_lookup_after_prepare_rate = 1.0
runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_hit_rate = 1.0
runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_available_rate = 1.0
runtime_shadow_aggregate_premap_consumer_error_count = 0
```

First consumer event sanity:

```text
premap_consumer_descriptor_handle_hit_count = 174
premap_consumer_real_descriptor_handle_hit_count = 174
premap_consumer_real_descriptor_handle_miss_count = 0
premap_consumer_real_descriptor_handle_available = true
premap_consumer_lookup_after_prepare = true
premap_consumer_parity_ok = true
```

Interpretation:

```text
The no-op premap path now reaches the real vLLM/AWQ descriptor/address object
boundary: every consumer-side active expert can resolve both the controlled
premap handle and the corresponding live packed-weight/scale tensor handle.

This is still a handle-resolution gate only.  It is not a payload-transfer gate,
not a readiness gate, and not an endpoint performance claim.
```


## Premap read-only cache-manager consumer contract

Promoted premap consumer mapping from one-shot handle resolution to a read-only
cache-manager consumer contract.  The consumer event now audits three additional
properties:

```text
1. handle lifecycle:
   address_key -> real vLLM/AWQ descriptor handle binding is created once and
   reused on later consumer lookups.

2. eviction/miss behavior:
   if the controlled premap manager evicts an address key, consumer mapping
   reports a manager miss even when the live vLLM layer still exposes a valid
   packed-weight/scale handle.

3. stable binding:
   repeated lookups for the same address key must resolve to the same live
   descriptor-handle hash; mismatches are counted explicitly.
```

New counters:

```text
premap_consumer_real_descriptor_handle_new_binding_count
premap_consumer_real_descriptor_handle_reused_binding_count
premap_consumer_real_descriptor_handle_binding_mismatch_count
premap_consumer_real_descriptor_handle_for_address_miss_count
```

Validation:

```text
focused:
  tests/test_runtime_shadow_log.py
  tests/test_vllm_router_shadow_sink.py
  58 passed

full:
  418 passed, 2 warnings
```

Unit contract coverage:

```text
capacity=1 controlled manager:
  one active expert remains resident
  one active expert is evicted

expected behavior:
  controlled address hit_count = 1
  controlled address miss_count = 1
  descriptor handle hit_count = 1
  descriptor handle miss_count = 1
  real vLLM/AWQ handle hit_count = 2
  real handle for evicted address miss_count = 1
  parity_ok = false

second lookup over same live layer:
  new_binding_count = 0
  reused_binding_count = 2
  binding_mismatch_count = 0
```

GPU1 AWQ/vLLM smoke:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/

runtime_shadow_aggregate_premap_consumer_mapping_count = 20480
runtime_shadow_aggregate_premap_consumer_address_hit_rate = 1.0
runtime_shadow_aggregate_premap_consumer_descriptor_handle_hit_rate = 1.0
runtime_shadow_aggregate_premap_consumer_lookup_after_prepare_rate = 1.0
runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_hit_rate = 1.0
runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_available_rate = 1.0
runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_new_binding_count = 8939
runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_reused_binding_count = 181276
runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_binding_mismatch_count = 0
runtime_shadow_aggregate_premap_consumer_real_descriptor_handle_for_address_miss_count = 0
runtime_shadow_aggregate_premap_consumer_error_count = 0
```

First consumer row sanity:

```text
premap_consumer_address_hit_count = 174
premap_consumer_address_miss_count = 0
premap_consumer_descriptor_handle_hit_count = 174
premap_consumer_real_descriptor_handle_hit_count = 174
premap_consumer_real_descriptor_handle_new_binding_count = 174
premap_consumer_real_descriptor_handle_reused_binding_count = 0
premap_consumer_real_descriptor_handle_binding_mismatch_count = 0
premap_consumer_real_descriptor_handle_for_address_miss_count = 0
premap_consumer_parity_ok = true
```

Boundary remains unchanged:

```text
no payload transfer
no ready credit
no router mutation
no descriptor_order execution
no vLLM kernel argument mutation
```

## Premap consumer mapping sampled long-run gate

The first 32-sample real-handle consumer mapping run proved the read-only
contract at medium scale, but also exposed that row-level consumer mapping is too
heavy for default long-run audit:

```text
unsampled 32-sample run:
  premap_consumer_mapping_count = 81920
  address_hit_rate = 1.0
  descriptor_handle_hit_rate = 1.0
  lookup_after_prepare_rate = 1.0
  real_descriptor_handle_hit_rate = 1.0
  real_descriptor_handle_available_rate = 1.0
  real_descriptor_handle_binding_mismatch_count = 0
  real_descriptor_handle_for_address_miss_count = 0
  runtime_shadow rows ~= 409600
  runtime_shadow size ~= 460 MB
```

Added sampled consumer mapping:

```text
premap_consumer_mapping_sample_period:
  default = 1
  32-sample gate smoke = 8
  128-sample long-run audit = 32
  512-sample long-run audit = 64
```

Validation:

```text
focused:
  tests/test_vllm_router_shadow_sink.py
  tests/test_runtime_shadow_log.py
  60 passed

full:
  420 passed, 2 warnings
```

Sampled 32-sample GPU1 AWQ/vLLM run:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_premap_manager_gate_smoke/

premap_consumer_mapping_sample_period = 8
premap_consumer_mapping_count = 10240
premap_consumer_address_hit_rate = 1.0
premap_consumer_descriptor_handle_hit_rate = 1.0
premap_consumer_lookup_after_prepare_rate = 1.0
premap_consumer_real_descriptor_handle_hit_rate = 1.0
premap_consumer_real_descriptor_handle_available_rate = 1.0
premap_consumer_real_descriptor_handle_new_binding_count = 1244
premap_consumer_real_descriptor_handle_reused_binding_count = 94938
premap_consumer_real_descriptor_handle_binding_mismatch_count = 0
premap_consumer_real_descriptor_handle_for_address_miss_count = 0
premap_consumer_error_count = 0
runtime_shadow rows ~= 337920
runtime_shadow size ~= 299 MB
```

Interpretation:

```text
Sampling preserves the handle-lifecycle signal while reducing consumer mapping
rows by 8x in the 32-sample gate.  The remaining log volume is no longer driven
by consumer mapping; it comes from other per token/layer audit rows such as
outcome_aggregate, descriptor_summary_min, and premap_summary.  The 32-sample
config now disables decoder_layer_timing to keep it aligned with the long-run
low-intrusion audit contract.
```

## Premap summary sampled audit gate

The next row-volume bottleneck was `premap_summary`: even after consumer mapping
sampling, the manager summary still emitted one row per token/layer.  Added
`premap_summary_sample_period` with an important contract:

```text
premap address manager prepare/update still runs on every layer
premap_summary JSONL emission is sampled
consumer mapping still checks the latest prepared handle state
```

Configured sampling:

```text
premap_summary_sample_period:
  default = 1
  32-sample gate smoke = 8
  128-sample long-run audit = 32
  512-sample long-run audit = 64
```

Validation:

```text
focused:
  tests/test_vllm_router_shadow_sink.py
  tests/test_vllm_premap_capacity_gate.py
  61 passed

full:
  421 passed, 2 warnings
```

Sampled 32-sample GPU1 AWQ/vLLM run:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_premap_manager_gate_smoke/

premap_summary_sample_period = 8
premap_consumer_mapping_sample_period = 8

event counts:
  outcome_aggregate = 81920
  descriptor_summary_min = 81920
  premap_summary = 10240
  premap_consumer_mapping = 10240

premap_consumer_mapping_count = 10240
premap_consumer_address_hit_rate = 1.0
premap_consumer_descriptor_handle_hit_rate = 1.0
premap_consumer_lookup_after_prepare_rate = 1.0
premap_consumer_real_descriptor_handle_hit_rate = 1.0
premap_consumer_real_descriptor_handle_binding_mismatch_count = 0
premap_consumer_error_count = 0
runtime_shadow size ~= 179 MB
```

Interpretation:

```text
Premap summary sampling reduces premap_summary rows by another 8x without
dropping manager lifecycle updates.  The remaining 32-sample log volume is now
dominated by outcome_aggregate and descriptor_summary_min.  performance_summary
now also exports runtime_shadow_size_mb and flattened aggregate counts for
premap_summary / descriptor_summary_min / outcome_aggregate, so long-run audits
do not need a manual JSONL scan to verify row-volume gates.
```

## Premap-only long-run audit row-volume gate

The premap handle audit does not require outcome rows or descriptor_order rows.
Those are useful for broader runtime diagnostics, but they dominate row volume
and are orthogonal to the read-only descriptor/address handle contract.  The
32/128/512 premap-manager audit configs now use:

```text
emit_outcomes = false
outcome_logging_mode = "off"
emit_descriptor_order_summaries = false
emit_premap_summaries = true
emit_premap_consumer_mapping = true
sampled premap_summary + sampled premap_consumer_mapping
```

Validation:

```text
focused:
  tests/test_vllm_premap_capacity_gate.py
  tests/test_vllm_router_shadow_sink.py
  61 passed

full:
  421 passed, 2 warnings
```

Low-volume 32-sample GPU1 AWQ/vLLM run:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_premap_manager_gate_smoke/

premap_summary_sample_period = 8
premap_consumer_mapping_sample_period = 8

event counts:
  outcome_aggregate = 0
  descriptor_summary_min = 0
  premap_summary = 10240
  premap_consumer_mapping = 10240

runtime_shadow_size_mb = 36.60
premap_consumer_address_hit_rate = 1.0
premap_consumer_descriptor_handle_hit_rate = 1.0
premap_consumer_real_descriptor_handle_hit_rate = 1.0
premap_consumer_lookup_after_prepare_rate = 1.0
premap_consumer_real_descriptor_handle_binding_mismatch_count = 0
premap_consumer_error_count = 0
```

Interpretation:

```text
Premap-only long-run audit is now a low-volume handle-stability path rather
than a mixed runtime diagnostic.  At 32 samples the shadow log drops from the
previous sampled ~179 MB to ~36.6 MB while preserving the address/descriptor
handle lifecycle evidence.  This makes 128/512 premap handle audits practical:
the expected row count now scales with the sampled premap manager/consumer rows,
not with every outcome or descriptor_order summary.
```

512-sample GPU1 AWQ/vLLM long-run audit:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit/

premap_summary_sample_period = 64
premap_consumer_mapping_sample_period = 64

event counts:
  outcome_aggregate = 0
  descriptor_summary_min = 0
  premap_summary = 20342
  premap_consumer_mapping = 20342

runtime_shadow_size_mb = 72.99
premap_address_manager_count = 20342
premap_address_resident_count_max = 10202
premap_address_resident_descriptor_bytes_max = 41787392
premap_address_prepared_descriptor_actual_bytes_max = 50078007296
premap_address_reused_count = 12215874
premap_address_evicted_count = 0
premap_address_reuse_rate_mean = 0.9945098118
premap_address_eviction_pressure_mean = 0.0

premap_consumer_address_hit_rate = 1.0
premap_consumer_descriptor_handle_hit_rate = 1.0
premap_consumer_real_descriptor_handle_hit_rate = 1.0
premap_consumer_lookup_after_prepare_rate = 1.0
premap_consumer_real_descriptor_handle_binding_mismatch_count = 0
premap_consumer_error_count = 0
```

Interpretation:

```text
The premap-only audit contract scales to 512 samples with stable sampled row
volume and no handle/parity failures.  The Dolly128-derived 12288-capacity gate
is sufficient for this 512-sample same-source validation: no premap address
evictions are observed, resident descriptor bytes stay at ~41.8 MB, and
consumer lookup-after-prepare remains 1.0.

This remains a read-only descriptor/address preparation audit:
no payload transfer, no ready credit, no router mutation, and no descriptor
visitation order execution.
```

## Premap Read-Only Consumer Gate (2026-05-20)

The premap address capacity gate is now enforced as a real-vLLM integration precondition for the read-only cache-manager consumer shim.  A tracked gate artifact records the 512-sample Dolly/AWQ evidence and the no-op contract:

```text
artifact: configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml
status: passed
contract:
  payload_bytes_required = 0
  ready_credit_required = false
  changes_router_required = false
  changes_descriptor_order_required = false
  address_key_scope = layer_expert
  handle_resolution = read_only
```

The vLLM runtime-shadow config can now require this gate before enabling real descriptor/address handle consumer mapping:

```text
premap_consumer_require_readonly_gate = true
premap_consumer_readonly_gate_path = configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml
```

GPU1 8-sample AWQ/vLLM smoke confirms the gate metadata is emitted into `performance_summary.json` and the runtime consumer remains read-only:

```text
artifact:
  data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/

runtime_shadow_premap_consumer_readonly_gate_required = true
runtime_shadow_premap_consumer_readonly_gate_passed = true
runtime_shadow_premap_consumer_readonly_gate_id = premap_consumer_readonly_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow

premap_consumer_mapping_count = 20480
premap_consumer_address_hit_rate = 1.0
premap_consumer_real_descriptor_handle_hit_rate = 1.0
premap_consumer_lookup_after_prepare_rate = 1.0
premap_consumer_real_descriptor_handle_binding_mismatch_count = 0
premap_consumer_error_count = 0
premap_consumer_payload_violation_count = 0
premap_consumer_router_change_violation_count = 0
premap_consumer_descriptor_order_change_violation_count = 0
premap_consumer_ready_credit_violation_count = 0
```

The gate loader is strict: `gate.passed` must be a boolean, failed gates are rejected, and required runtime mode must remain `premap_only_with_consumer_mapping_noop` with `premap_consumer_mapping_mode=noop_assertion` and real-handle resolution enabled.

Verification:

```text
pytest tests -q -> 431 passed, 2 warnings
```

Review follow-up tightened the readonly gate boundary:

```text
- gate.passed must be a YAML boolean, not a truthy string/object.
- descriptor_bytes is compared against the runtime default 4096 even when the option is omitted.
- 8-sample premap consumer smoke config is now covered by tests for readonly gate binding.
- pytest tests -q -> 433 passed, 2 warnings.
```

## Premap Consumer Event-Level Gate Metadata (2026-05-20)

The read-only consumer gate is now attached to each `premap_consumer_mapping` event, not only to `performance_summary.json`.  This makes the runtime shadow log self-contained for lab replay/audit: every consumer handle assertion carries the gate that allowed it.

GPU1 8-sample AWQ/vLLM smoke with latest code:

```text
artifact:
  data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/

premap_consumer_mapping_count = 20480
missing_premap_consumer_readonly_gate_passed = 0
premap_consumer_readonly_gate_required = true
premap_consumer_readonly_gate_passed = true
premap_consumer_readonly_gate_id = premap_consumer_readonly_dolly512_gen64_awq_w7900_gpu1
(historical pre-kernel-arg-shadow gate id; current lab gate uses the Dolly128
kernel-arg-shadow artifact below)

first-row no-op contract:
  premap_consumer_payload_bytes = 0
  premap_consumer_changes_router = false
  premap_consumer_changes_descriptor_order = false
  premap_consumer_ready_credit = false
  premap_consumer_address_hit_rate = 1.0
  premap_consumer_real_descriptor_handle_hit_count = 174
```

Review follow-up also added explicit event serialization coverage for `readonly_gate_passed=false` and `None`:

```text
false -> serialized as false
None  -> omitted
pytest tests -q -> 435 passed, 2 warnings
```

## Premap Read-Only Consumer Shim (2026-05-21)

Implemented a read-only runtime consumer shim for the premap descriptor/address
path.  This moves the gate from "mapping can be reconstructed" to "a consumer
can repeatedly resolve the prepared descriptor/address handle without payload
movement or runtime side effects."

Contract:

```text
ControlledPremapAddressManager.prepare(plan)
  -> resident PremapAddressHandle objects

fused-MoE/AWQ consumer lookup
  -> consume_readonly(address_keys, expected_handle_hash_by_address_key)
  -> count lookup / hit / miss / evicted-before-consume / stale-handle / parity
  -> do not mutate LRU residency
  -> do not move payload
  -> do not change router
  -> do not change descriptor_order execution
  -> do not grant ready credit
```

New audit fields on `premap_consumer_mapping`:

```text
premap_consumer_readonly_lookup_count
premap_consumer_readonly_handle_hit_count
premap_consumer_readonly_handle_miss_count
premap_consumer_readonly_evicted_before_consume_count
premap_consumer_readonly_stale_handle_count
premap_consumer_readonly_handle_parity_ok
```

The aggregate/gate contract now requires:

```text
premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_handle_parity_ok_rate = 1.0
premap_consumer_readonly_evicted_before_consume_count = 0
premap_consumer_readonly_stale_handle_count = 0
```

GPU1 8-sample AWQ/vLLM smoke:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml

artifact:
  data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/

row_count = 102400
event_counts = {
  decoder_layer_timing: 20480,
  descriptor_summary_min: 20480,
  outcome_aggregate: 20480,
  premap_summary: 20480,
  premap_consumer_mapping: 20480,
}

premap_consumer_real_descriptor_handle_hit_count = 190215
premap_consumer_real_descriptor_handle_miss_count = 0
premap_consumer_real_descriptor_handle_hit_rate = 1.0

premap_consumer_readonly_lookup_count = 190215
premap_consumer_readonly_handle_hit_count = 190215
premap_consumer_readonly_handle_miss_count = 0
premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_evicted_before_consume_count = 0
premap_consumer_readonly_evicted_before_consume_rate = 0.0
premap_consumer_readonly_stale_handle_count = 0
premap_consumer_readonly_stale_handle_rate = 0.0
premap_consumer_readonly_handle_parity_ok_rate = 1.0
premap_consumer_error_count = 0
```

Verification:

```text
focused tests -> 84 passed, 2 skipped
pytest tests -q -> 438 passed, 2 skipped, 2 warnings
```

Boundary:

```text
This is still a read-only premap consumer contract.  It validates descriptor/address
handle lifetime and stability before real runtime payload/cache integration.  It
is not a full_fetch payload-transfer result, not a ready-credit result, and not
an endpoint TPOT performance claim.
```

Review follow-up for the read-only consumer shim:

```text
- Long-run gate now has an explicit --require-readonly-consumer switch.
  Without it, legacy summaries that predate readonly consumer counters remain
  checkable.  With it, real runtime-admission gates require readonly hit/parity
  stability.
- ControlledPremapAddressManager documents eviction history as manager-lifetime
  state, matching the long-lived descriptor-cache model used by the vLLM shadow
  recorder.
- Added regression coverage that re-preparing an evicted address key clears the
  evicted-before-consume signal and does not create a stale false positive.
```

The mixed 8-sample diagnostic is not passed to the premap-only long-run gate as
an admission artifact because it intentionally contains decoder, descriptor, and
outcome diagnostic rows.  Its selected aggregate still confirms the runtime
consumer stability counters:

```text
premap_consumer_readonly_lookup_count = 190215
premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_evicted_before_consume_count = 0
premap_consumer_readonly_stale_handle_count = 0
premap_consumer_readonly_handle_parity_ok_rate = 1.0
```

Verification after review follow-up:

```text
focused tests -> 86 passed, 2 skipped
pytest tests -q -> 440 passed, 2 skipped, 2 warnings
```

128-sample premap-only long-run audit with the strict read-only consumer gate:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

summary:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_summary.json

gate:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate.json
```

Result:

```text
gate_passed = true
failures = []
row_count = 20390
event_counts = {premap_summary: 10195, premap_consumer_mapping: 10195}

premap_address_resident_count_max = 10127
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_evicted_count = 0

premap_consumer_real_descriptor_handle_hit_count = 110898
premap_consumer_real_descriptor_handle_miss_count = 0
premap_consumer_real_descriptor_handle_hit_rate = 1.0

premap_consumer_readonly_lookup_count = 110898
premap_consumer_readonly_handle_hit_count = 110898
premap_consumer_readonly_handle_miss_count = 0
premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_evicted_before_consume_count = 0
premap_consumer_readonly_stale_handle_count = 0
premap_consumer_readonly_handle_parity_ok_rate = 1.0
```

This confirms that the premap descriptor/address handles are not only mapped to
real vLLM/AWQ launch-time handle classes, but can also be consumed by a read-only
runtime shim over a sampled 128-sample long-run without stale, eviction, or
parity failures.

512-sample premap-only long-run audit with `--require-readonly-consumer`:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

summary:
  data/traces/external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_summary.json

gate:
  data/traces/external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate.json
```

Result:

```text
gate_passed = true
failures = []
row_count = 40684
event_counts = {premap_summary: 20342, premap_consumer_mapping: 20342}

premap_address_resident_count_max = 10202
premap_address_reuse_rate_mean = 0.9945098117726032
premap_address_evicted_count = 0

premap_consumer_real_descriptor_handle_hit_count = 210849
premap_consumer_real_descriptor_handle_miss_count = 0
premap_consumer_real_descriptor_handle_hit_rate = 1.0

premap_consumer_readonly_lookup_count = 210849
premap_consumer_readonly_handle_hit_count = 210849
premap_consumer_readonly_handle_miss_count = 0
premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_evicted_before_consume_count = 0
premap_consumer_readonly_stale_handle_count = 0
premap_consumer_readonly_handle_parity_ok_rate = 1.0
```

Updated `configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml`
with these strict read-only consumer metrics.  This artifact is now the required
precondition for real lab integration of the read-only premap descriptor/address
consumer path.

Lab default readonly-gated descriptor/address prep execution:

```text
configs:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

execution_mode:
  premap_descriptor_prep_execution_mode = readonly_descriptor_address_object
```

The readonly gate is now a precondition for the minimal descriptor/address prep
execution path.  The runtime refuses unknown prep execution modes and refuses to
enable descriptor/address prep execution without
`premap_consumer_require_readonly_gate=True`.  `attempted_count` means the config
activated descriptor prep for the consumer event; `executed_count` is the stricter
count of events that actually resolved descriptor/address objects after the
readonly gate and lookup checks passed.

The minimal execution path resolves already-resident `PremapAddressHandle`
objects into descriptor pointers, packed-weight descriptors, and scale-metadata
handles.  It does not move payload bytes, mutate LRU state, grant ready credit,
change router outputs, or change descriptor visitation order.

GPU1 8-sample vLLM/AWQ smoke:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml

summary:
  data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/premap_descriptor_prep_smoke_summary.json
```

Result:

```text
premap_consumer_mapping_count = 20480

premap_consumer_readonly_lookup_count = 190215
premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_evicted_before_consume_count = 0
premap_consumer_readonly_stale_handle_count = 0
premap_consumer_readonly_handle_parity_ok_rate = 1.0

premap_consumer_descriptor_prep_attempted_count = 20480
premap_consumer_descriptor_prep_executed_count = 20480
premap_consumer_descriptor_prep_lookup_count = 190215
premap_consumer_descriptor_prep_handle_count = 190215
premap_consumer_descriptor_prep_missing_handle_count = 0
premap_consumer_descriptor_prep_handle_hit_rate = 1.0
premap_consumer_descriptor_prep_descriptor_ptr_count = 190215
premap_consumer_descriptor_prep_packed_weight_descriptor_count = 190215
premap_consumer_descriptor_prep_scale_metadata_handle_count = 190215
premap_consumer_descriptor_prep_execution_ok_rate = 1.0
premap_consumer_descriptor_prep_execution_ok_attempted_rate = 1.0
premap_consumer_descriptor_prep_blocked_count = 0
premap_consumer_descriptor_prep_blocked_attempted_rate = 0.0

premap_consumer_payload_violation_count = 0
premap_consumer_ready_credit_violation_count = 0
premap_consumer_router_change_violation_count = 0
premap_consumer_descriptor_order_change_violation_count = 0
```

Verification:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
447 passed, 2 warnings
```

128/512 readonly-gated descriptor prep long-run gate:

```text
configs:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

gate command:
  scripts/check_premap_longrun_audit_gate.py
    --max-capacity 12288
    --min-reuse-rate 0.98
    --require-readonly-consumer
    --require-descriptor-prep
```

Results:

| samples | rows | premap_summary | consumer_mapping | reuse mean | evicted | resident addresses | resident bytes | readonly lookups | descriptor_prep attempted/executed | prep lookups/handles | prep handle hit | prep ok attempted | prep blocked |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 20,390 | 10,195 | 10,195 | 0.982739 | 0 | 10,127 | 41,480,192 | 110,898 | 10,195 / 10,195 | 110,898 / 110,898 | 1.0 | 1.0 | 0 |
| 512 | 40,684 | 20,342 | 20,342 | 0.994510 | 0 | 10,202 | 41,787,392 | 210,849 | 20,342 / 20,342 | 210,849 / 210,849 | 1.0 | 1.0 | 0 |

Strict gate artifacts:

```text
data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate.json
data/traces/external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate.json
```

Both gates pass with:

```text
premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_handle_parity_ok_rate = 1.0
premap_consumer_descriptor_prep_attempted_count = premap_consumer_mapping_count
premap_consumer_descriptor_prep_handle_hit_rate = 1.0
premap_consumer_descriptor_prep_execution_ok_attempted_rate = 1.0
premap_consumer_descriptor_prep_missing_handle_count = 0
premap_consumer_descriptor_prep_blocked_count = 0
premap_consumer_payload_violation_count = 0
premap_consumer_router_change_violation_count = 0
premap_consumer_descriptor_order_change_violation_count = 0
premap_consumer_ready_credit_violation_count = 0
premap_consumer_real_descriptor_handle_hit_rate = 1.0
premap_consumer_real_descriptor_handle_available_rate = 1.0
premap_consumer_real_descriptor_handle_binding_mismatch_count = 0
premap_consumer_error_count = 0
```

Updated lab precondition artifact:

```text
configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml
```

The artifact now requires the stricter descriptor prep execution contract:

```text
lab_precondition = true
descriptor_prep_execution_mode = readonly_descriptor_address_object
require_readonly_consumer = true
require_descriptor_prep = true
```

Interpretation:

```text
The premap path has now passed the real-lab precondition for a read-only
descriptor/address prep consumer: current-router premap address objects are
resident, real vLLM/AWQ packed-weight/scale handles are resolvable and stable,
and the descriptor prep object can be built from those handles without payload
transfer, readiness credit, router mutation, descriptor_order execution, or
kernel argument mutation.

This is still a safety/precondition gate for descriptor/address preparation.  It
does not grant readiness credit, and it is not a payload prefetch result or an
endpoint TPOT claim.
```

Verification:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests/test_check_premap_longrun_audit_gate.py -q
12 passed

conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
455 passed, 2 warnings
```

### 2026-05-22: Real-handle-backed descriptor prep object smoke

The minimal descriptor/address prep path now has a real-handle-backed execution
contract.  `ControlledPremapAddressManager.execute_descriptor_prep_readonly()`
can optionally receive live vLLM/AWQ runtime-address signatures:

```text
address_key
  -> PremapRealDescriptorHandle
  -> packed-weight descriptor signature
  -> scale metadata handle signature
  -> optional auxiliary metadata signature
```

This remains a read-only prep object:

```text
payload_bytes = 0
ready_credit = false
changes_router = false
changes_descriptor_order = false
kernel args unchanged
```

The execution result and runtime shadow aggregate now expose:

```text
premap_consumer_descriptor_prep_real_handle_count
premap_consumer_descriptor_prep_real_handle_miss_count
premap_consumer_descriptor_prep_real_handle_hit_rate
premap_consumer_descriptor_prep_real_handle_backed_count
premap_consumer_descriptor_prep_real_handle_backed_rate
premap_consumer_descriptor_prep_real_handle_hash
```

Safety refinements:

```text
real handle payload_bytes > 0 fails execution_ok
missing real handle fails execution_ok
real handle address_key mismatch fails execution_ok
incomplete packed-weight / scale metadata fails execution_ok
real-handle hit rate includes descriptor-prep missing handles in the denominator
```

GPU1 AWQ 8-sample smoke:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml

runtime_shadow rows: 102,400
premap_consumer_mapping rows: 20,480
descriptor_prep_real_handle_backed rows: 20,480 / 20,480
descriptor_prep_real_handle_count sum: 190,215
descriptor_prep_real_handle_miss_count sum: 0
descriptor_prep_execution_ok rows: 20,480 / 20,480
descriptor_prep_blocked rows: 0

performance_summary:
  runtime_shadow_aggregate_premap_consumer_descriptor_prep_real_handle_backed_rate = 1.0
  runtime_shadow_aggregate_premap_consumer_descriptor_prep_real_handle_hit_rate = 1.0
  runtime_shadow_aggregate_premap_consumer_descriptor_prep_real_handle_miss_count = 0

real descriptor prep gate:
  scripts/check_premap_longrun_audit_gate.py
    --require-readonly-consumer
    --require-descriptor-prep
    --require-real-descriptor-prep
  passed on filtered premap-only summary
```

Boundary:

```text
This validates that the read-only consumer can build a descriptor/address prep
object from actual vLLM/AWQ packed-weight and scale metadata handles.  It still
does not move payload, mark experts ready, change routing, change descriptor
visitation order, or patch a fused-MoE kernel launch argument.
```

Verification:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest \
  tests/test_runtime_premap.py \
  tests/test_runtime_shadow_log.py \
  tests/test_vllm_router_shadow_sink.py \
  tests/test_check_premap_longrun_audit_gate.py -q
97 passed

conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
464 passed, 2 warnings
```

### 2026-05-22: Real-handle descriptor prep promoted to lab gate

The 128/512 Dolly long-run audit was rerun with the real-handle-backed
descriptor prep code path and checked with the stricter gate:

```text
scripts/check_premap_longrun_audit_gate.py
  --max-capacity 12288
  --min-reuse-rate 0.98
  --require-readonly-consumer
  --require-descriptor-prep
  --require-real-descriptor-prep
```

Results:

| samples | rows | premap_summary | consumer_mapping | reuse mean | resident addresses | readonly lookups | prep lookups | real prep handles | real prep misses | real prep hit | real prep backed |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 20,390 | 10,195 | 10,195 | 0.9827389897 | 10,127 | 110,898 | 110,898 | 110,898 | 0 | 1.0 | 1.0 |
| 512 | 40,684 | 20,342 | 20,342 | 0.9945098118 | 10,202 | 210,849 | 210,849 | 210,849 | 0 | 1.0 | 1.0 |

Both gates pass with:

```text
premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_handle_parity_ok_rate = 1.0
premap_consumer_descriptor_prep_attempted_count = premap_consumer_mapping_count
premap_consumer_descriptor_prep_lookup_count = premap_consumer_descriptor_prep_handle_count
premap_consumer_descriptor_prep_execution_ok_attempted_rate = 1.0
premap_consumer_descriptor_prep_real_handle_count = premap_consumer_descriptor_prep_lookup_count
premap_consumer_descriptor_prep_real_handle_miss_count = 0
premap_consumer_descriptor_prep_real_handle_hit_rate = 1.0
premap_consumer_descriptor_prep_real_handle_backed_rate = 1.0
premap_consumer_payload_violation_count = 0
premap_consumer_router_change_violation_count = 0
premap_consumer_descriptor_order_change_violation_count = 0
premap_consumer_ready_credit_violation_count = 0
premap_consumer_error_count = 0
```

Updated lab precondition artifact:

```text
configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml
```

The artifact now requires:

```text
lab_precondition = true
require_readonly_consumer = true
require_descriptor_prep = true
require_real_descriptor_prep = true
real_descriptor_prep_required = true
descriptor_prep_execution_mode = readonly_descriptor_address_object
```

Interpretation:

```text
The real-lab precondition now requires that the read-only premap consumer can
resolve resident descriptor/address objects into actual vLLM/AWQ packed-weight
and scale metadata handle signatures at long-run scale.

This remains a safety gate.  It does not move expert payloads, mark experts
ready, change routing, change descriptor visitation order, patch kernel launch
arguments, or claim endpoint TPOT improvement.
```

### 2026-05-22: Runtime loader gate smoke for real descriptor prep

The real descriptor prep lab gate was exercised through the vLLM/AWQ trace
loader rather than only through offline gate checking.

Positive loader smoke:

| smoke | config | gate | execution mode | mappings | prep lookups | real handles | misses | real hit | backed | errors |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 8-sample gen64 | `configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml` | passed | `readonly_descriptor_address_object` | 20,480 | 190,215 | 190,215 | 0 | 1.0 | 1.0 | 0 |
| 32-sample gen8 smoke | `/tmp/router_mtp_trace_dolly_32_real_prep_loader_smoke.yaml` | passed | `readonly_descriptor_address_object` | 10,240 | 205,088 | 205,088 | 0 | 1.0 | 1.0 | 0 |

The 32-sample smoke intentionally uses short generation (`max_tokens=8`) to
validate loader/gate plumbing without paying the full diagnostic cost.  The
consumer mapping path still requires router-topk recording for this smoke; a
trial with `record_router_topk=false` correctly failed to produce descriptor
prep handles and was not used as positive evidence.

Negative loader smoke:

```text
config: /tmp/router_mtp_trace_dolly_1_bad_real_prep_gate_smoke.yaml
bad gate: /tmp/premap_consumer_readonly_gate_bad_no_real.yaml
mutation: contract.real_descriptor_prep_required=false
result: rejected before model load
error:
  premap_descriptor_prep_execution_mode requires a readonly gate with
  contract.real_descriptor_prep_required=true
```

Interpretation:

```text
The runtime loader is now fail-closed for real descriptor prep execution mode:
valid lab gate artifacts are accepted and summarized in performance_summary.json.
The tested bad gate with `contract.real_descriptor_prep_required=false` is
rejected before vLLM model loading in this execution mode, validating the
fail-closed path for this required-gate check.

This remains no-op/read-only evidence.  It validates handle availability and
gate enforcement, not payload movement or endpoint latency improvement.
```

### 2026-05-22: Lab-default 128-sample real descriptor prep audit

The lab-default real descriptor prep long-run audit was rerun at 128 samples
only.  The 512-sample rerun was intentionally skipped because the 128-sample
run is sufficient for this gate refresh and the 512-sample run is much slower.

Config:

```text
configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml
```

Strict gate checker:

```text
scripts/check_premap_longrun_audit_gate.py
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_summary.json
  --max-capacity 12288
  --min-reuse-rate 0.98
  --require-readonly-consumer
  --require-descriptor-prep
  --require-real-descriptor-prep
```

Result:

```text
passed = true
failures = []

premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_eviction_pressure_mean = 0.0
premap_address_resident_count_max = 10127
premap_address_resident_descriptor_bytes_max = 41480192

premap_consumer_mapping_count = 10195
premap_consumer_descriptor_prep_attempted_count = 10195
premap_consumer_descriptor_prep_executed_count = 10195
premap_consumer_descriptor_prep_lookup_count = 110898
premap_consumer_descriptor_prep_real_handle_count = 110898
premap_consumer_descriptor_prep_real_handle_hit_rate = 1.0
premap_consumer_descriptor_prep_real_handle_miss_count = 0
premap_consumer_descriptor_prep_real_handle_backed_rate = 1.0

premap_consumer_readonly_handle_hit_rate = 1.0
premap_consumer_readonly_handle_parity_ok_rate = 1.0
premap_consumer_readonly_stale_handle_count = 0
premap_consumer_error_count = 0
```

The corresponding `performance_summary.json` also contains the flattened
manager/gate fields:

```text
runtime_shadow_premap_consumer_readonly_gate_passed = true
runtime_shadow_premap_consumer_readonly_gate_required = true
runtime_shadow_premap_consumer_readonly_gate_id =
  premap_consumer_readonly_dolly512_gen64_awq_w7900_gpu1
(historical pre-kernel-arg-shadow gate id)
runtime_shadow_premap_descriptor_prep_execution_mode =
  readonly_descriptor_address_object
runtime_shadow_aggregate_premap_address_reuse_rate_mean =
  0.9827389896686539
runtime_shadow_aggregate_premap_address_eviction_pressure_mean = 0.0
runtime_shadow_aggregate_premap_address_resident_descriptor_bytes_max =
  41480192
```

Interpretation:

```text
The lab-default gate remains valid at 128-sample scale after the runtime loader
smoke and gate-artifact updates.  The audit validates read-only descriptor/
address-handle availability and manager stability, not payload movement,
ready-before-demand, descriptor-order execution, or endpoint latency gain.
```

### 2026-05-22: Minimal real descriptor prep consumer object integration

The readonly descriptor/address prep path now constructs a minimal
`PremapDescriptorConsumerObject` when every requested `(layer, expert)` address
key resolves to a complete descriptor/address handle:

```text
address_key
descriptor_ptr
packed_weight_descriptor
scale_metadata_handle
aux_metadata_handle
handle_hash
real_handle_hash
```

This object is a consumer contract only.  It remains no-op/read-only:

```text
payload_bytes = 0
ready_credit = false
changes_router = false
changes_descriptor_order = false
```

The runtime shadow event and aggregate summary now expose:

```text
premap_consumer_descriptor_prep_consumer_object_count
premap_consumer_descriptor_prep_consumer_object_hash
premap_consumer_descriptor_prep_consumer_object_rate
premap_consumer_descriptor_prep_consumer_object_read_lookup_count
premap_consumer_descriptor_prep_consumer_object_read_hit_count
premap_consumer_descriptor_prep_consumer_object_read_miss_count
premap_consumer_descriptor_prep_consumer_object_stale_count
premap_consumer_descriptor_prep_consumer_object_read_hit_rate
premap_consumer_descriptor_prep_consumer_object_stale_rate
premap_consumer_descriptor_prep_consumer_object_read_ok_rate
premap_consumer_descriptor_prep_consumer_shim_executed_count
premap_consumer_descriptor_prep_consumer_shim_ok_count
premap_consumer_descriptor_prep_consumer_shim_ok_rate
premap_consumer_descriptor_prep_consumer_shim_object_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max
premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes
premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count
premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count
```

`consumer_object_rate` is intentionally measured as:

```text
consumer_object_count / descriptor_prep_lookup_count
```

This is stricter than the real-handle hit rate: a handle may be present but
still fail to become a consumer object if it is incomplete or payload-backed.

The prelaunch consumer now also performs a second readonly object read against
the prepared object hashes:

```text
read lookup -> object hash parity -> stale/miss accounting
```

This validates that the object-shaped handle remains readable at the consumer
side without passing it to a kernel or mutating launch arguments.

The prelaunch path also runs an explicit readonly consumer shim:

```text
PremapDescriptorConsumerReadResult
  -> PremapDescriptorConsumerShimResult
```

The shim is the first named runtime consumer boundary for the prepared object.
It accepts only a successful readonly object read and records:

```text
execution_mode = readonly_prelaunch_consumer_shim
shim_ok
object_count
object_hash
handle_table_row_count
handle_table_column_count
handle_table_schema_hash
handle_table_payload_bytes = 0
changes_kernel_launch_args = false
```

This is still not a real kernel integration.  It is a no-op prelaunch consumer
shim that proves the prepared descriptor/address object can be handed across a
runtime boundary without changing payload, ready credit, router output,
descriptor order, or kernel launch arguments.

The handle-table fields are a dry-run shape contract only.  They describe the
future consumer table as:

```text
rows = readable descriptor prep objects
columns = descriptor_ptr / packed_weight_descriptor / scale_metadata_handle /
          aux_metadata_handle
payload bytes = 0
```

No table is passed into vLLM kernels yet.

Validation:

```text
env PYTHONPATH=$PWD:$PWD/src conda run -p ~/anaconda3/envs/TRY pytest tests -q
466 passed, 2 warnings
```

GPU1 AWQ smoke:

```text
configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml

runtime_shadow_premap_consumer_readonly_gate_passed = true
runtime_shadow_premap_descriptor_prep_execution_mode =
  readonly_descriptor_address_object
runtime_shadow_aggregate_premap_consumer_descriptor_prep_lookup_count =
  190215
runtime_shadow_aggregate_premap_consumer_descriptor_prep_real_handle_count =
  190215
runtime_shadow_aggregate_premap_consumer_descriptor_prep_real_handle_hit_rate =
  1.0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_real_handle_miss_count =
  0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_count =
  190215
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_rate =
  1.0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_read_lookup_count =
  190215
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_read_hit_count =
  190215
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_read_miss_count =
  0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_stale_count =
  0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_read_hit_rate =
  1.0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_stale_rate =
  0.0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_object_read_ok_rate =
  1.0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_executed_count =
  20480
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_object_count =
  190215
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count =
  190215
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max =
  4
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes =
  0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count =
  0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_ok_count =
  20480
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_ok_rate =
  1.0
runtime_shadow_aggregate_premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count =
  0
```

Interpretation:

```text
The premap path has advanced from address-key parity to a readonly
real-handle-backed descriptor prep object contract.  This still does not move
payloads, grant ready credit, mutate routing, mutate descriptor order, or prove
endpoint latency benefit.  It is the next safety gate before any real lab
descriptor/address preparation execution.
```

### 2026-05-22: Kernel-arg shadow table dry run

The readonly prelaunch consumer shim now builds a second no-op object:

```text
PremapKernelArgShadowTableResult
```

This object models the future kernel/consumer argument table without passing it
to any kernel.  It records only table shape, row order, and per-row object-hash
parity:

```text
execution_mode = readonly_kernel_arg_shadow_table
row_order_source = canonical_address_key_order
row_count
column_count
schema_hash
row_order_hash
ordered_row_hash
per_row_parity_ok_count
row_miss_count
stale_row_count
lifecycle_ok
table_ok
```

The no-op contract remains strict:

```text
payload_bytes = 0
ready_credit = false
changes_router = false
changes_descriptor_order = false
changes_kernel_launch_args = false
passed_to_kernel = false
```

The table schema is the same readonly handle-table schema used by the
prelaunch shim:

```text
descriptor_ptr
packed_weight_descriptor
scale_metadata_handle
aux_metadata_handle
```

Runtime shadow aggregation now exposes:

```text
premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate
premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate
premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max
premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes
premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_violation_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count
premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count
```

Interpretation:

```text
This is still not a vLLM kernel patch.  It is a dry-run kernel-argument contract
that verifies canonical descriptor/address table row ordering, schema hash,
per-row handle parity, and lifecycle before any real descriptor/address object
is wired into kernel launch args.  It does not claim to validate the final
fused-MoE block/tile launch row order.
```

### 2026-05-23: Kernel-arg shadow table promoted to lab gate

The premap readonly lab gate now requires the kernel-argument shadow table
contract in addition to real-handle-backed descriptor prep:

```text
contract.kernel_arg_shadow_table_required = true
gate.check.require_kernel_arg_shadow_table = true
```

`scripts/check_premap_longrun_audit_gate.py` now fails closed unless:

```text
kernel_arg_shadow_table_executed_count = descriptor_prep_executed_count
kernel_arg_shadow_table_row_count = descriptor_prep_lookup_count
kernel_arg_shadow_table_column_count_min = column_count_max = 4
kernel_arg_shadow_table_schema_hash = expected descriptor-consumer table schema
kernel_arg_shadow_table_schema_hash_checked_count = table_executed_count
kernel_arg_shadow_table_schema_hash_missing_count = 0
kernel_arg_shadow_table_schema_hash_mismatch_count = 0
kernel_arg_shadow_table_per_row_parity_ok_count = row_count
kernel_arg_shadow_table_ok_rate = 1.0
kernel_arg_shadow_table_lifecycle_ok_rate = 1.0
row_miss_count = 0
stale_row_count = 0
payload_bytes = 0
payload / ready / router / descriptor-order / kernel-arg violations = 0
passed_to_kernel_count = 0
```

GPU1 Dolly128 long-run audit was rerun with the stricter gate:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

summary:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_summary.json

gate:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate.json

passed = true
failures = []
premap_consumer_mapping_count = 10195
premap_consumer_descriptor_prep_lookup_count = 110898
premap_consumer_descriptor_prep_real_handle_count = 110898
premap_consumer_descriptor_prep_real_handle_hit_rate = 1.0
premap_consumer_descriptor_prep_real_handle_backed_rate = 1.0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count = 10195
premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count = 110898
premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max = 4
premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min = 4
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash = a02928d41970cdf1630dc2a743589ab18068454ac47341a34c4583fd40a5f294
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count = 10195
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count = 0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count = 0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count = 110898
premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate = 1.0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate = 1.0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count = 0
```

The runtime-loader gate is also fail-closed: descriptor prep execution now
requires a gate artifact checked with
`require_kernel_arg_shadow_table=true`.  This makes the readonly kernel-arg
shadow table a lab precondition before any real descriptor/address prep object
is allowed to approach a kernel launch path.

### 2026-05-23: Consumer shim reads the kernel-arg shadow table object

The minimal descriptor/address prep execution dry-run now advances one step
beyond constructing the kernel-arg shadow table:

```text
descriptor/address prep object
-> readonly descriptor consumer object read
-> readonly kernel-arg shadow table construction
-> readonly consumer shim reads that table object
```

The consumer shim still does not pass any object to a kernel, move payload, grant
ready credit, change the router, or change descriptor visitation order.  It now
records whether the table object was readable and lifecycle/parity-clean:

```text
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate
premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate
premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count
```

GPU1 Dolly8 AWQ/vLLM smoke:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml

summary:
  data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke/consumer_shim_table_read_summary.json

row_count = 102400
premap_consumer_mapping_count = 20480
premap_consumer_descriptor_prep_consumer_shim_executed_count = 20480
premap_consumer_descriptor_prep_consumer_shim_ok_rate = 1.0
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count = 20480
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate = 0.0
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count = 20480
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate = 1.0
premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate = 1.0
premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count = 190215
premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count = 0
premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count = 0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count = 20480
premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate = 1.0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate = 1.0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count = 0
premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count = 0
```

Boundary:

```text
This is still a dry-run consumer contract, not a vLLM kernel patch.  It validates
that a real prelaunch consumer shim can read the prepared descriptor/address
table object with stable lifecycle and handle parity, while keeping payload,
ready credit, router mutation, descriptor-order mutation, and kernel args off.
```

### 2026-05-23: Consumer shim table-read promoted to lab gate

The readonly descriptor/address prep gate now treats consumer-shim table reads
as a lab precondition.  Descriptor prep execution requires the gate artifact to
declare and pass:

```text
contract.consumer_shim_table_read_required = true
gate.check.require_consumer_shim_table_read = true
```

The checker is fail-closed for this mode: missing shim read fields fail the
gate, unchecked reads fail the gate, row misses/stale rows fail the gate, and
any payload/kernel handoff remains a violation.  The checker also closes the
row-count loop:

```text
consumer_shim_handle_table_row_count
  == kernel_arg_shadow_table_row_count
consumer_shim_handle_table_per_row_parity_ok_count
  == consumer_shim_handle_table_row_count
consumer_shim_handle_table_column_count_max
  == expected kernel-arg shadow table column count
```

GPU1 Dolly128 AWQ/vLLM long-run gate:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

summary:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_summary.json

gate:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate.json

premap_consumer_mapping_count = 10195
premap_consumer_descriptor_prep_lookup_count = 110898
premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count = 110898
premap_consumer_descriptor_prep_consumer_shim_executed_count = 10195
premap_consumer_descriptor_prep_consumer_shim_ok_rate = 1.0
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count = 10195
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate = 1.0
premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate = 1.0
premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count = 110898
premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max = 4
premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count = 110898
premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count = 0
```

The lab gate artifact was updated:

```text
configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml
```

This remains a readonly dry-run contract.  It proves that the runtime consumer
shim can read the prepared descriptor/address shadow table with stable
lifecycle and row parity; it still does not move payload, grant ready credit,
mutate router output, mutate descriptor order, or pass new kernel arguments.

### 2026-05-23: Consumer shim table-consume promoted to lab gate

The previous 128-sample long-run artifact with an empty `runtime_shadow.jsonl`
was re-run with the current code after isolating the write path.  The issue did
not reproduce:

```text
longrun-style Dolly8 smoke:
  runtime_shadow rows = 1,280
  premap_summary = 640
  premap_consumer_mapping = 640
  consumer_shim_table_consume_checked = 640
  consumer_shim_table_consume_ok_rate = 1.0

Dolly128 strict long-run:
  runtime_shadow rows = 20,390
  premap_summary = 10,195
  premap_consumer_mapping = 10,195
  consumer_shim_table_consume_checked = 10,195
  consumer_shim_table_consume_ok_rate = 1.0
```

Strict gate command:

```text
scripts/check_premap_longrun_audit_gate.py
  --require-readonly-consumer
  --require-descriptor-prep
  --require-real-descriptor-prep
  --require-kernel-arg-shadow-table
  --require-consumer-shim-table-read
  --require-consumer-shim-table-consume
```

Gate result:

```text
data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/longrun_audit_gate.json

passed = true
failures = []
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_eviction_pressure_mean = 0.0
premap_address_resident_count_max = 10127
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count = 110898
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max = 4
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash =
  a02928d41970cdf1630dc2a743589ab18068454ac47341a34c4583fd40a5f294
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_violation_count = 0
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count = 0
```

The lab gate artifact now requires both table read and table consume:

```text
contract.consumer_shim_table_read_required = true
contract.consumer_shim_table_consume_required = true
gate.check.require_consumer_shim_table_read = true
gate.check.require_consumer_shim_table_consume = true
```

The runtime loader is fail-closed for this precondition: descriptor prep
execution now rejects readonly gate artifacts that do not declare and pass the
consumer-shim table consume contract.  A dedicated 8-sample long-run audit
smoke config was added to catch future empty-shadow regressions quickly:

```text
configs/trace/router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke.yaml
```

Boundary:

```text
This is still not a kernel-argument patch.  The consumer shim consumes the
prepared shadow table object in runtime, verifies lifecycle/schema/row parity,
and records that nothing was passed to a kernel and no payload moved.
```

Next gate:

```text
Use this lab precondition before any minimal descriptor/address prep execution
that approaches a real fused-MoE/AWQ prelaunch consumer.  The next integration
step must keep payload movement, ready credit, router mutation, descriptor-order
mutation, and kernel-arg mutation disabled until the consumer-side table object
is explicitly wired and checked under the lab gate.
```

## Premap consume provenance gate

The read-only consumer shim table consume path now records explicit provenance:

```text
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source
```

Semantics:

```text
consume_mode   = readonly_consume_kernel_arg_shadow_table
consume_source = kernel_arg_shadow_table.row_order_source
```

This makes the lab gate state directly auditable from the runtime shadow row:
the consumer shim is consuming the prepared kernel-arg shadow table object in
canonical address-key order, not inferring that fact from the Python call path.

The long-run checker now requires this provenance when
`--require-consumer-shim-table-consume` is enabled:

```text
consume_mode_checked_count == consumer_shim_executed_count
consume_source_checked_count == consumer_shim_executed_count
consume_mode_missing_count == 0
consume_source_missing_count == 0
consume_mode_mismatch_count == 0
consume_source_mismatch_count == 0
```

GPU1 AWQ/vLLM 128-sample strict rerun:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate.json

passed = true
failures = []
runtime_shadow rows = 20,390
premap_summary = 10,195
premap_consumer_mapping = 10,195
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_resident_count_max = 10,127

consumer_shim_table_consume_checked = 10,195
consumer_shim_table_consume_mode =
  readonly_consume_kernel_arg_shadow_table
consumer_shim_table_consume_mode_checked = 10,195
consumer_shim_table_consume_source =
  canonical_address_key_order
consumer_shim_table_consume_source_checked = 10,195
consumer_shim_table_consume_row_count = 110,898
consumer_shim_table_consume_passed_to_kernel_count = 0
```

Boundary remains unchanged:

```text
no payload transfer
no ready credit
no router mutation
no descriptor_order execution
no kernel argument mutation
```

### Lab preflight machine-readable status summary

Added a top-level `lab_gate_status_summary` to the premap lab preflight
output so the default lab gate can be checked without manually walking the
nested evidence objects:

```text
script:
  scripts/run_premap_lab_preflight.py

refreshed artifact:
  outputs/reports/
    premap_lab_preflight_native_bridge_and_stub_required_128.json

compact status artifact:
  outputs/reports/
    premap_lab_preflight_status_native_bridge_and_stub_required_128.json

lab_gate_status_summary.passed = true
default_contract_passed = true
default_kernel_consumer_schema_passed = true
default_required_evidence_passed = true
runtime_gate_evidence_scan_passed = true
strict_default_gate_evidence_passed = true
trace_config_passed_count = 2 / 2
required_evidence.present_count = 9 / 9
required_evidence.passed_count = 9 / 9
native_typed_consumer_bridge_required = true
native_stub_online_invocation_canary_required = true
payload_bytes_required = 0
passed_to_kernel_required = false
changes_kernel_launch_args_required = false
```

This does not relax or change the gate. It only materializes the existing
contract/evidence checks into a machine-readable status block for lab-default
preflight and handoff review.

The preflight CLI also supports a compact handoff mode:

```text
scripts/run_premap_lab_preflight.py --summary-only
```

`--summary-only` writes only `lab_gate_status_summary` while preserving the
full preflight result internally for the process exit code.

Validation:

```text
env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests/test_run_premap_lab_preflight.py -q

29 passed in 3.49s

env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests -q

658 passed, 2 warnings in 8.65s
```

### Status-backed online native-stub canary

The online prelaunch native-stub canary runner now treats the compact lab
preflight status as part of the canary contract.  It still runs the full
preflight, but it also runs:

```text
scripts/run_premap_lab_preflight.py --summary-only
```

and requires the resulting status block to pass before the runner can pass.

Refreshed runner:

```text
script:
  scripts/run_premap_online_native_stub_canary.py

artifact:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_runner.json

compact preflight status:
  outputs/reports/
    premap_lab_preflight_status_online_prelaunch_native_stub_canary.json

runner passed = true
runner failures = []
native stub row_ok_count = 204 / 204
preflight_summary.passed = true
preflight_status_summary.passed = true
preflight_status_summary.required_evidence_present_count = 9
preflight_status_summary.required_evidence_passed_count = 9
native_typed_consumer_bridge_required = true
native_stub_online_invocation_canary_required = true
payload_bytes_required = 0
passed_to_kernel_required = false
changes_kernel_launch_args_required = false
```

This makes the compact status artifact the practical lab-default preflight
entry for the native/online bridge canary while preserving the full nested
preflight artifact for audit.

Validation:

```text
env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests/test_run_premap_online_native_stub_canary.py \
         tests/test_run_premap_lab_preflight.py -q

33 passed in 3.33s

env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests -q

659 passed, 2 warnings in 8.47s
```

Follow-up gate hardening:

The online prelaunch native-stub canary runner no longer lets the preflight
step validate a stale copy of the runner artifact.  The runner now uses a
two-stage preflight:

```text
stage 1:
  run full preflight and compact status with
  --defer-online-prelaunch-runner-evidence

  purpose:
    validate every non-self-referential lab gate dependency before the runner
    report exists.

stage 2:
  write the runner report
  run normal full preflight and compact status without defer

  purpose:
    validate the current runner artifact through the default lab gate.
```

Refreshed runner evidence:

```text
artifact:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_runner.json

stage 1 preflight:
  preflight_summary.passed = true
  deferred_online_prelaunch_runner_evidence = true
  preflight_status_summary.required_evidence_present_count = 8
  preflight_status_summary.required_evidence_passed_count = 8
  preflight_status_summary.required_evidence_required_count = 9
  preflight_status_summary.runtime_gate_evidence_deferred_count = 1
  preflight_status_summary.strict_default_gate_evidence_deferred_count = 1

stage 2 final preflight:
  final_preflight_summary.passed = true
  final_preflight_status_summary.required_evidence_present_count = 9
  final_preflight_status_summary.required_evidence_passed_count = 9
  final_preflight_status_summary.required_evidence_required_count = 9
  final_preflight_status_summary.runtime_gate_evidence_deferred_count = 0
  final_preflight_status_summary.strict_default_gate_evidence_deferred_count = 0

runner passed = true
runner failures = []
native stub row_ok_count = 204 / 204
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

This preserves the default lab gate semantics while removing the
self-referential stale-runner loophole.

Validation:

```text
env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests/test_run_premap_online_native_stub_canary.py \
         tests/test_run_premap_lab_preflight.py -q

52 passed in 3.41s

env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests -q

662 passed, 2 warnings in 7.80s
```

Additional regression coverage:

```text
scripts/check_gate_evidence_paths.py:
  deferred_labels now has direct tests proving that only the named
  self-referential runner label is deferred. Other missing evidence labels
  still fail in strict mode.

scripts/check_runtime_gate_evidence_paths.py:
  runtime scans now propagate deferred_labels and expose deferred_count.

scripts/run_premap_online_native_stub_canary.py:
  runner summaries now surface deferred_count for both the prewrite defer
  preflight and the final strict preflight. The expected pattern is 1 deferred
  self-reference before the runner exists and 0 deferred labels after the
  current runner artifact has been written.
```

Full GPU1 online canary rerun:

```text
command:
  env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
    PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
    conda run -p /home/husrcf/anaconda3/envs/TRY \
    python scripts/run_premap_online_native_stub_canary.py \
      --gpu-index 1 \
      --stub-device 0 \
      --output-json \
        outputs/reports/premap_kernel_consumer/
        online_prelaunch_native_stub_canary_runner.json

result:
  runner passed = true
  failures = []
  trace step = passed
  native stub step = passed
  stage1 defer preflight = passed
  stage2 final preflight = passed

exported online input:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary/
    premap_native_typed_consumer_inputs/
    premap_native_typed_consumer_input_0000_sample_0_seq0_tok-1_layer0.json

native stub:
  row_count = 204
  row_ok_count = 204
  error_count = 0
  hash_accumulator = bf04cc3a2ce41fdf
  compiled macros:
    MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA = true
    MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION = true
    MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY = true
    MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME = true
    MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR = true

stage1 prewrite:
  required evidence = 8 / 9
  runtime deferred_count = 1
  strict default deferred_count = 1

stage2 final:
  required evidence = 9 / 9
  runtime deferred_count = 0
  strict default deferred_count = 0

boundary:
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
```

This confirms the two-stage gate with a fresh online export and native stub
execution, not only with cached evidence artifacts.

Artifact consistency checker:

```text
script:
  scripts/check_premap_online_native_stub_canary_artifacts.py

artifact:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check.json

passed = true
failures = []
runner_stub_row_count = 204
runner_stub_row_ok_count = 204
stage1_deferred_count = 1
final_deferred_count = 0
status_deferred_count = 0
runner_preflight_output_json matches full preflight artifact
runner_preflight_status_output_json matches compact status artifact
```

The checker verifies the three-file evidence set:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_runner.json

full preflight:
  outputs/reports/premap_lab_preflight_online_prelaunch_native_stub_canary.json

compact status:
  outputs/reports/premap_lab_preflight_status_online_prelaunch_native_stub_canary.json
```

It rejects stale status paths, nonzero final defer counts, stub row-count
mismatches, and payload/kernel-arg boundary violations.

Validation:

```text
env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests/test_check_premap_online_native_stub_canary_artifacts.py \
         tests/test_run_premap_online_native_stub_canary.py \
         tests/test_run_premap_lab_preflight.py -q

38 passed in 3.37s

env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests -q

666 passed, 2 warnings in 9.22s
```

### In-process native typed-consumer bridge

The prelaunch descriptor/address path now has an in-process typed-consumer
bridge check:

```text
PremapKernelArgShadowTableObject
-> to_native_typed_consumer_input_dict()
-> PremapNativeTypedConsumerBridgeCheck
-> PremapNativeStubOnlineInvocationCanary (live-disabled package only)
```

This validates the same typed input shape used by the standalone native/HIP
consumer stub while staying inside the vLLM prelaunch no-op path. It checks:

```text
schema hash
row / column count
table object hash
row order / ordered row hash
required descriptor / packed-weight / scale handles are nonzero
optional aux handle accounting
expert id and address-key hash validity
payload_bytes = 0
ready_credit = false
changes_router = false
changes_descriptor_order = false
passed_to_kernel = false
changes_kernel_launch_args = false
```

The bridge is emitted through the premap consumer shim and aggregated into the
long-run audit gate as `native_typed_consumer_bridge`. The native stub online
invocation remains a blocked canary package:

```text
native_checker_invoked = true
native_bridge_ok = true
native_stub_invoked = false
block_reason = native_stub_live_disabled
```

Verification:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
657 passed, 2 warnings
```

Online canary:

```text
script:
  scripts/run_premap_online_native_stub_canary.py --gpu-index 1 --stub-device 0

trace:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary.yaml

exported input:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary/
    premap_native_typed_consumer_inputs/
    premap_native_typed_consumer_input_0000_sample_0_seq0_tok-1_layer0.json

result:
  passed = true
  failures = []
  row_count = 204
  native_stub row_ok_count = 204
  native_stub error_count = 0
  preflight passed = true
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
```

Boundary remains unchanged:

```text
no payload transfer
no ready credit
no router mutation
no descriptor_order execution
no live native stub invocation
no kernel argument mutation
```

### Strict 128 native bridge + native-stub gate refresh

The in-process/native typed-consumer bridge is now validated as part of the
default strict 128 lab gate, not just the 1-sample canary.

Rerun:

```text
trace:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

output:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/

manifest rows = 128
```

Refreshed strict gate artifacts:

```text
native bridge:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate_native_typed_consumer_bridge.json

  passed = true
  failures = []
  require_native_typed_consumer_bridge = true

native bridge + native-stub online canary:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate_native_stub_online_invocation_canary.json

  passed = true
  failures = []
  require_native_typed_consumer_bridge = true
  require_native_stub_online_invocation_canary = true

combined audit copy:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate_native_bridge_and_stub_required.json

  passed = true
  failures = []
```

Long-run counters:

```text
premap_consumer_mapping_count = 10,195

native_typed_consumer_bridge:
  checked / ok = 10,195 / 10,195
  row_count = 110,898
  required_handle_nonzero = 332,694
  required_handle_zero = 0
  optional_handle_nonzero = 110,898
  optional_handle_zero = 0
  failure_count = 0
  payload_bytes = 0
  passed_to_kernel = 0
  kernel_arg_violation = 0

native_stub_online_invocation:
  checked / ready / ok = 10,195 / 10,195 / 10,195
  native_checker_invoked = 10,195
  native_bridge_ok = 10,195
  native_stub_invoked = 0
  block_reason = native_stub_live_disabled
  payload_bytes = 0
  passed_to_kernel = 0
  kernel_arg_violation = 0
```

Lab preflight:

```text
script:
  scripts/run_premap_lab_preflight.py

output:
  outputs/reports/premap_lab_preflight_native_bridge_and_stub_required_128.json

passed = true
failures = []
```

This promotes the typed bridge + native-stub online canary combination into the
strict 128 lab precondition while preserving the no-op boundary:

```text
no payload transfer
no ready credit
no router mutation
no descriptor_order execution
native stub package constructed but native_stub_invoked = 0
no kernel argument mutation
```

## Online prelaunch native typed-consumer stub canary

The typed native-consumer canary is now bound to an object exported from the
real vLLM/AWQ prelaunch shim, rather than only to a standalone/latest bridge
input.  The export is sample-limited and disabled by default; when enabled, it
writes the prepared kernel-arg shadow table in the JSON shape consumed by the
native HIP stub.

GPU1 1-sample/gen16 online export canary:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary.yaml

exported online table:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary/
    premap_native_typed_consumer_inputs/
    premap_native_typed_consumer_input_0000_sample_0_seq0_tok-1_layer0.json

source = vllm_prelaunch_premap_kernel_arg_shadow_table_object
row_count = 204
column_count = 4
schema_hash = a02928d41970cdf1630dc2a743589ab18068454ac47341a34c4583fd40a5f294
payload_bytes = 0
ready_credit = false
changes_router = false
changes_descriptor_order = false
passed_to_kernel = false
changes_kernel_launch_args = false
```

The native typed consumer stub consumed this online-exported table directly:

```text
artifact:
  outputs/reports/premap_kernel_consumer/
    typed_consumer_stub_gpu1_online_prelaunch_input_canary.json

passed = true
failures = []
ok = true
row_count = 204
row_ok_count = 204
error_count = 0
column_count = 4
input_source = binary_prefix
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

The default lab preflight now requires both native-stub evidences:

```text
native_typed_consumer_stub_gpu1_canary_json
native_typed_consumer_stub_online_prelaunch_input_canary_json
```

and verifies that each stub's `input_json` is bound to the corresponding gate
input path.  The online-prelaunch variant is bound to:

```text
native_typed_consumer_online_prelaunch_input_json
```

The online-prelaunch stub input check is stricter than the standalone bridge
input check.  It requires the exported input to carry:

```text
_meta.schema_hash / row_count / column_count
_meta.payload_bytes = 0
_meta.ready_credit = false
_meta.changes_router = false
_meta.changes_descriptor_order = false
_meta.passed_to_kernel = false
_meta.changes_kernel_launch_args = false

_export_context.source = vllm_prelaunch_premap_kernel_arg_shadow_table_object
_export_context.row_count / column_count / schema_hash / table_object_hash match _meta
_export_context payload/ready/router/order/kernel-arg fields remain no-op
```

Validation:

```text
env PYTHONPATH=$PWD:$PWD/src conda run -p /home/husrcf/anaconda3/envs/TRY \
  python scripts/run_premap_lab_preflight.py \
  --output-json outputs/reports/premap_lab_preflight_online_prelaunch_native_stub_canary.json

passed = true
failures = []

env PYTHONPATH=$PWD:$PWD/src conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests -q

654 passed, 2 warnings
```

Review follow-up:

```text
Spark review could not run because GPT-5.3-Codex-Spark quota was exhausted.
A default review found two important gate-hardening issues:
  1. online stub evidence needed binding to the canary performance summary;
  2. exported input summaries could be polluted by stale files if performance
     used directory globbing.
```

Fixes:

```text
performance_summary now records the exact paths exported by the current
recorder run instead of globbing the export directory.

lab preflight checks:
  native_typed_consumer_stub_online_prelaunch_input_canary_json.input_json
    == native_typed_consumer_online_prelaunch_input_json

  performance_summary.runtime_shadow_premap_native_typed_consumer_input_export_first_path
    == native_typed_consumer_online_prelaunch_input_json

  performance_summary.runtime_shadow_premap_native_typed_consumer_input_export_paths
    contains native_typed_consumer_online_prelaunch_input_json

  performance_summary.runtime_shadow_premap_native_typed_consumer_input_export_count > 0
```

Added negative tests for:

```text
unbound online-prelaunch stub input
online-prelaunch no-op metadata mutation
online-prelaunch export-summary path mismatch
```

An end-to-end runner now makes the online native-stub canary reproducible:

```text
script:
  scripts/run_premap_online_native_stub_canary.py

default chain:
  run 1-sample/gen16 vLLM/AWQ online export canary
  -> read performance_summary.runtime_shadow_premap_native_typed_consumer_input_export_first_path
  -> run HIP native typed consumer stub on that exported input
  -> run lab preflight
  -> write runner report

runner artifact:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_runner.json

runner passed = true
runner failures = []
trace step = passed
native stub step = passed
preflight step = passed
native stub row_ok_count = 204 / 204
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

The default lab gate now requires the runner artifact as well:

```text
native_typed_consumer_online_prelaunch_canary_runner_json
```

Validation after review fixes:

```text
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  PYTHONPATH=$PWD:$PWD/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  python scripts/run_premap_online_native_stub_canary.py \
  --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner.json

passed = true
failures = []

env PYTHONPATH=$PWD:$PWD/src conda run -p /home/husrcf/anaconda3/envs/TRY \
  python scripts/run_premap_lab_preflight.py \
  --output-json outputs/reports/premap_lab_preflight_online_prelaunch_native_stub_canary.json

passed = true
failures = []

env PYTHONPATH=$PWD:$PWD/src conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests -q

657 passed, 2 warnings
```

## Premap live-connected readonly lab gate

The default lab precondition has advanced from a disconnected kernel-side
typed-consumer shadow object to a live-connected readonly consumer envelope.
This still does not pass arguments to the fused-MoE/AWQ kernel; it only proves
that the prelaunch consumer shim can see the prepared handle table through the
future live handoff path while all mutation/payload paths remain blocked.

Default gate artifact:

```text
configs/runtime/
  premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml

strict evidence:
data/traces/
  external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
  longrun_audit_gate_live_connected_readonly.json

preflight:
outputs/reports/premap_lab_preflight_live_connected_readonly.json
```

GPU1 AWQ/vLLM 128-sample strict rerun:

```text
passed = true
failures = []
premap_summary = 10,195
premap_consumer_mapping = 10,195

live_toggle_enabled_count = 10,195
live_toggle_live_eligible_count = 10,195
live_toggle_block_reason = kernel_arg_handoff_kernel_consumer_not_connected

live_noop_integration_enabled_count = 10,195
live_noop_integration_consumer_connected_count = 10,195
live_noop_integration_block_reason = kernel_arg_handoff_kernel_arg_pass_disabled

live_consumer_adapter_enabled_count = 10,195
live_consumer_adapter_consumer_connected_count = 10,195
live_consumer_adapter_live_eligible_count = 10,195
live_consumer_adapter_block_reason = kernel_arg_handoff_kernel_arg_pass_disabled

kernel_side_consumer_schema_adapter_consumer_connected_count = 10,195
kernel_side_consumer_schema_adapter_live_enabled_count = 10,195
kernel_side_consumer_schema_adapter_live_eligible_count = 10,195
kernel_side_consumer_schema_adapter_block_reason = kernel_side_consumer_kernel_arg_pass_disabled

kernel_side_typed_consumer_object_consumer_connected_count = 10,195
kernel_side_typed_consumer_object_live_enabled_count = 10,195
kernel_side_typed_consumer_object_live_eligible_count = 10,195
kernel_side_typed_consumer_object_block_reason = kernel_side_typed_consumer_kernel_arg_pass_disabled

typed-consumer row_count = 110,898
typed-consumer handle_field_read_count = 443,592
required_source_miss_count = 0
optional_source_miss_count = 0
payload_bytes = 0
passed_to_kernel_count = 0
kernel_arg_violation_count = 0
changes_kernel_launch_args_count = 0
```

The lab preflight now requires this live-connected readonly evidence in
addition to the typed consumer object and native typed consumer bridge smoke.
Validation:

```text
pytest tests -q
646 passed, 2 warnings
```

Current boundary:

```text
live-connected readonly consumer path is a lab precondition
kernel_arg_pass remains disabled
real kernel arg mutation remains disabled
single-field replacement remains disabled
payload movement remains disabled
ready credit remains disabled
```

## Premap kernel-side typed consumer object gate

The premap consumer path now constructs a typed kernel-side consumer object that
matches the shape of the future fused-MoE/AWQ WNA16 descriptor/address consumer,
without passing it to the kernel.  This is stricter than the schema-adapter gate:
the object carries a typed consumer schema, row count, handle-table column count,
source hit/miss accounting, and the explicit live-disabled boundary.

GPU1 AWQ/vLLM 128-sample strict rerun:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate_typed_consumer_object_128.json

passed = true
failures = []
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_eviction_pressure_mean = 0.0
premap_address_resident_count_max = 10,127

kernel_side_typed_consumer_object_checked = 10,195
kernel_side_typed_consumer_object_ready = 10,195
kernel_side_typed_consumer_object_row_count = 110,898
kernel_side_typed_consumer_object_column_count_max = 4
kernel_side_typed_consumer_object_field_count_total = 112,145
  # 10,195 checked objects x 11 typed schema fields
required_source_hit_count = 332,694
required_source_miss_count = 0
optional_source_hit_count = 110,898
optional_source_miss_count = 0
handle_field_read_count = 443,592

typed_consumer_schema_name =
  fused_moe_awq_wna16_kernel_side_typed_consumer_object_v1
typed_consumer_schema_hash =
  c1384d55958c9aa78b07b4ee3e9094f835ec1ca4c61bd7e9613c01ceb8275e98

mode = readonly_kernel_side_typed_consumer_object
block_reason = kernel_side_typed_consumer_live_disabled
consumer_object_present = 10,195
consumer_connected = 0
live_enabled = 0
live_eligible = 0
live_compatible_with_current_wna16_args = 0
payload_bytes = 0
passed_to_kernel = 0
kernel_arg_violation = 0
```

The promoted gate report is now self-checkable: running
`scripts/check_premap_longrun_audit_gate.py` on
`longrun_audit_gate_typed_consumer_object_128.json` with the same strict flags
passes and emits `longrun_audit_gate_typed_consumer_object_128_selfcheck.json`.

The lab precondition artifact now requires:

```text
require_kernel_side_typed_consumer_object = true
```

Boundary remains unchanged:

```text
no payload transfer
no ready credit
no router mutation
no descriptor_order execution
no kernel argument mutation
no live kernel-side consumer connection
```

Live-connected blocked canary:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary/
    longrun_audit_gate_typed_consumer_object_connected_canary.json

self-check:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary/
    longrun_audit_gate_typed_consumer_object_connected_canary_selfcheck.json

passed = true
failures = []
kernel_side_typed_consumer_object_checked = 640
kernel_side_typed_consumer_object_ready = 640
kernel_side_typed_consumer_object_row_count = 9,794
kernel_side_typed_consumer_object_column_count_max = 4
kernel_side_typed_consumer_object_field_count_total = 7,040
required_source_hit_count = 29,382
required_source_miss_count = 0
optional_source_hit_count = 9,794
optional_source_miss_count = 0
handle_field_read_count = 39,176

mode = readonly_kernel_side_typed_consumer_object
block_reason = kernel_side_typed_consumer_kernel_arg_pass_disabled
consumer_object_present = 640
consumer_connected = 640
live_enabled = 640
live_eligible = 640
live_compatible_with_current_wna16_args = 0
payload_bytes = 0
passed_to_kernel = 0
kernel_arg_violation = 0
```

This canary exercises the connected-but-blocked branch only.  It proves that a
typed kernel-side consumer object can be constructed while the prelaunch
consumer is connected and live-eligible, but the current WNA16 launch remains
incompatible and kernel-arg pass stays disabled.  It is not the default lab
gate and it still performs no payload movement, ready-credit grant, or kernel
argument mutation.

Live-kernel-pass typed-object canary:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_kernel_arg_pass_canary/
    kernel_arg_pass_typed_consumer_object_gate_check.json

self-check:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_kernel_arg_pass_canary/
    kernel_arg_pass_typed_consumer_object_gate_check_selfcheck.json

passed = true
failures = []
runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled = true

live_consumer_adapter:
  block_reason = kernel_arg_handoff_kernel_arg_pass_live
  passed_to_kernel_count = 640
  changes_kernel_launch_args_count = 640
  kernel_arg_violation_count = 640
  real_kernel_arg_handoff_count = 0

kernel_side_typed_consumer_object:
  mode = readonly_kernel_side_typed_consumer_object
  block_reason = kernel_side_typed_consumer_shadow_only_kernel_arg_pass_enabled
  checked = 640
  ready = 640
  row_count = 9,794
  typed_consumer_field_count_total = 7,040
  required_source_hit_count = 29,382
  required_source_miss_count = 0
  optional_source_hit_count = 9,794
  optional_source_miss_count = 0
  handle_field_read_count = 39,176
  payload_bytes = 0
  passed_to_kernel = 0
  kernel_arg_violation = 0
  live_compatible_with_current_wna16_args = 0
```

This is a negative/live-pass canary, not a default lab gate.  The live consumer
adapter intentionally records that the current WNA16 tensor-arg interface would
be violated, while the typed kernel-side consumer object remains a read-only
shadow object and never passes payload or kernel arguments.  This confirms that
the typed consumer contract survives the live-pass flag without pretending that
the current kernel can consume the handle schema.

Preflight hardening:

```text
risky canary gates:
  live_kernel_arg_pass_canary
  real_kernel_arg_mutation_canary

required metadata:
  canary = true
  lab_default = false
```

`scripts/run_premap_lab_preflight.py` now rejects risky kernel-arg pass /
mutation artifacts that are not explicitly marked canary-only, while keeping the
default readonly lab gate disconnected and live-disabled.

## 2026-05-27 - Kernel-Side Consumer Schema Adapter Gate

The premap kernel-side consumer schema adapter is now live-aware while
remaining blocked and side-effect free.  The default lab gate stays
live-disabled, and explicit live-connected canaries are allowed only as
blocked schema checks:

```text
default lab gate:
  live_enabled = 0
  consumer_connected = 0
  live_eligible = 0
  block_reason = kernel_side_consumer_live_disabled

live-connected canary gate:
  live_enabled = checked_count
  consumer_connected = checked_count
  live_eligible = checked_count
  block_reason = kernel_side_consumer_kernel_arg_pass_disabled

always required:
  payload_bytes = 0
  passed_to_kernel_count = 0
  kernel_arg_violation_count = 0
  live_compatible_with_current_wna16_args_count = 0
```

Evidence:

```text
default strict 128 gate:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate_kernel_side_consumer_schema_adapter.json

live-connected 1-sample gate:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary/
    connected_blocked_kernel_side_schema_gate_check.json

live-connected 8-sample gate:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_connected_adapter_canary/
    connected_blocked_kernel_side_schema_gate_check.json
```

Validation:

```text
pytest tests -q: 606 passed
scripts/run_premap_lab_preflight.py: passed
```

This is still a schema/consumer readiness gate, not a real kernel argument
handoff.  The next safe boundary is a typed kernel-side consumer schema object
that a future kernel can consume, still without payload movement or live kernel
argument mutation.

## Prepared handle-table candidate dry-run gate

The single-field kernel-arg replacement gate now supports an explicit
`prepared_handle_table` candidate source in dry-run mode.  This source resolves
the candidate value from the prepared descriptor/address table instead of using
the original kernel argument identity value.

Safety boundary:

```text
candidate_source = prepared_handle_table
live replacement = disabled
payload_bytes = 0
passed_to_kernel = 0
```

The candidate is intentionally expected to be type/signature incompatible with
the current WNA16 tensor kernel argument.  This validates that the prepared
handle table can be resolved as a candidate source, while preventing it from
being treated as a live tensor-compatible kernel arg.

GPU1 AWQ/vLLM 1-sample canary:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_single_field_replacement_prepared_table_candidate_dry_run_canary.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_single_field_replacement_prepared_table_candidate_dry_run_canary/
    prepared_table_candidate_dry_run_gate_check.json

lab gate artifact:
  configs/runtime/
    premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_prepared_table_candidate_dry_run.yaml

passed = true
failures = []

candidate_source = prepared_handle_table
dry_run_candidate_count = 1,280
dry_run_parity_ok_count = 0
dry_run_parity_mismatch_count = 1,280

prepared_table_candidate_count = 1,280
prepared_table_hit_count = 1,280
prepared_table_miss_count = 0
prepared_table_type_compatible_count = 0
prepared_table_type_mismatch_count = 1,280

live_disabled_count = 1,280
live_passed_to_kernel_count = 0
```

The checker rejects this source unless the report uses the explicit
`--allow-single-field-replacement-prepared-table-candidate-source` gate, and it
also rejects any prepared-table source with live replacement enabled.

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
588 passed, 2 warnings
```

Review hardening:

```text
candidate_source = prepared_handle_table now also requires:
  single_field_replacement_dry_run_enabled = true
  live replacement = false
  field in {B, B_scale, B_zp}

The runtime live branch also re-checks:
  candidate_source == original_kernel_arg_identity
  type_compatible = true

This prevents a future config from enabling the prepared-table source without
actually producing candidate hit/type/parity evidence.
```

### 2026-05-26: 128-sample strict real kernel-arg mutation canary passed

The live kernel-arg mutation canary has been promoted from 1/8-sample smoke to
a 128-sample strict lab gate candidate.

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_real_kernel_arg_mutation_strict.yaml

gate:
  configs/runtime/
    premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_real_kernel_arg_mutation_canary.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_real_kernel_arg_mutation_strict/
    real_kernel_arg_mutation_gate_check.json

passed = true
failures = []

package_seen_count = 20,390
package_pass_through_count = 20,390
package_missing_count = 632,090  # expected with sampled consumer mappings
package_layer_mismatch_count = 0
package_block_reason_mismatch_count = 0

adapter_real_kernel_arg_handoff_count = 10,195
adapter_passed_to_kernel_count = 10,195
adapter_changes_kernel_launch_args_count = 10,195
adapter_payload_bytes = 0

premap_address_resident_count_max = 10,127
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_eviction_pressure_mean = 0.0
```

Interpretation:

```text
The prelaunch consumer can hand the WNA16 wrapper a live kernel-argument package
at 128-sample scale, and the wrapper actually consumes that package to call the
original WNA16 kernel with pass-through values.

This is a launch-argument source mutation only:
the values remain unchanged, payload bytes remain zero, and descriptor/address
handles are not yet substituted into the live kernel arguments.
```

Next gate:

```text
single-field replacement dry-run:
construct a shadow replacement candidate for one kernel-arg field,
validate runtime identity parity,
but keep the live kernel call on the original pass-through package values.
```

The first single-field replacement dry-run canary uses `B_scale` as the
candidate field and keeps the actual WNA16 launch on the pass-through package.

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_single_field_replacement_dry_run_canary.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_single_field_replacement_dry_run_canary/
    single_field_replacement_dry_run_gate_check.json

passed = true
failures = []

single_field_replacement_dry_run_enabled = true
single_field_replacement_field = B_scale
candidate_count = 1,280
parity_ok_count = 1,280
parity_mismatch_count = 0
source_missing_count = 0
unsupported_field_count = 0
single_field_passed_to_kernel_count = 0
single_field_payload_bytes = 0
```

This proves the next handoff boundary can construct a one-field replacement
candidate and validate runtime identity parity without passing that replacement
to the kernel.  It is still a dry-run; no descriptor/address handle is
substituted into live launch arguments yet.

## Premap live kernel-arg mutation canary

The premap kernel-arg handoff path now has an explicit real-mutation canary
above the previous no-op/lab-gated adapter envelope.  This is the first live
boundary where the original WNA16 launch reads its arguments from a prelaunch
consumer package object.

Scope:

```text
enabled only by an explicit lab gate
WNA16 launch arguments are pass-through values
the argument source changes, but the values do not
payload movement remains disabled
prepared descriptor/address table is not passed as a kernel argument
```

GPU1 AWQ/vLLM 1-sample gen16 canary:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_real_kernel_arg_mutation_canary.yaml

gate:
  configs/runtime/
    premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_real_kernel_arg_mutation_canary.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_real_kernel_arg_mutation_canary/
    real_kernel_arg_mutation_gate_check.json

failures = []
runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled = true

kernel_arg_handoff_live_consumer_adapter_checked_count = 640
kernel_arg_handoff_live_consumer_adapter_block_reason =
  kernel_arg_handoff_real_kernel_arg_mutation_live
kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count = 640
kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count = 640
kernel_arg_handoff_live_consumer_adapter_contract_live_pass_count = 640
kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count = 640
kernel_arg_handoff_live_consumer_adapter_payload_bytes = 0

handle_table_object_passed_to_kernel_count = 0
handle_table_consume_passed_to_kernel_count = 0
prep_execution_dry_run_passed_to_kernel_count = 0

actual WNA16 package-consumed counters:
  package_seen_count = 1,280
  package_pass_through_count = 1,280
  package_missing_count = 0
  package_layer_mismatch_count = 0
  package_block_reason_mismatch_count = 0
```

Fail-closed check:

```text
same canary without --allow-kernel-arg-handoff-live-real-kernel-arg-mutation
fails with:
  kernel_arg_handoff_real_kernel_arg_mutation_enabled_true
  consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_mismatch
  consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count_mismatch=640!=0
```

Validation:

```text
py_compile passed
targeted pytest: 140 passed
full tests: 578 passed
```

GPU1 AWQ/vLLM 8-sample gen64 follow-up:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_real_kernel_arg_mutation_canary.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_real_kernel_arg_mutation_canary/
    real_kernel_arg_mutation_gate_check.json

failures = []
runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled = true

consumer_shim_executed_count = 640
kernel_arg_handoff_live_consumer_adapter_checked_count = 640
kernel_arg_handoff_live_consumer_adapter_block_reason =
  kernel_arg_handoff_real_kernel_arg_mutation_live
kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count = 640
kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count = 640
kernel_arg_handoff_live_consumer_adapter_contract_live_pass_count = 640
kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count = 640
kernel_arg_handoff_live_consumer_adapter_payload_bytes = 0

handle_table_object_passed_to_kernel_count = 0
handle_table_consume_passed_to_kernel_count = 0
prep_execution_dry_run_passed_to_kernel_count = 0

actual WNA16 package-consumed counters:
  package_seen_count = 1,280
  package_pass_through_count = 1,280
  package_missing_count = 39,680
  package_layer_mismatch_count = 0
  package_block_reason_mismatch_count = 0

premap_address_resident_count_max = 8,931
premap_address_reuse_rate_mean = 0.8665469360581731
```

The 8-sample canary uses sampled premap manager/consumer rows and is still a
mutation-boundary smoke, not the long-run address-reuse gate.  The canary gate
therefore sets `min_reuse_rate = 0.0`; long-run lab gates continue to own the
reuse/capacity threshold.  The nonzero `package_missing_count` is expected in
this sampled mode because unsampled WNA16 launches have no prelaunch package;
the gate requires pass-through coverage for the sampled real-handoff adapter
rows and requires layer/block-reason mismatches to remain zero.

Boundary remains:

```text
not a full_fetch path
not a payload residency claim
not a performance claim
not a descriptor/address replacement path yet
```

## 2026-05-25: connected-but-blocked live consumer adapter canary

The kernel-arg handoff no-op envelope now has one additional canary stage:

```text
premap_kernel_arg_handoff_live_enabled = true
premap_kernel_arg_handoff_live_consumer_connected = true
```

When this canary is enabled, the prelaunch consumer adapter may report:

```text
consumer_connected = true
block_reason = kernel_arg_handoff_kernel_arg_pass_disabled
```

but the safety boundary is still unchanged:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
ready_credit = false
```

The default lab/audit configs still keep the connected canary disabled.  The
runtime gate loader now rejects `premap_kernel_arg_handoff_live_consumer_connected`
unless `premap_kernel_arg_handoff_live_enabled` is also true and the readonly lab
gate contract explicitly requires the connected-but-blocked state.

Validation:

```text
targeted:
  pytest tests/test_runtime_premap.py \
         tests/test_vllm_premap_capacity_gate.py \
         tests/test_check_premap_longrun_audit_gate.py \
         tests/test_runtime_shadow_log.py -q
  138 passed

full:
  pytest tests -q
  539 passed, 2 warnings
```

Runtime canary smoke:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary.yaml

gate:
  configs/runtime/
    premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_blocked_canary.yaml

run-local copy used for this smoke:
  tmp/live_adapter_connected_canary_smoke/
    trace_live_connected_blocked_consumer_adapter_canary.yaml

artifact:
  /tmp/mtp_connected_adapter_canary_smoke/
    performance_summary.json
    connected_blocked_gate_check.json

committed-config artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary/
      performance_summary.json
      connected_blocked_gate_check.json

checker:
  --require-kernel-arg-handoff-live-toggle
  --require-kernel-arg-handoff-launch-schema-mirror
  --require-kernel-arg-handoff-live-noop-integration
  --require-kernel-arg-handoff-live-consumer-adapter
  --allow-enabled-blocked-live-toggle
  --allow-connected-blocked-consumer-adapter

The committed canary gate records these two `allow_*` checker flags under
`gate.check` so the non-default validation mode is self-describing.

passed = true
failures = []
live_noop_integration_checked = 640
live_noop_integration_consumer_connected = 640
live_noop_integration_blocked = 640
live_noop_integration_block_reason =
  kernel_arg_handoff_kernel_arg_pass_disabled
live_noop_integration_payload_bytes = 0
live_noop_integration_passed_to_kernel = 0
live_noop_integration_changes_kernel_launch_args = 0
live_noop_integration_ready_credit = false
live_noop_integration_kernel_arg_violation = 0

live_consumer_adapter_checked = 640
live_consumer_adapter_consumer_connected = 640
live_consumer_adapter_blocked = 640
live_consumer_adapter_block_reason =
  kernel_arg_handoff_kernel_arg_pass_disabled
live_consumer_adapter_payload_bytes = 0
live_consumer_adapter_passed_to_kernel = 0
live_consumer_adapter_changes_kernel_launch_args = 0
live_consumer_adapter_ready_credit = false
live_consumer_adapter_kernel_arg_violation = 0
```

This is still a canary-only no-op boundary check.  It does not pass any new
kernel arguments, move payload, or grant ready credit.

Hardened-checker recheck:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary/
      performance_summary.json

checker flags:
  --allow-enabled-blocked-live-toggle
  --allow-connected-blocked-consumer-adapter

passed = true
failures = []
live_consumer_adapter_checked = 640
live_consumer_adapter_consumer_connected = 640
live_consumer_adapter_blocked = 640
live_consumer_adapter_changes_kernel_launch_args = 0
live_consumer_adapter_kernel_arg_violation = 0
```

This confirms that the checker hardening still accepts the explicitly allowed
connected-but-blocked canary, while the default strict checker invocation
without the canary `allow_*` flags keeps the consumer disconnected and blocked.

8-sample connected-but-blocked canary:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_connected_adapter_canary.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_connected_adapter_canary/
      performance_summary.json
      connected_blocked_gate_check.json

runtime flags:
  runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled = false
  runtime_shadow_premap_kernel_arg_handoff_live_enabled = true
  runtime_shadow_premap_kernel_arg_handoff_live_consumer_connected = true

summary counts:
  premap_summary_count = 640
  premap_consumer_mapping_count = 640

checker with canary allow flags:
  passed = true
  failures = []
  live_consumer_adapter_checked = 640
  live_consumer_adapter_consumer_connected = 640
  live_consumer_adapter_blocked = 640
  live_consumer_adapter_payload_bytes = 0
  live_consumer_adapter_payload_violation_count = 0
  live_consumer_adapter_record_ready_count = 640
  premap_consumer_ready_credit_violation_count = 0
  live_consumer_adapter_changes_kernel_launch_args = 0
  live_consumer_adapter_kernel_arg_violation = 0

default strict checker without canary allow flags:
  passed = false
  expected failures include at least enabled/live-eligible/consumer-connected mismatch
```

This 8-sample run scales the connected-but-blocked canary smoke while preserving
the same safety boundary: no payload bytes, audit-only ready records with no
ready-credit violation, and no kernel-argument mutation.  It remains a canary
path and does not replace the default 128-sample lab gate.

Gate evidence-path checker:

```text
script:
  scripts/check_gate_evidence_paths.py

local strict validation:
  gate:
    configs/runtime/
      premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_blocked_canary.yaml
  command mode:
    --strict --require-json
  output:
    data/traces/
      external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_connected_adapter_canary/
        evidence_paths_check.json
  passed = true
  evidence_path_count = 12
  missing_count = 0
  invalid_json_count = 0
```

Default lab-gate strict evidence-path validation:

```text
script:
  scripts/check_gate_evidence_paths.py
command mode:
  --strict --require-json
gate:
  configs/runtime/
    premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml
output:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
      evidence_paths_check.json
passed = true
evidence_path_count = 8
missing_count = 0
invalid_json_count = 0
```

Runtime gate broad scan:

```text
script:
  scripts/check_runtime_gate_evidence_paths.py
scope:
  configs/runtime/*.yaml
mode:
  --require-json
result:
  total_runtime_yaml = 7
  passed = 7
  pattern_failure_count = 0
  evidence_section_present_count = 4
  evidence_section_missing_count = 3
  evidence_path_count = 36
  missing_count = 0 for all 4 evidence-bearing gates

Interpretation:
  passed = 7 because the CLI default allows missing evidence sections for
  non-evidence runtime configs; strict lab validation should use --strict and,
  when appropriate, --require-evidence-section.

evidence-bearing gates:
  descriptor_order_direct_topk_layer_allowlist_awq_w7900_gpu1.yaml:
    evidence_path_count = 8
  premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml:
    evidence_path_count = 8
  premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml:
    evidence_path_count = 8
  premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_blocked_canary.yaml:
    evidence_path_count = 12
```

Premap lab preflight:

```text
script:
  scripts/run_premap_lab_preflight.py
output:
  /tmp/premap_lab_preflight.json
passed = true
failures = []

covered checks:
  runtime gate evidence scan:
    gate_count = 7
    passed_gate_count = 7
    evidence_path_count = 36
    missing_count = 0
    invalid_json_count = 0
  strict gate evidence checks:
    default_readonly_gate: passed
    connected_blocked_canary_gate: passed
  trace config wiring:
    128-sample longrun: passed
      premap_kernel_arg_handoff_live_enabled = false
      premap_kernel_arg_handoff_kernel_arg_pass_enabled = false
    512-sample longrun: passed
      premap_kernel_arg_handoff_live_enabled = false
      premap_kernel_arg_handoff_kernel_arg_pass_enabled = false

extra safety:
  default_readonly_gate_equals_canary_gate is rejected
```

This preflight is a local read-only check.  The `/tmp/premap_lab_preflight.json`
file is generated output, not a persistent source artifact.

The checker defaults to allowing missing evidence paths at the CLI level because
`data/traces/*` is intentionally not tracked by git.  Use `--strict` for local
lab validation when the artifacts are present.  The `evidence_paths_check.json`
file is a local generated check result, not a persistent source artifact.

## 2026-05-25 - Kernel-Arg Launch-Schema Mirror Gate

Implemented a stricter prelaunch consumer mirror that is closer to the future
fused-MoE/AWQ launch schema while still remaining a no-op:

```text
mode = readonly_kernel_arg_handoff_launch_schema_mirror
launch_schema = fused_moe_awq_wna16_prelaunch_descriptor_address_v1
fields =
  sorted_token_ids_ref
  expert_ids_ref
  num_tokens_post_padded_ref
  descriptor_ptr_table_ref
  packed_weight_descriptor_table_ref
  scale_metadata_handle_table_ref
  aux_metadata_handle_table_ref
  row_order_hash
  ordered_row_hash
```

Contract:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
required descriptor/packed-weight/scale handle hits = 3 x row_count
handle field reads = 4 x row_count
launch_arg_field_count = checked_count x 9
```

Added runtime fields, shadow aggregation, performance-summary flattening, and
`check_premap_longrun_audit_gate.py --require-kernel-arg-handoff-launch-schema-mirror`.
The checker now treats launch-schema mirror fields as active only when
`checked_count > 0`, so zero-valued default aggregate keys do not falsely fail
legacy/non-enabled summaries.

Validation:

```text
pytest tests -q
  524 passed, 2 warnings

GPU1 AWQ 8-sample smoke:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml

performance_summary:
  launch_schema_mirror_checked_count = 20,480
  launch_schema_mirror_ready_count = 20,480
  launch_schema_mirror_row_count = 190,215
  launch_schema_mirror_handle_field_read_count = 760,860
  launch_schema_mirror_launch_arg_field_count = 184,320
  launch_schema_name = fused_moe_awq_wna16_prelaunch_descriptor_address_v1
  launch_schema_hash = 576c83df9f825786d494ae3fe1f2286fcbae1afc876b243e748bae8e5b804984
  payload_bytes = 0
  passed_to_kernel_count = 0
  kernel_arg_violation_count = 0
```

The smoke passes the full descriptor/address/consumer/kernel-arg mirror
contract when using a smoke-appropriate reuse threshold (`min_reuse_rate=0.80`).
It does not replace the 128-sample lab default gate because the 8-sample address
reuse rate is lower (`0.867`) than the long-run lab threshold (`0.98`).

## Kernel-arg handoff mirror no-op gate

The prelaunch consumer now constructs a no-op mirror of the future fused-MoE/AWQ
kernel argument package under the existing kernel-arg shadow-slot gate.  This is
the first integration step toward a kernel-arg handoff object, but it still does
not pass any argument package to the live kernel launch.

Mirror object contract:

```text
mode = readonly_kernel_arg_handoff_mirror
slot_hash = kernel_arg_handoff_shadow_slot.hash
table_object_hash = prepared handle-table object hash
row_count / column_count / schema_hash
row_order_hash / ordered_row_hash
descriptor_ptr_arg_hash
packed_weight_descriptor_arg_hash
scale_metadata_handle_arg_hash
aux_metadata_handle_arg_hash
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

GPU1 AWQ/vLLM 8-sample smoke:

```text
mirror_checked = 640
mirror_ready = 640
mirror_row_count = 6,965
mirror_required_source_hit_count = 20,895
mirror_required_source_miss_count = 0
mirror_optional_source_hit_count = 6,965
mirror_optional_source_miss_count = 0
mirror_payload_bytes = 0
mirror_passed_to_kernel_count = 0
mirror_kernel_arg_violation_count = 0
```

GPU1 AWQ/vLLM 128-sample strict rerun:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate.json

passed = true
failures = []

mirror_checked = 10,195
mirror_ready = 10,195
mirror_hash_checked = 10,195
mirror_hash_missing = 0
mirror_slot_hash_checked = 10,195
mirror_slot_hash_missing = 0

mirror_row_count = 110,898
mirror_column_count_min = 4
mirror_column_count_max = 4
mirror_schema_hash =
  a02928d41970cdf1630dc2a743589ab18068454ac47341a34c4583fd40a5f294
mirror_schema_hash_checked = 10,195
mirror_schema_hash_missing = 0
mirror_schema_hash_mismatch = 0

mirror_required_source_hit_count = 332,694
mirror_required_source_miss_count = 0
mirror_optional_source_hit_count = 110,898
mirror_optional_source_miss_count = 0

mirror_payload_bytes = 0
mirror_payload_violation_count = 0
mirror_passed_to_kernel_count = 0
mirror_kernel_arg_violation_count = 0
```

Static review found no blocker/high-risk issue.  The medium review item was
diagnostic: mirror hash coverage was not directly regression-tested against
slot/table/row/order/arg-hash changes.  This is now covered by
`test_kernel_arg_handoff_mirror_hash_covers_slot_table_rows_and_args`.

Boundary remains unchanged:

```text
no payload transfer
no ready credit
no router mutation
no descriptor_order execution
no live kernel argument mutation
```

### Kernel-arg handoff shadow slot gate

The descriptor/address prep path now constructs a final readonly shadow slot
that mirrors the argument package a future fused-MoE/AWQ kernel consumer would
receive.  The slot binds to the prepared table object hash and records the table
schema, row count, row/order hashes, required/optional source availability, and
explicit no-op side-effect flags.  It is still only recorded; it is not passed
to any kernel.

Validation:

```text
tests:
  pytest tests -q
  502 passed

compile:
  python -m compileall -q src scripts tests
```

Online smoke:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke.yaml

slot_checked = 640
slot_ready = 640
slot_row_count = 6,965
slot_column_count_min/max = 4 / 4
slot_schema_hash_checked = 640
slot_schema_hash_missing = 0
slot_required_source_hit = 20,895
slot_required_source_miss = 0
slot_optional_source_hit = 6,965
slot_payload_bytes = 0
slot_passed_to_kernel_count = 0
slot_kernel_arg_violation_count = 0
```

Strict 128-sample lab gate:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate.json

passed = true
failures = []

slot_checked = 10,195
slot_ready = 10,195
slot_hash_checked = 10,195
slot_hash_missing = 0
slot_row_count = 110,898
slot_column_count_min/max = 4 / 4
slot_schema_hash_checked = 10,195
slot_schema_hash_missing = 0
slot_schema_hash_mismatch = 0
slot_required_source_hit = 332,694
slot_required_source_miss = 0
slot_optional_source_hit = 110,898
slot_optional_source_miss = 0
slot_payload_bytes = 0
slot_payload_violation_count = 0
slot_passed_to_kernel_count = 0
slot_kernel_arg_violation_count = 0
```

This upgrades the lab precondition from a consumed handle table to a concrete
kernel-argument handoff shadow package, while preserving the same safety
boundary:

```text
no payload transfer
no ready credit
no router mutation
no descriptor_order execution
no kernel argument handoff
```

### Kernel-arg handoff dry-run gate

The prelaunch consumer shim now emits an explicit kernel-argument handoff
dry-run readiness record.  This is still a read-only gate: the shim validates
that the prepared handle table has all fields required by a future kernel
handoff, but it does not pass any table to the kernel and does not move payload.

Implementation contract:

```text
mode = readonly_kernel_arg_handoff_dry_run
ready iff:
  table consume passed
  row_count matches consumed handle-table rows
  descriptor_ptr / packed_weight_descriptor / scale_metadata_handle all hit
  required source misses = 0
  optional aux hit + miss = row_count
  payload_bytes = 0
  passed_to_kernel = false
```

GPU1 AWQ 8-sample smoke:

```text
premap_summary = 640
premap_consumer_mapping = 640
handoff_dry_run_checked = 640
handoff_dry_run_ready = 640
handoff_dry_run_row_count = 6,965
handoff_dry_run_required_source_hit_count = 20,895
handoff_dry_run_required_source_miss_count = 0
handoff_dry_run_optional_source_hit_count = 6,965
handoff_dry_run_optional_source_miss_count = 0
handoff_dry_run_payload_bytes = 0
handoff_dry_run_passed_to_kernel_count = 0
```

The strict checker validates the handoff dry-run fields under
`--require-consumer-shim-table-consume`.  The 8-sample smoke still fails the
long-run reuse threshold, as expected for the small split, but all readonly
descriptor-prep / table-consume / handoff-dry-run safety fields pass.

The same gate was then rerun on the full Dolly-128 GPU1 AWQ long-run artifact:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate.json

passed = true
failures = []
premap_summary = 10,195
premap_consumer_mapping = 10,195
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_resident_count_max = 10,127

handoff_dry_run_checked = 10,195
handoff_dry_run_ready = 10,195
handoff_dry_run_row_count = 110,898
handoff_dry_run_column_count_min/max = 4 / 4
handoff_dry_run_schema_hash_checked = 10,195
handoff_dry_run_schema_hash_missing = 0
handoff_dry_run_required_source_hit_count = 332,694
handoff_dry_run_required_source_miss_count = 0
handoff_dry_run_optional_source_hit_count = 110,898
handoff_dry_run_optional_source_miss_count = 0
handoff_dry_run_payload_bytes = 0
handoff_dry_run_passed_to_kernel_count = 0
```

This upgrades the lab precondition from “prepared table object can be consumed”
to “prepared table object is ready for a future readonly kernel-argument
handoff contract”, while still explicitly forbidding payload movement and
kernel argument mutation.

The handoff dry-run readiness is now schema-bound: the checker requires the
same four-column handle-table schema used by the kernel-arg shadow table and
rejects missing or mismatched schema hashes.

### 2026-05-24 - Lab gate now requires explicit prelaunch consumer table use

The readonly premap lab precondition was tightened again. The prelaunch
consumer shim must now explicitly consume the prepared handle table fields, not
only observe the table object or dry-run preparation result.

Default lab gate artifact:

```text
configs/runtime/
  premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml

contract.consumer_shim_table_consume_handle_field_reads_required = true
```

The runtime event and aggregate now report consumer-side table-consume field
reads separately from prep-execution dry-run field reads:

```text
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count
premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count
```

The committed 128-sample lab gate artifact records:

```text
row_count = 110,898
consumer_shim_table_consume_handle_field_read_count = 443,592
consumer_shim_table_consume_required_handle_field_available_count = 332,694
consumer_shim_table_consume_optional_handle_field_available_count = 110,898
consumer_shim_table_consume_payload_bytes = 0
consumer_shim_table_consume_passed_to_kernel_count = 0
```

A fresh GPU1 8-sample smoke with full VRAM (`gpu_memory_utilization=0.98`)
validated that the new fields are emitted by the online path:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke.yaml

output:
  data/traces/
    external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke/

consumer_shim_table_consume_checked_count = 640
consumer_shim_table_consume_row_count = 6,965
consumer_shim_table_consume_handle_field_read_count = 27,860
consumer_shim_table_consume_required_handle_field_available_count = 20,895
consumer_shim_table_consume_optional_handle_field_available_count = 6,965
consumer_shim_table_consume_payload_bytes = 0
consumer_shim_table_consume_passed_to_kernel_count = 0
```

The strict reuse threshold is still a long-run criterion: this 8-sample smoke
emits the prelaunch consumer fields correctly, but its address reuse rate is
0.8665 and therefore does not satisfy the 0.98 long-run reuse gate.

### 2026-05-24 - Prelaunch consumer table source-class attribution

The prelaunch consumer shim now reports source-class hit/miss counts for the
prepared handle table fields it explicitly consumes:

```text
descriptor_ptr
packed_weight_descriptor
scale_metadata_handle
aux_metadata_handle
```

This is still a no-op consumer boundary:

```text
payload_bytes = 0
passed_to_kernel = 0
ready_credit = false
kernel args unchanged
```

The same GPU1 8-sample smoke path now emits the source-class availability in
`performance_summary.json`:

```text
consumer_shim_table_consume_row_count = 6,965
descriptor_ptr_hit_count = 6,965
descriptor_ptr_miss_count = 0
packed_weight_descriptor_hit_count = 6,965
packed_weight_descriptor_miss_count = 0
scale_metadata_handle_hit_count = 6,965
scale_metadata_handle_miss_count = 0
aux_metadata_handle_hit_count = 6,965
aux_metadata_handle_miss_count = 0
```

This makes the lab precondition more actionable for the next integration gate:
the shim can distinguish field-level availability by source class before any
future kernel-argument handoff is attempted.

The strict gate checker now enforces this source-class contract whenever
consumer table consumption is required:

```text
descriptor_ptr hit_count == row_count and miss_count == 0
packed_weight_descriptor hit_count == row_count and miss_count == 0
scale_metadata_handle hit_count == row_count and miss_count == 0
aux_metadata_handle hit_count == aux_available_count
aux_metadata_handle hit_count + miss_count == row_count
```

The current 8-sample smoke still fails the long-run reuse threshold, but passes
the new source-class checks; its only strict-gate failure is:

```text
premap_address_reuse_rate_below_threshold
```

The full 128-sample GPU1 long-run was rerun after adding the source-class gate,
and the strict lab gate now passes from freshly generated runtime summaries:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml

artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate.json

passed = true
failures = []
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_resident_count_max = 10,127

consumer_shim_table_consume_row_count = 110,898
consumer_shim_table_consume_handle_field_read_count = 443,592
consumer_shim_table_consume_required_handle_field_available_count = 332,694

descriptor_ptr_hit_count = 110,898
descriptor_ptr_miss_count = 0
packed_weight_descriptor_hit_count = 110,898
packed_weight_descriptor_miss_count = 0
scale_metadata_handle_hit_count = 110,898
scale_metadata_handle_miss_count = 0
aux_metadata_handle_hit_count = 110,898
aux_metadata_handle_miss_count = 0

consumer_shim_table_consume_payload_bytes = 0
consumer_shim_table_consume_passed_to_kernel_count = 0
```

## Premap prelaunch no-op consumer boundary gate

The premap descriptor/address prep object is now checked against the real
fused-MoE/AWQ prelaunch expert-assignment boundary in no-op mode.  The runtime
records a prelaunch source and verifies that the prepared address/handle rows
align with the actual descriptor/address resolution domain before the kernel
launch, while still not passing any new kernel arguments.

Prelaunch boundary fields:

```text
premap_consumer_prelaunch_boundary_source
premap_consumer_prelaunch_handle_available
premap_consumer_prelaunch_block_count
premap_consumer_prelaunch_block_size
premap_consumer_prelaunch_expert_order_hash
premap_consumer_prelaunch_expert_multiset_hash
premap_consumer_prelaunch_unique_expert_count
premap_consumer_prelaunch_boundary_aligned
```

Important semantic fix:

```text
boundary alignment is checked against the resolved valid-expert/address-key
domain, not the raw active expert block list.  Invalid/OOB experts and duplicate
blocks cannot make the no-op boundary appear aligned.
```

GPU1 AWQ/vLLM 128-sample strict rerun:

```text
artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
    longrun_audit_gate.json

passed = true
failures = []
premap_summary = 10,195
premap_consumer_mapping = 10,195
premap_prelaunch_boundary_checked = 10,195
premap_prelaunch_boundary_aligned_rate = 1.0
premap_prelaunch_handle_available_rate = 1.0
premap_prelaunch_block_count = 110,898
premap_prelaunch_unique_expert_count = 110,898

prep_execution_dry_run_checked = 10,195
prep_execution_dry_run_row_count = 110,898
prep_execution_dry_run_handle_field_read_count = 443,592
prep_execution_dry_run_required_handle_field_available_count = 332,694
prep_execution_dry_run_optional_handle_field_available_count = 110,898
prep_execution_dry_run_row_handle_miss_count = 0
prep_execution_dry_run_payload_bytes = 0
prep_execution_dry_run_passed_to_kernel_count = 0
```

The strict gate now requires the consumer shim to explicitly read every
prepared handle-table field before it can pass:

```text
field reads = 4 x row_count
required descriptor/packed-weight/scale fields = 3 x row_count
optional aux fields may be present but are not required for the no-payload gate
```

The stricter per-column field-read contract was also validated with a
lower-memory concurrent-use configuration:

```text
config:
  configs/trace/
    router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit_mem70.yaml

model config:
  configs/model/qwen3_6_35b_a3b_awq_4bit_mem70.yaml

vLLM gpu_memory_utilization = 0.70

artifact:
  data/traces/
    external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit_mem70/
    longrun_audit_gate.json

passed = true
failures = []
premap_address_resident_count_max = 10,127
premap_address_reuse_rate_mean = 0.9827389896686539
premap_address_eviction_pressure_mean = 0.0

prep_execution_dry_run_row_count = 110,898
prep_execution_dry_run_handle_field_read_count = 443,592
prep_execution_dry_run_descriptor_ptr_field_read_count = 110,898
prep_execution_dry_run_packed_weight_descriptor_field_read_count = 110,898
prep_execution_dry_run_scale_metadata_handle_field_read_count = 110,898
prep_execution_dry_run_aux_metadata_handle_field_read_count = 110,898
prep_execution_dry_run_descriptor_ptr_field_available_count = 110,898
prep_execution_dry_run_packed_weight_descriptor_field_available_count = 110,898
prep_execution_dry_run_scale_metadata_handle_field_available_count = 110,898
prep_execution_dry_run_aux_metadata_handle_field_available_count = 110,898
prep_execution_dry_run_payload_bytes = 0
prep_execution_dry_run_passed_to_kernel_count = 0
```

Boundary remains unchanged:

```text
no payload transfer
no ready credit
no router mutation
no descriptor_order execution
no kernel argument mutation
```

## Online native typed-consumer canary artifact check

The online prelaunch native-stub canary runner now performs its own final
artifact consistency check after writing the runner, full preflight, and compact
status artifacts.  This makes the canary self-contained: every successful run
must prove that the three artifacts agree on the final lab gate evidence.

Current refreshed runner:

```text
artifact:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_runner.json

artifact_check:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check.json

passed = true
failures = []
stage1_deferred_count = 1
final_deferred_count = 0
status_deferred_count = 0
runner_stub_row_count = 204
runner_stub_row_ok_count = 204
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

The runner still uses the two-stage preflight contract:

```text
stage 1 before runner evidence exists:
  required evidence = 8 / 9
  deferred online-prelaunch-runner evidence = 1

final stage after runner evidence exists:
  required evidence = 9 / 9
  deferred evidence = 0
```

This keeps the online native typed-consumer bridge as a lab-gate artifact, not a
loose side report.  The path remains a no-op bridge only: the native checker reads
the typed table and validates row/schema/lifetime visibility, but no payload is
moved and no WNA16 kernel argument is passed or mutated.

Validation:

```bash
env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests/test_run_premap_online_native_stub_canary.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py -q
# 9 passed

env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
# 668 passed, 2 warnings
```

Failure handling was also hardened: if the artifact consistency checker returns
nonzero, the runner now records `artifact_consistency_check_failed` and writes
the checker summary instead of aborting before the final report can be saved.

## Single-field typed handle handoff canary

Added a readonly single-field handoff canary for the safest future handoff
field:

```text
field = scale_metadata_handle
source = semantic_handle_table
mode = readonly_single_field_handle_handoff_canary
```

This is not a live WNA16 argument replacement.  It validates that the prepared
typed table and semantic handle adapter agree on the scale metadata handle
column, then records a blocked/live-disabled canary:

```text
live_enabled = false
blocked = true
block_reason = single_field_handoff_live_disabled
payload_bytes = 0
ready_credit = false
passed_to_kernel = false
changes_kernel_launch_args = false
live_compatible_with_current_wna16_args = false
```

The long-run checker now has an explicit requirement:

```bash
--require-single-field-handle-handoff-canary
```

and verifies row count, nonzero handle count, field-hash parity against the
semantic adapter, zero payload/ready/kernel-arg side effects, and current-WNA16
incompatibility.

Validation:

```bash
env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  pytest tests/test_runtime_premap.py \
         tests/test_runtime_shadow_log.py \
         tests/test_check_premap_longrun_audit_gate.py \
         tests/test_premap_typed_consumer_stub.py \
         tests/test_premap_kernel_consumer_schema.py -q
# 142 passed
```

Native typed consumer check on GPU1:

```text
synthetic typed table:
  row_count = 4096
  row_ok_count = 4096
  error_count = 0
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false

online prelaunch typed input:
  input_json = data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary/premap_native_typed_consumer_inputs/premap_native_typed_consumer_input_0000_sample_0_seq0_tok-1_layer0.json
  row_count = 204
  row_ok_count = 204
  error_count = 0
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
```

This keeps the next handoff step honest: the current WNA16 kernel still does not
consume the typed table, but a separate native consumer can read the future
kernel-side handle schema without payload movement or kernel-argument mutation.

Online vLLM smoke:

```bash
env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  python scripts/trace_router_mtp_vllm.py \
    configs/trace/router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary.yaml

env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  python scripts/check_premap_longrun_audit_gate.py \
    data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary/performance_summary.json \
    --max-capacity 12288 \
    --min-reuse-rate 0.0 \
    --require-readonly-consumer \
    --require-descriptor-prep \
    --require-real-descriptor-prep \
    --require-kernel-arg-shadow-table \
    --require-consumer-shim-table-read \
    --require-consumer-shim-table-consume \
    --require-consumer-shim-table-object \
    --require-consumer-shim-prep-execution \
    --require-kernel-arg-handoff-attempt \
    --require-kernel-arg-handoff-live-toggle \
    --require-kernel-arg-handoff-launch-schema-mirror \
    --require-kernel-arg-handoff-live-noop-integration \
    --require-kernel-arg-handoff-live-consumer-adapter \
    --require-kernel-arg-semantic-handle-adapter \
    --require-single-field-handle-handoff-canary \
    --require-kernel-side-consumer-schema-adapter \
    --require-kernel-side-typed-consumer-object \
    --require-native-typed-consumer-bridge \
    --require-native-stub-online-invocation-canary \
    --allow-enabled-blocked-live-toggle \
    --allow-connected-blocked-consumer-adapter \
    --output-json \
    data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary/single_field_canary_gate_check.json
```

Result:

```text
single_field_canary_gate_check.passed = true
failures = []
checked_count = 640
ready_count = 640
row_count = 9,794
field_handle_nonzero_count = 9,794
parity_ok_count = 9,794
live_enabled_count = 0
blocked_count = 640
passed_to_kernel_count = 0
kernel_arg_violation_count = 0
live_compatible_with_current_wna16_args_count = 0
```

The smoke uses `--min-reuse-rate 0.0` intentionally because it is a 1-sample
canary; the strict long-run reuse threshold remains a separate 128/512 gate.

## Online native typed-consumer canary under the single-field gate

The online native typed-consumer bridge was refreshed after the single-field
canary became a default lab requirement.  The vLLM/AWQ prelaunch trace exports a
prepared typed table, the native HIP stub reads it, and final lab preflight
closes with all required evidence present.  This remains a no-op bridge only:
no payload is moved, no ready credit is granted, and no WNA16 kernel argument is
passed or mutated.

Evidence:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_runner_single_field_gate.json
  typed_consumer_stub_gpu1_online_prelaunch_input_canary_single_field_gate.json
  online_prelaunch_native_stub_canary_artifact_check_single_field_gate.json

outputs/reports/
  premap_lab_preflight_online_prelaunch_native_stub_canary_single_field_gate.json
  premap_lab_preflight_status_online_prelaunch_native_stub_canary_single_field_gate.json
```

Key checks:

```text
native stub row_count = 204
native stub row_ok_count = 204
native stub error_count = 0
native stub payload_bytes = 0
native stub passed_to_kernel = false
final preflight required evidence = 10 / 10
artifact check passed = true
stage1 deferred runner evidence = 1
final deferred evidence = 0
```

The artifact checker now derives required-evidence counts from the final gate
status instead of hard-coding the previous 9-evidence contract.  Stage1
preflight may intentionally defer the online runner evidence; final preflight
and status must still be fully closed.

## Prepared-table single-field replacement dry-run canary refreshed

The next handoff layer was rerun as a protected negative canary.  The trace uses
the prepared handle table as a candidate source for a single `B_scale`
replacement dry-run, but live replacement remains disabled.  This validates that
the prepared table can be resolved as a semantic source while confirming that it
is not type-compatible with the current WNA16 kernel argument slot.

Evidence:

```text
data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_single_field_replacement_prepared_table_candidate_dry_run_canary/
  prepared_table_candidate_dry_run_gate_check.json
  prepared_table_candidate_dry_run_gate_check_without_allow.json
```

Result:

```text
with explicit allow:
  passed = true
  dry_run_candidate_count = 1280
  prepared_table_candidate_count = 1280
  prepared_table_hit_count = 1280
  prepared_table_miss_count = 0
  prepared_table_type_compatible_count = 0
  prepared_table_type_mismatch_count = 1280
  dry_run_parity_ok_count = 0
  dry_run_parity_mismatch_count = 1280
  live_disabled_count = 1280
  live_passed_to_kernel_count = 0
  dry_run_payload_bytes = 0

without explicit allow:
  passed = false
  failure = single_field_replacement_prepared_table_candidate_source_requires_explicit_allow
```

This keeps the boundary explicit: prepared handle tables are valid typed
semantic objects, but they cannot be used as current WNA16 tensor kernel
arguments.  Real field replacement still requires a kernel-side typed consumer
ABI rather than tuple/tensor impersonation.

## Native typed-consumer per-field macro ladder

The native HIP typed-consumer stub now supports one-field-at-a-time handle
visibility checks in addition to the existing coarse pointer-visibility check:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR
MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR
MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE
MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE
```

The existing forbidden macros remain forbidden in the lab default gate:

```text
MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF
MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS
```

Validation:

```text
typed_consumer_stub_per_field_macro_dry_run.json:
  requested_macros =
    CHECK_DESCRIPTOR_PTR
    CHECK_SCALE_METADATA_HANDLE

typed_consumer_stub_gpu1_online_prelaunch_input_per_field_canary.json:
  row_count = 204
  row_ok_count = 204
  error_count = 0
  CHECK_DESCRIPTOR_PTR = true
  CHECK_PACKED_WEIGHT_DESCRIPTOR = true
  CHECK_SCALE_METADATA_HANDLE = true
  CHECK_AUX_METADATA_HANDLE = true
  payload_bytes = 0
  passed_to_kernel = false
```

This lets future canaries open descriptor, packed-weight, scale, or aux handle
checks independently instead of enabling all source-level checks at once.

The per-field online prelaunch canary is now wired as optional lab preflight
evidence rather than as a new hard gate.  The default gate still requires
10 / 10 core evidence artifacts, while the per-field artifact is validated when
present under `optional_evidence_paths`:

```text
optional_evidence_paths:
  native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json
```

Validation:

```text
outputs/reports/premap_lab_preflight_default_optional_per_field_canary.json:
  passed = true
  required_evidence = 10 / 10
  optional_evidence = 1 / 1
  native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json.passed = true
```

This keeps the lab default honest: per-field native checking is observable and
schema-checked, but it does not imply payload dereference, kernel argument pass,
or current WNA16 typed-table compatibility.

The online native-stub runner now refreshes both native checker variants:

```text
native_stub:
  CHECK_POINTER_VISIBILITY = true

native_stub_per_field:
  CHECK_DESCRIPTOR_PTR = true
  CHECK_PACKED_WEIGHT_DESCRIPTOR = true
  CHECK_SCALE_METADATA_HANDLE = true
  CHECK_AUX_METADATA_HANDLE = true
  CHECK_POINTER_VISIBILITY = false
```

Refresh command:

```bash
env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
  HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  conda run -p /home/husrcf/anaconda3/envs/TRY \
  python scripts/run_premap_online_native_stub_canary.py \
    --gpu-index 1 \
    --stub-device 0 \
    --skip-trace \
    --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_single_field_gate.json \
    --stub-output-json outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_online_prelaunch_input_canary_single_field_gate.json \
    --per-field-stub-output-json outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_online_prelaunch_input_per_field_canary.json \
    --preflight-output-json outputs/reports/premap_lab_preflight_online_prelaunch_native_stub_canary_single_field_gate.json \
    --preflight-status-output-json outputs/reports/premap_lab_preflight_status_online_prelaunch_native_stub_canary_single_field_gate.json \
    --artifact-check-output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_single_field_gate.json
```

Result:

```text
passed = true
stub_summary.row_count = 204
stub_summary.row_ok_count = 204
per_field_stub_summary.row_count = 204
per_field_stub_summary.row_ok_count = 204
per_field_stub_summary.payload_bytes = 0
per_field_stub_summary.passed_to_kernel = false
final_preflight_status.required_evidence = 10 / 10
final_preflight_status.optional_evidence = 1 / 1
artifact_check.passed = true
```

The online canary artifact checker now also validates `per_field_stub_summary`
when the runner emits it.  The refreshed checker confirms both native consumer
variants against the same online prelaunch input:

```text
online_prelaunch_native_stub_canary_artifact_check_single_field_gate.json:
  passed = true
  runner_stub_row_count = 204
  runner_stub_row_ok_count = 204
  runner_per_field_stub_row_count = 204
  runner_per_field_stub_row_ok_count = 204
```

## Kernel-side typed consumer ABI header

The native typed-consumer canary now uses an explicit kernel-side ABI header
instead of a stub-local table struct:

```text
microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h

struct PremapKernelSideTypedConsumerAbiV1:
  descriptor_ptr
  packed_weight_descriptor
  scale_metadata_handle
  aux_metadata_handle
  expert_id
  address_key_hash
  row_order_hash / ordered_row_hash
  lifetime_epoch
```

The HIP canary consumes `PremapKernelSideTypedConsumerAbiV1` directly and emits
ABI metadata in its JSON result:

```text
abi_name = premap_kernel_side_typed_consumer_abi_v1
abi_handle_column_count = 4
abi_payload_bytes_allowed = false
abi_kernel_arg_pass_allowed = false
```

The machine-readable schema now also records and checks the ABI binding:

```text
native_consumer_abi.abi_name = premap_kernel_side_typed_consumer_abi_v1
native_consumer_abi.cpp_header = microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h
native_consumer_abi.cpp_struct = PremapKernelSideTypedConsumerAbiV1
native_consumer_abi.handle_column_count = 4
native_consumer_abi.payload_bytes_allowed = false
native_consumer_abi.kernel_arg_pass_allowed = false
```

Validation on the online prelaunch input:

```text
typed_consumer_stub_gpu1_online_prelaunch_input_abi_header_per_field_canary.json:
  row_count = 204
  row_ok_count = 204
  error_count = 0
  CHECK_DESCRIPTOR_PTR = true
  CHECK_PACKED_WEIGHT_DESCRIPTOR = true
  CHECK_SCALE_METADATA_HANDLE = true
  CHECK_AUX_METADATA_HANDLE = true
  payload_bytes = 0
  passed_to_kernel = false
```

The per-field optional preflight evidence now requires this ABI metadata when
present, so a stale stub-local artifact cannot silently satisfy the per-field
canary.  This still does not authorize current WNA16 kernel-arg mutation; it
only proves that a native consumer can read the future typed ABI.

Refreshed default lab gate after regenerating the optional per-field artifact:

```text
online_prelaunch_native_stub_canary_runner_single_field_gate.json:
  passed = true
  stub_summary.row_count = 204
  stub_summary.row_ok_count = 204
  per_field_stub_summary.row_count = 204
  per_field_stub_summary.row_ok_count = 204
  per_field_stub_summary.payload_bytes = 0
  per_field_stub_summary.passed_to_kernel = false

premap_lab_preflight_default_typed_consumer_abi_header.json:
  passed = true
  required_evidence = 10 / 10
  optional_evidence = 1 / 1
  default_kernel_consumer_schema_passed = true
  payload_bytes_required = 0
  passed_to_kernel_required = false
  changes_kernel_launch_args_required = false
```

After adding the schema-level ABI binding check:

```text
premap_lab_preflight_default_typed_consumer_abi_schema.yaml.json:
  passed = true
  default_kernel_consumer_schema_passed = true
  required_evidence = 10 / 10
  optional_evidence = 1 / 1
  payload_bytes_required = 0
  passed_to_kernel_required = false
  changes_kernel_launch_args_required = false
```

## Kernel-side typed consumer adapter

The ABI path now has an explicit native row-view adapter:

```text
microbench/premap_kernel_consumer/premap_typed_consumer_adapter_v1.h

PremapKernelSideTypedConsumerRowV1:
  descriptor_ptr
  packed_weight_descriptor
  scale_metadata_handle
  aux_metadata_handle
  expert_id
  address_key_hash
  row_index

adapter_name = premap_kernel_side_typed_consumer_adapter_v1
adapter_payload_deref_allowed = false
adapter_kernel_arg_pass_allowed = false
```

`premap_typed_consumer_stub.hip` now consumes the table through this adapter
instead of directly spreading table field reads through the kernel body.  This
is the intended compatibility point for a future kernel-side consumer: the
current WNA16 kernel argument list remains unchanged and unsupported for typed
table handoff.

GPU1 online prelaunch validation after switching the stub to the adapter:

```text
online_prelaunch_native_stub_canary_runner_single_field_gate.json:
  passed = true
  stub_summary.row_count = 204
  stub_summary.row_ok_count = 204
  per_field_stub_summary.row_count = 204
  per_field_stub_summary.row_ok_count = 204
  per_field_stub_summary.payload_bytes = 0
  per_field_stub_summary.passed_to_kernel = false

premap_lab_preflight_default_typed_consumer_adapter.json:
  passed = true
  default_kernel_consumer_schema_passed = true
  required_evidence = 10 / 10
  optional_evidence = 1 / 1
  payload_bytes_required = 0
  passed_to_kernel_required = false
  changes_kernel_launch_args_required = false
```

## Kernel-side consumer launch-envelope canary

The typed consumer adapter now includes a disabled-by-default launch envelope
for a future kernel-side consumer:

```text
PremapKernelSideTypedConsumerLaunchEnvelopeV1:
  table
  expected_schema_hash_hi / expected_schema_hash_lo
  expected_row_order_hash / expected_ordered_row_hash
  expected_row_count / expected_column_count
  payload_bytes
  flags

launch_envelope_name = premap_kernel_side_typed_consumer_launch_envelope_v1
launch_envelope_default_enabled = false
launch_envelope_payload_bytes_required = 0
launch_envelope_passed_to_kernel_required = false
```

The envelope is only exercised when the native canary is compiled with:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE
```

This still does not pass anything to the current WNA16 fused-MoE kernel.  It
only validates the shape of the future kernel-side consumer handoff envelope.

GPU1 online-prelaunch validation:

```text
typed_consumer_stub_gpu1_online_prelaunch_input_kernel_envelope_canary.json:
  passed = true
  row_count = 204
  row_ok_count = 204
  error_count = 0
  kernel_consumer_envelope_checked = true
  kernel_consumer_envelope_payload_bytes = 0
  kernel_consumer_envelope_passed_to_kernel = false
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false

premap_lab_preflight_default_kernel_envelope_schema.json:
  passed = true
  default_kernel_consumer_schema_passed = true
  required_evidence = 10 / 10
  optional_evidence = 1 / 1
  payload_bytes_required = 0
  passed_to_kernel_required = false
  changes_kernel_launch_args_required = false
```

## Scale-metadata single-field ABI row mirror canary

The native typed consumer stub now has an explicit one-field mirror check for
the safest handoff candidate:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD
```

This macro loads `scale_metadata_handle` through
`PremapKernelSideTypedConsumerRowV1` and compares the row-view value with the
same row in the ABI table column.  It validates the future kernel-side row-read
path for the scale metadata mirror without changing the current WNA16 kernel
argument list:

```text
single_field_mirror_mode = readonly_scale_metadata_handle_abi_row_mirror
single_field_mirror_field_name = scale_metadata_handle
single_field_mirror_source = typed_consumer_abi_row_adapter_v1
single_field_mirror_payload_bytes = 0
single_field_mirror_passed_to_kernel = false
single_field_mirror_changes_kernel_launch_args = false
single_field_mirror_current_wna16_arg_compatible = false
```

GPU1 canary validation:

```text
typed_consumer_stub_gpu1_scale_metadata_mirror_canary.json:
  passed = true
  row_count = 64
  row_ok_count = 64
  single_field_mirror_checked = true
  single_field_mirror_row_ok_count = 64
  single_field_mirror_error_count = 0
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false

online_prelaunch_native_stub_canary_runner.json:
  passed = true
  per_field_stub_summary.row_count = 204
  per_field_stub_summary.row_ok_count = 204
  final_preflight_status_summary.optional_evidence = 1 / 1
  final_preflight_status_summary.required_evidence = 10 / 10
```

This remains a readonly native-stub canary.  It proves the typed ABI row adapter
can read the scale metadata mirror, but it still does not pass typed handles to
the real AWQ WNA16 fused-MoE kernel.

## Launch-envelope mirror and second-field canary

The scale-metadata mirror canary is now also exercised through the future
kernel-side launch envelope:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE
MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD
```

This path constructs `PremapKernelSideTypedConsumerLaunchEnvelopeV1`, then the
native stub loads the typed table through `PremapKernelSideTypedConsumerRowV1`
inside the envelope kernel.  It remains a readonly native-stub check:

```text
kernel_consumer_envelope_checked = true
kernel_consumer_envelope_payload_bytes = 0
kernel_consumer_envelope_passed_to_kernel = false
single_field_mirror_mode = readonly_scale_metadata_handle_abi_row_mirror
single_field_mirror_source = typed_consumer_abi_row_adapter_v1
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

GPU1 validation:

```text
typed_consumer_stub_gpu1_kernel_envelope_scale_metadata_mirror_canary.json:
  passed = true
  row_count = 64
  row_ok_count = 64
  kernel_consumer_envelope_checked = true
  single_field_mirror_checked = true
  single_field_mirror_row_ok_count = 64

online_prelaunch_native_stub_canary_runner.json:
  passed = true
  kernel_envelope_mirror_stub_summary.row_count = 204
  kernel_envelope_mirror_stub_summary.row_ok_count = 204
  kernel_envelope_mirror_stub_summary.kernel_consumer_envelope_checked = true
  kernel_envelope_mirror_stub_summary.single_field_mirror_checked = true
```

The stub also now supports a second disabled-by-default one-field mirror macro:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD
```

Only one mirror macro may be enabled per stub build.  The packed-weight mirror
canary is available for the next field-by-field handoff gate but is not part of
the default lab precondition yet.

GPU1 synthetic packed-weight validation:

```text
typed_consumer_stub_gpu1_packed_weight_mirror_canary.json:
  passed = true
  row_count = 64
  row_ok_count = 64
  single_field_mirror_mode = readonly_packed_weight_descriptor_abi_row_mirror
  single_field_mirror_field_name = packed_weight_descriptor
  single_field_mirror_row_ok_count = 64
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
```

## Online packed-weight mirror canary

The packed-weight mirror field is now also exercised on the online vLLM/AWQ
prelaunch typed-consumer input exported by the native-stub canary runner.  This
uses a separate native stub invocation:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA
MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION
MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD
MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR
```

GPU1 validation:

```text
online_prelaunch_native_stub_canary_runner.json:
  passed = true
  packed_weight_mirror_stub_summary.row_count = 204
  packed_weight_mirror_stub_summary.row_ok_count = 204
  packed_weight_mirror_stub_summary.single_field_mirror_checked = true
  packed_weight_mirror_stub_summary.single_field_mirror_field_name = packed_weight_descriptor
  packed_weight_mirror_stub_summary.single_field_mirror_row_ok_count = 204
  packed_weight_mirror_stub_summary.payload_bytes = 0
  packed_weight_mirror_stub_summary.passed_to_kernel = false
  packed_weight_mirror_stub_summary.changes_kernel_launch_args = false
```

This keeps the same safety boundary as the scale-metadata mirror canary.  It
proves that the future kernel-side typed consumer ABI can read the online
`packed_weight_descriptor` row field through the row adapter, but it still does
not mutate current WNA16 kernel arguments or dereference payload.

## Online aux-metadata mirror canary

The native typed-consumer stub now supports a third one-field mirror macro:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD
```

This checks the optional `aux_metadata_handle` column through the same
`PremapKernelSideTypedConsumerRowV1` row adapter when the online prepared table
exports an aux column.  Only one mirror macro remains legal per stub build, so
scale, packed-weight, and aux mirrors stay attributable to separate canaries.

GPU1 validation on the online vLLM/AWQ prelaunch input:

```text
online_prelaunch_native_stub_canary_runner.json:
  passed = true
  aux_metadata_mirror_stub_summary.row_count = 204
  aux_metadata_mirror_stub_summary.row_ok_count = 204
  aux_metadata_mirror_stub_summary.single_field_mirror_checked = true
  aux_metadata_mirror_stub_summary.single_field_mirror_field_name = aux_metadata_handle
  aux_metadata_mirror_stub_summary.single_field_mirror_row_ok_count = 204
  aux_metadata_mirror_stub_summary.payload_bytes = 0
  aux_metadata_mirror_stub_summary.passed_to_kernel = false
  aux_metadata_mirror_stub_summary.changes_kernel_launch_args = false
```

This is still a readonly typed-consumer ABI canary.  It expands field coverage
for the future kernel-side schema but does not enable payload access, ready
credit, or current WNA16 kernel-argument mutation.

## Online descriptor pointer mirror canary

The native typed-consumer stub now covers the fourth handle column with:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD
```

This mirror compares the `descriptor_ptr` address value loaded through
`PremapKernelSideTypedConsumerRowV1` against the ABI table column for the same
row.  It does not dereference the descriptor pointer and still reports
`payload_bytes=0`, `passed_to_kernel=false`, and
`changes_kernel_launch_args=false`.

GPU1 validation on the online vLLM/AWQ prelaunch input:

```text
online_prelaunch_native_stub_canary_runner.json:
  passed = true
  descriptor_ptr_mirror_stub_summary.row_count = 204
  descriptor_ptr_mirror_stub_summary.row_ok_count = 204
  descriptor_ptr_mirror_stub_summary.single_field_mirror_checked = true
  descriptor_ptr_mirror_stub_summary.single_field_mirror_field_name = descriptor_ptr
  descriptor_ptr_mirror_stub_summary.single_field_mirror_row_ok_count = 204
  descriptor_ptr_mirror_stub_summary.payload_bytes = 0
  descriptor_ptr_mirror_stub_summary.passed_to_kernel = false
  descriptor_ptr_mirror_stub_summary.changes_kernel_launch_args = false
```

At this point all four typed handle columns have independent readonly native
mirror canaries:

```text
descriptor_ptr
packed_weight_descriptor
scale_metadata_handle
aux_metadata_handle
```

This completes ABI row-adapter field coverage for the no-op native bridge.  It
is still not a live WNA16 kernel-argument handoff.

## Strict 128-sample field-mirror lab gate

The field-level canaries are now part of the default lab preflight path rather
than only single-input online smokes.

Implementation updates:

```text
run_premap_online_native_stub_canary.py:
  - supports --max-online-inputs
  - runs the native stub suite over multiple exported online prelaunch tables
  - records per-input pass/failure summaries

check_premap_online_native_stub_canary_artifacts.py:
  - requires all field mirror stubs when requested
  - supports --min-online-inputs
  - validates descriptor_ptr / packed_weight / scale_metadata / aux_metadata
    mirror row counts and no-op safety fields

run_premap_lab_preflight.py:
  - directly validates the runner multi-input and field-mirror evidence
  - does not require artifact_check_summary, avoiding a runner/preflight
    artifact-check cycle
  - requires all field mirror stubs
  - requires min_online_inputs >= 16 for the online prelaunch runner evidence
```

The 128-sample AWQ/vLLM audit now exports online typed-consumer inputs with
stride sampling:

```text
config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70.yaml

output:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70_stride320

export_count = 16
export_stride = 320
unique_samples = [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60]
unique_layers = [0]
```

Strict native field-mirror runner:

```text
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_dolly128_stride320_field_gate.json:
  passed = true
  online_prelaunch_input_check_count = 16
  online_prelaunch_input_extra_check_passed_count = 15

artifact_check_summary:
  passed = true
  require_all_field_mirror_stubs = true
  min_online_inputs = 16
  runner_descriptor_ptr_mirror_stub_row_count = 174
  runner_descriptor_ptr_mirror_stub_row_ok_count = 174
  runner_packed_weight_mirror_stub_row_count = 174
  runner_packed_weight_mirror_stub_row_ok_count = 174
  runner_kernel_envelope_mirror_stub_row_count = 174
  runner_kernel_envelope_mirror_stub_row_ok_count = 174
  runner_aux_metadata_mirror_stub_row_count = 174
  runner_aux_metadata_mirror_stub_row_ok_count = 174
```

The default readonly lab gate now points to this 128-sample stride artifact.
Preflight status:

```text
outputs/reports/premap_lab_preflight_status_strict_field_mirror_128_stride320.json:
  passed = true
  required_evidence = 10 / 10
  optional_evidence = 1 / 1
  runtime_gate_evidence_deferred_count = 0
  strict_default_gate_evidence_deferred_count = 0
```

Safety boundary remains unchanged:

```text
payload_bytes = 0
ready_credit = false
passed_to_kernel = false
changes_kernel_launch_args = false
```

This promotes the typed handle field coverage from single online input evidence
to a stricter long-run lab preflight gate.  The next step is a kernel-side
compatible consumer path that reads this typed schema directly, still without
pretending the typed table is a current WNA16 kernel argument.

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
  690 passed, 2 warnings
```

## Kernel-side typed row consumer path canary

The native premap consumer now has an explicit kernel-side compatible row
consumer path, still separate from the current WNA16 fused-MoE kernel argument
list.

Implementation updates:

```text
premap_typed_consumer_adapter_v1.h:
  - adds PremapKernelSideTypedConsumerPathResultV1
  - adds premap_typed_consumer_kernel_side_consume_row_v1(...)
  - consumes a typed ABI row through the future kernel-side row adapter

premap_typed_consumer_stub.hip:
  - adds MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH
  - records kernel_side_consumer_path_* fields
  - keeps payload_bytes=0 and passed_to_kernel=false

run_premap_online_native_stub_canary.py:
  - base native stub now enables the kernel-side consumer path macro
  - compact runner summaries preserve kernel_side_consumer_path_* evidence

check_premap_online_native_stub_canary_artifacts.py and
run_premap_lab_preflight.py:
  - require the base native stub to pass kernel_side_consumer_path_checked
  - require row_ok_count == row_count for the typed row consumer path
```

GPU1 online prelaunch canary:

```text
outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_online_prelaunch_input_dolly128_stride320_kernel_side_path_canary.json:
  passed = true
  kernel_side_consumer_path_checked = true
  kernel_side_consumer_path_name = premap_kernel_side_typed_consumer_path_v1
  kernel_side_consumer_path_row_count = 174
  kernel_side_consumer_path_row_ok_count = 174
  kernel_side_consumer_path_payload_bytes = 0
  kernel_side_consumer_path_passed_to_kernel = false
  kernel_side_consumer_path_changes_kernel_launch_args = false
  kernel_side_consumer_path_current_wna16_arg_compatible = false
```

The 16-input strict runner was refreshed with this path enabled:

```text
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_dolly128_stride320_field_gate.json:
  passed = true
  online_prelaunch_input_check_count = 16
  online_prelaunch_input_extra_check_passed_count = 15
  stub_summary.kernel_side_consumer_path_checked = true
  stub_summary.kernel_side_consumer_path_row_ok_count = 174

artifact_check_summary:
  passed = true
  runner_online_prelaunch_input_check_count = 16
```

This moves the native bridge one step beyond field-level mirrors: the stub now
executes a named typed row consumer path that a future kernel-side implementation
can adopt.  It still does not pass any argument to the real WNA16 kernel and
does not dereference payload.

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
  691 passed, 2 warnings
```

## Typed row path strict gate and second field canary

The kernel-side typed row consumer path is now part of the default lab
preflight contract instead of only a native stub canary.  The 128-sample AWQ
strict audit must now provide a typed-row consumer-path evidence artifact before
the readonly premap gate is considered lab-ready.

Implementation updates:

```text
check_premap_longrun_audit_gate.py:
  - adds --require-kernel-side-typed-row-consumer-path
  - validates typed row mode/name/source/schema hash
  - requires row_ok_count == row_count
  - requires payload_bytes=0, passed_to_kernel=0, kernel_arg_violation_count=0

run_premap_lab_preflight.py:
  - requires strict_kernel_side_typed_row_consumer_path_128_gate_json
  - validates typed-row consumer path metrics as a default gate prerequisite

runtime/cache_manager.py and vllm_router_trace.py:
  - parameterize one-field handoff canary field selection
  - support scale_metadata_handle and packed_weight_descriptor
```

128-sample strict audit:

```text
data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit/
  runtime_shadow.jsonl = 536M
  performance_summary.json refreshed
  longrun_audit_gate_typed_row_consumer_path_128.json generated

typed row path:
  checked_count > 0
  ready_count == checked_count
  row_ok_count == row_count
  column_count min/max = 4
  payload_bytes = 0
  passed_to_kernel_count = 0
  kernel_arg_violation_count = 0
  current_wna16_arg_compatible_count = 0
```

Second one-field canary:

```text
configs/trace/router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_packed_weight_handle_handoff_canary.yaml

field_name = packed_weight_descriptor
mirror_mode = readonly_packed_weight_descriptor_mirror
checked_count = 640
ready_count = 640
parity_ok_count = 9794
payload_bytes = 0
passed_to_kernel_count = 0
kernel_arg_violation_count = 0
```

Lab preflight now passes with the typed-row strict evidence included:

```text
outputs/reports/premap_lab_preflight_latest.json
  failures = []
  kernel_side_typed_row_consumer_path_required = true
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest \
  tests/test_check_premap_longrun_audit_gate.py \
  tests/test_run_premap_lab_preflight.py \
  tests/test_runtime_premap.py -q
  151 passed

conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
  695 passed, 2 warnings
```

The next gate remains conservative: keep payload, ready credit, and real WNA16
kernel args disabled while moving from typed-row evidence toward a native
kernel-side compatible consumer path.

## Packed-weight field canary as optional lab evidence

The second one-field handoff canary is now wired into the default lab preflight
as optional evidence.  It does not block the default readonly gate when absent,
but when the artifact exists the preflight validates that the runtime shadow
canary is specifically for `packed_weight_descriptor` and still keeps all live
handoff effects disabled.

Default gate update:

```text
optional_evidence_paths:
  packed_weight_single_field_handle_handoff_canary_smoke_json:
    data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_packed_weight_handle_handoff_canary/longrun_audit_gate_packed_weight_single_field_smoke.json
```

Real lab preflight:

```text
outputs/reports/premap_lab_preflight_latest.json
  failures = []
  optional_evidence.required_count = 2
  optional_evidence.present_count = 2
  optional_evidence.passed_count = 2

packed_weight_single_field_handle_handoff_canary_smoke_json:
  present = true
  passed = true
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest \
  tests/test_run_premap_lab_preflight.py \
  tests/test_check_premap_longrun_audit_gate.py -q
  130 passed

conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
  696 passed, 2 warnings
```

## Aux metadata one-field canary

The readonly one-field canary allowlist now also covers
`aux_metadata_handle`.  This is still a metadata-only mirror path: payload,
ready credit, and kernel argument pass remain disabled.

GPU1 1-sample smoke:

```text
configs/trace/router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_aux_metadata_handle_handoff_canary.yaml

field_name = aux_metadata_handle
checked_count = 640
ready_count = 640
parity_ok_count = 9794
payload_bytes = 0
passed_to_kernel_count = 0
kernel_arg_violation_count = 0

data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_aux_metadata_handle_handoff_canary/
  longrun_audit_gate_aux_metadata_single_field_smoke.json
```

Lab preflight optional evidence now validates three optional artifacts:

```text
outputs/reports/premap_lab_preflight_latest.json
  failures = []
  optional_evidence.required_count = 3
  optional_evidence.present_count = 3
  optional_evidence.passed_count = 3

optional evidence:
  native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json
  packed_weight_single_field_handle_handoff_canary_smoke_json
  aux_metadata_single_field_handle_handoff_canary_smoke_json
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest \
  tests/test_run_premap_lab_preflight.py \
  tests/test_check_premap_longrun_audit_gate.py \
  tests/test_runtime_premap.py -q
  153 passed

conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
  697 passed, 2 warnings
```

## Descriptor pointer readonly canary

The readonly one-field canary matrix now covers all four typed handle table
columns:

```text
descriptor_ptr
packed_weight_descriptor
scale_metadata_handle
aux_metadata_handle
```

The `descriptor_ptr` canary remains a mirror/parity check only.  It does not
dereference the pointer, pass it to the real WNA16 kernel, move payload, or
grant ready credit.

GPU1 1-sample smoke:

```text
configs/trace/router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_descriptor_ptr_handle_handoff_canary.yaml

field_name = descriptor_ptr
checked_count = 640
ready_count = 640
parity_ok_count = 9794
payload_bytes = 0
passed_to_kernel_count = 0
kernel_arg_violation_count = 0

data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_descriptor_ptr_handle_handoff_canary/
  longrun_audit_gate_descriptor_ptr_single_field_smoke.json
```

Lab preflight optional evidence now validates four optional artifacts:

```text
outputs/reports/premap_lab_preflight_latest.json
  failures = []
  optional_evidence.required_count = 4
  optional_evidence.present_count = 4
  optional_evidence.passed_count = 4

optional evidence:
  native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json
  packed_weight_single_field_handle_handoff_canary_smoke_json
  aux_metadata_single_field_handle_handoff_canary_smoke_json
  descriptor_ptr_single_field_handle_handoff_canary_smoke_json
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest \
  tests/test_run_premap_lab_preflight.py \
  tests/test_check_premap_longrun_audit_gate.py \
  tests/test_runtime_premap.py -q
  154 passed

conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
  698 passed, 2 warnings
```

## Native online prelaunch field mirror refresh

The native typed-consumer runner was refreshed using the 128-sample exported
online prelaunch inputs, without rerunning vLLM (`--skip-trace`).  This verifies
that the native stub side agrees with the readonly runtime field canary matrix.

Runner:

```text
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_dolly128_stride320_field_gate.json

passed = true
failures = []
online_prelaunch_input_check_count = 16
online_prelaunch_input_extra_check_count = 15
online_prelaunch_input_extra_check_passed_count = 15

artifact_check_summary:
  passed = true
  failures = []
  min_online_inputs = 16
  require_all_field_mirror_stubs = true
  runner_stub_row_count = 174
  runner_stub_row_ok_count = 174
  runner_descriptor_ptr_mirror_stub_row_count = 174
  runner_descriptor_ptr_mirror_stub_row_ok_count = 174
  runner_packed_weight_mirror_stub_row_count = 174
  runner_packed_weight_mirror_stub_row_ok_count = 174
  runner_aux_metadata_mirror_stub_row_count = 174
  runner_aux_metadata_mirror_stub_row_ok_count = 174
  runner_kernel_envelope_mirror_stub_row_count = 174
  runner_kernel_envelope_mirror_stub_row_ok_count = 174
```

The first input native stub also still validates the kernel-side typed row path:

```text
kernel_side_consumer_path_checked = true
kernel_side_consumer_path_name = premap_kernel_side_typed_consumer_path_v1
kernel_side_consumer_path_row_count = 174
kernel_side_consumer_path_row_ok_count = 174
kernel_side_consumer_path_payload_bytes = 0
kernel_side_consumer_path_passed_to_kernel = false
kernel_side_consumer_path_changes_kernel_launch_args = false
kernel_side_consumer_path_current_wna16_arg_compatible = false
```

## Kernel-side compatible consumer ABI stub

Added a distinct readonly future-kernel ABI canary instead of attempting to
reinterpret the typed table as the current AWQ WNA16 launch arguments.

New native path:

```text
PremapKernelSideTypedConsumerLaunchEnvelopeV1
  -> premap_typed_consumer_kernel_side_compatible_consume_row_v1(...)
  -> kernel_side_compatible_consumer_* summary fields
```

Contract:

```text
kernel_side_compatible_consumer_name =
  premap_kernel_side_compatible_consumer_abi_v1
kernel_side_compatible_consumer_mode =
  readonly_kernel_side_compatible_consumer_abi
kernel_side_compatible_consumer_source =
  premap_kernel_side_typed_consumer_launch_envelope_v1
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

Standalone native canary on the first 128-sample online prelaunch export:

```text
outputs/reports/premap_kernel_consumer/
  typed_consumer_stub_gpu1_kernel_side_compatible_consumer_abi_canary.json

kernel_side_compatible_consumer_checked = true
kernel_side_compatible_consumer_row_count = 174
kernel_side_compatible_consumer_row_ok_count = 174
kernel_side_compatible_consumer_error_count = 0
```

Online runner refresh over 16 exported prelaunch inputs:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_runner_dolly128_stride320_kernel_side_compatible_abi.json

passed = true
failures = []
online_prelaunch_input_check_count = 16
online_prelaunch_input_extra_check_count = 15
online_prelaunch_input_extra_check_passed_count = 15

artifact_check_summary:
  passed = true
  failures = []
  runner_kernel_side_compatible_stub_row_count = 174
  runner_kernel_side_compatible_stub_row_ok_count = 174
```

Review follow-up:

```text
Codex review found one defensive-safety issue and two evidence-strength issues.
Fixes applied:
  - compatible consumer now returns before row load if the launch envelope is invalid
  - artifact checker now requires kernel_side_compatible_stub_summary when the full native suite is required
  - artifact checker now validates kernel_side_compatible_consumer_source
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY pytest \
  tests/test_check_premap_online_native_stub_canary_artifacts.py \
  tests/test_run_premap_online_native_stub_canary.py \
  tests/test_premap_typed_consumer_stub.py \
  tests/test_run_premap_lab_preflight.py -q
  65 passed

conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
  699 passed, 2 warnings
```

## Future kernel consumer args ABI canary

Added a closer-to-real native ABI canary for the eventual kernel-side
descriptor/address consumer. This is still readonly and live-disabled; it does
not reinterpret the typed table as the current AWQ WNA16 launch args.

New native path:

```text
PremapFutureKernelSideConsumerArgsV1
  wraps PremapKernelSideTypedConsumerLaunchEnvelopeV1
  carries field_mask + single_field_mirror_kind
  -> typed_consumer_future_kernel_args_kernel(...)
  -> future_kernel_consumer_args_* summary fields
```

Contract:

```text
future_kernel_consumer_args_name =
  premap_future_kernel_side_consumer_args_v1
future_kernel_consumer_args_mode =
  readonly_future_kernel_consumer_args
future_kernel_consumer_args_source =
  premap_kernel_side_typed_consumer_launch_envelope_v1
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

Standalone GPU1 canary on the first 128-sample online prelaunch export:

```text
outputs/reports/premap_kernel_consumer/
  typed_consumer_stub_gpu1_future_kernel_args_scale_mirror_canary.json

future_kernel_consumer_args_checked = true
future_kernel_consumer_args_row_count = 174
future_kernel_consumer_args_row_ok_count = 174
future_kernel_consumer_args_error_count = 0
future_kernel_consumer_args_single_field_mirror_checked = true
future_kernel_consumer_args_single_field_mirror_field_name =
  scale_metadata_handle
future_kernel_consumer_args_single_field_mirror_error_count = 0
```

Online runner refresh over 16 exported prelaunch inputs:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_runner_dolly128_stride320_future_kernel_args.json

passed = true
failures = []
online_prelaunch_input_check_count = 16
online_prelaunch_input_extra_check_count = 15
online_prelaunch_input_extra_check_passed_count = 15

artifact_check_summary:
  passed = true
  failures = []
  runner_future_kernel_args_stub_row_count = 174
  runner_future_kernel_args_stub_row_ok_count = 174
```

This moves the typed premap consumer bridge one step closer to a real kernel
ABI: the independent native stub now accepts a future parameter object and
verifies scale-metadata one-field mirror parity through that object. It remains
strictly no-payload and no-kernel-arg-pass.

Follow-up field coverage on the same 128-sample online prelaunch export:

```text
outputs/reports/premap_kernel_consumer/
  typed_consumer_stub_gpu1_future_kernel_args_descriptor_ptr_mirror_canary.json
  typed_consumer_stub_gpu1_future_kernel_args_packed_weight_mirror_canary.json
  typed_consumer_stub_gpu1_future_kernel_args_aux_metadata_mirror_canary.json

all:
  future_kernel_consumer_args_checked = true
  future_kernel_consumer_args_row_count = 174
  future_kernel_consumer_args_row_ok_count = 174
  future_kernel_consumer_args_error_count = 0
  future_kernel_consumer_args_payload_bytes = 0
  future_kernel_consumer_args_passed_to_kernel = false
  future_kernel_consumer_args_changes_kernel_launch_args = false
  future_kernel_consumer_args_current_wna16_arg_compatible = false

single-field mirror fields:
  descriptor_ptr
  packed_weight_descriptor
  aux_metadata_handle
```

The default readonly lab gate now lists these future-args per-field canaries as
optional evidence. The required gate remains conservative and still requires
only the scale-metadata future-args mirror plus the existing all-field row-table
canary matrix.

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY python \
  scripts/run_premap_lab_preflight.py --summary-only \
  --output-json outputs/reports/premap_lab_preflight_status_future_args_field_refresh.json

passed = true
required_evidence = 11 / 11
optional_evidence = 4 / 4

conda run -p /home/husrcf/anaconda3/envs/TRY pytest \
  tests/test_run_premap_lab_preflight.py \
  tests/test_premap_typed_consumer_stub.py -q
  49 passed
```

Automated online runner refresh with all future-args field mirrors enabled:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_runner_future_args_field_refresh.json

passed = true
failures = []

future kernel args field mirrors:
  scale_metadata_handle:
    row_count = 204
    row_ok_count = 204
    error_count = 0
    passed_to_kernel = false
    changes_kernel_launch_args = false
    current_wna16_arg_compatible = false

  descriptor_ptr:
    row_count = 204
    row_ok_count = 204
    error_count = 0
    passed_to_kernel = false
    changes_kernel_launch_args = false
    current_wna16_arg_compatible = false

  packed_weight_descriptor:
    row_count = 204
    row_ok_count = 204
    error_count = 0
    passed_to_kernel = false
    changes_kernel_launch_args = false
    current_wna16_arg_compatible = false

  aux_metadata_handle:
    row_count = 204
    row_ok_count = 204
    error_count = 0
    passed_to_kernel = false
    changes_kernel_launch_args = false
    current_wna16_arg_compatible = false
```

This verifies that the online native-stub runner now exercises the complete
future-kernel-args field mirror matrix automatically, not only through manual
standalone canary commands.  The path remains a future ABI stub: no payload
movement, no live WNA16 kernel argument mutation, and no reinterpretation of the
current WNA16 launch schema.

Validation:

```text
env PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
conda run -p /home/husrcf/anaconda3/envs/TRY python \
  scripts/check_premap_online_native_stub_canary_artifacts.py \
  --runner-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_args_field_refresh.json \
  --preflight-json outputs/reports/premap_lab_preflight_future_args_field_refresh.json \
  --status-json outputs/reports/premap_lab_preflight_status_future_args_field_refresh_runner.json \
  --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_future_args_field_refresh_strict.json \
  --require-all-field-mirror-stubs \
  --min-online-inputs 1

passed = true
failures = []
runner_future_kernel_args_stub_row_ok_count = 204
runner_future_kernel_args_descriptor_ptr_stub_row_ok_count = 204
runner_future_kernel_args_packed_weight_stub_row_ok_count = 204
runner_future_kernel_args_aux_metadata_stub_row_ok_count = 204

PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
conda run -p /home/husrcf/anaconda3/envs/TRY pytest \
  tests/test_run_premap_online_native_stub_canary.py \
  tests/test_check_premap_online_native_stub_canary_artifacts.py \
  tests/test_run_premap_lab_preflight.py \
  tests/test_premap_typed_consumer_stub.py -q
  67 passed

PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
conda run -p /home/husrcf/anaconda3/envs/TRY pytest tests -q
  701 passed, 2 warnings
```

16-input runner refresh on the 128-sample native input export:

```text
env HIP_VISIBLE_DEVICES=1 CUDA_VISIBLE_DEVICES=1 \
  PYTHONPATH=/home/husrcf/Code/ProtBind/MTP:/home/husrcf/Code/ProtBind/MTP/src \
conda run -p /home/husrcf/anaconda3/envs/TRY python \
  scripts/run_premap_online_native_stub_canary.py \
  --skip-trace \
  --trace-config configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70.yaml \
  --max-online-inputs 16 \
  --min-artifact-online-inputs 16 \
  --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_args_field_refresh_16_128export.json \
  --preflight-output-json outputs/reports/premap_lab_preflight_future_args_field_refresh_16_128export.json \
  --preflight-status-output-json outputs/reports/premap_lab_preflight_status_future_args_field_refresh_16_128export_runner.json \
  --artifact-check-output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_future_args_field_refresh_16_128export.json

passed = true
failures = []
online_prelaunch_input_check_count = 16
online_prelaunch_input_extra_check_count = 15
online_prelaunch_input_extra_check_passed_count = 15
artifact_check_summary.passed = true
artifact_check_summary.failures = []
artifact_check_summary.require_all_field_mirror_stubs = true
artifact_check_summary.min_online_inputs = 16

first input row_ok_count:
  base native stub = 174 / 174
  future args scale_metadata_handle = 174 / 174
  future args descriptor_ptr = 174 / 174
  future args packed_weight_descriptor = 174 / 174
  future args aux_metadata_handle = 174 / 174

all 15 extra exported prelaunch tables passed the same native stub suite.
```

This promotes the future-kernel-args bridge evidence from a single online
prelaunch table to the existing 16-table 128-sample export.  It is still a
readonly ABI canary only: payload movement, ready credit, WNA16 kernel argument
mutation, and current WNA16 argument reinterpretation remain disabled.

Runner summary flatten check:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_runner_future_args_field_refresh_flatten_check.json

passed = true
artifact_check_summary.passed = true
artifact_check_summary.failures = []
artifact_check_summary.runner_future_kernel_args_stub_row_ok_count = 174
artifact_check_summary.runner_future_kernel_args_descriptor_ptr_stub_row_ok_count = 174
artifact_check_summary.runner_future_kernel_args_packed_weight_stub_row_ok_count = 174
artifact_check_summary.runner_future_kernel_args_aux_metadata_stub_row_ok_count = 174
```

The runner report now exposes the complete future-args field matrix directly in
its `artifact_check_summary`, while the separate strict checker JSON remains the
authoritative gate artifact for the 16-input sweep.

The default readonly lab gate now points its required
`native_typed_consumer_online_prelaunch_canary_runner_json` evidence to the
16-input field-refresh runner:

```text
configs/runtime/
  premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml

native_typed_consumer_online_prelaunch_canary_runner_json =
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_runner_future_args_field_refresh_16_128export.json

conda run -p /home/husrcf/anaconda3/envs/TRY python \
  scripts/run_premap_lab_preflight.py --summary-only \
  --output-json outputs/reports/premap_lab_preflight_status_future_args_field_refresh_16_128export_required_runner.json

passed = true
required_evidence = 11 / 11
optional_evidence = 4 / 4
```

This keeps the lab precondition tied to the multi-input online native-stub
evidence instead of the older scale-only runner artifact.

### 2026-05-31 future-native launch ABI runner refresh

The readonly lab preflight was refreshed to use the stricter future-native
launch ABI runner artifact.  This closes the previous false-fail where
`run_premap_lab_preflight.py` expected the future-kernel field-mask and
`requires_wna16_arg_reinterpretation` fields in runner summaries, while the
native stub outputs already contained them.

Patch scope:

```text
scripts/run_premap_online_native_stub_canary.py
  propagates *_requires_wna16_arg_reinterpretation
  propagates *_field_mask / *_required_field_mask
  into primary and extra online-input runner summaries
```

Refreshed evidence:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_runner_future_native_launch_abi_16_128export.json

passed = true
failures = []
online_prelaunch_input_check_count = 16
online_prelaunch_input_extra_check_passed_count = 15

future_kernel_consumer_args_requires_wna16_arg_reinterpretation = false
future_kernel_consumer_args_field_mask = 15
future_kernel_consumer_args_required_field_mask = 7

future_kernel_native_consumer_requires_wna16_arg_reinterpretation = false
future_kernel_native_consumer_field_mask = 15
future_kernel_native_consumer_required_field_mask = 7

future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation = false
future_kernel_native_launch_consumer_field_mask = 15
future_kernel_native_launch_consumer_required_field_mask = 7
```

Checker and preflight evidence:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_artifact_check_future_native_launch_abi_16_128export.json
passed = true
failures = []

outputs/reports/
  premap_lab_preflight_future_native_launch_abi_16_128export.json
passed = true
failures = []
required_evidence = 11 / 11
optional_evidence = 4 / 4

outputs/reports/
  premap_lab_preflight_full_latest.json
passed = true
failures = []
```

This promotes the four-field future-native launch ABI path to the current
default lab preflight evidence while still keeping the runtime boundary
readonly:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_check_premap_online_native_stub_canary_artifacts.py \
         tests/test_run_premap_lab_preflight.py \
         tests/test_run_premap_online_native_stub_canary.py -q

53 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

706 passed, 2 warnings
```

### 2026-05-31 vLLM decode block-table trace sidework

The decode workload trace sidework now has a schema-v2 block-table collector
under `traceData/`.  This trace is for workload metadata and paged-KV locality
analysis, not latency benchmarking.

Main outputs:

```text
traceData/vllm_decode_block_table_v2/
  SUMMARY.md
  length_sweep_manifest.json
  v2_sweep_run_status.json
  jsonl/dolly_plen64_gen64_gpu0.jsonl
  jsonl/dolly_plen128_gen64_gpu0.jsonl
  jsonl/dolly_plen256_gen64_gpu0.jsonl
  jsonl/dolly_plen512_gen64_gpu0.jsonl
  jsonl/dolly_plen1024_gen64_gpu0.jsonl
  jsonl/dolly_plen2048_gen64_gpu0.jsonl
```

All six length-sweep files passed the v2 checker:

```text
prompt lengths = 64 / 128 / 256 / 512 / 1024 / 2048
samples per length = 32
gen tokens = 64
checker error_count = 0 for all lengths
prompt_len null count = 0 for all lengths
block_ids present = true
block_size_tokens = 1056
kv_cache_layout.available = false at metadata-builder boundary
```

A lower-level contrast run confirms the same schema can capture real KV-cache
layout when collected at the chunked-prefill paged-decode boundary:

```text
traceData/vllm_decode_block_table_v2_kvlayout_true/
  jsonl/dolly_plen512_gen64_gpu0.jsonl
  jsonl/dolly_plen512_gen64_gpu0.check.json

rows = 2000
checker error_count = 0
kv_cache_layout_available_count = 2000
block_size_tokens = 1056
```

The nonstandard block size is expected for this model/runtime; vLLM reports:

```text
Setting attention block size to 1056 tokens to ensure that attention page size is >= mamba page size.
```

Reviewer follow-up:

```text
Subagent review found no blocker in the lab preflight evidence chain:
summary-only output does not bypass artifact checks, and the future-kernel
field-mask / reinterpretation fields are propagated through runner summaries.

The review did find sidework checker hardening issues:
  - block_size_tokens <= 0 could crash the checker
  - bool/negative numeric fields could be coerced silently
  - query_start_loc / prompt_len / generated_token_idx lacked semantic checks
```

Fixes applied:

```text
scripts/check_vllm_decode_workload_trace.py
  rejects bool integer fields
  rejects negative cache lengths / valid counts / block ids
  reports block_size_tokens <= 0 as checker errors instead of crashing
  checks query_start_loc monotonicity and closure against q_lens
  checks sequence cache_seqlen parity
  checks generated_token_idx == cache_seqlen - prompt_len when both fields exist
  keeps seq_start_loc validation intentionally light: monotonic + starts at 0

tests/test_check_vllm_decode_workload_trace.py
  covers valid v2 traces
  covers zero block size
  covers bool cache_seqlen
  covers negative valid_block_count
  covers query_start_loc and generated_token_idx semantic errors
```

All trace check artifacts were refreshed with the hardened checker:

```text
traceData/vllm_decode_block_table_v2/jsonl/*.check.json
traceData/vllm_decode_block_table_v2_kvlayout_true/jsonl/*.check.json

error_count = 0 for all refreshed files
```

Validation after review fixes:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_check_vllm_decode_workload_trace.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py \
         tests/test_run_premap_lab_preflight.py \
         tests/test_run_premap_online_native_stub_canary.py -q

58 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

711 passed, 2 warnings
```

## 2026-05-31 - Future Native Dispatch ABI Stub Gate

The typed premap native consumer path now has one more readonly ABI rung that
looks closer to a future kernel launch site while still avoiding current WNA16
kernel argument mutation:

```text
premap_future_kernel_native_consumer_dispatch_abi_v1
  source = premap_future_kernel_native_consumer_launch_abi_v1
  payload_bytes = 0
  passed_to_kernel = false
  changes_kernel_launch_args = false
  current_wna16_arg_compatible = false
```

This dispatch ABI wraps the existing native launch ABI with explicit dispatch
metadata:

```text
grid_x
block_x
shared_mem_bytes
row_offset
row_limit
rows_per_program
```

The independent HIP stub now validates this dispatch-shaped object and consumes
rows through the future-native path. It still does not dereference payloads and
does not pass anything to the real WNA16 fused-MoE kernel.

Evidence:

```text
outputs/reports/premap_kernel_consumer/
  schema_check_future_native_dispatch.json
  typed_consumer_stub_future_native_dispatch_dry_run.json
  typed_consumer_stub_future_native_dispatch_canary.json
```

The canary used an exported online vLLM/AWQ typed-consumer input:

```text
future_kernel_native_dispatch_consumer_checked = true
future_kernel_native_dispatch_consumer_row_count = 174
future_kernel_native_dispatch_consumer_row_ok_count = 174
future_kernel_native_dispatch_consumer_error_count = 0
future_kernel_native_dispatch_consumer_payload_bytes = 0
future_kernel_native_dispatch_consumer_passed_to_kernel = false
future_kernel_native_dispatch_consumer_current_wna16_arg_compatible = false
single_field_mirror = scale_metadata_handle
single_field_mirror_row_ok_count = 174 / 174
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_premap_typed_consumer_stub.py \
         tests/test_premap_kernel_consumer_schema.py \
         tests/test_run_premap_lab_preflight.py -q

65 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

713 passed, 2 warnings

git diff --check

clean
```

Current boundary:

```text
This is a future-kernel-shaped native dispatch stub, not a live WNA16 kernel
argument replacement. The next gate is to wire this dispatch ABI into the
online native-stub canary runner / lab preflight artifacts before any real
kernel-side field replacement.
```

## 2026-05-31 - Future Native Dispatch Online Gate Tightening

The future-native dispatch ABI is now wired into the online prelaunch native
stub runner and the artifact checker. A review pass identified one important
correctness gap: dispatch metadata previously did not bind the semantic row
window tightly enough to the launch geometry.

Fix:

```text
active_rows = row_limit - row_offset
grid_x * block_x >= active_rows
(grid_x - 1) * block_x < active_rows
rows_per_program == block_x
runtime gridDim.x == dispatch.grid_x
runtime blockDim.x == dispatch.block_x
```

The stub report now emits these invariants:

```text
future_kernel_native_dispatch_consumer_active_rows
future_kernel_native_dispatch_consumer_launch_threads
future_kernel_native_dispatch_consumer_launch_geometry_checked
future_kernel_native_dispatch_consumer_launch_covers_active_rows
future_kernel_native_dispatch_consumer_launch_minimal_cover
```

The schema artifact also records the dispatch contract:

```text
future_kernel_native_consumer_dispatch_abi_launch_geometry_required = true
future_kernel_native_consumer_dispatch_abi_row_window_required = true
future_kernel_native_consumer_dispatch_abi_minimal_cover_required = true
future_kernel_native_consumer_dispatch_abi_rows_per_program_source = block_x
```

Evidence:

```text
outputs/reports/premap_kernel_consumer/
  typed_consumer_stub_future_native_dispatch_canary.json
  online_prelaunch_native_stub_canary_runner_future_dispatch.json
  online_prelaunch_native_stub_canary_artifact_check_future_dispatch.json
```

Low-level dispatch canary:

```text
row_count = 174
row_ok_count = 174
active_rows = 174
grid_x = 1
block_x = 256
launch_threads = 256
launch_geometry_checked = true
launch_covers_active_rows = true
launch_minimal_cover = true
payload_bytes = 0
passed_to_kernel = false
current_wna16_arg_compatible = false
```

Online prelaunch canary:

```text
runner passed = true
artifact_check passed = true
runner_future_kernel_native_consumer_dispatch_stub_row_count = 204
runner_future_kernel_native_consumer_dispatch_stub_row_ok_count = 204
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_premap_typed_consumer_stub.py \
         tests/test_premap_kernel_consumer_schema.py \
         tests/test_run_premap_lab_preflight.py \
         tests/test_run_premap_online_native_stub_canary.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py -q

83 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

713 passed, 2 warnings

git diff --check

clean
```

Current boundary:

```text
The dispatch ABI is now a stricter online lab gate, but it is still readonly.
It does not mutate payloads, does not mark ready credit, does not pass kernel
arguments, and remains explicitly incompatible with the current WNA16 argument
list. The next gate is a future-kernel-compatible consumer path that accepts
this dispatch-shaped ABI as its own typed input, still default disabled.
```

## 2026-05-31 - Dispatch Row-Window Guard Review Fix

A second review pass tightened the future-native dispatch ABI guardrails before
promoting it further:

```text
1. The dispatch kernel now validates row_limit >= row_offset and
   row_limit <= row_count before computing active_rows, preventing unsigned
   row-window underflow from feeding row iteration.

2. The artifact checker now accepts generic dispatch row windows by deriving
   active_rows = row_limit - row_offset and comparing dispatch row counts
   against active_rows instead of the full table row_count.

3. The online runner remains stricter than the artifact checker and still
   requires the lab-gate full-range window:
   row_offset = 0 and row_limit = row_count.
```

Additional negative coverage now checks:

```text
active_rows mismatch
launch_threads mismatch
non-minimal dispatch launch cover
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_premap_typed_consumer_stub.py \
         tests/test_premap_kernel_consumer_schema.py \
         tests/test_run_premap_lab_preflight.py \
         tests/test_run_premap_online_native_stub_canary.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py -q

87 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_typed_consumer_stub.py \
    --device 0 \
    --input-json data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70_stride320/premap_native_typed_consumer_inputs/premap_native_typed_consumer_input_0000_sample_0_seq0_tok-1_layer0.json \
    --output-json outputs/reports/premap_kernel_consumer/typed_consumer_stub_future_native_dispatch_canary.json \
    --macro MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA \
    --macro MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION \
    --macro MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY \
    --macro MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME \
    --macro MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI \
    --macro MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI \
    --macro MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI \
    --macro MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD \
    --macro MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR

passed = true
row_count = 174
future_kernel_native_dispatch_consumer_active_rows = 174
future_kernel_native_dispatch_consumer_launch_threads = 256
future_kernel_native_dispatch_consumer_launch_minimal_cover = true
payload_bytes = 0
passed_to_kernel = false

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_online_native_stub_canary.py \
    --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_dispatch.json \
    --artifact-check-output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_future_dispatch.json

runner passed = true
artifact_check passed = true
dispatch row_count = 204
dispatch row_ok_count = 204

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

717 passed, 2 warnings

git diff --check

clean
```

Review:

```text
No blocking findings. The reviewer confirmed that row-window underflow is
guarded, the online runner keeps the intended full-range lab gate, and the
artifact checker now supports generic windowed summaries.
```

## 2026-05-31 - Future Dispatch Multi-Input Canary

The future-native dispatch online canary was extended beyond the single input
smoke by reusing the existing Dolly-128 native input export:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_online_native_stub_canary.py \
    --trace-config configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70.yaml \
    --skip-trace \
    --max-online-inputs 2 \
    --min-artifact-online-inputs 2 \
    --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_dispatch_2input.json \
    --artifact-check-output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_future_dispatch_2input.json
```

Result:

```text
runner passed = true
artifact_check passed = true
min_online_inputs = 2
online_prelaunch_input_check_count = 2
online_prelaunch_input_extra_check_count = 1
online_prelaunch_input_extra_check_passed_count = 1
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

This confirms that the dispatch-shaped readonly native consumer gate is not
limited to a single exported prelaunch table. The path still remains a native
stub / artifact gate only; it does not pass WNA16 kernel arguments.

The same gate was then extended to four exported prelaunch tables:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_online_native_stub_canary.py \
    --trace-config configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70.yaml \
    --skip-trace \
    --max-online-inputs 4 \
    --min-artifact-online-inputs 4 \
    --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_dispatch_4input.json \
    --artifact-check-output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_future_dispatch_4input.json

runner passed = true
artifact_check passed = true
min_online_inputs = 4
online_prelaunch_input_check_count = 4
online_prelaunch_input_extra_check_count = 3
online_prelaunch_input_extra_check_passed_count = 3
```

The four-input run covers row-count variation across exported prelaunch tables
while keeping the same safety boundary: no payload dereference, no ready credit,
no WNA16 argument mutation.

The runner now also supports compact stdout for larger stub sweeps:

```text
--stdout-mode full     # default, old behavior
--stdout-mode summary  # compact status line
--stdout-mode none     # artifacts only
```

This was used to extend the same gate to eight exported prelaunch tables:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_online_native_stub_canary.py \
    --trace-config configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70.yaml \
    --skip-trace \
    --max-online-inputs 8 \
    --min-artifact-online-inputs 8 \
    --stdout-mode summary \
    --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_dispatch_8input.json \
    --artifact-check-output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_future_dispatch_8input.json

passed = true
artifact_check_passed = true
min_online_inputs = 8
online_prelaunch_input_check_count = 8
online_prelaunch_input_extra_check_count = 7
online_prelaunch_input_extra_check_passed_count = 7
final_deferred_count = 0
status_deferred_count = 0
```

The previously interrupted 16-input target now also passes with compact stdout:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_online_native_stub_canary.py \
    --trace-config configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70.yaml \
    --skip-trace \
    --max-online-inputs 16 \
    --min-artifact-online-inputs 16 \
    --stdout-mode summary \
    --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_dispatch_16input.json \
    --artifact-check-output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_future_dispatch_16input.json

passed = true
artifact_check_passed = true
min_online_inputs = 16
online_prelaunch_input_check_count = 16
online_prelaunch_input_extra_check_count = 15
online_prelaunch_input_extra_check_passed_count = 15
final_deferred_count = 0
status_deferred_count = 0
```

### 2026-05-31 - Dispatch Canary Promoted Into Lab Preflight

The default live-connected readonly premap gate now uses the 16-input future
native dispatch canary as the canonical online prelaunch runner evidence:

```text
native_typed_consumer_online_prelaunch_canary_runner_json:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_dispatch_16input.json
```

The preflight content checker now validates the dispatch ABI summary in addition
to the existing native/launch summaries:

```text
future_kernel_native_dispatch_consumer_checked = true
future_kernel_native_dispatch_consumer_abi_name =
  premap_future_kernel_native_consumer_dispatch_abi_v1
future_kernel_native_dispatch_consumer_active_rows = row_limit - row_offset
future_kernel_native_dispatch_consumer_row_count = row_count
future_kernel_native_dispatch_consumer_row_ok_count = row_count
future_kernel_native_dispatch_consumer_launch_geometry_checked = true
future_kernel_native_dispatch_consumer_launch_covers_active_rows = true
future_kernel_native_dispatch_consumer_launch_minimal_cover = true
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

The default preflight passes with this stricter evidence:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_lab_preflight.py \
    --summary-only \
    --output-json outputs/reports/premap_lab_preflight_dispatch_default_gate_check.json

passed = true
default_contract_passed = true
default_required_evidence_passed = true
native_typed_consumer_online_prelaunch_canary_runner_json =
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_dispatch_16input.json
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

717 passed, 2 warnings
git diff --check: clean
```

Strict no-defer runner regeneration also passes. The canary runner no longer
asks lab preflight to defer runner/artifact evidence; both the stage preflight
and final preflight use the same strict no-defer lab gate.

```text
runner:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_window_tail4_32input_nodefer.json

artifact check:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input_nodefer.json

stage preflight:
  outputs/reports/premap_lab_preflight_online_prelaunch_native_stub_canary_nodefer_32input.json

stage preflight status:
  outputs/reports/premap_lab_preflight_status_online_prelaunch_native_stub_canary_nodefer_32input.json

passed = true
artifact_check_passed = true
final_preflight_passed = true
online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_passed_count = 31 / 31
stage1_deferred_count = 0
final_deferred_count = 0
status_deferred_count = 0
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
```

## 2026-06-02 - Native runner final compact status check

The online native-stub canary runner now validates its final no-defer lab
preflight status with the compact preflight summary checker before accepting
the run as a strict gate.  The runner already performs the two-stage flow:

```text
stage1:
  allow deferred runner/artifact self-evidence
  used only to bootstrap the runner artifacts

final:
  strict no-defer full preflight
  strict no-defer summary-only preflight
  compact summary checker over the final summary artifact
```

The final checker result is recorded in the runner report:

```text
final_preflight_status_check_output_json
final_preflight_status_check_summary.passed
final_preflight_status_check_summary.failures
final_preflight_status_check_summary.online_merged_source_count
final_preflight_status_check_summary.online_merged_row_count
final_preflight_status_check_summary.online_merged_dispatch_active_rows
```

If the compact checker fails, the runner now appends
`final_preflight_status_check_not_passed` and the final report is not accepted
as passed.  This closes the gap between generating a compact summary and
actually validating that the summary is sufficient for the lab default
preflight gate.

Validation:

```text
pytest tests/test_run_premap_online_native_stub_canary.py -q:
  16 passed

pytest tests/test_check_premap_lab_preflight_summary.py \
       tests/test_run_premap_lab_preflight.py \
       tests/test_run_premap_online_native_stub_canary.py -q:
  112 passed

pytest tests -q:
  867 passed, 2 warnings
```

## 2026-06-02 - Merged arg-slot runner lab GPU default

The online-merged future native arg-slot runner now defaults to the same device
as the lab preflight requirement:

```text
LAB_DEFAULT_GPU_DEVICE = 1
--device default = 1
```

The preflight had already rejected merged multiprogram arg-slot evidence whose
runner artifact did not target GPU1.  This patch removes the mismatch where
the runner could generate a default GPU0 artifact that was immediately invalid
for the lab gate unless the caller remembered to pass `--device 1`.

The option remains configurable for manual diagnostics, but the default runner
artifact is now aligned with the strict lab precondition.

Validation:

```text
pytest tests/test_run_premap_online_merged_native_arg_slot_canary.py \
       tests/test_run_premap_lab_preflight.py -q:
  97 passed
```

## 2026-06-02 - Compact preflight arg-slot boundary fields

The summary-only lab preflight artifact now exposes the online-merged
multiprogram arg-slot runner boundary fields required to judge whether compact
status is equivalent to the full lab gate:

```text
default_kernel_consumer_online_merged_multiprogram_device = 1
default_kernel_consumer_online_merged_multiprogram_mirror_field =
  scale_metadata_handle
default_kernel_consumer_online_merged_multiprogram_not_single_launch_table =
  true
default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible =
  false
```

The compact preflight summary checker now rejects summaries that target the
wrong lab GPU, use the wrong arg-slot mirror field, pretend the merged evidence
is a single vLLM launch table, or mark the future arg-slot ABI as current-WNA16
compatible.

Refreshed artifact check:

```text
outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.json:
  device = 1
  mirror_field = scale_metadata_handle
  not_single_launch_table = true
  current_wna16_arg_compatible = false

outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.check.json:
  passed = true
```

Validation:

```text
pytest tests/test_check_premap_lab_preflight_summary.py \
       tests/test_run_premap_lab_preflight.py -q:
  97 passed

pytest tests -q:
  868 passed, 2 warnings
```

Post-commit runtime canary check with the new lab default also passed:

```text
command:
  python scripts/run_premap_online_merged_native_arg_slot_canary.py
    --output-json
      outputs/reports/premap_kernel_consumer/
        online_merged_future_native_arg_slot_canary_runner_latest.json
    --stub-output-json
      outputs/reports/premap_kernel_consumer/
        typed_consumer_stub_gpu1_online_merged_future_native_arg_slot_32tables_canary_latest.json
    --merged-output-json
      outputs/reports/premap_kernel_consumer/
        online_merged_prelaunch_typed_consumer_input_arg_slot_32tables_latest.json

passed = true
device = 1
selected_source_count = 32
merged_row_count = 1841
dispatch_active_rows = 1841
future_kernel_native_arg_slot_consumer_row_ok_count = 1841 / 1841
packet_chain_depth = 3
handle_projection_hashchain_equal = true
no_payload = true
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
not_a_single_vllm_launch_table = true
```

## 2026-06-02 - Post-schema-refresh lab preflight

After refreshing the kernel consumer schema documentation, the default lab
preflight was rerun in summary-only, no-defer mode:

```text
artifact:
  outputs/reports/premap_lab_preflight_default_with_evidence_sha256_final.json

passed = true
default_contract_passed = true
default_required_evidence_passed = true
default_optional_evidence_passed = true
default_kernel_consumer_schema_passed = true
default_kernel_consumer_online_merged_multiprogram_source_count = 32
default_kernel_consumer_online_merged_multiprogram_row_count = 1841
default_kernel_consumer_online_merged_multiprogram_dispatch_active_rows = 1841
default_kernel_consumer_online_merged_multiprogram_hashchain_equal = true
default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked = true
default_kernel_consumer_online_merged_multiprogram_no_payload = true
default_kernel_consumer_online_merged_multiprogram_passed_to_kernel = false
default_kernel_consumer_online_merged_multiprogram_changes_kernel_launch_args = false
default_kernel_consumer_dispatch_runner_evidence_sha256 =
  79b3df236b19f2ab08e3020280424e155402e883bb05c14f0bd5d8d783371469
default_kernel_consumer_dispatch_runner_artifact_evidence_sha256 =
  f094f2488273062866c126fa8a3f2e7cb869e155a1ddce3e232a21bd1ede4e6f
default_kernel_consumer_online_merged_multiprogram_evidence_sha256 =
  dae8057ebb0f9b350578f5030b85582de828c437d56f9e5a73ec9f5e7b27ed86
default_kernel_consumer_dispatch_ptr_standalone_evidence_sha256 =
  7a1f89aba767b4c530fe6fa2a78555691202d9d7a1a884ac4587cb92c29d1be7
default_kernel_consumer_arg_slot_standalone_evidence_sha256 =
  1b542fbbe0848a5716d7a3629b69e25da5adae64ded9cd70597e6f1b8c7c0331
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
```

This keeps the lab default gate on the safe future-native typed ABI path:
readonly/prelaunch-derived handle rows are consumed by the native bridge and
merged multiprogram runner, while payload movement, ready credit, current WNA16
argument mutation, and WNA16 argument reinterpretation remain disabled.
The preflight summary now also records SHA256 digests for required evidence
files, so a later run can detect if a `latest` evidence path resolves to
different content.

The compact status also records SHA256 digests for the default readonly gate,
the blocked canary gate, and the typed consumer schema artifact:

```text
artifact:
  outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.json

passed = true
default_readonly_gate_sha256 =
  d71b6f5afd476212165fd366ca05995d2d19c849d77864af715f536d5fdf3d92
canary_gate_sha256 =
  b9ffed4a6b70ab79598c4c3ef7fabf7b87f1df1691b39d25fee58b35a62bc9f6
default_kernel_consumer_schema_artifact_sha256 =
  cd5330301d4c2cb9fc0999d20dcbeeefd5f02e02572ae2d8ccfea64f36ba9fc0
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
```

A compact summary checker is now available for this artifact:

```text
script:
  scripts/check_premap_lab_preflight_summary.py

input:
  outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.json
output:
  outputs/reports/premap_lab_preflight_default_with_gate_schema_sha256.check.json

passed = true
online_merged_source_count = 32
online_merged_row_count = 1841
online_merged_dispatch_active_rows = 1841
failures = []
```

The standalone schema checker also passes on the typed consumer schema artifact:

```text
artifact:
  outputs/reports/premap_kernel_consumer/schema_check_post_schema_refresh.json

schema = fused_moe_awq_wna16_kernel_side_typed_consumer_object_v1
schema_hash = c1384d55958c9aa78b07b4ee3e9094f835ec1ca4c61bd7e9613c01ceb8275e98
row fields =
  descriptor_ptr
  packed_weight_descriptor
  scale_metadata_handle
  aux_metadata_handle
row metadata =
  layer_id
  expert_id
  address_key_hash
  row_order_hash
  ordered_row_hash
future args layout reported = true
native consumer ABI layout reported = true
launch ABI layout reported = true
dispatch ABI layout reported = true
dispatch-ptr ABI layout reported = true
arg-slot ABI layout reported = true
passed = true
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_online_native_stub_canary.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py -q

39 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

747 passed, 2 warnings
```

The default lab gate now references the strict no-defer 32-input online native
stub artifacts for all required native/future-native runner and artifact-check
evidence labels. A fresh default preflight after the config update passes with
zero deferred evidence:

```text
default gate config:
  configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml

preflight:
  outputs/reports/premap_lab_preflight_default_nodefer_artifact_current.json

preflight status:
  outputs/reports/premap_lab_preflight_status_default_nodefer_artifact_current.json

passed = true
failures = []
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
default_kernel_consumer_schema_passed = true
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py -q

72 passed
```

Post-review hardening:

```text
artifact checker:
  runtime/strict deferred-count summaries are now cross-checked against the
  full preflight evidence scan when that scan is available.

lab preflight:
  --defer-online-prelaunch-artifact-evidence is rejected unless the matching
  runner evidence is also deferred, so artifact-only defer cannot hide a
  missing artifact-check during normal lab preflight.

dispatch ABI tests:
  added a positive grid_x > 1 / multi-program dispatch coverage case, covering
  the future row assignment formula beyond the single-program tail-window path.
  added explicit runtime and strict deferred-count mismatch tests.
```

Latest validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_check_premap_online_native_stub_canary_artifacts.py \
         tests/test_run_premap_lab_preflight.py -q

64 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/check_premap_online_native_stub_canary_artifacts.py \
    --runner-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_window_tail4_32input.json \
    --preflight-json outputs/reports/premap_lab_preflight_dispatch_program_iteration_32required_contract_check.json \
    --status-json outputs/reports/premap_lab_preflight_status_dispatch_program_iteration_32required_contract_check.json \
    --output-json outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input.json \
    --require-all-field-mirror-stubs \
    --min-online-inputs 32

passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_lab_preflight.py \
    --summary-only \
    --output-json outputs/reports/premap_lab_preflight_dispatch_program_iteration_review_fix_final_status.json

passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
deferred_online_prelaunch_runner_evidence = false
deferred_online_prelaunch_artifact_evidence = false

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

740 passed, 2 warnings

git diff --check: clean
```

### 2026-05-31 16:54 CST — Future-native dispatch ABI program/lane gate

The future-native typed consumer dispatch ABI now validates the row iteration
shape that a future kernel-side consumer would use:

```text
row = row_offset + program_id * rows_per_program + lane_id
program_id = blockIdx.x
lane_id = threadIdx.x
rows_per_program = block_x
```

This remains a no-op bridge:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

The native stub launch was corrected to use the dispatch window grid
(`dispatch_blocks`) rather than the full table grid, so tail-window dispatch
geometry now matches the declared ABI when `active_rows << row_count`.

Evidence:

```text
runner:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_window_tail4_32input.json

artifact check:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input.json

lab preflight:
  outputs/reports/premap_lab_preflight_dispatch_program_iteration_32required_final_status.json

runner passed = true
runner failures = []
online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_passed_count = 31 / 31
artifact_check passed = true
artifact_check failures = []
default lab preflight passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
```

Main dispatch summary:

```text
row_count = 174
row_offset = 170
row_limit = 174
active_rows = 4
grid_x = 1
block_x = 256
program_iteration_checked = true
row_assignment_formula = row_offset + program_id * rows_per_program + lane_id
program_count = 1
last_program_active_rows = 4
inactive_lane_count = 252
first_program_row_offset = 170
last_program_row_offset = 170
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_check_premap_online_native_stub_canary_artifacts.py \
         tests/test_run_premap_lab_preflight.py \
         tests/test_premap_kernel_consumer_schema.py -q

66 passed
```

Reviewer blocker fixed:

```text
dispatch.grid_x is now the actual launched dispatch grid, not the full table
grid. Required online artifact evidence now also supports artifact deferral
during self-bootstrapping, and missing min/count fields fail explicitly.
```

Follow-up hardening:

```text
future_kernel_native_dispatch_consumer_program_iteration_hash is now checked,
not only recorded.

hash formula:
  mix64(grid_x + 0xd15c2001)
^ mix64(block_x + 0xd15c2002)
^ mix64(row_offset + 0xd15c2003)
^ mix64(row_limit + 0xd15c2004)
^ mix64(last_program_active_rows + 0xd15c2005)
^ mix64(inactive_lane_count + 0xd15c2006)

artifact checker passed = true
default lab preflight passed = true

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q
736 passed, 2 warnings

Additional regression coverage:
  artifact checker rejects program_iteration_hash missing/mismatch
  lab preflight rejects program_iteration_hash missing/mismatch
```

### 2026-05-31 — 32-Input Dispatch Tail-Window Evidence in Default Preflight

The 32-input adaptive dispatch tail-window evidence is now part of the default
lab gate's machine-checked required evidence set, not just a manual PROGRESS
artifact.  The default gate now requires:

```text
future_kernel_native_dispatch_consumer_online_runner_32_128export_json:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_window_tail4_32input.json

future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input.json
```

The preflight checker treats the 32-input runner label as a stricter online
evidence class.  The standalone artifact-check label is validated with the
same minimum input-count rule, so a stale 16-input artifact cannot satisfy the
32-input required gate:

```text
min online inputs required = 32
future_native_dispatch_tail_window_size = 4
row_offset = max(0, source_row_count - 4)
row_limit = source_row_count
active_rows = row_limit - row_offset
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

Default preflight evidence after promoting the 32-input labels:

```text
output:
  outputs/reports/premap_lab_preflight_dispatch_tail_window_32required_contract_check.json

passed = true
default_contract_passed = true
default_required_evidence_passed = true
default_optional_evidence_passed = true
required_evidence required/present/passed = 13 / 13 / 13
optional_evidence required/present/passed = 10 / 10 / 10
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py \
         tests/test_run_premap_online_native_stub_canary.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py -q

65 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

730 passed, 2 warnings
```

### 2026-05-31 - Future Dispatch Row-Window Canary

The native typed consumer stub now supports an explicit dispatch row window:

```text
--dispatch-row-offset
--dispatch-row-limit
```

Only the future-native dispatch ABI consumes this window.  The table/schema and
other full-row checks continue to cover the full typed table, while the dispatch
stub validates the row subset that a future kernel launch block/window would
consume.

Small online-input canary:

```text
input:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70_stride320/premap_native_typed_consumer_inputs/premap_native_typed_consumer_input_0000_sample_0_seq0_tok-1_layer0.json

output:
  outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_dispatch_row_window_canary_input0000.json

dispatch_row_offset = 1
dispatch_row_limit = 5
future_native_dispatch active_rows = 4
future_native_dispatch row_count = 4
future_native_dispatch row_ok_count = 4
future_native_dispatch grid_x = 1
future_native_dispatch launch_covers_active_rows = true
future_native_dispatch launch_minimal_cover = true
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

This is still a standalone native-stub gate, not a WNA16 kernel-arg handoff.
It validates that the future dispatch ABI can represent block/window-level row
iteration without materializing or mutating the current fused-MoE launch args.

Follow-up review found one non-blocking observability gap: the future native,
launch, and dispatch runner/artifact-check paths were listed in the gate YAML
but not consumed by the optional preflight whitelist.  That gap is now closed:

```text
optional_evidence.required_count = 10
optional_evidence.present_count = 10
optional_evidence.passed_count = 10

future_kernel_native_consumer_online_runner_16_128export_json = passed
future_kernel_native_consumer_online_artifact_check_16_128export_json = passed
future_kernel_native_launch_consumer_online_runner_16_128export_json = passed
future_kernel_native_launch_consumer_online_artifact_check_16_128export_json = passed
future_kernel_native_dispatch_consumer_online_runner_16_128export_json = passed
future_kernel_native_dispatch_consumer_online_artifact_check_16_128export_json = passed
```

The self-referential runner-defer mode now defers the canonical runner plus the
three future-native runner aliases together, so partial pre-write preflight does
not report false missing evidence.

### 2026-05-31 - Future Dispatch ABI Four-Field Mirror Gate

The online native-stub canary now validates the future-native dispatch ABI
against all four typed handle fields instead of only the scale metadata mirror:

```text
scale_metadata_handle
descriptor_ptr
packed_weight_descriptor
aux_metadata_handle
```

The runner exercises the base native ABI, launch ABI, and dispatch ABI for the
same online prelaunch inputs.  It still preserves the lab safety boundary:

```text
payload_bytes = 0
ready_credit = false
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

Latest evidence:

```text
runner:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_dispatch_16input.json

artifact check:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_future_dispatch_16input.json

passed = true
runner_online_prelaunch_input_check_count = 16
runner_online_prelaunch_input_extra_check_count = 15
runner_online_prelaunch_input_extra_check_passed_count = 15
stage1_deferred_count = 7
final_deferred_count = 3
status_deferred_count = 3

future_native_dispatch scale rows = 174 / 174
future_native_dispatch descriptor_ptr rows = 174 / 174
future_native_dispatch packed_weight rows = 174 / 174
future_native_dispatch aux_metadata rows = 174 / 174
```

The defer contract is now split explicitly:

```text
stage1 preflight:
  defers online runner evidence and artifact-check evidence
  deferred_count = 7

final/status preflight inside the runner:
  defers only artifact-check evidence, because the runner artifact exists
  deferred_count = 3

default lab preflight after artifact generation:
  defers nothing
```

This prevents runner defer mode from silently masking non-self-referential
artifact evidence failures.  The final default lab preflight, after artifact
generation, consumes all evidence normally:

```text
outputs/reports/premap_lab_preflight_dispatch_default_gate_check.json

passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
required_evidence = 11 / 11
optional_evidence = 10 / 10
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

719 passed, 2 warnings
git diff --check: clean
```

### Future-Native Dispatch Row-Window Gate

The online native stub canary now supports an explicit dispatch row window for
the future kernel-side consumer ABI:

```text
--future-native-dispatch-row-offset
--future-native-dispatch-row-limit
```

Only dispatch ABI stubs receive this row-window contract.  Base native-consumer
and launch ABI stubs remain full-table checks, which keeps the launch schema and
dispatch schema separated.

Latest 16-input real canary:

```text
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_window_16input.json
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_16input.json

passed = true
artifact_check_passed = true
online_prelaunch_input_check_count = 16
online_prelaunch_input_extra_check_count = 15
online_prelaunch_input_extra_check_passed_count = 15
future_native_dispatch_row_offset = 1
future_native_dispatch_row_limit = 5
future_kernel_native_dispatch_consumer_active_rows = 4
future_kernel_native_dispatch_consumer_row_count = 4
future_kernel_native_dispatch_consumer_row_ok_count = 4
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

This moves the future-native dispatch ABI from a full-table read-only checker to
a windowed row-iteration checker, which is closer to how a real kernel consumer
would receive a subset of prepared descriptor/address rows.

### Strict Decode KV-Layout Trace Gate

The sidework paged-KV trace checker now supports strict workload validation:

```text
--require-decode-only
--require-provenance
--require-kv-cache-layout-available
```

The materializer also has a strict recapture preset:

```text
--strict-decode-kv-layout-trace
```

This preset captures the real `chunked_prefill_paged_decode` boundary, filters
out prefill/chunked rows by requiring `q_len == 1`, preserves batch row
provenance through `sample_indices` / `record_ids` and
`sequences[].sample_idx`, and records KV-cache layout shape/stride/data pointers.

Strict smoke evidence:

```text
traceData/tmp_strict_layout_chunked_smoke/jsonl/dolly_plen64_gen4_gpu0.jsonl
traceData/tmp_strict_layout_chunked_smoke/jsonl/dolly_plen64_gen4_gpu0.check.json

row_count = 30
error_count = 0
phase_counts = {decode: 30}
kv_cache_layout_available_count = 30
kv_cache_layout_unavailable_count = 0
strict decode/provenance/layout requirements = true
```

This replaces the older `kvlayout_true` artifact as the path for future strict
KV-layout recapture.  The old artifact remains useful only as a shape/stride
reference because it includes prefill-like `q_len > 1` rows and weak provenance.

### Strict Decode KV-Layout Full Sweep + Replay

The strict v2 paged-KV block-table sidework now has a full length sweep:

```text
root:
  traceData/vllm_decode_block_table_v2_strict_kvlayout_true/

lengths = 64, 128, 256, 512, 1024, 2048
samples_per_length = 32
gen = 64
gpu = 0
```

All six JSONL traces pass the locked checker requirements:

```text
error_count = 0
q_len = 1 only
kv_cache_layout.available = true for every record
sample_indices / record_ids / prompt_lens present
sequences[].sample_idx present
sequences[].block_ids present
block_size_tokens explicitly recorded
k/v shape, stride, dtype, element_size, and device present
```

Checker summary:

```text
plen64:   rows=630 errors=0 kv_layout=630/630 block_size=1056 cache_p50/max=95/127   valid_blocks=1/1 unique_blocks=32
plen128:  rows=630 errors=0 kv_layout=630/630 block_size=1056 cache_p50/max=160/191  valid_blocks=1/1 unique_blocks=32
plen256:  rows=630 errors=0 kv_layout=630/630 block_size=1056 cache_p50/max=288/319  valid_blocks=1/1 unique_blocks=32
plen512:  rows=630 errors=0 kv_layout=630/630 block_size=1056 cache_p50/max=545/575  valid_blocks=1/1 unique_blocks=32
plen1024: rows=630 errors=0 kv_layout=630/630 block_size=1056 cache_p50/max=1057/1087 valid_blocks=2/2 unique_blocks=63
plen2048: rows=630 errors=0 kv_layout=630/630 block_size=1056 cache_p50/max=2082/2111 valid_blocks=2/2 unique_blocks=64
```

The batched records were flattened into one-sequence-per-row JSONL for replay
consumers:

```text
flattened_rows = 114820
```

Capacity plans:

```text
batched records:
  records = 3780
  actual_work_size p50/p90/p99/max = 620 / 4092 / 4224 / 4224
  recommended_classes = [128, 320, 1152, 4224]

flattened rows:
  records = 114820
  actual_work_size p50/p90/p99/max = 20 / 130 / 132 / 132
  recommended_classes = [64, 192]
```

unidec replay successfully consumed the flattened real block IDs.  For fused
`paged-full-producer` over all 114,820 rows:

```text
real vLLM block_ids:     429.810 ms, 3.743 us/row
synthetic random:        529.435 ms, 4.611 us/row
synthetic contiguous:    515.537 ms, 4.490 us/row
synthetic hot-page:      386.751 ms, 3.368 us/row
```

For full K/V replay (`paged-full`, `value_dim=32`):

```text
real vLLM block_ids:     434.053 ms, 3.780 us/row
synthetic random:        535.060 ms, 4.660 us/row
synthetic contiguous:    519.803 ms, 4.527 us/row
synthetic hot-page:      388.823 ms, 3.386 us/row
```

This is not a vLLM endpoint performance claim.  It is a replay-level locality
probe showing that the captured vLLM block table is materially better than
random/contiguous synthetic placement and still leaves a measurable gap to the
synthetic hot-page upper-locality case.

Relevant files:

```text
traceData/vllm_decode_block_table_v2_strict_kvlayout_true/SUMMARY.md
traceData/vllm_decode_block_table_v2_strict_kvlayout_true/jsonl/
traceData/vllm_decode_block_table_v2_strict_kvlayout_true/jsonl_flattened/
traceData/vllm_decode_block_table_v2_strict_kvlayout_true/*capacity_plan*.json
traceData/vllm_decode_block_table_v2_strict_kvlayout_true/replay_*_paged_full*.csv
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

723 passed, 2 warnings
git diff --check: clean
```

### 2026-05-31 — Adaptive future-native dispatch row-window canary

The future-native dispatch ABI canary now supports a per-input adaptive tail
window:

```text
--future-native-dispatch-tail-window-size N
```

This keeps the existing fixed `--future-native-dispatch-row-offset/limit`
contract intact, but when the tail-window mode is enabled each exported
typed-consumer input derives its own dispatch window from that input's
`row_count`:

```text
row_offset = max(0, row_count - N)
row_limit  = row_count
```

Motivation:

```text
fixed head window 0..4:
  passed on 16 online inputs

fixed mid window 100..104:
  correctly failed on a small exported input with row_count=8

adaptive tail window size 4:
  passed on 16 online inputs
```

Successful canary:

```text
output:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_window_tail4_16input.json

artifact check:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_16input.json

passed = true
artifact_check_passed = true
online_prelaunch_input_check_count = 16
online_prelaunch_input_extra_check_passed_count = 15 / 15
tail_window_size = 4
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

Representative small-row exported inputs now select the valid tail window
instead of failing on a global offset:

```text
input0010 row_count = 8
dispatch row_offset = 4
dispatch row_limit = 8
active_rows = 4

input0015 row_count = 8
dispatch row_offset = 4
dispatch row_limit = 8
active_rows = 4
```

This remains a native typed-consumer / future-dispatch ABI gate. It still does
not pass kernel args to WNA16, does not move payload, and does not change the
real fused-MoE launch.

The default lab preflight now points its future-native dispatch online evidence
at the adaptive tail-window artifacts. The preflight checker was updated so
dispatch sub-windows are validated against `active_rows` instead of incorrectly
requiring every dispatch ABI evidence row to cover the full table.

Default lab preflight after promotion:

```text
output:
  outputs/reports/premap_lab_preflight_dispatch_tail_window_default_gate_check.json

passed = true
default_contract_passed = true
default_required_evidence_passed = true
default_optional_evidence_passed = true
runtime_gate_evidence_scan_passed = true
strict_default_gate_evidence_passed = true
payload_bytes_required = 0
passed_to_kernel_required = false
changes_kernel_launch_args_required = false
```

The adaptive dispatch window is now an explicit default lab contract:

```text
future_kernel_native_dispatch_consumer_tail_window_required = true
future_kernel_native_dispatch_consumer_tail_window_size = 4
```

The lab preflight validates this in two places:

```text
1. runner top-level evidence must report future_native_dispatch_tail_window_size = 4
2. each dispatch consumer summary must satisfy:
   row_offset = max(0, source_row_count - 4)
   row_limit = source_row_count
   active_rows = row_limit - row_offset
   dispatch row_count / row_ok_count = active_rows
```

This prevents a full-range or fixed-window artifact from silently satisfying
the default lab gate.

Contract validation:

```text
output:
  outputs/reports/premap_lab_preflight_dispatch_tail_window_contract_check.json

passed = true
default_contract_passed = true
default_required_evidence_passed = true
default_optional_evidence_passed = true
strict_default_gate_evidence_passed = true
payload_bytes_required = 0
passed_to_kernel_required = false
changes_kernel_launch_args_required = false
```

The stronger 32-input version also passes after exporting a dedicated 32-table
online typed-consumer artifact:

```text
trace config:
  configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70_32tables.yaml

export root:
  data/traces/external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70_stride320_32tables/

exported typed inputs = 32
export stride = 320

runner:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_window_tail4_32input.json

artifact check:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input.json

passed = true
artifact_check_passed = true
online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_passed_count = 31 / 31
tail_window_size = 4
```

The main input dispatch window now covers only the last 4 rows:

```text
source row_count = 174
dispatch row_offset = 170
dispatch row_limit = 174
dispatch active_rows = 4
dispatch row_count = 4
dispatch row_ok_count = 4
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_online_native_stub_canary.py -q

10 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q

728 passed, 2 warnings

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py \
         tests/test_run_premap_online_native_stub_canary.py -q

44 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py \
         tests/test_run_premap_online_native_stub_canary.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py -q

63 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_online_native_stub_canary.py \
    --trace-config configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_native_input_export_audit_mem70_32tables.yaml \
    --skip-trace \
    --max-online-inputs 32 \
    --min-artifact-online-inputs 32 \
    --future-native-dispatch-tail-window-size 4

passed = true

git diff --check: clean
```
## 2026-06-01 - Premap native ABI layout gate

- Added explicit ABI layout metadata for the future native typed consumer path:
  params/launch/dispatch struct sizes, alignments, and critical field offsets.
- The ABI layout gate now checks numeric struct size/alignment/offset values,
  not only the presence of layout field names.
- Added a two-stage bootstrap rule for the online native-stub canary:
  stage-1 may defer only the self-referential runner/artifact evidence needed to
  generate a fresh artifact, but the final lab gate requires a strict no-defer
  preflight and final artifact check.
- Bootstrap and final artifact checks are now recorded separately:
  `outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input_nodefer_bootstrap.json`
  is bootstrap-only and reports `bootstrap_preflight_allowed=true`, while the
  final gate artifact below reports `bootstrap_preflight_allowed=false`.
- The official 32-input canary passed:
  `outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_window_tail4_32input_nodefer.json`
  reports `passed=true`, `online_prelaunch_input_check_count=32`, and
  `online_prelaunch_input_extra_check_passed_count=31`.
- The final artifact check passed:
  `outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_window_tail4_32input_nodefer.json`
  reports `passed=true`, `min_online_inputs=32`, `final_deferred_count=0`,
  `status_deferred_count=0`, and `bootstrap_preflight_allowed=false`.
- Default lab preflight passed with no deferred evidence:
  `outputs/reports/premap_lab_preflight_default_nodefer_layout_current.json`
  and
  `outputs/reports/premap_lab_preflight_status_default_nodefer_layout_current.json`
  report `passed=true`, `runtime_gate_evidence_deferred_count=0`, and
  `strict_default_gate_evidence_deferred_count=0`.

Current gate status: future native typed consumer ABI layout is now part of the
lab preflight. Bootstrap evidence is allowed only for artifact generation; lab
acceptance remains strict no-defer only.

## 2026-06-01 - Pointer-backed future-native dispatch ABI

Added a pointer-backed future dispatch ABI packet:

```cpp
PremapFutureKernelNativeConsumerDispatchPtrV1
```

This packet models a future kernel-side argument slot more closely than the
previous by-value dispatch mirror: it carries a device pointer to
`PremapFutureKernelNativeConsumerDispatchV1`, ABI version, dispatch/result
struct sizes, zero payload bytes, and readonly/no-kernel-pass/no-payload-deref
flags.  It remains a standalone native typed-consumer canary and is explicitly
not compatible with the current AWQ/WNA16 fused-MoE kernel argument list.

Safety boundary:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

Review follow-up:

- A code-review pass found no blocker.
- The device-side dispatch-pointer consumer now validates the by-value packet
  metadata before dereferencing the pointed-to dispatch struct.
- Artifact checks now require dispatch-pointer summaries for the online
  future-dispatch path, including ABI identity, layout values, row counts,
  single-field mirror status, and safety flags.
- Added negative tests for dispatch-pointer ABI version, layout size, and
  kernel-pass safety flag mismatches.

Evidence:

```text
HIP tail smoke:
  /tmp/premap_dispatch_ptr_tail_smoke_after_review.json
  row_count = 4
  row_ok_count = 4
  error_count = 0

online runner:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_runner_future_native_dispatch_ptr_16input.json

artifact check:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_future_native_dispatch_ptr_16input.json

preflight:
  outputs/reports/premap_lab_preflight_status_online_prelaunch_native_stub_canary_future_native_dispatch_ptr_16input.json

online_prelaunch_input_check_count = 16
online_prelaunch_input_extra_check_passed_count = 15 / 15
artifact_check_passed = true
final_preflight_passed = true
final_deferred_count = 0
status_deferred_count = 0
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_check_premap_online_native_stub_canary_artifacts.py \
         tests/test_premap_typed_consumer_stub.py \
         tests/test_run_premap_online_native_stub_canary.py -q

64 passed
```

Current status: this is the closest native-stub ABI so far to a future
kernel-side typed consumer argument shape, but it still does not pass any
argument to the live WNA16 fused-MoE kernel and does not move payload.

## 2026-06-01 - Full-table future-native dispatch lab gate

The default lab preflight now requires full-table future-native dispatch
evidence instead of the earlier tail-window/tail4 canary.  The default runtime
gate contract uses:

```text
future_kernel_native_dispatch_consumer_full_table_required = true
```

and rejects stale tail-window contract keys or runner fields.  In full-table
mode, the online runner must not contain `future_native_dispatch_tail_window_size`
at all, including a null value.  The native dispatch summary must cover the
entire table:

```text
row_offset = 0
row_limit = row_count
active_rows = row_count
```

The accepted default evidence is now:

```text
runner:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_full_32input_nodefer.json

artifact check:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_full_32input_nodefer.json

preflight status:
  outputs/reports/premap_lab_preflight_status_default_after_full_dispatch_evidence_reviewfix.json
```

The regenerated full-table runner reports:

```text
passed = true
online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_passed_count = 31 / 31
future_native_dispatch_tail_window_size present = false
dispatch row_count = 174
dispatch row_offset / row_limit / active_rows = 0 / 174 / 174
dispatch_ptr checked = true
dispatch_ptr row_ok_count = 174 / 174
dispatch_ptr passed_to_kernel = false
dispatch_ptr changes_kernel_launch_args = false
```

Safety boundary remains unchanged:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

Review and validation:

- A GPT-5.3-Codex-Spark review found no blocker after the full-table switch.
- Review follow-up fixed null-tail acceptance, stale tail-window contract
  coexistence, and full-table limit/active-row test coverage.
- `conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q`
  passes with `758 passed, 2 warnings`.

Current status: the lab preflight now guards the closest native-stub dispatch
shape with full-table coverage while still keeping payload movement and live
WNA16 kernel-arg mutation disabled.

## 2026-06-01 - Dispatch-pointer ABI promoted to explicit lab contract

The default lab gate now explicitly requires the pointer-backed future-native
dispatch consumer:

```text
future_kernel_native_dispatch_ptr_consumer_required = true
```

This makes the closest current ABI shape a required lab precondition rather
than an implicit field inside the runner summary.  The required evidence remains
the same full-table 32-input online runner, which reports:

```text
future_kernel_native_dispatch_ptr_consumer_checked = true
future_kernel_native_dispatch_ptr_consumer_row_count = 174
future_kernel_native_dispatch_ptr_consumer_row_ok_count = 174
future_kernel_native_dispatch_ptr_consumer_passed_to_kernel = false
future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args = false
future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible = false
```

The default preflight passes with this stricter contract:

```text
outputs/reports/premap_lab_preflight_status_default_after_dispatch_ptr_required.json
passed = true
default_contract_passed = true
default_required_evidence_passed = true
default_optional_evidence_passed = true
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

758 passed, 2 warnings
```

Current status: the lab default now requires full-table dispatch coverage and a
pointer-backed future kernel dispatch packet, while still forbidding payload
movement and live WNA16 kernel-arg mutation.

## 2026-06-01 - Default preflight status exposes full-table dispatch evidence

The compact default lab preflight status now flattens the required 32-input
future-native dispatch runner fields, so the status artifact can be used as the
first lab preflight entry point without manually opening the runner evidence.

New status fields include:

```text
default_kernel_consumer_dispatch_full_table_required = true
default_kernel_consumer_dispatch_runner_evidence_present = true
default_kernel_consumer_dispatch_runner_evidence_passed = true
default_kernel_consumer_dispatch_checked = true
default_kernel_consumer_dispatch_row_count = 174
default_kernel_consumer_dispatch_row_ok_count = 174
default_kernel_consumer_dispatch_active_rows = 174
default_kernel_consumer_dispatch_row_offset = 0
default_kernel_consumer_dispatch_row_limit = 174
default_kernel_consumer_dispatch_full_table_checked = true
default_kernel_consumer_dispatch_payload_bytes = 0
default_kernel_consumer_dispatch_passed_to_kernel = false
default_kernel_consumer_dispatch_changes_kernel_launch_args = false

default_kernel_consumer_dispatch_ptr_required = true
default_kernel_consumer_dispatch_ptr_checked = true
default_kernel_consumer_dispatch_ptr_row_count = 174
default_kernel_consumer_dispatch_ptr_row_ok_count = 174
default_kernel_consumer_dispatch_ptr_payload_bytes = 0
default_kernel_consumer_dispatch_ptr_passed_to_kernel = false
default_kernel_consumer_dispatch_ptr_changes_kernel_launch_args = false
default_kernel_consumer_dispatch_ptr_current_wna16_arg_compatible = false
```

Review follow-up tightened the status semantics: missing/deferred/failed runner
evidence now appears explicitly in the compact summary instead of only producing
empty flattened metrics, and `full_table_checked` is computed from typed integer
metrics rather than raw JSON values.

Generated artifact:

```text
outputs/reports/premap_lab_preflight_status_default_after_dispatch_ptr_status_flatten.json
passed = true
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

759 passed, 2 warnings
```

Standalone native ABI spot-check:

```text
outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_dispatch_ptr_standalone_canary.json
passed = true
row_count = 1024
future_kernel_native_consumer_row_ok_count = 1024
future_kernel_native_dispatch_consumer_row_ok_count = 1024
future_kernel_native_dispatch_ptr_consumer_row_ok_count = 1024
future_kernel_native_dispatch_ptr_consumer_payload_bytes = 0
future_kernel_native_dispatch_ptr_consumer_passed_to_kernel = false
future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible = false
```

This spot-check exercises the standalone pointer-backed dispatch packet ABI
directly in the native stub.  It still does not pass arguments to the current
WNA16 fused-MoE kernel.

## 2026-06-01 - Standalone dispatch-ptr ABI canary is now a default lab preflight requirement

The default readonly/premap lab gate now requires the standalone
pointer-backed future-native dispatch ABI canary:

```text
future_kernel_native_dispatch_ptr_standalone_canary_json
```

This promotes the standalone native stub check from PROGRESS-only evidence into
the strict default preflight contract.  The required evidence must show:

```text
input_source = synthetic
schema_hash matches the kernel-side typed consumer schema
native / launch / dispatch / dispatch_ptr consumers checked
row_count == row_ok_count at every consumer layer
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
required debug macros enabled
payload dereference / kernel-arg pass macros disabled
```

The compact preflight status now also exposes the standalone canary fields:

```text
outputs/reports/premap_lab_preflight_status_default_after_dispatch_ptr_standalone_required.json
passed = true
required evidence = 14 / 14

default_kernel_consumer_dispatch_ptr_standalone_evidence_present = true
default_kernel_consumer_dispatch_ptr_standalone_evidence_passed = true
default_kernel_consumer_dispatch_ptr_standalone_input_source = synthetic
default_kernel_consumer_dispatch_ptr_standalone_checked = true
default_kernel_consumer_dispatch_ptr_standalone_row_count = 1024
default_kernel_consumer_dispatch_ptr_standalone_row_ok_count = 1024
default_kernel_consumer_dispatch_ptr_standalone_payload_bytes = 0
default_kernel_consumer_dispatch_ptr_standalone_passed_to_kernel = false
default_kernel_consumer_dispatch_ptr_standalone_changes_kernel_launch_args = false
default_kernel_consumer_dispatch_ptr_standalone_current_wna16_arg_compatible = false
```

Review follow-up added explicit negative tests for standalone canary schema hash
mismatch, row-count mismatch, dispatch-ptr packet struct size mismatch, and
unsafe kernel-arg-pass macro enablement.

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py -q

51 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

763 passed, 2 warnings
```

## 2026-06-01 - Default lab gate now uses the nodefer 32-input online native runner

The default readonly/premap lab gate now points the native/launch/dispatch
online runner and artifact-check labels at the post-standalone 32-input
nodefer evidence:

```text
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_dispatch_full_32input_nodefer_after_standalone_required.json
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_dispatch_full_32input_nodefer_after_standalone_required.json
```

The runner validates 32 exported online prelaunch inputs through the native
typed consumer path, including the future-native consumer, launch ABI, dispatch
ABI, and dispatch-ptr ABI checks.  The run remains a no-op consumer gate:

```text
runner passed = true
runner failures = []
online_prelaunch_input_check_count = 32

artifact_check passed = true
artifact_check failures = []
min_online_inputs = 32

default preflight passed = true
default status passed = true
strict_default_gate_evidence_deferred_count = 0
runtime_gate_evidence_deferred_count = 0
```

Compact default status after promotion:

```text
outputs/reports/premap_lab_preflight_status_default_after_online_32input_dispatch_ptr_required.json
passed = true

default_kernel_consumer_dispatch_ptr_checked = true
default_kernel_consumer_dispatch_ptr_row_count = 174
default_kernel_consumer_dispatch_ptr_row_ok_count = 174
default_kernel_consumer_dispatch_ptr_payload_bytes = 0
default_kernel_consumer_dispatch_ptr_passed_to_kernel = false
default_kernel_consumer_dispatch_ptr_changes_kernel_launch_args = false

default_kernel_consumer_dispatch_ptr_standalone_evidence_passed = true
default_kernel_consumer_dispatch_ptr_standalone_row_count = 1024
default_kernel_consumer_dispatch_ptr_standalone_row_ok_count = 1024

default_kernel_consumer_dispatch_runner_online_input_count = 32
default_kernel_consumer_dispatch_runner_online_extra_input_count = 31
default_kernel_consumer_dispatch_runner_online_extra_input_passed_count = 31
default_kernel_consumer_dispatch_runner_artifact_check_passed = true
default_kernel_consumer_dispatch_runner_artifact_check_min_online_inputs = 32
default_kernel_consumer_dispatch_runner_artifact_check_final_deferred_count = 0
default_kernel_consumer_dispatch_runner_final_preflight_passed = true
default_kernel_consumer_dispatch_runner_final_strict_default_gate_evidence_deferred_count = 0
default_kernel_consumer_dispatch_runner_final_runtime_gate_evidence_deferred_count = 0
```

This is still not a WNA16 kernel-argument handoff.  The current gate proves that
the exported prelaunch handle tables can be consumed by the independent typed
ABI stubs and that the default lab preflight rejects missing/deferred evidence
before any payload movement or kernel argument mutation is allowed.

Review follow-up tightened this status path:

```text
runner artifact_check_summary must be present
runner artifact_check_summary.final_deferred_count must be 0
runner final_preflight_status_summary must be present
runner final strict/runtime deferred counts must be 0
compact artifact-check fields are sourced from the independent artifact-check
evidence path, not only from the runner-embedded summary
```

Additional negative tests cover runner-embedded artifact defer, missing runner
final status, and independent artifact-check defer.

Validation after the follow-up:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py -q

54 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

766 passed, 2 warnings
```

## 2026-06-01 - Future native arg-slot ABI is now part of the schema and artifact gate

The future native consumer path now has one more checked ABI layer above the
dispatch-pointer packet:

```text
PremapFutureKernelNativeConsumerArgSlotV1
  dispatch_ptr -> dispatch-ptr packet -> dispatch metadata -> launch params
```

This arg-slot packet models the mirror object a future kernel launcher would
bind as a typed native argument bundle.  It is still explicitly disconnected
from the current WNA16 kernel arguments:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

The lab schema now pins the arg-slot ABI metadata and numeric layout:

```text
abi_name = premap_future_kernel_native_consumer_arg_slot_abi_v1
mode = readonly_future_kernel_native_consumer_arg_slot_abi
source = premap_future_kernel_native_consumer_dispatch_ptr_abi_v1
slot_struct_size = 32
slot_struct_align = 8
offset(dispatch_ptr) = 0
offset(abi_version) = 8
offset(dispatch_ptr_struct_size) = 12
offset(result_struct_size) = 16
offset(payload_bytes) = 20
offset(flags) = 24
```

The online native-stub artifact checker now requires the arg-slot layer in the
dispatch stub summary.  It verifies:

```text
checked = true
version = 1
field mask covers descriptor_ptr / packed_weight_descriptor / scale_metadata_handle
single-field mirror field matches the expected canary field
row_count / row_ok_count == active dispatch rows
mirror row_count / row_ok_count == active dispatch rows
layout values match the pinned schema
payload/kernel-arg/WNA16 safety flags remain disabled
```

This closes the evidence gap where the runner internally checked arg-slot
rows but the independent artifact gate only enforced the dispatch-ptr layer.
The result is still a no-op readiness gate, not a WNA16 handoff or performance
claim.

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/check_premap_kernel_consumer_schema.py \
    configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml \
    --output-json outputs/reports/premap_kernel_consumer/schema_check_arg_slot_current.json

passed = true
failures = []

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_premap_kernel_consumer_schema.py \
    tests/test_check_premap_online_native_stub_canary_artifacts.py \
    tests/test_run_premap_online_native_stub_canary.py -q

58 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py \
    tests/test_premap_typed_consumer_stub.py -q

78 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

771 passed, 2 warnings
```

## 2026-06-01 -- Arg-slot nodefer artifact refreshed and flattened in lab status

The future native arg-slot ABI gate has now been refreshed with the existing
32 exported online inputs, without rerunning vLLM tracing:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_nodefer.json

artifact check:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_nodefer.json

preflight:
  outputs/reports/premap_lab_preflight_online_prelaunch_native_stub_canary_arg_slot_32input_nodefer.json

status:
  outputs/reports/premap_lab_preflight_status_online_prelaunch_native_stub_canary_arg_slot_32input_nodefer.json
```

Result:

```text
passed = true
artifact_check_passed = true
final_preflight_passed = true
final_deferred_count = 0
status_deferred_count = 0
online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_count = 31
online_prelaunch_input_extra_check_passed_count = 31
active dispatch rows = 174
arg-slot stub rows = 174 / 174
arg-slot mirror rows = 174 / 174
```

The refreshed artifact confirms the same safety boundary:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

Follow-up review found no blocker, but pointed out that the lab preflight
status flattened only the dispatch-ptr evidence and not the arg-slot evidence.
The status summary now also exposes arg-slot fields at the same lab-contract
level:

```text
default_kernel_consumer_arg_slot_abi_name
default_kernel_consumer_arg_slot_checked
default_kernel_consumer_arg_slot_row_count / row_ok_count
default_kernel_consumer_arg_slot_payload_bytes
default_kernel_consumer_arg_slot_passed_to_kernel
default_kernel_consumer_arg_slot_changes_kernel_launch_args
default_kernel_consumer_arg_slot_field_mask / required_field_mask
default_kernel_consumer_arg_slot_mirror_row_count / mirror_row_ok_count
default_kernel_consumer_arg_slot_slot_struct_size / align
default_kernel_consumer_arg_slot_offset_dispatch_ptr / offset_flags
```

The artifact checker tests now include dedicated arg-slot negative cases for
source mismatch, field-mask mismatch, and required-field-mask mismatch, in
addition to the existing safety-flag and layout mismatch checks.

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py \
    tests/test_check_premap_online_native_stub_canary_artifacts.py -q

91 passed
```

The default lab gate now points at the refreshed arg-slot 32-input nodefer
runner and artifact check:

```text
configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml

future_kernel_native_dispatch_consumer_online_runner_32_128export_json:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_arg_slot_32input_nodefer.json

future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:
  outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_nodefer.json
```

Final no-defer preflight:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  python scripts/run_premap_lab_preflight.py \
    --default-readonly-gate configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml \
    --canary-gate configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml \
    --output-json outputs/reports/premap_lab_preflight_status_default_arg_slot_32input_nodefer.json

passed = true
failures = []
runner path = outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_arg_slot_32input_nodefer.json
artifact path = outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_nodefer.json
online input count = 32
artifact final_deferred_count = 0
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
arg-slot rows = 174 / 174
arg-slot mirror rows = 174 / 174
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

This promotes the arg-slot runner from standalone evidence to the default lab
precondition while preserving the no-op boundary.

Review follow-up tightened the legacy `16_128export` evidence labels that now
reuse the same 32-input arg-slot runner/artifact.  The lab preflight minimum
input table now explicitly requires 32 online inputs for those labels too:

```text
native_typed_consumer_online_prelaunch_canary_runner_json
future_kernel_native_consumer_online_runner_16_128export_json
future_kernel_native_consumer_online_artifact_check_16_128export_json
future_kernel_native_launch_consumer_online_runner_16_128export_json
future_kernel_native_launch_consumer_online_artifact_check_16_128export_json
future_kernel_native_dispatch_consumer_online_runner_16_128export_json
future_kernel_native_dispatch_consumer_online_artifact_check_16_128export_json
future_kernel_native_dispatch_consumer_online_runner_32_128export_json
future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json
```

Final no-defer preflight after this tightening:

```text
output = outputs/reports/premap_lab_preflight_status_default_arg_slot_32input_nodefer_min32.json

passed = true
failures = []
runner_count = 32
artifact_min_online_inputs = 32
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
arg-slot rows = 174 / 174
passed_to_kernel = false
```

Standalone arg-slot native canary is now also part of the default lab gate.
This separates the future kernel argument-slot ABI check from the online
runner artifact and verifies the scale-metadata single-field mirror path in
the native stub itself:

```text
required evidence:
  future_kernel_native_arg_slot_standalone_canary_json

artifact:
  outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_arg_slot_standalone_canary.json

standalone rows = 1024 / 1024
single-field mirror = scale_metadata_handle
mirror rows = 1024 / 1024
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

Default lab preflight with the standalone arg-slot evidence:

```text
output = outputs/reports/premap_lab_preflight_status_default_arg_slot_standalone.json

passed = true
failures = []
required evidence = 15 / 15
standalone arg-slot evidence = passed
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py -q

56 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

776 passed, 2 warnings
```

Boundary remains unchanged: this is still a no-op future-kernel ABI gate.  It
does not move payload, does not issue ready credit, does not pass kernel args,
and does not reinterpret current WNA16 arguments.

Review follow-up tightened the standalone arg-slot validator:

```text
must enable exactly the scale_metadata mirror macro
must reject descriptor/packed/aux mirror macros in the same standalone canary
must reject no-op boundary violations such as passed_to_kernel=true
```

Updated validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py -q

58 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

778 passed, 2 warnings

output = outputs/reports/premap_lab_preflight_status_default_arg_slot_standalone_strict.json
passed = true
failures = []
required evidence = 15 / 15
standalone arg-slot rows = 1024 / 1024
passed_to_kernel = false
```

The flattened lab status now labels the two arg-slot evidence sources
explicitly:

```text
default_kernel_consumer_arg_slot_status_source =
  online_dispatch_runner_summary

default_kernel_consumer_arg_slot_standalone_status_source =
  standalone_native_stub_artifact
```

This keeps the 32-input online runner evidence and the standalone native
arg-slot canary evidence distinguishable in downstream status dashboards.

A second field was added as optional diagnostic evidence for the same arg-slot
ABI path:

```text
optional evidence:
  future_kernel_native_arg_slot_packed_weight_mirror_canary_json

artifact:
  outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_arg_slot_packed_weight_mirror_canary.json

field = packed_weight_descriptor
standalone rows = 1024 / 1024
mirror rows = 1024 / 1024
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

Default preflight with this optional evidence:

```text
output = outputs/reports/premap_lab_preflight_status_default_arg_slot_packed_weight_optional.json
passed = true
failures = []
required evidence = 15 / 15
optional evidence = 11 / 11
```

This is intentionally optional/diagnostic.  The lab default precondition still
requires the scale-metadata standalone arg-slot canary; packed-weight mirror is
tracked as the next field-level canary without expanding the required gate.

Aux metadata was added to the same optional arg-slot diagnostic lane:

```text
optional evidence:
  future_kernel_native_arg_slot_aux_metadata_mirror_canary_json

artifact:
  outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_arg_slot_aux_metadata_mirror_canary.json

field = aux_metadata_handle
standalone rows = 1024 / 1024
mirror rows = 1024 / 1024
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false

output = outputs/reports/premap_lab_preflight_status_default_arg_slot_aux_optional.json
passed = true
failures = []
required evidence = 15 / 15
optional evidence = 12 / 12
```

With this, the default lab gate requires scale-metadata arg-slot evidence and
tracks packed-weight plus aux-metadata arg-slot evidence as optional field-level
canaries.

Descriptor pointer was added as the final optional arg-slot diagnostic field:

```text
optional evidence:
  future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json

artifact:
  outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_arg_slot_descriptor_ptr_mirror_canary.json

field = descriptor_ptr
standalone rows = 1024 / 1024
mirror rows = 1024 / 1024
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false

output = outputs/reports/premap_lab_preflight_status_default_arg_slot_all_fields_optional.json
passed = true
failures = []
required evidence = 15 / 15
optional evidence = 13 / 13
```

The future native arg-slot ABI now has field coverage for all four handle
columns:

```text
required:
  scale_metadata_handle

optional diagnostic:
  descriptor_ptr
  packed_weight_descriptor
  aux_metadata_handle
```

The lab preflight summary now exposes arg-slot mirror field coverage explicitly,
so the online runner status cannot be mistaken for all-field online mirror
coverage:

```text
output = outputs/reports/premap_lab_preflight_status_arg_slot_coverage.json
passed = true

online runner mirror coverage:
  scale_metadata_handle
  full_field_mirror_coverage = false

online runner diagnostic dispatch coverage:
  descriptor_ptr
  packed_weight_descriptor
  aux_metadata_handle

online runner total coverage:
  descriptor_ptr
  packed_weight_descriptor
  scale_metadata_handle
  aux_metadata_handle
  full_field_mirror_coverage = true

standalone required coverage:
  scale_metadata_handle
  full_field_mirror_coverage = false

standalone optional diagnostic coverage:
  descriptor_ptr
  packed_weight_descriptor
  aux_metadata_handle

total standalone coverage:
  descriptor_ptr
  packed_weight_descriptor
  scale_metadata_handle
  aux_metadata_handle
  full_field_mirror_coverage = true
```

This preserves the current gate semantics: the online dispatch runner's primary
arg-slot status still mirrors only the safest scale metadata field, while its
diagnostic dispatch summaries and standalone native stub artifacts cover the
remaining fields. No payload is moved, no kernel launch argument is changed,
and no current WNA16 argument is reinterpreted.

The online total mirror coverage is now a strict no-defer lab preflight
condition.  A missing descriptor/packed-weight/aux diagnostic dispatch summary
fails the lab gate instead of only lowering a reporting field:

```text
required failure:
  default_kernel_consumer_arg_slot_online_total_mirror_coverage_incomplete

output = outputs/reports/premap_lab_preflight_status_arg_slot_online_coverage_required.json
passed = true
failures = []
contract:
  future_kernel_native_arg_slot_online_total_mirror_coverage_required = true
online total coverage:
  descriptor_ptr
  packed_weight_descriptor
  scale_metadata_handle
  aux_metadata_handle
  full_field_mirror_coverage = true

validation:
  conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q
  780 passed, 2 warnings
```

This makes the default lab gate stricter while preserving the bootstrap boundary:
stage-1/deferred runner preflight can still defer self-evidence, but final
strict no-defer lab preflight requires full online arg-slot mirror coverage.

The latest standalone future native arg-slot canary is now machine-checked by
the lab artifact checker instead of being read manually from the JSON output:

```text
canary =
  outputs/reports/premap_kernel_consumer/
    typed_consumer_stub_gpu1_future_native_arg_slot_full_guard_scale_canary_latest.json

checker =
  outputs/reports/premap_kernel_consumer/
    typed_consumer_stub_gpu1_future_native_arg_slot_full_guard_scale_canary_latest.check.json

passed = true
row_count / row_ok_count = 1024 / 1024
arg_slot_row_count / arg_slot_row_ok_count = 1024 / 1024
expected mirror field = scale_metadata_handle
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false

required compiled macros:
  schema / row_iteration / pointer_visibility
  descriptor_ptr / packed_weight_descriptor / scale_metadata_handle / aux_metadata_handle
  lifetime / hash_accumulator
  future_native consumer / launch / dispatch / dispatch_ptr / arg_slot ABI
  scale_metadata mirror field

validation:
  conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
    pytest tests/test_check_premap_online_native_stub_canary_artifacts.py -q
  42 passed

  conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q
  791 passed, 2 warnings
```

This closes the gap between the standalone native typed consumer canary and the
online lab gate checker: the future arg-slot ABI evidence must now carry the
expected compile-time guard set and still prove that it is readonly, non-payload,
not passed to the current WNA16 kernel, and not current-WNA16-arg compatible.
The standalone checker keeps the default artifact strict, but its field macro
requirement is now tied to `expected_field_name`, so descriptor/packed-weight/
auxiliary single-field canaries can be checked without pretending that every
handle field macro was enabled.  The checker also hard-fails if the top-level
artifact ever reports nonzero payload bytes, kernel handoff, kernel launch
argument changes, or current-WNA16 argument compatibility.
The default lab preflight standalone-evidence validator now uses the same
field-aware macro rule for arg-slot canaries, so optional descriptor,
packed-weight, and auxiliary mirror artifacts are not forced to enable unrelated
handle macros, but each must still enable the handle macro for the field it
claims to mirror.

The default lab preflight still passes after the macro alignment:

```text
output =
  outputs/reports/premap_lab_preflight_default_after_arg_slot_macro_alignment.json

passed = true
failures = []
default_kernel_consumer_arg_slot_online_total_full_field_mirror_coverage = true
default_kernel_consumer_arg_slot_total_full_field_mirror_coverage = true

focused validation:
  conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
    pytest tests/test_run_premap_lab_preflight.py \
           tests/test_check_premap_online_native_stub_canary_artifacts.py -q
  108 passed
```

All four standalone future native arg-slot mirror artifacts now have machine
checker outputs under the same readonly/no-kernel-arg contract:

```text
scale:
  typed_consumer_stub_gpu1_future_native_arg_slot_full_guard_scale_canary_latest.check.json
descriptor_ptr:
  typed_consumer_stub_gpu1_future_native_arg_slot_descriptor_ptr_mirror_canary.check.json
packed_weight_descriptor:
  typed_consumer_stub_gpu1_future_native_arg_slot_packed_weight_mirror_canary.check.json
aux_metadata_handle:
  typed_consumer_stub_gpu1_future_native_arg_slot_aux_metadata_mirror_canary.check.json

all four:
  passed = true
  row_count = 1024
  arg_slot_row_count = 1024
  payload_bytes = 0
  passed_to_kernel = false
  current_wna16_arg_compatible = false
```

## 2026-06-01 - Online prelaunch native stub canary refreshed with 32 inputs

The four-field readonly/native gate is now exercised through the online
prelaunch typed-consumer input path, not just standalone artifacts.  The runner
exports typed prelaunch inputs from the vLLM/AWQ trace and feeds them through
the native typed consumer stub suite, including the future native consumer,
launch, dispatch, and arg-slot ABI paths.  This remains a no-op integration:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current WNA16 kernel args are not modified
```

Artifacts:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_nodefer.json

artifact checker:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_nodefer.json

final default preflight:
  outputs/reports/
    premap_lab_preflight_default_after_online_arg_slot_32input_refresh.json
```

Result:

```text
runner passed = true
runner failures = []
online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_count = 31
online_prelaunch_input_extra_check_passed_count = 31

artifact checker passed = true
artifact checker failures = []
min_online_inputs = 32
final_deferred_count = 0
status_deferred_count = 0

future native dispatch arg-slot row_count / row_ok_count = 174 / 174
future native dispatch arg-slot mirror row_count / row_ok_count = 174 / 174

final strict default lab preflight:
  passed = true
  failures = []
  runtime_gate_evidence_deferred_count = 0
  strict_default_gate_evidence_deferred_count = 0
  bootstrap_preflight_allowed = false
  online_runner_self_finalization_allowed = false
```

During the refresh, the runner exposed a self-referential gate ordering issue:
the final no-defer preflight expected the runner JSON to already contain the
final artifact-check and final-preflight summaries, while the runner could only
write those summaries after running the checks.  The fix makes the sequence
explicit:

```text
1. stage-1 bootstrap preflight may defer only runner/artifact self-evidence;
2. self-finalization preflight may read the bootstrap artifact summary only to
   let the runner write its final preflight summary;
3. final artifact check runs against that runner JSON;
4. final strict preflight reruns with no defer and no self-finalization escape.
```

Only step 4 is accepted as the lab gate.  The final status above confirms that
the online prelaunch native stub canary is now a strict no-defer lab preflight
condition while still staying readonly and disconnected from the WNA16 launch
arguments.

Review hardening:

```text
--allow-online-runner-self-finalization is accepted only when the runner
artifact carries artifact_check_bootstrap_summary.bootstrap_preflight_allowed=true.

Normal/default lab preflight does not enable this flag and still requires
final_preflight_status_summary plus final_deferred_count=0.
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests/test_run_premap_lab_preflight.py \
         tests/test_run_premap_online_native_stub_canary.py \
         tests/test_check_premap_online_native_stub_canary_artifacts.py -q
121 passed

conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src pytest tests -q
793 passed, 2 warnings
```

### Online prelaunch native arg-slot summary refresh

Refreshed the 32-input online prelaunch native stub canary after exposing the
future native dispatch arg-slot summaries at the runner top level.

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_alias_nodefer.json

artifact checker:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_alias_nodefer.json
```

Result:

```text
runner passed = true
runner failures = []
online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_passed_count = 31

top-level future native dispatch arg-slot summary:
  row_count = 174
  mirror_row_count = 174

top-level future native dispatch arg-slot mirror summary:
  row_count = 174
  mirror_row_count = 174

artifact checker passed = true
artifact checker failures = []
min_online_inputs = 32
final_deferred_count = 0
status_deferred_count = 0
bootstrap_preflight_allowed = false
```

Here `row_count` and `mirror_row_count` are the readable summary names for the
runner JSON keys `future_kernel_native_arg_slot_consumer_row_count` and
`future_kernel_native_arg_slot_consumer_single_field_mirror_row_count`.
They apply to each top-level summary projection above: the arg-slot summary and
the arg-slot mirror summary each carry their own row/mirror counts.

This does not change the safety boundary: the canary still runs only the
readonly native checker/stub path, keeps payload bytes at zero, and does not
pass or reinterpret WNA16 kernel arguments.  The value is observability: the
future kernel argument slot is now visible as a first-class runner summary in
addition to the nested dispatch-stub payload.

### Online native canary row-stats lab gate

The online prelaunch native stub canary now records the row-count distribution
across the selected online exported typed-consumer inputs, and the artifact
checker validates that distribution before the artifact can satisfy the default
lab gate.

New default runner/artifact:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_alias_rowstats_nodefer.json

artifact checker:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_alias_rowstats_nodefer.json
```

Strict checker result:

```text
passed = true
failures = []
online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_passed_count = 31

online input row_count:
  min = 8
  max = 198
  sum = 1841
  diverse = true

arg-slot projection rows = 174
arg-slot mirror projection rows = 174
final_deferred_count = 0
status_deferred_count = 0
```

The checker now rejects multi-input artifacts that omit row counts, report
non-integer or non-positive row counts, mismatch min/max/sum, or use multiple
inputs with only a single row-count shape.  This turns the 32-input canary from
"many inputs passed" into "many inputs with varied handle-table shapes passed."

Default preflight with the row-stats artifact:

```text
passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
default_kernel_consumer_dispatch_runner_artifact_check_passed = true
default_kernel_consumer_dispatch_runner_artifact_check_min_online_inputs = 32
default_kernel_consumer_dispatch_runner_artifact_check_final_deferred_count = 0
```

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

798 passed, 2 warnings
```

Follow-up lab preflight hardening:

```text
default lab preflight now also requires/exposes:
  default_kernel_consumer_dispatch_runner_artifact_check_row_count_min = 8
  default_kernel_consumer_dispatch_runner_artifact_check_row_count_max = 198
  default_kernel_consumer_dispatch_runner_artifact_check_row_count_sum = 1841
  default_kernel_consumer_dispatch_runner_artifact_check_row_count_diverse = true

default preflight:
  outputs/reports/premap_lab_preflight_default_after_rowstats_summary_fields.json

passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
```

The canary runner now also writes its own top-level
`online_prelaunch_input_row_count_diverse` field, so runner output, artifact
checker output, and lab preflight status use the same row-shape diversity
contract.

The artifact checker also exposes the raw 32-entry row-count list, and lab
preflight recomputes min/max/sum/diverse from that list.  This prevents a
tampered or stale artifact summary from satisfying the default gate with an
incorrect `row_count_sum`.

Validation:

```text
conda run -p /home/husrcf/anaconda3/envs/TRY env PYTHONPATH=.:src \
  pytest tests -q

800 passed, 2 warnings
```

Safety boundary unchanged:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

Tail-window native consumer side artifact:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_4input_tail8_probe.json

checker:
  scripts/check_premap_native_stub_tail_window_probe.py

checker output:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_4input_tail8_probe_check.json

stronger side probe:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_8input_tail8_probe.json

stronger side probe check:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_8input_tail8_probe_check.json

passed = true
tail_window_size = 8
online inputs = 4
input row counts = [174, 190, 106, 187]
row_count_diverse = true

8-input check:
  passed = true
  input row counts = [174, 190, 106, 187, 139, 134, 175, 189]
  row_count_min/max/sum = 106 / 190 / 1294
  row_count_diverse = true

16-input mixed-size check:
  runner:
    outputs/reports/premap_kernel_consumer/
      online_prelaunch_native_stub_canary_arg_slot_16input_tail8_probe.json
  checker output:
    outputs/reports/premap_kernel_consumer/
      online_prelaunch_native_stub_canary_arg_slot_16input_tail8_probe_check.json
  passed = true
  input row counts = [174, 190, 106, 187, 139, 134, 175, 189,
                      173, 198, 8, 8, 8, 8, 8, 8]
  row_count_min/max/sum = 8 / 198 / 1713
  row_count_diverse = true
  tail_windowed_input_count = 10
  extra_online_input_tail_window_check_count = 15

32-input mixed-size check:
  runner:
    outputs/reports/premap_kernel_consumer/
      online_prelaunch_native_stub_canary_arg_slot_32input_tail8_probe.json
  checker output:
    outputs/reports/premap_kernel_consumer/
      online_prelaunch_native_stub_canary_arg_slot_32input_tail8_probe_check.json
  passed = true
  input row counts = [174, 190, 106, 187, 139, 134, 175, 189,
                      173, 198, 8, 8, 8, 8, 8, 8,
                      8, 8, 8, 8, 8, 8, 8, 8,
                      8, 8, 8, 8, 8, 8, 8, 8]
  row_count_min/max/sum = 8 / 198 / 1841
  row_count_diverse = true
  tail_windowed_input_count = 10
  extra_online_input_tail_window_check_count = 31
  checker min_tail_windowed_inputs = 10

dispatch input rows:
  scale_metadata_handle = 174
  descriptor_ptr = 174
  packed_weight_descriptor = 174
  aux_metadata_handle = 174

dispatch/dispatch_ptr/arg-slot active rows:
  scale_metadata_handle = 8
  descriptor_ptr = 8
  packed_weight_descriptor = 8
  aux_metadata_handle = 8
```

The checker now rejects:

```text
summary row_count not matching the online input row count
cross-field row_count / offset / limit / active-row mismatch
requires_wna16_arg_reinterpretation = true
non-diverse multi-input row-count evidence when requested
```

The 8-input checker also validates every `extra_online_input_check_summaries`
entry, not just the top-level first input:

```text
extra_online_input_tail_window_check_count = 7
```

The 16-input checker extends this to mixed-size online inputs.  Inputs with
`row_count > tail_window_size` must consume exactly the tail window, while
inputs with `row_count <= tail_window_size` consume their full table with the
same offset/limit/active-row formula.  This prevents the side artifact from
rejecting valid small prepared tables while still requiring real tail-window
coverage through `min_tail_windowed_inputs`.

The checker defaults are intentionally conservative for this side artifact:
`min_tail_windowed_inputs=4` and row-count diversity is required unless a caller
explicitly opts out with `--allow-uniform-row-counts`.  The 16-input artifact
above was checked with `--min-tail-windowed-inputs 8`, and 10 inputs actually
exercised the tail-window path.

Default lab preflight after the 32-input side probe:

```text
outputs/reports/premap_lab_preflight_default_after_tail_window_side_probe.json

passed = true
default_contract_passed = true
default_kernel_consumer_dispatch_full_table_required = true
default_kernel_consumer_dispatch_full_table_checked = true
default_kernel_consumer_arg_slot_online_total_full_field_mirror_coverage = true
default_kernel_consumer_arg_slot_passed_to_kernel = false
default_kernel_consumer_arg_slot_changes_kernel_launch_args = false
default_kernel_consumer_arg_slot_current_wna16_arg_compatible = false
default_kernel_consumer_arg_slot_requires_wna16_arg_reinterpretation = false
```

This confirms the tail-window side evidence does not replace or weaken the
default full-table lab gate.

This is intentionally not the default lab gate yet.  The default preflight
continues to require full-table coverage.  The tail-window artifact proves the
future kernel-side ABI can consume a row-window slice of the prepared handle
table while preserving the no-op boundary:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

### Packet-chain visibility restored in the default lab gate

The future native ABI runner now carries packet-chain visibility fields through
the compact online runner summary, not only through the full native stub JSON.
This matters because the lab preflight checks the runner/artifact evidence, not
just standalone HIP stub outputs.

Fixes in this gate:

```text
dispatch-ptr-only standalone builds no longer reference the arg-slot object
unless MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI
is enabled.

online runner summaries now include:
  future_kernel_native_dispatch_ptr_consumer_packet_visible
  future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible
  future_kernel_native_dispatch_ptr_consumer_packet_chain_depth
  future_kernel_native_arg_slot_consumer_slot_visible
  future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible
  future_kernel_native_arg_slot_consumer_dispatch_packet_visible
  future_kernel_native_arg_slot_consumer_packet_chain_depth
```

Refreshed evidence:

```text
outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_dispatch_ptr_standalone_canary.json
outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_arg_slot_standalone_canary.json
outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_arg_slot_descriptor_ptr_mirror_canary.json
outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_arg_slot_packed_weight_mirror_canary.json
outputs/reports/premap_kernel_consumer/typed_consumer_stub_gpu1_future_native_arg_slot_aux_metadata_mirror_canary.json
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_arg_slot_32input_alias_rowstats_nodefer.json
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_alias_rowstats_nodefer.json
outputs/reports/premap_lab_preflight_default_after_packet_chain_visibility.json
```

Final default lab preflight:

```text
passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
required_evidence = 15 / 15 passed
optional_evidence = 13 / 13 passed
online runner inputs = 32
extra online input checks = 31 / 31 passed
artifact check passed = true
```

Safety boundary remains unchanged:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

### Packet-chain mirror hash equivalence

The future native dispatch, dispatch-pointer packet, and arg-slot packet now
must expose valid path-specific row hash accumulators and identical
single-field mirror hash accumulators in the online runner/artifact gate.  This
tightens the packet-chain evidence from "the packets are visible" to "each
packet layer sees the same mirrored handle field while keeping its own
ABI-specific row hash."

Checked requirements:

```text
future_kernel_native_dispatch_consumer_hash_accumulator is valid hex64
future_kernel_native_dispatch_ptr_consumer_hash_accumulator is valid hex64
future_kernel_native_arg_slot_consumer_hash_accumulator is valid hex64

future_kernel_native_dispatch_consumer_single_field_mirror_hash_accumulator
== future_kernel_native_dispatch_ptr_consumer_single_field_mirror_hash_accumulator
== future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator
```

The full row hashes intentionally remain path-specific because they include
ABI-wrapper metadata for dispatch, dispatch pointer, and arg-slot packets.  The
single-field mirror hash is the cross-packet equivalence check for handle-field
visibility.

This remains a readonly future-kernel ABI check only:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

Refreshed evidence:

```text
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_arg_slot_32input_alias_rowstats_hashchain_nodefer.json
outputs/reports/premap_kernel_consumer/online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_alias_rowstats_hashchain_nodefer.json
outputs/reports/premap_lab_preflight_default_after_packet_chain_hash_equivalence.json
```

Gate result:

```text
online runner passed = true
artifact_check_passed = true
final_preflight_passed = true
online inputs = 32
extra online input checks = 31 / 31 passed
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
required_evidence = 15 / 15 passed
optional_evidence = 13 / 13 passed
```

### Packet-chain handle-projection hash equivalence

The packet-chain hash gate now also validates an ABI-independent full-row handle
projection across the future native dispatch, dispatch-pointer packet, and
arg-slot packet:

```text
future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator
== future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator
== future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator
```

This projection intentionally excludes ABI/packet wrapper metadata and hashes
only the typed row handle view:

```text
descriptor_ptr
packed_weight_descriptor
scale_metadata_handle
aux_metadata_handle
address_key_hash
expert_id
row_index
```

The distinction is important:

```text
path-specific row hash accumulator:
  must be present and valid, but may differ by packet shape

single-field mirror hash accumulator:
  must match across dispatch -> dispatch_ptr -> arg_slot

handle-projection hash accumulator:
  must match across dispatch -> dispatch_ptr -> arg_slot
```

Standalone GPU1 native-stub smoke:

```text
outputs/reports/premap_kernel_consumer/
  typed_consumer_stub_gpu1_future_native_arg_slot_handle_projection_smoke.json

row_count = 16
dispatch / dispatch_ptr / arg_slot row_ok_count = 16 / 16 / 16
handle_projection_hash_accumulator = 9eac876e3b41938b on all three packet paths
payload_bytes = 0
passed_to_kernel = false
current_wna16_arg_compatible = false
```

Refreshed 32-input online prelaunch canary:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_arg_slot_32input_alias_rowstats_hashchain_projection_nodefer.json
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_alias_rowstats_hashchain_projection_nodefer.json

online runner passed = true
artifact_check_passed = true
stdout final_preflight_passed = true
stdout final_deferred_count = 0
online inputs = 32
extra online input checks = 31 / 31 passed

dispatch handle_projection_hash_accumulator = 877da3c93286127c
dispatch_ptr handle_projection_hash_accumulator = 877da3c93286127c
arg_slot handle_projection_hash_accumulator = 877da3c93286127c

dispatch row hash accumulator = b85d3491976eca34
dispatch_ptr row hash accumulator = 50685f4a0fd6f707
arg_slot row hash accumulator = a8bb5d2ff3a6e662
```

The differing row hashes confirm that the checker still treats packet-specific
row hashes as ABI-local evidence.  The matching handle-projection hashes confirm
that all three packet layers read the same typed descriptor/address handle row
view.  Boundary remains unchanged: no payload transfer, no ready credit, and no
current WNA16 kernel-argument mutation.

Default lab preflight refresh:

```text
outputs/reports/premap_lab_preflight_default_after_handle_projection_hashchain.json

passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
payload_bytes_required = 0
passed_to_kernel_required = false
```

The default lab gate evidence paths were then promoted from the older
`rowstats_nodefer` canary to the handle-projection artifact:

```text
configs/runtime/
  premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml

required runner evidence =
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_alias_rowstats_hashchain_projection_nodefer.json

required artifact-check evidence =
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_alias_rowstats_hashchain_projection_nodefer.json
```

Refreshed default lab preflight:

```text
outputs/reports/premap_lab_preflight_default_requires_handle_projection_hashchain.json

passed = true
runner evidence path = ...hashchain_projection_nodefer.json
artifact evidence path = ...hashchain_projection_nodefer.json
artifact_check_passed = true
online inputs = 32
extra online input checks = 31 / 31 passed
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
```

Additional nonzero row-window canary:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_arg_slot_tail8_4input_hashchain_projection_nodefer.json
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_artifact_check_arg_slot_tail8_4input_hashchain_projection_nodefer.json

online runner passed = true
artifact_check_passed = true
stdout final_preflight_passed = true
stdout final_deferred_count = 0
online inputs = 4
extra online input checks = 3 / 3 passed

dispatch row_count = 8
dispatch row_offset = 166
dispatch row_limit = 174
dispatch active_rows = 8

dispatch handle_projection_hash_accumulator = 625adc96bd325030
dispatch_ptr handle_projection_hash_accumulator = 625adc96bd325030
arg_slot handle_projection_hash_accumulator = 625adc96bd325030
```

This verifies the same packet-chain projection contract on a nonzero tail
dispatch window, which is closer to how a future kernel-side consumer would
iterate a row slice.  It is recorded as supplemental evidence for now; the
default required lab gate remains the 32-input full-table projection canary.

Standalone multi-program native-stub canary:

```text
outputs/reports/premap_kernel_consumer/
  typed_consumer_stub_gpu1_future_native_arg_slot_multiprogram_handle_projection_canary.json

passed = true
row_count = 520
dispatch grid_x = 3
dispatch block_x = 256
dispatch program_count = 3
dispatch full_program_count = 2
dispatch last_program_active_rows = 8
dispatch inactive_lane_count = 248

dispatch handle_projection_hash_accumulator = 12201358096b98ac
dispatch_ptr handle_projection_hash_accumulator = 12201358096b98ac
arg_slot handle_projection_hash_accumulator = 12201358096b98ac

dispatch row_ok_count = 520
dispatch_ptr row_ok_count = 520
arg_slot row_ok_count = 520
payload_bytes = 0
passed_to_kernel = false
current_wna16_arg_compatible = false
```

This is synthetic rather than online-vLLM evidence, but it exercises the future
native dispatch geometry beyond a single block/program.  It confirms the
packet-chain consumer can iterate the same typed handle projection over a
multi-program row assignment without changing the current kernel boundary.

Default preflight summary now exposes and enforces the hashchain state
directly:

```text
outputs/reports/premap_lab_preflight_default_projection_hashchain_summary_fields.json
outputs/reports/premap_lab_preflight_default_projection_hashchain_hard_gate.json

passed = true
default_kernel_consumer_dispatch_runner_row_hashchain_all_valid = true
default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal = true

dispatch row hash = b85d3491976eca34
dispatch_ptr row hash = 50685f4a0fd6f707
arg_slot row hash = a8bb5d2ff3a6e662

dispatch handle projection hash = 877da3c93286127c
dispatch_ptr handle projection hash = 877da3c93286127c
arg_slot handle projection hash = 877da3c93286127c
```

This keeps the summary faithful to the contract: row hashes are path-local
packet evidence, while handle-projection hashes are cross-packet equivalence
evidence.

The default no-defer lab gate now fails if the dispatch / dispatch_ptr /
arg_slot row hashchain is not valid hex64 evidence, or if the typed-handle
projection hash is not equal across those packet boundaries.  Focused tests
cover both failure cases so this cannot silently regress into summary-only
observability.

32-input online prelaunch native-stub canary with the hard hashchain preflight
gate:

```text
outputs/reports/premap_kernel_consumer/
  online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json
  online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_hard_hashchain_preflight_32tables.json

runner passed = true
artifact_check passed = true
failures = []
online_prelaunch_input_check_count = 32
online_prelaunch_input_extra_check_passed_count = 31 / 31
online row_count min/max/diverse = 8 / 198 / true

final strict preflight passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
required evidence = 15 / 15
optional evidence = 13 / 13

dispatch rows / ok = 174 / 174
arg_slot rows / ok = 174 / 174

dispatch row hash = b85d3491976eca34
dispatch_ptr row hash = 50685f4a0fd6f707
arg_slot row hash = a8bb5d2ff3a6e662

dispatch / dispatch_ptr / arg_slot handle-projection hash =
  877da3c93286127c

arg_slot payload_bytes = 0
arg_slot passed_to_kernel = false
arg_slot changes_kernel_launch_args = false
```

This promotes the future-native dispatch/arg-slot path from single-table
online evidence to a 32-table online prelaunch canary under the same strict
no-defer lab gate.  It still does not hand the typed table to the current
WNA16 kernel and it does not move payload.

Default lab preflight now requires the multi-program future-native arg-slot
canary as part of the strict lab precondition:

```text
outputs/reports/premap_lab_preflight_default_required_multiprogram_gate.json

passed = true
required evidence = 16 / 16
optional evidence = 13 / 13

future_kernel_native_arg_slot_multiprogram_canary_json:
  present = true
  passed = true
  path = outputs/reports/premap_kernel_consumer/
    typed_consumer_stub_gpu1_future_native_arg_slot_multiprogram_handle_projection_canary.json
```

The canary is content-checked rather than treated as a loose
`passed=true` artifact.  It must satisfy the arg-slot no-op safety contract,
multi-program dispatch geometry, program-iteration hash validation, and
dispatch / dispatch_ptr / arg_slot handle-projection hash equality.  The
current artifact uses a mirror-only scale-metadata field check, so the
multi-program validator does not require the raw scale-metadata handle macro;
the existing required single-program arg-slot gate remains strict.

Review tightened the multi-program geometry validation before commit: the
required evidence now fails if launch-thread metadata is missing, if the active
row window does not match the full table, if the launch is under-covered or
non-minimal, or if `full_program_count`, `last_program_active_rows`,
`inactive_lane_count`, first/last program row offsets, or the
program-iteration hash disagree with the row assignment formula.  Focused
tests cover the single-program, missing-launch-threads, and bad-full-program
failure modes.  Additional regression coverage keeps the legacy
`*_16_128export` launch labels tied to the same 32-table hard-hashchain
artifact and verifies that `--allow-missing-evidence` marks missing required
multi-program evidence as allowed-missing rather than silently passing it as
present.

## 2026-06-02 - online-merged future arg-slot mirror-field canaries

The online prelaunch native-stub evidence can now be merged into a single
future-native arg-slot table and checked with a selectable one-field mirror:

```text
script:
  scripts/run_premap_online_merged_native_arg_slot_canary.py

input:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json

merged table:
  outputs/reports/premap_kernel_consumer/
    online_merged_prelaunch_typed_consumer_input_arg_slot_32tables.json
```

The default lab evidence remains the full-table `scale_metadata_handle`
mirror.  The runner now also supports explicit `--mirror-field` selection for
`descriptor_ptr`, `packed_weight_descriptor`, and `aux_metadata_handle`, so
field-level canaries can be run without changing the current WNA16 launch ABI.

GPU1 tail-window and full-table canaries passed for the remaining three fields:

```text
tail dispatch window:
  row_offset = 1792
  row_limit = 1841
  active_rows = 49
  expected_program_count = 1
  block_threads = 256

full-table dispatch window:
  row_offset = 0
  row_limit = 1841
  active_rows = 1841
  expected_program_count = 8
  block_threads = 256

descriptor_ptr:
  tail runner = outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_tail_window49_descriptor_ptr_canary_runner.json
  full runner = outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_32tables_descriptor_ptr_canary_runner.json
  tail rows / ok = 49 / 49
  full rows / ok = 1841 / 1841

packed_weight_descriptor:
  tail runner = outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_tail_window49_packed_weight_canary_runner.json
  full runner = outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_32tables_packed_weight_canary_runner.json
  tail rows / ok = 49 / 49
  full rows / ok = 1841 / 1841

aux_metadata_handle:
  tail runner = outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_tail_window49_aux_metadata_canary_runner.json
  full runner = outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_32tables_aux_metadata_canary_runner.json
  tail rows / ok = 49 / 49
  full rows / ok = 1841 / 1841
```

All three runs preserve the strict no-op contract:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

This does not make the existing WNA16 kernel consume the typed table.  It only
shows that the future-native dispatch / dispatch_ptr / arg-slot consumer path
can read each typed schema field through the same online-derived row window
without payload movement or kernel-argument mutation.

The three full-table non-default mirror runners are now optional lab preflight
evidence:

```text
outputs/reports/premap_lab_preflight_default_with_online_merged_mirror_optional.json

passed = true
required evidence = 18 / 18
optional evidence = 16 / 16

online-merged optional mirror coverage:
  aux_metadata_handle
  descriptor_ptr
  packed_weight_descriptor
```

The required default full-table runner still uses `scale_metadata_handle`;
the new optional entries only add stricter field-level evidence for the
future-native typed ABI and do not change the no-op lab gate boundary.

## 2026-06-02 - Future kernel args ABI layout pinned

The future kernel-side consumer args packet is now layout-pinned as an explicit
ABI contract rather than just a Python-side summary object.  The native typed
consumer stub reports the `PremapFutureKernelSideConsumerArgsV1` size, alignment,
result size/alignment, and field offsets for:

```text
envelope
field_mask
single_field_mirror_kind
payload_bytes
flags
```

The schema checker, online canary artifact checker, lab preflight checker, and
runner tests now require this layout evidence.  The current pinned layout is:

```text
args struct size / align = 160 / 8
result struct size / align = 56 / 8
offset(envelope) = 0
offset(field_mask) = 144
offset(single_field_mirror_kind) = 148
offset(payload_bytes) = 152
offset(flags) = 156
```

The refreshed GPU1 32-input online prelaunch native-stub canary passes with
strict no-defer evidence:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json

artifact check:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_hard_hashchain_preflight_32tables.json

passed = true
artifact_check_passed = true
final_preflight_passed = true
online inputs = 32
extra input checks = 31 / 31
final_deferred_count = 0
status_deferred_count = 0
```

The default lab preflight also passes with no deferred evidence:

```text
outputs/reports/premap_lab_preflight_default_with_projection_coverage.json

passed = true
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
payload_bytes_required = 0
passed_to_kernel_required = false
changes_kernel_launch_args_required = false
```

This is still a no-op bridge toward a future kernel ABI.  It does not pass
typed table handles into the current WNA16 kernel, does not move payload, and
does not reinterpret the existing WNA16 kernel argument layout.

## 2026-06-02 - Future-native row-window canary

The future-native typed consumer stub now has an independent middle-window
canary for the dispatch / dispatch-ptr / arg-slot ABI path.  This verifies that
the native bridge can consume a row subset rather than only full-table inputs:

```text
artifact:
  outputs/reports/premap_kernel_consumer/
    typed_consumer_stub_gpu1_future_native_arg_slot_middle_window32_96_input0.json

requested_dispatch_row_offset = 32
requested_dispatch_row_limit = 96
future_kernel_native_dispatch_consumer_active_rows = 64
future_kernel_native_dispatch_consumer_launch_covers_active_rows = true
future_kernel_native_dispatch_consumer_launch_minimal_cover = true
future_kernel_native_dispatch_consumer_program_iteration_checked = true
future_kernel_native_dispatch_ptr_consumer_row_count = 64
future_kernel_native_arg_slot_consumer_row_count = 64
single_field_mirror = scale_metadata_handle
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

The online native-stub canary runner now also guards its optional
`MTP_PREMAP_REUSE_EXISTING_STUB_OUTPUTS=1` fast path: existing stub outputs are
reused only when their `requested_dispatch_row_offset` and
`requested_dispatch_row_limit` match the current command.  Legacy outputs
without explicit dispatch-window evidence are rejected and rerun.  This prevents
full-table artifacts from being accidentally reused as row-window evidence.

## 2026-06-02 - Merged online arg-slot canary

The future-native arg-slot ABI now has a merged online canary that combines 32
online prelaunch typed-consumer exports into one multiprogram row stream and
feeds it to the native stub:

```text
full merged artifact:
  outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_canary_runner_32input_gpu1.json

tail-window artifact:
  outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_canary_runner_32input_tail512_gpu1.json

selected sources = 32
merged row count = 1841
full dispatch active rows = 1841
tail dispatch window = rows [1329, 1841)
tail dispatch active rows = 512
handle projection hashchain equal = true
all handle fields projected = true
single_field_mirror = scale_metadata_handle
tail one-field mirrors also passed =
  descriptor_ptr
  packed_weight_descriptor
  aux_metadata_handle
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

This remains diagnostic evidence rather than a real vLLM launch table.  It
shows that the future typed ABI can iterate a real online-derived row stream
across multiple native programs, including a bounded tail window, without
touching WNA16 kernel arguments or dereferencing payload.

The compact lab preflight status now also exposes the required online-merged
multiprogram runner fields directly:

```text
artifact:
  outputs/reports/
    premap_lab_preflight_default_with_online_merged_summary_fields.json

passed = true
online_merged evidence passed = true
source_count = 32
merged_row_count = 1841
dispatch_row_offset = 0
dispatch_row_limit = 1841
dispatch_active_rows = 1841
handle_projection_hashchain_equal = true
all_handle_fields_checked = true
no_payload = true
passed_to_kernel = false
changes_kernel_launch_args = false
runtime_gate_evidence_deferred_count = 0
strict_default_gate_evidence_deferred_count = 0
```

## 2026-06-02 - Online-merged arg-slot row-window sweep

The online-merged future-native arg-slot ABI now has a row-window sweep runner
that validates full-table, head, middle, and tail row slices from the same
online-derived typed handle stream.  This is a geometry / future-kernel
consumer check only: the typed table is still not passed to the current WNA16
kernel and no payload bytes are moved.

GPU1 strict canary:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_window_sweep_runner.json

source runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json

row_count = 1841
window_size = 512
mirror_field = scale_metadata_handle
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

Window coverage:

```text
full:
  dispatch_row_offset = 0
  dispatch_row_limit = 1841
  dispatch_active_rows = 1841
  dispatch_expected_program_count = 8

head:
  dispatch_row_offset = 0
  dispatch_row_limit = 512
  dispatch_active_rows = 512
  dispatch_expected_program_count = 2

middle:
  dispatch_row_offset = 664
  dispatch_row_limit = 1176
  dispatch_active_rows = 512
  dispatch_expected_program_count = 2

tail:
  dispatch_row_offset = 1329
  dispatch_row_limit = 1841
  dispatch_active_rows = 512
  dispatch_expected_program_count = 2
```

All four windows pass the native typed consumer stub with:

```text
no_payload = true
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
not_a_single_vllm_launch_table = true
handle_projection_all_handle_fields_checked = true
```

This extends the previous full-table and tail-only evidence to cover the row
slice patterns a future kernel-side consumer would need for CTA/program-level
iteration.  It remains a no-op typed ABI canary, not a live WNA16 kernel-arg
handoff.

The sweep artifact is now machine-checkable:

```text
checker:
  outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_window_sweep_check.json

passed = true
failures = []
expected_window_size = 512
expected_block_threads = 256
expected_mirror_field = scale_metadata_handle
require_child_artifacts = true
row_count = 1841
windows_checked = full, head, middle, tail
```

The checker rejects missing or mismatched row-window geometry and also reads the
per-window child canary artifacts, so this evidence can be promoted into a lab
preflight requirement without relying on manual JSON inspection.

The one-step lab gate verifier now refreshes and checks this window sweep as
part of the canonical readonly premap lab preflight:

```text
verify artifact:
  outputs/reports/premap_lab_gate_verify.json

passed = true
failures = []
steps =
  default_closure
  default_closure_check
  tail_window_closure
  tail_window_closure_check
  window_sweep
  window_sweep_check

window_sweep_check:
  passed = true
  row_count = 1841
  expected_window_size = 512
  expected_block_threads = 256
  require_child_artifacts = true
  windows_checked = full, head, middle, tail
```

This makes the full/head/middle/tail future-native arg-slot row-window evidence
a machine-checked lab preflight condition while still preserving the strict
no-payload / no-current-WNA16-arg boundary.

The integrated verify report itself is now statically checkable:

```text
verify checker:
  outputs/reports/premap_lab_gate_verify.check.json

passed = true
failures = []
allow_dry_run = false
expected_window_size = 512
required_steps =
  default_closure
  default_closure_check
  tail_window_closure
  tail_window_closure_check
  window_sweep
  window_sweep_check
```

This gives the lab a single no-defer preflight entrypoint: run
`scripts/run_premap_lab_gate_verify.py`, then require
`scripts/check_premap_lab_gate_verify.py` to pass before any future
kernel-side typed consumer experiment.

Code review tightened the row-window checker further.  The checker now rejects
degenerate sweeps where `row_count <= window_size`, and it reads each child
window canary artifact to validate:

```text
dispatch_expected_program_count
block_threads
merged_row_count
handle_projection_hashchain_equal
stub_summary.future_kernel_native_arg_slot_consumer_row_count
stub_summary.future_kernel_native_arg_slot_consumer_row_ok_count
stub_summary.future_kernel_native_arg_slot_consumer_single_field_mirror_row_count
stub_summary.future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count
stub_summary.future_kernel_native_dispatch_consumer_program_count
stub_summary.future_kernel_native_dispatch_consumer_block_x
stub_summary.future_kernel_native_dispatch_consumer_row_limit
```

The refreshed real artifacts still pass:

```text
outputs/reports/premap_kernel_consumer/
  online_merged_future_native_arg_slot_window_sweep_check.json

outputs/reports/
  premap_lab_gate_verify.check.json

passed = true
failures = []
require_non_degenerate_windows = true
```

The window-sweep runner now uses field-specific child artifact paths.  This
prevents optional mirror-field sweeps from overwriting the default
`scale_metadata_handle` child artifacts:

```text
scale_metadata_handle:
  online_merged_future_native_arg_slot_scale_metadata_handle_{full,head,middle,tail}_window_canary_runner.json

descriptor_ptr:
  online_merged_future_native_arg_slot_descriptor_ptr_{full,head,middle,tail}_window_canary_runner.json

packed_weight_descriptor:
  online_merged_future_native_arg_slot_packed_weight_descriptor_{full,head,middle,tail}_window_canary_runner.json

aux_metadata_handle:
  online_merged_future_native_arg_slot_aux_metadata_handle_{full,head,middle,tail}_window_canary_runner.json
```

The checker now also validates the child `mirror_field` and the native stub's
`future_kernel_native_arg_slot_consumer_single_field_mirror_field_name`, so a
child artifact from another mirror field cannot satisfy the default lab gate.
All four mirror fields passed the 1841-row full/head/middle/tail window sweep
with the strict no-payload / no-kernel-arg boundary intact.

A convenience all-field runner now refreshes the four mirror-field sweeps and
their static checks in one command:

```text
all-field runner:
  outputs/reports/premap_kernel_consumer/
    online_merged_future_native_arg_slot_all_field_window_sweep_runner.json

passed = true
failures = []
window_size = 512
block_threads = 256
row_counts =
  descriptor_ptr = 1841
  packed_weight_descriptor = 1841
  scale_metadata_handle = 1841
  aux_metadata_handle = 1841

field_reports:
  descriptor_ptr: full/head/middle/tail checked
  packed_weight_descriptor: full/head/middle/tail checked
  scale_metadata_handle: full/head/middle/tail checked
  aux_metadata_handle: full/head/middle/tail checked
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

This is still a native-stub ABI check, not a live WNA16 handoff.  It does,
however, verify that every field in the future typed handle schema can be read
through the same row-window dispatch geometry.

The all-field sweep is now part of the canonical lab gate verifier:

```text
verify artifact:
  outputs/reports/premap_lab_gate_verify.json

verify checker:
  outputs/reports/premap_lab_gate_verify.check.json

passed = true
failures = []
required_steps =
  default_closure
  default_closure_check
  tail_window_closure
  tail_window_closure_check
  window_sweep
  window_sweep_check
  all_field_window_sweep
  all_field_window_sweep_check
```

The lab preflight now requires both the default scale-metadata row-window sweep
and the stricter all-field sweep before any future kernel-side typed consumer
experiment.  The gate remains explicitly no-op with respect to the current
vLLM/WNA16 launch path.

## Native arg-slot row-read evidence promoted into compact lab preflight

The future native arg-slot consumer now reports per-row field-read evidence for
all four typed handle fields:

```text
descriptor_ptr
packed_weight_descriptor
scale_metadata_handle
aux_metadata_handle
```

The HIP stub reads each field through the future native arg-slot path and emits
row counts, ok counts, error counts, and hash accumulators:

```text
future_kernel_native_arg_slot_consumer_<field>_read_row_count
future_kernel_native_arg_slot_consumer_<field>_read_row_ok_count
future_kernel_native_arg_slot_consumer_<field>_read_error_count
future_kernel_native_arg_slot_consumer_<field>_read_hash_accumulator
```

The online-merged default lab artifact was refreshed and finalized:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json

artifact check:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_hard_hashchain_preflight_32tables.json

compact preflight:
  outputs/reports/premap_lab_preflight_status_arg_slot_field_reads.json
  outputs/reports/premap_lab_preflight_status_arg_slot_field_reads.check.json
```

Status:

```text
online inputs = 32
online-merged rows = 1841
arg_slot_all_handle_fields_read = true
descriptor_ptr row_ok = 1841
packed_weight_descriptor row_ok = 1841
scale_metadata_handle row_ok = 1841
aux_metadata_handle row_ok = 1841
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

The compact lab preflight checker now requires these online-merged row-read
counts/hashes.  A two-stage bootstrap path remains available only for producing
self-referential runner artifacts; the final lab gate accepts only strict
no-defer evidence.  The runner also gained a `--finalize-existing` mode so the
self-finalization / artifact-check / final-preflight closure can be rerun
without rebuilding all native stub inputs.

Verification:

```text
python -m pytest tests/test_premap_typed_consumer_stub.py \
  tests/test_run_premap_online_merged_native_arg_slot_canary.py \
  tests/test_check_premap_online_merged_native_arg_slot_window_sweep.py \
  tests/test_check_premap_online_merged_native_arg_slot_all_field_window_sweep.py \
  tests/test_run_premap_online_native_stub_canary.py \
  tests/test_run_premap_lab_preflight.py \
  tests/test_check_premap_lab_preflight_summary.py -q

154 passed

python -m pytest tests -q

913 passed, 2 warnings
```

## Future native consumer-view ABI gate added to lab preflight

The premap typed-consumer path now has one more native ABI layer after the
future native arg-slot packet:

```text
typed handle table
  -> future native consumer params
  -> launch envelope
  -> dispatch packet
  -> dispatch-ptr packet
  -> arg-slot packet
  -> future native consumer-view packet
```

The new consumer-view ABI is still a readonly, no-payload, no-kernel-mutation
contract.  It does not reinterpret the object as an existing WNA16 argument.
Instead, it models the shape of a future kernel-side consumer view and requires
the native stub to explicitly read all four typed handle fields:

```text
descriptor_ptr
packed_weight_descriptor
scale_metadata_handle
aux_metadata_handle
```

The lab preflight compact status now checks the consumer-view row-read evidence:

```text
default_kernel_consumer_consumer_view_all_handle_fields_read = true
default_kernel_consumer_consumer_view_field_read_row_count = 174
default_kernel_consumer_consumer_view_source_packet_chain_depth = 3
default_kernel_consumer_consumer_view_payload_bytes = 0
default_kernel_consumer_consumer_view_passed_to_kernel = false
default_kernel_consumer_consumer_view_changes_kernel_launch_args = false
default_kernel_consumer_consumer_view_current_wna16_arg_compatible = false
default_kernel_consumer_consumer_view_requires_wna16_arg_reinterpretation = false
```

The default 32-input online prelaunch native-stub artifact was re-finalized with
strict no-defer evidence:

```text
runner:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json

artifact check:
  outputs/reports/premap_kernel_consumer/
    online_prelaunch_native_stub_canary_artifact_check_arg_slot_32input_hard_hashchain_preflight_32tables.json

compact preflight:
  outputs/reports/
    premap_lab_preflight_status_online_prelaunch_native_stub_canary_hard_hashchain_preflight_32tables.json
  outputs/reports/
    premap_lab_preflight_status_online_prelaunch_native_stub_canary_hard_hashchain_preflight_32tables.check.json
```

Status:

```text
online inputs = 32
extra online inputs = 31 / 31 passed
artifact_check_passed = true
final_preflight_passed = true
final_deferred_count = 0
status_deferred_count = 0
```

This keeps the approved two-stage bootstrap rule: the runner may mirror a
bootstrap artifact only to close the self-referential evidence loop, then the
canonical artifact is overwritten by the final strict artifact-check.  The lab
gate accepts only the final no-defer passed state.

Verification:

```text
python -m pytest tests/test_run_premap_online_native_stub_canary.py \
  tests/test_run_premap_lab_preflight.py \
  tests/test_check_premap_lab_preflight_summary.py -q

116 passed

python -m pytest tests -q

917 passed, 2 warnings
```

## Consumer-view ABI added to the machine-readable kernel consumer schema

The future native consumer-view ABI is now part of the formal premap
kernel-side typed consumer schema, not only a runtime stub artifact.

Updated artifacts:

```text
docs/premap_kernel_consumer_schema.md
configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml
scripts/check_premap_kernel_consumer_schema.py
```

The schema now pins:

```text
future_kernel_native_consumer_view_abi_name =
  premap_future_kernel_native_consumer_view_abi_v1
future_kernel_native_consumer_view_abi_struct =
  PremapFutureKernelNativeConsumerViewV1
future_kernel_native_consumer_view_abi_source =
  premap_future_kernel_native_consumer_arg_slot_abi_v1
future_kernel_native_consumer_view_abi_source_packet_chain_depth_required = 3
future_kernel_native_consumer_view_abi_payload_bytes_required = 0
future_kernel_native_consumer_view_abi_passed_to_kernel_required = false
future_kernel_native_consumer_view_abi_current_wna16_arg_compatible = false
future_kernel_native_consumer_view_abi_requires_wna16_arg_reinterpretation = false
```

It also pins the C++ layout:

```text
PremapFutureKernelNativeConsumerViewV1
  size = 208
  align = 8
  params_size = 112
  result_size = 80
  offset(params) = 0
  offset(abi_version) = 112
  offset(source_packet_chain_depth) = 116
  offset(row_offset) = 120
  offset(row_limit) = 124
  offset(rows_per_program) = 128
  offset(payload_bytes) = 132
  offset(flags) = 136
```

The macro ladder now includes:

```text
MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI
```

Verification:

```text
env PYTHONPATH=src python scripts/check_premap_kernel_consumer_schema.py \
  configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml \
  --output-json outputs/reports/premap_kernel_consumer_schema_check.json

python -m pytest tests/test_premap_kernel_consumer_schema.py \
  tests/test_run_premap_lab_preflight.py \
  tests/test_check_premap_lab_preflight_summary.py -q

115 passed

python -m pytest tests -q

918 passed, 2 warnings
```

## Consumer-view ABI is now enforced by the unified lab gate

The canonical premap lab gate now requires the future native consumer-view path,
not only the arg-slot path.

The window-sweep checker now validates, for each full/head/middle/tail child
canary:

```text
future_kernel_native_consumer_view_checked = true
future_kernel_native_consumer_view_source_packet_chain_depth = 3
future_kernel_native_consumer_view_row_count / row_ok_count match active rows
future_kernel_native_consumer_view_error_count = 0
all four handle fields are read:
  descriptor_ptr
  packed_weight_descriptor
  scale_metadata_handle
  aux_metadata_handle
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
requires_wna16_arg_reinterpretation = false
```

The checker also follows each child canary's `stub_output_json` and validates
the native stub artifact itself:

```text
future_kernel_native_consumer_view_row_offset
future_kernel_native_consumer_view_row_limit
future_kernel_native_consumer_view_rows_per_program
```

This keeps the gate tied to the future native consumer ABI output, not only the
runner's summarized status.

The all-field sweep checker and the top-level lab gate checker now require:

```text
require_child_consumer_view = true
```

This means the lab preflight no longer accepts artifacts that only prove
arg-slot readability.  The typed consumer bridge must prove the future
kernel-side consumer-view ABI reads the four-field handle table while still
remaining a strict no-op with respect to the current WNA16 launch.

Verification:

```text
python -m pytest \
  tests/test_check_premap_online_merged_native_arg_slot_window_sweep.py \
  tests/test_check_premap_online_merged_native_arg_slot_all_field_window_sweep.py \
  tests/test_check_premap_lab_gate_verify.py \
  tests/test_run_premap_lab_gate_verify.py -q

29 passed

python scripts/run_premap_lab_gate_verify.py \
  --output-json outputs/reports/premap_lab_gate_verify.json

passed = true
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
window_sweep_check.require_child_consumer_view = true
all_field_window_sweep_check.require_child_consumer_view = true

python scripts/check_premap_lab_gate_verify.py \
  outputs/reports/premap_lab_gate_verify.json \
  --output-json outputs/reports/premap_lab_gate_verify.check.json

passed = true
failures = []
```

## Consumer-view ABI layout is checked by the window gate

The future native consumer-view packet is now part of the lab evidence as a
layout-checked ABI object, not just a group of JSON summary fields.

The native stub now emits:

```text
future_kernel_native_consumer_view_struct_size
future_kernel_native_consumer_view_struct_align
future_kernel_native_consumer_view_params_struct_size
future_kernel_native_consumer_view_params_struct_align
future_kernel_native_consumer_view_result_struct_size
future_kernel_native_consumer_view_result_struct_align
future_kernel_native_consumer_view_offset_params
future_kernel_native_consumer_view_offset_abi_version
future_kernel_native_consumer_view_offset_source_packet_chain_depth
future_kernel_native_consumer_view_offset_row_offset
future_kernel_native_consumer_view_offset_row_limit
future_kernel_native_consumer_view_offset_rows_per_program
future_kernel_native_consumer_view_offset_payload_bytes
future_kernel_native_consumer_view_offset_flags
```

The window-sweep checker follows each child canary's `stub_output_json` and
validates that:

```text
offset(params) = 0
offset(abi_version) = params_struct_size
source_packet_chain_depth / row_offset / row_limit / rows_per_program /
payload_bytes / flags are contiguous uint32 fields
offset(flags) + 4 <= struct_size
struct_size and result_struct_size respect their alignments
```

This catches ABI layout drift at the future kernel-side consumer-view boundary
while preserving the no-op runtime contract:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
current_wna16_arg_compatible = false
```

Verification:

```text
python -m pytest \
  tests/test_premap_typed_consumer_stub.py \
  tests/test_check_premap_online_merged_native_arg_slot_window_sweep.py \
  tests/test_run_premap_online_merged_native_arg_slot_canary.py \
  tests/test_run_premap_online_merged_native_arg_slot_window_sweep.py -q

44 passed

python scripts/run_premap_lab_gate_verify.py \
  --output-json outputs/reports/premap_lab_gate_verify.json

passed = true
window_sweep_check.require_child_consumer_view = true
all_field_window_sweep_check.require_child_consumer_view = true

python scripts/check_premap_lab_gate_verify.py \
  outputs/reports/premap_lab_gate_verify.json \
  --output-json outputs/reports/premap_lab_gate_verify.check.json

passed = true
failures = []
```

## Canary runner now validates consumer-view row geometry directly

The online merged native arg-slot canary now validates the future native
consumer-view geometry inside the runner itself, not only in the downstream
window-sweep checker.

For each dispatch window, the canary requires the native stub summary to match:

```text
future_kernel_native_consumer_view_row_offset = dispatch_row_offset
future_kernel_native_consumer_view_row_limit = dispatch_row_limit
future_kernel_native_consumer_view_rows_per_program = block_threads
future_kernel_native_consumer_view_row_count = active_rows
future_kernel_native_consumer_view_row_ok_count = active_rows
future_kernel_native_consumer_view_error_count = 0
```

The dry-run stub artifact emits the same geometry fields, so schema drift is
caught before the higher-level lab gate consumes the artifact.  This keeps the
future kernel-side consumer-view ABI tied to the same row window that the
prelaunch shim intends to expose, while still enforcing:

```text
payload_bytes = 0
passed_to_kernel = false
changes_kernel_launch_args = false
```

Verification:

```text
python -m pytest \
  tests/test_run_premap_online_merged_native_arg_slot_canary.py \
  tests/test_check_premap_online_merged_native_arg_slot_window_sweep.py \
  tests/test_run_premap_online_merged_native_arg_slot_window_sweep.py -q

17 passed

python scripts/run_premap_lab_gate_verify.py \
  --output-json outputs/reports/premap_lab_gate_verify.json

passed = true
window_sweep_check.require_child_consumer_view = true
all_field_window_sweep_check.require_child_consumer_view = true

python scripts/check_premap_lab_gate_verify.py \
  outputs/reports/premap_lab_gate_verify.json \
  --output-json outputs/reports/premap_lab_gate_verify.check.json

passed = true
failures = []
```
