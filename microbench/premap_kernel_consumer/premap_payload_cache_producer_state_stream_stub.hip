#include <hip/hip_runtime.h>

#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
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

struct ProducerTransitionStreamLayerResult {
  uint32_t checked;
  uint32_t ready;
  uint32_t layer_id;
  uint32_t packet_count;
  uint32_t previous_nonempty_packet_count;
  uint32_t current_nonempty_packet_count;
  uint32_t issue_candidate_count;
  uint32_t expected_issue_candidate_count;
  uint32_t transition_topk_count;
  uint32_t experts_per_layer;
  uint32_t vectorized_copy_used;
  uint32_t error_count;
  uint32_t state_override_count;
  uint32_t state_mismatch_count;
  uint32_t issue_expert_mismatch_count;
  int32_t issue_candidate_first_expert;
  int32_t issue_candidate_last_expert;
  uint64_t issue_candidate_hash;
  uint64_t state_hash;
};

struct PacketStreamHeader {
  uint32_t magic;
  uint32_t version;
  uint32_t packet_count;
  uint32_t layer_count;
  uint32_t max_experts_per_packet;
  uint32_t transition_topk_count;
  uint32_t max_num_experts;
  uint32_t reserved;
};

constexpr uint32_t kPacketStreamMagic = 0x5054434dU;  // "MCTP" little endian.
constexpr uint32_t kPacketStreamVersion = 2U;

static void hip_check(hipError_t err, const char* label) {
  if (err != hipSuccess) {
    std::cerr << label << ": " << hipGetErrorString(err) << "\n";
    std::exit(1);
  }
}

__host__ __device__ uint64_t stream_hash_mix(uint64_t value, uint32_t item) {
  value ^= static_cast<uint64_t>(item);
  value *= 0x100000001b3ULL;
  return value;
}

__global__ void producer_transition_stream_kernel(
    const int32_t* __restrict__ current_expert_stream,
    int32_t* __restrict__ previous_expert_state,
    uint32_t* __restrict__ previous_count_state,
    ProducerTransitionStreamLayerResult* __restrict__ layer_results,
    uint32_t step_count,
    uint32_t layer_count,
    uint32_t experts_per_layer,
    uint32_t transition_topk_count,
    uint64_t state_hash_base,
    uint32_t use_vectorized_copy) {
  const uint32_t layer = blockIdx.x;
  if (layer >= layer_count) {
    return;
  }

  __shared__ uint32_t previous_count;
  __shared__ uint64_t issue_hash;
  __shared__ uint32_t issue_count;
  __shared__ int32_t issue_first;
  __shared__ int32_t issue_last;
  __shared__ uint32_t error_count;
  __shared__ uint32_t vectorized_copy_seen;

  int32_t* previous_base = previous_expert_state + layer * experts_per_layer;
  uint32_t* previous_count_ptr = previous_count_state + layer;

  if (threadIdx.x == 0) {
    previous_count = *previous_count_ptr;
    issue_hash = 0xcbf29ce484222325ULL;
    issue_count = 0;
    issue_first = -1;
    issue_last = -1;
    error_count = 0;
    vectorized_copy_seen = 0;
  }
  __syncthreads();

  for (uint32_t step = 0; step < step_count; ++step) {
    const int32_t* current_base =
        current_expert_stream +
        (static_cast<uint64_t>(step) * layer_count + layer) * experts_per_layer;

    if (threadIdx.x == 0) {
      const uint32_t issue_limit =
          transition_topk_count == 0
              ? previous_count
              : (previous_count < transition_topk_count ? previous_count
                                                        : transition_topk_count);
      for (uint32_t i = 0; i < issue_limit; ++i) {
        const int32_t expert = previous_base[i];
        if (expert < 0) {
          error_count += 1;
          continue;
        }
        if (issue_count == 0) {
          issue_first = expert;
        }
        issue_last = expert;
        issue_hash = stream_hash_mix(issue_hash, static_cast<uint32_t>(expert));
        issue_count += 1;
      }
      issue_hash = stream_hash_mix(issue_hash, issue_limit);
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
      previous_count = experts_per_layer;
      *previous_count_ptr = experts_per_layer;
    }
    __syncthreads();
  }

  if (threadIdx.x == 0) {
    ProducerTransitionStreamLayerResult result{};
    result.checked = 1;
    result.ready = error_count == 0 ? 1 : 0;
    result.layer_id = layer;
    result.packet_count = step_count;
    result.previous_nonempty_packet_count = step_count == 0 ? 0 : step_count - 1;
    result.current_nonempty_packet_count = step_count;
    result.issue_candidate_count = issue_count;
    result.transition_topk_count = transition_topk_count;
    result.experts_per_layer = experts_per_layer;
    result.vectorized_copy_used = vectorized_copy_seen;
    result.error_count = error_count;
    result.issue_candidate_first_expert = issue_first;
    result.issue_candidate_last_expert = issue_last;
    result.issue_candidate_hash = issue_hash;
    result.state_hash = stream_hash_mix(state_hash_base, layer);
    layer_results[layer] = result;
  }
}

__global__ void producer_transition_step_kernel(
    const int32_t* __restrict__ current_expert_stream,
    int32_t* __restrict__ previous_expert_state,
    uint32_t* __restrict__ previous_count_state,
    ProducerTransitionStreamLayerResult* __restrict__ layer_results,
    const uint32_t* __restrict__ step_state,
    uint32_t step_count,
    uint32_t layer_count,
    uint32_t experts_per_layer,
    uint32_t transition_topk_count,
    uint64_t state_hash_base,
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
  ProducerTransitionStreamLayerResult* result = layer_results + layer;
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
          stream_hash_mix(local_issue_hash, static_cast<uint32_t>(expert));
      local_issue_count += 1;
    }
    local_issue_hash = stream_hash_mix(local_issue_hash, issue_limit);
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
    result->layer_id = layer;
    result->packet_count += 1;
    result->previous_nonempty_packet_count += previous_count > 0 ? 1 : 0;
    result->current_nonempty_packet_count += 1;
    result->issue_candidate_count += local_issue_count;
    result->transition_topk_count = transition_topk_count;
    result->experts_per_layer = experts_per_layer;
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
        stream_hash_mix(result->issue_candidate_hash, static_cast<uint32_t>(local_issue_hash));
    result->state_hash = stream_hash_mix(state_hash_base, layer);
    result->ready = result->error_count == 0 ? 1 : 0;
  }
}

__global__ void producer_transition_step_increment_kernel(
    uint32_t* __restrict__ step_state) {
  if (threadIdx.x == 0 && blockIdx.x == 0) {
    *step_state += 1;
  }
}

