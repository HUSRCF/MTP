#pragma once

#include <cstdint>

// Future kernel-side typed consumer ABI for readonly descriptor/address prep.
// This is not the current AWQ WNA16 fused-MoE kernel argument list.  The table
// is a no-payload struct-of-arrays handle view that native canaries can consume
// before any real kernel-argument handoff exists.
struct PremapKernelSideTypedConsumerAbiV1 {
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

constexpr const char* kPremapKernelSideTypedConsumerAbiV1Name =
    "premap_kernel_side_typed_consumer_abi_v1";
constexpr uint32_t kPremapKernelSideTypedConsumerAbiV1HandleColumnCount = 4;
constexpr bool kPremapKernelSideTypedConsumerAbiV1PayloadBytesAllowed = false;
constexpr bool kPremapKernelSideTypedConsumerAbiV1KernelArgPassAllowed = false;

