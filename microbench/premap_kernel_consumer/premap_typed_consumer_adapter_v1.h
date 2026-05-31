#pragma once

#include <cstdint>

#include "premap_typed_consumer_abi_v1.h"

// Future kernel-side consumer adapter for the readonly typed premap ABI.
//
// The adapter is intentionally not the current AWQ WNA16 fused-MoE kernel
// launch signature.  It is a native row-view contract that a future kernel can
// consume after its ABI is updated to accept the typed descriptor/address table.
struct PremapKernelSideTypedConsumerRowV1 {
  uint64_t descriptor_ptr;
  uint64_t packed_weight_descriptor;
  uint64_t scale_metadata_handle;
  uint64_t aux_metadata_handle;
  int32_t expert_id;
  uint64_t address_key_hash;
  uint32_t row_index;
};

constexpr const char* kPremapKernelSideTypedConsumerAdapterV1Name =
    "premap_kernel_side_typed_consumer_adapter_v1";
constexpr bool kPremapKernelSideTypedConsumerAdapterV1PayloadDerefAllowed = false;
constexpr bool kPremapKernelSideTypedConsumerAdapterV1KernelArgPassAllowed = false;
constexpr const char* kPremapKernelSideTypedConsumerPathV1Name =
    "premap_kernel_side_typed_consumer_path_v1";
constexpr const char* kPremapKernelSideCompatibleConsumerAbiV1Name =
    "premap_kernel_side_compatible_consumer_abi_v1";
constexpr const char* kPremapKernelSideCompatibleConsumerAbiV1Mode =
    "readonly_kernel_side_compatible_consumer_abi";
constexpr bool kPremapKernelSideCompatibleConsumerAbiV1PayloadDerefAllowed = false;
constexpr bool kPremapKernelSideCompatibleConsumerAbiV1KernelArgPassAllowed = false;
constexpr bool kPremapKernelSideCompatibleConsumerAbiV1CurrentWna16ArgCompatible =
    false;

// A closer-to-real future kernel argument envelope.  This is still explicitly
// not the current WNA16 kernel argument list; it models the typed object a
// future descriptor/address consumer kernel would receive once its ABI grows a
// readonly premap table slot.
constexpr const char* kPremapFutureKernelSideConsumerArgsV1Name =
    "premap_future_kernel_side_consumer_args_v1";
constexpr const char* kPremapFutureKernelSideConsumerArgsV1Mode =
    "readonly_future_kernel_consumer_args";
constexpr bool kPremapFutureKernelSideConsumerArgsV1PayloadDerefAllowed =
    false;
constexpr bool kPremapFutureKernelSideConsumerArgsV1KernelArgPassAllowed =
    false;
constexpr bool kPremapFutureKernelSideConsumerArgsV1CurrentWna16ArgCompatible =
    false;
constexpr const char* kPremapFutureKernelArgsCompatibleConsumerPathV1Name =
    "premap_future_kernel_args_compatible_consumer_path_v1";
constexpr const char* kPremapFutureKernelArgsCompatibleConsumerPathV1Mode =
    "readonly_future_kernel_args_to_compatible_consumer_path";
constexpr const char* kPremapFutureKernelArgsCompatibleConsumerPathV1Source =
    "premap_future_kernel_side_consumer_args_v1";
constexpr bool
    kPremapFutureKernelArgsCompatibleConsumerPathV1PayloadDerefAllowed = false;
constexpr bool kPremapFutureKernelArgsCompatibleConsumerPathV1KernelArgPassAllowed =
    false;
constexpr bool
    kPremapFutureKernelArgsCompatibleConsumerPathV1CurrentWna16ArgCompatible =
        false;

// A standalone, future-kernel-shaped native ABI.  Unlike the compatibility path
// above, this does not call through the current launch envelope representation;
// it exposes the descriptor/address columns as the fields a future consumer
// kernel would read directly.
constexpr const char* kPremapFutureKernelNativeConsumerAbiV1Name =
    "premap_future_kernel_native_consumer_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerAbiV1Mode =
    "readonly_future_kernel_native_consumer_abi";
constexpr const char* kPremapFutureKernelNativeConsumerAbiV1Source =
    "premap_typed_handle_table_soa_fields";
constexpr bool kPremapFutureKernelNativeConsumerAbiV1PayloadDerefAllowed =
    false;
constexpr bool kPremapFutureKernelNativeConsumerAbiV1KernelArgPassAllowed =
    false;
constexpr bool kPremapFutureKernelNativeConsumerAbiV1CurrentWna16ArgCompatible =
    false;
constexpr const char* kPremapFutureKernelNativeConsumerLaunchAbiV1Name =
    "premap_future_kernel_native_consumer_launch_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerLaunchAbiV1Mode =
    "readonly_future_kernel_native_consumer_launch_abi";
constexpr const char* kPremapFutureKernelNativeConsumerLaunchAbiV1Source =
    "premap_future_kernel_native_consumer_abi_v1";
constexpr uint32_t kPremapFutureKernelNativeConsumerLaunchAbiV1Version = 1;
constexpr bool kPremapFutureKernelNativeConsumerLaunchAbiV1PayloadDerefAllowed =
    false;
constexpr bool kPremapFutureKernelNativeConsumerLaunchAbiV1KernelArgPassAllowed =
    false;
