#include <hip/hip_runtime.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

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

struct TypedConsumerTable {
  uint64_t typed_schema_hash_hi;
  uint64_t typed_schema_hash_lo;
  const uint64_t* descriptor_ptr;
  const uint64_t* packed_weight_descriptor;
  const uint64_t* scale_metadata_handle;
  const uint64_t* aux_metadata_handle;
  const int32_t* expert_id;
  const uint64_t* address_key_hash;
  uint64_t row_order_hash;
  uint64_t ordered_row_hash;
  uint64_t lifetime_epoch;
  uint32_t row_count;
  uint32_t column_count;
};

constexpr uint64_t kTypedSchemaHashHi = MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI;
constexpr uint64_t kTypedSchemaHashLo = MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO;

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
    TypedConsumerTable table,
    uint32_t* row_ok,
    uint64_t* row_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= table.row_count) {
    return;
  }
  uint32_t ok = 1;
  uint64_t h = 0x9e3779b97f4a7c15ULL ^ static_cast<uint64_t>(idx);

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA)
  ok &= static_cast<uint32_t>(table.typed_schema_hash_hi == kTypedSchemaHashHi);
  ok &= static_cast<uint32_t>(table.typed_schema_hash_lo == kTypedSchemaHashLo);
  ok &= static_cast<uint32_t>(table.column_count == 4);
  ok &= static_cast<uint32_t>(table.row_count > 0);
  ok &= static_cast<uint32_t>(table.descriptor_ptr != nullptr);
  ok &= static_cast<uint32_t>(table.packed_weight_descriptor != nullptr);
  ok &= static_cast<uint32_t>(table.scale_metadata_handle != nullptr);
  ok &= static_cast<uint32_t>(table.expert_id != nullptr);
  ok &= static_cast<uint32_t>(table.address_key_hash != nullptr);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION)
  ok &= static_cast<uint32_t>(idx < table.row_count);
#endif

  const uint64_t descriptor = table.descriptor_ptr[idx];
  const uint64_t packed = table.packed_weight_descriptor[idx];
  const uint64_t scale = table.scale_metadata_handle[idx];
  const uint64_t aux =
      table.aux_metadata_handle == nullptr ? 0ULL : table.aux_metadata_handle[idx];
  const int32_t expert = table.expert_id[idx];
  const uint64_t address_key = table.address_key_hash[idx];

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY)
  ok &= static_cast<uint32_t>(descriptor != 0);
  ok &= static_cast<uint32_t>(packed != 0);
  ok &= static_cast<uint32_t>(scale != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR)
  ok &= static_cast<uint32_t>(descriptor != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR)
  ok &= static_cast<uint32_t>(packed != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE)
  ok &= static_cast<uint32_t>(scale != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE)
  ok &= static_cast<uint32_t>(table.aux_metadata_handle != nullptr);
  ok &= static_cast<uint32_t>(aux != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME)
  ok &= static_cast<uint32_t>(table.lifetime_epoch == 1);
  ok &= static_cast<uint32_t>(address_key != 0);
  ok &= static_cast<uint32_t>(expert >= 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR)
  h ^= mix64(descriptor);
  h ^= mix64(packed + 0x1000ULL);
  h ^= mix64(scale + 0x2000ULL);
  h ^= mix64(aux + 0x3000ULL);
  h ^= mix64(address_key + static_cast<uint64_t>(expert));
  h ^= mix64(table.row_order_hash);
  h ^= mix64(table.ordered_row_hash);
#else
  h ^= descriptor ^ packed ^ scale ^ aux ^ address_key ^ static_cast<uint64_t>(expert);
#endif

  row_ok[idx] = ok;
  row_hash[idx] = h;
}

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
           *d_aux = nullptr, *d_address_key = nullptr, *d_hash = nullptr;
  int32_t* d_expert = nullptr;
  uint32_t* d_ok = nullptr;
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
  hip_check(hipMemcpy(d_descriptor, descriptor.data(), u64_bytes, hipMemcpyHostToDevice), "copy descriptor");
  hip_check(hipMemcpy(d_packed, packed.data(), u64_bytes, hipMemcpyHostToDevice), "copy packed");
  hip_check(hipMemcpy(d_scale, scale.data(), u64_bytes, hipMemcpyHostToDevice), "copy scale");
  if (!args.omit_aux_pointer) {
    hip_check(hipMemcpy(d_aux, aux.data(), u64_bytes, hipMemcpyHostToDevice), "copy aux");
  }
  hip_check(hipMemcpy(d_address_key, address_key.data(), u64_bytes, hipMemcpyHostToDevice), "copy address_key");
  hip_check(hipMemcpy(d_expert, expert.data(), i32_bytes, hipMemcpyHostToDevice), "copy expert");

  TypedConsumerTable table;
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
  hipLaunchKernelGGL(
      typed_consumer_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      table,
      d_ok,
      d_hash);
  hip_check(hipGetLastError(), "kernel launch");
  hip_check(hipDeviceSynchronize(), "kernel sync");

  std::vector<uint32_t> ok(rows);
  std::vector<uint64_t> hashes(rows);
  hip_check(hipMemcpy(ok.data(), d_ok, u32_bytes, hipMemcpyDeviceToHost), "copy ok");
  hip_check(hipMemcpy(hashes.data(), d_hash, u64_bytes, hipMemcpyDeviceToHost), "copy hash");

  uint64_t hash_acc = 0;
  int ok_count = 0;
  for (int i = 0; i < rows; ++i) {
    ok_count += ok[i] == 1 ? 1 : 0;
    hash_acc ^= mix64(hashes[i] + static_cast<uint64_t>(i));
  }
  const int error_count = rows - ok_count;

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

  std::cout << "{";
  std::cout << "\"ok\":" << (error_count == 0 ? "true" : "false");
  std::cout << ",\"device\":" << args.device;
  std::cout << ",\"row_count\":" << rows;
  std::cout << ",\"column_count\":4";
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
