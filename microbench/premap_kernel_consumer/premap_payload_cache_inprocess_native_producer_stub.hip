#include <hip/hip_runtime.h>

#include <algorithm>
#include <cstdint>
#include <vector>

#include "premap_typed_consumer_abi_v1.h"

static_assert(kPremapPayloadCacheProducerTransitionStateAbiV1FieldCount == 9,
              "producer transition-state ABI v1 field count changed");
static_assert(!kPremapPayloadCacheProducerTransitionStateAbiV1PayloadBytesAllowed,
              "producer transition-state ABI must not allow payload bytes");
static_assert(!kPremapPayloadCacheProducerTransitionStateAbiV1KernelArgPassAllowed,
              "producer transition-state ABI must not allow kernel-arg pass");
static_assert(
    !kPremapPayloadCacheProducerTransitionStateAbiV1CurrentWna16ArgCompatible,
    "producer transition-state ABI must not be the current WNA16 arg list");

struct PremapPayloadCacheInprocessProducerResultV1 {
  uint32_t abi_version;
  uint32_t ok;
  uint32_t passed;
  uint32_t native_returncode;
  uint32_t steps;
  uint32_t layers;
  uint32_t experts_per_layer;
  uint32_t transition_topk_count;
  uint64_t packet_count;
  uint64_t previous_nonempty_packet_count;
  uint64_t current_nonempty_packet_count;
  uint64_t issue_candidate_count;
  uint64_t expected_issue_candidate_count;
  uint64_t issue_candidate_hash;
  int32_t first_issue_expert;
  int32_t last_issue_expert;
  uint32_t ready_layer_count;
  uint32_t error_count;
  float gpu_elapsed_ms;
  uint32_t persistent_state_on_device;
  uint32_t issue_generation_on_device;
  uint32_t native_graph_replay;
  uint32_t native_stub_invoked;
  uint32_t vectorized_copy_requested;
  uint32_t vectorized_copy_used;
  uint32_t payload_bytes;
  uint32_t payload_transfer_enabled;
  uint32_t payload_deref_allowed;
  uint32_t ready_credit;
  uint32_t ready_before_demand_credit;
  uint32_t real_ready_credit_granted;
  uint32_t passed_to_kernel;
  uint32_t changes_kernel_launch_args;
  uint32_t kernel_arg_pass;
  uint32_t kernel_arg_pass_allowed;
  uint32_t current_wna16_arg_compatible;
  uint32_t uses_current_wna16_args;
  uint32_t passes_current_wna16_args;
  uint32_t measures_tpot;
  uint32_t measures_vllm_latency;
};

struct PremapPayloadCacheInprocessProducerSessionUpdateResultV1 {
  uint32_t abi_version;
  uint32_t ok;
  uint32_t passed;
  uint32_t native_returncode;
  uint32_t session_handle_nonzero;
  uint32_t current_expert_ptr_nonzero;
  uint32_t layer_id;
  uint32_t layers;
  uint32_t experts_per_layer;
  uint32_t transition_topk_count;
  uint32_t previous_count_before;
  uint32_t current_count;
  uint32_t packet_count;
  uint32_t previous_nonempty_packet_count;
  uint32_t current_nonempty_packet_count;
  uint32_t issue_candidate_count;
  uint32_t expected_issue_candidate_count;
  uint64_t issue_candidate_hash;
  int32_t first_issue_expert;
  int32_t last_issue_expert;
  uint32_t ready;
  uint32_t error_count;
  float gpu_elapsed_ms;
  uint32_t persistent_state_on_device;
  uint32_t issue_generation_on_device;
  uint32_t prelaunch_callable_native_session;
  uint32_t graph_visible;
  uint32_t native_stub_invoked;
  uint32_t vectorized_copy_requested;
  uint32_t vectorized_copy_used;
  uint32_t payload_bytes;
  uint32_t payload_transfer_enabled;
  uint32_t payload_deref_allowed;
  uint32_t ready_credit;
  uint32_t ready_before_demand_credit;
  uint32_t real_ready_credit_granted;
  uint32_t passed_to_kernel;
  uint32_t changes_kernel_launch_args;
  uint32_t kernel_arg_pass;
  uint32_t kernel_arg_pass_allowed;
  uint32_t current_wna16_arg_compatible;
  uint32_t uses_current_wna16_args;
  uint32_t passes_current_wna16_args;
  uint32_t measures_tpot;
  uint32_t measures_vllm_latency;
};

struct InprocessLayerResult {
  uint32_t checked;
  uint32_t ready;
  uint32_t packet_count;
  uint32_t previous_nonempty_packet_count;
  uint32_t current_nonempty_packet_count;
  uint32_t current_count;
  uint32_t issue_candidate_count;
  uint32_t error_count;
  uint32_t vectorized_copy_used;
  int32_t issue_candidate_first_expert;
  int32_t issue_candidate_last_expert;
  uint64_t issue_candidate_hash;
};

struct PremapPayloadCacheInprocessProducerSessionV1 {
  uint32_t magic;
  int device;
  uint32_t layers;
  uint32_t experts_per_layer;
  uint32_t transition_topk_count;
  int32_t* d_previous_state;
  uint32_t* d_previous_count;
  InprocessLayerResult* d_layer_results;
  hipStream_t stream;
};

constexpr uint32_t kPremapPayloadCacheInprocessProducerSessionMagicV1 =
    0x4d545053U;

__host__ __device__ uint64_t inprocess_hash_mix(uint64_t value, uint32_t item) {
  value ^= static_cast<uint64_t>(item);
  value *= 0x100000001b3ULL;
  return value;
}