constexpr bool
    kPremapFutureKernelNativeConsumerLaunchAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char* kPremapFutureKernelNativeConsumerDispatchAbiV1Name =
    "premap_future_kernel_native_consumer_dispatch_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerDispatchAbiV1Mode =
    "readonly_future_kernel_native_consumer_dispatch_abi";
constexpr const char* kPremapFutureKernelNativeConsumerDispatchAbiV1Source =
    "premap_future_kernel_native_consumer_launch_abi_v1";
constexpr uint32_t kPremapFutureKernelNativeConsumerDispatchAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerDispatchAbiV1PayloadDerefAllowed = false;
constexpr bool
    kPremapFutureKernelNativeConsumerDispatchAbiV1KernelArgPassAllowed = false;
constexpr bool
    kPremapFutureKernelNativeConsumerDispatchAbiV1CurrentWna16ArgCompatible =
        false;

constexpr uint32_t kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag = 1u << 0;
constexpr uint32_t
    kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag = 1u << 1;
constexpr uint32_t
    kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag = 1u << 2;
constexpr uint32_t kPremapFutureKernelSideConsumerArgsV1RequiredFlags =
    kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag |
    kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag |
    kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag;

constexpr uint32_t kPremapFutureKernelSideConsumerFieldNone = 0;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldDescriptorPtr = 1;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor = 2;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldScaleMetadataHandle = 3;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldAuxMetadataHandle = 4;

constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskDescriptorPtr =
    1u << 0;
constexpr uint32_t
    kPremapFutureKernelSideConsumerFieldMaskPackedWeightDescriptor = 1u << 1;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskScaleMetadataHandle =
    1u << 2;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle =
    1u << 3;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskRequired =
    kPremapFutureKernelSideConsumerFieldMaskDescriptorPtr |
    kPremapFutureKernelSideConsumerFieldMaskPackedWeightDescriptor |
    kPremapFutureKernelSideConsumerFieldMaskScaleMetadataHandle;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskAll =
    kPremapFutureKernelSideConsumerFieldMaskRequired |
    kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle;

struct PremapKernelSideTypedConsumerLaunchEnvelopeV1 {
  PremapKernelSideTypedConsumerAbiV1 table;
  uint64_t expected_schema_hash_hi;
  uint64_t expected_schema_hash_lo;
  uint64_t expected_row_order_hash;
  uint64_t expected_ordered_row_hash;
  uint32_t expected_row_count;
  uint32_t expected_column_count;
  uint32_t payload_bytes;
  uint32_t flags;
};

struct PremapFutureKernelSideConsumerArgsV1 {
  PremapKernelSideTypedConsumerLaunchEnvelopeV1 envelope;
  uint32_t field_mask;
  uint32_t single_field_mirror_kind;
  uint32_t payload_bytes;
  uint32_t flags;
};

struct PremapFutureKernelNativeConsumerParamsV1 {
  const uint64_t* descriptor_ptr;
  const uint64_t* packed_weight_descriptor;
  const uint64_t* scale_metadata_handle;
  const uint64_t* aux_metadata_handle;
  const int32_t* expert_id;
  const uint64_t* address_key_hash;
  uint64_t typed_schema_hash_hi;
  uint64_t typed_schema_hash_lo;
  uint64_t row_order_hash;
  uint64_t ordered_row_hash;
  uint32_t row_count;
  uint32_t column_count;
  uint32_t lifetime_epoch;
  uint32_t field_mask;
  uint32_t single_field_mirror_kind;
  uint32_t payload_bytes;
  uint32_t flags;
};

// A launch-shaped wrapper around the standalone native consumer params. This
// mirrors the object a future kernel launch would receive after a real ABI slot
// exists, but remains independent from the current WNA16 argument list.
struct PremapFutureKernelNativeConsumerLaunchV1 {
  PremapFutureKernelNativeConsumerParamsV1 params;
  uint32_t abi_version;
  uint32_t params_struct_size;
  uint32_t result_struct_size;
  uint32_t row_stride;
  uint32_t payload_bytes;
  uint32_t flags;
};

// Dispatch-shaped readonly wrapper.  This is the closest native stub to a
// future launch site: it carries the launch ABI plus row-window and launch-shape
// metadata a real kernel-side consumer would see, while still avoiding payload
// dereference and current WNA16 kernel-argument mutation.
struct PremapFutureKernelNativeConsumerDispatchV1 {
  PremapFutureKernelNativeConsumerLaunchV1 launch;
  uint32_t dispatch_version;
  uint32_t grid_x;
  uint32_t block_x;
  uint32_t shared_mem_bytes;
  uint32_t row_offset;
  uint32_t row_limit;
  uint32_t rows_per_program;
  uint32_t payload_bytes;
  uint32_t flags;
};

constexpr const char* kPremapKernelSideTypedConsumerLaunchEnvelopeV1Name =
    "premap_kernel_side_typed_consumer_launch_envelope_v1";
constexpr uint32_t kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag =
    1u << 0;
constexpr uint32_t
    kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag =
        1u << 1;

struct PremapKernelSideTypedConsumerPathResultV1 {
  uint32_t ok;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t field_count;
  uint64_t row_hash;
};

struct PremapKernelSideCompatibleConsumerResultV1 {
  uint32_t ok;
  uint32_t envelope_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t field_count;
  uint64_t row_hash;
};

