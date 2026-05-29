#include <hip/hip_runtime.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "premap_typed_consumer_adapter_v1.h"
#include "premap_typed_consumer_abi_v1.h"

#ifndef MTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1
#error "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1 must be defined for this stub"
#endif

#ifndef MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI
#error "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI must be injected by the runner"
#endif

#ifndef MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO
#error "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO must be injected by the runner"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF)
#error "payload dereference is forbidden in the readonly native stub"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS)
#error "kernel-arg passing is forbidden in the readonly native stub"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD) && \
    defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
#error "enable only one single-field mirror canary per stub build"
#endif

static_assert(!kPremapKernelSideTypedConsumerAbiV1PayloadBytesAllowed,
              "readonly typed consumer ABI must not allow payload bytes");
static_assert(!kPremapKernelSideTypedConsumerAbiV1KernelArgPassAllowed,
              "readonly typed consumer ABI must not allow kernel-arg pass");
static_assert(kPremapKernelSideTypedConsumerAbiV1HandleColumnCount == 4,
              "typed consumer ABI v1 must expose four handle columns");
static_assert(!kPremapKernelSideTypedConsumerAdapterV1PayloadDerefAllowed,
              "readonly typed consumer adapter must not allow payload dereference");
static_assert(!kPremapKernelSideTypedConsumerAdapterV1KernelArgPassAllowed,
              "readonly typed consumer adapter must not allow kernel-arg pass");

constexpr uint64_t kTypedSchemaHashHi = MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI;
constexpr uint64_t kTypedSchemaHashLo = MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO;

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_scale_metadata_handle_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "scale_metadata_handle";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_packed_weight_descriptor_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "packed_weight_descriptor";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
#else
constexpr const char* kSingleFieldMirrorMode = "none";
constexpr const char* kSingleFieldMirrorFieldName = "none";
constexpr const char* kSingleFieldMirrorSource = "none";
#endif

static inline void hip_check(hipError_t err, const char* what) {
  if (err != hipSuccess) {
    std::cerr << what << ": " << hipGetErrorString(err) << "\n";
    std::exit(2);
  }
}

__host__ __device__ static inline uint64_t mix64(uint64_t x) {
  x ^= x >> 33;
  x *= 0xff51afd7ed558ccdULL;
  x ^= x >> 33;
  x *= 0xc4ceb9fe1a85ec53ULL;
  x ^= x >> 33;
  return x;
}

__global__ void typed_consumer_kernel(
    PremapKernelSideTypedConsumerAbiV1 table,
    uint32_t* row_ok,
    uint64_t* row_hash,
    uint32_t* single_field_mirror_ok,
    uint64_t* single_field_mirror_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= table.row_count) {
    return;
  }
  uint32_t ok = 1;
  uint64_t h = 0x9e3779b97f4a7c15ULL ^ static_cast<uint64_t>(idx);

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA)
  ok &= static_cast<uint32_t>(
      premap_typed_consumer_schema_matches_v1(
          table, kTypedSchemaHashHi, kTypedSchemaHashLo));
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION)
  ok &= static_cast<uint32_t>(idx < table.row_count);
#endif

  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(table, idx);
  uint32_t mirror_ok = 0;
  uint64_t mirror_hash = 0;

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY)
  ok &= premap_typed_consumer_required_handles_visible_v1(row);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR)
  ok &= static_cast<uint32_t>(row.descriptor_ptr != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR)
  ok &= static_cast<uint32_t>(row.packed_weight_descriptor != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE)
  ok &= static_cast<uint32_t>(row.scale_metadata_handle != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_scale_metadata_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.scale_metadata_handle + 0x5ca1e00000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_packed_weight_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.packed_weight_descriptor + 0x9ac6ed0000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE)
  ok &= static_cast<uint32_t>(table.aux_metadata_handle != nullptr);
  ok &= static_cast<uint32_t>(row.aux_metadata_handle != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME)
  ok &= premap_typed_consumer_lifetime_valid_v1(table, row);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR)
  h ^= mix64(row.descriptor_ptr);
  h ^= mix64(row.packed_weight_descriptor + 0x1000ULL);
  h ^= mix64(row.scale_metadata_handle + 0x2000ULL);
  h ^= mix64(row.aux_metadata_handle + 0x3000ULL);
  h ^= mix64(row.address_key_hash + static_cast<uint64_t>(row.expert_id));
  h ^= mix64(table.row_order_hash);
  h ^= mix64(table.ordered_row_hash);
