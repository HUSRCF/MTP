#include <hip/hip_runtime.h>

#include <cstddef>
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

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS)
#error "future-args compatible consumer path requires future kernel consumer args"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI)
#error "future native consumer launch ABI requires future native consumer ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI)
#error "future native consumer dispatch ABI requires future native consumer launch ABI"
#endif

#if (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD))
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
static_assert(!kPremapKernelSideCompatibleConsumerAbiV1PayloadDerefAllowed,
              "kernel-side compatible consumer ABI must not allow payload dereference");
static_assert(!kPremapKernelSideCompatibleConsumerAbiV1KernelArgPassAllowed,
              "kernel-side compatible consumer ABI must not allow kernel-arg pass");
static_assert(!kPremapKernelSideCompatibleConsumerAbiV1CurrentWna16ArgCompatible,
              "kernel-side compatible consumer ABI must not be the current WNA16 arg list");
static_assert(!kPremapFutureKernelSideConsumerArgsV1PayloadDerefAllowed,
              "future kernel consumer args must not allow payload dereference");
static_assert(!kPremapFutureKernelSideConsumerArgsV1KernelArgPassAllowed,
              "future kernel consumer args must not allow kernel-arg pass");
static_assert(!kPremapFutureKernelSideConsumerArgsV1CurrentWna16ArgCompatible,
              "future kernel consumer args must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelArgsCompatibleConsumerPathV1PayloadDerefAllowed,
    "future args compatible consumer path must not allow payload dereference");
static_assert(
    !kPremapFutureKernelArgsCompatibleConsumerPathV1KernelArgPassAllowed,
    "future args compatible consumer path must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelArgsCompatibleConsumerPathV1CurrentWna16ArgCompatible,
    "future args compatible consumer path must not be the current WNA16 arg list");
static_assert(!kPremapFutureKernelNativeConsumerAbiV1PayloadDerefAllowed,
              "future native consumer ABI must not allow payload dereference");
static_assert(!kPremapFutureKernelNativeConsumerAbiV1KernelArgPassAllowed,
              "future native consumer ABI must not allow kernel-arg pass");
static_assert(!kPremapFutureKernelNativeConsumerAbiV1CurrentWna16ArgCompatible,
              "future native consumer ABI must not be the current WNA16 arg list");
static_assert(!kPremapFutureKernelNativeConsumerLaunchAbiV1PayloadDerefAllowed,
              "future native consumer launch ABI must not allow payload dereference");
static_assert(!kPremapFutureKernelNativeConsumerLaunchAbiV1KernelArgPassAllowed,
              "future native consumer launch ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerLaunchAbiV1CurrentWna16ArgCompatible,
    "future native consumer launch ABI must not be the current WNA16 arg list");
static_assert(!kPremapFutureKernelNativeConsumerDispatchAbiV1PayloadDerefAllowed,
              "future native consumer dispatch ABI must not allow payload dereference");
static_assert(!kPremapFutureKernelNativeConsumerDispatchAbiV1KernelArgPassAllowed,
              "future native consumer dispatch ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerDispatchAbiV1CurrentWna16ArgCompatible,
    "future native consumer dispatch ABI must not be the current WNA16 arg list");

constexpr uint64_t kTypedSchemaHashHi = MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI;
constexpr uint64_t kTypedSchemaHashLo = MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO;

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_descriptor_ptr_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "descriptor_ptr";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldDescriptorPtr;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_scale_metadata_handle_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "scale_metadata_handle";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldScaleMetadataHandle;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_packed_weight_descriptor_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "packed_weight_descriptor";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_aux_metadata_handle_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "aux_metadata_handle";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldAuxMetadataHandle;
#else
constexpr const char* kSingleFieldMirrorMode = "none";
constexpr const char* kSingleFieldMirrorFieldName = "none";
constexpr const char* kSingleFieldMirrorSource = "none";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldNone;
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
    uint64_t* single_field_mirror_hash,
    uint32_t* kernel_side_consumer_path_ok,
    uint64_t* kernel_side_consumer_path_hash,
    uint32_t* kernel_side_compatible_consumer_ok,
    uint64_t* kernel_side_compatible_consumer_hash) {
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
  uint32_t kernel_path_ok = 0;
  uint64_t kernel_path_hash = 0;
  uint32_t compatible_consumer_ok = 0;
  uint64_t compatible_consumer_hash = 0;

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

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_descriptor_ptr_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.descriptor_ptr + 0xde5c000000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_scale_metadata_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.scale_metadata_handle + 0x5ca1e00000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_packed_weight_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.packed_weight_descriptor + 0x9ac6ed0000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_aux_metadata_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.aux_metadata_handle + 0xa11c000000000000ULL) ^
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

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH)
  const PremapKernelSideTypedConsumerPathResultV1 kernel_path_result =
      premap_typed_consumer_kernel_side_consume_row_v1(table, idx);
  kernel_path_ok = kernel_path_result.ok;
  kernel_path_hash = kernel_path_result.row_hash;
  ok &= kernel_path_ok;
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI)
  PremapKernelSideTypedConsumerLaunchEnvelopeV1 compatible_envelope;
  compatible_envelope.table = table;
  compatible_envelope.expected_schema_hash_hi = kTypedSchemaHashHi;
  compatible_envelope.expected_schema_hash_lo = kTypedSchemaHashLo;
  compatible_envelope.expected_row_order_hash = table.row_order_hash;
  compatible_envelope.expected_ordered_row_hash = table.ordered_row_hash;
  compatible_envelope.expected_row_count = table.row_count;
  compatible_envelope.expected_column_count = table.column_count;
  compatible_envelope.payload_bytes = 0;
  compatible_envelope.flags =
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag |
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag;
  const PremapKernelSideCompatibleConsumerResultV1 compatible_result =
      premap_typed_consumer_kernel_side_compatible_consume_row_v1(
          compatible_envelope, idx);
  compatible_consumer_ok = compatible_result.ok;
  compatible_consumer_hash = compatible_result.row_hash;
  ok &= compatible_consumer_ok;
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
  kernel_side_consumer_path_ok[idx] = kernel_path_ok;
  kernel_side_consumer_path_hash[idx] = kernel_path_hash;
  kernel_side_compatible_consumer_ok[idx] = compatible_consumer_ok;
  kernel_side_compatible_consumer_hash[idx] = compatible_consumer_hash;
}

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE)
__global__ void typed_consumer_envelope_kernel(
    PremapKernelSideTypedConsumerLaunchEnvelopeV1 envelope,
    uint32_t* row_ok,
    uint64_t* row_hash,
    uint32_t* single_field_mirror_ok,
    uint64_t* single_field_mirror_hash,
    uint32_t* kernel_side_consumer_path_ok,
    uint64_t* kernel_side_consumer_path_hash,
    uint32_t* kernel_side_compatible_consumer_ok,
    uint64_t* kernel_side_compatible_consumer_hash) {
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
  uint32_t kernel_path_ok = 0;
  uint64_t kernel_path_hash = 0;
  uint32_t compatible_consumer_ok = 0;
  uint64_t compatible_consumer_hash = 0;

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_descriptor_ptr_mirror_matches_v1(
      envelope.table, row);
  mirror_hash = mix64(row.descriptor_ptr + 0xde5c000000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
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
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_aux_metadata_mirror_matches_v1(
      envelope.table, row);
  mirror_hash = mix64(row.aux_metadata_handle + 0xa11c000000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH)
  const PremapKernelSideTypedConsumerPathResultV1 kernel_path_result =
      premap_typed_consumer_kernel_side_consume_row_v1(envelope.table, idx);
  kernel_path_ok = kernel_path_result.ok;
  kernel_path_hash = kernel_path_result.row_hash;
  ok &= kernel_path_ok;
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI)
  const PremapKernelSideCompatibleConsumerResultV1 compatible_result =
      premap_typed_consumer_kernel_side_compatible_consume_row_v1(envelope, idx);
  compatible_consumer_ok = compatible_result.ok;
  compatible_consumer_hash = compatible_result.row_hash;
  ok &= compatible_consumer_ok;
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
  kernel_side_consumer_path_ok[idx] = kernel_path_ok;
  kernel_side_consumer_path_hash[idx] = kernel_path_hash;
  kernel_side_compatible_consumer_ok[idx] = compatible_consumer_ok;
  kernel_side_compatible_consumer_hash[idx] = compatible_consumer_hash;
}
#endif

