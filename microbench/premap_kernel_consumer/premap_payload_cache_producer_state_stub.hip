#include <hip/hip_runtime.h>

#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
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

struct ProducerTransitionStateResult {
  uint32_t checked;
  uint32_t ready;
  uint32_t previous_count;
  uint32_t current_count;
  uint32_t previous_valid_count;
  uint32_t current_valid_count;
  uint32_t overlap_count;
  uint32_t issue_candidate_count;
  uint32_t previous_nonempty;
  uint32_t current_nonempty;
  uint32_t transition_topk_count;
  uint32_t layer_id;
  uint32_t error_count;
  uint64_t state_hash;
  uint64_t issue_candidate_hash;
};

static void hip_check(hipError_t err, const char* label) {
  if (err != hipSuccess) {
    std::cerr << label << ": " << hipGetErrorString(err) << "\n";
    std::exit(1);
  }
}

__device__ bool contains_i32(const int32_t* values, uint32_t count, int32_t needle) {
  for (uint32_t i = 0; i < count; ++i) {
    if (values[i] == needle) {
      return true;
    }
  }
  return false;
}

__device__ uint64_t issue_hash_mix(uint64_t value, uint32_t expert_id) {
  value ^= static_cast<uint64_t>(expert_id);
  value *= 0x100000001b3ULL;
  return value;
}

__global__ void producer_transition_state_kernel(
    PremapPayloadCacheProducerTransitionStateAbiV1 packet,
    ProducerTransitionStateResult* out) {
  if (threadIdx.x != 0 || blockIdx.x != 0) {
    return;
  }
  ProducerTransitionStateResult result{};
  result.checked = 1;
  result.previous_count = packet.previous_count;
  result.current_count = packet.current_count;
  result.layer_id = packet.layer_id;
  result.transition_topk_count = packet.transition_topk_count;
  result.previous_nonempty = packet.previous_count > 0 ? 1 : 0;
  result.current_nonempty = packet.current_count > 0 ? 1 : 0;
  result.state_hash = packet.state_hash;

  if (packet.previous_expert_id == nullptr && packet.previous_count != 0) {
    result.error_count += 1;
  }
  if (packet.current_expert_id == nullptr && packet.current_count != 0) {
    result.error_count += 1;
  }
  if (packet.schema_hash_hi == 0 || packet.schema_hash_lo == 0) {
    result.error_count += 1;
  }
  if (packet.state_hash == 0) {
    result.error_count += 1;
  }

  const uint32_t previous_count =
      packet.previous_expert_id == nullptr ? 0 : packet.previous_count;
  const uint32_t current_count =
      packet.current_expert_id == nullptr ? 0 : packet.current_count;
  const uint32_t topk = packet.transition_topk_count;

  // The semantic producer packet canonicalizes expert ids before this native
  // boundary.  This canary therefore treats previous/current arrays as set-like
  // rows and reports raw-count overlap for the canonicalized input contract.
  const uint32_t issue_limit =
      topk == 0 ? previous_count
                : (previous_count < topk ? previous_count : topk);
  result.issue_candidate_hash = 0xcbf29ce484222325ULL;
  uint32_t issue_selected_count = 0;
  for (uint32_t i = 0; i < previous_count; ++i) {
    const int32_t expert = packet.previous_expert_id[i];
    if (expert >= 0) {
      result.previous_valid_count += 1;
      if (issue_selected_count < issue_limit) {
        result.issue_candidate_hash =
            issue_hash_mix(result.issue_candidate_hash, static_cast<uint32_t>(expert));
        issue_selected_count += 1;
      }
    } else {
      result.error_count += 1;
    }
  }
  for (uint32_t i = 0; i < current_count; ++i) {
    const int32_t expert = packet.current_expert_id[i];
    if (expert >= 0) {
      result.current_valid_count += 1;
      if (contains_i32(packet.previous_expert_id, previous_count, expert)) {
        result.overlap_count += 1;
      }
    } else {
      result.error_count += 1;
    }
  }

  result.issue_candidate_count = issue_selected_count;
  result.issue_candidate_hash =
      issue_hash_mix(result.issue_candidate_hash, issue_selected_count);
  result.ready = result.error_count == 0 ? 1 : 0;
  *out = result;
}