#else
  h ^= row.descriptor_ptr ^ row.packed_weight_descriptor ^
       row.scale_metadata_handle ^ row.aux_metadata_handle ^
       row.address_key_hash ^ static_cast<uint64_t>(row.expert_id);
#endif

  row_ok[idx] = ok;
  row_hash[idx] = h;
  single_field_mirror_ok[idx] = mirror_ok;
  single_field_mirror_hash[idx] = mirror_hash;
}

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE)
__global__ void typed_consumer_envelope_kernel(
    PremapKernelSideTypedConsumerLaunchEnvelopeV1 envelope,
    uint32_t* row_ok,
    uint64_t* row_hash,
    uint32_t* single_field_mirror_ok,
    uint64_t* single_field_mirror_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= envelope.table.row_count) {
    return;
  }
  uint32_t ok = static_cast<uint32_t>(
      premap_typed_consumer_launch_envelope_matches_v1(envelope));
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(envelope.table, idx);
  ok &= premap_typed_consumer_required_handles_visible_v1(row);
  ok &= premap_typed_consumer_lifetime_valid_v1(envelope.table, row);
  uint32_t mirror_ok = 0;
  uint64_t mirror_hash = 0;

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_scale_metadata_mirror_matches_v1(
      envelope.table, row);
  mirror_hash = mix64(row.scale_metadata_handle + 0x5ca1e00000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_packed_weight_mirror_matches_v1(
      envelope.table, row);
  mirror_hash = mix64(row.packed_weight_descriptor + 0x9ac6ed0000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#endif

  uint64_t h = 0x517cc1b727220a95ULL ^ static_cast<uint64_t>(idx);
  h ^= mix64(row.descriptor_ptr);
  h ^= mix64(row.packed_weight_descriptor + 0x1000ULL);
  h ^= mix64(row.scale_metadata_handle + 0x2000ULL);
  h ^= mix64(row.aux_metadata_handle + 0x3000ULL);
  h ^= mix64(row.address_key_hash + static_cast<uint64_t>(row.expert_id));
  h ^= mix64(envelope.expected_row_order_hash);
  h ^= mix64(envelope.expected_ordered_row_hash);
  row_ok[idx] = ok;
  row_hash[idx] = h;
  single_field_mirror_ok[idx] = mirror_ok;
  single_field_mirror_hash[idx] = mirror_hash;
}
#endif

struct Args {
  int device = 0;
  int rows = 1024;
  int block_threads = 256;
  std::string input_prefix;
  bool omit_aux_pointer = false;
};

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
    } else if (key == "--rows") {
      args.rows = std::atoi(require_value("--rows"));
    } else if (key == "--block-threads") {
      args.block_threads = std::atoi(require_value("--block-threads"));
    } else if (key == "--input-prefix") {
      args.input_prefix = require_value("--input-prefix");
    } else if (key == "--omit-aux-pointer") {
      args.omit_aux_pointer = true;
    } else {
      std::cerr << "unknown argument: " << key << "\n";
      std::exit(2);
    }
  }
  if (args.rows <= 0 || args.block_threads <= 0) {
    std::cerr << "rows and block-threads must be positive\n";
    std::exit(2);
  }
  return args;
}

template <typename T>
static void read_binary_array(const std::string& path, std::vector<T>& values) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream) {
    std::cerr << "failed to open input array: " << path << "\n";
    std::exit(2);
  }
  stream.read(
      reinterpret_cast<char*>(values.data()),
      static_cast<std::streamsize>(values.size() * sizeof(T)));
  if (!stream) {
    std::cerr << "failed to read complete input array: " << path << "\n";
    std::exit(2);
  }
}

static std::string macro_json() {
  std::ostringstream os;
  os << "{";
  os << "\"MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE)
     << "true";
#else
     << "false";
#endif
  os << "}";
  return os.str();
}