__global__ void typed_consumer_future_kernel_args_kernel(
    PremapFutureKernelSideConsumerArgsV1 args,
    uint32_t* future_kernel_consumer_ok,
    uint64_t* future_kernel_consumer_hash,
    uint32_t* future_kernel_single_field_mirror_ok,
    uint64_t* future_kernel_single_field_mirror_hash,
    uint32_t* future_kernel_compatible_path_ok,
    uint64_t* future_kernel_compatible_path_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= args.envelope.table.row_count) {
    return;
  }
  const PremapFutureKernelSideConsumerResultV1 result =
      premap_typed_consumer_future_kernel_consume_row_v1(args, idx);
  uint32_t compatible_path_ok = 0;
  uint64_t compatible_path_hash = 0;
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH)
  const PremapFutureKernelArgsCompatibleConsumerPathResultV1 compatible_path =
      premap_typed_consumer_future_kernel_args_compatible_consume_row_v1(
          args, idx);
  compatible_path_ok = compatible_path.ok;
  compatible_path_hash = compatible_path.row_hash;
#endif
  future_kernel_consumer_ok[idx] = result.ok;
  future_kernel_consumer_hash[idx] = result.row_hash;
  future_kernel_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_kernel_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
  future_kernel_compatible_path_ok[idx] = compatible_path_ok;
  future_kernel_compatible_path_hash[idx] = compatible_path_hash;
}

__global__ void typed_consumer_future_native_kernel(
    PremapFutureKernelNativeConsumerParamsV1 params,
    uint32_t* future_native_consumer_ok,
    uint64_t* future_native_consumer_hash,
    uint32_t* future_native_single_field_mirror_ok,
    uint64_t* future_native_single_field_mirror_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= params.row_count) {
    return;
  }
  const PremapFutureKernelNativeConsumerResultV1 result =
      premap_typed_consumer_future_native_consume_row_v1(
          params, idx, kTypedSchemaHashHi, kTypedSchemaHashLo);
  future_native_consumer_ok[idx] = result.ok;
  future_native_consumer_hash[idx] = result.row_hash;
  future_native_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_native_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
}

__global__ void typed_consumer_future_native_launch_kernel(
    PremapFutureKernelNativeConsumerLaunchV1 launch,
    uint32_t* future_native_launch_consumer_ok,
    uint64_t* future_native_launch_consumer_hash,
    uint32_t* future_native_launch_single_field_mirror_ok,
    uint64_t* future_native_launch_single_field_mirror_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= launch.params.row_count) {
    return;
  }
  const PremapFutureKernelNativeConsumerLaunchResultV1 result =
      premap_typed_consumer_future_native_launch_consume_row_v1(
          launch, idx, kTypedSchemaHashHi, kTypedSchemaHashLo);
  future_native_launch_consumer_ok[idx] = result.ok;
  future_native_launch_consumer_hash[idx] = result.row_hash;
  future_native_launch_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_native_launch_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
}

