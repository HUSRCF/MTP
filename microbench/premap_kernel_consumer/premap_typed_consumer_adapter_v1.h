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