__global__ void inprocess_transition_step_kernel(
    const int32_t* __restrict__ current_expert_stream,
    int32_t* __restrict__ previous_expert_state,
    uint32_t* __restrict__ previous_count_state,
    InprocessLayerResult* __restrict__ layer_results,
    const uint32_t* __restrict__ step_state,
    uint32_t step_count,
    uint32_t layer_count,
    uint32_t experts_per_layer,
    uint32_t transition_topk_count,
    uint32_t use_vectorized_copy) {
  const uint32_t layer = blockIdx.x;
  if (layer >= layer_count) {
    return;
  }
  const uint32_t step = *step_state;
  if (step >= step_count) {
    return;
  }

  __shared__ uint32_t previous_count;
  __shared__ uint32_t issue_limit;
  __shared__ uint64_t local_issue_hash;
  __shared__ uint32_t local_issue_count;
  __shared__ int32_t local_issue_first;
  __shared__ int32_t local_issue_last;
  __shared__ uint32_t local_error_count;
  __shared__ uint32_t vectorized_copy_seen;

  int32_t* previous_base = previous_expert_state + layer * experts_per_layer;
  uint32_t* previous_count_ptr = previous_count_state + layer;
  InprocessLayerResult* result = layer_results + layer;
  const int32_t* current_base =
      current_expert_stream +
      (static_cast<uint64_t>(step) * layer_count + layer) * experts_per_layer;

  if (threadIdx.x == 0) {
    previous_count = *previous_count_ptr;
    issue_limit = transition_topk_count == 0
                      ? previous_count
                      : (previous_count < transition_topk_count
                             ? previous_count
                             : transition_topk_count);
    local_issue_hash = 0xcbf29ce484222325ULL;
    local_issue_count = 0;
    local_issue_first = -1;
    local_issue_last = -1;
    local_error_count = 0;
    vectorized_copy_seen = 0;
    for (uint32_t i = 0; i < issue_limit; ++i) {
      const int32_t expert = previous_base[i];
      if (expert < 0) {
        local_error_count += 1;
        continue;
      }
      if (local_issue_count == 0) {
        local_issue_first = expert;
      }
      local_issue_last = expert;
      local_issue_hash =
          inprocess_hash_mix(local_issue_hash, static_cast<uint32_t>(expert));
      local_issue_count += 1;
    }
    local_issue_hash = inprocess_hash_mix(local_issue_hash, issue_limit);
  }
  __syncthreads();

  const bool aligned_for_int4 =
      reinterpret_cast<uintptr_t>(current_base) % alignof(int4) == 0 &&
      reinterpret_cast<uintptr_t>(previous_base) % alignof(int4) == 0;
  if (use_vectorized_copy != 0 && experts_per_layer % 4 == 0 &&
      aligned_for_int4) {
    if (threadIdx.x == 0) {
      vectorized_copy_seen = 1;
    }
    const uint32_t vec_count = experts_per_layer / 4;
    const int4* current_vec = reinterpret_cast<const int4*>(current_base);
    int4* previous_vec = reinterpret_cast<int4*>(previous_base);
    for (uint32_t vec = threadIdx.x; vec < vec_count; vec += blockDim.x) {
      previous_vec[vec] = current_vec[vec];
    }
  } else {
    for (uint32_t i = threadIdx.x; i < experts_per_layer; i += blockDim.x) {
      previous_base[i] = current_base[i];
    }
  }
  __syncthreads();

  if (threadIdx.x == 0) {
    *previous_count_ptr = experts_per_layer;
    result->checked = 1;
    result->packet_count += 1;
    result->previous_nonempty_packet_count += previous_count > 0 ? 1 : 0;
    result->current_nonempty_packet_count += 1;
    result->current_count = experts_per_layer;
    result->issue_candidate_count += local_issue_count;
    result->vectorized_copy_used =
        result->vectorized_copy_used || vectorized_copy_seen ? 1 : 0;
    result->error_count += local_error_count;
    if (local_issue_first >= 0 && result->issue_candidate_first_expert < 0) {
      result->issue_candidate_first_expert = local_issue_first;
    }
    if (local_issue_last >= 0) {
      result->issue_candidate_last_expert = local_issue_last;
    }
    result->issue_candidate_hash =
        inprocess_hash_mix(
            result->issue_candidate_hash,
            static_cast<uint32_t>(local_issue_hash));
    result->ready = result->error_count == 0 ? 1 : 0;
  }
}

__global__ void inprocess_step_increment_kernel(uint32_t* __restrict__ step_state) {
  if (threadIdx.x == 0 && blockIdx.x == 0) {
    *step_state += 1;
  }
}

__global__ void inprocess_session_restore_state_kernel(
    const int32_t* __restrict__ previous_experts,
    uint32_t previous_count,
    int32_t* __restrict__ previous_expert_state,
    uint32_t* __restrict__ previous_count_state,
    uint32_t layer,
    uint32_t layer_count,
    uint32_t experts_per_layer) {
  if (blockIdx.x != 0 || layer >= layer_count || previous_count > experts_per_layer) {
    return;
  }

  int32_t* previous_base = previous_expert_state + layer * experts_per_layer;
  for (uint32_t i = threadIdx.x; i < previous_count; i += blockDim.x) {
    previous_base[i] = previous_experts[i];
  }
  for (uint32_t i = previous_count + threadIdx.x; i < experts_per_layer;
       i += blockDim.x) {
    previous_base[i] = -1;
  }
  __syncthreads();
  if (threadIdx.x == 0) {
    previous_count_state[layer] = previous_count;
  }
}