struct Args {
  int device = 0;
  uint32_t previous_count = 8;
  uint32_t current_count = 8;
  uint32_t transition_topk_count = 8;
  uint32_t current_offset = 4;
  uint32_t layer_id = 0;
  uint64_t state_hash = 0x8a45d2c91fe01237ULL;
  std::vector<int32_t> previous_experts;
  std::vector<int32_t> current_experts;
};

static uint32_t parse_bounded_u32(const char* raw, const char* name) {
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
  constexpr unsigned long kMaxCount = 65536UL;
  if (value > kMaxCount ||
      value > static_cast<unsigned long>(std::numeric_limits<uint32_t>::max())) {
    std::cerr << name << " exceeds the native canary safety bound\n";
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

static std::vector<int32_t> parse_expert_csv(const char* raw, const char* name) {
  std::vector<int32_t> values;
  const std::string text(raw == nullptr ? "" : raw);
  if (text.empty()) {
    return values;
  }
  std::stringstream stream(text);
  std::string item;
  while (std::getline(stream, item, ',')) {
    if (item.empty() || item[0] == '-') {
      std::cerr << name << " entries must be non-negative integers\n";
      std::exit(2);
    }
    char* end = nullptr;
    const unsigned long value = std::strtoul(item.c_str(), &end, 10);
    if (end == item.c_str() || *end != '\0' || value > 65536UL) {
      std::cerr << name << " contains an invalid expert id\n";
      std::exit(2);
    }
    values.push_back(static_cast<int32_t>(value));
  }
  constexpr size_t kMaxCsvCount = 65536UL;
  if (values.size() > kMaxCsvCount) {
    std::cerr << name << " exceeds the native canary safety bound\n";
    std::exit(2);
  }
  return values;
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
    } else if (key == "--layer-id") {
      args.layer_id = parse_bounded_u32(require_value("--layer-id"), "--layer-id");
    } else if (key == "--state-hash") {
      args.state_hash = parse_u64(require_value("--state-hash"), "--state-hash");
    } else if (key == "--previous-count") {
      args.previous_count =
          parse_bounded_u32(require_value("--previous-count"), "--previous-count");
    } else if (key == "--current-count") {
      args.current_count =
          parse_bounded_u32(require_value("--current-count"), "--current-count");
    } else if (key == "--transition-topk-count") {
      args.transition_topk_count = parse_bounded_u32(
          require_value("--transition-topk-count"),
          "--transition-topk-count");
    } else if (key == "--current-offset") {
      args.current_offset =
          parse_bounded_u32(require_value("--current-offset"), "--current-offset");
    } else if (key == "--previous-experts") {
      args.previous_experts =
          parse_expert_csv(require_value("--previous-experts"), "--previous-experts");
    } else if (key == "--current-experts") {
      args.current_experts =
          parse_expert_csv(require_value("--current-experts"), "--current-experts");
    } else {
      std::cerr << "unknown argument: " << key << "\n";
      std::exit(2);
    }
  }
  return args;
}