__global__ void typed_consumer_future_native_dispatch_kernel(
    PremapFutureKernelNativeConsumerDispatchV1 dispatch,
    uint32_t* future_native_dispatch_consumer_ok,
    uint64_t* future_native_dispatch_consumer_hash,
    uint32_t* future_native_dispatch_single_field_mirror_ok,
    uint64_t* future_native_dispatch_single_field_mirror_hash) {
  const uint32_t program_id = static_cast<uint32_t>(blockIdx.x);
  const uint32_t lane_id = static_cast<uint32_t>(threadIdx.x);
  const bool row_window_valid =
      dispatch.row_limit >= dispatch.row_offset &&
      dispatch.row_limit <= dispatch.launch.params.row_count;
  const uint32_t active_rows =
      row_window_valid ? dispatch.row_limit - dispatch.row_offset : 0;
  if (!row_window_valid) {
    return;
  }
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(dispatch.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  if (local_row_index_64 >= static_cast<uint64_t>(active_rows)) {
    return;
  }
  const uint32_t idx = static_cast<uint32_t>(local_row_index_64);
  const PremapFutureKernelNativeConsumerDispatchResultV1 result =
      premap_typed_consumer_future_native_dispatch_consume_program_lane_v1(
          dispatch,
          program_id,
          lane_id,
          static_cast<uint32_t>(gridDim.x),
          static_cast<uint32_t>(blockDim.x),
          kTypedSchemaHashHi,
          kTypedSchemaHashLo);
  future_native_dispatch_consumer_ok[idx] = result.ok;
  future_native_dispatch_consumer_hash[idx] = result.row_hash;
  future_native_dispatch_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_native_dispatch_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
}

struct Args {
  int device = 0;
  int rows = 1024;
  int block_threads = 256;
  int dispatch_row_offset = 0;
  int dispatch_row_limit = -1;
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
    } else if (key == "--dispatch-row-offset") {
      args.dispatch_row_offset = std::atoi(require_value("--dispatch-row-offset"));
    } else if (key == "--dispatch-row-limit") {
      args.dispatch_row_limit = std::atoi(require_value("--dispatch-row-limit"));
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
  const int effective_dispatch_limit =
      args.dispatch_row_limit < 0 ? args.rows : args.dispatch_row_limit;
  if (args.dispatch_row_offset < 0 || effective_dispatch_limit <= args.dispatch_row_offset ||
      effective_dispatch_limit > args.rows) {
    std::cerr << "dispatch row window must satisfy 0 <= offset < limit <= rows\n";
    std::exit(2);
  }
  args.dispatch_row_limit = effective_dispatch_limit;
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
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
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
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)
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
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI)
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
           *d_single_field_mirror_hash = nullptr,
           *d_kernel_side_consumer_path_hash = nullptr,
           *d_kernel_side_compatible_consumer_hash = nullptr,
           *d_future_kernel_consumer_hash = nullptr,
           *d_future_kernel_single_field_mirror_hash = nullptr,
           *d_future_kernel_compatible_path_hash = nullptr,
           *d_future_native_consumer_hash = nullptr,
           *d_future_native_single_field_mirror_hash = nullptr,
           *d_future_native_launch_consumer_hash = nullptr,
           *d_future_native_launch_single_field_mirror_hash = nullptr,
           *d_future_native_dispatch_consumer_hash = nullptr,
           *d_future_native_dispatch_single_field_mirror_hash = nullptr;
  int32_t* d_expert = nullptr;
  uint32_t *d_ok = nullptr, *d_single_field_mirror_ok = nullptr,
           *d_kernel_side_consumer_path_ok = nullptr,
           *d_kernel_side_compatible_consumer_ok = nullptr,
           *d_future_kernel_consumer_ok = nullptr,
           *d_future_kernel_single_field_mirror_ok = nullptr,
           *d_future_kernel_compatible_path_ok = nullptr,
           *d_future_native_consumer_ok = nullptr,
           *d_future_native_single_field_mirror_ok = nullptr,
           *d_future_native_launch_consumer_ok = nullptr,
           *d_future_native_launch_single_field_mirror_ok = nullptr,
           *d_future_native_dispatch_consumer_ok = nullptr,
           *d_future_native_dispatch_single_field_mirror_ok = nullptr;
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
  hip_check(
      hipMalloc(&d_kernel_side_consumer_path_ok, u32_bytes),
      "hipMalloc kernel_side_consumer_path_ok");
  hip_check(
      hipMalloc(&d_kernel_side_consumer_path_hash, u64_bytes),
      "hipMalloc kernel_side_consumer_path_hash");
  hip_check(
      hipMalloc(&d_kernel_side_compatible_consumer_ok, u32_bytes),
      "hipMalloc kernel_side_compatible_consumer_ok");
  hip_check(
      hipMalloc(&d_kernel_side_compatible_consumer_hash, u64_bytes),
      "hipMalloc kernel_side_compatible_consumer_hash");
  hip_check(
      hipMalloc(&d_future_kernel_consumer_ok, u32_bytes),
      "hipMalloc future_kernel_consumer_ok");
  hip_check(
      hipMalloc(&d_future_kernel_consumer_hash, u64_bytes),
      "hipMalloc future_kernel_consumer_hash");
  hip_check(
      hipMalloc(&d_future_kernel_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_kernel_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_kernel_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_kernel_single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_future_kernel_compatible_path_ok, u32_bytes),
      "hipMalloc future_kernel_compatible_path_ok");
  hip_check(
      hipMalloc(&d_future_kernel_compatible_path_hash, u64_bytes),
      "hipMalloc future_kernel_compatible_path_hash");
  hip_check(
      hipMalloc(&d_future_native_consumer_ok, u32_bytes),
      "hipMalloc future_native_consumer_ok");
  hip_check(
      hipMalloc(&d_future_native_consumer_hash, u64_bytes),
      "hipMalloc future_native_consumer_hash");
  hip_check(
      hipMalloc(&d_future_native_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_native_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_native_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_native_single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_future_native_launch_consumer_ok, u32_bytes),
      "hipMalloc future_native_launch_consumer_ok");
  hip_check(
      hipMalloc(&d_future_native_launch_consumer_hash, u64_bytes),
      "hipMalloc future_native_launch_consumer_hash");
  hip_check(
      hipMalloc(&d_future_native_launch_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_native_launch_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_native_launch_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_native_launch_single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_future_native_dispatch_consumer_ok, u32_bytes),
      "hipMalloc future_native_dispatch_consumer_ok");
  hip_check(
      hipMalloc(&d_future_native_dispatch_consumer_hash, u64_bytes),
      "hipMalloc future_native_dispatch_consumer_hash");
  hip_check(
      hipMalloc(&d_future_native_dispatch_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_native_dispatch_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_native_dispatch_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_native_dispatch_single_field_mirror_hash");
  hip_check(hipMemcpy(d_descriptor, descriptor.data(), u64_bytes, hipMemcpyHostToDevice), "copy descriptor");
  hip_check(hipMemcpy(d_packed, packed.data(), u64_bytes, hipMemcpyHostToDevice), "copy packed");
  hip_check(hipMemcpy(d_scale, scale.data(), u64_bytes, hipMemcpyHostToDevice), "copy scale");
  if (!args.omit_aux_pointer) {
    hip_check(hipMemcpy(d_aux, aux.data(), u64_bytes, hipMemcpyHostToDevice), "copy aux");
  }
  hip_check(hipMemcpy(d_address_key, address_key.data(), u64_bytes, hipMemcpyHostToDevice), "copy address_key");
  hip_check(hipMemcpy(d_expert, expert.data(), i32_bytes, hipMemcpyHostToDevice), "copy expert");
  hip_check(hipMemset(d_future_kernel_consumer_ok, 0, u32_bytes), "memset future_kernel_consumer_ok");
  hip_check(hipMemset(d_future_kernel_consumer_hash, 0, u64_bytes), "memset future_kernel_consumer_hash");
  hip_check(hipMemset(d_future_kernel_single_field_mirror_ok, 0, u32_bytes), "memset future_kernel_single_field_mirror_ok");
  hip_check(hipMemset(d_future_kernel_single_field_mirror_hash, 0, u64_bytes), "memset future_kernel_single_field_mirror_hash");
  hip_check(hipMemset(d_future_kernel_compatible_path_ok, 0, u32_bytes), "memset future_kernel_compatible_path_ok");
  hip_check(hipMemset(d_future_kernel_compatible_path_hash, 0, u64_bytes), "memset future_kernel_compatible_path_hash");
  hip_check(hipMemset(d_future_native_consumer_ok, 0, u32_bytes), "memset future_native_consumer_ok");
  hip_check(hipMemset(d_future_native_consumer_hash, 0, u64_bytes), "memset future_native_consumer_hash");
  hip_check(hipMemset(d_future_native_single_field_mirror_ok, 0, u32_bytes), "memset future_native_single_field_mirror_ok");
  hip_check(hipMemset(d_future_native_single_field_mirror_hash, 0, u64_bytes), "memset future_native_single_field_mirror_hash");
  hip_check(
      hipMemset(d_future_native_launch_consumer_ok, 0, u32_bytes),
      "memset future_native_launch_consumer_ok");
  hip_check(
      hipMemset(d_future_native_launch_consumer_hash, 0, u64_bytes),
      "memset future_native_launch_consumer_hash");
  hip_check(
      hipMemset(d_future_native_launch_single_field_mirror_ok, 0, u32_bytes),
      "memset future_native_launch_single_field_mirror_ok");
  hip_check(
      hipMemset(d_future_native_launch_single_field_mirror_hash, 0, u64_bytes),
      "memset future_native_launch_single_field_mirror_hash");
  hip_check(
      hipMemset(d_future_native_dispatch_consumer_ok, 0, u32_bytes),
      "memset future_native_dispatch_consumer_ok");
  hip_check(
      hipMemset(d_future_native_dispatch_consumer_hash, 0, u64_bytes),
      "memset future_native_dispatch_consumer_hash");
  hip_check(
      hipMemset(d_future_native_dispatch_single_field_mirror_ok, 0, u32_bytes),
      "memset future_native_dispatch_single_field_mirror_ok");
  hip_check(
      hipMemset(d_future_native_dispatch_single_field_mirror_hash, 0, u64_bytes),
      "memset future_native_dispatch_single_field_mirror_hash");

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
  const uint32_t future_kernel_consumer_args_field_mask =
      args.omit_aux_pointer ? kPremapFutureKernelSideConsumerFieldMaskRequired
                            : kPremapFutureKernelSideConsumerFieldMaskAll;

  const uint32_t threads = static_cast<uint32_t>(args.block_threads);
  const uint64_t blocks_u64 =
      (static_cast<uint64_t>(rows) + static_cast<uint64_t>(threads) - 1ULL) /
      static_cast<uint64_t>(threads);
  if (blocks_u64 == 0 || blocks_u64 > 0xffffffffULL) {
    std::cerr << "computed block count is outside uint32 range\n";
    std::exit(2);
  }
  const uint32_t blocks = static_cast<uint32_t>(blocks_u64);
  const uint64_t launch_threads =
      static_cast<uint64_t>(blocks) * static_cast<uint64_t>(threads);
  const uint32_t dispatch_row_offset =
      static_cast<uint32_t>(args.dispatch_row_offset);
  const uint32_t dispatch_row_limit =
      static_cast<uint32_t>(args.dispatch_row_limit);
  const uint32_t dispatch_active_rows =
      dispatch_row_limit >= dispatch_row_offset
          ? dispatch_row_limit - dispatch_row_offset
          : 0;
  const uint64_t dispatch_blocks_u64 =
      (static_cast<uint64_t>(dispatch_active_rows) +
       static_cast<uint64_t>(threads) - 1ULL) /
      static_cast<uint64_t>(threads);
  if (dispatch_blocks_u64 == 0 || dispatch_blocks_u64 > 0xffffffffULL) {
    std::cerr << "computed dispatch block count is outside uint32 range\n";
    std::exit(2);
  }
  const uint32_t dispatch_blocks = static_cast<uint32_t>(dispatch_blocks_u64);
  const uint64_t dispatch_launch_threads =
      static_cast<uint64_t>(dispatch_blocks) * static_cast<uint64_t>(threads);
  const bool dispatch_launch_covers_active_rows =
      dispatch_launch_threads >= static_cast<uint64_t>(dispatch_active_rows);
  const bool dispatch_launch_minimal_cover =
      dispatch_blocks == 1 ||
      ((static_cast<uint64_t>(dispatch_blocks - 1) *
        static_cast<uint64_t>(threads)) <
       static_cast<uint64_t>(dispatch_active_rows));
  const uint64_t dispatch_previous_program_threads =
      dispatch_blocks > 0
          ? static_cast<uint64_t>(dispatch_blocks - 1) *
                static_cast<uint64_t>(threads)
          : 0ULL;
  const uint32_t dispatch_full_program_count =
      static_cast<uint32_t>(
          static_cast<uint64_t>(dispatch_active_rows) /
          static_cast<uint64_t>(threads));
  const uint32_t dispatch_last_program_active_rows =
      dispatch_active_rows > 0
          ? static_cast<uint32_t>(
                static_cast<uint64_t>(dispatch_active_rows) -
                dispatch_previous_program_threads)
          : 0;
  const uint32_t dispatch_inactive_lane_count =
      dispatch_launch_threads >= static_cast<uint64_t>(dispatch_active_rows)
          ? static_cast<uint32_t>(
                dispatch_launch_threads -
                static_cast<uint64_t>(dispatch_active_rows))
          : 0;
  const uint32_t dispatch_first_program_row_offset = dispatch_row_offset;
  const uint32_t dispatch_last_program_row_offset =
      static_cast<uint32_t>(
          static_cast<uint64_t>(dispatch_row_offset) +
          dispatch_previous_program_threads);
  const uint64_t dispatch_program_iteration_hash =
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_blocks) + 0xd15c2001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(threads) + 0xd15c2002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_row_offset) + 0xd15c2003ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_row_limit) + 0xd15c2004ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_last_program_active_rows) +
          0xd15c2005ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_inactive_lane_count) + 0xd15c2006ULL);
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
      d_single_field_mirror_hash,
      d_kernel_side_consumer_path_ok,
      d_kernel_side_consumer_path_hash,
      d_kernel_side_compatible_consumer_ok,
      d_kernel_side_compatible_consumer_hash);
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
      d_single_field_mirror_hash,
      d_kernel_side_consumer_path_ok,
      d_kernel_side_consumer_path_hash,
      d_kernel_side_compatible_consumer_ok,
      d_kernel_side_compatible_consumer_hash);