__global__ void inprocess_session_update_layer_kernel(
    const int32_t* __restrict__ current_experts,
    uint32_t current_count,
    const uint32_t* __restrict__ current_count_device,
    int32_t* __restrict__ previous_expert_state,
    uint32_t* __restrict__ previous_count_state,
    InprocessLayerResult* __restrict__ layer_results,
    uint32_t layer,
    uint32_t layer_count,
    uint32_t experts_per_layer,
    uint32_t transition_topk_count,
    uint32_t use_vectorized_copy) {
  if (blockIdx.x != 0 || layer >= layer_count) {
    return;
  }
  const uint32_t effective_current_count =
      current_count_device == nullptr ? current_count : *current_count_device;
  InprocessLayerResult* result = layer_results + layer;
  if (effective_current_count > experts_per_layer) {
    if (threadIdx.x == 0) {
      result->checked = 1;
      result->packet_count += 1;
      result->current_count = effective_current_count;
      result->error_count += 1;
      result->ready = 0;
    }
    return;
  }

  __shared__ uint32_t previous_count;
  __shared__ uint32_t issue_limit;
  __shared__ uint64_t local_issue_hash;
  __shared__ uint32_t local_issue_count;
  __shared__ int32_t local_issue_first;
  __shared__ int32_t local_issue_last;
  __shared__ uint32_t local_error_count;
  __shared__ uint32_t vectorized_copy_seen;

  int32_t* previous_base = previous_expert_state + layer * experts_per_layer;
  uint32_t* previous_count_ptr = previous_count_state + layer;

  if (threadIdx.x == 0) {
    previous_count = *previous_count_ptr;
    issue_limit = transition_topk_count == 0
                      ? previous_count
                      : (previous_count < transition_topk_count
                             ? previous_count
                             : transition_topk_count);
    local_issue_hash = 0xcbf29ce484222325ULL;
    local_issue_count = 0;
    local_issue_first = -1;
    local_issue_last = -1;
    local_error_count = 0;
    vectorized_copy_seen = 0;
    for (uint32_t i = 0; i < issue_limit; ++i) {
      const int32_t expert = previous_base[i];
      if (expert < 0) {
        local_error_count += 1;
        continue;
      }
      if (local_issue_count == 0) {
        local_issue_first = expert;
      }
      local_issue_last = expert;
      local_issue_hash =
          inprocess_hash_mix(local_issue_hash, static_cast<uint32_t>(expert));
      local_issue_count += 1;
    }
    local_issue_hash = inprocess_hash_mix(local_issue_hash, issue_limit);
  }
  __syncthreads();

  const bool aligned_for_int4 =
      reinterpret_cast<uintptr_t>(current_experts) % alignof(int4) == 0 &&
      reinterpret_cast<uintptr_t>(previous_base) % alignof(int4) == 0;
  if (use_vectorized_copy != 0 && effective_current_count == experts_per_layer &&
      experts_per_layer % 4 == 0 && aligned_for_int4) {
    if (threadIdx.x == 0) {
      vectorized_copy_seen = 1;
    }
    const uint32_t vec_count = experts_per_layer / 4;
    const int4* current_vec = reinterpret_cast<const int4*>(current_experts);
    int4* previous_vec = reinterpret_cast<int4*>(previous_base);
    for (uint32_t vec = threadIdx.x; vec < vec_count; vec += blockDim.x) {
      previous_vec[vec] = current_vec[vec];
    }
  } else {
    for (uint32_t i = threadIdx.x; i < effective_current_count; i += blockDim.x) {
      previous_base[i] = current_experts[i];
    }
    for (uint32_t i = effective_current_count + threadIdx.x; i < experts_per_layer;
         i += blockDim.x) {
      previous_base[i] = -1;
    }
  }
  __syncthreads();

  if (threadIdx.x == 0) {
    *previous_count_ptr = effective_current_count;
    result->checked = 1;
    result->packet_count += 1;
    result->previous_nonempty_packet_count += previous_count > 0 ? 1 : 0;
    result->current_nonempty_packet_count +=
        effective_current_count > 0 ? 1 : 0;
    result->current_count = effective_current_count;
    result->issue_candidate_count += local_issue_count;
    result->vectorized_copy_used =
        result->vectorized_copy_used || vectorized_copy_seen ? 1 : 0;
    result->error_count += local_error_count;
    if (local_issue_first >= 0 && result->issue_candidate_first_expert < 0) {
      result->issue_candidate_first_expert = local_issue_first;
    }
    if (local_issue_last >= 0) {
      result->issue_candidate_last_expert = local_issue_last;
    }
    result->issue_candidate_hash =
        inprocess_hash_mix(
            result->issue_candidate_hash,
            static_cast<uint32_t>(local_issue_hash));
    result->ready = result->error_count == 0 ? 1 : 0;
  }
}

static void fill_safe_defaults(PremapPayloadCacheInprocessProducerResultV1* out) {
  if (out == nullptr) {
    return;
  }
  *out = PremapPayloadCacheInprocessProducerResultV1{};
  out->abi_version = 1;
  out->first_issue_expert = -1;
  out->last_issue_expert = -1;
  out->issue_candidate_hash = 0xcbf29ce484222325ULL;
  out->payload_bytes = 0;
  out->payload_transfer_enabled = 0;
  out->payload_deref_allowed = 0;
  out->ready_credit = 0;
  out->ready_before_demand_credit = 0;
  out->real_ready_credit_granted = 0;
  out->passed_to_kernel = 0;
  out->changes_kernel_launch_args = 0;
  out->kernel_arg_pass = 0;
  out->kernel_arg_pass_allowed = 0;
  out->current_wna16_arg_compatible = 0;
  out->uses_current_wna16_args = 0;
  out->passes_current_wna16_args = 0;
  out->measures_tpot = 0;
  out->measures_vllm_latency = 0;
}