struct PremapFutureKernelSideConsumerResultV1 {
  uint32_t ok;
  uint32_t args_valid;
  uint32_t envelope_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t single_field_mirror_checked;
  uint32_t single_field_mirror_ok;
  uint32_t single_field_mirror_kind;
  uint32_t field_count;
  uint64_t row_hash;
  uint64_t single_field_mirror_hash;
};

struct PremapFutureKernelArgsCompatibleConsumerPathResultV1 {
  uint32_t ok;
  uint32_t args_valid;
  uint32_t compatible_consumer_ok;
  uint32_t envelope_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t field_count;
  uint64_t row_hash;
};

struct PremapFutureKernelNativeConsumerResultV1 {
  uint32_t ok;
  uint32_t params_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t single_field_mirror_checked;
  uint32_t single_field_mirror_ok;
  uint32_t single_field_mirror_kind;
  uint32_t field_count;
  uint64_t row_hash;
  uint64_t single_field_mirror_hash;
};

struct PremapFutureKernelNativeConsumerLaunchResultV1 {
  uint32_t ok;
  uint32_t launch_valid;
  uint32_t native_consumer_ok;
  uint32_t params_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t single_field_mirror_checked;
  uint32_t single_field_mirror_ok;
  uint32_t single_field_mirror_kind;
  uint32_t field_count;
  uint64_t row_hash;
  uint64_t single_field_mirror_hash;
};

struct PremapFutureKernelNativeConsumerDispatchResultV1 {
  uint32_t ok;
  uint32_t dispatch_valid;
  uint32_t launch_geometry_valid;
  uint32_t launch_consumer_ok;
  uint32_t launch_valid;
  uint32_t row_window_valid;
  uint32_t active_rows;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t single_field_mirror_checked;
  uint32_t single_field_mirror_ok;
  uint32_t single_field_mirror_kind;
  uint32_t field_count;
  uint64_t row_hash;
  uint64_t single_field_mirror_hash;
};

__host__ __device__ static inline uint64_t
premap_typed_consumer_mix64_v1(uint64_t x) {
  x ^= x >> 33;
  x *= 0xff51afd7ed558ccdULL;
  x ^= x >> 33;
  x *= 0xc4ceb9fe1a85ec53ULL;
  x ^= x >> 33;
  return x;
}

__host__ __device__ static inline bool
premap_typed_consumer_schema_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  return table.typed_schema_hash_hi == expected_schema_hash_hi &&
         table.typed_schema_hash_lo == expected_schema_hash_lo &&
         table.column_count == kPremapKernelSideTypedConsumerAbiV1HandleColumnCount &&
         table.row_count > 0 && table.descriptor_ptr != nullptr &&
         table.packed_weight_descriptor != nullptr &&
         table.scale_metadata_handle != nullptr && table.expert_id != nullptr &&
         table.address_key_hash != nullptr;
}

__host__ __device__ static inline bool
premap_typed_consumer_launch_envelope_matches_v1(
    const PremapKernelSideTypedConsumerLaunchEnvelopeV1& envelope) {
  return premap_typed_consumer_schema_matches_v1(
             envelope.table,
             envelope.expected_schema_hash_hi,
             envelope.expected_schema_hash_lo) &&
         envelope.table.row_count == envelope.expected_row_count &&
         envelope.table.column_count == envelope.expected_column_count &&
         envelope.table.row_order_hash == envelope.expected_row_order_hash &&
         envelope.table.ordered_row_hash == envelope.expected_ordered_row_hash &&
         envelope.payload_bytes == 0 &&
         (envelope.flags &
          kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag) != 0 &&
         (envelope.flags &
          kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag) !=
             0;
}