int main(int argc, char** argv) {
  const Args args = parse_args(argc, argv);
  hip_check(hipSetDevice(args.device), "hipSetDevice");

  std::vector<int32_t> previous = args.previous_experts;
  std::vector<int32_t> current = args.current_experts;
  if (previous.empty()) {
    previous.resize(args.previous_count);
    for (uint32_t i = 0; i < args.previous_count; ++i) {
      previous[i] = static_cast<int32_t>(i);
    }
  }
  if (current.empty()) {
    current.resize(args.current_count);
    for (uint32_t i = 0; i < args.current_count; ++i) {
      current[i] = static_cast<int32_t>(i + args.current_offset);
    }
  }

  int32_t* d_previous = nullptr;
  int32_t* d_current = nullptr;
  ProducerTransitionStateResult* d_result = nullptr;
  hip_check(
      hipMalloc(&d_previous, std::max<size_t>(1, previous.size()) * sizeof(int32_t)),
      "hipMalloc previous");
  hip_check(
      hipMalloc(&d_current, std::max<size_t>(1, current.size()) * sizeof(int32_t)),
      "hipMalloc current");
  hip_check(hipMalloc(&d_result, sizeof(ProducerTransitionStateResult)),
            "hipMalloc result");
  if (!previous.empty()) {
    hip_check(
        hipMemcpy(
            d_previous,
            previous.data(),
            previous.size() * sizeof(int32_t),
            hipMemcpyHostToDevice),
        "hipMemcpy previous");
  }
  if (!current.empty()) {
    hip_check(
        hipMemcpy(
            d_current,
            current.data(),
            current.size() * sizeof(int32_t),
            hipMemcpyHostToDevice),
        "hipMemcpy current");
  }
  hip_check(hipMemset(d_result, 0, sizeof(ProducerTransitionStateResult)),
            "hipMemset result");

  PremapPayloadCacheProducerTransitionStateAbiV1 packet{};
  packet.schema_hash_hi = 0x9e8a8c42f1539bd1ULL;
  packet.schema_hash_lo = 0x3a2a914cefc1d579ULL;
  packet.previous_expert_id = d_previous;
  packet.current_expert_id = d_current;
  packet.state_hash = args.state_hash;
  packet.previous_count = static_cast<uint32_t>(previous.size());
  packet.current_count = static_cast<uint32_t>(current.size());
  packet.layer_id = args.layer_id;
  packet.transition_topk_count = args.transition_topk_count;

  hipLaunchKernelGGL(
      producer_transition_state_kernel,
      dim3(1),
      dim3(64),
      0,
      0,
      packet,
      d_result);
  hip_check(hipGetLastError(), "producer_transition_state_kernel launch");
  hip_check(hipDeviceSynchronize(), "hipDeviceSynchronize");

  ProducerTransitionStateResult result{};
  hip_check(
      hipMemcpy(
          &result,
          d_result,
          sizeof(ProducerTransitionStateResult),
          hipMemcpyDeviceToHost),
      "hipMemcpy result");

  hip_check(hipFree(d_previous), "hipFree previous");
  hip_check(hipFree(d_current), "hipFree current");
  hip_check(hipFree(d_result), "hipFree result");

  const bool ok = result.checked == 1 && result.ready == 1 &&
                  result.error_count == 0 &&
                  result.previous_count == previous.size() &&
                  result.current_count == current.size() &&
                  result.layer_id == args.layer_id &&
                  result.state_hash == args.state_hash;
  std::cout << "{";
  std::cout << "\"ok\":" << (ok ? "true" : "false");
  std::cout << ",\"passed\":" << (ok ? "true" : "false");
  std::cout << ",\"mode\":\"readonly_payload_cache_producer_transition_state_native_canary\"";
  std::cout << ",\"abi_name\":\""
            << kPremapPayloadCacheProducerTransitionStateAbiV1Name << "\"";
  std::cout << ",\"abi_field_count\":"
            << kPremapPayloadCacheProducerTransitionStateAbiV1FieldCount;
  std::cout << ",\"checked\":" << (result.checked ? "true" : "false");
  std::cout << ",\"ready\":" << (result.ready ? "true" : "false");
  std::cout << ",\"previous_count\":" << result.previous_count;
  std::cout << ",\"current_count\":" << result.current_count;
  std::cout << ",\"previous_valid_count\":" << result.previous_valid_count;
  std::cout << ",\"current_valid_count\":" << result.current_valid_count;
  std::cout << ",\"overlap_count\":" << result.overlap_count;
  std::cout << ",\"issue_candidate_count\":" << result.issue_candidate_count;
  std::cout << ",\"issue_candidate_hash\":\"" << std::hex << std::setfill('0')
            << std::setw(16) << result.issue_candidate_hash << std::dec
            << std::setfill(' ') << "\"";
  std::cout << ",\"previous_nonempty\":" << result.previous_nonempty;
  std::cout << ",\"current_nonempty\":" << result.current_nonempty;
  std::cout << ",\"transition_topk_count\":" << result.transition_topk_count;
  std::cout << ",\"layer_id\":" << result.layer_id;
  std::cout << ",\"error_count\":" << result.error_count;
  std::cout << ",\"state_hash\":\"" << std::hex << std::setfill('0')
            << std::setw(16) << result.state_hash << std::dec
            << std::setfill(' ') << "\"";
  std::cout << ",\"payload_bytes\":0";
  std::cout << ",\"ready_credit\":false";
  std::cout << ",\"passed_to_kernel\":false";
  std::cout << ",\"changes_kernel_launch_args\":false";
  std::cout << ",\"current_wna16_arg_compatible\":false";
  std::cout << ",\"native_stub_invoked\":true";
  std::cout << "}\n";
  return ok ? 0 : 1;
}