__global__ void producer_transition_packet_step_kernel(
    const uint32_t* __restrict__ packet_layer_ids,
    const uint32_t* __restrict__ packet_current_counts,
    const uint32_t* __restrict__ packet_previous_counts,
    const uint32_t* __restrict__ packet_issue_counts,
    const uint32_t* __restrict__ packet_state_override_flags,
    const int32_t* __restrict__ packet_current_experts,
    const int32_t* __restrict__ packet_previous_experts,
    const int32_t* __restrict__ packet_issue_experts,
    int32_t* __restrict__ previous_expert_state,
    uint32_t* __restrict__ previous_count_state,
    ProducerTransitionStreamLayerResult* __restrict__ aggregate_result,
    const uint32_t* __restrict__ packet_state,
    uint32_t packet_count,
    uint32_t layer_count,
    uint32_t max_experts_per_packet,
    uint32_t transition_topk_count,
    uint64_t state_hash_base,
    uint32_t use_vectorized_copy) {
  const uint32_t packet_index = *packet_state;
  if (packet_index >= packet_count) {
    return;
  }

  const uint32_t layer = packet_layer_ids[packet_index];
  const uint32_t current_count = packet_current_counts[packet_index];
  const uint32_t expected_previous_count = packet_previous_counts[packet_index];
  const uint32_t expected_issue_count = packet_issue_counts[packet_index];
  const uint32_t state_override = packet_state_override_flags[packet_index];
  if (layer >= layer_count || current_count > max_experts_per_packet ||
      expected_previous_count > max_experts_per_packet ||
      expected_issue_count > max_experts_per_packet ||
      state_override > 1U) {
    if (threadIdx.x == 0) {
      aggregate_result->checked = 1;
      aggregate_result->error_count += 1;
      aggregate_result->ready = 0;
    }
    return;
  }

  __shared__ uint32_t previous_count;
  __shared__ uint32_t issue_limit;
  __shared__ uint64_t local_issue_hash;
  __shared__ uint32_t local_issue_count;
  __shared__ uint32_t local_expected_issue_count;
  __shared__ int32_t local_issue_first;
  __shared__ int32_t local_issue_last;
  __shared__ uint32_t local_error_count;
  __shared__ uint32_t local_state_mismatch_count;
  __shared__ uint32_t local_issue_mismatch_count;
  __shared__ uint32_t vectorized_copy_seen;

  int32_t* previous_base =
      previous_expert_state +
      static_cast<uint64_t>(layer) * max_experts_per_packet;
  uint32_t* previous_count_ptr = previous_count_state + layer;
  const int32_t* current_base =
      packet_current_experts +
      static_cast<uint64_t>(packet_index) * max_experts_per_packet;
  const int32_t* expected_previous_base =
      packet_previous_experts +
      static_cast<uint64_t>(packet_index) * max_experts_per_packet;
  const int32_t* expected_issue_base =
      packet_issue_experts +
      static_cast<uint64_t>(packet_index) * max_experts_per_packet;

  if (state_override != 0) {
    for (uint32_t i = threadIdx.x; i < expected_previous_count; i += blockDim.x) {
      previous_base[i] = expected_previous_base[i];
    }
  }
  __syncthreads();

  if (threadIdx.x == 0) {
    if (state_override != 0) {
      *previous_count_ptr = expected_previous_count;
    }
    previous_count = *previous_count_ptr;
    if (previous_count > max_experts_per_packet) {
      previous_count = max_experts_per_packet;
      local_error_count = 1;
    } else {
      local_error_count = 0;
    }
    local_state_mismatch_count = 0;
    if (previous_count != expected_previous_count) {
      local_state_mismatch_count += 1;
      local_error_count += 1;
    }
    issue_limit = transition_topk_count == 0
                      ? previous_count
                      : (previous_count < transition_topk_count
                             ? previous_count
                             : transition_topk_count);
    local_expected_issue_count = expected_issue_count;
    if (issue_limit != local_expected_issue_count) {
      local_issue_mismatch_count = 1;
      local_error_count += 1;
    } else {
      local_issue_mismatch_count = 0;
    }
    local_issue_hash = 0xcbf29ce484222325ULL;
    local_issue_count = 0;
    local_issue_first = -1;
    local_issue_last = -1;
    vectorized_copy_seen = 0;
    for (uint32_t i = 0; i < issue_limit; ++i) {
      const int32_t expert = previous_base[i];
      const int32_t expected_expert =
          i < expected_issue_count ? expected_issue_base[i] : -1;
      if (expert < 0) {
        local_error_count += 1;
        continue;
      }
      if (i < expected_previous_count && expected_previous_base[i] != expert) {
        local_state_mismatch_count += 1;
        local_error_count += 1;
      }
      if (expert != expected_expert) {
        local_issue_mismatch_count += 1;
        local_error_count += 1;
      }
      if (local_issue_count == 0) {
        local_issue_first = expert;
      }
      local_issue_last = expert;
      local_issue_hash =
          stream_hash_mix(local_issue_hash, static_cast<uint32_t>(expert));
      local_issue_count += 1;
    }
    for (uint32_t i = issue_limit; i < expected_previous_count; ++i) {
      if (previous_base[i] != expected_previous_base[i]) {
        local_state_mismatch_count += 1;
        local_error_count += 1;
      }
    }
    local_issue_hash = stream_hash_mix(local_issue_hash, issue_limit);
  }
  __syncthreads();

  const bool aligned_for_int4 =
      reinterpret_cast<uintptr_t>(current_base) % alignof(int4) == 0 &&
      reinterpret_cast<uintptr_t>(previous_base) % alignof(int4) == 0;
  if (use_vectorized_copy != 0 && current_count % 4 == 0 &&
      aligned_for_int4) {
    if (threadIdx.x == 0) {
      vectorized_copy_seen = 1;
    }
    const uint32_t vec_count = current_count / 4;
    const int4* current_vec = reinterpret_cast<const int4*>(current_base);
    int4* previous_vec = reinterpret_cast<int4*>(previous_base);
    for (uint32_t vec = threadIdx.x; vec < vec_count; vec += blockDim.x) {
      previous_vec[vec] = current_vec[vec];
    }
  } else {
    for (uint32_t i = threadIdx.x; i < current_count; i += blockDim.x) {
      previous_base[i] = current_base[i];
    }
  }
  __syncthreads();

  if (threadIdx.x == 0) {
    *previous_count_ptr = current_count;
    aggregate_result->checked = 1;
    aggregate_result->layer_id = layer;
    aggregate_result->packet_count += 1;
    aggregate_result->previous_nonempty_packet_count +=
        previous_count > 0 ? 1 : 0;
    aggregate_result->current_nonempty_packet_count +=
        current_count > 0 ? 1 : 0;
    aggregate_result->issue_candidate_count += local_issue_count;
    aggregate_result->expected_issue_candidate_count += local_expected_issue_count;
    aggregate_result->transition_topk_count = transition_topk_count;
    aggregate_result->experts_per_layer = max_experts_per_packet;
    aggregate_result->vectorized_copy_used =
        aggregate_result->vectorized_copy_used || vectorized_copy_seen ? 1 : 0;
    aggregate_result->error_count += local_error_count;
    aggregate_result->state_override_count += state_override != 0 ? 1 : 0;
    aggregate_result->state_mismatch_count += local_state_mismatch_count;
    aggregate_result->issue_expert_mismatch_count += local_issue_mismatch_count;
    if (local_issue_first >= 0 &&
        aggregate_result->issue_candidate_first_expert < 0) {
      aggregate_result->issue_candidate_first_expert = local_issue_first;
    }
    if (local_issue_last >= 0) {
      aggregate_result->issue_candidate_last_expert = local_issue_last;
    }
    aggregate_result->issue_candidate_hash =
        stream_hash_mix(
            aggregate_result->issue_candidate_hash,
            static_cast<uint32_t>(local_issue_hash));
    aggregate_result->state_hash = stream_hash_mix(state_hash_base, layer);
    aggregate_result->ready = aggregate_result->error_count == 0 ? 1 : 0;
  }
}