__host__ __device__ static inline bool
premap_typed_consumer_future_kernel_args_match_v1(
    const PremapFutureKernelSideConsumerArgsV1& args) {
  return premap_typed_consumer_launch_envelope_matches_v1(args.envelope) &&
         args.payload_bytes == 0 &&
         (args.flags & kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (args.flags &
         kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (args.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         args.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         (args.field_mask & ~kPremapFutureKernelSideConsumerFieldMaskAll) == 0 &&
         (args.field_mask & kPremapFutureKernelSideConsumerFieldMaskRequired) ==
             kPremapFutureKernelSideConsumerFieldMaskRequired &&
         !kPremapFutureKernelSideConsumerArgsV1PayloadDerefAllowed &&
         !kPremapFutureKernelSideConsumerArgsV1KernelArgPassAllowed &&
         !kPremapFutureKernelSideConsumerArgsV1CurrentWna16ArgCompatible;
}

__host__ __device__ static inline bool
premap_typed_consumer_future_native_params_match_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  return params.typed_schema_hash_hi == expected_schema_hash_hi &&
         params.typed_schema_hash_lo == expected_schema_hash_lo &&
         params.column_count == kPremapKernelSideTypedConsumerAbiV1HandleColumnCount &&
         params.row_count > 0 && params.descriptor_ptr != nullptr &&
         params.packed_weight_descriptor != nullptr &&
         params.scale_metadata_handle != nullptr && params.expert_id != nullptr &&
         params.address_key_hash != nullptr && params.lifetime_epoch == 1 &&
         params.payload_bytes == 0 &&
         (params.flags & kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (params.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (params.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         params.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         (params.field_mask & ~kPremapFutureKernelSideConsumerFieldMaskAll) == 0 &&
         (params.field_mask & kPremapFutureKernelSideConsumerFieldMaskRequired) ==
             kPremapFutureKernelSideConsumerFieldMaskRequired &&
         !kPremapFutureKernelNativeConsumerAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerAbiV1CurrentWna16ArgCompatible;
}

__host__ __device__ static inline bool
premap_typed_consumer_future_native_launch_matches_v1(
    const PremapFutureKernelNativeConsumerLaunchV1& launch,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  return premap_typed_consumer_future_native_params_match_v1(
             launch.params,
             expected_schema_hash_hi,
             expected_schema_hash_lo) &&
         launch.abi_version ==
             kPremapFutureKernelNativeConsumerLaunchAbiV1Version &&
         launch.params_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerParamsV1) &&
         launch.result_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerLaunchResultV1) &&
         launch.row_stride == 1 && launch.payload_bytes == 0 &&
         (launch.flags & kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (launch.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (launch.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         launch.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerLaunchAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerLaunchAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerLaunchAbiV1CurrentWna16ArgCompatible;
}

__host__ __device__ static inline bool
premap_typed_consumer_future_native_dispatch_matches_v1(
    const PremapFutureKernelNativeConsumerDispatchV1& dispatch,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  const bool row_window_valid =
      dispatch.row_offset <= dispatch.launch.params.row_count &&
      dispatch.row_limit <= dispatch.launch.params.row_count &&
      dispatch.row_offset < dispatch.row_limit;
  const uint32_t active_rows =
      row_window_valid ? (dispatch.row_limit - dispatch.row_offset) : 0;
  const uint64_t launched_threads =
      static_cast<uint64_t>(dispatch.grid_x) *
      static_cast<uint64_t>(dispatch.block_x);
  const uint64_t previous_grid_threads =
      dispatch.grid_x > 0
          ? static_cast<uint64_t>(dispatch.grid_x - 1) *
                static_cast<uint64_t>(dispatch.block_x)
          : 0;
  return premap_typed_consumer_future_native_launch_matches_v1(
             dispatch.launch,
             expected_schema_hash_hi,
             expected_schema_hash_lo) &&
         dispatch.dispatch_version ==
             kPremapFutureKernelNativeConsumerDispatchAbiV1Version &&
         dispatch.grid_x > 0 && dispatch.block_x > 0 &&
         row_window_valid && active_rows > 0 &&
         launched_threads >= static_cast<uint64_t>(active_rows) &&
         previous_grid_threads < static_cast<uint64_t>(active_rows) &&
         dispatch.rows_per_program == dispatch.block_x &&
         dispatch.payload_bytes == 0 &&
         (dispatch.flags & kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (dispatch.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (dispatch.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         dispatch.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerDispatchAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerDispatchAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerDispatchAbiV1CurrentWna16ArgCompatible;
}

__device__ static inline PremapKernelSideTypedConsumerRowV1
premap_typed_consumer_load_row_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    uint32_t row_index) {
  PremapKernelSideTypedConsumerRowV1 row;
  row.descriptor_ptr = table.descriptor_ptr[row_index];
  row.packed_weight_descriptor = table.packed_weight_descriptor[row_index];
  row.scale_metadata_handle = table.scale_metadata_handle[row_index];
  row.aux_metadata_handle =
      table.aux_metadata_handle == nullptr ? 0ULL : table.aux_metadata_handle[row_index];
  row.expert_id = table.expert_id[row_index];
  row.address_key_hash = table.address_key_hash[row_index];
  row.row_index = row_index;
  return row;
}

__device__ static inline PremapKernelSideTypedConsumerRowV1
premap_typed_consumer_load_future_native_row_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    uint32_t row_index) {
  PremapKernelSideTypedConsumerRowV1 row;
  row.descriptor_ptr = params.descriptor_ptr[row_index];
  row.packed_weight_descriptor = params.packed_weight_descriptor[row_index];
  row.scale_metadata_handle = params.scale_metadata_handle[row_index];
  row.aux_metadata_handle =
      params.aux_metadata_handle == nullptr ? 0ULL : params.aux_metadata_handle[row_index];
  row.expert_id = params.expert_id[row_index];
  row.address_key_hash = params.address_key_hash[row_index];
  row.row_index = row_index;
  return row;
}

__device__ static inline uint32_t
premap_typed_consumer_required_handles_visible_v1(
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      row.descriptor_ptr != 0 && row.packed_weight_descriptor != 0 &&
      row.scale_metadata_handle != 0);
}

__device__ static inline uint32_t
premap_typed_consumer_descriptor_ptr_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.descriptor_ptr != nullptr && row.descriptor_ptr != 0 &&
      row.descriptor_ptr == table.descriptor_ptr[row.row_index]);
}

__device__ static inline uint32_t
premap_typed_consumer_scale_metadata_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.scale_metadata_handle != nullptr && row.scale_metadata_handle != 0 &&
      row.scale_metadata_handle == table.scale_metadata_handle[row.row_index]);
}

__device__ static inline uint32_t
premap_typed_consumer_packed_weight_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.packed_weight_descriptor != nullptr &&
      row.packed_weight_descriptor != 0 &&
      row.packed_weight_descriptor == table.packed_weight_descriptor[row.row_index]);
}