static void fill_session_update_safe_defaults(
    PremapPayloadCacheInprocessProducerSessionUpdateResultV1* out) {
  if (out == nullptr) {
    return;
  }
  *out = PremapPayloadCacheInprocessProducerSessionUpdateResultV1{};
  out->abi_version = 1;
  out->first_issue_expert = -1;
  out->last_issue_expert = -1;
  out->issue_candidate_hash = 0xcbf29ce484222325ULL;
  out->payload_bytes = 0;
  out->payload_transfer_enabled = 0;
  out->payload_deref_allowed = 0;
  out->ready_credit = 0;
  out->ready_before_demand_credit = 0;
  out->real_ready_credit_granted = 0;
  out->passed_to_kernel = 0;
  out->changes_kernel_launch_args = 0;
  out->kernel_arg_pass = 0;
  out->kernel_arg_pass_allowed = 0;
  out->current_wna16_arg_compatible = 0;
  out->uses_current_wna16_args = 0;
  out->passes_current_wna16_args = 0;
  out->measures_tpot = 0;
  out->measures_vllm_latency = 0;
}

static int fail_with_code(
    PremapPayloadCacheInprocessProducerResultV1* out,
    uint32_t code) {
  if (out != nullptr) {
    out->ok = 0;
    out->passed = 0;
    out->native_returncode = code;
  }
  return static_cast<int>(code);
}

static void discard_hip_error(hipError_t err) {
  (void)err;
}

static void cleanup_active_capture(hipStream_t stream, uint32_t capture_active) {
  if (stream == nullptr || capture_active == 0) {
    return;
  }
  hipGraph_t cleanup_graph = nullptr;
  const hipError_t err = hipStreamEndCapture(stream, &cleanup_graph);
  if (err == hipSuccess && cleanup_graph != nullptr) {
    discard_hip_error(hipGraphDestroy(cleanup_graph));
  }
}

static void initialize_layer_results(std::vector<InprocessLayerResult>* results) {
  if (results == nullptr) {
    return;
  }
  for (auto& result : *results) {
    result = InprocessLayerResult{};
    result.issue_candidate_first_expert = -1;
    result.issue_candidate_last_expert = -1;
    result.issue_candidate_hash = 0xcbf29ce484222325ULL;
  }
}

extern "C" int premap_payload_cache_inprocess_producer_session_create_v1(
    int device,
    uint32_t layers,
    uint32_t experts_per_layer,
    uint32_t transition_topk_count,
    uint64_t* out_handle) {
  if (out_handle == nullptr) {
    return 200;
  }
  *out_handle = 0;
  if (layers == 0 || experts_per_layer == 0 || layers > 4096 ||
      experts_per_layer > 4096) {
    return 201;
  }
  if (hipSetDevice(device) != hipSuccess) {
    return 202;
  }

  auto* session = new PremapPayloadCacheInprocessProducerSessionV1{};
  session->magic = kPremapPayloadCacheInprocessProducerSessionMagicV1;
  session->device = device;
  session->layers = layers;
  session->experts_per_layer = experts_per_layer;
  session->transition_topk_count = transition_topk_count;

  const size_t previous_bytes =
      static_cast<size_t>(layers) * experts_per_layer * sizeof(int32_t);
  const size_t previous_count_bytes = static_cast<size_t>(layers) * sizeof(uint32_t);
  const size_t result_bytes = static_cast<size_t>(layers) * sizeof(InprocessLayerResult);

#define SESSION_TRY_HIP(EXPR, CODE) \
  do { \
    if ((EXPR) != hipSuccess) { \
      if (session->stream != nullptr) discard_hip_error(hipStreamDestroy(session->stream)); \
      if (session->d_previous_state != nullptr) discard_hip_error(hipFree(session->d_previous_state)); \
      if (session->d_previous_count != nullptr) discard_hip_error(hipFree(session->d_previous_count)); \
      if (session->d_layer_results != nullptr) discard_hip_error(hipFree(session->d_layer_results)); \
      delete session; \
      return CODE; \
    } \
  } while (0)

  SESSION_TRY_HIP(hipStreamCreate(&session->stream), 203);
  SESSION_TRY_HIP(hipMalloc(&session->d_previous_state, previous_bytes), 204);
  SESSION_TRY_HIP(hipMalloc(&session->d_previous_count, previous_count_bytes), 205);
  SESSION_TRY_HIP(hipMalloc(&session->d_layer_results, result_bytes), 206);
  SESSION_TRY_HIP(hipMemset(session->d_previous_state, 0xff, previous_bytes), 207);
  SESSION_TRY_HIP(hipMemset(session->d_previous_count, 0, previous_count_bytes), 208);

  std::vector<InprocessLayerResult> initial_results(layers);
  initialize_layer_results(&initial_results);
  SESSION_TRY_HIP(
      hipMemcpy(
          session->d_layer_results,
          initial_results.data(),
          result_bytes,
          hipMemcpyHostToDevice),
      209);

#undef SESSION_TRY_HIP

  *out_handle = reinterpret_cast<uint64_t>(session);
  return 0;
}

extern "C" int premap_payload_cache_inprocess_producer_session_destroy_v1(
    uint64_t handle) {
  auto* session =
      reinterpret_cast<PremapPayloadCacheInprocessProducerSessionV1*>(handle);
  if (session == nullptr ||
      session->magic != kPremapPayloadCacheInprocessProducerSessionMagicV1) {
    return 220;
  }
  if (hipSetDevice(session->device) != hipSuccess) {
    return 221;
  }
  session->magic = 0;
  if (session->stream != nullptr) {
    discard_hip_error(hipStreamDestroy(session->stream));
  }
  if (session->d_previous_state != nullptr) {
    discard_hip_error(hipFree(session->d_previous_state));
  }
  if (session->d_previous_count != nullptr) {
    discard_hip_error(hipFree(session->d_previous_count));
  }
  if (session->d_layer_results != nullptr) {
    discard_hip_error(hipFree(session->d_layer_results));
  }
  delete session;
  return 0;
}