struct Args {
  int device = 0;
  uint32_t steps = 64;
  uint32_t layers = 40;
  uint32_t experts_per_layer = 8;
  uint32_t transition_topk_count = 8;
  uint32_t max_num_experts = 256;
  uint32_t step_shift = 1;
  uint32_t layer_stride = 17;
  uint32_t use_vectorized_copy = 1;
  uint32_t graph_replay = 0;
  uint64_t state_hash_base = 0x8a45d2c91fe01237ULL;
  std::string packet_stream_path;
};

static uint32_t parse_bounded_u32(
    const char* raw,
    const char* name,
    uint32_t max_value = 65536U) {
  const std::string text(raw == nullptr ? "" : raw);
  if (text.empty() || text[0] == '-') {
    std::cerr << name << " must be a non-negative integer\n";
    std::exit(2);
  }
  char* end = nullptr;
  const unsigned long value = std::strtoul(text.c_str(), &end, 10);
  if (end == text.c_str() || *end != '\0') {
    std::cerr << name << " must be a base-10 integer\n";
    std::exit(2);
  }
  if (value > static_cast<unsigned long>(max_value) ||
      value > static_cast<unsigned long>(std::numeric_limits<uint32_t>::max())) {
    std::cerr << name << " exceeds the native stream canary safety bound\n";
    std::exit(2);
  }
  return static_cast<uint32_t>(value);
}

static uint64_t parse_u64(const char* raw, const char* name) {
  const std::string text(raw == nullptr ? "" : raw);
  if (text.empty() || text[0] == '-') {
    std::cerr << name << " must be a non-negative integer\n";
    std::exit(2);
  }
  char* end = nullptr;
  const int base =
      text.size() > 2 && text[0] == '0' && (text[1] == 'x' || text[1] == 'X')
          ? 16
          : 10;
  errno = 0;
  const unsigned long long value = std::strtoull(text.c_str(), &end, base);
  if (end == text.c_str() || *end != '\0' || errno == ERANGE) {
    std::cerr << name << " must be an unsigned 64-bit integer\n";
    std::exit(2);
  }
  return static_cast<uint64_t>(value);
}

static Args parse_args(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) {
    std::string key(argv[i]);
    auto require_value = [&](const char* name) -> const char* {
      if (i + 1 >= argc) {
        std::cerr << "missing value for " << name << "\n";
        std::exit(2);
      }
      return argv[++i];
    };
    if (key == "--device") {
      args.device = std::atoi(require_value("--device"));
    } else if (key == "--steps") {
      args.steps = parse_bounded_u32(require_value("--steps"), "--steps");
    } else if (key == "--layers") {
      args.layers = parse_bounded_u32(require_value("--layers"), "--layers", 4096U);
    } else if (key == "--experts-per-layer") {
      args.experts_per_layer = parse_bounded_u32(
          require_value("--experts-per-layer"), "--experts-per-layer", 4096U);
    } else if (key == "--transition-topk-count") {
      args.transition_topk_count = parse_bounded_u32(
          require_value("--transition-topk-count"), "--transition-topk-count");
    } else if (key == "--max-num-experts") {
      args.max_num_experts = parse_bounded_u32(
          require_value("--max-num-experts"), "--max-num-experts");
    } else if (key == "--step-shift") {
      args.step_shift =
          parse_bounded_u32(require_value("--step-shift"), "--step-shift");
    } else if (key == "--layer-stride") {
      args.layer_stride =
          parse_bounded_u32(require_value("--layer-stride"), "--layer-stride");
    } else if (key == "--state-hash-base") {
      args.state_hash_base = parse_u64(
          require_value("--state-hash-base"), "--state-hash-base");
    } else if (key == "--disable-vectorized-copy") {
      args.use_vectorized_copy = 0;
    } else if (key == "--graph-replay") {
      args.graph_replay = 1;
    } else if (key == "--packet-stream-bin") {
      args.packet_stream_path = require_value("--packet-stream-bin");
    } else {
      std::cerr << "unknown argument: " << key << "\n";
      std::exit(2);
    }
  }
  if (args.steps == 0 || args.layers == 0 || args.experts_per_layer == 0) {
    std::cerr << "steps, layers, and experts-per-layer must be positive\n";
    std::exit(2);
  }
  if (args.max_num_experts == 0) {
    std::cerr << "max-num-experts must be positive\n";
    std::exit(2);
  }
  return args;
}