__device__ static inline uint32_t
premap_typed_consumer_aux_metadata_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.aux_metadata_handle != nullptr && row.aux_metadata_handle != 0 &&
      row.aux_metadata_handle == table.aux_metadata_handle[row.row_index]);
}

__device__ static inline uint32_t
premap_typed_consumer_lifetime_valid_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.lifetime_epoch == 1 && row.address_key_hash != 0 && row.expert_id >= 0);
}

__device__ static inline PremapKernelSideTypedConsumerPathResultV1
premap_typed_consumer_kernel_side_consume_row_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    uint32_t row_index) {
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(table, row_index);
  PremapKernelSideTypedConsumerPathResultV1 result;
  result.required_handle_visible =
      premap_typed_consumer_required_handles_visible_v1(row);
  result.lifetime_valid = premap_typed_consumer_lifetime_valid_v1(table, row);
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.ok = static_cast<uint32_t>(
      result.required_handle_visible != 0 && result.lifetime_valid != 0 &&
      row_index < table.row_count &&
      table.column_count == kPremapKernelSideTypedConsumerAbiV1HandleColumnCount);
  result.row_hash =
      premap_typed_consumer_mix64_v1(row.descriptor_ptr) ^
      premap_typed_consumer_mix64_v1(row.packed_weight_descriptor + 0x1000ULL) ^
      premap_typed_consumer_mix64_v1(row.scale_metadata_handle + 0x2000ULL) ^
      premap_typed_consumer_mix64_v1(row.aux_metadata_handle + 0x3000ULL) ^
      premap_typed_consumer_mix64_v1(
          row.address_key_hash + static_cast<uint64_t>(row.expert_id)) ^
      premap_typed_consumer_mix64_v1(static_cast<uint64_t>(row.row_index)) ^
      premap_typed_consumer_mix64_v1(table.row_order_hash) ^
      premap_typed_consumer_mix64_v1(table.ordered_row_hash);
  return result;
}

__device__ static inline PremapKernelSideCompatibleConsumerResultV1
premap_typed_consumer_kernel_side_compatible_consume_row_v1(
    const PremapKernelSideTypedConsumerLaunchEnvelopeV1& envelope,
    uint32_t row_index) {
  PremapKernelSideCompatibleConsumerResultV1 result;
  result.envelope_valid = static_cast<uint32_t>(
      premap_typed_consumer_launch_envelope_matches_v1(envelope));
  result.row_valid = static_cast<uint32_t>(row_index < envelope.table.row_count);
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.row_hash = 0;
  if (result.envelope_valid == 0 || result.row_valid == 0) {
    result.ok = 0;
    return result;
  }
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(envelope.table, row_index);
  result.required_handle_visible =
      premap_typed_consumer_required_handles_visible_v1(row);
  result.lifetime_valid =
      premap_typed_consumer_lifetime_valid_v1(envelope.table, row);
  result.ok = static_cast<uint32_t>(
      result.envelope_valid != 0 && result.row_valid != 0 &&
      result.required_handle_visible != 0 && result.lifetime_valid != 0 &&
      !kPremapKernelSideCompatibleConsumerAbiV1PayloadDerefAllowed &&
      !kPremapKernelSideCompatibleConsumerAbiV1KernelArgPassAllowed &&
      !kPremapKernelSideCompatibleConsumerAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(row.descriptor_ptr + 0xd35c0001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.packed_weight_descriptor + 0x9ac6ed01ULL) ^
      premap_typed_consumer_mix64_v1(
          row.scale_metadata_handle + 0x5ca1e001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.aux_metadata_handle + 0xa11c0001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.address_key_hash + static_cast<uint64_t>(row.expert_id)) ^
      premap_typed_consumer_mix64_v1(static_cast<uint64_t>(row.row_index)) ^
      premap_typed_consumer_mix64_v1(envelope.expected_row_order_hash) ^
      premap_typed_consumer_mix64_v1(envelope.expected_ordered_row_hash);
  return result;
}

__device__ static inline uint32_t
premap_typed_consumer_future_kernel_single_field_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row,
    uint32_t mirror_kind) {
  switch (mirror_kind) {
    case kPremapFutureKernelSideConsumerFieldDescriptorPtr:
      return premap_typed_consumer_descriptor_ptr_mirror_matches_v1(table, row);
    case kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor:
      return premap_typed_consumer_packed_weight_mirror_matches_v1(table, row);
    case kPremapFutureKernelSideConsumerFieldScaleMetadataHandle:
      return premap_typed_consumer_scale_metadata_mirror_matches_v1(table, row);
    case kPremapFutureKernelSideConsumerFieldAuxMetadataHandle:
      return premap_typed_consumer_aux_metadata_mirror_matches_v1(table, row);
    case kPremapFutureKernelSideConsumerFieldNone:
    default:
      return 0;
  }
}