extern "C" int premap_payload_cache_inprocess_producer_session_restore_state_v1(
    uint64_t handle,
    uint32_t layer,
    const int32_t* previous_experts_device,
    uint32_t previous_count) {
  auto* session =
      reinterpret_cast<PremapPayloadCacheInprocessProducerSessionV1*>(handle);
  if (session == nullptr ||
      session->magic != kPremapPayloadCacheInprocessProducerSessionMagicV1) {
    return 260;
  }
  if (previous_experts_device == nullptr && previous_count != 0) {
    return 261;
  }
  if (layer >= session->layers || previous_count > session->experts_per_layer) {
    return 262;
  }
  if (hipSetDevice(session->device) != hipSuccess) {
    return 263;
  }
  hipLaunchKernelGGL(
      inprocess_session_restore_state_kernel,
      dim3(1),
      dim3(128),
      0,
      session->stream,
      previous_experts_device,
      previous_count,
      session->d_previous_state,
      session->d_previous_count,
      layer,
      session->layers,
      session->experts_per_layer);
  if (hipGetLastError() != hipSuccess) {
    return 264;
  }
  if (hipStreamSynchronize(session->stream) != hipSuccess) {
    return 265;
  }
  return 0;
}

static int premap_payload_cache_inprocess_producer_session_update_common_v1(
    uint64_t handle,
    uint32_t layer,
    const int32_t* current_experts_device,
    uint32_t current_count,
    const uint32_t* current_count_device,
    uint32_t use_vectorized_copy,
    PremapPayloadCacheInprocessProducerSessionUpdateResultV1* out) {
  fill_session_update_safe_defaults(out);
  if (out == nullptr) {
    return 230;
  }
  out->native_stub_invoked = 1;
  out->session_handle_nonzero = handle != 0 ? 1 : 0;
  out->current_expert_ptr_nonzero = current_experts_device != nullptr ? 1 : 0;
  out->layer_id = layer;
  out->vectorized_copy_requested = use_vectorized_copy != 0 ? 1 : 0;
  out->persistent_state_on_device = 1;
  out->issue_generation_on_device = 1;
  out->prelaunch_callable_native_session = 1;
  out->graph_visible = 0;

  auto* session =
      reinterpret_cast<PremapPayloadCacheInprocessProducerSessionV1*>(handle);
  if (session == nullptr ||
      session->magic != kPremapPayloadCacheInprocessProducerSessionMagicV1) {
    out->native_returncode = 231;
    return 231;
  }
  out->layers = session->layers;
  out->experts_per_layer = session->experts_per_layer;
  out->transition_topk_count = session->transition_topk_count;

  if (current_experts_device == nullptr) {
    out->native_returncode = 232;
    return 232;
  }
  if (layer >= session->layers ||
      (current_count_device == nullptr &&
       current_count > session->experts_per_layer)) {
    out->native_returncode = 233;
    return 233;
  }
  if (hipSetDevice(session->device) != hipSuccess) {
    out->native_returncode = 234;
    return 234;
  }

  hipEvent_t start = nullptr;
  hipEvent_t stop = nullptr;
  uint32_t previous_count_before = 0;
  InprocessLayerResult before_layer_result{};
  InprocessLayerResult layer_result{};
  layer_result.issue_candidate_first_expert = -1;
  layer_result.issue_candidate_last_expert = -1;
  layer_result.issue_candidate_hash = 0xcbf29ce484222325ULL;

#define SESSION_UPDATE_TRY_HIP(EXPR, CODE) \
  do { \
    if ((EXPR) != hipSuccess) { \
      if (start != nullptr) discard_hip_error(hipEventDestroy(start)); \
      if (stop != nullptr) discard_hip_error(hipEventDestroy(stop)); \
      out->native_returncode = CODE; \
      return CODE; \
    } \
  } while (0)

  SESSION_UPDATE_TRY_HIP(
      hipMemcpy(
          &previous_count_before,
          session->d_previous_count + layer,
          sizeof(uint32_t),
          hipMemcpyDeviceToHost),
      235);
  SESSION_UPDATE_TRY_HIP(
      hipMemcpy(
          &before_layer_result,
          session->d_layer_results + layer,
          sizeof(InprocessLayerResult),
          hipMemcpyDeviceToHost),
      236);
  SESSION_UPDATE_TRY_HIP(hipEventCreate(&start), 236);
  SESSION_UPDATE_TRY_HIP(hipEventCreate(&stop), 237);
  SESSION_UPDATE_TRY_HIP(hipEventRecord(start, session->stream), 238);
  hipLaunchKernelGGL(
      inprocess_session_update_layer_kernel,
      dim3(1),
      dim3(128),
      0,
      session->stream,
      current_experts_device,
      current_count,
      current_count_device,
      session->d_previous_state,
      session->d_previous_count,
      session->d_layer_results,
      layer,
      session->layers,
      session->experts_per_layer,
      session->transition_topk_count,
      use_vectorized_copy);
  SESSION_UPDATE_TRY_HIP(hipGetLastError(), 239);
  SESSION_UPDATE_TRY_HIP(hipEventRecord(stop, session->stream), 240);
  SESSION_UPDATE_TRY_HIP(hipEventSynchronize(stop), 241);
  SESSION_UPDATE_TRY_HIP(hipEventElapsedTime(&out->gpu_elapsed_ms, start, stop), 242);
  SESSION_UPDATE_TRY_HIP(
      hipMemcpy(
          &layer_result,
          session->d_layer_results + layer,
          sizeof(InprocessLayerResult),
          hipMemcpyDeviceToHost),
      243);
  SESSION_UPDATE_TRY_HIP(hipEventDestroy(start), 244);
  start = nullptr;
  SESSION_UPDATE_TRY_HIP(hipEventDestroy(stop), 245);
  stop = nullptr;

#undef SESSION_UPDATE_TRY_HIP

  const uint32_t expected_issue_per_update =
      session->transition_topk_count == 0
          ? previous_count_before
          : std::min(previous_count_before, session->transition_topk_count);
  const uint32_t packet_delta =
      layer_result.packet_count - before_layer_result.packet_count;
  const uint32_t previous_nonempty_delta =
      layer_result.previous_nonempty_packet_count -
      before_layer_result.previous_nonempty_packet_count;
  const uint32_t current_nonempty_delta =
      layer_result.current_nonempty_packet_count -
      before_layer_result.current_nonempty_packet_count;
  const uint32_t issue_delta =
      layer_result.issue_candidate_count - before_layer_result.issue_candidate_count;
  const uint32_t error_delta =
      layer_result.error_count - before_layer_result.error_count;
  out->previous_count_before = previous_count_before;
  out->current_count = layer_result.current_count;
  out->packet_count = packet_delta;
  out->previous_nonempty_packet_count = previous_nonempty_delta;
  out->current_nonempty_packet_count = current_nonempty_delta;
  out->issue_candidate_count = issue_delta;
  out->expected_issue_candidate_count = expected_issue_per_update;
  out->issue_candidate_hash = layer_result.issue_candidate_hash;
  out->first_issue_expert = layer_result.issue_candidate_first_expert;
  out->last_issue_expert = layer_result.issue_candidate_last_expert;
  out->ready = layer_result.ready;
  out->error_count = error_delta;
  out->vectorized_copy_used = layer_result.vectorized_copy_used;
  const bool ok =
      layer_result.checked != 0 && layer_result.ready != 0 &&
      error_delta == 0 && packet_delta == 1 &&
      previous_nonempty_delta == (previous_count_before > 0 ? 1U : 0U) &&
      current_nonempty_delta == (layer_result.current_count > 0 ? 1U : 0U) &&
      issue_delta == expected_issue_per_update;
  out->ok = ok ? 1 : 0;
  out->passed = ok ? 1 : 0;
  out->native_returncode = ok ? 0 : 10;
  return ok ? 0 : 10;
}