int main(int argc, char** argv) {
  const Args args = parse_args(argc, argv);
  hip_check(hipSetDevice(args.device), "hipSetDevice");

  const int rows = args.rows;
  std::vector<uint64_t> descriptor(rows);
  std::vector<uint64_t> packed(rows);
  std::vector<uint64_t> scale(rows);
  std::vector<uint64_t> aux(rows);
  std::vector<int32_t> expert(rows);
  std::vector<uint64_t> address_key(rows);
  if (!args.input_prefix.empty()) {
    read_binary_array(args.input_prefix + ".descriptor_ptr.u64", descriptor);
    read_binary_array(args.input_prefix + ".packed_weight_descriptor.u64", packed);
    read_binary_array(args.input_prefix + ".scale_metadata_handle.u64", scale);
    read_binary_array(args.input_prefix + ".aux_metadata_handle.u64", aux);
    read_binary_array(args.input_prefix + ".expert_id.i32", expert);
    read_binary_array(args.input_prefix + ".address_key_hash.u64", address_key);
  } else {
    for (int i = 0; i < rows; ++i) {
      descriptor[i] = 0x100000000ULL + static_cast<uint64_t>(i) * 4096ULL;
      packed[i] = 0x200000000ULL + static_cast<uint64_t>(i) * 2048ULL;
      scale[i] = 0x300000000ULL + static_cast<uint64_t>(i) * 1024ULL;
      aux[i] = 0x400000000ULL + static_cast<uint64_t>(i) * 512ULL;
      expert[i] = static_cast<int32_t>(i % 256);
      address_key[i] = mix64(
          1ULL + static_cast<uint64_t>(expert[i]) + (static_cast<uint64_t>(i) << 16));
    }
  }

  uint64_t *d_descriptor = nullptr, *d_packed = nullptr, *d_scale = nullptr,
           *d_aux = nullptr, *d_address_key = nullptr, *d_hash = nullptr,
           *d_single_field_mirror_hash = nullptr;
  int32_t* d_expert = nullptr;
  uint32_t *d_ok = nullptr, *d_single_field_mirror_ok = nullptr;
  const size_t u64_bytes = static_cast<size_t>(rows) * sizeof(uint64_t);
  const size_t i32_bytes = static_cast<size_t>(rows) * sizeof(int32_t);
  const size_t u32_bytes = static_cast<size_t>(rows) * sizeof(uint32_t);
  hip_check(hipMalloc(&d_descriptor, u64_bytes), "hipMalloc descriptor");
  hip_check(hipMalloc(&d_packed, u64_bytes), "hipMalloc packed");
  hip_check(hipMalloc(&d_scale, u64_bytes), "hipMalloc scale");
  if (!args.omit_aux_pointer) {
    hip_check(hipMalloc(&d_aux, u64_bytes), "hipMalloc aux");
  }
  hip_check(hipMalloc(&d_address_key, u64_bytes), "hipMalloc address_key");
  hip_check(hipMalloc(&d_expert, i32_bytes), "hipMalloc expert");
  hip_check(hipMalloc(&d_ok, u32_bytes), "hipMalloc ok");
  hip_check(hipMalloc(&d_hash, u64_bytes), "hipMalloc hash");
  hip_check(
      hipMalloc(&d_single_field_mirror_ok, u32_bytes),
      "hipMalloc single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_single_field_mirror_hash, u64_bytes),
      "hipMalloc single_field_mirror_hash");
  hip_check(hipMemcpy(d_descriptor, descriptor.data(), u64_bytes, hipMemcpyHostToDevice), "copy descriptor");
  hip_check(hipMemcpy(d_packed, packed.data(), u64_bytes, hipMemcpyHostToDevice), "copy packed");
  hip_check(hipMemcpy(d_scale, scale.data(), u64_bytes, hipMemcpyHostToDevice), "copy scale");
  if (!args.omit_aux_pointer) {
    hip_check(hipMemcpy(d_aux, aux.data(), u64_bytes, hipMemcpyHostToDevice), "copy aux");
  }
  hip_check(hipMemcpy(d_address_key, address_key.data(), u64_bytes, hipMemcpyHostToDevice), "copy address_key");
  hip_check(hipMemcpy(d_expert, expert.data(), i32_bytes, hipMemcpyHostToDevice), "copy expert");

  PremapKernelSideTypedConsumerAbiV1 table;
  table.typed_schema_hash_hi = kTypedSchemaHashHi;
  table.typed_schema_hash_lo = kTypedSchemaHashLo;
  table.descriptor_ptr = d_descriptor;
  table.packed_weight_descriptor = d_packed;
  table.scale_metadata_handle = d_scale;
  table.aux_metadata_handle = d_aux;
  table.expert_id = d_expert;
  table.address_key_hash = d_address_key;
  table.row_order_hash = 0xa02928d41970cdf1ULL;
  table.ordered_row_hash = 0xc1384d55958c9aa7ULL;
  table.lifetime_epoch = 1;
  table.row_count = static_cast<uint32_t>(rows);
  table.column_count = 4;

  const int threads = args.block_threads;
  const int blocks = (rows + threads - 1) / threads;
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE)
  PremapKernelSideTypedConsumerLaunchEnvelopeV1 envelope;
  envelope.table = table;
  envelope.expected_schema_hash_hi = kTypedSchemaHashHi;
  envelope.expected_schema_hash_lo = kTypedSchemaHashLo;
  envelope.expected_row_order_hash = table.row_order_hash;
  envelope.expected_ordered_row_hash = table.ordered_row_hash;
  envelope.expected_row_count = table.row_count;
  envelope.expected_column_count = table.column_count;
  envelope.payload_bytes = 0;
  envelope.flags =
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag |
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag;
  hipLaunchKernelGGL(
      typed_consumer_envelope_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      envelope,
      d_ok,
      d_hash,
      d_single_field_mirror_ok,
      d_single_field_mirror_hash);