__device__ static inline uint64_t
premap_typed_consumer_future_kernel_single_field_mirror_hash_v1(
    const PremapKernelSideTypedConsumerRowV1& row,
    uint32_t mirror_kind) {
  switch (mirror_kind) {
    case kPremapFutureKernelSideConsumerFieldDescriptorPtr:
      return premap_typed_consumer_mix64_v1(
                 row.descriptor_ptr + 0xf17d000000000001ULL) ^
             premap_typed_consumer_mix64_v1(row.row_index);
    case kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor:
      return premap_typed_consumer_mix64_v1(
                 row.packed_weight_descriptor + 0xf17d000000000002ULL) ^
             premap_typed_consumer_mix64_v1(row.row_index);
    case kPremapFutureKernelSideConsumerFieldScaleMetadataHandle:
      return premap_typed_consumer_mix64_v1(
                 row.scale_metadata_handle + 0xf17d000000000003ULL) ^
             premap_typed_consumer_mix64_v1(row.row_index);
    case kPremapFutureKernelSideConsumerFieldAuxMetadataHandle:
      return premap_typed_consumer_mix64_v1(
                 row.aux_metadata_handle + 0xf17d000000000004ULL) ^
             premap_typed_consumer_mix64_v1(row.row_index);
    case kPremapFutureKernelSideConsumerFieldNone:
    default:
      return 0;
  }
}

__device__ static inline PremapFutureKernelSideConsumerResultV1
premap_typed_consumer_future_kernel_consume_row_v1(
    const PremapFutureKernelSideConsumerArgsV1& args,
    uint32_t row_index) {
  PremapFutureKernelSideConsumerResultV1 result;
  result.args_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_kernel_args_match_v1(args));
  result.envelope_valid = static_cast<uint32_t>(
      premap_typed_consumer_launch_envelope_matches_v1(args.envelope));
  result.row_valid = static_cast<uint32_t>(row_index < args.envelope.table.row_count);
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.single_field_mirror_checked = static_cast<uint32_t>(
      args.single_field_mirror_kind != kPremapFutureKernelSideConsumerFieldNone);
  result.single_field_mirror_ok = 0;
  result.single_field_mirror_kind = args.single_field_mirror_kind;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.row_hash = 0;
  result.single_field_mirror_hash = 0;
  if (result.args_valid == 0 || result.envelope_valid == 0 ||
      result.row_valid == 0) {
    result.ok = 0;
    return result;
  }
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(args.envelope.table, row_index);
  result.required_handle_visible =
      premap_typed_consumer_required_handles_visible_v1(row);
  result.lifetime_valid =
      premap_typed_consumer_lifetime_valid_v1(args.envelope.table, row);
  if (result.single_field_mirror_checked != 0) {
    result.single_field_mirror_ok =
        premap_typed_consumer_future_kernel_single_field_mirror_matches_v1(
            args.envelope.table, row, args.single_field_mirror_kind);
    result.single_field_mirror_hash =
        premap_typed_consumer_future_kernel_single_field_mirror_hash_v1(
            row, args.single_field_mirror_kind);
  }
  const uint32_t mirror_gate =
      result.single_field_mirror_checked == 0 || result.single_field_mirror_ok != 0;
  result.ok = static_cast<uint32_t>(
      result.args_valid != 0 && result.envelope_valid != 0 &&
      result.row_valid != 0 && result.required_handle_visible != 0 &&
      result.lifetime_valid != 0 && mirror_gate != 0);
  result.row_hash =
      premap_typed_consumer_mix64_v1(row.descriptor_ptr + 0xf00d0001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.packed_weight_descriptor + 0xf00d0002ULL) ^
      premap_typed_consumer_mix64_v1(
          row.scale_metadata_handle + 0xf00d0003ULL) ^
      premap_typed_consumer_mix64_v1(
          row.aux_metadata_handle + 0xf00d0004ULL) ^
      premap_typed_consumer_mix64_v1(
          row.address_key_hash + static_cast<uint64_t>(row.expert_id)) ^
      premap_typed_consumer_mix64_v1(row.row_index) ^
      premap_typed_consumer_mix64_v1(args.field_mask) ^
      premap_typed_consumer_mix64_v1(args.single_field_mirror_kind) ^
      premap_typed_consumer_mix64_v1(args.envelope.expected_row_order_hash) ^
      premap_typed_consumer_mix64_v1(args.envelope.expected_ordered_row_hash);
  return result;
}

__device__ static inline PremapFutureKernelArgsCompatibleConsumerPathResultV1
premap_typed_consumer_future_kernel_args_compatible_consume_row_v1(
    const PremapFutureKernelSideConsumerArgsV1& args,
    uint32_t row_index) {
  PremapFutureKernelArgsCompatibleConsumerPathResultV1 result;
  result.args_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_kernel_args_match_v1(args));
  const PremapKernelSideCompatibleConsumerResultV1 compatible =
      premap_typed_consumer_kernel_side_compatible_consume_row_v1(
          args.envelope, row_index);
  result.compatible_consumer_ok = compatible.ok;
  result.envelope_valid = compatible.envelope_valid;
  result.row_valid = compatible.row_valid;
  result.required_handle_visible = compatible.required_handle_visible;
  result.lifetime_valid = compatible.lifetime_valid;
  result.field_count = compatible.field_count;
  result.ok = static_cast<uint32_t>(
      result.args_valid != 0 && result.compatible_consumer_ok != 0 &&
      !kPremapFutureKernelArgsCompatibleConsumerPathV1PayloadDerefAllowed &&
      !kPremapFutureKernelArgsCompatibleConsumerPathV1KernelArgPassAllowed &&
      !kPremapFutureKernelArgsCompatibleConsumerPathV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(compatible.row_hash + 0xfc0a0001ULL) ^
      premap_typed_consumer_mix64_v1(args.field_mask + 0xfc0a0002ULL) ^
      premap_typed_consumer_mix64_v1(
          args.envelope.expected_row_order_hash + 0xfc0a0003ULL) ^
      premap_typed_consumer_mix64_v1(
          args.envelope.expected_ordered_row_hash + 0xfc0a0004ULL);
  return result;
}