static void load_packet_stream(
    const std::string& path,
    PacketStreamHeader* header,
    std::vector<uint32_t>* packet_layer_ids,
    std::vector<uint32_t>* packet_current_counts,
    std::vector<uint32_t>* packet_previous_counts,
    std::vector<uint32_t>* packet_issue_counts,
    std::vector<uint32_t>* packet_state_override_flags,
    std::vector<int32_t>* packet_current_experts,
    std::vector<int32_t>* packet_previous_experts,
    std::vector<int32_t>* packet_issue_experts) {
  std::ifstream input(path, std::ios::binary);
  if (!input) {
    std::cerr << "could not open packet stream: " << path << "\n";
    std::exit(2);
  }
  input.read(reinterpret_cast<char*>(header), sizeof(PacketStreamHeader));
  if (!input) {
    std::cerr << "could not read packet stream header\n";
    std::exit(2);
  }
  if (header->magic != kPacketStreamMagic ||
      header->version != kPacketStreamVersion) {
    std::cerr << "packet stream header mismatch\n";
    std::exit(2);
  }
  if (header->packet_count == 0 || header->layer_count == 0 ||
      header->max_experts_per_packet == 0 || header->max_num_experts == 0) {
    std::cerr << "packet stream dimensions must be positive\n";
    std::exit(2);
  }
  if (header->packet_count > 65536U || header->layer_count > 4096U ||
      header->max_experts_per_packet > 4096U) {
    std::cerr << "packet stream dimensions exceed canary safety bounds\n";
    std::exit(2);
  }
  const uint64_t expert_count =
      static_cast<uint64_t>(header->packet_count) *
      header->max_experts_per_packet;
  if (expert_count > 16ULL * 1024ULL * 1024ULL) {
    std::cerr << "packet stream experts exceed canary safety bounds\n";
    std::exit(2);
  }
  packet_layer_ids->resize(header->packet_count);
  packet_current_counts->resize(header->packet_count);
  packet_previous_counts->resize(header->packet_count);
  packet_issue_counts->resize(header->packet_count);
  packet_state_override_flags->resize(header->packet_count);
  packet_current_experts->resize(static_cast<size_t>(expert_count));
  packet_previous_experts->resize(static_cast<size_t>(expert_count));
  packet_issue_experts->resize(static_cast<size_t>(expert_count));
  input.read(
      reinterpret_cast<char*>(packet_layer_ids->data()),
      packet_layer_ids->size() * sizeof(uint32_t));
  input.read(
      reinterpret_cast<char*>(packet_current_counts->data()),
      packet_current_counts->size() * sizeof(uint32_t));
  input.read(
      reinterpret_cast<char*>(packet_previous_counts->data()),
      packet_previous_counts->size() * sizeof(uint32_t));
  input.read(
      reinterpret_cast<char*>(packet_issue_counts->data()),
      packet_issue_counts->size() * sizeof(uint32_t));
  input.read(
      reinterpret_cast<char*>(packet_state_override_flags->data()),
      packet_state_override_flags->size() * sizeof(uint32_t));
  input.read(
      reinterpret_cast<char*>(packet_current_experts->data()),
      packet_current_experts->size() * sizeof(int32_t));
  input.read(
      reinterpret_cast<char*>(packet_previous_experts->data()),
      packet_previous_experts->size() * sizeof(int32_t));
  input.read(
      reinterpret_cast<char*>(packet_issue_experts->data()),
      packet_issue_experts->size() * sizeof(int32_t));
  if (!input) {
    std::cerr << "could not read complete packet stream payload\n";
    std::exit(2);
  }
  char trailing = 0;
  if (input.read(&trailing, 1)) {
    std::cerr << "packet stream contains trailing bytes\n";
    std::exit(2);
  }
  for (uint32_t i = 0; i < header->packet_count; ++i) {
    if ((*packet_layer_ids)[i] >= header->layer_count ||
        (*packet_current_counts)[i] > header->max_experts_per_packet ||
        (*packet_previous_counts)[i] > header->max_experts_per_packet ||
        (*packet_issue_counts)[i] > header->max_experts_per_packet) {
      std::cerr << "packet stream row out of bounds\n";
      std::exit(2);
    }
    if ((*packet_state_override_flags)[i] > 1U) {
      std::cerr << "packet stream state override flag out of bounds\n";
      std::exit(2);
    }
    for (uint32_t j = 0; j < (*packet_current_counts)[i]; ++j) {
      const int32_t expert =
          (*packet_current_experts)[
              static_cast<uint64_t>(i) * header->max_experts_per_packet + j];
      if (expert < 0 || static_cast<uint32_t>(expert) >= header->max_num_experts) {
        std::cerr << "packet stream current expert out of bounds\n";
        std::exit(2);
      }
    }
    for (uint32_t j = 0; j < (*packet_previous_counts)[i]; ++j) {
      const int32_t expert =
          (*packet_previous_experts)[
              static_cast<uint64_t>(i) * header->max_experts_per_packet + j];
      if (expert < 0 || static_cast<uint32_t>(expert) >= header->max_num_experts) {
        std::cerr << "packet stream previous expert out of bounds\n";
        std::exit(2);
      }
    }
    for (uint32_t j = 0; j < (*packet_issue_counts)[i]; ++j) {
      const int32_t expert =
          (*packet_issue_experts)[
              static_cast<uint64_t>(i) * header->max_experts_per_packet + j];
      if (expert < 0 || static_cast<uint32_t>(expert) >= header->max_num_experts) {
        std::cerr << "packet stream issue expert out of bounds\n";
        std::exit(2);
      }
    }
  }
}