#else
  hipLaunchKernelGGL(
      typed_consumer_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      table,
      d_ok,
      d_hash,
      d_single_field_mirror_ok,
      d_single_field_mirror_hash);
#endif
  hip_check(hipGetLastError(), "kernel launch");
  hip_check(hipDeviceSynchronize(), "kernel sync");

  std::vector<uint32_t> ok(rows);
  std::vector<uint64_t> hashes(rows);
  std::vector<uint32_t> single_field_mirror_ok(rows);
  std::vector<uint64_t> single_field_mirror_hashes(rows);
  hip_check(hipMemcpy(ok.data(), d_ok, u32_bytes, hipMemcpyDeviceToHost), "copy ok");
  hip_check(hipMemcpy(hashes.data(), d_hash, u64_bytes, hipMemcpyDeviceToHost), "copy hash");
  hip_check(
      hipMemcpy(
          single_field_mirror_ok.data(),
          d_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          single_field_mirror_hashes.data(),
          d_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy single_field_mirror_hash");

  uint64_t hash_acc = 0;
  uint64_t single_field_mirror_hash_acc = 0;
  int ok_count = 0;
  int single_field_mirror_ok_count = 0;
  for (int i = 0; i < rows; ++i) {
    ok_count += ok[i] == 1 ? 1 : 0;
    hash_acc ^= mix64(hashes[i] + static_cast<uint64_t>(i));
    single_field_mirror_ok_count += single_field_mirror_ok[i] == 1 ? 1 : 0;
    single_field_mirror_hash_acc ^=
        mix64(single_field_mirror_hashes[i] + static_cast<uint64_t>(i));
  }
  const int error_count = rows - ok_count;
  const bool single_field_mirror_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD) || \
    defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
      true;
#else
      false;
#endif
  const int single_field_mirror_row_count =
      single_field_mirror_checked ? rows : 0;
  const int single_field_mirror_error_count =
      single_field_mirror_checked ? rows - single_field_mirror_ok_count : 0;

  hip_check(hipFree(d_descriptor), "hipFree descriptor");
  hip_check(hipFree(d_packed), "hipFree packed");
  hip_check(hipFree(d_scale), "hipFree scale");
  if (d_aux != nullptr) {
    hip_check(hipFree(d_aux), "hipFree aux");
  }
  hip_check(hipFree(d_address_key), "hipFree address_key");
  hip_check(hipFree(d_expert), "hipFree expert");
  hip_check(hipFree(d_ok), "hipFree ok");
  hip_check(hipFree(d_hash), "hipFree hash");
  hip_check(hipFree(d_single_field_mirror_ok), "hipFree single_field_mirror_ok");
  hip_check(
      hipFree(d_single_field_mirror_hash),
      "hipFree single_field_mirror_hash");

  std::cout << "{";
  std::cout << "\"ok\":" << (error_count == 0 ? "true" : "false");
  std::cout << ",\"device\":" << args.device;
  std::cout << ",\"row_count\":" << rows;
  std::cout << ",\"column_count\":4";
  std::cout << ",\"abi_name\":\"" << kPremapKernelSideTypedConsumerAbiV1Name << "\"";
  std::cout << ",\"abi_handle_column_count\":"
            << kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  std::cout << ",\"abi_payload_bytes_allowed\":false";
  std::cout << ",\"abi_kernel_arg_pass_allowed\":false";
  std::cout << ",\"adapter_name\":\"" << kPremapKernelSideTypedConsumerAdapterV1Name
            << "\"";
  std::cout << ",\"adapter_payload_deref_allowed\":false";
  std::cout << ",\"adapter_kernel_arg_pass_allowed\":false";
  std::cout << ",\"kernel_consumer_envelope_name\":\""
            << kPremapKernelSideTypedConsumerLaunchEnvelopeV1Name << "\"";
  std::cout << ",\"kernel_consumer_envelope_checked\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE)
            << "true";
#else
            << "false";
#endif
  std::cout << ",\"kernel_consumer_envelope_payload_bytes\":0";
  std::cout << ",\"kernel_consumer_envelope_passed_to_kernel\":false";
  std::cout << ",\"single_field_mirror_checked\":"
            << (single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"single_field_mirror_mode\":\"" << kSingleFieldMirrorMode
            << "\"";
  std::cout << ",\"single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"single_field_mirror_source\":\"" << kSingleFieldMirrorSource
            << "\"";
  std::cout << ",\"single_field_mirror_row_count\":"
            << single_field_mirror_row_count;
  std::cout << ",\"single_field_mirror_row_ok_count\":"
            << (single_field_mirror_checked ? single_field_mirror_ok_count : 0);
  std::cout << ",\"single_field_mirror_error_count\":"
            << single_field_mirror_error_count;
  std::cout << ",\"single_field_mirror_hash_accumulator\":\"" << std::hex
            << single_field_mirror_hash_acc << std::dec << "\"";
  std::cout << ",\"single_field_mirror_payload_bytes\":0";
  std::cout << ",\"single_field_mirror_passed_to_kernel\":false";
  std::cout << ",\"single_field_mirror_changes_kernel_launch_args\":false";
  std::cout << ",\"single_field_mirror_kernel_side_typed_consumer_compatible\":"
            << (single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"single_field_mirror_current_wna16_arg_compatible\":false";
  std::cout << ",\"typed_schema_hash_hi\":\"" << std::hex << kTypedSchemaHashHi << std::dec << "\"";
  std::cout << ",\"typed_schema_hash_lo\":\"" << std::hex << kTypedSchemaHashLo << std::dec << "\"";
  std::cout << ",\"aux_pointer_present\":" << (args.omit_aux_pointer ? "false" : "true");
  std::cout << ",\"row_ok_count\":" << ok_count;
  std::cout << ",\"error_count\":" << error_count;
  std::cout << ",\"input_source\":\"" << (args.input_prefix.empty() ? "synthetic" : "binary_prefix") << "\"";
  std::cout << ",\"hash_accumulator\":\"" << std::hex << hash_acc << std::dec << "\"";
  std::cout << ",\"payload_bytes\":0";
  std::cout << ",\"passed_to_kernel\":false";
  std::cout << ",\"changes_kernel_launch_args\":false";
  std::cout << ",\"compiled_macros\":" << macro_json();
  std::cout << "}\n";
  return error_count == 0 ? 0 : 1;
}