extern "C" int premap_payload_cache_inprocess_producer_session_update_v1(
    uint64_t handle,
    uint32_t layer,
    const int32_t* current_experts_device,
    uint32_t current_count,
    uint32_t use_vectorized_copy,
    PremapPayloadCacheInprocessProducerSessionUpdateResultV1* out) {
  return premap_payload_cache_inprocess_producer_session_update_common_v1(
      handle,
      layer,
      current_experts_device,
      current_count,
      nullptr,
      use_vectorized_copy,
      out);
}

extern "C" int premap_payload_cache_inprocess_producer_session_update_count_ptr_v1(
    uint64_t handle,
    uint32_t layer,
    const int32_t* current_experts_device,
    const uint32_t* current_count_device,
    uint32_t use_vectorized_copy,
    PremapPayloadCacheInprocessProducerSessionUpdateResultV1* out) {
  if (current_count_device == nullptr) {
    fill_session_update_safe_defaults(out);
    if (out != nullptr) {
      out->native_stub_invoked = 1;
      out->native_returncode = 247;
    }
    return 247;
  }
  return premap_payload_cache_inprocess_producer_session_update_common_v1(
      handle,
      layer,
      current_experts_device,
      0,
      current_count_device,
      use_vectorized_copy,
      out);
}

extern "C" int premap_payload_cache_inprocess_producer_session_update_generated_v1(
    uint64_t handle,
    uint32_t layer,
    uint32_t step,
    uint32_t step_shift,
    uint32_t layer_stride,
    uint32_t max_num_experts,
    uint32_t use_vectorized_copy,
    PremapPayloadCacheInprocessProducerSessionUpdateResultV1* out) {
  fill_session_update_safe_defaults(out);
  if (out == nullptr) {
    return 250;
  }
  auto* session =
      reinterpret_cast<PremapPayloadCacheInprocessProducerSessionV1*>(handle);
  if (session == nullptr ||
      session->magic != kPremapPayloadCacheInprocessProducerSessionMagicV1) {
    out->native_returncode = 251;
    return 251;
  }
  if (max_num_experts == 0 || layer >= session->layers) {
    out->native_returncode = 252;
    return 252;
  }
  if (hipSetDevice(session->device) != hipSuccess) {
    out->native_returncode = 253;
    return 253;
  }

  std::vector<int32_t> current_host(session->experts_per_layer);
  for (uint32_t expert = 0; expert < session->experts_per_layer; ++expert) {
    current_host[expert] = static_cast<int32_t>(
        (expert + step * step_shift + layer * layer_stride) % max_num_experts);
  }

  int32_t* d_current = nullptr;
  const size_t current_bytes =
      static_cast<size_t>(session->experts_per_layer) * sizeof(int32_t);
  if (hipMalloc(&d_current, current_bytes) != hipSuccess) {
    out->native_returncode = 254;
    return 254;
  }
  if (hipMemcpy(d_current, current_host.data(), current_bytes, hipMemcpyHostToDevice) !=
      hipSuccess) {
    discard_hip_error(hipFree(d_current));
    out->native_returncode = 255;
    return 255;
  }
  const int rc = premap_payload_cache_inprocess_producer_session_update_v1(
      handle,
      layer,
      d_current,
      session->experts_per_layer,
      use_vectorized_copy,
      out);
  discard_hip_error(hipFree(d_current));
  return rc;
}