#endif
  hip_check(hipGetLastError(), "kernel launch");
  hip_check(hipDeviceSynchronize(), "kernel sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS)
  PremapKernelSideTypedConsumerLaunchEnvelopeV1 future_envelope;
  future_envelope.table = table;
  future_envelope.expected_schema_hash_hi = kTypedSchemaHashHi;
  future_envelope.expected_schema_hash_lo = kTypedSchemaHashLo;
  future_envelope.expected_row_order_hash = table.row_order_hash;
  future_envelope.expected_ordered_row_hash = table.ordered_row_hash;
  future_envelope.expected_row_count = table.row_count;
  future_envelope.expected_column_count = table.column_count;
  future_envelope.payload_bytes = 0;
  future_envelope.flags =
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag |
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag;
  PremapFutureKernelSideConsumerArgsV1 future_args;
  future_args.envelope = future_envelope;
  future_args.field_mask = future_kernel_consumer_args_field_mask;
  future_args.single_field_mirror_kind = kSingleFieldMirrorKind;
  future_args.payload_bytes = 0;
  future_args.flags = kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_kernel_args_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      future_args,
      d_future_kernel_consumer_ok,
      d_future_kernel_consumer_hash,
      d_future_kernel_single_field_mirror_ok,
      d_future_kernel_single_field_mirror_hash,
      d_future_kernel_compatible_path_ok,
      d_future_kernel_compatible_path_hash);
  hip_check(hipGetLastError(), "future kernel consumer args launch");
  hip_check(hipDeviceSynchronize(), "future kernel consumer args sync");
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI)
  PremapFutureKernelNativeConsumerParamsV1 future_native_params;
  future_native_params.descriptor_ptr = table.descriptor_ptr;
  future_native_params.packed_weight_descriptor = table.packed_weight_descriptor;
  future_native_params.scale_metadata_handle = table.scale_metadata_handle;
  future_native_params.aux_metadata_handle = table.aux_metadata_handle;
  future_native_params.expert_id = table.expert_id;
  future_native_params.address_key_hash = table.address_key_hash;
  future_native_params.typed_schema_hash_hi = table.typed_schema_hash_hi;
  future_native_params.typed_schema_hash_lo = table.typed_schema_hash_lo;
  future_native_params.row_order_hash = table.row_order_hash;
  future_native_params.ordered_row_hash = table.ordered_row_hash;
  future_native_params.row_count = table.row_count;
  future_native_params.column_count = table.column_count;
  future_native_params.lifetime_epoch = table.lifetime_epoch;
  future_native_params.field_mask = future_kernel_consumer_args_field_mask;
  future_native_params.single_field_mirror_kind = kSingleFieldMirrorKind;
  future_native_params.payload_bytes = 0;
  future_native_params.flags = kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      future_native_params,
      d_future_native_consumer_ok,
      d_future_native_consumer_hash,
      d_future_native_single_field_mirror_ok,
      d_future_native_single_field_mirror_hash);
  hip_check(hipGetLastError(), "future native consumer launch");
  hip_check(hipDeviceSynchronize(), "future native consumer sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI)
  PremapFutureKernelNativeConsumerLaunchV1 future_native_launch;
  future_native_launch.params = future_native_params;
  future_native_launch.abi_version =
      kPremapFutureKernelNativeConsumerLaunchAbiV1Version;
  future_native_launch.params_struct_size =
      sizeof(PremapFutureKernelNativeConsumerParamsV1);
  future_native_launch.result_struct_size =
      sizeof(PremapFutureKernelNativeConsumerLaunchResultV1);
  future_native_launch.row_stride = 1;
  future_native_launch.payload_bytes = 0;
  future_native_launch.flags = kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_launch_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      future_native_launch,
      d_future_native_launch_consumer_ok,
      d_future_native_launch_consumer_hash,
      d_future_native_launch_single_field_mirror_ok,
      d_future_native_launch_single_field_mirror_hash);
  hip_check(hipGetLastError(), "future native launch consumer launch");
  hip_check(hipDeviceSynchronize(), "future native launch consumer sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI)
  PremapFutureKernelNativeConsumerDispatchV1 future_native_dispatch;
  future_native_dispatch.launch = future_native_launch;
  future_native_dispatch.dispatch_version =
      kPremapFutureKernelNativeConsumerDispatchAbiV1Version;
  future_native_dispatch.grid_x = static_cast<uint32_t>(dispatch_blocks);
  future_native_dispatch.block_x = static_cast<uint32_t>(threads);
  future_native_dispatch.shared_mem_bytes = 0;
  future_native_dispatch.row_offset = dispatch_row_offset;
  future_native_dispatch.row_limit = dispatch_row_limit;
  future_native_dispatch.rows_per_program = static_cast<uint32_t>(threads);
  future_native_dispatch.payload_bytes = 0;
  future_native_dispatch.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_dispatch_kernel,
      dim3(dispatch_blocks),
      dim3(threads),
      0,
      0,
      future_native_dispatch,
      d_future_native_dispatch_consumer_ok,
      d_future_native_dispatch_consumer_hash,
      d_future_native_dispatch_single_field_mirror_ok,
      d_future_native_dispatch_single_field_mirror_hash);
  hip_check(hipGetLastError(), "future native dispatch consumer launch");
  hip_check(hipDeviceSynchronize(), "future native dispatch consumer sync");