static int run_packet_stream_mode(const Args& args) {
  PacketStreamHeader header{};
  std::vector<uint32_t> packet_layer_ids;
  std::vector<uint32_t> packet_current_counts;
  std::vector<uint32_t> packet_previous_counts;
  std::vector<uint32_t> packet_issue_counts;
  std::vector<uint32_t> packet_state_override_flags;
  std::vector<int32_t> packet_current_experts;
  std::vector<int32_t> packet_previous_experts;
  std::vector<int32_t> packet_issue_experts;
  load_packet_stream(
      args.packet_stream_path,
      &header,
      &packet_layer_ids,
      &packet_current_counts,
      &packet_previous_counts,
      &packet_issue_counts,
      &packet_state_override_flags,
      &packet_current_experts,
      &packet_previous_experts,
      &packet_issue_experts);

  uint32_t* d_packet_layer_ids = nullptr;
  uint32_t* d_packet_current_counts = nullptr;
  uint32_t* d_packet_previous_counts = nullptr;
  uint32_t* d_packet_issue_counts = nullptr;
  uint32_t* d_packet_state_override_flags = nullptr;
  int32_t* d_packet_current_experts = nullptr;
  int32_t* d_packet_previous_experts = nullptr;
  int32_t* d_packet_issue_experts = nullptr;
  int32_t* d_previous_state = nullptr;
  uint32_t* d_previous_count = nullptr;
  uint32_t* d_packet_state = nullptr;
  ProducerTransitionStreamLayerResult* d_aggregate_result = nullptr;

  const size_t packet_u32_bytes =
      static_cast<size_t>(header.packet_count) * sizeof(uint32_t);
  const size_t expert_bytes =
      packet_current_experts.size() * sizeof(int32_t);
  const size_t previous_bytes =
      static_cast<size_t>(header.layer_count) *
      header.max_experts_per_packet * sizeof(int32_t);
  const size_t previous_count_bytes =
      static_cast<size_t>(header.layer_count) * sizeof(uint32_t);

  hip_check(hipMalloc(&d_packet_layer_ids, packet_u32_bytes),
            "hipMalloc packet layer ids");
  hip_check(hipMalloc(&d_packet_current_counts, packet_u32_bytes),
            "hipMalloc packet current counts");
  hip_check(hipMalloc(&d_packet_previous_counts, packet_u32_bytes),
            "hipMalloc packet previous counts");
  hip_check(hipMalloc(&d_packet_issue_counts, packet_u32_bytes),
            "hipMalloc packet issue counts");
  hip_check(hipMalloc(&d_packet_state_override_flags, packet_u32_bytes),
            "hipMalloc packet state override flags");
  hip_check(hipMalloc(&d_packet_current_experts, expert_bytes),
            "hipMalloc packet current experts");
  hip_check(hipMalloc(&d_packet_previous_experts, expert_bytes),
            "hipMalloc packet previous experts");
  hip_check(hipMalloc(&d_packet_issue_experts, expert_bytes),
            "hipMalloc packet issue experts");
  hip_check(hipMalloc(&d_previous_state, previous_bytes),
            "hipMalloc packet previous state");
  hip_check(hipMalloc(&d_previous_count, previous_count_bytes),
            "hipMalloc packet previous count");
  hip_check(hipMalloc(&d_packet_state, sizeof(uint32_t)),
            "hipMalloc packet state");
  hip_check(hipMalloc(&d_aggregate_result, sizeof(ProducerTransitionStreamLayerResult)),
            "hipMalloc packet aggregate result");

  hip_check(
      hipMemcpy(
          d_packet_layer_ids,
          packet_layer_ids.data(),
          packet_u32_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy packet layer ids");
  hip_check(
      hipMemcpy(
          d_packet_current_counts,
          packet_current_counts.data(),
          packet_u32_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy packet current counts");
  hip_check(
      hipMemcpy(
          d_packet_previous_counts,
          packet_previous_counts.data(),
          packet_u32_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy packet previous counts");
  hip_check(
      hipMemcpy(
          d_packet_issue_counts,
          packet_issue_counts.data(),
          packet_u32_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy packet issue counts");
  hip_check(
      hipMemcpy(
          d_packet_state_override_flags,
          packet_state_override_flags.data(),
          packet_u32_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy packet state override flags");
  hip_check(
      hipMemcpy(
          d_packet_current_experts,
          packet_current_experts.data(),
          expert_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy packet current experts");
  hip_check(
      hipMemcpy(
          d_packet_previous_experts,
          packet_previous_experts.data(),
          expert_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy packet previous experts");
  hip_check(
      hipMemcpy(
          d_packet_issue_experts,
          packet_issue_experts.data(),
          expert_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy packet issue experts");
  hip_check(hipMemset(d_previous_state, 0xff, previous_bytes),
            "hipMemset packet previous state");
  hip_check(hipMemset(d_previous_count, 0, previous_count_bytes),
            "hipMemset packet previous count");
  hip_check(hipMemset(d_packet_state, 0, sizeof(uint32_t)),
            "hipMemset packet state");

  ProducerTransitionStreamLayerResult initial{};
  initial.issue_candidate_first_expert = -1;
  initial.issue_candidate_last_expert = -1;
  initial.issue_candidate_hash = 0xcbf29ce484222325ULL;
  hip_check(
      hipMemcpy(
          d_aggregate_result,
          &initial,
          sizeof(ProducerTransitionStreamLayerResult),
          hipMemcpyHostToDevice),
      "hipMemcpy packet aggregate result");

  hipEvent_t start;
  hipEvent_t stop;
  hip_check(hipEventCreate(&start), "hipEventCreate packet start");
  hip_check(hipEventCreate(&stop), "hipEventCreate packet stop");
  hipStream_t stream = nullptr;
  hip_check(hipStreamCreate(&stream), "hipStreamCreate packet");
  hip_check(hipEventRecord(start, stream), "hipEventRecord packet start");
  if (args.graph_replay != 0) {
    hipGraph_t graph = nullptr;
    hipGraphExec_t graph_exec = nullptr;
    hip_check(
        hipStreamBeginCapture(stream, hipStreamCaptureModeGlobal),
        "hipStreamBeginCapture packet transition step");
    hipLaunchKernelGGL(
        producer_transition_packet_step_kernel,
        dim3(1),
        dim3(128),
        0,
        stream,
        d_packet_layer_ids,
        d_packet_current_counts,
        d_packet_previous_counts,
        d_packet_issue_counts,
        d_packet_state_override_flags,
        d_packet_current_experts,
        d_packet_previous_experts,
        d_packet_issue_experts,
        d_previous_state,
        d_previous_count,
        d_aggregate_result,
        d_packet_state,
        header.packet_count,
        header.layer_count,
        header.max_experts_per_packet,
        header.transition_topk_count,
        args.state_hash_base,
        args.use_vectorized_copy);
    hip_check(hipGetLastError(), "producer_transition_packet_step_kernel capture launch");
    hipLaunchKernelGGL(
        producer_transition_step_increment_kernel,
        dim3(1),
        dim3(1),
        0,
        stream,
        d_packet_state);
    hip_check(
        hipGetLastError(),
        "producer_transition_packet_step_increment_kernel capture launch");
    hip_check(
        hipStreamEndCapture(stream, &graph),
        "hipStreamEndCapture packet transition step");
    hip_check(
        hipGraphInstantiate(&graph_exec, graph, nullptr, nullptr, 0),
        "hipGraphInstantiate packet transition step");
    for (uint32_t replay = 0; replay < header.packet_count; ++replay) {
      hip_check(
          hipGraphLaunch(graph_exec, stream),
          "hipGraphLaunch packet transition step");
    }
    hip_check(hipGraphExecDestroy(graph_exec), "hipGraphExecDestroy packet");
    hip_check(hipGraphDestroy(graph), "hipGraphDestroy packet");
  } else {
    for (uint32_t packet = 0; packet < header.packet_count; ++packet) {
      hipLaunchKernelGGL(
          producer_transition_packet_step_kernel,
          dim3(1),
          dim3(128),
          0,
          stream,
          d_packet_layer_ids,
          d_packet_current_counts,
          d_packet_previous_counts,
          d_packet_issue_counts,
          d_packet_state_override_flags,
          d_packet_current_experts,
          d_packet_previous_experts,
          d_packet_issue_experts,
          d_previous_state,
          d_previous_count,
          d_aggregate_result,
          d_packet_state,
          header.packet_count,
          header.layer_count,
          header.max_experts_per_packet,
          header.transition_topk_count,
          args.state_hash_base,
          args.use_vectorized_copy);
      hip_check(hipGetLastError(), "producer_transition_packet_step_kernel launch");
      hipLaunchKernelGGL(
          producer_transition_step_increment_kernel,
          dim3(1),
          dim3(1),
          0,
          stream,
          d_packet_state);
      hip_check(
          hipGetLastError(),
          "producer_transition_packet_step_increment_kernel launch");
    }
  }
  hip_check(hipEventRecord(stop, stream), "hipEventRecord packet stop");
  hip_check(hipEventSynchronize(stop), "hipEventSynchronize packet stop");
  float elapsed_ms = 0.0f;
  hip_check(hipEventElapsedTime(&elapsed_ms, start, stop),
            "hipEventElapsedTime packet");

  ProducerTransitionStreamLayerResult result{};
  hip_check(
      hipMemcpy(
          &result,
          d_aggregate_result,
          sizeof(ProducerTransitionStreamLayerResult),
          hipMemcpyDeviceToHost),
      "hipMemcpy packet aggregate result");

  hip_check(hipEventDestroy(start), "hipEventDestroy packet start");
  hip_check(hipEventDestroy(stop), "hipEventDestroy packet stop");
  hip_check(hipStreamDestroy(stream), "hipStreamDestroy packet");
  hip_check(hipFree(d_packet_layer_ids), "hipFree packet layer ids");
  hip_check(hipFree(d_packet_current_counts), "hipFree packet current counts");
  hip_check(hipFree(d_packet_previous_counts), "hipFree packet previous counts");
  hip_check(hipFree(d_packet_issue_counts), "hipFree packet issue counts");
  hip_check(
      hipFree(d_packet_state_override_flags),
      "hipFree packet state override flags");
  hip_check(hipFree(d_packet_current_experts), "hipFree packet current experts");
  hip_check(hipFree(d_packet_previous_experts), "hipFree packet previous experts");
  hip_check(hipFree(d_packet_issue_experts), "hipFree packet issue experts");
  hip_check(hipFree(d_previous_state), "hipFree packet previous state");
  hip_check(hipFree(d_previous_count), "hipFree packet previous count");
  hip_check(hipFree(d_packet_state), "hipFree packet state");
  hip_check(hipFree(d_aggregate_result), "hipFree packet aggregate result");

  uint64_t state_override_count = 0;
  uint64_t nonempty_current_packet_count = 0;
  for (uint32_t i = 0; i < header.packet_count; ++i) {
    state_override_count += packet_state_override_flags[i] != 0 ? 1 : 0;
    nonempty_current_packet_count += packet_current_counts[i] != 0 ? 1 : 0;
  }

  const bool ok = result.ready != 0 && result.error_count == 0 &&
                  result.packet_count == header.packet_count &&
                  result.current_nonempty_packet_count ==
                      nonempty_current_packet_count &&
                  result.issue_candidate_count == result.expected_issue_candidate_count &&
                  result.issue_candidate_count > 0 &&
                  result.state_mismatch_count == 0 &&
                  result.issue_expert_mismatch_count == 0 &&
                  result.state_override_count == state_override_count;

  std::cout << "{";
  std::cout << "\"ok\":" << (ok ? "true" : "false");
  std::cout << ",\"passed\":" << (ok ? "true" : "false");
  std::cout << ",\"mode\":\"payload_cache_producer_transition_state_packet_stream_native_canary\"";
  std::cout << ",\"packet_stream_input\":true";
  std::cout << ",\"native_graph_replay\":"
            << (args.graph_replay ? "true" : "false");
  std::cout << ",\"abi_name\":\""
            << kPremapPayloadCacheProducerTransitionStateAbiV1Name << "\"";
  std::cout << ",\"abi_field_count\":"
            << kPremapPayloadCacheProducerTransitionStateAbiV1FieldCount;
  std::cout << ",\"steps\":" << header.packet_count;
  std::cout << ",\"layers\":" << header.layer_count;
  std::cout << ",\"experts_per_layer\":" << header.max_experts_per_packet;
  std::cout << ",\"max_experts_per_packet\":"
            << header.max_experts_per_packet;
  std::cout << ",\"max_num_experts\":" << header.max_num_experts;
  std::cout << ",\"transition_topk_count\":"
            << header.transition_topk_count;
  std::cout << ",\"packet_count\":" << result.packet_count;
  std::cout << ",\"state_override_count\":" << result.state_override_count;
  std::cout << ",\"expected_state_override_count\":" << state_override_count;
  std::cout << ",\"previous_nonempty_packet_count\":"
            << result.previous_nonempty_packet_count;
  std::cout << ",\"current_nonempty_packet_count\":"
            << result.current_nonempty_packet_count;
  std::cout << ",\"issue_candidate_count\":"
            << result.issue_candidate_count;
  std::cout << ",\"expected_issue_candidate_count\":"
            << result.expected_issue_candidate_count;
  std::cout << ",\"state_mismatch_count\":"
            << result.state_mismatch_count;
  std::cout << ",\"issue_expert_mismatch_count\":"
            << result.issue_expert_mismatch_count;
  std::cout << ",\"first_issue_expert\":"
            << result.issue_candidate_first_expert;
  std::cout << ",\"last_issue_expert\":"
            << result.issue_candidate_last_expert;
  std::cout << ",\"issue_candidate_hash\":\"" << std::hex << std::setfill('0')
            << std::setw(16) << result.issue_candidate_hash << std::dec
            << std::setfill(' ') << "\"";
  std::cout << ",\"error_count\":" << result.error_count;
  std::cout << ",\"gpu_elapsed_ms\":" << std::fixed << std::setprecision(6)
            << elapsed_ms;
  std::cout << ",\"persistent_state_on_device\":true";
  std::cout << ",\"issue_generation_on_device\":true";
  std::cout << ",\"vectorized_copy_requested\":"
            << (args.use_vectorized_copy ? "true" : "false");
  std::cout << ",\"vectorized_copy_used\":"
            << (result.vectorized_copy_used != 0 ? "true" : "false");
  std::cout << ",\"payload_bytes\":0";
  std::cout << ",\"payload_transfer_enabled\":false";
  std::cout << ",\"payload_deref_allowed\":false";
  std::cout << ",\"ready_credit\":false";
  std::cout << ",\"ready_before_demand_credit\":false";
  std::cout << ",\"real_ready_credit_granted\":false";
  std::cout << ",\"kernel_arg_pass\":false";
  std::cout << ",\"kernel_arg_pass_allowed\":false";
  std::cout << ",\"passed_to_kernel\":false";
  std::cout << ",\"changes_kernel_launch_args\":false";
  std::cout << ",\"current_wna16_arg_compatible\":false";
  std::cout << ",\"uses_current_wna16_args\":false";
  std::cout << ",\"passes_current_wna16_args\":false";
  std::cout << ",\"measures_tpot\":false";
  std::cout << ",\"measures_vllm_latency\":false";
  std::cout << ",\"native_stub_invoked\":true";
  std::cout << "}\n";
  return ok ? 0 : 1;
}

int main(int argc, char** argv) {
  const Args args = parse_args(argc, argv);
  hip_check(hipSetDevice(args.device), "hipSetDevice");
  if (!args.packet_stream_path.empty()) {
    return run_packet_stream_mode(args);
  }

  const uint64_t stream_count =
      static_cast<uint64_t>(args.steps) * args.layers * args.experts_per_layer;
  if (stream_count > 16ULL * 1024ULL * 1024ULL) {
    std::cerr << "requested stream exceeds native stream canary safety bound\n";
    return 2;
  }

  std::vector<int32_t> current_stream(static_cast<size_t>(stream_count));
  for (uint32_t step = 0; step < args.steps; ++step) {
    for (uint32_t layer = 0; layer < args.layers; ++layer) {
      for (uint32_t expert = 0; expert < args.experts_per_layer; ++expert) {
        const uint64_t offset =
            (static_cast<uint64_t>(step) * args.layers + layer) *
                args.experts_per_layer +
            expert;
        current_stream[static_cast<size_t>(offset)] = static_cast<int32_t>(
            (expert + step * args.step_shift + layer * args.layer_stride) %
            args.max_num_experts);
      }
    }
  }

  int32_t* d_current_stream = nullptr;
  int32_t* d_previous_state = nullptr;
  uint32_t* d_previous_count = nullptr;
  uint32_t* d_step_state = nullptr;
  ProducerTransitionStreamLayerResult* d_layer_results = nullptr;

  const size_t current_bytes = current_stream.size() * sizeof(int32_t);
  const size_t previous_bytes =
      static_cast<size_t>(args.layers) * args.experts_per_layer * sizeof(int32_t);
  const size_t previous_count_bytes = static_cast<size_t>(args.layers) * sizeof(uint32_t);
  const size_t result_bytes =
      static_cast<size_t>(args.layers) * sizeof(ProducerTransitionStreamLayerResult);

  hip_check(hipMalloc(&d_current_stream, current_bytes), "hipMalloc current stream");
  hip_check(hipMalloc(&d_previous_state, previous_bytes), "hipMalloc previous state");
  hip_check(hipMalloc(&d_previous_count, previous_count_bytes),
            "hipMalloc previous count");
  hip_check(hipMalloc(&d_step_state, sizeof(uint32_t)), "hipMalloc step state");
  hip_check(hipMalloc(&d_layer_results, result_bytes), "hipMalloc layer results");
  hip_check(
      hipMemcpy(
          d_current_stream,
          current_stream.data(),
          current_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy current stream");
  hip_check(hipMemset(d_previous_state, 0xff, previous_bytes),
            "hipMemset previous state");
  hip_check(hipMemset(d_previous_count, 0, previous_count_bytes),
            "hipMemset previous count");
  hip_check(hipMemset(d_step_state, 0, sizeof(uint32_t)), "hipMemset step state");
  std::vector<ProducerTransitionStreamLayerResult> initial_results(args.layers);
  for (auto& result : initial_results) {
    result.issue_candidate_first_expert = -1;
    result.issue_candidate_last_expert = -1;
    result.issue_candidate_hash = 0xcbf29ce484222325ULL;
  }
  hip_check(
      hipMemcpy(
          d_layer_results,
          initial_results.data(),
          result_bytes,
          hipMemcpyHostToDevice),
      "hipMemcpy initial layer results");

  hipEvent_t start;
  hipEvent_t stop;
  hip_check(hipEventCreate(&start), "hipEventCreate start");
  hip_check(hipEventCreate(&stop), "hipEventCreate stop");
  hipStream_t stream = nullptr;
  hip_check(hipStreamCreate(&stream), "hipStreamCreate");
  hip_check(hipEventRecord(start, stream), "hipEventRecord start");
  if (args.graph_replay != 0) {
    hipGraph_t graph = nullptr;
    hipGraphExec_t graph_exec = nullptr;
    hip_check(
        hipStreamBeginCapture(stream, hipStreamCaptureModeGlobal),
        "hipStreamBeginCapture producer transition step");
    hipLaunchKernelGGL(
        producer_transition_step_kernel,
        dim3(args.layers),
        dim3(128),
        0,
        stream,
        d_current_stream,
        d_previous_state,
        d_previous_count,
        d_layer_results,
        d_step_state,
        args.steps,
        args.layers,
        args.experts_per_layer,
        args.transition_topk_count,
        args.state_hash_base,
        args.use_vectorized_copy);
    hip_check(hipGetLastError(), "producer_transition_step_kernel capture launch");
    hipLaunchKernelGGL(
        producer_transition_step_increment_kernel,
        dim3(1),
        dim3(1),
        0,
        stream,
        d_step_state);
    hip_check(
        hipGetLastError(), "producer_transition_step_increment_kernel capture launch");
    hip_check(
        hipStreamEndCapture(stream, &graph),
        "hipStreamEndCapture producer transition step");
    hip_check(
        hipGraphInstantiate(&graph_exec, graph, nullptr, nullptr, 0),
        "hipGraphInstantiate producer transition step");
    for (uint32_t replay = 0; replay < args.steps; ++replay) {
      hip_check(
          hipGraphLaunch(graph_exec, stream),
          "hipGraphLaunch producer transition step");
    }
    hip_check(hipGraphExecDestroy(graph_exec), "hipGraphExecDestroy");
    hip_check(hipGraphDestroy(graph), "hipGraphDestroy");
  } else {
    hipLaunchKernelGGL(
        producer_transition_stream_kernel,
        dim3(args.layers),
        dim3(128),
        0,
        stream,
        d_current_stream,
        d_previous_state,
        d_previous_count,
        d_layer_results,
        args.steps,
        args.layers,
        args.experts_per_layer,
        args.transition_topk_count,
        args.state_hash_base,
        args.use_vectorized_copy);
    hip_check(hipGetLastError(), "producer_transition_stream_kernel launch");
  }
  hip_check(hipEventRecord(stop, stream), "hipEventRecord stop");
  hip_check(hipEventSynchronize(stop), "hipEventSynchronize stop");
  float elapsed_ms = 0.0f;
  hip_check(hipEventElapsedTime(&elapsed_ms, start, stop), "hipEventElapsedTime");

  std::vector<ProducerTransitionStreamLayerResult> layer_results(args.layers);
  hip_check(
      hipMemcpy(
          layer_results.data(),
          d_layer_results,
          result_bytes,
          hipMemcpyDeviceToHost),
      "hipMemcpy layer results");

  hip_check(hipEventDestroy(start), "hipEventDestroy start");
  hip_check(hipEventDestroy(stop), "hipEventDestroy stop");
  hip_check(hipStreamDestroy(stream), "hipStreamDestroy");
  hip_check(hipFree(d_current_stream), "hipFree current stream");
  hip_check(hipFree(d_previous_state), "hipFree previous state");
  hip_check(hipFree(d_previous_count), "hipFree previous count");
  hip_check(hipFree(d_step_state), "hipFree step state");
  hip_check(hipFree(d_layer_results), "hipFree layer results");

  uint64_t packet_count = 0;
  uint64_t previous_nonempty_packet_count = 0;
  uint64_t current_nonempty_packet_count = 0;
  uint64_t issue_candidate_count = 0;
  uint64_t ready_layer_count = 0;
  uint64_t error_count = 0;
  uint64_t issue_hash = 0xcbf29ce484222325ULL;
  int32_t first_issue_expert = -1;
  int32_t last_issue_expert = -1;
  bool vectorized_copy_used = false;
  for (const auto& result : layer_results) {
    packet_count += result.packet_count;
    previous_nonempty_packet_count += result.previous_nonempty_packet_count;
    current_nonempty_packet_count += result.current_nonempty_packet_count;
    issue_candidate_count += result.issue_candidate_count;
    ready_layer_count += result.ready != 0 ? 1 : 0;
    error_count += result.error_count;
    issue_hash = stream_hash_mix(issue_hash, static_cast<uint32_t>(result.issue_candidate_hash));
    vectorized_copy_used = vectorized_copy_used || result.vectorized_copy_used != 0;
    if (first_issue_expert < 0 && result.issue_candidate_first_expert >= 0) {
      first_issue_expert = result.issue_candidate_first_expert;
    }
    if (result.issue_candidate_last_expert >= 0) {
      last_issue_expert = result.issue_candidate_last_expert;
    }
  }
  issue_hash = stream_hash_mix(issue_hash, static_cast<uint32_t>(issue_candidate_count));

  const uint64_t expected_previous_nonempty =
      args.steps == 0 ? 0ULL : static_cast<uint64_t>(args.steps - 1) * args.layers;
  const uint64_t expected_issue_per_packet =
      args.transition_topk_count == 0
          ? args.experts_per_layer
          : std::min(args.experts_per_layer, args.transition_topk_count);
  const uint64_t expected_issue_candidate_count =
      expected_previous_nonempty * expected_issue_per_packet;
  const bool ok = ready_layer_count == args.layers && error_count == 0 &&
                  packet_count == static_cast<uint64_t>(args.steps) * args.layers &&
                  previous_nonempty_packet_count == expected_previous_nonempty &&
                  issue_candidate_count == expected_issue_candidate_count &&
                  issue_candidate_count > 0;

  std::cout << "{";
  std::cout << "\"ok\":" << (ok ? "true" : "false");
  std::cout << ",\"passed\":" << (ok ? "true" : "false");
  std::cout << ",\"mode\":\"payload_cache_producer_transition_state_stream_native_canary\"";
  std::cout << ",\"native_graph_replay\":"
            << (args.graph_replay ? "true" : "false");
  std::cout << ",\"abi_name\":\""
            << kPremapPayloadCacheProducerTransitionStateAbiV1Name << "\"";
  std::cout << ",\"abi_field_count\":"
            << kPremapPayloadCacheProducerTransitionStateAbiV1FieldCount;
  std::cout << ",\"steps\":" << args.steps;
  std::cout << ",\"layers\":" << args.layers;
  std::cout << ",\"experts_per_layer\":" << args.experts_per_layer;
  std::cout << ",\"transition_topk_count\":" << args.transition_topk_count;
  std::cout << ",\"packet_count\":" << packet_count;
  std::cout << ",\"previous_nonempty_packet_count\":"
            << previous_nonempty_packet_count;
  std::cout << ",\"current_nonempty_packet_count\":"
            << current_nonempty_packet_count;
  std::cout << ",\"issue_candidate_count\":" << issue_candidate_count;
  std::cout << ",\"expected_issue_candidate_count\":"
            << expected_issue_candidate_count;
  std::cout << ",\"first_issue_expert\":" << first_issue_expert;
  std::cout << ",\"last_issue_expert\":" << last_issue_expert;
  std::cout << ",\"issue_candidate_hash\":\"" << std::hex << std::setfill('0')
            << std::setw(16) << issue_hash << std::dec << std::setfill(' ')
            << "\"";
  std::cout << ",\"ready_layer_count\":" << ready_layer_count;
  std::cout << ",\"error_count\":" << error_count;
  std::cout << ",\"gpu_elapsed_ms\":" << std::fixed << std::setprecision(6)
            << elapsed_ms;
  std::cout << ",\"persistent_state_on_device\":true";
  std::cout << ",\"issue_generation_on_device\":true";
  std::cout << ",\"vectorized_copy_requested\":"
            << (args.use_vectorized_copy ? "true" : "false");
  std::cout << ",\"vectorized_copy_used\":"
            << (vectorized_copy_used ? "true" : "false");
  std::cout << ",\"payload_bytes\":0";
  std::cout << ",\"payload_transfer_enabled\":false";
  std::cout << ",\"payload_deref_allowed\":false";
  std::cout << ",\"ready_credit\":false";
  std::cout << ",\"ready_before_demand_credit\":false";
  std::cout << ",\"real_ready_credit_granted\":false";
  std::cout << ",\"kernel_arg_pass\":false";
  std::cout << ",\"kernel_arg_pass_allowed\":false";
  std::cout << ",\"passed_to_kernel\":false";
  std::cout << ",\"changes_kernel_launch_args\":false";
  std::cout << ",\"current_wna16_arg_compatible\":false";
  std::cout << ",\"uses_current_wna16_args\":false";
  std::cout << ",\"passes_current_wna16_args\":false";
  std::cout << ",\"measures_tpot\":false";
  std::cout << ",\"measures_vllm_latency\":false";
  std::cout << ",\"native_stub_invoked\":true";
  std::cout << "}\n";
  return ok ? 0 : 1;
}