extern "C" int premap_payload_cache_inprocess_producer_run_v1(
    int device,
    uint32_t steps,
    uint32_t layers,
    uint32_t experts_per_layer,
    uint32_t transition_topk_count,
    uint32_t max_num_experts,
    uint32_t step_shift,
    uint32_t layer_stride,
    uint32_t use_vectorized_copy,
    uint32_t graph_replay,
    PremapPayloadCacheInprocessProducerResultV1* out) {
  fill_safe_defaults(out);
  if (out == nullptr) {
    return 100;
  }
  out->steps = steps;
  out->layers = layers;
  out->experts_per_layer = experts_per_layer;
  out->transition_topk_count = transition_topk_count;
  out->native_graph_replay = graph_replay != 0 ? 1 : 0;
  out->native_stub_invoked = 1;
  out->vectorized_copy_requested = use_vectorized_copy != 0 ? 1 : 0;
  out->persistent_state_on_device = 1;
  out->issue_generation_on_device = 1;

  if (steps <= 1 || layers == 0 || experts_per_layer == 0 ||
      max_num_experts == 0 || steps > 4096 || layers > 4096 ||
      experts_per_layer > 4096) {
    return fail_with_code(out, 101);
  }
  const uint64_t stream_count =
      static_cast<uint64_t>(steps) * layers * experts_per_layer;
  if (stream_count > 16ULL * 1024ULL * 1024ULL) {
    return fail_with_code(out, 102);
  }
  if (hipSetDevice(device) != hipSuccess) {
    return fail_with_code(out, 103);
  }

  std::vector<int32_t> current_stream(static_cast<size_t>(stream_count));
  for (uint32_t step = 0; step < steps; ++step) {
    for (uint32_t layer = 0; layer < layers; ++layer) {
      for (uint32_t expert = 0; expert < experts_per_layer; ++expert) {
        const uint64_t offset =
            (static_cast<uint64_t>(step) * layers + layer) * experts_per_layer +
            expert;
        current_stream[static_cast<size_t>(offset)] = static_cast<int32_t>(
            (expert + step * step_shift + layer * layer_stride) %
            max_num_experts);
      }
    }
  }

  int32_t* d_current_stream = nullptr;
  int32_t* d_previous_state = nullptr;
  uint32_t* d_previous_count = nullptr;
  uint32_t* d_step_state = nullptr;
  InprocessLayerResult* d_layer_results = nullptr;
  hipEvent_t start = nullptr;
  hipEvent_t stop = nullptr;
  hipStream_t stream = nullptr;
  hipGraph_t graph = nullptr;
  hipGraphExec_t graph_exec = nullptr;
  uint32_t capture_active = 0;

  const size_t current_bytes = current_stream.size() * sizeof(int32_t);
  const size_t previous_bytes =
      static_cast<size_t>(layers) * experts_per_layer * sizeof(int32_t);
  const size_t previous_count_bytes = static_cast<size_t>(layers) * sizeof(uint32_t);
  const size_t result_bytes = static_cast<size_t>(layers) * sizeof(InprocessLayerResult);

#define TRY_HIP(EXPR, CODE) \
  do { \
    if ((EXPR) != hipSuccess) { \
      cleanup_active_capture(stream, capture_active); \
      if (graph_exec != nullptr) discard_hip_error(hipGraphExecDestroy(graph_exec)); \
      if (graph != nullptr) discard_hip_error(hipGraphDestroy(graph)); \
      if (start != nullptr) discard_hip_error(hipEventDestroy(start)); \
      if (stop != nullptr) discard_hip_error(hipEventDestroy(stop)); \
      if (stream != nullptr) discard_hip_error(hipStreamDestroy(stream)); \
      if (d_current_stream != nullptr) discard_hip_error(hipFree(d_current_stream)); \
      if (d_previous_state != nullptr) discard_hip_error(hipFree(d_previous_state)); \
      if (d_previous_count != nullptr) discard_hip_error(hipFree(d_previous_count)); \
      if (d_step_state != nullptr) discard_hip_error(hipFree(d_step_state)); \
      if (d_layer_results != nullptr) discard_hip_error(hipFree(d_layer_results)); \
      return fail_with_code(out, CODE); \
    } \
  } while (0)

  TRY_HIP(hipMalloc(&d_current_stream, current_bytes), 110);
  TRY_HIP(hipMalloc(&d_previous_state, previous_bytes), 111);
  TRY_HIP(hipMalloc(&d_previous_count, previous_count_bytes), 112);
  TRY_HIP(hipMalloc(&d_step_state, sizeof(uint32_t)), 113);
  TRY_HIP(hipMalloc(&d_layer_results, result_bytes), 114);
  TRY_HIP(
      hipMemcpy(
          d_current_stream,
          current_stream.data(),
          current_bytes,
          hipMemcpyHostToDevice),
      115);
  TRY_HIP(hipMemset(d_previous_state, 0xff, previous_bytes), 116);
  TRY_HIP(hipMemset(d_previous_count, 0, previous_count_bytes), 117);
  TRY_HIP(hipMemset(d_step_state, 0, sizeof(uint32_t)), 118);

  std::vector<InprocessLayerResult> initial_results(layers);
  for (auto& result : initial_results) {
    result.issue_candidate_first_expert = -1;
    result.issue_candidate_last_expert = -1;
    result.issue_candidate_hash = 0xcbf29ce484222325ULL;
  }
  TRY_HIP(
      hipMemcpy(
          d_layer_results,
          initial_results.data(),
          result_bytes,
          hipMemcpyHostToDevice),
      119);

  TRY_HIP(hipEventCreate(&start), 120);
  TRY_HIP(hipEventCreate(&stop), 121);
  TRY_HIP(hipStreamCreate(&stream), 122);
  TRY_HIP(hipEventRecord(start, stream), 123);

  if (graph_replay != 0) {
    TRY_HIP(hipStreamBeginCapture(stream, hipStreamCaptureModeGlobal), 124);
    capture_active = 1;
    hipLaunchKernelGGL(
        inprocess_transition_step_kernel,
        dim3(layers),
        dim3(128),
        0,
        stream,
        d_current_stream,
        d_previous_state,
        d_previous_count,
        d_layer_results,
        d_step_state,
        steps,
        layers,
        experts_per_layer,
        transition_topk_count,
        use_vectorized_copy);
    TRY_HIP(hipGetLastError(), 125);
    hipLaunchKernelGGL(
        inprocess_step_increment_kernel,
        dim3(1),
        dim3(1),
        0,
        stream,
        d_step_state);
    TRY_HIP(hipGetLastError(), 126);
    TRY_HIP(hipStreamEndCapture(stream, &graph), 127);
    capture_active = 0;
    TRY_HIP(hipGraphInstantiate(&graph_exec, graph, nullptr, nullptr, 0), 128);
    for (uint32_t replay = 0; replay < steps; ++replay) {
      TRY_HIP(hipGraphLaunch(graph_exec, stream), 129);
    }
    TRY_HIP(hipGraphExecDestroy(graph_exec), 130);
    graph_exec = nullptr;
    TRY_HIP(hipGraphDestroy(graph), 131);
    graph = nullptr;
  } else {
    for (uint32_t step = 0; step < steps; ++step) {
      hipLaunchKernelGGL(
          inprocess_transition_step_kernel,
          dim3(layers),
          dim3(128),
          0,
          stream,
          d_current_stream,
          d_previous_state,
          d_previous_count,
          d_layer_results,
          d_step_state,
          steps,
          layers,
          experts_per_layer,
          transition_topk_count,
          use_vectorized_copy);
      TRY_HIP(hipGetLastError(), 132);
      hipLaunchKernelGGL(
          inprocess_step_increment_kernel,
          dim3(1),
          dim3(1),
          0,
          stream,
          d_step_state);
      TRY_HIP(hipGetLastError(), 133);
    }
  }

  TRY_HIP(hipEventRecord(stop, stream), 134);
  TRY_HIP(hipEventSynchronize(stop), 135);
  TRY_HIP(hipEventElapsedTime(&out->gpu_elapsed_ms, start, stop), 136);

  std::vector<InprocessLayerResult> layer_results(layers);
  TRY_HIP(
      hipMemcpy(
          layer_results.data(),
          d_layer_results,
          result_bytes,
          hipMemcpyDeviceToHost),
      137);

  TRY_HIP(hipEventDestroy(start), 138);
  start = nullptr;
  TRY_HIP(hipEventDestroy(stop), 139);
  stop = nullptr;
  TRY_HIP(hipStreamDestroy(stream), 140);
  stream = nullptr;
  TRY_HIP(hipFree(d_current_stream), 141);
  d_current_stream = nullptr;
  TRY_HIP(hipFree(d_previous_state), 142);
  d_previous_state = nullptr;
  TRY_HIP(hipFree(d_previous_count), 143);
  d_previous_count = nullptr;
  TRY_HIP(hipFree(d_step_state), 144);
  d_step_state = nullptr;
  TRY_HIP(hipFree(d_layer_results), 145);
  d_layer_results = nullptr;

#undef TRY_HIP

  uint64_t issue_hash = 0xcbf29ce484222325ULL;
  for (const auto& result : layer_results) {
    out->packet_count += result.packet_count;
    out->previous_nonempty_packet_count += result.previous_nonempty_packet_count;
    out->current_nonempty_packet_count += result.current_nonempty_packet_count;
    out->issue_candidate_count += result.issue_candidate_count;
    out->ready_layer_count += result.ready != 0 ? 1 : 0;
    out->error_count += result.error_count;
    out->vectorized_copy_used =
        out->vectorized_copy_used || result.vectorized_copy_used ? 1 : 0;
    issue_hash =
        inprocess_hash_mix(issue_hash, static_cast<uint32_t>(result.issue_candidate_hash));
    if (out->first_issue_expert < 0 && result.issue_candidate_first_expert >= 0) {
      out->first_issue_expert = result.issue_candidate_first_expert;
    }
    if (result.issue_candidate_last_expert >= 0) {
      out->last_issue_expert = result.issue_candidate_last_expert;
    }
  }
  out->issue_candidate_hash =
      inprocess_hash_mix(issue_hash, static_cast<uint32_t>(out->issue_candidate_count));
  const uint64_t expected_previous_nonempty =
      static_cast<uint64_t>(steps - 1) * layers;
  const uint64_t expected_issue_per_packet =
      transition_topk_count == 0
          ? experts_per_layer
          : std::min(experts_per_layer, transition_topk_count);
  out->expected_issue_candidate_count =
      expected_previous_nonempty * expected_issue_per_packet;
  const bool ok =
      out->ready_layer_count == layers && out->error_count == 0 &&
      out->packet_count == static_cast<uint64_t>(steps) * layers &&
      out->previous_nonempty_packet_count == expected_previous_nonempty &&
      out->issue_candidate_count == out->expected_issue_candidate_count &&
      out->issue_candidate_count > 0;
  out->ok = ok ? 1 : 0;
  out->passed = ok ? 1 : 0;
  out->native_returncode = ok ? 0 : 10;
  return ok ? 0 : 10;
}