#endif
#endif
#endif

  std::vector<uint32_t> ok(rows);
  std::vector<uint64_t> hashes(rows);
  std::vector<uint32_t> single_field_mirror_ok(rows);
  std::vector<uint64_t> single_field_mirror_hashes(rows);
  std::vector<uint32_t> kernel_side_consumer_path_ok(rows);
  std::vector<uint64_t> kernel_side_consumer_path_hashes(rows);
  std::vector<uint32_t> kernel_side_compatible_consumer_ok(rows);
  std::vector<uint64_t> kernel_side_compatible_consumer_hashes(rows);
  std::vector<uint32_t> future_kernel_consumer_ok(rows);
  std::vector<uint64_t> future_kernel_consumer_hashes(rows);
  std::vector<uint32_t> future_kernel_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_kernel_single_field_mirror_hashes(rows);
  std::vector<uint32_t> future_kernel_compatible_path_ok(rows);
  std::vector<uint64_t> future_kernel_compatible_path_hashes(rows);
  std::vector<uint32_t> future_native_consumer_ok(rows);
  std::vector<uint64_t> future_native_consumer_hashes(rows);
  std::vector<uint32_t> future_native_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_native_single_field_mirror_hashes(rows);
  std::vector<uint32_t> future_native_launch_consumer_ok(rows);
  std::vector<uint64_t> future_native_launch_consumer_hashes(rows);
  std::vector<uint32_t> future_native_launch_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_native_launch_single_field_mirror_hashes(rows);
  std::vector<uint32_t> future_native_dispatch_consumer_ok(rows);
  std::vector<uint64_t> future_native_dispatch_consumer_hashes(rows);
  std::vector<uint32_t> future_native_dispatch_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_native_dispatch_single_field_mirror_hashes(rows);
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
  hip_check(
      hipMemcpy(
          kernel_side_consumer_path_ok.data(),
          d_kernel_side_consumer_path_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy kernel_side_consumer_path_ok");
  hip_check(
      hipMemcpy(
          kernel_side_consumer_path_hashes.data(),
          d_kernel_side_consumer_path_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy kernel_side_consumer_path_hash");
  hip_check(
      hipMemcpy(
          kernel_side_compatible_consumer_ok.data(),
          d_kernel_side_compatible_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy kernel_side_compatible_consumer_ok");
  hip_check(
      hipMemcpy(
          kernel_side_compatible_consumer_hashes.data(),
          d_kernel_side_compatible_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy kernel_side_compatible_consumer_hash");
  hip_check(
      hipMemcpy(
          future_kernel_consumer_ok.data(),
          d_future_kernel_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_consumer_ok");
  hip_check(
      hipMemcpy(
          future_kernel_consumer_hashes.data(),
          d_future_kernel_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_consumer_hash");
  hip_check(
      hipMemcpy(
          future_kernel_single_field_mirror_ok.data(),
          d_future_kernel_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_kernel_single_field_mirror_hashes.data(),
          d_future_kernel_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          future_kernel_compatible_path_ok.data(),
          d_future_kernel_compatible_path_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_compatible_path_ok");
  hip_check(
      hipMemcpy(
          future_kernel_compatible_path_hashes.data(),
          d_future_kernel_compatible_path_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_compatible_path_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_ok.data(),
          d_future_native_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_hashes.data(),
          d_future_native_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_hash");
  hip_check(
      hipMemcpy(
          future_native_single_field_mirror_ok.data(),
          d_future_native_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_native_single_field_mirror_hashes.data(),
          d_future_native_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          future_native_launch_consumer_ok.data(),
          d_future_native_launch_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_launch_consumer_ok");
  hip_check(
      hipMemcpy(
          future_native_launch_consumer_hashes.data(),
          d_future_native_launch_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_launch_consumer_hash");
  hip_check(
      hipMemcpy(
          future_native_launch_single_field_mirror_ok.data(),
          d_future_native_launch_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_launch_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_native_launch_single_field_mirror_hashes.data(),
          d_future_native_launch_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_launch_single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          future_native_dispatch_consumer_ok.data(),
          d_future_native_dispatch_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_consumer_ok");
  hip_check(
      hipMemcpy(
          future_native_dispatch_consumer_hashes.data(),
          d_future_native_dispatch_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_consumer_hash");
  hip_check(
      hipMemcpy(
          future_native_dispatch_single_field_mirror_ok.data(),
          d_future_native_dispatch_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_native_dispatch_single_field_mirror_hashes.data(),
          d_future_native_dispatch_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_single_field_mirror_hash");

  uint64_t hash_acc = 0;
  uint64_t single_field_mirror_hash_acc = 0;
  uint64_t kernel_side_consumer_path_hash_acc = 0;
  uint64_t kernel_side_compatible_consumer_hash_acc = 0;
  uint64_t future_kernel_consumer_hash_acc = 0;
  uint64_t future_kernel_single_field_mirror_hash_acc = 0;
  uint64_t future_kernel_compatible_path_hash_acc = 0;
  uint64_t future_native_consumer_hash_acc = 0;
  uint64_t future_native_single_field_mirror_hash_acc = 0;
  uint64_t future_native_launch_consumer_hash_acc = 0;
  uint64_t future_native_launch_single_field_mirror_hash_acc = 0;
  uint64_t future_native_dispatch_consumer_hash_acc = 0;
  uint64_t future_native_dispatch_single_field_mirror_hash_acc = 0;
  int ok_count = 0;
  int single_field_mirror_ok_count = 0;
  int kernel_side_consumer_path_ok_count = 0;
  int kernel_side_compatible_consumer_ok_count = 0;
  int future_kernel_consumer_ok_count = 0;
  int future_kernel_single_field_mirror_ok_count = 0;
  int future_kernel_compatible_path_ok_count = 0;
  int future_native_consumer_ok_count = 0;
  int future_native_single_field_mirror_ok_count = 0;
  int future_native_launch_consumer_ok_count = 0;
  int future_native_launch_single_field_mirror_ok_count = 0;
  int future_native_dispatch_consumer_ok_count = 0;
  int future_native_dispatch_single_field_mirror_ok_count = 0;
  for (int i = 0; i < rows; ++i) {
    ok_count += ok[i] == 1 ? 1 : 0;
    hash_acc ^= mix64(hashes[i] + static_cast<uint64_t>(i));
    single_field_mirror_ok_count += single_field_mirror_ok[i] == 1 ? 1 : 0;
    single_field_mirror_hash_acc ^=
        mix64(single_field_mirror_hashes[i] + static_cast<uint64_t>(i));
    kernel_side_consumer_path_ok_count +=
        kernel_side_consumer_path_ok[i] == 1 ? 1 : 0;
    kernel_side_consumer_path_hash_acc ^=
        mix64(kernel_side_consumer_path_hashes[i] + static_cast<uint64_t>(i));
    kernel_side_compatible_consumer_ok_count +=
        kernel_side_compatible_consumer_ok[i] == 1 ? 1 : 0;
    kernel_side_compatible_consumer_hash_acc ^=
        mix64(kernel_side_compatible_consumer_hashes[i] + static_cast<uint64_t>(i));
    future_kernel_consumer_ok_count +=
        future_kernel_consumer_ok[i] == 1 ? 1 : 0;
    future_kernel_consumer_hash_acc ^=
        mix64(future_kernel_consumer_hashes[i] + static_cast<uint64_t>(i));
    future_kernel_single_field_mirror_ok_count +=
        future_kernel_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_kernel_single_field_mirror_hash_acc ^=
        mix64(
            future_kernel_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
    future_kernel_compatible_path_ok_count +=
        future_kernel_compatible_path_ok[i] == 1 ? 1 : 0;
    future_kernel_compatible_path_hash_acc ^=
        mix64(
            future_kernel_compatible_path_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_ok_count +=
        future_native_consumer_ok[i] == 1 ? 1 : 0;
    future_native_consumer_hash_acc ^=
        mix64(future_native_consumer_hashes[i] + static_cast<uint64_t>(i));
    future_native_single_field_mirror_ok_count +=
        future_native_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_native_single_field_mirror_hash_acc ^=
        mix64(
            future_native_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_launch_consumer_ok_count +=
        future_native_launch_consumer_ok[i] == 1 ? 1 : 0;
    future_native_launch_consumer_hash_acc ^=
        mix64(
            future_native_launch_consumer_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_launch_single_field_mirror_ok_count +=
        future_native_launch_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_native_launch_single_field_mirror_hash_acc ^=
        mix64(
            future_native_launch_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_dispatch_consumer_ok_count +=
        future_native_dispatch_consumer_ok[i] == 1 ? 1 : 0;
    future_native_dispatch_consumer_hash_acc ^=
        mix64(
            future_native_dispatch_consumer_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_dispatch_single_field_mirror_ok_count +=
        future_native_dispatch_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_native_dispatch_single_field_mirror_hash_acc ^=
        mix64(
            future_native_dispatch_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
  }
  const int error_count = rows - ok_count;
  const bool single_field_mirror_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD) || \
    defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD) || \
    defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD) || \
    defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
      true;
#else
      false;
#endif
  const int single_field_mirror_row_count =
      single_field_mirror_checked ? rows : 0;
  const int single_field_mirror_error_count =
      single_field_mirror_checked ? rows - single_field_mirror_ok_count : 0;
  const bool kernel_side_consumer_path_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH)
      true;
#else
      false;
#endif
  const int kernel_side_consumer_path_row_count =
      kernel_side_consumer_path_checked ? rows : 0;
  const int kernel_side_consumer_path_error_count =
      kernel_side_consumer_path_checked ? rows - kernel_side_consumer_path_ok_count : 0;
  const bool kernel_side_compatible_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI)
      true;
#else
      false;
#endif
  const int kernel_side_compatible_consumer_row_count =
      kernel_side_compatible_consumer_checked ? rows : 0;
  const int kernel_side_compatible_consumer_error_count =
      kernel_side_compatible_consumer_checked
          ? rows - kernel_side_compatible_consumer_ok_count
          : 0;
  const bool future_kernel_consumer_args_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS)
      true;
#else
      false;
#endif
  const int future_kernel_consumer_args_row_count =
      future_kernel_consumer_args_checked ? rows : 0;
  const int future_kernel_consumer_args_error_count =
      future_kernel_consumer_args_checked ? rows - future_kernel_consumer_ok_count
                                          : 0;
  const bool future_kernel_single_field_mirror_checked =
      future_kernel_consumer_args_checked && single_field_mirror_checked;
  const int future_kernel_single_field_mirror_row_count =
      future_kernel_single_field_mirror_checked ? rows : 0;
  const int future_kernel_single_field_mirror_error_count =
      future_kernel_single_field_mirror_checked
          ? rows - future_kernel_single_field_mirror_ok_count
          : 0;
  const bool future_kernel_compatible_path_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH)
      true;
#else
      false;
#endif
  const int future_kernel_compatible_path_row_count =
      future_kernel_compatible_path_checked ? rows : 0;
  const int future_kernel_compatible_path_error_count =
      future_kernel_compatible_path_checked
          ? rows - future_kernel_compatible_path_ok_count
          : 0;
  const bool future_native_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_row_count =
      future_native_consumer_checked ? rows : 0;
  const int future_native_consumer_error_count =
      future_native_consumer_checked
          ? rows - future_native_consumer_ok_count
          : 0;
  const bool future_native_single_field_mirror_checked =
      future_native_consumer_checked && single_field_mirror_checked;
  const int future_native_single_field_mirror_row_count =
      future_native_single_field_mirror_checked ? rows : 0;
  const int future_native_single_field_mirror_error_count =
      future_native_single_field_mirror_checked
          ? rows - future_native_single_field_mirror_ok_count
          : 0;
  const bool future_native_launch_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI)
      true;
#else
      false;
#endif
  const int future_native_launch_consumer_row_count =
      future_native_launch_consumer_checked ? rows : 0;
  const int future_native_launch_consumer_error_count =
      future_native_launch_consumer_checked
          ? rows - future_native_launch_consumer_ok_count
          : 0;
  const bool future_native_launch_single_field_mirror_checked =
      future_native_launch_consumer_checked && single_field_mirror_checked;
  const int future_native_launch_single_field_mirror_row_count =
      future_native_launch_single_field_mirror_checked ? rows : 0;
  const int future_native_launch_single_field_mirror_error_count =
      future_native_launch_single_field_mirror_checked
          ? rows - future_native_launch_single_field_mirror_ok_count
          : 0;
  const bool future_native_dispatch_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI)
      true;
#else
      false;
#endif
  const int future_native_dispatch_active_rows =
      future_native_dispatch_consumer_checked
          ? static_cast<int>(dispatch_active_rows)
          : 0;
  const bool future_native_dispatch_launch_covers_active_rows =
      future_native_dispatch_consumer_checked
          ? dispatch_launch_covers_active_rows
          : false;
  const bool future_native_dispatch_launch_minimal_cover =
      future_native_dispatch_consumer_checked ? dispatch_launch_minimal_cover : false;
  const int future_native_dispatch_consumer_row_count =
      future_native_dispatch_consumer_checked ? future_native_dispatch_active_rows : 0;
  const int future_native_dispatch_consumer_error_count =
      future_native_dispatch_consumer_checked
          ? future_native_dispatch_active_rows -
                future_native_dispatch_consumer_ok_count
          : 0;
  const bool future_native_dispatch_single_field_mirror_checked =
      future_native_dispatch_consumer_checked && single_field_mirror_checked;
  const int future_native_dispatch_single_field_mirror_row_count =
      future_native_dispatch_single_field_mirror_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_dispatch_single_field_mirror_error_count =
      future_native_dispatch_single_field_mirror_checked
          ? future_native_dispatch_active_rows -
                future_native_dispatch_single_field_mirror_ok_count
          : 0;
  const bool all_ok =
      error_count == 0 && future_kernel_consumer_args_error_count == 0 &&
      future_kernel_single_field_mirror_error_count == 0 &&
      future_kernel_compatible_path_error_count == 0 &&
      future_native_consumer_error_count == 0 &&
      future_native_single_field_mirror_error_count == 0 &&
      future_native_launch_consumer_error_count == 0 &&
      future_native_launch_single_field_mirror_error_count == 0 &&
      future_native_dispatch_consumer_error_count == 0 &&
      future_native_dispatch_single_field_mirror_error_count == 0;

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
  hip_check(
      hipFree(d_kernel_side_consumer_path_ok),
      "hipFree kernel_side_consumer_path_ok");
  hip_check(
      hipFree(d_kernel_side_consumer_path_hash),
      "hipFree kernel_side_consumer_path_hash");
  hip_check(
      hipFree(d_kernel_side_compatible_consumer_ok),
      "hipFree kernel_side_compatible_consumer_ok");
  hip_check(
      hipFree(d_kernel_side_compatible_consumer_hash),
      "hipFree kernel_side_compatible_consumer_hash");
  hip_check(
      hipFree(d_future_kernel_consumer_ok),
      "hipFree future_kernel_consumer_ok");
  hip_check(
      hipFree(d_future_kernel_consumer_hash),
      "hipFree future_kernel_consumer_hash");
  hip_check(
      hipFree(d_future_kernel_single_field_mirror_ok),
      "hipFree future_kernel_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_kernel_single_field_mirror_hash),
      "hipFree future_kernel_single_field_mirror_hash");
  hip_check(
      hipFree(d_future_kernel_compatible_path_ok),
      "hipFree future_kernel_compatible_path_ok");
  hip_check(
      hipFree(d_future_kernel_compatible_path_hash),
      "hipFree future_kernel_compatible_path_hash");
  hip_check(
      hipFree(d_future_native_consumer_ok),
      "hipFree future_native_consumer_ok");
  hip_check(
      hipFree(d_future_native_consumer_hash),
      "hipFree future_native_consumer_hash");
  hip_check(
      hipFree(d_future_native_single_field_mirror_ok),
      "hipFree future_native_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_native_single_field_mirror_hash),
      "hipFree future_native_single_field_mirror_hash");
  hip_check(
      hipFree(d_future_native_launch_consumer_ok),
      "hipFree future_native_launch_consumer_ok");
  hip_check(
      hipFree(d_future_native_launch_consumer_hash),
      "hipFree future_native_launch_consumer_hash");
  hip_check(
      hipFree(d_future_native_launch_single_field_mirror_ok),
      "hipFree future_native_launch_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_native_launch_single_field_mirror_hash),
      "hipFree future_native_launch_single_field_mirror_hash");
  hip_check(
      hipFree(d_future_native_dispatch_consumer_ok),
      "hipFree future_native_dispatch_consumer_ok");
  hip_check(
      hipFree(d_future_native_dispatch_consumer_hash),
      "hipFree future_native_dispatch_consumer_hash");
  hip_check(
      hipFree(d_future_native_dispatch_single_field_mirror_ok),
      "hipFree future_native_dispatch_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_native_dispatch_single_field_mirror_hash),
      "hipFree future_native_dispatch_single_field_mirror_hash");

  std::cout << "{";
  std::cout << "\"ok\":" << (all_ok ? "true" : "false");
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
  std::cout << ",\"kernel_side_consumer_path_name\":\""
            << kPremapKernelSideTypedConsumerPathV1Name << "\"";
  std::cout << ",\"kernel_side_consumer_path_checked\":"
            << (kernel_side_consumer_path_checked ? "true" : "false");
  std::cout << ",\"kernel_side_consumer_path_mode\":\"readonly_typed_row_consumer_path\"";
  std::cout << ",\"kernel_side_consumer_path_source\":\""
            << kPremapKernelSideTypedConsumerAdapterV1Name << "\"";
  std::cout << ",\"kernel_side_consumer_path_row_count\":"
            << kernel_side_consumer_path_row_count;
  std::cout << ",\"kernel_side_consumer_path_row_ok_count\":"
            << (kernel_side_consumer_path_checked
                    ? kernel_side_consumer_path_ok_count
                    : 0);
  std::cout << ",\"kernel_side_consumer_path_error_count\":"
            << kernel_side_consumer_path_error_count;
  std::cout << ",\"kernel_side_consumer_path_hash_accumulator\":\"" << std::hex
            << kernel_side_consumer_path_hash_acc << std::dec << "\"";
  std::cout << ",\"kernel_side_consumer_path_payload_bytes\":0";
  std::cout << ",\"kernel_side_consumer_path_passed_to_kernel\":false";
  std::cout << ",\"kernel_side_consumer_path_changes_kernel_launch_args\":false";
  std::cout << ",\"kernel_side_consumer_path_current_wna16_arg_compatible\":false";
  std::cout << ",\"kernel_side_compatible_consumer_name\":\""
            << kPremapKernelSideCompatibleConsumerAbiV1Name << "\"";
  std::cout << ",\"kernel_side_compatible_consumer_checked\":"
            << (kernel_side_compatible_consumer_checked ? "true" : "false");
  std::cout << ",\"kernel_side_compatible_consumer_mode\":\""
            << kPremapKernelSideCompatibleConsumerAbiV1Mode << "\"";
  std::cout << ",\"kernel_side_compatible_consumer_source\":\""
            << kPremapKernelSideTypedConsumerLaunchEnvelopeV1Name << "\"";
  std::cout << ",\"kernel_side_compatible_consumer_row_count\":"
            << kernel_side_compatible_consumer_row_count;
  std::cout << ",\"kernel_side_compatible_consumer_row_ok_count\":"
            << (kernel_side_compatible_consumer_checked
                    ? kernel_side_compatible_consumer_ok_count
                    : 0);
  std::cout << ",\"kernel_side_compatible_consumer_error_count\":"
            << kernel_side_compatible_consumer_error_count;
  std::cout << ",\"kernel_side_compatible_consumer_hash_accumulator\":\"" << std::hex
            << kernel_side_compatible_consumer_hash_acc << std::dec << "\"";
  std::cout << ",\"kernel_side_compatible_consumer_payload_bytes\":0";
  std::cout << ",\"kernel_side_compatible_consumer_payload_deref_allowed\":false";
  std::cout << ",\"kernel_side_compatible_consumer_passed_to_kernel\":false";
  std::cout << ",\"kernel_side_compatible_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"kernel_side_compatible_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"kernel_side_compatible_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"kernel_side_compatible_consumer_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_consumer_args_name\":\""
            << kPremapFutureKernelSideConsumerArgsV1Name << "\"";
  std::cout << ",\"future_kernel_consumer_args_checked\":"
            << (future_kernel_consumer_args_checked ? "true" : "false");
  std::cout << ",\"future_kernel_consumer_args_mode\":\""
            << kPremapFutureKernelSideConsumerArgsV1Mode << "\"";
  std::cout << ",\"future_kernel_consumer_args_source\":\""
            << kPremapKernelSideTypedConsumerLaunchEnvelopeV1Name << "\"";
  std::cout << ",\"future_kernel_consumer_args_row_count\":"
            << future_kernel_consumer_args_row_count;
  std::cout << ",\"future_kernel_consumer_args_row_ok_count\":"
            << (future_kernel_consumer_args_checked
                    ? future_kernel_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_consumer_args_error_count\":"
            << future_kernel_consumer_args_error_count;
  std::cout << ",\"future_kernel_consumer_args_hash_accumulator\":\""
            << std::hex << future_kernel_consumer_hash_acc << std::dec << "\"";
  std::cout << ",\"future_kernel_consumer_args_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_consumer_args_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_checked\":"
            << (future_kernel_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_row_count\":"
            << future_kernel_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_row_ok_count\":"
            << (future_kernel_single_field_mirror_checked
                    ? future_kernel_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_error_count\":"
            << future_kernel_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_kernel_single_field_mirror_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_consumer_args_payload_bytes\":0";
  std::cout << ",\"future_kernel_consumer_args_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_consumer_args_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_consumer_args_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_consumer_args_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_consumer_args_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_consumer_args_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_name\":\""
            << kPremapFutureKernelArgsCompatibleConsumerPathV1Name << "\"";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_checked\":"
            << (future_kernel_compatible_path_checked ? "true" : "false");
  std::cout << ",\"future_kernel_args_compatible_consumer_path_mode\":\""
            << kPremapFutureKernelArgsCompatibleConsumerPathV1Mode << "\"";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_source\":\""
            << kPremapFutureKernelArgsCompatibleConsumerPathV1Source << "\"";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_row_count\":"
            << future_kernel_compatible_path_row_count;
  std::cout << ",\"future_kernel_args_compatible_consumer_path_row_ok_count\":"
            << (future_kernel_compatible_path_checked
                    ? future_kernel_compatible_path_ok_count
                    : 0);
  std::cout << ",\"future_kernel_args_compatible_consumer_path_error_count\":"
            << future_kernel_compatible_path_error_count;
  std::cout << ",\"future_kernel_args_compatible_consumer_path_hash_accumulator\":\""
            << std::hex << future_kernel_compatible_path_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_payload_bytes\":0";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_abi_name\":\""
            << kPremapFutureKernelNativeConsumerAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_checked\":"
            << (future_native_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_mode\":\""
            << kPremapFutureKernelNativeConsumerAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_source\":\""
            << kPremapFutureKernelNativeConsumerAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_params_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_consumer_params_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_consumer_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerResultV1);
  std::cout << ",\"future_kernel_native_consumer_result_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerResultV1);
  std::cout << ",\"future_kernel_native_consumer_params_offset_descriptor_ptr\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, descriptor_ptr);
  std::cout << ",\"future_kernel_native_consumer_params_offset_packed_weight_descriptor\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, packed_weight_descriptor);
  std::cout << ",\"future_kernel_native_consumer_params_offset_scale_metadata_handle\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, scale_metadata_handle);
  std::cout << ",\"future_kernel_native_consumer_params_offset_aux_metadata_handle\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, aux_metadata_handle);
  std::cout << ",\"future_kernel_native_consumer_params_offset_expert_id\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, expert_id);
  std::cout << ",\"future_kernel_native_consumer_params_offset_address_key_hash\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, address_key_hash);
  std::cout << ",\"future_kernel_native_consumer_params_offset_row_count\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, row_count);
  std::cout << ",\"future_kernel_native_consumer_params_offset_field_mask\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, field_mask);
  std::cout << ",\"future_kernel_native_consumer_params_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_params_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, flags);
  std::cout << ",\"future_kernel_native_consumer_row_count\":"
            << future_native_consumer_row_count;
  std::cout << ",\"future_kernel_native_consumer_row_ok_count\":"
            << (future_native_consumer_checked
                    ? future_native_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_error_count\":"
            << future_native_consumer_error_count;
  std::cout << ",\"future_kernel_native_consumer_hash_accumulator\":\""
            << std::hex << future_native_consumer_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_consumer_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_checked\":"
            << (future_native_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_row_count\":"
            << future_native_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_row_ok_count\":"
            << (future_native_single_field_mirror_checked
                    ? future_native_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_error_count\":"
            << future_native_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_native_single_field_mirror_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_abi_name\":\""
            << kPremapFutureKernelNativeConsumerLaunchAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_checked\":"
            << (future_native_launch_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_launch_consumer_mode\":\""
            << kPremapFutureKernelNativeConsumerLaunchAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_source\":\""
            << kPremapFutureKernelNativeConsumerLaunchAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_version\":"
            << kPremapFutureKernelNativeConsumerLaunchAbiV1Version;
  std::cout << ",\"future_kernel_native_launch_consumer_launch_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchV1);
  std::cout << ",\"future_kernel_native_launch_consumer_launch_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerLaunchV1);
  std::cout << ",\"future_kernel_native_launch_consumer_params_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_launch_consumer_params_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_launch_consumer_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchResultV1);
  std::cout << ",\"future_kernel_native_launch_consumer_result_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerLaunchResultV1);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_params\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, params);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_abi_version\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, abi_version);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_params_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, params_struct_size);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_result_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, result_struct_size);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_row_stride\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, row_stride);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, payload_bytes);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, flags);
  std::cout << ",\"future_kernel_native_launch_consumer_row_stride\":1";
  std::cout << ",\"future_kernel_native_launch_consumer_row_count\":"
            << future_native_launch_consumer_row_count;
  std::cout << ",\"future_kernel_native_launch_consumer_row_ok_count\":"
            << (future_native_launch_consumer_checked
                    ? future_native_launch_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_launch_consumer_error_count\":"
            << future_native_launch_consumer_error_count;
  std::cout << ",\"future_kernel_native_launch_consumer_hash_accumulator\":\""
            << std::hex << future_native_launch_consumer_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_launch_consumer_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_checked\":"
            << (future_native_launch_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_row_count\":"
            << future_native_launch_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_row_ok_count\":"
            << (future_native_launch_single_field_mirror_checked
                    ? future_native_launch_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_error_count\":"
            << future_native_launch_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_native_launch_single_field_mirror_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_launch_consumer_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_abi_name\":\""
            << kPremapFutureKernelNativeConsumerDispatchAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_checked\":"
            << (future_native_dispatch_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_mode\":\""
            << kPremapFutureKernelNativeConsumerDispatchAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_source\":\""
            << kPremapFutureKernelNativeConsumerDispatchAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_version\":"
            << kPremapFutureKernelNativeConsumerDispatchAbiV1Version;
  std::cout << ",\"future_kernel_native_dispatch_consumer_dispatch_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerDispatchV1);
  std::cout << ",\"future_kernel_native_dispatch_consumer_dispatch_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerDispatchV1);
  std::cout << ",\"future_kernel_native_dispatch_consumer_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerDispatchResultV1);
  std::cout << ",\"future_kernel_native_dispatch_consumer_result_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerDispatchResultV1);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_launch\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, launch);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_dispatch_version\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, dispatch_version);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_grid_x\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, grid_x);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_block_x\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, block_x);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_shared_mem_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, shared_mem_bytes);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_row_offset\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, row_offset);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_row_limit\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, row_limit);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_rows_per_program\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, rows_per_program);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, payload_bytes);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, flags);
  std::cout << ",\"future_kernel_native_dispatch_consumer_grid_x\":"
            << dispatch_blocks;
  std::cout << ",\"future_kernel_native_dispatch_consumer_block_x\":"
            << threads;
  std::cout << ",\"future_kernel_native_dispatch_consumer_shared_mem_bytes\":0";
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_offset\":"
            << dispatch_row_offset;
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_limit\":"
            << dispatch_row_limit;
  std::cout << ",\"future_kernel_native_dispatch_consumer_rows_per_program\":"
            << threads;
  std::cout << ",\"future_kernel_native_dispatch_consumer_active_rows\":"
            << future_native_dispatch_active_rows;
  std::cout << ",\"future_kernel_native_dispatch_consumer_launch_threads\":"
            << dispatch_launch_threads;
  std::cout << ",\"future_kernel_native_dispatch_consumer_program_iteration_checked\":"
            << (future_native_dispatch_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_assignment_formula\":\""
            << "row_offset + program_id * rows_per_program + lane_id\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_program_count\":"
            << dispatch_blocks;
  std::cout << ",\"future_kernel_native_dispatch_consumer_full_program_count\":"
            << dispatch_full_program_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_last_program_active_rows\":"
            << dispatch_last_program_active_rows;
  std::cout << ",\"future_kernel_native_dispatch_consumer_inactive_lane_count\":"
            << dispatch_inactive_lane_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_first_program_row_offset\":"
            << dispatch_first_program_row_offset;
  std::cout << ",\"future_kernel_native_dispatch_consumer_last_program_row_offset\":"
            << dispatch_last_program_row_offset;
  std::cout << ",\"future_kernel_native_dispatch_consumer_program_iteration_hash\":\""
            << std::hex << dispatch_program_iteration_hash << std::dec << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_launch_geometry_checked\":"
            << (future_native_dispatch_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_launch_covers_active_rows\":"
            << (future_native_dispatch_launch_covers_active_rows ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_launch_minimal_cover\":"
            << (future_native_dispatch_launch_minimal_cover ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_count\":"
            << future_native_dispatch_consumer_row_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_ok_count\":"
            << (future_native_dispatch_consumer_checked
                    ? future_native_dispatch_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_dispatch_consumer_error_count\":"
            << future_native_dispatch_consumer_error_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_hash_accumulator\":\""
            << std::hex << future_native_dispatch_consumer_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_dispatch_consumer_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_checked\":"
            << (future_native_dispatch_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_row_count\":"
            << future_native_dispatch_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count\":"
            << (future_native_dispatch_single_field_mirror_checked
                    ? future_native_dispatch_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_error_count\":"
            << future_native_dispatch_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_native_dispatch_single_field_mirror_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_dispatch_consumer_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation\":false";
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
  return all_ok ? 0 : 1;
}