__device__ static inline uint32_t
premap_typed_consumer_future_native_single_field_mirror_matches_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    const PremapKernelSideTypedConsumerRowV1& row,
    uint32_t mirror_kind) {
  switch (mirror_kind) {
    case kPremapFutureKernelSideConsumerFieldDescriptorPtr:
      return static_cast<uint32_t>(
          params.descriptor_ptr != nullptr && row.descriptor_ptr != 0 &&
          row.descriptor_ptr == params.descriptor_ptr[row.row_index]);
    case kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor:
      return static_cast<uint32_t>(
          params.packed_weight_descriptor != nullptr &&
          row.packed_weight_descriptor != 0 &&
          row.packed_weight_descriptor ==
              params.packed_weight_descriptor[row.row_index]);
    case kPremapFutureKernelSideConsumerFieldScaleMetadataHandle:
      return static_cast<uint32_t>(
          params.scale_metadata_handle != nullptr &&
          row.scale_metadata_handle != 0 &&
          row.scale_metadata_handle == params.scale_metadata_handle[row.row_index]);
    case kPremapFutureKernelSideConsumerFieldAuxMetadataHandle:
      return static_cast<uint32_t>(
          params.aux_metadata_handle != nullptr && row.aux_metadata_handle != 0 &&
          row.aux_metadata_handle == params.aux_metadata_handle[row.row_index]);
    case kPremapFutureKernelSideConsumerFieldNone:
    default:
      return 0;
  }
}

__device__ static inline uint32_t
premap_typed_consumer_future_native_lifetime_valid_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      params.lifetime_epoch == 1 && row.address_key_hash != 0 &&
      row.expert_id >= 0);
}

__device__ static inline PremapFutureKernelNativeConsumerResultV1
premap_typed_consumer_future_native_consume_row_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    uint32_t row_index,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerResultV1 result;
  result.params_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_params_match_v1(
          params, expected_schema_hash_hi, expected_schema_hash_lo));
  result.row_valid = static_cast<uint32_t>(row_index < params.row_count);
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.single_field_mirror_checked = static_cast<uint32_t>(
      params.single_field_mirror_kind != kPremapFutureKernelSideConsumerFieldNone);
  result.single_field_mirror_ok = 0;
  result.single_field_mirror_kind = params.single_field_mirror_kind;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.row_hash = 0;
  result.single_field_mirror_hash = 0;
  if (result.params_valid == 0 || result.row_valid == 0) {
    result.ok = 0;
    return result;
  }
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_future_native_row_v1(params, row_index);
  result.required_handle_visible =
      premap_typed_consumer_required_handles_visible_v1(row);
  result.lifetime_valid =
      premap_typed_consumer_future_native_lifetime_valid_v1(params, row);
  if (result.single_field_mirror_checked != 0) {
    result.single_field_mirror_ok =
        premap_typed_consumer_future_native_single_field_mirror_matches_v1(
            params, row, params.single_field_mirror_kind);
    result.single_field_mirror_hash =
        premap_typed_consumer_future_kernel_single_field_mirror_hash_v1(
            row, params.single_field_mirror_kind);
  }
  const uint32_t mirror_gate =
      result.single_field_mirror_checked == 0 || result.single_field_mirror_ok != 0;
  result.ok = static_cast<uint32_t>(
      result.params_valid != 0 && result.row_valid != 0 &&
      result.required_handle_visible != 0 && result.lifetime_valid != 0 &&
      mirror_gate != 0 &&
      !kPremapFutureKernelNativeConsumerAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(row.descriptor_ptr + 0xab100001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.packed_weight_descriptor + 0xab100002ULL) ^
      premap_typed_consumer_mix64_v1(
          row.scale_metadata_handle + 0xab100003ULL) ^
      premap_typed_consumer_mix64_v1(
          row.aux_metadata_handle + 0xab100004ULL) ^
      premap_typed_consumer_mix64_v1(
          row.address_key_hash + static_cast<uint64_t>(row.expert_id)) ^
      premap_typed_consumer_mix64_v1(row.row_index) ^
      premap_typed_consumer_mix64_v1(params.field_mask) ^
      premap_typed_consumer_mix64_v1(params.single_field_mirror_kind) ^
      premap_typed_consumer_mix64_v1(params.row_order_hash) ^
      premap_typed_consumer_mix64_v1(params.ordered_row_hash);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerLaunchResultV1
premap_typed_consumer_future_native_launch_consume_row_v1(
    const PremapFutureKernelNativeConsumerLaunchV1& launch,
    uint32_t row_index,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerLaunchResultV1 result;
  result.launch_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_launch_matches_v1(
          launch, expected_schema_hash_hi, expected_schema_hash_lo));
  const PremapFutureKernelNativeConsumerResultV1 native =
      premap_typed_consumer_future_native_consume_row_v1(
          launch.params,
          row_index,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.native_consumer_ok = native.ok;
  result.params_valid = native.params_valid;
  result.row_valid = native.row_valid;
  result.required_handle_visible = native.required_handle_visible;
  result.lifetime_valid = native.lifetime_valid;
  result.single_field_mirror_checked = native.single_field_mirror_checked;
  result.single_field_mirror_ok = native.single_field_mirror_ok;
  result.single_field_mirror_kind = native.single_field_mirror_kind;
  result.field_count = native.field_count;
  result.single_field_mirror_hash = native.single_field_mirror_hash;
  result.ok = static_cast<uint32_t>(
      result.launch_valid != 0 && result.native_consumer_ok != 0 &&
      !kPremapFutureKernelNativeConsumerLaunchAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerLaunchAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerLaunchAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(native.row_hash + 0x1a9c000000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(launch.abi_version) + 0x1a9c0002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(launch.params_struct_size) + 0x1a9c0003ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(launch.row_stride) + 0x1a9c0004ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerDispatchResultV1
premap_typed_consumer_future_native_dispatch_consume_row_v1(
    const PremapFutureKernelNativeConsumerDispatchV1& dispatch,
    uint32_t local_row_index,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerDispatchResultV1 result;
  result.dispatch_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_dispatch_matches_v1(
          dispatch, expected_schema_hash_hi, expected_schema_hash_lo));
  result.launch_geometry_valid = static_cast<uint32_t>(
      actual_grid_x == dispatch.grid_x && actual_block_x == dispatch.block_x);
  result.active_rows =
      dispatch.row_limit >= dispatch.row_offset
          ? dispatch.row_limit - dispatch.row_offset
          : 0;
  const bool row_index_add_valid =
      local_row_index <= (0xffffffffu - dispatch.row_offset);
  const uint32_t row_index =
      row_index_add_valid ? dispatch.row_offset + local_row_index : 0;
  result.row_window_valid = static_cast<uint32_t>(
      row_index_add_valid && local_row_index < result.active_rows &&
      row_index < dispatch.row_limit && row_index < dispatch.launch.params.row_count);
  result.launch_consumer_ok = 0;
  result.launch_valid = 0;
  result.row_valid = 0;
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.single_field_mirror_checked = 0;
  result.single_field_mirror_ok = 0;
  result.single_field_mirror_kind = kPremapFutureKernelSideConsumerFieldNone;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.single_field_mirror_hash = 0;
  result.row_hash = 0;
  if (result.dispatch_valid == 0 || result.launch_geometry_valid == 0 ||
      result.row_window_valid == 0) {
    result.ok = 0;
    return result;
  }
  const PremapFutureKernelNativeConsumerLaunchResultV1 launch_result =
      premap_typed_consumer_future_native_launch_consume_row_v1(
          dispatch.launch,
          row_index,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.launch_consumer_ok = launch_result.ok;
  result.launch_valid = launch_result.launch_valid;
  result.row_valid = launch_result.row_valid;
  result.required_handle_visible = launch_result.required_handle_visible;
  result.lifetime_valid = launch_result.lifetime_valid;
  result.single_field_mirror_checked =
      launch_result.single_field_mirror_checked;
  result.single_field_mirror_ok = launch_result.single_field_mirror_ok;
  result.single_field_mirror_kind = launch_result.single_field_mirror_kind;
  result.field_count = launch_result.field_count;
  result.single_field_mirror_hash = launch_result.single_field_mirror_hash;
  result.ok = static_cast<uint32_t>(
      result.dispatch_valid != 0 && result.launch_geometry_valid != 0 &&
      result.row_window_valid != 0 && result.launch_consumer_ok != 0 &&
      !kPremapFutureKernelNativeConsumerDispatchAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerDispatchAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerDispatchAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(
          launch_result.row_hash + 0xd15c000000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.dispatch_version) + 0xd15c0002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.grid_x) + 0xd15c0003ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.block_x) + 0xd15c0004ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.row_offset) + 0xd15c0005ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.row_limit) + 0xd15c0006ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerDispatchResultV1
premap_typed_consumer_future_native_dispatch_consume_program_lane_v1(
    const PremapFutureKernelNativeConsumerDispatchV1& dispatch,
    uint32_t program_id,
    uint32_t lane_id,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  const bool program_lane_valid =
      program_id < actual_grid_x && lane_id < actual_block_x &&
      program_id < dispatch.grid_x && lane_id < dispatch.block_x &&
      lane_id < dispatch.rows_per_program;
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(dispatch.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  const bool local_row_index_valid = local_row_index_64 <= 0xffffffffULL;
  PremapFutureKernelNativeConsumerDispatchResultV1 result =
      premap_typed_consumer_future_native_dispatch_consume_row_v1(
          dispatch,
          local_row_index_valid ? static_cast<uint32_t>(local_row_index_64) : 0,
          actual_grid_x,
          actual_block_x,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.ok = static_cast<uint32_t>(
      result.ok != 0 && program_lane_valid && local_row_index_valid);
  if (!program_lane_valid || !local_row_index_valid) {
    result.row_window_valid = 0;
    result.row_valid = 0;
    result.launch_consumer_ok = 0;
    result.required_handle_visible = 0;
    result.lifetime_valid = 0;
  }
  result.row_hash ^=
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(program_id) + 0xd15c100000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(lane_id) + 0xd15c100000000002ULL) ^
      premap_typed_consumer_mix64_v1(local_row_index_64 + 0xd15c100000000003ULL);
  return result;
}
